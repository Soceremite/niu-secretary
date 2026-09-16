from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
import urllib.request

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import sync_paperpipe, utc_now
from airesearch.providers import arxiv_id_from_input, is_conference_page, pdf_fallback_command
from airesearch.url_normalizer import (
    NormalizeCategory,
    normalize_url_raw,
    categorize_url,
)


@dataclass(frozen=True)
class ManifestItem:
    raw_input: str
    line_number: int


# A stalled download or LLM call inside papi must not wedge the whole ingest run.
PAPI_PRIMARY_TIMEOUT_S = 180
PAPI_FALLBACK_TIMEOUT_S = 600


@dataclass(frozen=True)
class BatchResult:
    total: int
    success: int
    failed: int
    duplicate: int
    skipped: int


def parse_manifest(path: Path) -> list[ManifestItem]:
    items: list[ManifestItem] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        items.append(ManifestItem(raw_input=value, line_number=line_number))
    return items


def known_source_exists(db_path: Path, raw_input: str) -> bool:
    if not db_path.exists():
        return False
    with connect(db_path) as conn:
        row = conn.execute(
            "select 1 from paper_sources where source_value = ? limit 1",
            (raw_input,),
        ).fetchone()
    return row is not None


def known_arxiv_id_exists(db_path: Path, arxiv_id: str) -> bool:
    """True when the arXiv id is already in paper sources or in a paper's ids/url.

    Sources store bare ids ("2407.21243", sometimes with a version suffix) while the
    approved manifest lists abs URLs, so an exact source match alone never dedupes.
    """
    if not arxiv_id or not db_path.exists():
        return False
    pattern = f"%{arxiv_id}%"
    with connect(db_path) as conn:
        row = conn.execute(
            "select 1 from paper_sources where source_value = ? or source_value like ? limit 1",
            (arxiv_id, pattern),
        ).fetchone()
        if row is not None:
            return True
        row = conn.execute(
            "select 1 from papers where ids_json like ? limit 1",
            (pattern,),
        ).fetchone()
    return row is not None


