from __future__ import annotations

import json
import re
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.image_selection import IMAGE_SUFFIXES, ImageDimensions, image_dimensions, representative_image
from airesearch.layout_parser import PARSER_NAME, PARSER_VERSION, _caption_kind


VISUAL_BLOCK_TYPES = {"image", "chart", "table"}
EARLY_FIGURE_NUMBERS = {1, 2}


@dataclass(frozen=True)
class LayoutVisualCandidate:
    source_path: Path
    source_kind: str
    asset_kind: str
    caption: str = ""
    source_reference: str = ""
    confidence: float = 0.0
    score: float = 0.0
    page_index: int | None = None
    block_index: int | None = None
    dimensions: ImageDimensions | None = None
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_path"] = str(self.source_path)
        if self.dimensions is not None:
            payload["dimensions"] = {
                "width": self.dimensions.width,
                "height": self.dimensions.height,
                "area": self.dimensions.area,
                "aspect_skew": self.dimensions.aspect_skew,
            }
        return payload


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _existing_file(path: str | Path | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.exists() and candidate.is_file():
        return candidate.resolve()
    return None


def _existing_dir(path: str | Path | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.exists() and candidate.is_dir():
        return candidate.resolve()
    return None


def _resolve_layout_asset_path(asset_path: str, metadata: dict[str, Any], output_dir: str = "") -> Path | None:
    if not asset_path:
        return None
    candidate = Path(asset_path)
    if candidate.is_absolute():
        return _existing_file(candidate)

    source_path = _existing_file(str(metadata.get("source_path") or ""))
    if source_path is not None:
        resolved = _existing_file(source_path.parent / asset_path)
        if resolved is not None:
            return resolved

    run_output = _existing_dir(output_dir)
    if run_output is not None:
        resolved = _existing_file(run_output / asset_path)
        if resolved is not None:
            return resolved

    return _existing_file(candidate)


def _dimension_score(dimensions: ImageDimensions | None) -> float:
    if dimensions is None:
        return 0.0
    score = float(dimensions.area)
    min_side = min(dimensions.width, dimensions.height)
    if dimensions.area < 90_000:
        score *= 0.25
    if min_side < 160:
        score *= 0.12
    elif min_side < 240:
        score *= 0.55
    skew = dimensions.aspect_skew
    if skew > 8:
        score *= 0.08
    elif skew > 5:
        score *= 0.22
    elif skew > 3.6:
        score *= 0.58
    elif skew > 3:
        score *= 0.82
    return score


def _figure_number(value: str) -> int | None:
    lowered = value.lower()
    match = re.search(r"\b(?:fig(?:ure)?\.?)\s*([0-9]{1,2})(?:\b|[.:])", lowered)
    if match:
        return int(match.group(1))
    match = re.search(r"(?:^|[^\w])图\s*([0-9]{1,2})(?:\b|[.:：])", value)
    if match:
        return int(match.group(1))
    match = re.search(r"(?:^|[-_])(?:fig(?:ure)?[-_]?|figure[-_])?0?([1-9][0-9]?)(?:[-_.]|$)", lowered)
    if match:
        return int(match.group(1))
    return None


def _figure_number_bonus(number: int | None) -> float:
    if number is None:
        return 0.0
    if number == 1:
        return 2_350_000.0
    if number == 2:
        return 2_250_000.0
    if number <= 5:
        return 1_350_000.0 - (number * 80_000.0)
    return max(0.0, 780_000.0 - (number * 35_000.0))


def _page_bonus(page_index: int | None) -> float:
    if page_index is None:
        return 0.0
    if page_index <= 0:
        return 520_000.0
    if page_index == 1:
        return 440_000.0
    if page_index == 2:
        return 360_000.0
    if page_index <= 4:
        return 180_000.0
    return 0.0


def _kind_bonus(asset_kind: str, source_kind: str) -> float:
    if asset_kind == "figure":
        base = 420_000.0
    elif asset_kind == "chart":
        base = 360_000.0
    elif asset_kind == "table":
        base = -180_000.0
    else:
        base = 0.0
    if source_kind == "layout_block":
        base += 220_000.0
    elif source_kind == "pdf_figure_crop":
        base += 1_250_000.0
    elif source_kind == "source_figure":
        base += 160_000.0
    return base


def _caption_semantic_bonus(value: str) -> float:
    lowered = value.lower()
    bonus = 0.0
    if any(term in lowered for term in ("overview", "framework", "architecture", "pipeline", "roadmap")):
        bonus += 320_000.0
    if any(term in lowered for term in ("example", "qualitative", "case study")):
        bonus += 120_000.0
    return bonus


def _score_candidate(candidate: LayoutVisualCandidate) -> LayoutVisualCandidate:
    caption_text = candidate.caption or candidate.source_path.name
    number = _figure_number(caption_text)
    dimension = _dimension_score(candidate.dimensions)
    score = (
        min(dimension / 4.0, 820_000.0)
        + _figure_number_bonus(number)
        + _page_bonus(candidate.page_index)
        + _kind_bonus(candidate.asset_kind, candidate.source_kind)
        + _caption_semantic_bonus(caption_text)
        + (candidate.confidence * 240_000.0)
    )
    if not candidate.caption and candidate.source_kind == "layout_block":
        score -= 320_000.0
    if candidate.dimensions is not None and candidate.dimensions.aspect_skew > 4.5:
        score -= 170_000.0
    reason_parts = [candidate.source_kind]
    if number is not None:
        reason_parts.append(f"figure={number}")
    if candidate.page_index is not None:
        reason_parts.append(f"page={candidate.page_index + 1}")
    if candidate.dimensions is not None:
        reason_parts.append(f"{candidate.dimensions.width}x{candidate.dimensions.height}")
    return LayoutVisualCandidate(
        source_path=candidate.source_path,
        source_kind=candidate.source_kind,
        asset_kind=candidate.asset_kind,
        caption=candidate.caption,
        source_reference=candidate.source_reference,
        confidence=candidate.confidence,
        score=score,
        page_index=candidate.page_index,
        block_index=candidate.block_index,
        dimensions=candidate.dimensions,
        reason=", ".join(reason_parts),
    )


def get_layout_summary(db_path: Path, paper_key: str) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            select stats_json from paper_layout_runs
            where paper_key = ? and provider = ? and provider_version = ? and status = 'completed'
            order by id desc
            limit 1
            """,
            (paper_key, PARSER_NAME, PARSER_VERSION),
        ).fetchone()
    stats = _json_loads(row["stats_json"], {}) if row is not None else {}
    summary = stats.get("summary") if isinstance(stats, dict) else {}
    return summary if isinstance(summary, dict) else {}


def layout_visual_candidates(db_path: Path, paper_key: str) -> list[LayoutVisualCandidate]:
    init_db(db_path)
    with connect(db_path) as conn:
        latest = conn.execute(
            """
            select id, output_dir from paper_layout_runs
            where paper_key = ? and provider = ? and provider_version = ? and status = 'completed'
            order by id desc
            limit 1
            """,
            (paper_key, PARSER_NAME, PARSER_VERSION),
        ).fetchone()
        if latest is None:
            return []
        rows = conn.execute(
            """
            select id, page_index, block_index, block_type, text, asset_path, metadata_json
            from paper_layout_blocks
            where paper_key = ? and run_id = ? and asset_path <> ''
              and block_type in ('image', 'chart', 'table')
            order by page_index, block_index
            """,
            (paper_key, int(latest["id"])),
        ).fetchall()

    candidates: list[LayoutVisualCandidate] = []
    for row in rows:
        metadata = _json_loads(row["metadata_json"], {})
        if not isinstance(metadata, dict):
            metadata = {}
        source_path = _resolve_layout_asset_path(str(row["asset_path"] or ""), metadata, str(latest["output_dir"] or ""))
        if source_path is None or source_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        block_type = str(row["block_type"] or "")
        asset_kind = "table" if block_type == "table" else "chart" if block_type == "chart" else "figure"
        caption = str(metadata.get("caption") or row["text"] or "").strip()
        try:
            confidence = float(metadata.get("evidence_confidence") or 0.72)
        except (TypeError, ValueError):
            confidence = 0.72
        candidates.append(
            _score_candidate(
                LayoutVisualCandidate(
                    source_path=source_path,
                    source_kind="layout_block",
                    asset_kind=asset_kind,
                    caption=caption,
                    source_reference=str(metadata.get("source_reference") or f"page={int(row['page_index']) + 1} block={row['block_index']}"),
                    confidence=confidence,
                    page_index=int(row["page_index"]),
                    block_index=int(row["block_index"]),
                    dimensions=image_dimensions(source_path),
                )
            )
        )
    return sorted(candidates, key=lambda item: (item.score, item.source_path.name), reverse=True)


def _latest_layout_run(conn: Any, paper_key: str) -> Any:
    return conn.execute(
        """
        select id, output_dir from paper_layout_runs
        where paper_key = ? and provider = ? and provider_version = ? and status = 'completed'
        order by id desc
        limit 1
        """,
        (paper_key, PARSER_NAME, PARSER_VERSION),
    ).fetchone()


def _paper_pdf_path(conn: Any, paper_key: str) -> Path | None:
    artifact = conn.execute(
        """
        select path from paper_artifacts
        where paper_key = ? and artifact_type = 'paper_pdf'
        order by id desc
        limit 1
        """,
        (paper_key,),
    ).fetchone()
    if artifact is not None:
        existing = _existing_file(str(artifact["path"] or ""))
        if existing is not None:
            return existing
    paper = conn.execute("select paper_dir from papers where paper_key = ?", (paper_key,)).fetchone()
    if paper is None:
        return None
    return _existing_file(Path(str(paper["paper_dir"] or "")) / "paper.pdf")


def _candidate_caption_number(text: str, metadata: dict[str, Any]) -> int | None:
    return _figure_number(str(metadata.get("caption") or "") or text)


def _looks_like_figure_caption(text: str) -> bool:
    return _caption_kind(text) == "figure"


def _normalize_bbox(value: str | list[Any] | tuple[Any, ...] | None) -> list[float] | None:
    if isinstance(value, str):
        try:
            parsed = json.loads(value or "[]")
        except json.JSONDecodeError:
            return None
    else:
        parsed = value
    if not isinstance(parsed, (list, tuple)) or len(parsed) < 4:
        return None
    try:
        left, top, right, bottom = [float(item) for item in parsed[:4]]
    except (TypeError, ValueError):
        return None
    if right <= left or bottom <= top:
        return None
    return [left, top, right, bottom]


def _bbox_union(boxes: list[list[float]]) -> list[float] | None:
    if not boxes:
        return None
    left, top, right, bottom = boxes[0]
    for box in boxes[1:]:
        left = min(left, float(box[0]))
        top = min(top, float(box[1]))
        right = max(right, float(box[2]))
        bottom = max(bottom, float(box[3]))
    return [left, top, right, bottom]


def _horizontal_overlap_ratio(a: list[float], b: list[float]) -> float:
    overlap = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    narrow = max(1.0, min(a[2] - a[0], b[2] - b[0]))
    return overlap / narrow


def _visual_boxes_connected(
    first: list[float],
    second: list[float],
    *,
    page_width: float,
    page_height: float,
) -> bool:
    """Return whether two extracted layers belong to one visual composition."""
    horizontal_overlap = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    vertical_overlap = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    horizontal_gap = max(0.0, max(first[0], second[0]) - min(first[2], second[2]))
    vertical_gap = max(0.0, max(first[1], second[1]) - min(first[3], second[3]))
    x_tolerance = max(14.0, page_width * 0.05)
    y_tolerance = max(12.0, page_height * 0.035)

    if horizontal_overlap > 0.0 and vertical_gap <= y_tolerance:
        return True
    if vertical_overlap > 0.0 and horizontal_gap <= x_tolerance:
        return True
    return horizontal_gap <= x_tolerance and vertical_gap <= y_tolerance


def _nearby_visual_bbox(
    visuals: list[dict[str, Any]],
    caption_bbox: list[float],
    *,
    figure_number: int | None = None,
) -> tuple[list[float] | None, int]:
    if not visuals:
        return None, 0
    caption_left, caption_top, caption_right, caption_bottom = caption_bbox
    caption_width = max(1.0, caption_right - caption_left)
    page_left = min(float(item["bbox"][0]) for item in visuals)
    page_right = max(float(item["bbox"][2]) for item in visuals)
    page_width = max(caption_width, page_right - page_left, 1.0)
    x_tolerance = page_width * 0.08
    caption_band = [
        max(page_left, caption_left - x_tolerance),
        caption_top,
        min(page_right, caption_right + x_tolerance),
        caption_bottom,
    ]

    page_height = max(
        caption_bottom,
        max(float(item["bbox"][3]) for item in visuals),
    ) - min(caption_top, min(float(item["bbox"][1]) for item in visuals))
    caption_link_gap = max(240.0, page_height * 0.75)
    expansion_pool: list[tuple[float, dict[str, Any]]] = []
    above: list[tuple[float, dict[str, Any]]] = []
    for visual in visuals:
        bbox = visual["bbox"]
        if _horizontal_overlap_ratio(bbox, caption_band) < 0.18:
            continue
        gap = caption_top - float(bbox[3])
        if -8.0 <= gap <= caption_link_gap:
            expansion_pool.append((max(0.0, gap), visual))
        caption_linked = figure_number is not None and visual.get("figure_number") == figure_number and gap >= -8.0
        if -8.0 <= gap <= 190.0 or (caption_linked and gap <= caption_link_gap):
            above.append((max(0.0, gap), visual))

    if above:
        nearest_gap = min(gap for gap, _visual in above)
        band = max(28.0, page_width * 0.045)
        nearest = [visual for gap, visual in above if gap <= nearest_gap + band]
        same_caption = [
            visual
            for _gap, visual in above
            if figure_number is not None and visual.get("figure_number") == figure_number
        ]
        seeds = same_caption or nearest

        # A PDF may expose one composite figure as many image layers. Expand
        # from the caption-linked layers through adjacent/overlapping layers so
        # a lower panel cannot hide the rest of the figure.
        selected_ids = {id(visual) for visual in seeds}
        changed = True
        while changed:
            changed = False
            selected = [visual for _gap, visual in expansion_pool if id(visual) in selected_ids]
            for _gap, visual in expansion_pool:
                if id(visual) in selected_ids:
                    continue
                if any(
                    _visual_boxes_connected(
                        visual["bbox"],
                        selected_visual["bbox"],
                        page_width=page_width,
                        page_height=page_height,
                    )
                    for selected_visual in selected
                ):
                    selected_ids.add(id(visual))
                    changed = True

        selected_boxes = [visual["bbox"] for _gap, visual in expansion_pool if id(visual) in selected_ids]
        union = _bbox_union(selected_boxes)
        if union is not None:
            # Some PDF producers attach the figure caption only to a subset
            # of image layers. Pull in uncaptioned layers that overlap the
            # assembled envelope, including a right-hand panel separated by
            # text objects.
            changed = True
            while changed:
                changed = False
                for _gap, visual in expansion_pool:
                    if id(visual) in selected_ids:
                        continue
                    if _visual_boxes_connected(
                        visual["bbox"],
                        union,
                        page_width=page_width,
                        page_height=page_height,
                    ):
                        selected_ids.add(id(visual))
                        selected_boxes.append(visual["bbox"])
                        union = _bbox_union(selected_boxes)
                        changed = True
        return union, len(selected_boxes)

    nearest = min(
        visuals,
        key=lambda item: min(abs(float(item["bbox"][1]) - caption_bottom), abs(float(item["bbox"][3]) - caption_top)),
    )
    return list(nearest["bbox"]), 1


def _expand_figure_bbox_with_supporting_text(
    visual_bbox: list[float] | None,
    text_blocks: list[dict[str, Any]],
    *,
    caption_top: float | None,
) -> list[float] | None:
    if visual_bbox is None or caption_top is None:
        return visual_bbox
    expanded = list(visual_bbox)
    for block in text_blocks:
        bbox = block.get("bbox")
        if not isinstance(bbox, list) or len(bbox) < 4:
            continue
        text = " ".join(str(block.get("text") or "").split())
        if not text or len(text) > 360:
            continue
        if float(bbox[1]) < float(visual_bbox[3]) - 6.0:
            continue
        if float(bbox[3]) > float(caption_top) - 1.0:
            continue
        if _horizontal_overlap_ratio(bbox, visual_bbox) < 0.12:
            continue
        expanded[0] = min(expanded[0], float(bbox[0]))
        expanded[2] = max(expanded[2], float(bbox[2]))
        expanded[3] = max(expanded[3], float(bbox[3]))
    return expanded


def _figure_caption_crop_rows(conn: Any, paper_key: str, run_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select page_index, block_index, block_type, bbox_json, text, asset_path, metadata_json
        from paper_layout_blocks
        where paper_key = ? and run_id = ?
        order by page_index, block_index
        """,
        (paper_key, run_id),
    ).fetchall()
    page_visuals: dict[int, list[dict[str, Any]]] = {}
    page_text_blocks: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        page_index = int(row["page_index"])
        bbox = _normalize_bbox(str(row["bbox_json"] or "[]"))
        if bbox is not None and str(row["block_type"] or "") in {"text", "title"}:
            page_text_blocks.setdefault(page_index, []).append(
                {
                    "bbox": bbox,
                    "text": str(row["text"] or ""),
                }
            )
        if str(row["block_type"] or "") in {"image", "chart"} and str(row["asset_path"] or ""):
            if bbox is not None:
                metadata = _json_loads(row["metadata_json"], {})
                if not isinstance(metadata, dict):
                    metadata = {}
                text = str(row["text"] or "")
                page_visuals.setdefault(page_index, []).append(
                    {
                        "block_index": int(row["block_index"]),
                        "bbox": bbox,
                        "figure_number": _candidate_caption_number(text, metadata),
                    }
                )

    grouped: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        metadata = _json_loads(row["metadata_json"], {})
        if not isinstance(metadata, dict):
            metadata = {}
        text = str(row["text"] or "")
        number = _candidate_caption_number(text, metadata)
        if number not in EARLY_FIGURE_NUMBERS:
            continue
        page_index = int(row["page_index"])
        caption_text = str(metadata.get("caption") or text).strip()
        row_block_type = str(row["block_type"] or "")
        is_caption = _looks_like_figure_caption(text)
        if not is_caption and row_block_type in {"text", "title"}:
            is_caption = _looks_like_figure_caption(str(metadata.get("caption") or ""))
        if not is_caption:
            continue
        normalized_bbox = _normalize_bbox(str(row["bbox_json"] or "[]"))
        if normalized_bbox is None:
            continue
        page_visual_items = page_visuals.get(page_index, [])
        caption_layer_count = sum(
            1
            for visual in page_visual_items
            if visual.get("figure_number") == number
        )
        if (
            row_block_type in {"image", "chart"}
            and str(row["asset_path"] or "")
            and caption_layer_count <= 1
        ):
            crop_bbox = normalized_bbox
            fragment_count = 1
        else:
            crop_bbox, fragment_count = _nearby_visual_bbox(
                page_visual_items,
                normalized_bbox,
                figure_number=number,
            )
        crop_method = "figure_bbox" if crop_bbox is not None else "caption_window"
        if crop_bbox is not None and fragment_count > 1:
            crop_method = "fragmented_layers"
        key = (page_index, number)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                "page_index": page_index,
                "block_index": int(row["block_index"]),
                "figure_number": number,
                "caption": caption_text,
                "bbox": normalized_bbox,
                "crop_bbox": crop_bbox,
                "crop_method": crop_method,
                "fragment_count": fragment_count,
                "caption_top": normalized_bbox[1] if row_block_type in {"text", "title"} else None,
            }
            continue
        existing_bbox = existing["bbox"]
        existing["bbox"] = [
            min(float(existing_bbox[0]), normalized_bbox[0]),
            min(float(existing_bbox[1]), normalized_bbox[1]),
            max(float(existing_bbox[2]), normalized_bbox[2]),
            max(float(existing_bbox[3]), normalized_bbox[3]),
        ]
        if len(caption_text) > len(str(existing.get("caption") or "")):
            existing["caption"] = caption_text
        existing["block_index"] = min(int(existing["block_index"]), int(row["block_index"]))
        if row_block_type in {"text", "title"}:
            existing_caption_top = existing.get("caption_top")
            existing["caption_top"] = min(
                float(existing_caption_top) if existing_caption_top is not None else normalized_bbox[1],
                normalized_bbox[1],
            )
        existing_crop_bbox = existing.get("crop_bbox")
        if existing_crop_bbox is not None and crop_bbox is not None:
            existing["crop_bbox"] = [
                min(float(existing_crop_bbox[0]), float(crop_bbox[0])),
                min(float(existing_crop_bbox[1]), float(crop_bbox[1])),
                max(float(existing_crop_bbox[2]), float(crop_bbox[2])),
                max(float(existing_crop_bbox[3]), float(crop_bbox[3])),
            ]
            existing["fragment_count"] = max(int(existing.get("fragment_count") or 1), fragment_count)
            if int(existing["fragment_count"]) > 1:
                existing["crop_method"] = "fragmented_layers"
        elif existing_crop_bbox is None and crop_bbox is not None:
            existing["crop_bbox"] = crop_bbox
            existing["crop_method"] = crop_method
            existing["fragment_count"] = fragment_count
    for item in grouped.values():
        item["crop_bbox"] = _expand_figure_bbox_with_supporting_text(
            item.get("crop_bbox"),
            page_text_blocks.get(int(item["page_index"]), []),
            caption_top=float(item["caption_top"]) if item.get("caption_top") is not None else None,
        )
        item.pop("caption_top", None)
    return sorted(grouped.values(), key=lambda item: (int(item["figure_number"]), int(item["page_index"])))


