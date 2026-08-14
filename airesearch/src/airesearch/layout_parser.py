from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import shutil
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.formula_ocr import (
    FormulaOCRConfig,
    FormulaOCRError,
    OpenAICompatibleFormulaOCRProvider,
    is_likely_formula,
)
from airesearch.table_reconstruction import reconstruct_table_from_words as _reconstruct_table_from_words


PARSER_NAME = "airesearch_layout"
PARSER_VERSION = "v2"
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MATH_TOKENS = ("=", "\\", "∑", "∫", "√", "≤", "≥", "±", "×", "arg", "log", "softmax", "loss")
CAPTION_RE = re.compile(r"^\s*((?:fig(?:ure)?\.?|table|图|表)\s*[\dIVXivx一二三四五六七八九十]+[.:：、\-\s].*)", re.I)
CAPTION_PREFIX_RE = re.compile(
    r"^\s*(?P<label>(?:(?i:fig(?:ure)?\.?|table)|图|表)\s*"
    r"[\dIVXivx一二三四五六七八九十]+(?:\s*\([a-z]\))?)\s*"
    r"(?P<body>[\s\S]*)$"
)
PAGE_NUMBER_RE = re.compile(r"^(?:page\s*)?\d{1,4}$", re.I)


@dataclass(frozen=True)
class LayoutParserOptions:
    output_dir: Path
    max_pages: int | None = None
    ocr_mode: str = "auto"
    ocr_languages: str = "eng+chi_sim"
    ocr_dpi: int = 220
    ocr_executable: str = "tesseract"
    ocr_min_text_chars: int = 60
    formula_ocr_mode: str = "off"
    formula_ocr_dpi: int = 260
    formula_ocr_min_confidence: float = 0.7


@dataclass(frozen=True)
class LayoutParseOutput:
    output_dir: Path
    markdown_files: list[Path]
    content_list_files: list[Path]
    structure_json_files: list[Path]
    debug_json_files: list[Path]
    summary_files: list[Path]
    assets: list[Path]


def _build_formula_ocr_provider() -> OpenAICompatibleFormulaOCRProvider | None:
    config = FormulaOCRConfig.from_env()
    return OpenAICompatibleFormulaOCRProvider(config) if config.configured else None


def _formula_crop_png(page: Any, bbox: list[float], *, dpi: int) -> bytes:
    if len(bbox) < 4:
        return b""
    page_rect = page.rect
    padding_x = float(page_rect.width) * 0.025
    padding_y = float(page_rect.height) * 0.015
    left = max(0.0, float(bbox[0]) - padding_x)
    top = max(0.0, float(bbox[1]) - padding_y)
    right = min(float(page_rect.width), float(bbox[2]) + padding_x)
    bottom = min(float(page_rect.height), float(bbox[3]) + padding_y)
    if right - left < 8 or bottom - top < 8:
        return b""
    clip = page_rect.__class__(left, top, right, bottom)
    return page.get_pixmap(dpi=dpi, clip=clip, alpha=False).tobytes("png")


def _page_text_profile(page_dict: dict[str, Any], *, page_width: float, page_height: float) -> dict[str, Any]:
    text_chars = 0
    text_blocks = 0
    image_blocks = 0
    image_area = 0.0
    page_area = max(1.0, page_width * page_height)
    for block in page_dict.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        raw_type = int(block.get("type") or 0)
        if raw_type == 0:
            text = _block_text(block)
            if text:
                text_blocks += 1
                text_chars += len(re.sub(r"\s+", "", text))
        elif raw_type == 1:
            image_blocks += 1
            bbox = block.get("bbox") if isinstance(block.get("bbox"), (list, tuple)) else []
            if len(bbox) >= 4:
                image_area += max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))
    image_area_ratio = min(1.0, image_area / page_area)
    if text_chars >= 60:
        page_type = "digital"
    elif text_chars < 20 and image_area_ratio >= 0.5:
        page_type = "scanned"
    elif image_area_ratio >= 0.3:
        page_type = "mixed"
    else:
        page_type = "digital"
    return {
        "page_type": page_type,
        "text_chars": text_chars,
        "text_blocks": text_blocks,
        "image_blocks": image_blocks,
        "image_area_ratio": round(image_area_ratio, 4),
    }


def _ocr_page_with_tesseract(
    page: Any,
    *,
    page_index: int,
    languages: str,
    dpi: int,
    executable: str,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    scale = max(1.0, float(dpi) / 72.0)
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    image_bytes = pixmap.tobytes("png")
    try:
        completed = subprocess.run(
            [executable, "stdin", "stdout", "-l", languages, "--dpi", str(dpi), "tsv"],
            input=image_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=90,
        )
    except FileNotFoundError:
        return [], {"status": "unavailable", "engine": "tesseract", "error": f"executable not found: {executable}"}
    except subprocess.TimeoutExpired:
        return [], {"status": "failed", "engine": "tesseract", "error": f"OCR timeout on page {page_index + 1}"}
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()[:500]
        return [], {"status": "failed", "engine": "tesseract", "error": error or f"exit code {completed.returncode}"}

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    reader = csv.DictReader(io.StringIO(completed.stdout.decode("utf-8", errors="replace")), delimiter="\t")
    for row in reader:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        try:
            confidence = float(row.get("conf") or -1)
            left = float(row.get("left") or 0) / scale
            top = float(row.get("top") or 0) / scale
            width = float(row.get("width") or 0) / scale
            height = float(row.get("height") or 0) / scale
        except (TypeError, ValueError):
            continue
        if confidence < 0 or width <= 0 or height <= 0:
            continue
        key = (str(row.get("block_num") or "0"), str(row.get("par_num") or "0"), str(row.get("line_num") or "0"))
        groups.setdefault(key, []).append(
            {"text": text, "confidence": confidence / 100.0, "bbox": [left, top, left + width, top + height]}
        )

    blocks: list[dict[str, Any]] = []
    for words in groups.values():
        bbox = [
            min(word["bbox"][0] for word in words),
            min(word["bbox"][1] for word in words),
            max(word["bbox"][2] for word in words),
            max(word["bbox"][3] for word in words),
        ]
        blocks.append(
            {
                "bbox": bbox,
                "text": " ".join(word["text"] for word in words),
                "confidence": sum(float(word["confidence"]) for word in words) / len(words),
            }
        )
    return blocks, {"status": "completed", "engine": "tesseract", "error": ""}


def _safe_stem(path: Path) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_.-]+", "-", path.stem).strip("-")
    return stem or "paper"


def _span_text(line: dict[str, Any]) -> str:
    spans = line.get("spans") if isinstance(line.get("spans"), list) else []
    return "".join(str(span.get("text") or "") for span in spans).strip()


def _block_text(block: dict[str, Any]) -> str:
    lines = block.get("lines") if isinstance(block.get("lines"), list) else []
    return "\n".join(text for line in lines if (text := _span_text(line))).strip()


def _normalized_layout_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _span_sizes(block: dict[str, Any]) -> list[float]:
    sizes: list[float] = []
    for line in block.get("lines") or []:
        if not isinstance(line, dict):
            continue
        for span in line.get("spans") or []:
            if isinstance(span, dict):
                try:
                    sizes.append(float(span.get("size") or 0))
                except (TypeError, ValueError):
                    pass
    return sizes


