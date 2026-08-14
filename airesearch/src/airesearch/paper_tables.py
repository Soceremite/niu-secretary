from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from airesearch.figure_crop import (
    CaptionMatch,
    CropPlan,
    CropResult,
    PageLayout,
    TextBlock,
    extract_page_layouts,
    render_figure_crop,
)
from airesearch.paper_figures import (
    _balanced_command,
    _clean_latex_text,
    _command_values,
    _containing_headings,
    _heading_commands,
    _paragraphs_with_offsets,
    _referenced_labels,
    _remove_latex_comments,
)


RunCommand = Callable[..., Any]

TABLE_BEGIN_RE = re.compile(r"\\begin\s*\{(table\*?)\}(?:\s*\[[^\]]*\])?")
TABLE_REF_RE = re.compile(r"^\s*(?:Table|Tab\.?)\s*(\d+)\b", re.IGNORECASE)

MAIN_RESULT_TERMS = {
    "main": 24,
    "state-of-the-art": 28,
    "sota": 28,
    "benchmark": 24,
    "comparison": 22,
    "compare": 18,
    "result": 24,
    "results": 24,
    "open-loop": 28,
    "closed-loop": 28,
    "neuroncap": 24,
    "nuscenes": 22,
    "planning": 14,
    "score": 12,
    "collision": 12,
    "success": 12,
    "accuracy": 10,
}
ABLATION_TERMS = {"ablation": 18, "variant": 8, "retained": 8, "strategy": 8}
EFFICIENCY_TERMS = {"latency": 18, "inference": 10, "efficiency": 10}
IMPLEMENTATION_TERMS = {"implementation": 20, "hyperparameter": 20, "training": 8, "setting": 8}


@dataclass(frozen=True)
class TableEvidence:
    evidence_id: str
    kind: str
    text: str


@dataclass(frozen=True)
class TableRecord:
    table_id: str
    number: int
    label: str
    layout: str
    caption: str
    raw_latex: str
    section: str
    subsection: str
    role: str
    score: int
    caption_position: str
    evidence: tuple[TableEvidence, ...]


@dataclass(frozen=True)
class ResolvedTable:
    record: TableRecord
    path: Path
    source_reference: str
    extraction_method: str
    confidence: float
    content_sha256: str
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class _TableEnvironment:
    start: int
    end: int
    name: str
    body: str


@dataclass(frozen=True)
class _Paragraph:
    start: int
    text: str


def _table_environments(text: str) -> list[_TableEnvironment]:
    environments: list[_TableEnvironment] = []
    cursor = 0
    while match := TABLE_BEGIN_RE.search(text, cursor):
        name = match.group(1)
        end_match = re.search(rf"\\end\s*\{{{re.escape(name)}\}}", text[match.end() :])
        if end_match is None:
            cursor = match.end()
            continue
        body_end = match.end() + end_match.start()
        environment_end = match.end() + end_match.end()
        environments.append(
            _TableEnvironment(
                start=match.start(),
                end=environment_end,
                name=name,
                body=text[match.end() : body_end],
            )
        )
        cursor = environment_end
    return environments


def _mask_environments(text: str, environments: list[_TableEnvironment]) -> str:
    chars = list(text)
    for environment in environments:
        for index in range(environment.start, environment.end):
            if chars[index] != "\n":
                chars[index] = " "
    return "".join(chars)


def _table_text_for_score(record_text: str) -> str:
    cleaned = _clean_latex_text(record_text)
    return cleaned.casefold()


def _keyword_score(text: str, weights: dict[str, int]) -> int:
    return sum(weight for term, weight in weights.items() if term in text)


def _numeric_density_score(raw_latex: str) -> int:
    numbers = re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", raw_latex)
    rows = raw_latex.count("\\\\")
    return min(24, len(numbers) * 2 + rows)