def _pdf_page_size(pdf_path: Path, page_index: int) -> tuple[float, float] | None:
    try:
        import fitz
    except Exception:
        return None
    try:
        document = fitz.open(pdf_path)
    except Exception:
        return None
    try:
        if page_index < 0 or page_index >= len(document):
            return None
        page = document[page_index]
        return float(page.rect.width), float(page.rect.height)
    finally:
        document.close()


def _caption_window_crop_bbox(pdf_path: Path, *, page_index: int, caption_bbox: list[float], visual_bbox: list[float] | None) -> list[float] | None:
    page_size = _pdf_page_size(pdf_path, page_index)
    if page_size is None or len(caption_bbox) < 4:
        return None
    page_width, page_height = page_size
    caption_left, caption_top, caption_right, _caption_bottom = [float(value) for value in caption_bbox[:4]]
    caption_width = max(1.0, caption_right - caption_left)
    page_margin = page_width * 0.055
    gutter = page_width * 0.04
    midpoint = page_width / 2.0

    use_full_width = caption_width >= page_width * 0.52
    if visual_bbox is not None and len(visual_bbox) >= 4:
        visual_width = max(0.0, float(visual_bbox[2]) - float(visual_bbox[0]))
        use_full_width = use_full_width or visual_width >= page_width * 0.46

    if use_full_width:
        left = page_margin
        right = page_width - page_margin
    elif (caption_left + caption_right) / 2.0 < midpoint:
        left = page_margin
        right = midpoint - gutter / 2.0
    else:
        left = midpoint + gutter / 2.0
        right = page_width - page_margin

    bottom = max(page_height * 0.08, caption_top - 6.0)
    top = max(page_height * 0.055, bottom - page_height * 0.52)
    if visual_bbox is not None and len(visual_bbox) >= 4:
        left = min(left, max(page_margin, float(visual_bbox[0]) - page_width * 0.04))
        right = max(right, min(page_width - page_margin, float(visual_bbox[2]) + page_width * 0.04))
        top = min(top, max(page_height * 0.04, float(visual_bbox[1]) - page_height * 0.035))
        bottom = max(bottom, min(caption_top - 2.0, float(visual_bbox[3]) + page_height * 0.035))

    if right - left < 90 or bottom - top < 80:
        return None
    return [left, top, right, bottom]


