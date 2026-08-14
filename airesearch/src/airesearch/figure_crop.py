from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


RunCommand = Callable[..., Any]


@dataclass(frozen=True)
class WordBox:
    left: float
    top: float
    right: float
    bottom: float
    text: str


@dataclass(frozen=True)
class TextLine:
    left: float
    top: float
    right: float
    bottom: float
    words: tuple[WordBox, ...]
    text: str


@dataclass(frozen=True)
class TextBlock:
    left: float
    top: float
    right: float
    bottom: float
    lines: tuple[TextLine, ...]
    text: str


@dataclass(frozen=True)
class PageLayout:
    number: int
    width: float
    height: float
    blocks: tuple[TextBlock, ...]


@dataclass(frozen=True)
class CaptionMatch:
    page: PageLayout
    block: TextBlock
    confidence: float
    candidate_count: int
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class CropPlan:
    page: int
    left: float
    top: float
    right: float
    bottom: float
    confidence: float
    accepted: bool
    reasons: tuple[str, ...]
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class CropResult:
    path: Path | None
    confidence: float
    accepted: bool
    reasons: tuple[str, ...]
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class FigureCaption:
    page: int
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    page_width: float
    page_height: float


def _run(command: list[str], *, timeout: int = 30) -> None:
    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
    )


def _required_tools_available() -> bool:
    return all(shutil.which(tool) for tool in ("pdftotext", "pdftoppm", "identify", "convert"))


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _coordinate(element: ET.Element, name: str) -> float:
    try:
        return float(element.attrib[name])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid bbox {name} on {_local_name(element.tag)}") from exc


def _element_bbox(element: ET.Element, fallback: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    try:
        return (
            _coordinate(element, "xMin"),
            _coordinate(element, "yMin"),
            _coordinate(element, "xMax"),
            _coordinate(element, "yMax"),
        )
    except ValueError:
        return fallback


def _words(element: ET.Element) -> tuple[WordBox, ...]:
    words: list[WordBox] = []
    for child in element.iter():
        if _local_name(child.tag) != "word":
            continue
        text = "".join(child.itertext()).strip()
        if not text:
            continue
        try:
            words.append(
                WordBox(
                    _coordinate(child, "xMin"),
                    _coordinate(child, "yMin"),
                    _coordinate(child, "xMax"),
                    _coordinate(child, "yMax"),
                    text,
                )
            )
        except ValueError:
            continue
    return tuple(sorted(words, key=lambda word: (word.left, word.top)))


def parse_bbox_layout(value: str) -> list[PageLayout]:
    """Parse Poppler bbox-layout XML without flattening its geometry hierarchy."""
    root = ET.fromstring(value)
    layouts: list[PageLayout] = []
    page_elements = [element for element in root.iter() if _local_name(element.tag) == "page"]
    for page_number, page in enumerate(page_elements, start=1):
        try:
            width = float(page.attrib["width"])
            height = float(page.attrib["height"])
        except (KeyError, ValueError):
            continue
        blocks: list[TextBlock] = []
        for block in (element for element in page.iter() if _local_name(element.tag) == "block"):
            lines: list[TextLine] = []
            for line in (element for element in block if _local_name(element.tag) == "line"):
                words = _words(line)
                if not words:
                    continue
                fallback = (
                    min(word.left for word in words),
                    min(word.top for word in words),
                    max(word.right for word in words),
                    max(word.bottom for word in words),
                )
                left, top, right, bottom = _element_bbox(line, fallback)
                lines.append(
                    TextLine(
                        left,
                        top,
                        right,
                        bottom,
                        words,
                        " ".join(word.text for word in words),
                    )
                )
            if not lines:
                continue
            fallback = (
                min(line.left for line in lines),
                min(line.top for line in lines),
                max(line.right for line in lines),
                max(line.bottom for line in lines),
            )
            left, top, right, bottom = _element_bbox(block, fallback)
            blocks.append(
                TextBlock(
                    left,
                    top,
                    right,
                    bottom,
                    tuple(lines),
                    " ".join(line.text for line in lines),
                )
            )
        layouts.append(PageLayout(page_number, width, height, tuple(blocks)))
    return layouts


def extract_page_layouts(
    pdf_path: Path,
    work_dir: Path,
    *,
    max_pages: int | None = None,
    run: RunCommand = subprocess.run,
) -> list[PageLayout]:
    bbox_path = work_dir / "bbox.html"
    command = ["pdftotext", "-bbox-layout"]
    if max_pages is not None:
        command.extend(["-f", "1", "-l", str(max_pages)])
    command.extend([str(pdf_path), str(bbox_path)])
    run(command, check=True, capture_output=True, timeout=30)
    return parse_bbox_layout(bbox_path.read_text(encoding="utf-8", errors="ignore"))


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9]+", value.casefold())
        if token not in {"figure", "fig"}
    }


