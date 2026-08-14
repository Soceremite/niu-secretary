from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from airesearch.db import connect
from airesearch.layout_parse import parse_paper_layout
from airesearch.layout_parser import LayoutParserOptions


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def _free_bytes(path: Path) -> int:
    stats = os.statvfs(path)
    return stats.f_bavail * stats.f_frsize


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _completed_keys(log_path: Path) -> set[str]:
    if not log_path.exists():
        return set()
    completed: set[str] = set()
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "paper" and row.get("status") == "completed" and row.get("pruned"):
            completed.add(str(row.get("paper_key") or ""))
    return completed


def _run_snapshot(db_path: Path, paper_key: str) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "select id, status, output_dir from paper_layout_runs where paper_key = ? order by id",
                (paper_key,),
            ).fetchall()
        ]


def _validate_run(db_path: Path, paper_key: str, run_id: int, output_dir: Path) -> dict[str, int]:
    with connect(db_path) as conn:
        run = conn.execute(
            "select status, stats_json from paper_layout_runs where id = ? and paper_key = ?",
            (run_id, paper_key),
        ).fetchone()
        block_count = int(
            conn.execute(
                "select count(*) as count from paper_layout_blocks where run_id = ?",
                (run_id,),
            ).fetchone()["count"]
        )
    if run is None or str(run["status"]) != "completed":
        raise RuntimeError(f"layout run {run_id} did not complete")
    if not output_dir.exists() or not output_dir.is_dir():
        raise RuntimeError(f"layout output is missing: {output_dir}")
    stats = _json(str(run["stats_json"] or "{}"), {})
    summary = stats.get("summary") if isinstance(stats, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    page_count = int(summary.get("page_count") or 0)
    if page_count <= 0 or block_count <= 0:
        raise RuntimeError(f"layout output is empty: pages={page_count} blocks={block_count}")
    return {
        "page_count": page_count,
        "block_count": block_count,
        "equation_blocks": int(summary.get("equation_blocks") or 0),
        "structured_table_blocks": int(summary.get("structured_table_blocks") or 0),
    }


def _prune_old_runs(
    db_path: Path,
    paper_key: str,
    current_run_id: int,
    current_output_dir: Path,
    layout_root: Path,
) -> tuple[int, int, int]:
    with connect(db_path) as conn:
        run_rows = conn.execute(
            "select id, output_dir from paper_layout_runs where paper_key = ? and id <> ?",
            (paper_key, current_run_id),
        ).fetchall()
        artifact_rows = conn.execute(
            "select id, path from paper_artifacts where paper_key = ? and artifact_type like 'layout_%'",
            (paper_key,),
        ).fetchall()
        stale_artifact_ids = [
            int(row["id"])
            for row in artifact_rows
            if not Path(str(row["path"] or "")).resolve(strict=False).is_relative_to(
                current_output_dir.resolve(strict=False)
            )
        ]
        if stale_artifact_ids:
            conn.executemany("delete from paper_artifacts where id = ?", [(item,) for item in stale_artifact_ids])
        old_run_ids = [int(row["id"]) for row in run_rows]
        if old_run_ids:
            conn.executemany("delete from paper_layout_runs where id = ?", [(item,) for item in old_run_ids])
        conn.commit()

    removed_dirs = 0
    for row in run_rows:
        old_dir = Path(str(row["output_dir"] or ""))
        if not old_dir.is_absolute():
            old_dir = Path.cwd() / old_dir
        if old_dir == current_output_dir or not _inside(old_dir, layout_root):
            continue
        if old_dir.exists() and old_dir.is_dir():
            shutil.rmtree(old_dir)
            removed_dirs += 1
    return len(old_run_ids), len(stale_artifact_ids), removed_dirs


def _cleanup_failed_run(db_path: Path, paper_key: str, previous_run_ids: set[int], layout_root: Path) -> None:
    with connect(db_path) as conn:
        failed_rows = conn.execute(
            "select id, output_dir from paper_layout_runs where paper_key = ? and status = 'failed'",
            (paper_key,),
        ).fetchall()
        failed_rows = [row for row in failed_rows if int(row["id"]) not in previous_run_ids]
        for row in failed_rows:
            failed_dir = Path(str(row["output_dir"] or ""))
            conn.execute(
                "delete from paper_artifacts where paper_key = ? and artifact_type like 'layout_%' and path like ?",
                (paper_key, f"{failed_dir}%"),
            )
            conn.execute("delete from paper_layout_runs where id = ?", (int(row["id"]),))
        conn.commit()
    for row in failed_rows:
        failed_dir = Path(str(row["output_dir"] or ""))
        if not failed_dir.is_absolute():
            failed_dir = Path.cwd() / failed_dir
        if _inside(failed_dir, layout_root) and failed_dir.exists() and failed_dir.is_dir():
            shutil.rmtree(failed_dir)


def _write_record(handle: Any, record: dict[str, Any]) -> None:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    handle.write(line + "\n")
    handle.flush()
    print(line, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Force-reparse every paper layout with bounded disk usage.")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--layout-output-dir", type=Path, required=True)
    parser.add_argument("--log-dir", type=Path, required=True)
    parser.add_argument("--min-free-mb", type=int, default=700)
    args = parser.parse_args()

    db_path = args.db.resolve()
    layout_root = args.layout_output_dir.resolve()
    log_dir = args.log_dir.resolve()
    layout_root.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "rerun.jsonl"
    summary_path = log_dir / "summary.json"
    completed = _completed_keys(log_path)

    with connect(db_path) as conn:
        paper_keys = [
            str(row["paper_key"])
            for row in conn.execute("select paper_key from papers order by updated_at desc, paper_key").fetchall()
        ]

    options = LayoutParserOptions(
        output_dir=layout_root,
        max_pages=None,
        ocr_mode=os.environ.get("AIRESEARCH_LAYOUT_OCR_MODE", "auto"),
        ocr_languages=os.environ.get("AIRESEARCH_LAYOUT_OCR_LANGUAGES", "eng+chi_sim"),
        ocr_dpi=int(os.environ.get("AIRESEARCH_LAYOUT_OCR_DPI", "220")),
        ocr_executable=os.environ.get("AIRESEARCH_LAYOUT_OCR_EXECUTABLE", "tesseract"),
        formula_ocr_mode=os.environ.get("AIRESEARCH_FORMULA_OCR_MODE", "auto"),
        formula_ocr_dpi=int(os.environ.get("AIRESEARCH_FORMULA_OCR_DPI", "260")),
        formula_ocr_min_confidence=float(os.environ.get("AIRESEARCH_FORMULA_OCR_MIN_CONFIDENCE", "0.7")),
    )
    started = time.time()
    succeeded = len(completed)
    failed = 0
    with log_path.open("a", encoding="utf-8") as log:
        _write_record(
            log,
            {
                "event": "start",
                "paper_count": len(paper_keys),
                "already_completed": len(completed),
                "ocr_mode": options.ocr_mode,
                "formula_ocr_mode": options.formula_ocr_mode,
                "free_bytes": _free_bytes(layout_root),
            },
        )
        for index, paper_key in enumerate(paper_keys, start=1):
            if paper_key in completed:
                continue
            free_bytes = _free_bytes(layout_root)
            if free_bytes < args.min_free_mb * 1024 * 1024:
                record = {
                    "event": "paper",
                    "index": index,
                    "total": len(paper_keys),
                    "paper_key": paper_key,
                    "status": "failed",
                    "error": f"free-space guard: {free_bytes} bytes",
                }
                _write_record(log, record)
                failed += 1
                break
            item_started = time.time()
            previous_runs = _run_snapshot(db_path, paper_key)
            previous_run_ids = {int(row["id"]) for row in previous_runs}
            try:
                result = parse_paper_layout(
                    db_path=db_path,
                    paper_key=paper_key,
                    options=options,
                    force=True,
                )
                validation = _validate_run(db_path, paper_key, result.run_id, result.output_dir.resolve())
                old_runs, stale_artifacts, removed_dirs = _prune_old_runs(
                    db_path,
                    paper_key,
                    result.run_id,
                    result.output_dir.resolve(),
                    layout_root,
                )
                record = {
                    "event": "paper",
                    "index": index,
                    "total": len(paper_keys),
                    "paper_key": paper_key,
                    "status": "completed",
                    "run_id": result.run_id,
                    "artifact_count": result.artifact_count,
                    **validation,
                    "output_dir": str(result.output_dir),
                    "old_runs_deleted": old_runs,
                    "stale_artifacts_deleted": stale_artifacts,
                    "old_dirs_deleted": removed_dirs,
                    "pruned": True,
                    "free_bytes": _free_bytes(layout_root),
                    "elapsed_seconds": round(time.time() - item_started, 3),
                }
                succeeded += 1
            except Exception as exc:
                _cleanup_failed_run(db_path, paper_key, previous_run_ids, layout_root)
                record = {
                    "event": "paper",
                    "index": index,
                    "total": len(paper_keys),
                    "paper_key": paper_key,
                    "status": "failed",
                    "error": str(exc)[:1000],
                    "traceback": traceback.format_exc(limit=8),
                    "elapsed_seconds": round(time.time() - item_started, 3),
                }
                failed += 1
            _write_record(log, record)

    summary = {
        "event": "summary",
        "paper_count": len(paper_keys),
        "succeeded": succeeded,
        "failed": failed,
        "elapsed_seconds": round(time.time() - started, 3),
        "free_bytes": _free_bytes(layout_root),
        "log_path": str(log_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    return 0 if failed == 0 and succeeded == len(paper_keys) else 2


if __name__ == "__main__":
    sys.exit(main())
