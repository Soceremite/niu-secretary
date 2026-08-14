from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.layout_parser import LayoutParseOutput, LayoutParserOptions, PARSER_NAME, PARSER_VERSION, parse_pdf_layout
from airesearch.paperpipe_sync import sha256_file, stable_json, utc_now


LAYOUT_ARTIFACT_GROUPS = {
    "layout_markdown": "markdown_files",
    "layout_content_list": "content_list_files",
    "layout_structure_json": "structure_json_files",
    "layout_debug_json": "debug_json_files",
    "layout_summary_json": "summary_files",
    "layout_asset": "assets",
}
EVIDENCE_BLOCK_TYPES = {"image", "chart", "table", "interline_equation"}


@dataclass(frozen=True)
class LayoutParseResult:
    paper_key: str
    run_id: int
    status: str
    output_dir: Path
    artifact_count: int = 0
    block_count: int = 0
    message: str = ""


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")
    return text or "paper"


def find_paper_pdf(conn: Any, paper_key: str) -> Path:
    artifact = conn.execute(
        """
        select path from paper_artifacts
        where paper_key = ? and artifact_type = 'paper_pdf'
        order by id desc
        limit 1
        """,
        (paper_key,),
    ).fetchone()
    if artifact and Path(str(artifact["path"])).exists():
        return Path(str(artifact["path"]))

    paper = conn.execute("select paper_dir from papers where paper_key = ?", (paper_key,)).fetchone()
    if paper is None:
        raise ValueError(f"unknown paper: {paper_key}")
    candidate = Path(str(paper["paper_dir"])) / "paper.pdf"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"paper PDF not found for {paper_key}")