def _caption_suffix(value: str, number: int) -> str:
    return re.sub(
        rf"^\s*(?:Figure|Fig\.?)\s*{number}\s*[.:\-]?\s*",
        "",
        value,
        count=1,
        flags=re.IGNORECASE,
    )


def _token_similarity(first: str, second: str) -> float:
    left = _tokens(first)
    right = _tokens(second)
    if not left or not right:
        return 0.0
    return 2 * len(left & right) / (len(left) + len(right))


def find_figure_caption(layouts: list[PageLayout], record: Any) -> CaptionMatch | None:
    prefix = re.compile(rf"^\s*(?:Figure|Fig\.?)\s*{record.number}\b", re.IGNORECASE)
    candidates = [
        (page, block)
        for page in layouts
        for block in page.blocks
        if prefix.match(block.text)
    ]
    if not candidates:
        return None
    if not record.caption:
        strict = [
            (page, block)
            for page, block in candidates
            if re.match(rf"^\s*Figure\s*{record.number}\s*[.:]", block.text, re.IGNORECASE)
        ]
        if len(strict) != 1:
            return None
        page, block = strict[0]
        return CaptionMatch(page, block, 0.72, len(candidates), {"similarity": None})

    scored = sorted(
        [
            (
                _token_similarity(record.caption, _caption_suffix(block.text, record.number)),
                index,
                page,
                block,
            )
            for index, (page, block) in enumerate(candidates)
        ],
        key=lambda item: item[0],
    )
    best_score, _index, page, block = scored[-1]
    runner_up = scored[-2][0] if len(scored) > 1 else 0.0
    if best_score < 0.25 or (len(scored) > 1 and best_score - runner_up < 0.15):
        return None
    confidence = min(0.98, 0.68 + best_score * 0.28 + min(0.02, (best_score - runner_up) * 0.05))
    return CaptionMatch(
        page,
        block,
        confidence,
        len(candidates),
        {"similarity": round(best_score, 4), "runner_up_similarity": round(runner_up, 4)},
    )


def _overlap_area(block: TextBlock, left: float, top: float, right: float, bottom: float) -> float:
    width = max(0.0, min(right, block.right) - max(left, block.left))
    height = max(0.0, min(bottom, block.bottom) - max(top, block.top))
    return width * height


def _is_body_text_block(block: TextBlock, region_width: float) -> bool:
    if len(block.lines) < 3 or block.right - block.left < region_width * 0.55:
        return False
    word_counts = [len(_tokens(line.text)) for line in block.lines]
    if sum(word_counts) / len(word_counts) < 5:
        return False
    gaps = [
        following.top - preceding.bottom
        for preceding, following in zip(block.lines, block.lines[1:])
    ]
    return not gaps or sum(gap <= max(8.0, (preceding.bottom - preceding.top) * 1.2) for gap, preceding in zip(gaps, block.lines)) / len(gaps) >= 0.75


def _caption_prefix(value: str) -> bool:
    return bool(re.match(r"^\s*(?:Figure|Fig\.?|Table|Tab\.?)\s*\d+\b", value, re.IGNORECASE))