def _render_pdf_figure_crop(pdf_path: Path, output_path: Path, *, page_index: int, crop_bbox: list[float], tight: bool = False) -> bool:
    try:
        import fitz
    except Exception:
        return False
    if not pdf_path.exists() or not pdf_path.is_file():
        return False
    try:
        document = fitz.open(pdf_path)
    except Exception:
        return False
    try:
        if page_index < 0 or page_index >= len(document):
            return False
        page = document[page_index]
        page_rect = page.rect
        if tight:
            padding_x = float(page_rect.width) * 0.012
            padding_top = float(page_rect.height) * 0.006
            padding_bottom = float(page_rect.height) * 0.006
        else:
            padding_x = float(page_rect.width) * 0.06
            padding_top = float(page_rect.height) * 0.025
            padding_bottom = float(page_rect.height) * 0.01
        left = max(0.0, float(crop_bbox[0]) - padding_x)
        top = max(0.0, float(crop_bbox[1]) - padding_top)
        right = min(float(page_rect.width), float(crop_bbox[2]) + padding_x)
        bottom = min(float(page_rect.height), float(crop_bbox[3]) + padding_bottom)
        if right - left < 80 or bottom - top < 80:
            return False
        clip = fitz.Rect(left, top, right, bottom)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2.4, 2.4), clip=clip, alpha=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(output_path)
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception:
        return False
    finally:
        document.close()


