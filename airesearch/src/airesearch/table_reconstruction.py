from __future__ import annotations

import re
from statistics import median
from typing import Any, Iterable


NUMBER_RE = re.compile(r"(?:^|\s)[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?:\s?(?:%|ms|s|gb|mb|k|m|b))?(?:\s|$)", re.I)


def _as_bbox(value: Any) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) < 4:
        return []
    try:
        bbox = [float(item) for item in value[:4]]
    except (TypeError, ValueError):
        return []
    if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        return []
    return bbox


def _normalize_word(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        bbox = _as_bbox(value.get("bbox"))
        text = str(value.get("text") or "").strip()
    elif isinstance(value, (list, tuple)) and len(value) >= 5:
        bbox = _as_bbox(value[:4])
        text = str(value[4] or "").strip()
    else:
        return None
    if not bbox or not text:
        return None
    return {
        "bbox": bbox,
        "text": text,
        "x0": bbox[0],
        "y0": bbox[1],
        "x1": bbox[2],
        "y1": bbox[3],
        "cx": (bbox[0] + bbox[2]) / 2,
        "cy": (bbox[1] + bbox[3]) / 2,
        "height": bbox[3] - bbox[1],
    }


def _inside_table(word: dict[str, Any], table_bbox: list[float]) -> bool:
    return table_bbox[0] - 1 <= word["cx"] <= table_bbox[2] + 1 and table_bbox[1] - 1 <= word["cy"] <= table_bbox[3] + 1


def _join_words(words: list[dict[str, Any]]) -> str:
    result = ""
    for word in sorted(words, key=lambda item: (item["x0"], item["y0"])):
        token = str(word["text"])
        if not result or token[:1] in ",.;:%!?)]}" or result[-1:] in "([{/$":
            result += token
        else:
            result += " " + token
    return result.strip()


def _bbox_union(items: Iterable[dict[str, Any]]) -> list[float]:
    values = list(items)
    return [
        min(item["x0"] for item in values),
        min(item["y0"] for item in values),
        max(item["x1"] for item in values),
        max(item["y1"] for item in values),
    ]


def _cluster_visual_rows(words: list[dict[str, Any]], median_height: float) -> list[list[dict[str, Any]]]:
    tolerance = max(2.5, median_height * 0.58)
    rows: list[dict[str, Any]] = []
    for word in sorted(words, key=lambda item: (item["cy"], item["x0"])):
        best_row: dict[str, Any] | None = None
        best_distance = float("inf")
        for row in rows[-3:]:
            vertical_overlap = max(0.0, min(row["y1"], word["y1"]) - max(row["y0"], word["y0"]))
            overlap_ratio = vertical_overlap / max(1.0, min(row["height"], word["height"]))
            distance = abs(row["cy"] - word["cy"])
            if (distance <= tolerance or overlap_ratio >= 0.42) and distance < best_distance:
                best_row = row
                best_distance = distance
        if best_row is None:
            rows.append(
                {
                    "words": [word],
                    "y0": word["y0"],
                    "y1": word["y1"],
                    "cy": word["cy"],
                    "height": word["height"],
                }
            )
            continue
        best_row["words"].append(word)
        best_row["y0"] = min(best_row["y0"], word["y0"])
        best_row["y1"] = max(best_row["y1"], word["y1"])
        best_row["cy"] = median(item["cy"] for item in best_row["words"])
        best_row["height"] = best_row["y1"] - best_row["y0"]
    rows.sort(key=lambda row: (row["cy"], min(word["x0"] for word in row["words"])))
    return [sorted(row["words"], key=lambda item: item["x0"]) for row in rows]


def _segment_rows(
    rows: list[list[dict[str, Any]]],
    *,
    median_height: float,
    median_character_width: float,
) -> list[list[dict[str, Any]]]:
    gap_threshold = max(2.5, median_height * 0.52, median_character_width * 1.35)
    segmented_rows: list[list[dict[str, Any]]] = []
    for row_index, words in enumerate(rows):
        groups: list[list[dict[str, Any]]] = []
        for word in words:
            if not groups or word["x0"] - groups[-1][-1]["x1"] > gap_threshold:
                groups.append([word])
            else:
                groups[-1].append(word)
        segments: list[dict[str, Any]] = []
        for group in groups:
            bbox = _bbox_union(group)
            segments.append(
                {
                    "row": row_index,
                    "bbox": bbox,
                    "text": _join_words(group),
                    "x0": bbox[0],
                    "y0": bbox[1],
                    "x1": bbox[2],
                    "y1": bbox[3],
                    "cx": (bbox[0] + bbox[2]) / 2,
                }
            )
        segmented_rows.append(segments)
    return segmented_rows


def _segment_anchor_x(segment: dict[str, Any]) -> float:
    if "anchor_x" in segment:
        return float(segment["anchor_x"])
    text = str(segment.get("text") or "").strip()
    alphabetic = len(re.findall(r"[A-Za-z]", text))
    if NUMBER_RE.search(text) and alphabetic <= 2:
        return float(segment["cx"])
    return float(segment["cx"])


def _infer_column_anchors(
    segmented_rows: list[list[dict[str, Any]]],
    *,
    table_width: float,
    median_height: float,
) -> tuple[list[float], list[int], float]:
    tolerance = max(5.0, min(24.0, max(median_height * 1.1, table_width * 0.022)))
    all_segments = [segment for row in segmented_rows for segment in row]
    for segment in all_segments:
        text = str(segment.get("text") or "").strip()
        alphabetic = len(re.findall(r"[A-Za-z]", text))
        if NUMBER_RE.search(text) and alphabetic <= 2:
            segment["anchor_x"] = float(segment["cx"])
            continue
        x0_rows = {
            int(other["row"])
            for other in all_segments
            if abs(float(other["x0"]) - float(segment["x0"])) <= tolerance
        }
        center_rows = {
            int(other["row"])
            for other in all_segments
            if abs(float(other["cx"]) - float(segment["cx"])) <= tolerance
        }
        segment["anchor_x"] = float(segment["x0"] if len(x0_rows) > len(center_rows) else segment["cx"])
    candidates = [segment for row in segmented_rows if len(row) >= 2 for segment in row]
    if len(candidates) < 4:
        candidates = [segment for row in segmented_rows for segment in row]
    clusters: list[dict[str, Any]] = []
    for segment in sorted(candidates, key=_segment_anchor_x):
        anchor_x = _segment_anchor_x(segment)
        target = next(
            (
                cluster
                for cluster in clusters
                if abs(anchor_x - median(cluster["centers"])) <= tolerance
            ),
            None,
        )
        if target is None:
            clusters.append({"centers": [anchor_x], "rows": {segment["row"]}})
        else:
            target["centers"].append(anchor_x)
            target["rows"].add(segment["row"])
    supported = [cluster for cluster in clusters if len(cluster["rows"]) >= 2]
    supported.sort(key=lambda cluster: median(cluster["centers"]))
    return (
        [float(median(cluster["centers"])) for cluster in supported],
        [len(cluster["rows"]) for cluster in supported],
        tolerance,
    )


def _infer_header_row_count(rows: list[list[str]], cells: list[dict[str, Any]]) -> int:
    if len(rows) < 2:
        return 0
    for row_index, row in enumerate(rows[: min(3, len(rows) - 1)]):
        values = [value for value in row if value.strip()]
        if not values:
            continue
        numeric_ratio = sum(1 for value in values if NUMBER_RE.search(value)) / len(values)
        if numeric_ratio >= 0.34:
            return max(1, row_index)
    first_row_spans = any(cell["row"] == 0 and cell["column_span"] > 1 for cell in cells)
    if first_row_spans and len(rows) >= 3:
        return 2
    return 1


def reconstruct_table_from_words(words: Iterable[Any], table_bbox: Any) -> dict[str, Any]:
    bbox = _as_bbox(table_bbox)
    if not bbox:
        return {}
    normalized = [word for value in words if (word := _normalize_word(value)) is not None]
    normalized = [word for word in normalized if _inside_table(word, bbox)]
    if len(normalized) < 4:
        return {}

    median_height = float(median(word["height"] for word in normalized))
    character_widths = [
        (word["x1"] - word["x0"]) / max(1, len(str(word["text"])))
        for word in normalized
        if word["x1"] > word["x0"]
    ]
    median_character_width = float(median(character_widths)) if character_widths else median_height * 0.45
    visual_rows = _cluster_visual_rows(normalized, median_height)
    if len(visual_rows) < 2:
        return {}
    segmented_rows = _segment_rows(
        visual_rows,
        median_height=median_height,
        median_character_width=median_character_width,
    )
    anchors, column_support, column_tolerance = _infer_column_anchors(
        segmented_rows,
        table_width=bbox[2] - bbox[0],
        median_height=median_height,
    )
    if len(anchors) < 2:
        return {}

    cells: list[dict[str, Any]] = []
    rows = [["" for _anchor in anchors] for _row in segmented_rows]
    alignment_scores: list[float] = []
    for row_index, segments in enumerate(segmented_rows):
        assigned: dict[int, dict[str, Any]] = {}
        for segment in segments:
            covered = [
                index
                for index, anchor in enumerate(anchors)
                if segment["x0"] - column_tolerance * 0.25 <= anchor <= segment["x1"] + column_tolerance * 0.25
            ]
            can_span = len(covered) >= 2 and len(segments) < len(anchors)
            if can_span:
                column = covered[0]
                column_span = covered[-1] - covered[0] + 1
                cell_confidence = 0.86
            else:
                segment_anchor = _segment_anchor_x(segment)
                column = min(range(len(anchors)), key=lambda index: abs(segment_anchor - anchors[index]))
                column_span = 1
                distance = abs(segment_anchor - anchors[column])
                cell_confidence = max(0.55, min(0.99, 1.0 - distance / max(1.0, column_tolerance * 2.5)))
            if column in assigned:
                previous = assigned[column]
                previous["text"] = f'{previous["text"]} {segment["text"]}'.strip()
                previous["bbox"] = [
                    min(previous["bbox"][0], segment["x0"]),
                    min(previous["bbox"][1], segment["y0"]),
                    max(previous["bbox"][2], segment["x1"]),
                    max(previous["bbox"][3], segment["y1"]),
                ]
                previous["confidence"] = round(min(previous["confidence"], cell_confidence), 4)
                continue
            assigned[column] = {
                "row": row_index,
                "column": column,
                "row_span": 1,
                "column_span": column_span,
                "bbox": [round(value, 3) for value in segment["bbox"]],
                "text": segment["text"],
                "confidence": round(cell_confidence, 4),
            }
        for column, cell in assigned.items():
            rows[row_index][column] = cell["text"]
            cells.append(cell)
            alignment_scores.append(float(cell["confidence"]))

    active_columns = [
        column
        for column in range(len(anchors))
        if any(str(row[column]).strip() for row in rows)
    ]
    if 2 <= len(active_columns) < len(anchors):
        column_map = {old: new for new, old in enumerate(active_columns)}
        rows = [[row[column] for column in active_columns] for row in rows]
        for cell in cells:
            old_column = int(cell["column"])
            old_span = max(1, int(cell.get("column_span") or 1))
            cell["column"] = column_map[old_column]
            covered = [
                column for column in active_columns if old_column <= column < old_column + old_span
            ]
            cell["column_span"] = max(1, len(covered))
        anchors = [anchors[column] for column in active_columns]
        column_support = [column_support[column] for column in active_columns]

    multi_cell_ratio = sum(1 for row in rows if sum(bool(value) for value in row) >= 2) / len(rows)
    support_ratio = sum(column_support) / max(1, len(anchors) * len(rows))
    occupancy = len(cells) / max(1, len(rows) * len(anchors))
    alignment = sum(alignment_scores) / max(1, len(alignment_scores))
    confidence = 0.42
    confidence += min(0.2, alignment * 0.2)
    confidence += min(0.14, multi_cell_ratio * 0.14)
    confidence += min(0.14, support_ratio * 0.14)
    confidence += min(0.08, len(rows) / 4 * 0.08)
    confidence += min(0.08, occupancy * 0.08)
    confidence = round(max(0.0, min(0.96, confidence)), 4)

    reasons = ["word-bbox-geometry", "repeated-column-anchors"]
    if multi_cell_ratio >= 0.7:
        reasons.append("stable-multi-cell-rows")
    if occupancy < 0.75:
        reasons.append("sparse-cells-preserved")
    has_spanning_cells = any(cell["column_span"] > 1 or cell["row_span"] > 1 for cell in cells)
    if has_spanning_cells:
        reasons.append("spanning-cells-inferred")

    inner_boundaries = [(anchors[index] + anchors[index + 1]) / 2 for index in range(len(anchors) - 1)]
    boundaries = [bbox[0], *inner_boundaries, bbox[2]]
    return {
        "table_rows": rows,
        "table_cells": sorted(cells, key=lambda cell: (cell["row"], cell["column"])),
        "row_count": len(rows),
        "column_count": len(anchors),
        "header_row_count": _infer_header_row_count(rows, cells),
        "column_anchors": [round(value, 3) for value in anchors],
        "column_boundaries": [round(value, 3) for value in boundaries],
        "has_spanning_cells": has_spanning_cells,
        "reconstruction_method": "word_geometry_v2",
        "reconstruction_confidence": confidence,
        "reconstruction_reasons": reasons,
    }