def plan_figure_crop(record: Any, page: PageLayout, caption: TextBlock) -> CropPlan:
    page_margin = page.width * 0.05
    if record.layout == "double-column":
        left, right = page_margin, page.width - page_margin
        layout_reason = "double-column"
    else:
        gutter = page.width * 0.04
        midpoint = page.width / 2
        if (caption.left + caption.right) / 2 < midpoint:
            left, right = page_margin, midpoint - gutter / 2
            layout_reason = "left-column"
        else:
            left, right = midpoint + gutter / 2, page.width - page_margin
            layout_reason = "right-column"

    bottom = max(0.0, caption.top - 6.0)
    initial_top = page.height * 0.06
    region_width = right - left
    body_blocks = [
        block
        for block in page.blocks
        if block.bottom <= bottom
        and _overlap_area(block, left, initial_top, right, bottom) > 0
        and _is_body_text_block(block, region_width)
    ]
    initial_area = max(1.0, region_width * max(1.0, bottom - initial_top))
    body_coverage = sum(
        _overlap_area(block, left, initial_top, right, bottom) for block in body_blocks
    ) / initial_area

    preceding_captions = [
        block
        for block in page.blocks
        if block is not caption
        and block.bottom < caption.top
        and _caption_prefix(block.text)
        and _overlap_area(block, left, initial_top, right, bottom) > 0
    ]
    top = initial_top
    if preceding_captions:
        top = max(top, max(block.bottom for block in preceding_captions) + 8.0)
    elif body_blocks and body_coverage <= 0.35:
        top = max(top, max(block.bottom for block in body_blocks) + 8.0)

    width = right - left
    height = bottom - top
    area_ratio = max(0.0, width * height) / max(1.0, page.width * page.height)
    aspect_ratio = width / max(1.0, height)
    reasons: list[str] = [layout_reason]
    accepted = True
    confidence = 0.86
    if body_coverage > 0.35:
        reasons.append("text-heavy")
        accepted = False
        confidence -= 0.45
    if area_ratio < 0.025 or width < 80 or height < 60:
        reasons.append("tiny-area")
        accepted = False
        confidence -= 0.35
    if aspect_ratio > 8.0 or aspect_ratio < 0.12:
        reasons.append("extreme-aspect-ratio")
        accepted = False
        confidence -= 0.3
    if preceding_captions:
        reasons.append("preceding-caption-boundary")

    diagnostics = {
        "body_text_coverage": round(body_coverage, 4),
        "area_ratio": round(area_ratio, 4),
        "aspect_ratio": round(aspect_ratio, 4),
        "body_block_count": len(body_blocks),
        "preceding_caption_count": len(preceding_captions),
    }
    return CropPlan(
        page.number,
        left,
        top,
        right,
        bottom,
        max(0.0, min(1.0, confidence)),
        accepted,
        tuple(reasons),
        diagnostics,
    )