def _looks_like_table(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    multi_column = 0
    for line in lines:
        if "\t" in line or len(re.split(r"\s{2,}", line)) >= 3:
            multi_column += 1
    return multi_column >= 2 or str(lines[0]).lower().startswith("table ")


def _looks_like_equation(text: str) -> bool:
    return is_likely_formula(text)


def _caption_kind(text: str) -> str:
    stripped = text.strip()
    match = CAPTION_PREFIX_RE.match(stripped)
    if match is None:
        return ""
    body = str(match.group("body") or "")
    if not body:
        return ""
    # A real caption normally starts with punctuation or a title-cased label.
    # This rejects prose such as "Figure 2 presents ..." while preserving
    # captions like "Figure 2: Overview ..." and "Figure 2 Overview ...".
    first = body[0]
    if first not in ".:：、-" and not first.isupper() and not ("\u3400" <= first <= "\u9fff"):
        return ""
    lowered = stripped.lower()
    if lowered.startswith(("table", "表")):
        return "table"
    return "figure"


def _parse_table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "\t" in stripped:
            cells = [cell.strip() for cell in stripped.split("\t")]
        else:
            cells = [cell.strip() for cell in re.split(r"\s{2,}", stripped)]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 2:
            rows.append(cells)
    if len(rows) < 2:
        return []
    return rows


def _normalize_table_rows(rows: list[list[str]]) -> list[list[str]]:
    if not rows:
        return []
    width = max(len(row) for row in rows)
    if width < 2:
        return []
    return [row + [""] * (width - len(row)) for row in rows]


def _fallback_table_cells(rows: list[list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "row": row_index,
            "column": column_index,
            "row_span": 1,
            "column_span": 1,
            "bbox": [],
            "text": str(value),
            "confidence": 0.58,
        }
        for row_index, row in enumerate(rows)
        for column_index, value in enumerate(row)
        if str(value).strip()
    ]


def _escape_markdown_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _table_to_markdown(
    rows: list[list[str]],
    *,
    header_row_count: int = 1,
    cells: list[dict[str, Any]] | None = None,
) -> str:
    normalized = _normalize_table_rows(rows)
    if len(normalized) < 2:
        return ""
    header_count = max(1, min(int(header_row_count or 1), len(normalized) - 1))
    header_parts: list[list[str]] = [[] for _cell in normalized[0]]
    if cells:
        for cell in cells:
            row_index = int(cell.get("row") or 0)
            if row_index >= header_count:
                continue
            column = int(cell.get("column") or 0)
            span = max(1, int(cell.get("column_span") or 1))
            value = str(cell.get("text") or "").strip()
            for target in range(column, min(len(header_parts), column + span)):
                if value and value not in header_parts[target]:
                    header_parts[target].append(value)
    else:
        for row in normalized[:header_count]:
            for column, value in enumerate(row):
                if value and value not in header_parts[column]:
                    header_parts[column].append(value)
    header = [" / ".join(parts) for parts in header_parts]
    body = normalized[header_count:]
    lines = [
        "| " + " | ".join(_escape_markdown_cell(cell) for cell in header) + " |",
        "| " + " | ".join("---" for _cell in header) + " |",
    ]
    lines.extend("| " + " | ".join(_escape_markdown_cell(cell) for cell in row) + " |" for row in body)
    return "\n".join(lines)


def _table_to_html(
    rows: list[list[str]],
    *,
    header_row_count: int = 1,
    cells: list[dict[str, Any]] | None = None,
) -> str:
    normalized = _normalize_table_rows(rows)
    if len(normalized) < 2:
        return ""
    header_count = max(1, min(int(header_row_count or 1), len(normalized) - 1))
    cell_map = {
        (int(cell.get("row") or 0), int(cell.get("column") or 0)): cell
        for cell in (cells or [])
    }

    def render_row(row_index: int) -> str:
        rendered: list[str] = []
        column = 0
        while column < len(normalized[row_index]):
            cell = cell_map.get((row_index, column))
            value = str((cell.get("text") or "") if cell else (normalized[row_index][column] or "")).strip()
            span = max(1, int(cell.get("column_span") or 1)) if cell else 1
            tag = "th" if row_index < header_count else "td"
            span_attribute = f' colspan="{span}"' if span > 1 else ""
            rendered.append(f"<{tag}{span_attribute}>{html.escape(value)}</{tag}>")
            column += span
        return "<tr>" + "".join(rendered) + "</tr>"

    head_rows = "".join(render_row(index) for index in range(header_count))
    body_rows = "".join(render_row(index) for index in range(header_count, len(normalized)))
    return f"<table><thead>{head_rows}</thead><tbody>{body_rows}</tbody></table>"


def _geometry_table_metadata(result: dict[str, Any]) -> dict[str, Any]:
    if not result:
        return {}
    return {
        "table_rows": result.get("table_rows") or [],
        "table_cells": result.get("table_cells") or [],
        "row_count": int(result.get("row_count") or 0),
        "column_count": int(result.get("column_count") or 0),
        "table_header_row_count": int(result.get("header_row_count") or 1),
        "table_column_anchors": result.get("column_anchors") or [],
        "table_column_boundaries": result.get("column_boundaries") or [],
        "table_has_spanning_cells": bool(result.get("has_spanning_cells")),
        "table_reconstruction_method": str(result.get("reconstruction_method") or "word_geometry_v2"),
        "table_reconstruction_confidence": round(float(result.get("reconstruction_confidence") or 0), 4),
        "table_reconstruction_reasons": result.get("reconstruction_reasons") or [],
    }


def _bbox_overlap_ratio(inner_bbox: Any, outer_bbox: Any) -> float:
    inner = [float(value) for value in inner_bbox[:4]] if isinstance(inner_bbox, (list, tuple)) and len(inner_bbox) >= 4 else []
    outer = [float(value) for value in outer_bbox[:4]] if isinstance(outer_bbox, (list, tuple)) and len(outer_bbox) >= 4 else []
    if not inner or not outer:
        return 0.0
    intersection_width = max(0.0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    intersection_height = max(0.0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    inner_area = max(1.0, (inner[2] - inner[0]) * (inner[3] - inner[1]))
    return intersection_width * intersection_height / inner_area


def _native_table_regions(page: Any, page_words: list[Any]) -> list[dict[str, Any]]:
    if not hasattr(page, "find_tables"):
        return []
    try:
        import fitz

        version = tuple(int(value) for value in re.findall(r"\d+", str(getattr(fitz, "__version__", "0.0")))[:3])
    except Exception:
        return []
    if version < (1, 27, 0):
        return []
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            finder = page.find_tables()
    except Exception:
        return []

    regions: list[dict[str, Any]] = []
    for table in getattr(finder, "tables", []) or []:
        bbox = [float(value) for value in getattr(table, "bbox", [])[:4]]
        if len(bbox) < 4:
            continue
        geometry = _reconstruct_table_from_words(page_words, bbox)
        if not geometry:
            continue
        try:
            extracted = table.extract()
        except Exception:
            extracted = []
        normalized_rows = [
            [str(value or "").strip() for value in row]
            for row in extracted
            if isinstance(row, (list, tuple))
        ]
        normalized_rows = _normalize_table_rows(normalized_rows)
        if (
            len(normalized_rows) >= 2
            and len(normalized_rows) == int(geometry.get("row_count") or 0)
            and len(normalized_rows[0]) == int(geometry.get("column_count") or 0)
        ):
            geometry["table_rows"] = normalized_rows
            geometry["row_count"] = len(normalized_rows)
            text_by_position = {
                (row_index, column_index): value
                for row_index, row in enumerate(normalized_rows)
                for column_index, value in enumerate(row)
                if value
            }
            for cell in geometry.get("table_cells") or []:
                value = text_by_position.get((int(cell.get("row") or 0), int(cell.get("column") or 0)))
                if value:
                    cell["text"] = value
        geometry["reconstruction_method"] = "pymupdf_table_lines"
        geometry["reconstruction_confidence"] = max(0.93, float(geometry.get("reconstruction_confidence") or 0))
        reasons = list(geometry.get("reconstruction_reasons") or [])
        if "ruled-table-boundaries" not in reasons:
            reasons.append("ruled-table-boundaries")
        geometry["reconstruction_reasons"] = reasons
        regions.append({"bbox": bbox, "geometry": geometry})
    return regions


def _table_geometry_is_coherent(geometry: dict[str, Any]) -> bool:
    rows = geometry.get("table_rows") if isinstance(geometry.get("table_rows"), list) else []
    column_count = int(geometry.get("column_count") or 0)
    if len(rows) < 3 or column_count < 2 or column_count > 32:
        return False
    populated = [sum(bool(str(value).strip()) for value in row) for row in rows if isinstance(row, list)]
    collapsed_prose_rows = sum(
        1
        for row in rows
        if isinstance(row, list)
        and row
        and len(re.findall(r"\b[A-Za-z]{2,}\b", str(row[0]))) >= 5
        and sum(bool(str(value).strip()) for value in row[1:]) <= 1
    )
    if collapsed_prose_rows >= max(2, (len(rows) + 1) // 2):
        return False
    stable_rows = sum(value >= max(2, min(column_count, 4)) for value in populated)
    return stable_rows / max(1, len(populated)) >= 0.5


def _horizontal_table_rules(page: Any) -> list[dict[str, float]]:
    page_width = float(page.rect.width)
    rules: list[dict[str, float]] = []
    try:
        drawings = page.get_drawings()
    except Exception:
        return []
    for drawing in drawings:
        stroke = float(drawing.get("width") or 0)
        for item in drawing.get("items") or []:
            if not item or item[0] != "l":
                continue
            start, end = item[1], item[2]
            if abs(float(start.y) - float(end.y)) > 1.2:
                continue
            x0, x1 = sorted((float(start.x), float(end.x)))
            if x1 - x0 < max(70.0, page_width * 0.11):
                continue
            rules.append(
                {"x0": x0, "x1": x1, "y": (float(start.y) + float(end.y)) / 2, "stroke": stroke}
            )
    return rules


def _has_vertical_table_grid(page: Any, bbox: list[float]) -> bool:
    verticals = 0
    try:
        drawings = page.get_drawings()
    except Exception:
        return False
    for drawing in drawings:
        for item in drawing.get("items") or []:
            if not item or item[0] != "l":
                continue
            start, end = item[1], item[2]
            if abs(float(start.x) - float(end.x)) > 1.2:
                continue
            x = (float(start.x) + float(end.x)) / 2
            y0, y1 = sorted((float(start.y), float(end.y)))
            overlap = max(0.0, min(y1, bbox[3]) - max(y0, bbox[1]))
            if bbox[0] - 2 <= x <= bbox[2] + 2 and overlap >= (bbox[3] - bbox[1]) * 0.72:
                verticals += 1
    return verticals >= 2


def _booktabs_table_regions(page: Any, page_words: list[Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for rule in sorted(_horizontal_table_rules(page), key=lambda item: (item["x0"], item["x1"], item["y"])):
        group = next(
            (
                item
                for item in groups
                if abs(float(item["x0"]) - rule["x0"]) <= 3.0
                and abs(float(item["x1"]) - rule["x1"]) <= 3.0
            ),
            None,
        )
        if group is None:
            group = {"x0": rule["x0"], "x1": rule["x1"], "rules": []}
            groups.append(group)
        group["rules"].append(rule)
        count = len(group["rules"])
        group["x0"] = sum(item["x0"] for item in group["rules"]) / count
        group["x1"] = sum(item["x1"] for item in group["rules"]) / count

    candidate_bboxes: list[dict[str, Any]] = []

    def add_candidate(
        group_index: int,
        group: dict[str, Any],
        top: float,
        bottom: float,
        *,
        fallback: bool = False,
    ) -> None:
        max_table_height = max(360.0, float(page.rect.height) * 0.85)
        if not 20.0 <= bottom - top <= max_table_height:
            return
        bbox = [float(group["x0"]) - 2.0, top - 1.0, float(group["x1"]) + 2.0, bottom + 1.0]
        if not any(
            item["group_index"] == group_index
            and all(abs(left - right) <= 1.0 for left, right in zip(bbox, item["bbox"]))
            for item in candidate_bboxes
        ):
            candidate_bboxes.append(
                {"bbox": bbox, "group_index": group_index, "fallback": fallback}
            )

    for group_index, group in enumerate(groups):
        unique_rules: list[dict[str, float]] = []
        for rule in sorted(group["rules"], key=lambda item: item["y"]):
            if unique_rules and abs(unique_rules[-1]["y"] - rule["y"]) <= 1.2:
                if rule["stroke"] > unique_rules[-1]["stroke"]:
                    unique_rules[-1] = rule
            else:
                unique_rules.append(rule)
        if len(unique_rules) < 3:
            continue
        max_stroke = max(rule["stroke"] for rule in unique_rules)
        min_stroke = min(rule["stroke"] for rule in unique_rules)
        if max_stroke > max(0.01, min_stroke) * 1.2:
            outer_indices = [
                index for index, rule in enumerate(unique_rules) if rule["stroke"] >= max_stroke * 0.78
            ]
            pairs = [
                (start, end)
                for start, end in zip(outer_indices, outer_indices[1:])
                if end - start >= 2
            ]
        else:
            pairs = [(0, len(unique_rules) - 1)]
        for start, end in pairs:
            add_candidate(group_index, group, unique_rules[start]["y"], unique_rules[end]["y"])

        # Stacked subtables often share a middle rule and alternate outer/header rules.
        # Keep these candidates only when the enclosing geometry later proves incoherent.
        if len(unique_rules) >= 5:
            for start in range(0, len(unique_rules) - 2, 2):
                add_candidate(
                    group_index,
                    group,
                    unique_rules[start]["y"],
                    unique_rules[start + 2]["y"],
                    fallback=True,
                )

    regions: list[dict[str, Any]] = []
    coherent_primary_groups: set[int] = set()
    for candidate in sorted(candidate_bboxes, key=lambda item: bool(item["fallback"])):
        bbox = candidate["bbox"]
        group_index = int(candidate["group_index"])
        if candidate["fallback"] and group_index in coherent_primary_groups:
            continue
        if _has_vertical_table_grid(page, bbox):
            continue
        geometry = _reconstruct_table_from_words(page_words, bbox)
        if not geometry or not _table_geometry_is_coherent(geometry):
            continue
        if not candidate["fallback"]:
            coherent_primary_groups.add(group_index)
        geometry["reconstruction_method"] = "booktabs_geometry_v1"
        geometry["reconstruction_confidence"] = max(
            0.9, float(geometry.get("reconstruction_confidence") or 0)
        )
        reasons = list(geometry.get("reconstruction_reasons") or [])
        if "booktabs-horizontal-rules" not in reasons:
            reasons.append("booktabs-horizontal-rules")
        geometry["reconstruction_reasons"] = reasons
        regions.append({"bbox": bbox, "geometry": geometry})

    # A complete coherent table takes precedence over fragments inferred from its
    # internal rules. Disjoint stacked subtables remain separate.
    regions.sort(
        key=lambda item: (item["bbox"][2] - item["bbox"][0]) * (item["bbox"][3] - item["bbox"][1]),
        reverse=True,
    )
    complete_regions: list[dict[str, Any]] = []
    for region in regions:
        if any(_bbox_overlap_ratio(region["bbox"], complete["bbox"]) >= 0.96 for complete in complete_regions):
            continue
        complete_regions.append(region)
    return complete_regions


def _table_regions_overlap(left: list[float], right: list[float]) -> bool:
    horizontal = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    vertical = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    min_width = max(1.0, min(left[2] - left[0], right[2] - right[0]))
    min_height = max(1.0, min(left[3] - left[1], right[3] - right[1]))
    return horizontal / min_width >= 0.75 and vertical / min_height >= 0.25


def _table_regions(page: Any, page_words: list[Any]) -> list[dict[str, Any]]:
    booktabs = _booktabs_table_regions(page, page_words)
    native = _native_table_regions(page, page_words)
    regions = list(booktabs)
    for native_region in native:
        if not _table_geometry_is_coherent(native_region["geometry"]):
            continue
        if any(_table_regions_overlap(native_region["bbox"], region["bbox"]) for region in booktabs):
            continue
        if any(_bbox_overlap_ratio(native_region["bbox"], region["bbox"]) >= 0.72 for region in booktabs):
            continue
        native_area = max(1.0, (native_region["bbox"][2] - native_region["bbox"][0]) * (native_region["bbox"][3] - native_region["bbox"][1]))
        if any(
            _bbox_overlap_ratio(region["bbox"], native_region["bbox"]) >= 0.9
            and native_area
            > max(1.0, (region["bbox"][2] - region["bbox"][0]) * (region["bbox"][3] - region["bbox"][1]))
            * 2.5
            for region in booktabs
        ):
            continue
        regions.append(native_region)
    return sorted(regions, key=lambda item: (float(item["bbox"][1]), float(item["bbox"][0])))


def _equation_role(text: str) -> str:
    lowered = text.lower()
    if "loss" in lowered or "log" in lowered:
        return "loss"
    if "attention" in lowered or "softmax" in lowered:
        return "attention"
    if "arg" in lowered or "min" in lowered or "max" in lowered:
        return "optimization"
    return "math"


def _classify_text_block(text: str, block: dict[str, Any], *, page_height: float) -> str:
    stripped = text.strip()
    if not stripped:
        return "empty"
    if _looks_like_table(stripped):
        return "table"
    if _looks_like_equation(stripped):
        return "interline_equation"
    sizes = _span_sizes(block)
    avg_size = sum(sizes) / len(sizes) if sizes else 0
    line_count = len([line for line in stripped.splitlines() if line.strip()])
    bbox = block.get("bbox") if isinstance(block.get("bbox"), (list, tuple)) else [0, 0, 0, 0]
    top = float(bbox[1] or 0) if len(bbox) > 1 else 0.0
    if line_count <= 3 and len(stripped) <= 220 and (avg_size >= 13 or (top < page_height * 0.1 and len(stripped) <= 120)):
        return "title"
    if stripped.startswith(("-", "•")) or re.match(r"^\d+[\.)]\s+", stripped):
        return "list"
    return "text"


def _block_role(text: str, bbox: list[float], *, page_width: float, page_height: float) -> str:
    stripped = text.strip()
    normalized = _normalized_layout_text(stripped)
    if normalized and PAGE_NUMBER_RE.match(normalized):
        return "page_number"
    if len(bbox) >= 4:
        top = float(bbox[1])
        bottom = float(bbox[3])
        height = max(0.0, bottom - top)
        width = max(0.0, float(bbox[2]) - float(bbox[0]))
        if top <= page_height * 0.105 and height <= page_height * 0.06 and len(stripped) <= 180:
            return "header"
        if bottom >= page_height * 0.895 and height <= page_height * 0.065 and len(stripped) <= 200:
            return "footer"
        if width >= page_width * 0.88 and height <= page_height * 0.035 and len(stripped) <= 180:
            if top <= page_height * 0.1:
                return "header"
            if bottom >= page_height * 0.9:
                return "footer"
    return "body"


def _repeated_margin_texts(raw_pages: list[dict[str, Any]], *, min_pages: int = 2) -> set[str]:
    counts: dict[str, int] = {}
    for page in raw_pages:
        seen_on_page: set[str] = set()
        for block in page.get("blocks") or []:
            if str(block.get("type") or "") not in {"text", "title"}:
                continue
            role = str(block.get("metadata", {}).get("role") or "")
            if role not in {"header", "footer", "page_number"}:
                continue
            normalized = _normalized_layout_text(str(block.get("text") or ""))
            if not normalized:
                continue
            seen_on_page.add(normalized)
        for normalized in seen_on_page:
            counts[normalized] = counts.get(normalized, 0) + 1
    threshold = max(min_pages, min(3, len(raw_pages)))
    return {text for text, count in counts.items() if count >= threshold}


def _reading_sort_key(block: dict[str, Any], *, page_width: float) -> tuple[int, float, float, float]:
    bbox = block.get("bbox") if isinstance(block.get("bbox"), list) else [0, 0, 0, 0]
    left = float(bbox[0] or 0) if len(bbox) > 0 else 0.0
    top = float(bbox[1] or 0) if len(bbox) > 1 else 0.0
    bottom = float(bbox[3] or top) if len(bbox) > 3 else top
    center_x = (left + (float(bbox[2] or left) if len(bbox) > 2 else left)) / 2
    column = 0
    if center_x > page_width * 0.55:
        column = 1
    return (column, top, bottom, left)


def _block_bbox(block: dict[str, Any]) -> list[float]:
    bbox = block.get("bbox") if isinstance(block.get("bbox"), list) else []
    if len(bbox) < 4:
        return []
    try:
        return [float(value) for value in bbox[:4]]
    except (TypeError, ValueError):
        return []


def _reading_region_for_bbox(bbox: list[float], *, page_width: float) -> tuple[str, int | None]:
    if len(bbox) < 4 or page_width <= 0:
        return "unknown", None
    left, _top, right, _bottom = bbox
    width = max(0.0, right - left)
    center_x = (left + right) / 2.0
    if width >= page_width * 0.58 or (page_width * 0.32 <= left and right <= page_width * 0.68 and width >= page_width * 0.24):
        return "full_width", None
    if center_x <= page_width * 0.53:
        return "left_column", 0
    return "right_column", 1


def _group_bbox(blocks: list[dict[str, Any]]) -> list[float]:
    bboxes = [_block_bbox(block) for block in blocks]
    bboxes = [bbox for bbox in bboxes if len(bbox) >= 4]
    if not bboxes:
        return []
    return [
        min(bbox[0] for bbox in bboxes),
        min(bbox[1] for bbox in bboxes),
        max(bbox[2] for bbox in bboxes),
        max(bbox[3] for bbox in bboxes),
    ]


def _visual_caption_groups(page_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_original_index = {
        int(block.get("block_index") or 0): block
        for block in page_blocks
    }
    assigned: set[int] = set()
    groups: list[dict[str, Any]] = []

    for block in page_blocks:
        block_id = id(block)
        if block_id in assigned:
            continue
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        block_type = str(block.get("type") or "")
        caption_index = metadata.get("caption_block_index")
        if block_type in {"image", "chart", "table"} and caption_index is not None:
            try:
                caption = by_original_index.get(int(caption_index))
            except (TypeError, ValueError):
                caption = None
            if caption is not None and id(caption) not in assigned:
                members = sorted([block, caption], key=lambda item: (_block_bbox(item)[1] if _block_bbox(item) else 0.0))
                groups.append({"members": members, "kind": "caption_pair", "bbox": _group_bbox(members)})
                assigned.add(block_id)
                assigned.add(id(caption))
                continue
    for block in page_blocks:
        block_id = id(block)
        if block_id in assigned:
            continue
        groups.append({"members": [block], "kind": "single", "bbox": _block_bbox(block)})
        assigned.add(block_id)
    return groups


def _order_reading_segment(groups: list[dict[str, Any]], *, page_width: float) -> list[dict[str, Any]]:
    if len(groups) <= 1:
        return groups
    left = []
    right = []
    other = []
    for group in groups:
        region, column = _reading_region_for_bbox(group.get("bbox") or [], page_width=page_width)
        if column == 0:
            left.append(group)
        elif column == 1:
            right.append(group)
        else:
            other.append(group)
        group["region"] = region
        group["column"] = column
    if len(left) >= 1 and len(right) >= 1:
        return [
            *sorted(left, key=lambda item: ((item.get("bbox") or [0, 0, 0, 0])[1], (item.get("bbox") or [0, 0, 0, 0])[0])),
            *sorted(right, key=lambda item: ((item.get("bbox") or [0, 0, 0, 0])[1], (item.get("bbox") or [0, 0, 0, 0])[0])),
            *sorted(other, key=lambda item: ((item.get("bbox") or [0, 0, 0, 0])[1], (item.get("bbox") or [0, 0, 0, 0])[0])),
        ]
    return sorted(groups, key=lambda item: ((item.get("bbox") or [0, 0, 0, 0])[1], (item.get("bbox") or [0, 0, 0, 0])[0]))


def _apply_reading_order(
    page_blocks: list[dict[str, Any]],
    *,
    page_width: float,
    page_height: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups = _visual_caption_groups(page_blocks)
    for group in groups:
        region, column = _reading_region_for_bbox(group.get("bbox") or [], page_width=page_width)
        group["region"] = region
        group["column"] = column

    full_width_groups = sorted(
        [group for group in groups if group.get("region") == "full_width"],
        key=lambda item: ((item.get("bbox") or [0, 0, 0, 0])[1], (item.get("bbox") or [0, 0, 0, 0])[0]),
    )
    body_groups = [group for group in groups if group.get("region") != "full_width"]
    ordered_groups: list[dict[str, Any]] = []
    cursor_top = 0.0
    for full_group in full_width_groups:
        full_bbox = full_group.get("bbox") or []
        full_top = float(full_bbox[1]) if len(full_bbox) >= 4 else cursor_top
        segment = [
            group
            for group in body_groups
            if cursor_top <= float((group.get("bbox") or [0, 0, 0, 0])[1]) < full_top
        ]
        ordered_groups.extend(_order_reading_segment(segment, page_width=page_width))
        ordered_groups.append(full_group)
        if len(full_bbox) >= 4:
            cursor_top = max(cursor_top, float(full_bbox[3]))
    trailing = [
        group
        for group in body_groups
        if float((group.get("bbox") or [0, 0, 0, 0])[1]) >= cursor_top
    ]
    ordered_groups.extend(_order_reading_segment(trailing, page_width=page_width))

    seen_groups: set[int] = set()
    deduped_groups: list[dict[str, Any]] = []
    for group in ordered_groups:
        group_id = id(group)
        if group_id in seen_groups:
            continue
        seen_groups.add(group_id)
        deduped_groups.append(group)
    for group in groups:
        if id(group) not in seen_groups:
            deduped_groups.append(group)

    final_blocks: list[dict[str, Any]] = []
    caption_pairs = 0
    cross_column_blocks = 0
    low_confidence_blocks = 0
    confidence_total = 0.0
    left_count = 0
    right_count = 0
    for group in deduped_groups:
        region = str(group.get("region") or "unknown")
        if region == "left_column":
            left_count += 1
        elif region == "right_column":
            right_count += 1
        elif region == "full_width":
            cross_column_blocks += 1
        if group.get("kind") == "caption_pair":
            caption_pairs += 1
        for block in group.get("members") or []:
            bbox = _block_bbox(block)
            block_region, column = _reading_region_for_bbox(bbox, page_width=page_width)
            reasons = ["page-geometry"]
            confidence = 0.78
            if left_count and right_count:
                reasons.append("multi-column-segment")
                confidence += 0.08
            if region == "full_width" or block_region == "full_width":
                reasons.append("cross-column-anchor")
                confidence += 0.05
            if group.get("kind") == "caption_pair":
                reasons.append("caption-paired")
                confidence += 0.05
            if not bbox:
                reasons.append("missing-bbox")
                confidence -= 0.2
            confidence = round(max(0.0, min(1.0, confidence)), 4)
            metadata = block.setdefault("metadata", {})
            metadata["reading_order_method"] = "geometry_columns_v2"
            metadata["reading_order_index"] = len(final_blocks)
            metadata["reading_order_region"] = block_region
            metadata["reading_order_column"] = column
            metadata["reading_order_confidence"] = confidence
            metadata["reading_order_reasons"] = reasons
            block["block_index"] = len(final_blocks)
            metadata["source_reference"] = f"page={int(block.get('page_index') or 0) + 1} block={len(final_blocks)}"
            final_blocks.append(block)
            confidence_total += confidence
            if confidence < 0.72:
                low_confidence_blocks += 1

    average_confidence = round(confidence_total / len(final_blocks), 4) if final_blocks else 0.0
    return final_blocks, {
        "method": "geometry_columns_v2",
        "block_count": len(final_blocks),
        "multi_column": left_count > 0 and right_count > 0,
        "left_column_blocks": left_count,
        "right_column_blocks": right_count,
        "cross_column_blocks": cross_column_blocks,
        "caption_paired_blocks": caption_pairs,
        "low_confidence_blocks": low_confidence_blocks,
        "average_confidence": average_confidence,
    }


def _clean_and_order_pages(raw_pages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    repeated = _repeated_margin_texts(raw_pages)
    cleaned_pages: list[dict[str, Any]] = []
    removed_counts = {"header": 0, "footer": 0, "page_number": 0, "repeated_margin": 0}
    for page in raw_pages:
        page_width = float(page.get("page_size", [0, 0])[0] or 0)
        kept: list[dict[str, Any]] = []
        for block in page.get("blocks") or []:
            role = str(block.get("metadata", {}).get("role") or "body")
            normalized = _normalized_layout_text(str(block.get("text") or ""))
            if role == "page_number":
                removed_counts[role] += 1
                continue
            if role in {"header", "footer"} and normalized in repeated:
                removed_counts[role] += 1
                continue
            if role not in {"header", "footer"} and normalized in repeated:
                removed_counts["repeated_margin"] += 1
                continue
            kept.append(block)
        ordered = sorted(kept, key=lambda item: _reading_sort_key(item, page_width=page_width))
        for index, block in enumerate(ordered):
            block["block_index"] = index
        cleaned_pages.append({**page, "blocks": ordered})
    return cleaned_pages, removed_counts


def _markdown_for_block(block: dict[str, Any]) -> str:
    block_type = str(block.get("type") or "")
    text = str(block.get("text") or "").strip()
    if block_type == "title":
        return f"## {text}"
    if block_type == "interline_equation":
        return f"$$\n{text}\n$$"
    if block_type == "table":
        table_markdown = str(block.get("metadata", {}).get("table_markdown") or "").strip()
        if table_markdown:
            return table_markdown
        return f"```text\n{text}\n```"
    if block_type in {"image", "chart"} and block.get("asset_path"):
        caption = text or f"Image on page {int(block.get('page_index') or 0) + 1}"
        return f"![{caption}]({block['asset_path']})"
    return text


def _bbox_distance(source: list[float], target: list[float], *, page_height: float) -> float:
    if len(source) < 4 or len(target) < 4:
        return page_height
    source_x = (source[0] + source[2]) / 2
    target_x = (target[0] + target[2]) / 2
    vertical_gap = min(abs(target[1] - source[3]), abs(source[1] - target[3]))
    horizontal_gap = abs(source_x - target_x)
    return vertical_gap + horizontal_gap * 0.15


def _nearest_caption(block: dict[str, Any], captions: list[dict[str, Any]], *, page_height: float) -> dict[str, Any] | None:
    block_type = str(block.get("type") or "")
    preferred_kind = "table" if block_type == "table" else "figure"
    bbox = block.get("bbox") if isinstance(block.get("bbox"), list) else []
    if len(bbox) < 4:
        return None
    ranked: list[tuple[float, dict[str, Any]]] = []
    for caption in captions:
        kind = str(caption.get("metadata", {}).get("caption_kind") or "")
        if kind and kind != preferred_kind:
            continue
        caption_bbox = caption.get("bbox") if isinstance(caption.get("bbox"), list) else []
        if len(caption_bbox) < 4:
            continue
        distance = _bbox_distance(bbox, caption_bbox, page_height=page_height)
        if distance <= page_height * 0.18:
            ranked.append((distance, caption))
    if not ranked:
        return None
    return sorted(ranked, key=lambda item: item[0])[0][1]


def _bbox_area(block: dict[str, Any]) -> float:
    bbox = block.get("bbox") if isinstance(block.get("bbox"), list) else []
    if len(bbox) < 4:
        return 0.0
    return max(0.0, float(bbox[2]) - float(bbox[0])) * max(0.0, float(bbox[3]) - float(bbox[1]))


def _evidence_quality(block: dict[str, Any]) -> tuple[float, list[str]]:
    block_type = str(block.get("type") or "")
    text = str(block.get("text") or "").strip()
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    if not metadata.get("evidence_kind"):
        return 0.0, []

    score = 0.48
    reasons: list[str] = ["evidence-kind"]
    if metadata.get("caption"):
        score += 0.2
        reasons.append("caption-linked")
    if metadata.get("caption_kind") == "figure" or _caption_kind(text) == "figure":
        score += 0.1
        reasons.append("figure-caption")
    if metadata.get("source_reference"):
        score += 0.04
        reasons.append("source-reference")

    if block_type in {"image", "chart"}:
        if block.get("asset_path"):
            score += 0.12
            reasons.append("asset")
        area = _bbox_area(block)
        if area >= 12_000:
            score += 0.1
            reasons.append("large-bbox")
        elif area >= 3_000:
            score += 0.05
            reasons.append("usable-bbox")
    elif block_type == "table":
        rows = metadata.get("table_rows") if isinstance(metadata.get("table_rows"), list) else []
        if len(rows) >= 2:
            score += 0.2
            reasons.append("table-rows")
        if metadata.get("table_markdown") or metadata.get("table_html"):
            score += 0.12
            reasons.append("structured-table")
        if int(metadata.get("row_count") or len(rows) or 0) >= 3:
            score += 0.04
            reasons.append("multi-row")
        if int(metadata.get("column_count") or 0) >= 2:
            score += 0.04
            reasons.append("multi-column")
        reconstruction_method = str(metadata.get("table_reconstruction_method") or "")
        reconstruction_confidence = float(metadata.get("table_reconstruction_confidence") or 0)
        if reconstruction_method in {"word_geometry_v2", "pymupdf_table_lines", "booktabs_geometry_v1"}:
            score += min(0.06, reconstruction_confidence * 0.065)
            reasons.append("geometry-reconstructed")
        elif reconstruction_method == "text_spacing_v1":
            reasons.append("text-spacing-fallback")
        if metadata.get("table_has_spanning_cells"):
            reasons.append("spanning-cells")
    elif block_type == "interline_equation":
        if metadata.get("formula_ocr"):
            score += 0.12
            reasons.append("formula-ocr")
        if _looks_like_equation(text):
            score += 0.24
            reasons.append("math-signal")
        if 8 <= len(text) <= 260:
            score += 0.1
            reasons.append("equation-length")
        if metadata.get("equation_id"):
            score += 0.04
            reasons.append("equation-id")
    elif block_type in {"text", "title"}:
        if 12 <= len(text) <= 260:
            score += 0.08
            reasons.append("concise-text")

    confidence = float(metadata.get("evidence_confidence") or 0.0)
    if confidence:
        score += min(0.08, max(0.0, confidence - 0.5) * 0.14)
        reasons.append("confidence")
    return round(max(0.0, min(1.0, score)), 4), reasons


def _enrich_page_blocks(page_blocks: list[dict[str, Any]], *, page_height: float) -> list[dict[str, Any]]:
    captions: list[dict[str, Any]] = []
    for block in page_blocks:
        if str(block.get("type") or "") not in {"text", "title"}:
            continue
        kind = _caption_kind(str(block.get("text") or ""))
        if kind:
            metadata = block.setdefault("metadata", {})
            metadata["caption_kind"] = kind
            metadata["evidence_kind"] = "caption"
            metadata["evidence_confidence"] = 0.78
            captions.append(block)

    for block in page_blocks:
        block_type = str(block.get("type") or "")
        metadata = block.setdefault("metadata", {})
        metadata["source_reference"] = f"page={int(block.get('page_index') or 0) + 1} block={int(block.get('block_index') or 0)}"
        if block_type in {"image", "chart", "table"}:
            caption = _nearest_caption(block, captions, page_height=page_height)
            if caption is not None:
                caption_text = str(caption.get("text") or "").strip()
                metadata["caption"] = caption_text
                metadata["caption_block_index"] = caption.get("block_index")
                metadata["caption_kind"] = caption.get("metadata", {}).get("caption_kind")
                metadata["evidence_confidence"] = 0.86
                if block_type in {"image", "chart"} and not str(block.get("text") or "").strip():
                    block["text"] = caption_text
            else:
                metadata["evidence_confidence"] = 0.58
            metadata["evidence_kind"] = "table" if block_type == "table" else "figure"
        if block_type == "table":
            rows = metadata.get("table_rows") if isinstance(metadata.get("table_rows"), list) else []
            if not rows:
                rows = _parse_table_rows(str(block.get("text") or ""))
                if rows:
                    rows = _normalize_table_rows(rows)
                    metadata.update(
                        {
                            "table_rows": rows,
                            "table_cells": _fallback_table_cells(rows),
                            "table_header_row_count": 1,
                            "table_column_anchors": [],
                            "table_column_boundaries": [],
                            "table_has_spanning_cells": False,
                            "table_reconstruction_method": "text_spacing_v1",
                            "table_reconstruction_confidence": 0.62,
                            "table_reconstruction_reasons": ["whitespace-column-split", "geometry-unavailable"],
                        }
                    )
            if rows:
                rows = _normalize_table_rows(rows)
                metadata["table_rows"] = rows
                cells = metadata.get("table_cells") if isinstance(metadata.get("table_cells"), list) else []
                header_row_count = int(metadata.get("table_header_row_count") or 1)
                metadata["table_markdown"] = _table_to_markdown(
                    rows,
                    header_row_count=header_row_count,
                    cells=cells,
                )
                metadata["table_html"] = _table_to_html(
                    rows,
                    header_row_count=header_row_count,
                    cells=cells,
                )
                metadata["row_count"] = len(rows)
                metadata["column_count"] = max(len(row) for row in rows)
                metadata["evidence_confidence"] = max(
                    float(metadata.get("evidence_confidence") or 0),
                    float(metadata.get("table_reconstruction_confidence") or 0.62),
                )
        if block_type == "interline_equation":
            metadata["evidence_kind"] = "equation"
            metadata["equation_role"] = _equation_role(str(block.get("text") or ""))
            metadata["evidence_confidence"] = 0.76
    for block in page_blocks:
        metadata = block.setdefault("metadata", {})
        if not metadata.get("evidence_kind"):
            continue
        quality_score, quality_reasons = _evidence_quality(block)
        metadata["quality_score"] = quality_score
        metadata["quality_reasons"] = quality_reasons
    return page_blocks


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def parse_pdf_layout(input_path: Path, options: LayoutParserOptions) -> LayoutParseOutput:
    if not input_path.exists():
        raise FileNotFoundError(f"input file does not exist: {input_path}")
    if options.ocr_mode not in {"off", "auto", "force"}:
        raise ValueError("ocr_mode must be one of: off, auto, force")
    if options.ocr_dpi < 72:
        raise ValueError("ocr_dpi must be at least 72")
    if options.formula_ocr_mode not in {"off", "auto", "force"}:
        raise ValueError("formula_ocr_mode must be one of: off, auto, force")
    if options.formula_ocr_dpi < 72:
        raise ValueError("formula_ocr_dpi must be at least 72")
    if not 0 <= options.formula_ocr_min_confidence <= 1:
        raise ValueError("formula_ocr_min_confidence must be between 0 and 1")
    try:
        import fitz
    except Exception as exc:  # pragma: no cover - dependency is present in the project venv
        raise RuntimeError("PyMuPDF is required for AIResearch layout parsing") from exc

    stem = _safe_stem(input_path)
    output_dir = options.output_dir
    assets_dir = output_dir / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    raw_pages: list[dict[str, Any]] = []
    assets: list[Path] = []
    equation_counter = 0
    page_profiles: list[dict[str, Any]] = []
    ocr_pages_attempted = 0
    ocr_pages_succeeded = 0
    ocr_block_count = 0
    ocr_errors: list[str] = []
    ocr_engines: set[str] = set()
    formula_provider = _build_formula_ocr_provider() if options.formula_ocr_mode != "off" else None
    formula_blocks_eligible = 0
    formula_blocks_attempted = 0
    formula_blocks_succeeded = 0
    formula_blocks_rejected = 0
    formula_ocr_errors: list[str] = []
    formula_ocr_models: set[str] = set()

    document = fitz.open(str(input_path))
    try:
        page_count = len(document)
        max_pages = page_count if options.max_pages is None else max(0, min(page_count, options.max_pages))
        for page_index in range(max_pages):
            page = document[page_index]
            page_dict = page.get_text("dict", sort=True)
            page_words = page.get_text("words", sort=True)
            native_table_regions = _table_regions(page, page_words)
            page_width = float(page.rect.width)
            page_height = float(page.rect.height)
            page_profile = _page_text_profile(page_dict, page_width=page_width, page_height=page_height)
            page_profiles.append(page_profile)
            page_blocks: list[dict[str, Any]] = []
            reading_index = 0
            for block in page_dict.get("blocks") or []:
                if not isinstance(block, dict):
                    continue
                raw_type = int(block.get("type") or 0)
                bbox = [float(value) for value in block.get("bbox", [0, 0, 0, 0])]
                if raw_type == 0:
                    if any(_bbox_overlap_ratio(bbox, region["bbox"]) >= 0.72 for region in native_table_regions):
                        continue
                    text = _block_text(block)
                    if not text:
                        continue
                    block_type = _classify_text_block(text, block, page_height=page_height)
                    table_geometry = (
                        _reconstruct_table_from_words(page_words, bbox)
                        if block_type == "table"
                        else {}
                    )
                    if block_type == "table" and not _table_geometry_is_coherent(table_geometry):
                        block_type = "text"
                        table_geometry = {}
                    equation_id = ""
                    if block_type == "interline_equation":
                        equation_counter += 1
                        equation_id = f"eq-{equation_counter}"
                    record = {
                        "type": block_type,
                        "page_index": page_index,
                        "block_index": reading_index,
                        "bbox": bbox,
                        "text": text,
                        "asset_path": "",
                        "metadata": {
                            "parser": PARSER_NAME,
                            "role": _block_role(text, bbox, page_width=page_width, page_height=page_height),
                            "span_sizes": _span_sizes(block)[:20],
                            **(_geometry_table_metadata(table_geometry) if block_type == "table" else {}),
                            **({"equation_id": equation_id} if equation_id else {}),
                        },
                    }
                elif raw_type == 1:
                    image_bytes = block.get("image")
                    ext = str(block.get("ext") or "png").lower()
                    if ext not in IMAGE_EXTENSIONS:
                        ext = "png"
                    asset_path = ""
                    if isinstance(image_bytes, (bytes, bytearray)) and image_bytes:
                        digest = hashlib.sha256(image_bytes).hexdigest()[:16]
                        asset = assets_dir / f"page-{page_index + 1}-image-{reading_index}-{digest}.{ext}"
                        if not asset.exists():
                            asset.write_bytes(image_bytes)
                        assets.append(asset)
                        asset_path = str(asset.relative_to(output_dir))
                    record = {
                        "type": "image",
                        "page_index": page_index,
                        "block_index": reading_index,
                        "bbox": bbox,
                        "text": "",
                        "asset_path": asset_path,
                        "metadata": {
                            "parser": PARSER_NAME,
                            "width": block.get("width"),
                            "height": block.get("height"),
                        },
                    }
                else:
                    continue
                page_blocks.append(record)
                reading_index += 1
            for native_table in native_table_regions:
                geometry = native_table["geometry"]
                table_rows = geometry.get("table_rows") or []
                table_text = "\n".join("\t".join(str(value) for value in row) for row in table_rows)
                native_bbox = [float(value) for value in native_table["bbox"]]
                page_blocks.append(
                    {
                        "type": "table",
                        "page_index": page_index,
                        "block_index": reading_index,
                        "bbox": native_bbox,
                        "text": table_text,
                        "asset_path": "",
                        "metadata": {
                            "parser": PARSER_NAME,
                            "role": _block_role(table_text, native_bbox, page_width=page_width, page_height=page_height),
                            "table_region_source": (
                                "booktabs_horizontal_rules"
                                if geometry.get("reconstruction_method") == "booktabs_geometry_v1"
                                else "pymupdf_lines"
                            ),
                            **_geometry_table_metadata(geometry),
                        },
                    }
                )
                reading_index += 1
            should_ocr = options.ocr_mode == "force" or (
                options.ocr_mode == "auto"
                and page_profile["page_type"] in {"scanned", "mixed"}
                and int(page_profile["text_chars"]) < options.ocr_min_text_chars
            )
            ocr_status = "not_requested"
            if should_ocr:
                ocr_pages_attempted += 1
                ocr_rows, ocr_result = _ocr_page_with_tesseract(
                    page,
                    page_index=page_index,
                    languages=options.ocr_languages,
                    dpi=options.ocr_dpi,
                    executable=options.ocr_executable,
                )
                ocr_status = str(ocr_result.get("status") or "failed")
                engine = str(ocr_result.get("engine") or "tesseract")
                ocr_engines.add(engine)
                error = str(ocr_result.get("error") or "")
                if error:
                    ocr_errors.append(f"page {page_index + 1}: {error}")
                if ocr_status == "completed":
                    ocr_pages_succeeded += 1
                for ocr_row in ocr_rows:
                    text = str(ocr_row.get("text") or "").strip()
                    bbox = ocr_row.get("bbox") if isinstance(ocr_row.get("bbox"), list) else []
                    if not text or len(bbox) < 4:
                        continue
                    normalized_bbox = [float(value) for value in bbox[:4]]
                    if _looks_like_table(text):
                        block_type = "table"
                    elif _looks_like_equation(text):
                        block_type = "interline_equation"
                    else:
                        block_type = "text"
                    equation_id = ""
                    if block_type == "interline_equation":
                        equation_counter += 1
                        equation_id = f"eq-{equation_counter}"
                    page_blocks.append(
                        {
                            "type": block_type,
                            "page_index": page_index,
                            "block_index": reading_index,
                            "bbox": normalized_bbox,
                            "text": text,
                            "asset_path": "",
                            "metadata": {
                                "parser": PARSER_NAME,
                                "role": _block_role(text, normalized_bbox, page_width=page_width, page_height=page_height),
                                "ocr": True,
                                "ocr_engine": engine,
                                "ocr_languages": options.ocr_languages,
                                "ocr_confidence": round(float(ocr_row.get("confidence") or 0), 4),
                                **({"equation_id": equation_id} if equation_id else {}),
                            },
                        }
                    )
                    reading_index += 1
                    ocr_block_count += 1
            for formula_block in page_blocks:
                if str(formula_block.get("type") or "") != "interline_equation":
                    continue
                formula_metadata = formula_block.setdefault("metadata", {})
                should_formula_ocr = options.formula_ocr_mode == "force" or (
                    options.formula_ocr_mode == "auto" and bool(formula_metadata.get("ocr"))
                )
                if not should_formula_ocr:
                    continue
                formula_blocks_eligible += 1
                if formula_provider is None:
                    formula_metadata["formula_ocr_status"] = "unavailable"
                    continue
                formula_blocks_attempted += 1
                crop_bytes = _formula_crop_png(
                    page,
                    formula_block.get("bbox") if isinstance(formula_block.get("bbox"), list) else [],
                    dpi=options.formula_ocr_dpi,
                )
                if not crop_bytes:
                    formula_blocks_rejected += 1
                    formula_metadata["formula_ocr_status"] = "invalid_crop"
                    continue
                try:
                    formula_result = formula_provider.recognize(
                        crop_bytes,
                        mime_type="image/png",
                        context=str(formula_block.get("text") or ""),
                    )
                except FormulaOCRError as exc:
                    formula_blocks_rejected += 1
                    formula_metadata["formula_ocr_status"] = "failed"
                    formula_ocr_errors.append(f"page {page_index + 1} block {formula_block.get('block_index')}: {exc}")
                    lowered_error = str(exc).lower()
                    if any(token in lowered_error for token in ("invalidsubscription", "http 401", "http 403")):
                        formula_provider = None
                    continue
                except Exception as exc:  # provider adapters may raise transport-specific errors
                    formula_blocks_rejected += 1
                    formula_metadata["formula_ocr_status"] = "failed"
                    formula_ocr_errors.append(
                        f"page {page_index + 1} block {formula_block.get('block_index')}: {type(exc).__name__}: {exc}"
                    )
                    continue
                formula_ocr_models.add(str(formula_result.model))
                formula_metadata["formula_ocr_candidate_latex"] = formula_result.latex
                formula_metadata["formula_ocr_confidence"] = round(float(formula_result.confidence), 4)
                formula_metadata["formula_ocr_model"] = formula_result.model
                formula_metadata["formula_ocr_provider"] = formula_result.provider
                if formula_result.confidence < options.formula_ocr_min_confidence:
                    formula_blocks_rejected += 1
                    formula_metadata["formula_ocr_status"] = "low_confidence"
                    continue
                digest = hashlib.sha256(crop_bytes).hexdigest()[:16]
                formula_asset = assets_dir / f"page-{page_index + 1}-equation-{formula_block.get('block_index')}-{digest}.png"
                if not formula_asset.exists():
                    formula_asset.write_bytes(crop_bytes)
                assets.append(formula_asset)
                source_text = str(formula_block.get("text") or "")
                formula_block["text"] = formula_result.latex
                formula_block["asset_path"] = str(formula_asset.relative_to(output_dir))
                formula_metadata["formula_ocr"] = True
                formula_metadata["formula_ocr_status"] = "completed"
                formula_metadata["formula_ocr_source_text"] = source_text
                formula_metadata["formula_latex"] = formula_result.latex
                formula_metadata["evidence_confidence"] = max(
                    float(formula_metadata.get("evidence_confidence") or 0),
                    float(formula_result.confidence),
                )
                formula_blocks_succeeded += 1
            raw_pages.append(
                {
                    "page_index": page_index,
                    "page_size": [page_width, page_height],
                    "metadata": {**page_profile, "ocr_status": ocr_status},
                    "blocks": page_blocks,
                }
            )
    finally:
        document.close()

    pages, removed_counts = _clean_and_order_pages(raw_pages)
    content_list: list[dict[str, Any]] = []
    markdown_blocks: list[str] = []
    reading_order_pages: list[dict[str, Any]] = []
    for page in pages:
        page_width = float(page.get("page_size", [0, 0])[0] or 0)
        page_height = float(page.get("page_size", [0, 0])[1] or 0)
        page_blocks = _enrich_page_blocks(page.get("blocks") or [], page_height=page_height)
        page_blocks, reading_order_stats = _apply_reading_order(
            page_blocks,
            page_width=page_width,
            page_height=page_height,
        )
        page["blocks"] = page_blocks
        page.setdefault("metadata", {})["reading_order"] = reading_order_stats
        reading_order_pages.append(reading_order_stats)
        for record in page_blocks:
            content_list.append(record)
            rendered = _markdown_for_block(record)
            if rendered:
                markdown_blocks.append(rendered)

    markdown_path = output_dir / f"{stem}_layout.md"
    content_path = output_dir / f"{stem}_content_list.json"
    structure_path = output_dir / f"{stem}_layout.json"
    debug_path = output_dir / f"{stem}_layout_debug.json"
    summary_path = output_dir / f"{stem}_layout_summary.json"
    block_types = {
        block_type: sum(1 for item in content_list if item.get("type") == block_type)
        for block_type in sorted({str(item.get("type") or "") for item in content_list})
    }
    page_type_counts = {
        page_type: sum(1 for profile in page_profiles if profile.get("page_type") == page_type)
        for page_type in ("digital", "mixed", "scanned")
        if any(profile.get("page_type") == page_type for profile in page_profiles)
    }
    document_type = "digital"
    if page_type_counts.get("scanned") == len(page_profiles) and page_profiles:
        document_type = "scanned"
    elif page_type_counts.get("scanned") or page_type_counts.get("mixed"):
        document_type = "mixed"
    summary = {
        "parser": PARSER_NAME,
        "parser_version": PARSER_VERSION,
        "input_path": str(input_path),
        "page_count": len(pages),
        "block_count": len(content_list),
        "asset_count": len(assets),
        "document_type": document_type,
        "page_types": page_type_counts,
        "ocr": {
            "mode": options.ocr_mode,
            "languages": options.ocr_languages,
            "dpi": options.ocr_dpi,
            "available": bool(shutil.which(options.ocr_executable)) or ocr_pages_succeeded > 0,
            "engines": sorted(ocr_engines),
            "pages_attempted": ocr_pages_attempted,
            "pages_succeeded": ocr_pages_succeeded,
            "block_count": ocr_block_count,
            "errors": ocr_errors[:20],
        },
        "formula_ocr": {
            "mode": options.formula_ocr_mode,
            "configured": formula_provider is not None,
            "dpi": options.formula_ocr_dpi,
            "min_confidence": options.formula_ocr_min_confidence,
            "blocks_eligible": formula_blocks_eligible,
            "blocks_attempted": formula_blocks_attempted,
            "blocks_succeeded": formula_blocks_succeeded,
            "blocks_rejected": formula_blocks_rejected,
            "models": sorted(formula_ocr_models),
            "errors": formula_ocr_errors[:20],
        },
        "block_types": block_types,
        "captioned_visual_blocks": sum(
            1
            for item in content_list
            if item.get("type") in {"image", "chart", "table"} and item.get("metadata", {}).get("caption")
        ),
        "structured_table_blocks": sum(1 for item in content_list if item.get("metadata", {}).get("table_rows")),
        "geometry_table_blocks": sum(
            1
            for item in content_list
            if item.get("metadata", {}).get("table_reconstruction_method")
            in {"word_geometry_v2", "pymupdf_table_lines", "booktabs_geometry_v1"}
        ),
        "text_fallback_table_blocks": sum(
            1
            for item in content_list
            if item.get("metadata", {}).get("table_reconstruction_method") == "text_spacing_v1"
        ),
        "spanning_table_blocks": sum(
            1 for item in content_list if item.get("metadata", {}).get("table_has_spanning_cells")
        ),
        "reading_order": {
            "method": "geometry_columns_v2",
            "pages_completed": len(reading_order_pages),
            "multi_column_pages": sum(1 for item in reading_order_pages if item.get("multi_column")),
            "cross_column_blocks": sum(int(item.get("cross_column_blocks") or 0) for item in reading_order_pages),
            "caption_paired_blocks": sum(int(item.get("caption_paired_blocks") or 0) for item in reading_order_pages),
            "low_confidence_blocks": sum(int(item.get("low_confidence_blocks") or 0) for item in reading_order_pages),
            "average_confidence": round(
                sum(float(item.get("average_confidence") or 0) for item in reading_order_pages)
                / max(1, len(reading_order_pages)),
                4,
            ),
        },
        "equation_blocks": sum(1 for item in content_list if item.get("type") == "interline_equation"),
        "evidence_ready_blocks": sum(1 for item in content_list if item.get("metadata", {}).get("evidence_kind")),
        "high_quality_evidence_blocks": sum(1 for item in content_list if float(item.get("metadata", {}).get("quality_score") or 0) >= 0.72),
        "high_quality_visual_blocks": sum(
            1
            for item in content_list
            if item.get("type") in {"image", "chart"} and float(item.get("metadata", {}).get("quality_score") or 0) >= 0.72
        ),
        "high_quality_table_blocks": sum(
            1
            for item in content_list
            if item.get("type") == "table" and float(item.get("metadata", {}).get("quality_score") or 0) >= 0.72
        ),
        "high_quality_equation_blocks": sum(
            1
            for item in content_list
            if item.get("type") == "interline_equation" and float(item.get("metadata", {}).get("quality_score") or 0) >= 0.72
        ),
        "removed_margin_blocks": removed_counts,
    }
    markdown_path.write_text("\n\n".join(markdown_blocks).strip() + "\n", encoding="utf-8")
    _write_json(content_path, content_list)
    _write_json(
        structure_path,
        {
            "parser": PARSER_NAME,
            "parser_version": PARSER_VERSION,
            "input_path": str(input_path),
            "page_count": len(pages),
            "pages": pages,
        },
    )
    _write_json(
        debug_path,
        {
            "parser": PARSER_NAME,
            "parser_version": PARSER_VERSION,
            "block_count": len(content_list),
            "asset_count": len(assets),
            "block_types": block_types,
            "removed_margin_blocks": removed_counts,
            "document_type": document_type,
            "page_types": page_type_counts,
            "ocr": summary["ocr"],
            "formula_ocr": summary["formula_ocr"],
            "reading_order": summary["reading_order"],
        },
    )
    _write_json(summary_path, summary)

    return LayoutParseOutput(
        output_dir=output_dir,
        markdown_files=[markdown_path],
        content_list_files=[content_path],
        structure_json_files=[structure_path],
        debug_json_files=[debug_path],
        summary_files=[summary_path],
        assets=assets,
    )