def _insert_run(conn: Any, *, paper_key: str, input_pdf: Path, output_dir: Path) -> int:
    now = utc_now()
    cursor = conn.execute(
        """
        insert into paper_layout_runs (
            paper_key, provider, provider_version, backend, method, status,
            input_pdf_path, output_dir, started_at
        ) values (?, ?, ?, 'pymupdf', 'native', 'running', ?, ?, ?)
        """,
        (paper_key, PARSER_NAME, PARSER_VERSION, str(input_pdf), str(output_dir), now),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _latest_completed_run(conn: Any, paper_key: str) -> Any:
    return conn.execute(
        """
        select * from paper_layout_runs
        where paper_key = ? and provider = ? and provider_version = ? and status = 'completed'
        order by id desc
        limit 1
        """,
        (paper_key, PARSER_NAME, PARSER_VERSION),
    ).fetchone()


def _artifact_paths(result: LayoutParseOutput) -> dict[str, list[Path]]:
    return {
        artifact_type: [Path(path) for path in getattr(result, attr)]
        for artifact_type, attr in LAYOUT_ARTIFACT_GROUPS.items()
    }


def _record_artifacts(conn: Any, paper_key: str, result: LayoutParseOutput) -> tuple[int, dict[str, list[str]]]:
    now = utc_now()
    artifact_json: dict[str, list[str]] = {}
    artifact_count = 0
    for artifact_type, paths in _artifact_paths(result).items():
        artifact_json[artifact_type] = [str(path) for path in paths]
        for path in paths:
            if not path.exists() or not path.is_file():
                continue
            stat = path.stat()
            conn.execute(
                """
                insert into paper_artifacts (
                    paper_key, artifact_type, path, sha256, size_bytes, updated_at
                ) values (?, ?, ?, ?, ?, ?)
                on conflict(paper_key, artifact_type, path) do update set
                    sha256 = excluded.sha256,
                    size_bytes = excluded.size_bytes,
                    updated_at = excluded.updated_at
                """,
                (paper_key, artifact_type, str(path), sha256_file(path), stat.st_size, now),
            )
            artifact_count += 1
    return artifact_count, artifact_json


def _collect_text(value: Any) -> str:
    chunks: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                chunks.append(content.strip())
            for key in ("blocks", "lines", "spans"):
                visit(item.get(key))
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return " ".join(chunks)[:4000]


def _collect_asset_path(value: Any) -> str:
    if isinstance(value, dict):
        image_path = value.get("image_path")
        if isinstance(image_path, str) and image_path:
            return image_path
        for key in ("blocks", "lines", "spans"):
            nested = _collect_asset_path(value.get(key))
            if nested:
                return nested
    elif isinstance(value, list):
        for item in value:
            nested = _collect_asset_path(item)
            if nested:
                return nested
    return ""


def _iter_structure_blocks(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        return []

    records: list[dict[str, Any]] = []
    for page_offset, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        page_index = int(
            page.get("page_index")
            if isinstance(page.get("page_index"), int)
            else page.get("page_idx")
            if isinstance(page.get("page_idx"), int)
            else page_offset
        )
        page_blocks = page.get("blocks") if isinstance(page.get("blocks"), list) else []
        for block_offset, block in enumerate(page_blocks):
            if not isinstance(block, dict):
                continue
            records.append(
                {
                    "page_index": page_index,
                    "block_index": int(block.get("block_index") if isinstance(block.get("block_index"), int) else block_offset),
                    "block_type": str(block.get("type") or "unknown"),
                    "bbox": block.get("bbox") if isinstance(block.get("bbox"), list) else [],
                    "text": str(block.get("text") or _collect_text(block)),
                    "asset_path": str(block.get("asset_path") or _collect_asset_path(block)),
                    "metadata": {
                        "source_path": str(path),
                        **(_json_loads(stable_json(block.get("metadata") or {}), {}) if isinstance(block.get("metadata"), dict) else {}),
                        "keys": sorted(str(key) for key in block.keys()),
                    },
                }
            )
    return records


def _record_blocks(conn: Any, paper_key: str, run_id: int, structure_json_files: list[Path]) -> tuple[int, dict[str, int]]:
    now = utc_now()
    stats: dict[str, int] = {}
    count = 0
    conn.execute("delete from paper_layout_blocks where run_id = ?", (run_id,))
    for structure_path in structure_json_files:
        for block in _iter_structure_blocks(structure_path):
            block_type = str(block["block_type"])
            stats[block_type] = stats.get(block_type, 0) + 1
            conn.execute(
                """
                insert into paper_layout_blocks (
                    paper_key, run_id, page_index, block_index, block_type,
                    bbox_json, text, asset_path, metadata_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_key,
                    run_id,
                    int(block["page_index"]),
                    int(block["block_index"]),
                    block_type,
                    stable_json(block["bbox"]),
                    str(block["text"]),
                    str(block["asset_path"]),
                    stable_json(block["metadata"]),
                    now,
                ),
            )
            count += 1
    return count, stats


def _load_summary(summary_files: list[Path]) -> dict[str, Any]:
    for path in summary_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _block_payload(row: Any) -> dict[str, Any]:
    metadata = _json_loads(row["metadata_json"], {})
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        **_row_to_dict(row),
        "bbox": _json_loads(row["bbox_json"], []),
        "metadata": metadata,
        "source_reference": str(
            metadata.get("source_reference")
            or f"page={int(row['page_index']) + 1} block={int(row['block_index'])}"
        ),
        "evidence_kind": str(metadata.get("evidence_kind") or ""),
        "evidence_confidence": metadata.get("evidence_confidence"),
    }


def _artifacts_by_type(rows: list[Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = _row_to_dict(row)
        artifact_type = str(item.get("artifact_type") or "")
        if not artifact_type:
            continue
        grouped.setdefault(artifact_type, []).append(item)
    return grouped


def _layout_capabilities(summary: dict[str, Any], block_counts: dict[str, int], artifacts_by_type: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ocr = summary.get("ocr") if isinstance(summary.get("ocr"), dict) else {}
    ocr_attempted = int(ocr.get("pages_attempted") or 0)
    ocr_succeeded = int(ocr.get("pages_succeeded") or 0)
    formula_ocr = summary.get("formula_ocr") if isinstance(summary.get("formula_ocr"), dict) else {}
    formula_eligible = int(formula_ocr.get("blocks_eligible") or 0)
    formula_succeeded = int(formula_ocr.get("blocks_succeeded") or 0)
    reading_order = summary.get("reading_order") if isinstance(summary.get("reading_order"), dict) else {}
    return {
        "parser": PARSER_NAME,
        "parser_version": PARSER_VERSION,
        "has_markdown": bool(artifacts_by_type.get("layout_markdown")),
        "has_content_list": bool(artifacts_by_type.get("layout_content_list")),
        "has_structure_json": bool(artifacts_by_type.get("layout_structure_json")),
        "has_assets": bool(artifacts_by_type.get("layout_asset")),
        "has_visual_blocks": any(block_counts.get(block_type, 0) > 0 for block_type in ("image", "chart", "table")),
        "has_captioned_visual_blocks": int(summary.get("captioned_visual_blocks") or 0) > 0,
        "has_structured_tables": int(summary.get("structured_table_blocks") or 0) > 0 or block_counts.get("table", 0) > 0,
        "has_geometry_tables": int(summary.get("geometry_table_blocks") or 0) > 0,
        "has_spanning_table_cells": int(summary.get("spanning_table_blocks") or 0) > 0,
        "has_text_fallback_tables": int(summary.get("text_fallback_table_blocks") or 0) > 0,
        "has_equations": int(summary.get("equation_blocks") or 0) > 0 or block_counts.get("interline_equation", 0) > 0,
        "has_evidence_blocks": int(summary.get("evidence_ready_blocks") or 0) > 0,
        "has_high_quality_evidence": int(summary.get("high_quality_evidence_blocks") or 0) > 0,
        "has_high_quality_tables": int(summary.get("high_quality_table_blocks") or 0) > 0,
        "has_high_quality_equations": int(summary.get("high_quality_equation_blocks") or 0) > 0,
        "has_reading_order": str(reading_order.get("method") or "") == "geometry_columns_v2",
        "has_multi_column_reading_order": int(reading_order.get("multi_column_pages") or 0) > 0,
        "has_caption_paired_reading_order": int(reading_order.get("caption_paired_blocks") or 0) > 0,
        "needs_reading_order_attention": int(reading_order.get("low_confidence_blocks") or 0) > 0,
        "ocr_available": bool(ocr.get("available")),
        "has_ocr_blocks": int(ocr.get("block_count") or 0) > 0,
        "needs_ocr_attention": summary.get("document_type") in {"scanned", "mixed"} and ocr_attempted > ocr_succeeded,
        "formula_ocr_configured": bool(formula_ocr.get("configured")),
        "has_formula_ocr": formula_succeeded > 0,
        "needs_formula_ocr_attention": formula_eligible > formula_succeeded,
    }


def parse_paper_layout(
    *,
    db_path: Path,
    paper_key: str,
    options: LayoutParserOptions,
    force: bool = False,
) -> LayoutParseResult:
    init_db(db_path)
    with connect(db_path) as conn:
        input_pdf = find_paper_pdf(conn, paper_key)
        if not force:
            latest = _latest_completed_run(conn, paper_key)
            if latest is not None:
                return LayoutParseResult(
                    paper_key=paper_key,
                    run_id=int(latest["id"]),
                    status="skipped",
                    output_dir=Path(str(latest["output_dir"])),
                    message="latest completed layout run reused",
                )
        output_dir = options.output_dir / _slug(paper_key) / utc_now().replace(":", "").replace("+", "Z")
        run_options = LayoutParserOptions(
            output_dir=output_dir,
            max_pages=options.max_pages,
            ocr_mode=options.ocr_mode,
            ocr_languages=options.ocr_languages,
            ocr_dpi=options.ocr_dpi,
            ocr_executable=options.ocr_executable,
            ocr_min_text_chars=options.ocr_min_text_chars,
            formula_ocr_mode=options.formula_ocr_mode,
            formula_ocr_dpi=options.formula_ocr_dpi,
            formula_ocr_min_confidence=options.formula_ocr_min_confidence,
        )
        run_id = _insert_run(conn, paper_key=paper_key, input_pdf=input_pdf, output_dir=output_dir)

    try:
        layout_result = parse_pdf_layout(input_pdf, run_options)
        with connect(db_path) as conn:
            artifact_count, artifact_json = _record_artifacts(conn, paper_key, layout_result)
            block_count, block_stats = _record_blocks(conn, paper_key, run_id, layout_result.structure_json_files)
            conn.execute(
                """
                update paper_layout_runs
                set status = 'completed', artifact_json = ?, stats_json = ?, finished_at = ?
                where id = ?
                """,
                (
                    stable_json(artifact_json),
                    stable_json(
                        {
                            "blocks": block_stats,
                            "block_count": block_count,
                            "artifact_count": artifact_count,
                            "summary": _load_summary(layout_result.summary_files),
                        }
                    ),
                    utc_now(),
                    run_id,
                ),
            )
            conn.commit()
        return LayoutParseResult(
            paper_key=paper_key,
            run_id=run_id,
            status="completed",
            output_dir=output_dir,
            artifact_count=artifact_count,
            block_count=block_count,
            message="layout parse completed",
        )
    except Exception as exc:
        with connect(db_path) as conn:
            conn.execute(
                """
                update paper_layout_runs
                set status = 'failed', error = ?, finished_at = ?
                where id = ?
                """,
                (str(exc)[:4000], utc_now(), run_id),
            )
            conn.commit()
        raise


def parse_missing_layouts(*, db_path: Path, options: LayoutParserOptions, limit: int = 10) -> list[LayoutParseResult]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select p.paper_key
            from papers p
            left join paper_layout_runs r
              on r.paper_key = p.paper_key and r.provider = ? and r.provider_version = ? and r.status = 'completed'
            where r.id is null
            order by p.updated_at desc, p.paper_key
            limit ?
            """,
            (PARSER_NAME, PARSER_VERSION, limit),
        ).fetchall()
    return [parse_paper_layout(db_path=db_path, paper_key=str(row["paper_key"]), options=options) for row in rows]


def layout_detail(db_path: Path, paper_key: str) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        latest = conn.execute(
            """
            select * from paper_layout_runs
            where paper_key = ? and provider = ?
            order by id desc
            limit 1
            """,
            (paper_key, PARSER_NAME),
        ).fetchone()
        latest_run_id = int(latest["id"]) if latest is not None else None
        artifacts = conn.execute(
            """
            select * from paper_artifacts
            where paper_key = ? and artifact_type like 'layout_%'
            order by artifact_type, path
            """,
            (paper_key,),
        ).fetchall()
        if latest_run_id is not None:
            counts = conn.execute(
                """
                select block_type, count(*) as count
                from paper_layout_blocks
                where paper_key = ? and run_id = ?
                group by block_type
                order by block_type
                """,
                (paper_key, latest_run_id),
            ).fetchall()
            block_rows = conn.execute(
                """
                select id, page_index, block_index, block_type, bbox_json, text, asset_path, metadata_json
                from paper_layout_blocks
                where paper_key = ? and run_id = ?
                order by page_index, block_index
                limit 220
                """,
                (paper_key, latest_run_id),
            ).fetchall()
        else:
            counts = []
            block_rows = []

    latest_run = _row_to_dict(latest)
    if latest_run:
        latest_run["artifact"] = _json_loads(latest_run.get("artifact_json"), {})
        latest_run["stats"] = _json_loads(latest_run.get("stats_json"), {})
    summary = {}
    if isinstance(latest_run.get("stats"), dict):
        maybe_summary = latest_run["stats"].get("summary")
        if isinstance(maybe_summary, dict):
            summary = maybe_summary
    block_counts = {str(row["block_type"]): int(row["count"]) for row in counts}
    artifact_groups = _artifacts_by_type(list(artifacts))
    parsed_blocks = [_block_payload(row) for row in block_rows]
    evidence_blocks = [
        block
        for block in parsed_blocks
        if block["block_type"] in EVIDENCE_BLOCK_TYPES or block["evidence_kind"]
    ][:80]
    return {
        "api_version": "layout-v2",
        "paper_key": paper_key,
        "latest_run": latest_run,
        "artifacts": [_row_to_dict(row) for row in artifacts],
        "artifacts_by_type": artifact_groups,
        "summary": summary,
        "block_counts": block_counts,
        "capabilities": _layout_capabilities(summary, block_counts, artifact_groups),
        "sample_blocks": parsed_blocks[:20],
        "evidence_blocks": evidence_blocks,
        "limits": {"sample_blocks": 20, "evidence_blocks": 80},
    }