def render_figure_crop(
    pdf_path: Path,
    destination: Path,
    plan: CropPlan,
    work_dir: Path,
    *,
    dpi: int = 180,
    run: RunCommand = subprocess.run,
) -> CropResult:
    if not plan.accepted:
        return CropResult(None, plan.confidence, False, plan.reasons, {**plan.diagnostics, "stage": "plan"})
    prefix = work_dir / "page"
    try:
        run(
            [
                "pdftocairo",
                "-png",
                "-singlefile",
                "-f",
                str(plan.page),
                "-l",
                str(plan.page),
                "-r",
                str(dpi),
                str(pdf_path),
                str(prefix),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        rendered = prefix.with_suffix(".png")
        if not rendered.is_file():
            raise RuntimeError("pdftocairo produced no page image")
        scale = dpi / 72.0
        geometry = (
            f"{max(1, round((plan.right - plan.left) * scale))}x"
            f"{max(1, round((plan.bottom - plan.top) * scale))}+"
            f"{max(0, round(plan.left * scale))}+{max(0, round(plan.top * scale))}"
        )
        temporary = work_dir / "figure.webp"
        run(
            [
                "convert",
                str(rendered),
                "-crop",
                geometry,
                "+repage",
                "-trim",
                "+repage",
                "-resize",
                "2400x2400>",
                "-strip",
                "-quality",
                "88",
                str(temporary),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise RuntimeError("figure crop produced no output")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.replace(destination)
    except (OSError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return CropResult(
            None,
            plan.confidence,
            False,
            (*plan.reasons, "render-failed"),
            {**plan.diagnostics, "stage": "render", "error": type(exc).__name__},
        )
    return CropResult(
        destination,
        plan.confidence,
        True,
        plan.reasons,
        {**plan.diagnostics, "stage": "complete"},
    )


def find_figure_one_caption(pdf_path: Path, work_dir: Path, *, max_pages: int = 5) -> FigureCaption | None:
    if not pdf_path.exists() or not _required_tools_available():
        return None
    try:
        layouts = extract_page_layouts(pdf_path, work_dir, max_pages=max_pages)
    except (ET.ParseError, ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    prefix = re.compile(r"^\s*(?:Figure|Fig\.?)\s*1\b", re.IGNORECASE)
    for page in layouts:
        for block in page.blocks:
            if prefix.match(block.text):
                return FigureCaption(
                    page.number,
                    block.left,
                    block.top,
                    block.right,
                    block.bottom,
                    page.width,
                    page.height,
                )
    return None


def _render_caption_page(pdf_path: Path, caption: FigureCaption, work_dir: Path, *, dpi: int) -> Path:
    prefix = work_dir / "page"
    _run(
        ["pdftoppm", "-f", str(caption.page), "-l", str(caption.page), "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        timeout=20,
    )
    rendered = work_dir / f"page-{caption.page:02d}.png"
    if rendered.exists():
        return rendered
    matches = sorted(work_dir.glob("page-*.png"))
    if not matches:
        raise RuntimeError(f"pdftoppm did not render {pdf_path}")
    return matches[0]


def _identify_size(path: Path) -> tuple[int, int]:
    output = subprocess.check_output(["identify", "-format", "%w %h", str(path)], text=True, timeout=10)
    width, height = output.strip().split()
    return int(width), int(height)


def write_pdf_window_trim_cover(
    pdf_path: Path,
    cover_path: Path,
    *,
    target_width: int = 400,
    dpi: int = 180,
) -> bool:
    if not _required_tools_available() or not pdf_path.exists():
        return False
    with tempfile.TemporaryDirectory(prefix="airesearch-figure-crop-") as temp_dir:
        work_dir = Path(temp_dir)
        caption = find_figure_one_caption(pdf_path, work_dir)
        if caption is None:
            return False
        try:
            rendered = _render_caption_page(pdf_path, caption, work_dir, dpi=dpi)
            rendered_width, rendered_height = _identify_size(rendered)
            scale_x = rendered_width / caption.page_width
            scale_y = rendered_height / caption.page_height
            left = round(caption.page_width * 0.075 * scale_x)
            right = round(caption.page_width * 0.925 * scale_x)
            caption_top = round(max(0, caption.y_min - 6) * scale_y)
            top = max(
                round(caption_top - caption.page_height * 0.52 * scale_y),
                round(caption.page_height * 0.06 * scale_y),
            )
            crop_width = max(1, right - left)
            crop_height = max(1, caption_top - top)
            geometry = f"{crop_width}x{crop_height}+{left}+{top}"
            cover_path.parent.mkdir(parents=True, exist_ok=True)
            _run(
                [
                    "convert",
                    str(rendered),
                    "-crop",
                    geometry,
                    "+repage",
                    "-trim",
                    "+repage",
                    "-resize",
                    f"{target_width}x>",
                    "-quality",
                    "90",
                    str(cover_path),
                ]
            )
        except (OSError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
    return cover_path.exists() and cover_path.stat().st_size > 0