def _can_direct_visual_crop(visual_bbox: list[float] | None, caption_bbox: list[float]) -> bool:
    if visual_bbox is None or len(visual_bbox) < 4 or len(caption_bbox) < 4:
        return False
    visual_width = max(0.0, float(visual_bbox[2]) - float(visual_bbox[0]))
    visual_height = max(0.0, float(visual_bbox[3]) - float(visual_bbox[1]))
    caption_width = max(1.0, float(caption_bbox[2]) - float(caption_bbox[0]))
    return visual_width >= caption_width * 0.42 and visual_height >= 55.0


def pdf_figure_crop_candidates(db_path: Path, paper_key: str, *, source_dir: Path | None = None) -> list[LayoutVisualCandidate]:
    init_db(db_path)
    with connect(db_path) as conn:
        latest = _latest_layout_run(conn, paper_key)
        if latest is None:
            return []
        pdf_path = _paper_pdf_path(conn, paper_key)
        if pdf_path is None:
            return []
        caption_rows = _figure_caption_crop_rows(conn, paper_key, int(latest["id"]))

    output_root = source_dir if source_dir is not None and source_dir.exists() and source_dir.is_dir() else pdf_path.parent
    output_dir = output_root / "blog-assets" / "covers"
    candidates: list[LayoutVisualCandidate] = []
    for row in caption_rows:
        crop_method = str(row.get("crop_method") or "caption_window")
        visual_bbox = row.get("crop_bbox") if isinstance(row.get("crop_bbox"), list) else None
        caption_bbox = list(row["bbox"])
        if crop_method in {"figure_bbox", "fragmented_layers"} and _can_direct_visual_crop(visual_bbox, caption_bbox):
            crop_bbox = visual_bbox
        else:
            crop_method = "caption_window"
            crop_bbox = _caption_window_crop_bbox(
                pdf_path,
                page_index=int(row["page_index"]),
                caption_bbox=caption_bbox,
                visual_bbox=visual_bbox,
            )
        if crop_bbox is None:
            continue
        digest = hashlib.sha256(
            f"{paper_key}:{row['page_index']}:{row['block_index']}:{row['caption']}:{crop_bbox}:{crop_method}:v9".encode("utf-8")
        ).hexdigest()[:12]
        output_path = output_dir / f"figure-{int(row['figure_number']):02d}-pdf-crop-{digest}.png"
        if not output_path.exists() or output_path.stat().st_size == 0:
            if not _render_pdf_figure_crop(
                pdf_path,
                output_path,
                page_index=int(row["page_index"]),
                crop_bbox=crop_bbox,
                tight=crop_method in {"figure_bbox", "fragmented_layers"},
            ):
                continue
        confidence = 0.9 if crop_method in {"caption_window", "figure_bbox"} else 0.88
        if crop_method == "caption_window":
            source_reference = f"pdf page={int(row['page_index']) + 1} figure={row['figure_number']} caption_window"
        elif crop_method == "figure_bbox":
            source_reference = f"pdf page={int(row['page_index']) + 1} figure={row['figure_number']} figure_bbox"
        else:
            source_reference = f"pdf page={int(row['page_index']) + 1} figure={row['figure_number']} fragmented_layers={row['fragment_count']}"
        candidates.append(
            _score_candidate(
                LayoutVisualCandidate(
                    source_path=output_path.resolve(),
                    source_kind="pdf_figure_crop",
                    asset_kind="figure",
                    caption=str(row["caption"]),
                    source_reference=source_reference,
                    confidence=confidence,
                    page_index=int(row["page_index"]),
                    block_index=int(row["block_index"]),
                    dimensions=image_dimensions(output_path),
                )
            )
        )
    return sorted(candidates, key=lambda item: (item.score, item.source_path.name), reverse=True)