def _table_role_and_score(*, caption: str, label: str, section: str, subsection: str, raw_latex: str) -> tuple[str, int]:
    caption_text = _table_text_for_score(" ".join((caption, label)))
    section_text = _table_text_for_score(" ".join((section, subsection)))
    context_text = " ".join((caption_text, section_text)).strip()
    body_text = _table_text_for_score(raw_latex[:4000])
    caption_main_score = _keyword_score(caption_text, MAIN_RESULT_TERMS)
    caption_ablation_score = _keyword_score(caption_text, ABLATION_TERMS)
    caption_efficiency_score = _keyword_score(caption_text, EFFICIENCY_TERMS)
    caption_implementation_score = _keyword_score(caption_text, IMPLEMENTATION_TERMS)
    section_main_score = min(18, _keyword_score(section_text, MAIN_RESULT_TERMS) // 2)
    section_ablation_score = min(12, _keyword_score(section_text, ABLATION_TERMS) // 2)
    section_efficiency_score = min(10, _keyword_score(section_text, EFFICIENCY_TERMS) // 2)
    main_score = caption_main_score + section_main_score
    ablation_score = caption_ablation_score + section_ablation_score
    efficiency_score = caption_efficiency_score + section_efficiency_score
    implementation_score = caption_implementation_score

    score = 10 + _numeric_density_score(raw_latex)
    score += main_score + ablation_score + efficiency_score
    score += min(18, _keyword_score(body_text, MAIN_RESULT_TERMS) // 2)
    implementation_penalty = implementation_score
    if implementation_penalty:
        score -= min(36, implementation_penalty)

    if implementation_score >= 20 and not any(
        term in caption_text
        for term in (
            "result",
            "results",
            "benchmark",
            "comparison",
            "open-loop",
            "closed-loop",
            "neuroncap",
            "nuscenes",
            "ablation",
            "latency",
        )
    ):
        role = "implementation"
    elif main_score >= 20:
        role = "experiments"
    elif ablation_score:
        role = "ablation"
    elif efficiency_score:
        role = "efficiency"
    else:
        role = "table"
    return role, max(0, score)


def _caption_offset(body: str) -> int:
    values = _command_values(body, "caption")
    return values[0][0] if values else -1


def _caption_position(body: str) -> str:
    caption_at = _caption_offset(body)
    if caption_at < 0:
        return "below"
    content_candidates = [
        offset
        for pattern in (
            r"\\begin\s*\{tabular\*?\}",
            r"\\begin\s*\{array\}",
            r"\\resizebox\b",
            r"\\includegraphics\b",
        )
        for offset in [match.start() for match in re.finditer(pattern, body)]
    ]
    if not content_candidates:
        return "below"
    return "above" if caption_at < min(content_candidates) else "below"


def _build_evidence(
    table_id: str,
    caption: str,
    label: str,
    paragraphs: list[_Paragraph],
) -> tuple[TableEvidence, ...]:
    evidence: list[TableEvidence] = []
    if caption:
        evidence.append(TableEvidence(f"{table_id}-caption", "caption", caption))
    reference_number = 0
    if label:
        for paragraph in paragraphs:
            if label not in _referenced_labels(paragraph.text):
                continue
            text = _clean_latex_text(paragraph.text)
            if not text:
                continue
            reference_number += 1
            evidence.append(TableEvidence(f"{table_id}-reference-{reference_number}", "reference", text))
    return tuple(evidence)


def parse_table_manifest(source_tex: Path) -> list[TableRecord]:
    text = _remove_latex_comments(source_tex.read_text(encoding="utf-8", errors="replace"))
    environments = _table_environments(text)
    headings = _heading_commands(text)
    paragraphs = _paragraphs_with_offsets(_mask_environments(text, environments))
    records: list[TableRecord] = []

    for number, environment in enumerate(environments, start=1):
        table_id = f"tab-{number}"
        caption = _clean_latex_text(_balanced_command(environment.body, "caption"))
        label = _balanced_command(environment.body, "label").strip()
        section, subsection = _containing_headings(headings, environment.start)
        role, score = _table_role_and_score(
            caption=caption,
            label=label,
            section=section,
            subsection=subsection,
            raw_latex=environment.body,
        )
        records.append(
            TableRecord(
                table_id=table_id,
                number=number,
                label=label,
                layout="double-column" if environment.name == "table*" else "single-column",
                caption=caption,
                raw_latex=environment.body.strip(),
                section=section,
                subsection=subsection,
                role=role,
                score=score,
                caption_position=_caption_position(environment.body),
                evidence=_build_evidence(table_id, caption, label, paragraphs),
            )
        )
    return records


def _table_number_from_caption(value: str) -> int | None:
    match = TABLE_REF_RE.match(value)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _pdf_caption_position(page: PageLayout, caption: TextBlock) -> str:
    above = [
        block
        for block in page.blocks
        if block is not caption
        and block.bottom < caption.top
        and abs(((block.left + block.right) / 2) - ((caption.left + caption.right) / 2)) < page.width * 0.4
    ]
    below = [
        block
        for block in page.blocks
        if block is not caption
        and block.top > caption.bottom
        and abs(((block.left + block.right) / 2) - ((caption.left + caption.right) / 2)) < page.width * 0.4
    ]
    previous_gap = caption.top - max((block.bottom for block in above), default=page.height)
    next_gap = min((block.top for block in below), default=page.height) - caption.bottom
    return "below" if previous_gap <= next_gap else "above"


def parse_pdf_table_manifest(pdf_path: Path, work_dir: Path, *, run: RunCommand = subprocess.run) -> list[TableRecord]:
    try:
        layouts = extract_page_layouts(pdf_path, work_dir, run=run)
    except Exception:
        return []
    records: list[TableRecord] = []
    seen: set[int] = set()
    for page in layouts:
        for block in page.blocks:
            number = _table_number_from_caption(block.text)
            if number is None or number in seen:
                continue
            caption = _clean_latex_text(_caption_suffix(block.text, number))
            layout = "double-column" if block.right - block.left > page.width * 0.6 else "single-column"
            role, score = _table_role_and_score(
                caption=caption,
                label="",
                section="",
                subsection="",
                raw_latex="",
            )
            table_id = f"tab-{number}"
            seen.add(number)
            evidence = (TableEvidence(f"{table_id}-caption", "caption", caption),) if caption else ()
            records.append(
                TableRecord(
                    table_id=table_id,
                    number=number,
                    label="",
                    layout=layout,
                    caption=caption,
                    raw_latex="",
                    section="",
                    subsection="",
                    role=role,
                    score=score,
                    caption_position=_pdf_caption_position(page, block),
                    evidence=evidence,
                )
            )
    return sorted(records, key=lambda record: record.number)


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9]+", value.casefold())
        if token not in {"table", "tab"}
    }


def _caption_suffix(value: str, number: int) -> str:
    return re.sub(
        rf"^\s*(?:Table|Tab\.?)\s*{number}\s*[.:\-]?\s*",
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


def find_table_caption(layouts: list[PageLayout], record: TableRecord) -> CaptionMatch | None:
    prefix = re.compile(rf"^\s*(?:Table|Tab\.?)\s*{record.number}\b", re.IGNORECASE)
    candidates = [
        (page, block)
        for page in layouts
        for block in page.blocks
        if prefix.match(block.text)
    ]
    if not candidates:
        return None
    if not record.caption:
        if len(candidates) != 1:
            return None
        page, block = candidates[0]
        return CaptionMatch(page, block, 0.7, len(candidates), {"similarity": None})

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
    if best_score < 0.2 or (len(scored) > 1 and best_score - runner_up < 0.12):
        return None
    confidence = min(0.97, 0.66 + best_score * 0.28 + min(0.03, (best_score - runner_up) * 0.08))
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


def _caption_prefix(value: str) -> bool:
    return bool(re.match(r"^\s*(?:Figure|Fig\.?|Table|Tab\.?)\s*\d+\b", value, re.IGNORECASE))


def _section_heading(value: str) -> bool:
    return bool(re.match(r"^\s*\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z0-9 ,:/\\-]{2,}$", value))


def _initial_region(record: TableRecord, page: PageLayout, caption: TextBlock) -> tuple[float, float, float, float, str]:
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

    if record.caption_position == "above":
        top = min(page.height * 0.9, caption.bottom + 6.0)
        bottom = page.height * 0.9
        following_boundaries = [
            block.top - 8.0
            for block in page.blocks
            if block is not caption
            and block.top > caption.bottom
            and (_caption_prefix(block.text) or _section_heading(block.text))
            and _overlap_area(block, left, top, right, bottom) > 0
        ]
        if following_boundaries:
            bottom = min(bottom, min(following_boundaries))
    else:
        top = page.height * 0.06
        bottom = max(0.0, caption.top - 6.0)
        preceding_boundaries = [
            block.bottom + 8.0
            for block in page.blocks
            if block is not caption
            and block.bottom < caption.top
            and _caption_prefix(block.text)
            and _overlap_area(block, left, top, right, bottom) > 0
        ]
        if preceding_boundaries:
            top = max(top, max(preceding_boundaries))
    return left, top, right, bottom, layout_reason


def plan_table_crop(record: TableRecord, page: PageLayout, caption: TextBlock) -> CropPlan:
    left, top, right, bottom, layout_reason = _initial_region(record, page, caption)
    content_blocks = [
        block
        for block in page.blocks
        if block is not caption
        and not _caption_prefix(block.text)
        and _overlap_area(block, left, top, right, bottom) > 0
    ]
    reasons: list[str] = [layout_reason, f"caption-{record.caption_position}"]
    accepted = True
    confidence = 0.84
    if not content_blocks:
        accepted = False
        confidence -= 0.5
        reasons.append("no-table-blocks")
    else:
        pad_x = 12.0
        pad_y = 8.0
        left = max(0.0, min(block.left for block in content_blocks) - pad_x)
        right = min(page.width, max(block.right for block in content_blocks) + pad_x)
        top = max(0.0, min(block.top for block in content_blocks) - pad_y)
        bottom = min(page.height, max(block.bottom for block in content_blocks) + pad_y)

    width = max(0.0, right - left)
    height = max(0.0, bottom - top)
    area_ratio = width * height / max(1.0, page.width * page.height)
    aspect_ratio = width / max(1.0, height)
    if width < 100 or height < 28 or area_ratio < 0.01:
        accepted = False
        confidence -= 0.35
        reasons.append("tiny-area")
    if aspect_ratio > 12.0 or aspect_ratio < 0.4:
        accepted = False
        confidence -= 0.2
        reasons.append("extreme-aspect-ratio")

    return CropPlan(
        page.number,
        left,
        top,
        right,
        bottom,
        max(0.0, min(1.0, confidence)),
        accepted,
        tuple(reasons),
        {
            "area_ratio": round(area_ratio, 4),
            "aspect_ratio": round(aspect_ratio, 4),
            "content_block_count": len(content_blocks),
            "caption_position": record.caption_position,
            "table_score": record.score,
        },
    )


def crop_pdf_table_fallback(
    record: TableRecord,
    pdf_path: Path,
    destination: Path,
    *,
    run: RunCommand = subprocess.run,
) -> CropResult:
    if not pdf_path.exists() or not pdf_path.is_file():
        return CropResult(None, 0.0, False, ("pdf-missing",), {"stage": "input", "pdf_path": str(pdf_path)})

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="paper-table-crop-", dir=destination.parent) as temp_dir:
        work_dir = Path(temp_dir)
        try:
            layouts = extract_page_layouts(pdf_path, work_dir, run=run)
        except Exception as exc:
            return CropResult(None, 0.0, False, ("layout-failed",), {"stage": "layout", "error": type(exc).__name__})

        match = find_table_caption(layouts, record)
        if match is None:
            return CropResult(
                None,
                0.0,
                False,
                ("caption-not-found",),
                {"stage": "caption", "table_number": record.number},
            )

        plan = plan_table_crop(record, match.page, match.block)
        if not plan.accepted:
            return CropResult(
                None,
                min(match.confidence, plan.confidence),
                False,
                plan.reasons,
                {
                    **plan.diagnostics,
                    "stage": "plan",
                    "caption_confidence": match.confidence,
                    "caption_diagnostics": match.diagnostics,
                },
            )

        result = render_figure_crop(pdf_path, destination, plan, work_dir, run=run)
        return CropResult(
            result.path,
            min(match.confidence, result.confidence),
            result.accepted,
            result.reasons,
            {
                **result.diagnostics,
                "caption_confidence": match.confidence,
                "caption_diagnostics": match.diagnostics,
            },
        )


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_destination(output_dir: Path, record: TableRecord) -> Path:
    return output_dir / f"table-{record.number:02d}.webp"


def _table_sort_key(record: TableRecord) -> tuple[int, int]:
    role_bonus = {
        "experiments": 40,
        "efficiency": 26,
        "ablation": 20,
        "table": 8,
        "implementation": -30,
    }.get(record.role, 0)
    return (-(record.score + role_bonus), record.number)


def resolve_paper_tables(
    *,
    source_tex: Path | None,
    pdf_path: Path | None,
    output_dir: Path,
    max_tables: int = 3,
    cropper: Callable[..., CropResult] | None = None,
) -> list[ResolvedTable]:
    if pdf_path is None or not pdf_path.exists() or not pdf_path.is_file():
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    cropper = cropper or crop_pdf_table_fallback
    if source_tex is not None and source_tex.exists() and source_tex.is_file():
        records = parse_table_manifest(source_tex)
    else:
        with tempfile.TemporaryDirectory(prefix="paper-table-manifest-", dir=output_dir) as temp_dir:
            records = parse_pdf_table_manifest(pdf_path, Path(temp_dir))
    records = sorted(records, key=_table_sort_key)
    resolved: list[ResolvedTable] = []
    for record in records[: max(0, max_tables)]:
        destination = _normalized_destination(output_dir, record)
        result = cropper(record, pdf_path, destination)
        if not getattr(result, "accepted", False) or getattr(result, "path", None) is None:
            continue
        path = Path(result.path)
        resolved.append(
            ResolvedTable(
                record=record,
                path=path,
                source_reference=record.label,
                extraction_method="pdf_table_crop",
                confidence=float(getattr(result, "confidence", 0.0) or 0.0),
                content_sha256=_file_fingerprint(path),
                diagnostics=tuple(getattr(result, "reasons", ()) or ()),
            )
        )
    return sorted(resolved, key=lambda table: _table_sort_key(table.record))