def paper_keys(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()
    with connect(db_path) as conn:
        return {row["paper_key"] for row in conn.execute("select paper_key from papers")}


def create_run(db_path: Path, manifest_path: Path, total: int) -> int:
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            insert into ingest_runs
                (manifest_path, total_items, started_at, status)
            values (?, ?, ?, ?)
            """,
            (str(manifest_path), total, utc_now(), "running"),
        )
        conn.commit()
        return int(cursor.lastrowid)


def create_item(db_path: Path, run_id: int, item: ManifestItem, status: str = "running") -> int:
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            insert into ingest_items
                (run_id, line_number, raw_input, status, started_at)
            values (?, ?, ?, ?, ?)
            """,
            (run_id, item.line_number, item.raw_input, status, utc_now()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_item(
    db_path: Path,
    item_id: int,
    *,
    status: str,
    resolved_paper_key: str | None = None,
    stdout: str = "",
    stderr: str = "",
    error: str = "",
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            update ingest_items
            set status = ?,
                resolved_paper_key = ?,
                stdout = ?,
                stderr = ?,
                error = ?,
                finished_at = ?
            where id = ?
            """,
            (status, resolved_paper_key, stdout, stderr, error, utc_now(), item_id),
        )
        conn.commit()


def finish_run(db_path: Path, run_id: int) -> BatchResult:
    with connect(db_path) as conn:
        counts = {
            row["status"]: row["count"]
            for row in conn.execute(
                """
                select status, count(*) as count
                from ingest_items
                where run_id = ?
                group by status
                """,
                (run_id,),
            )
        }
        result = BatchResult(
            total=sum(counts.values()),
            success=counts.get("success", 0),
            failed=counts.get("failed", 0),
            duplicate=counts.get("duplicate", 0),
            skipped=counts.get("skipped", 0),
        )
        conn.execute(
            """
            update ingest_runs
            set success_count = ?,
                failed_count = ?,
                duplicate_count = ?,
                skipped_count = ?,
                finished_at = ?,
                status = ?
            where id = ?
            """,
            (
                result.success,
                result.failed,
                result.duplicate,
                result.skipped,
                utc_now(),
                "success" if result.failed == 0 else "partial_failure",
                run_id,
            ),
        )
        conn.commit()
    return result


def run_batch_ingest(
    *,
    db_path: Path,
    paper_db_path: Path,
    manifest_path: Path,
    papi_executable: str,
    normalize_urls: bool = True,
    normalize_opener: Callable[[urllib.request.Request, float], str] | None = None,
    concurrency: int = 4,
) -> BatchResult:
    init_db(db_path)
    paper_db_path.mkdir(parents=True, exist_ok=True)
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db_path)
    items = parse_manifest(manifest_path)
    run_id = create_run(db_path, manifest_path, len(items))

    jobs: list[tuple[int, str, str | None, str]] = []
    for item in items:
        item_id = create_item(db_path, run_id, item)
        if known_source_exists(db_path, item.raw_input) or known_arxiv_id_exists(
            db_path, arxiv_id_from_input(item.raw_input)
        ):
            update_item(db_path, item_id, status="duplicate", resolved_paper_key=None)
            continue

        papi_input = item.raw_input
        norm_result = None
        if normalize_urls:
            norm_result = normalize_url_raw(item.raw_input, opener=normalize_opener)
            if norm_result.normalized is not None:
                papi_input = norm_result.normalized
            elif norm_result.category != NormalizeCategory.UNKNOWN:
                # Recognized pattern but couldn't resolve — skip with detail
                update_item(
                    db_path,
                    item_id,
                    status="failed",
                    error=f"url_normalizer_failed: method={norm_result.method} "
                    f"messages={'; '.join(norm_result.messages)}",
                )
                continue

        jobs.append(
            (
                item_id,
                papi_input,
                norm_result.method if norm_result and norm_result.method else None,
                item.raw_input,
            )
        )

    def run_papi(
        item_id: int, papi_input: str, normalizer_method: str | None, raw_input: str
    ) -> tuple[int, subprocess.CompletedProcess[str], str | None, bool]:
        env = os.environ.copy()
        env["PAPER_DB_PATH"] = str(paper_db_path)

        def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
            try:
                return subprocess.run(
                    command,
                    check=False,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired as exc:
                # A stalled download or LLM call inside papi must not wedge the whole run.
                def _as_text(value: object) -> str:
                    if isinstance(value, bytes):
                        return value.decode("utf-8", "ignore")
                    return str(value or "")

                return subprocess.CompletedProcess(
                    command,
                    124,
                    stdout=_as_text(exc.stdout),
                    stderr=f"papi timed out after {timeout}s",
                )

        completed = _run([papi_executable, "add", papi_input], PAPI_PRIMARY_TIMEOUT_S)
        used_fallback = False
        if completed.returncode != 0:
            # arXiv export API is rate-limited often enough that `papi add <id>` fails
            # outright; retry through the public PDF endpoint, which stays reachable.
            # Conference landing pages (CVPR/NeurIPS/ICLR/AAAI) have no arXiv version at
            # all — the unified fallback also maps their page → PDF (2026-09-16).
            # 会议页归一化后 papi_input 会是「抽出来的标题」，兜底必须拿原始 URL 才能 page→pdf
            fallback_value = raw_input if is_conference_page(raw_input) else papi_input
            fallback_command = pdf_fallback_command(papi_executable, fallback_value)
            if fallback_command is not None:
                completed = _run(fallback_command, PAPI_FALLBACK_TIMEOUT_S)
                used_fallback = completed.returncode == 0
        return (item_id, completed, normalizer_method, used_fallback)

    results: list[tuple[int, subprocess.CompletedProcess[str], str | None, bool]] = []
    max_workers = max(1, min(concurrency, len(jobs) or 1))
    if max_workers == 1:
        results = [run_papi(*job) for job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(run_papi, *job) for job in jobs]
            for future in as_completed(futures):
                results.append(future.result())

    any_success = False
    for item_id, completed, normalizer_method, used_fallback in sorted(results, key=lambda item: item[0]):
        stdout = completed.stdout or ""
        if used_fallback:
            stdout += "\n[arxiv-pdf-fallback] export API unavailable; ingested via papi add --pdf"
        if completed.returncode != 0:
            error_parts = [completed.stderr.strip() or f"papi exited with {completed.returncode}"]
            if normalizer_method:
                error_parts.insert(0, f"normalizer: {normalizer_method}")
            update_item(
                db_path,
                item_id,
                status="failed",
                stdout=stdout,
                stderr=completed.stderr,
                error=" | ".join(error_parts),
            )
            continue
        any_success = True
        update_item(
            db_path,
            item_id,
            status="success",
            resolved_paper_key=None,
            stdout=stdout,
            stderr=completed.stderr,
        )

    if any_success:
        sync_paperpipe(db_path=db_path, paper_db_path=paper_db_path)

    return finish_run(db_path, run_id)