def source_visual_candidates(source_dir: Path) -> list[LayoutVisualCandidate]:
    candidates: list[LayoutVisualCandidate] = []
    figures_dir = source_dir / "figures"
    if figures_dir.exists() and figures_dir.is_dir():
        preferred = representative_image(figures_dir, source_tex=source_dir / "source.tex")
        for path in sorted(figures_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            confidence = 0.78 if preferred is not None and path.resolve() == preferred.resolve() else 0.64
            candidates.append(
                _score_candidate(
                    LayoutVisualCandidate(
                        source_path=path.resolve(),
                        source_kind="source_figure",
                        asset_kind="figure",
                        caption=path.stem.replace("_", " "),
                        source_reference=f"figures/{path.name}",
                        confidence=confidence,
                        dimensions=image_dimensions(path),
                    )
                )
            )
    return sorted(candidates, key=lambda item: (item.score, item.source_path.name), reverse=True)


def cover_fallback_candidates(source_dir: Path, names: tuple[str, ...]) -> list[LayoutVisualCandidate]:
    candidates: list[LayoutVisualCandidate] = []
    for filename in names:
        path = source_dir / filename
        if not path.exists() or not path.is_file():
            continue
        candidates.append(
            _score_candidate(
                LayoutVisualCandidate(
                    source_path=path.resolve(),
                    source_kind="cover_fallback",
                    asset_kind="cover",
                    caption=path.stem,
                    source_reference=filename,
                    confidence=0.34,
                    dimensions=image_dimensions(path),
                )
            )
        )
    return sorted(candidates, key=lambda item: (item.score, item.source_path.name), reverse=True)


def visual_candidates(
    db_path: Path,
    paper_key: str,
    *,
    source_dir: Path | None = None,
    cover_names: tuple[str, ...] = (),
) -> list[LayoutVisualCandidate]:
    candidates = list(layout_visual_candidates(db_path, paper_key))
    if source_dir is not None and source_dir.exists() and source_dir.is_dir():
        candidates.extend(pdf_figure_crop_candidates(db_path, paper_key, source_dir=source_dir))
        candidates.extend(source_visual_candidates(source_dir))
        candidates.extend(cover_fallback_candidates(source_dir, cover_names))
    else:
        candidates.extend(pdf_figure_crop_candidates(db_path, paper_key))
    return sorted(candidates, key=lambda item: (item.score, item.source_path.name), reverse=True)


def select_representative_visual(
    db_path: Path,
    paper_key: str,
    *,
    source_dir: Path | None = None,
    cover_names: tuple[str, ...] = (),
) -> LayoutVisualCandidate | None:
    candidates = visual_candidates(db_path, paper_key, source_dir=source_dir, cover_names=cover_names)
    return candidates[0] if candidates else None
