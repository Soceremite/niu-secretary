from __future__ import annotations

import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import traceback
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.launch_refresh import run_launch_refresh
from airesearch.layout_evidence_graph import extract_layout_evidence_graph, load_paper_evidence_graph
from airesearch.layout_parse import layout_detail as paper_layout_detail
from airesearch.layout_parse import parse_paper_layout
from airesearch.layout_parser import LayoutParserOptions
from airesearch.layout_service import visual_candidates
from airesearch.mvp_pipeline import run_mvp_pipeline
from airesearch.paper_blog import (
    DEFAULT_BLOG_MODEL,
    FixtureBlogProvider,
    OpenAICompatibleBlogProvider,
    blog_detail as paper_blog_detail,
    generate_and_publish_blog,
    hide_blog_post,
    rollback_blog_post,
)
from airesearch.paperpipe_sync import sync_paperpipe, utc_now
from airesearch.profiles import default_profiles
from airesearch.providers import ArxivProvider, GoogleScholarProvider, OpenAlexProvider, SemanticScholarProvider
from airesearch.research_bundle import export_report_bundle
from airesearch.research_site import export_report_site
from airesearch.static_publish import publish_static_site


FACT_TYPES = ("method", "claim", "limitation", "dataset", "benchmark")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
GITHUB_RE = re.compile(r"^https://github\.com/([^/\s]+)/([^/\s#?]+)", re.IGNORECASE)
JOB_STATUSES = ("queued", "running", "completed", "failed", "publish_failed", "canceled")
PROVIDER_NAMES = ("arxiv", "openalex", "semantic_scholar", "google_scholar")
DEFAULT_JOB_LIMIT = 40
PROFILE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
_WORKER_LOCK = threading.Lock()
_WORKER_THREAD: threading.Thread | None = None
_BLOG_PUBLISH_LOCK = threading.Lock()


@dataclass(frozen=True)
class AdminConfig:
    base_path: str
    db_path: Path
    paper_db_path: Path
    project_dir: Path
    deploy_script: Path
    papi_executable: str
    username: str
    password: str
    layout_output_dir: Path | None = None
    layout_max_pages: int | None = None
    layout_ocr_mode: str = "auto"
    layout_ocr_languages: str = "eng+chi_sim"
    layout_ocr_dpi: int = 220
    layout_ocr_executable: str = "tesseract"
    layout_formula_ocr_mode: str = "off"
    layout_formula_ocr_dpi: int = 260
    layout_formula_ocr_min_confidence: float = 0.7


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _admin_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _safe_text(value: Any, *, limit: int = 20000) -> str:
    return str(value or "").strip()[:limit]


def _safe_url(value: Any) -> str:
    text = _safe_text(value, limit=1000)
    if text and not URL_RE.match(text):
        raise ValueError("URL must start with http:// or https://")
    return text


def _safe_list(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [line.strip() for line in value.splitlines()]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = []
    return [item for item in items if item]


def ensure_admin_schema(db_path: Path) -> None:
    init_db(db_path)
    required_columns = {
        "params_json": "text not null default '{}'",
        "current_step": "text not null default ''",
        "result_json": "text not null default '{}'",
        "priority": "integer not null default 0",
        "created_at": "text",
    }
    with connect(db_path) as conn:
        conn.execute(
            """
            create table if not exists admin_paper_drafts (
                paper_key text primary key,
                payload_json text not null default '{}',
                updated_at text not null
            )
            """
        )
        existing = {row["name"] for row in conn.execute("pragma table_info(admin_jobs)").fetchall()}
        for name, definition in required_columns.items():
            if name not in existing:
                conn.execute(f"alter table admin_jobs add column {name} {definition}")
        conn.execute("update admin_jobs set created_at = started_at where created_at is null or created_at = ''")
        conn.commit()


def _paper_url_from_ids(ids: dict[str, Any]) -> str:
    if ids.get("url"):
        return str(ids["url"])
    if ids.get("arxiv_id"):
        return f"https://arxiv.org/abs/{ids['arxiv_id']}"
    return ""


def _build_discovery_providers(names: list[str], *, db_path: Path, refresh_provider_cache: bool = False):
    providers = []
    for name in names:
        if name == "openalex":
            providers.append(OpenAlexProvider())
        elif name == "arxiv":
            providers.append(ArxivProvider())
        elif name == "semantic_scholar":
            providers.append(SemanticScholarProvider())
        elif name == "google_scholar":
            providers.append(GoogleScholarProvider(db_path=db_path, refresh_cache=refresh_provider_cache))
        else:
            raise ValueError(f"unknown provider: {name}")
    if not providers:
        raise ValueError("at least one provider is required")
    return providers


def _primary_github(conn, paper_key: str) -> str:
    row = conn.execute(
        """
        select url from paper_code_links
        where paper_key = ? and lower(host) = 'github.com'
        order by case source_type when 'manual' then 0 when 'meta_json' then 1 else 2 end, id
        limit 1
        """,
        (paper_key,),
    ).fetchone()
    return str(row["url"]) if row else ""


def _job_insert(conn, job_type: str, params: dict[str, Any]) -> int:
    now = _admin_now()
    priority = int(params.get("priority") or 0)
    cursor = conn.execute(
        """
        insert into admin_jobs (
            job_type, status, message, params_json, current_step, result_json,
            priority, created_at, started_at
        ) values (?, 'queued', 'waiting in queue', ?, '', '{}', ?, ?, ?)
        """,
        (job_type, _json_dumps(params), priority, now, now),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _job_update(
    db_path: Path,
    job_id: int,
    *,
    status: str,
    message: str = "",
    log: str = "",
    result: dict[str, Any] | None = None,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            update admin_jobs
            set status = ?, message = ?, log = ?, result_json = ?, finished_at = ?
            where id = ?
            """,
            (status, message[:1000], log[-20000:], _json_dumps(result or {}), _admin_now(), job_id),
        )
        conn.commit()


def _job_message(db_path: Path, job_id: int, message: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "update admin_jobs set message = ?, current_step = ? where id = ? and status = 'running'",
            (message[:1000], message[:200], job_id),
        )
        conn.commit()


def _mark_interrupted_jobs(db_path: Path) -> None:
    ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            update admin_jobs
            set status = 'failed',
                message = 'interrupted by admin service restart',
                finished_at = ?
            where status = 'running'
            """,
            (_admin_now(),),
        )
        conn.commit()


def _jobs_payload(conn, *, limit: int = DEFAULT_JOB_LIMIT) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select * from admin_jobs
        order by case status when 'running' then 0 when 'queued' then 1 else 2 end,
                 priority desc, id desc
        limit ?
        """,
        (limit,),
    ).fetchall()
    jobs: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["params"] = _json_loads(item.get("params_json"), {})
        item["result"] = _json_loads(item.get("result_json"), {})
        jobs.append(item)
    return jobs


def list_state(db_path: Path) -> dict[str, Any]:
    ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        latest_blog_jobs: dict[str, dict[str, Any]] = {}
        for job_row in conn.execute(
            "select * from admin_jobs where job_type in ('paper_blog_generate', 'paper_blog_publish') order by id desc"
        ).fetchall():
            job = dict(job_row)
            params = _json_loads(job.get("params_json"), {})
            paper_key = str(params.get("paperKey") or params.get("paper_key") or "")
            if paper_key and paper_key not in latest_blog_jobs:
                latest_blog_jobs[paper_key] = job
        latest_layout_jobs: dict[str, dict[str, Any]] = {}
        for job_row in conn.execute(
            "select * from admin_jobs where job_type = 'paper_layout_parse' order by id desc"
        ).fetchall():
            job = dict(job_row)
            params = _json_loads(job.get("params_json"), {})
            paper_key = str(params.get("paperKey") or params.get("paper_key") or "")
            if paper_key and paper_key not in latest_layout_jobs:
                latest_layout_jobs[paper_key] = job
        latest_layout_runs: dict[str, dict[str, Any]] = {}
        for run_row in conn.execute(
            """
            select id, paper_key, provider, provider_version, status,
                   stats_json, error, started_at, finished_at
            from paper_layout_runs
            order by id desc
            """
        ).fetchall():
            paper_key = str(run_row["paper_key"] or "")
            if not paper_key or paper_key in latest_layout_runs:
                continue
            stats = _json_loads(run_row["stats_json"], {})
            if not isinstance(stats, dict):
                stats = {}
            summary = stats.get("summary") if isinstance(stats.get("summary"), dict) else {}
            reading_order = summary.get("reading_order") if isinstance(summary.get("reading_order"), dict) else {}
            latest_layout_runs[paper_key] = {
                "id": run_row["id"],
                "provider": run_row["provider"] or "",
                "provider_version": run_row["provider_version"] or "",
                "status": run_row["status"] or "",
                "artifact_count": int(stats.get("artifact_count") or 0),
                "block_count": int(stats.get("block_count") or 0),
                "error": run_row["error"] or "",
                "started_at": run_row["started_at"] or "",
                "finished_at": run_row["finished_at"] or "",
                "summary": {
                    "parser_version": summary.get("parser_version") or "",
                    "evidence_ready_blocks": int(summary.get("evidence_ready_blocks") or 0),
                    "captioned_visual_blocks": int(summary.get("captioned_visual_blocks") or 0),
                    "structured_table_blocks": int(summary.get("structured_table_blocks") or 0),
                    "geometry_table_blocks": int(summary.get("geometry_table_blocks") or 0),
                    "text_fallback_table_blocks": int(summary.get("text_fallback_table_blocks") or 0),
                    "spanning_table_blocks": int(summary.get("spanning_table_blocks") or 0),
                    "reading_order": {
                        "method": reading_order.get("method") or "",
                        "pages_completed": int(reading_order.get("pages_completed") or 0),
                        "multi_column_pages": int(reading_order.get("multi_column_pages") or 0),
                        "cross_column_blocks": int(reading_order.get("cross_column_blocks") or 0),
                        "caption_paired_blocks": int(reading_order.get("caption_paired_blocks") or 0),
                        "low_confidence_blocks": int(reading_order.get("low_confidence_blocks") or 0),
                        "average_confidence": float(reading_order.get("average_confidence") or 0),
                    },
                    "equation_blocks": int(summary.get("equation_blocks") or 0),
                    "high_quality_evidence_blocks": int(summary.get("high_quality_evidence_blocks") or 0),
                    "high_quality_visual_blocks": int(summary.get("high_quality_visual_blocks") or 0),
                    "high_quality_table_blocks": int(summary.get("high_quality_table_blocks") or 0),
                    "high_quality_equation_blocks": int(summary.get("high_quality_equation_blocks") or 0),
                    "document_type": summary.get("document_type") or "",
                    "ocr": summary.get("ocr") if isinstance(summary.get("ocr"), dict) else {},
                    "formula_ocr": summary.get("formula_ocr") if isinstance(summary.get("formula_ocr"), dict) else {},
                    "page_count": int(summary.get("page_count") or 0),
                },
            }
        papers = []
        rows = conn.execute(
            """
            select p.paper_key, p.title, p.year, p.ids_json, p.updated_at,
                   coalesce(o.hidden, 0) as hidden,
                   coalesce(o.paper_url, '') as override_paper_url,
                   coalesce(o.arxiv_id, '') as override_arxiv_id,
                   coalesce(o.github_url, '') as override_github_url,
                   d.updated_at as draft_updated_at,
                   b.status as blog_status,
                   b.word_count as blog_word_count,
                   b.updated_at as blog_updated_at,
                   b.current_version_id as blog_current_version_id
            from papers p
            left join admin_paper_overrides o on o.paper_key = p.paper_key
            left join admin_paper_drafts d on d.paper_key = p.paper_key
            left join paper_blog_posts b on b.paper_key = p.paper_key
            order by p.updated_at desc, p.paper_key
            """
        ).fetchall()
        for row in rows:
            ids = _json_loads(row["ids_json"], {})
            if not isinstance(ids, dict):
                ids = {}
            paper_key = str(row["paper_key"])
            latest_blog_job = latest_blog_jobs.get(paper_key, {})
            latest_layout_job = latest_layout_jobs.get(paper_key, {})
            latest_layout_run = latest_layout_runs.get(paper_key, {})
            latest_layout_summary = latest_layout_run.get("summary") if isinstance(latest_layout_run.get("summary"), dict) else {}
            latest_layout_ocr = latest_layout_summary.get("ocr") if isinstance(latest_layout_summary.get("ocr"), dict) else {}
            latest_formula_ocr = latest_layout_summary.get("formula_ocr") if isinstance(latest_layout_summary.get("formula_ocr"), dict) else {}
            latest_reading_order = latest_layout_summary.get("reading_order") if isinstance(latest_layout_summary.get("reading_order"), dict) else {}
            papers.append(
                {
                    "paper_key": paper_key,
                    "title": row["title"] or paper_key,
                    "year": row["year"],
                    "hidden": bool(row["hidden"]),
                    "arxiv_id": row["override_arxiv_id"] or ids.get("arxiv_id") or "",
                    "paper_url": row["override_paper_url"] or _paper_url_from_ids(ids),
                    "github_url": row["override_github_url"] or _primary_github(conn, paper_key),
                    "updated_at": row["updated_at"],
                    "draft_updated_at": row["draft_updated_at"] or "",
                    "has_draft": bool(row["draft_updated_at"]),
                    "blog_status": row["blog_status"] or "not_generated",
                    "blog_word_count": int(row["blog_word_count"] or 0),
                    "blog_updated_at": row["blog_updated_at"] or "",
                    "blog_current_version_id": row["blog_current_version_id"],
                    "blog_latest_job_id": latest_blog_job.get("id"),
                    "blog_latest_job_status": latest_blog_job.get("status") or "",
                    "blog_latest_job_message": latest_blog_job.get("message") or "",
                    "layout_latest_job_id": latest_layout_job.get("id"),
                    "layout_latest_job_status": latest_layout_job.get("status") or "",
                    "layout_latest_job_message": latest_layout_job.get("message") or "",
                    "layout_latest_run_id": latest_layout_run.get("id"),
                    "layout_status": latest_layout_job.get("status")
                    if latest_layout_job.get("status") in {"queued", "running"}
                    else latest_layout_run.get("status") or "not_parsed",
                    "layout_parser_version": latest_layout_run.get("provider_version") or latest_layout_summary.get("parser_version") or "",
                    "layout_artifact_count": latest_layout_run.get("artifact_count") or 0,
                    "layout_block_count": latest_layout_run.get("block_count") or 0,
                    "layout_evidence_ready_blocks": latest_layout_summary.get("evidence_ready_blocks") or 0,
                    "layout_captioned_visual_blocks": latest_layout_summary.get("captioned_visual_blocks") or 0,
                    "layout_structured_table_blocks": latest_layout_summary.get("structured_table_blocks") or 0,
                    "layout_geometry_table_blocks": latest_layout_summary.get("geometry_table_blocks") or 0,
                    "layout_text_fallback_table_blocks": latest_layout_summary.get("text_fallback_table_blocks") or 0,
                    "layout_spanning_table_blocks": latest_layout_summary.get("spanning_table_blocks") or 0,
                    "layout_reading_order_multi_column_pages": latest_reading_order.get("multi_column_pages") or 0,
                    "layout_reading_order_cross_column_blocks": latest_reading_order.get("cross_column_blocks") or 0,
                    "layout_reading_order_caption_paired_blocks": latest_reading_order.get("caption_paired_blocks") or 0,
                    "layout_reading_order_low_confidence_blocks": latest_reading_order.get("low_confidence_blocks") or 0,
                    "layout_reading_order_average_confidence": latest_reading_order.get("average_confidence") or 0,
                    "layout_equation_blocks": latest_layout_summary.get("equation_blocks") or 0,
                    "layout_high_quality_evidence_blocks": latest_layout_summary.get("high_quality_evidence_blocks") or 0,
                    "layout_high_quality_visual_blocks": latest_layout_summary.get("high_quality_visual_blocks") or 0,
                    "layout_high_quality_table_blocks": latest_layout_summary.get("high_quality_table_blocks") or 0,
                    "layout_high_quality_equation_blocks": latest_layout_summary.get("high_quality_equation_blocks") or 0,
                    "layout_document_type": latest_layout_summary.get("document_type") or "",
                    "layout_ocr_pages_attempted": int(latest_layout_ocr.get("pages_attempted") or 0),
                    "layout_ocr_pages_succeeded": int(latest_layout_ocr.get("pages_succeeded") or 0),
                    "layout_ocr_block_count": int(latest_layout_ocr.get("block_count") or 0),
                    "layout_formula_ocr_blocks_attempted": int(latest_formula_ocr.get("blocks_attempted") or 0),
                    "layout_formula_ocr_blocks_succeeded": int(latest_formula_ocr.get("blocks_succeeded") or 0),
                    "layout_page_count": latest_layout_summary.get("page_count") or 0,
                    "layout_finished_at": latest_layout_run.get("finished_at") or "",
                }
            )
        profiles = []
        for row in conn.execute("select * from research_profiles order by name").fetchall():
            profiles.append(
                {
                    "name": row["name"],
                    "description": row["description"],
                    "keywords": _json_loads(row["keywords_json"], []),
                    "primary_since": row["primary_since"],
                    "exception_since": row["exception_since"],
                }
            )
        jobs = _jobs_payload(conn)
        hidden_count = sum(1 for paper in papers if paper["hidden"])
        status_counts = {status: 0 for status in JOB_STATUSES}
        for job in jobs:
            status = str(job.get("status") or "")
            if status in status_counts:
                status_counts[status] += 1
    return {
        "papers": papers,
        "profiles": profiles,
        "jobs": jobs,
        "job_statuses": list(JOB_STATUSES),
        "providers": list(PROVIDER_NAMES),
        "fact_types": list(FACT_TYPES),
        "stats": {
            "paper_count": len(papers),
            "hidden_count": hidden_count,
            "visible_count": len(papers) - hidden_count,
            "job_status_counts": status_counts,
        },
    }


def paper_detail(db_path: Path, paper_key: str) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        paper = conn.execute("select * from papers where paper_key = ?", (paper_key,)).fetchone()
        if paper is None:
            raise KeyError(paper_key)
        ids = _json_loads(paper["ids_json"], {})
        if not isinstance(ids, dict):
            ids = {}
        override = conn.execute(
            "select * from admin_paper_overrides where paper_key = ?",
            (paper_key,),
        ).fetchone()
        draft = conn.execute(
            "select payload_json, updated_at from admin_paper_drafts where paper_key = ?",
            (paper_key,),
        ).fetchone()
        facts = []
        for row in conn.execute(
            """
            select id, fact_type, name, statement, confidence, metadata_json
            from research_facts
            where paper_key = ?
            order by case fact_type
                when 'method' then 1 when 'claim' then 2 when 'limitation' then 3
                when 'dataset' then 4 when 'benchmark' then 5 else 6 end, id
            """,
            (paper_key,),
        ).fetchall():
            facts.append(
                {
                    "id": row["id"],
                    "fact_type": row["fact_type"],
                    "name": row["name"],
                    "statement": row["statement"],
                    "confidence": row["confidence"],
                    "metadata": _json_loads(row["metadata_json"], {}),
                }
            )
        return {
            "paper_key": paper_key,
            "title": paper["title"] or paper_key,
            "ids": ids,
            "hidden": bool(override["hidden"]) if override else False,
            "paper_url": (override["paper_url"] if override else "") or _paper_url_from_ids(ids),
            "arxiv_id": (override["arxiv_id"] if override else "") or ids.get("arxiv_id") or "",
            "github_url": (override["github_url"] if override else "") or _primary_github(conn, paper_key),
            "facts": facts,
            "draft": _json_loads(draft["payload_json"], {}) if draft else {},
            "draft_updated_at": draft["updated_at"] if draft else "",
        }


def update_paper(db_path: Path, paper_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    init_db(db_path)
    hidden = 1 if bool(payload.get("hidden")) else 0
    paper_url = _safe_url(payload.get("paper_url", ""))
    arxiv_id = _safe_text(payload.get("arxiv_id", ""), limit=80)
    github_url = _safe_url(payload.get("github_url", ""))
    if github_url and not GITHUB_RE.match(github_url):
        raise ValueError("GitHub link must be a github.com repository URL")
    now = _admin_now()
    with connect(db_path) as conn:
        if conn.execute("select 1 from papers where paper_key = ?", (paper_key,)).fetchone() is None:
            raise KeyError(paper_key)
        conn.execute(
            """
            insert into admin_paper_overrides (paper_key, hidden, paper_url, arxiv_id, github_url, updated_at)
            values (?, ?, ?, ?, ?, ?)
            on conflict(paper_key) do update set
                hidden = excluded.hidden,
                paper_url = excluded.paper_url,
                arxiv_id = excluded.arxiv_id,
                github_url = excluded.github_url,
                updated_at = excluded.updated_at
            """,
            (paper_key, hidden, paper_url, arxiv_id, github_url, now),
        )
        row = conn.execute("select ids_json from papers where paper_key = ?", (paper_key,)).fetchone()
        ids = _json_loads(row["ids_json"], {}) if row else {}
        if not isinstance(ids, dict):
            ids = {}
        if paper_url:
            ids["url"] = paper_url
        if arxiv_id:
            ids["arxiv_id"] = arxiv_id
        conn.execute("update papers set ids_json = ?, updated_at = ? where paper_key = ?", (_json_dumps(ids), now, paper_key))
        conn.execute("update paper_cards set ids_json = ?, updated_at = ? where paper_key = ?", (_json_dumps(ids), now, paper_key))
        conn.execute("delete from paper_code_links where paper_key = ? and source_type = 'manual'", (paper_key,))
        if github_url:
            match = GITHUB_RE.match(github_url)
            owner = match.group(1) if match else ""
            repo = match.group(2).removesuffix(".git") if match else ""
            conn.execute(
                """
                insert into paper_code_links (
                    paper_key, url, host, owner, repo, source_type, source_path, context, created_at, updated_at
                ) values (?, ?, 'github.com', ?, ?, 'manual', '', 'admin override', ?, ?)
                """,
                (paper_key, github_url, owner, repo, now, now),
            )
        conn.execute("delete from admin_paper_drafts where paper_key = ?", (paper_key,))
        conn.commit()
    return paper_detail(db_path, paper_key)


def save_paper_draft(db_path: Path, paper_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    init_db(db_path)
    now = _admin_now()
    allowed = {
        "hidden",
        "arxiv_id",
        "paper_url",
        "github_url",
        "facts",
        "new_fact_type",
        "new_fact_name",
        "new_fact_confidence",
        "new_fact_statement",
    }
    draft = {key: payload.get(key) for key in allowed if key in payload}
    with connect(db_path) as conn:
        if conn.execute("select 1 from papers where paper_key = ?", (paper_key,)).fetchone() is None:
            raise KeyError(paper_key)
        conn.execute(
            """
            insert into admin_paper_drafts (paper_key, payload_json, updated_at)
            values (?, ?, ?)
            on conflict(paper_key) do update set
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (paper_key, _json_dumps(draft), now),
        )
        conn.commit()
    return {"paper_key": paper_key, "status": "draft_saved", "updated_at": now}


def delete_paper_draft(db_path: Path, paper_key: str) -> dict[str, Any]:
    with connect(db_path) as conn:
        conn.execute("delete from admin_paper_drafts where paper_key = ?", (paper_key,))
        conn.commit()
    return {"paper_key": paper_key, "status": "draft_deleted"}


def blog_detail(db_path: Path, paper_key: str) -> dict[str, Any]:
    detail = paper_blog_detail(db_path, paper_key)
    current_version_id = (detail.get("post") or {}).get("current_version_id")
    current_meta: dict[str, Any] = {}
    for version in detail.get("versions") or []:
        if version.get("id") == current_version_id:
            current_meta = _json_loads(version.get("generation_meta_json"), {})
            break
    latest_job = None
    ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            "select * from admin_jobs where job_type in ('paper_blog_generate', 'paper_blog_publish') order by id desc"
        ).fetchall()
    for row in rows:
        item = dict(row)
        params = _json_loads(item.get("params_json"), {})
        if str(params.get("paperKey") or params.get("paper_key") or "") != paper_key:
            continue
        item["params"] = params
        item["result"] = _json_loads(item.get("result_json"), {})
        latest_job = item
        break
    detail["generation_meta"] = current_meta
    detail["latest_job"] = latest_job
    return detail


def layout_detail(db_path: Path, paper_key: str) -> dict[str, Any]:
    detail = paper_layout_detail(db_path, paper_key)
    detail["evidence_graph"] = load_paper_evidence_graph(db_path, paper_key, public=False)
    latest_job = None
    ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            "select * from admin_jobs where job_type = 'paper_layout_parse' order by id desc"
        ).fetchall()
    for row in rows:
        item = dict(row)
        params = _json_loads(item.get("params_json"), {})
        if str(params.get("paperKey") or params.get("paper_key") or "") != paper_key:
            continue
        item["params"] = params
        item["result"] = _json_loads(item.get("result_json"), {})
        latest_job = item
        break
    detail["latest_job"] = latest_job
    detail["enabled"] = True
    source_dir = None
    with connect(db_path) as conn:
        paper = conn.execute("select paper_dir from papers where paper_key = ?", (paper_key,)).fetchone()
        card = conn.execute("select source_dir from paper_cards where paper_key = ?", (paper_key,)).fetchone()
    for value in (
        str(card["source_dir"] or "") if card is not None else "",
        str(paper["paper_dir"] or "") if paper is not None else "",
    ):
        candidate = Path(value)
        if candidate.exists() and candidate.is_dir():
            source_dir = candidate
            break
    candidates = visual_candidates(
        db_path,
        paper_key,
        source_dir=source_dir,
        cover_names=("cover.webp", "cover.png", "cover.jpg", "cover.jpeg", "cover.svg"),
    )
    detail["representative_visual"] = candidates[0].as_dict() if candidates else None
    detail["visual_candidates"] = [candidate.as_dict() for candidate in candidates[:8]]
    return detail


def _refresh_paper_evidence_graph(db_path: Path, paper_key: str) -> dict[str, Any]:
    try:
        result = extract_layout_evidence_graph(db_path, paper_key=paper_key)
    except Exception as exc:
        return {"status": "failed", "paper_key": paper_key, "error": str(exc)}
    return {
        "status": "completed",
        "paper_key": paper_key,
        "facts": result.fact_nodes_written,
        "evidence": result.evidence_nodes_written,
        "edges": result.edges_written,
        "supported": result.supported_by_edges,
        "provenance": result.provenance_written,
    }


def hide_blog(db_path: Path, paper_key: str, *, config: AdminConfig | None = None) -> dict[str, Any]:
    result = hide_blog_post(db_path, paper_key)
    if config is not None:
        job_id = _start_blog_publish_job(db_path, paper_key, "hide")
        try:
            log = _rebuild_paper_blog_site(config)
        except Exception as exc:
            _job_update(db_path, job_id, status="publish_failed", message=str(exc), log=traceback.format_exc(), result=result)
            raise PaperBlogPublishError(
                f"blog was hidden in the database, but static site publish failed: {exc}",
                result=result,
            ) from exc
        _job_update(db_path, job_id, status="completed", message="blog hide published", log=log, result=result)
    return result


def rollback_blog(
    db_path: Path,
    paper_key: str,
    version_id: int,
    *,
    config: AdminConfig | None = None,
) -> dict[str, Any]:
    result = rollback_blog_post(db_path, paper_key, version_id)
    if config is not None:
        job_id = _start_blog_publish_job(db_path, paper_key, "rollback")
        try:
            log = _rebuild_paper_blog_site(config)
        except Exception as exc:
            _job_update(db_path, job_id, status="publish_failed", message=str(exc), log=traceback.format_exc(), result=result)
            raise PaperBlogPublishError(
                f"blog rollback was saved in the database, but static site publish failed: {exc}",
                result=result,
            ) from exc
        _job_update(db_path, job_id, status="completed", message="blog rollback published", log=log, result=result)
    return result


class PaperBlogPublishError(RuntimeError):
    def __init__(self, message: str, *, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result


def _start_blog_publish_job(db_path: Path, paper_key: str, operation: str) -> int:
    ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        job_id = _job_insert(
            conn,
            "paper_blog_publish",
            {"paperKey": paper_key, "operation": operation},
        )
        conn.execute(
            "update admin_jobs set status = 'running', message = ?, current_step = ? where id = ?",
            (f"publishing blog {operation}", operation, job_id),
        )
        conn.commit()
    return job_id


def _rebuild_paper_blog_site(config: AdminConfig) -> str:
    with _BLOG_PUBLISH_LOCK:
        with tempfile.TemporaryDirectory(prefix="airesearch-blog-publish-") as tmp:
            tmp_root = Path(tmp)
            filtered_db = tmp_root / "airesearch.sqlite3"
            bundle_dir = tmp_root / "bundle"
            hidden = _copy_db_without_hidden(config, filtered_db)
            export_report_bundle(filtered_db, bundle_dir, concurrency=5)
            site = export_report_site(bundle_dir)
            published = publish_static_site(bundle_dir, config.project_dir / "exports" / "site-current")
        deploy = subprocess.run(
            [
                "sudo",
                "env",
                f"PROJECT_ROOT={config.project_dir}",
                f"SITE_DIR={config.project_dir / 'exports' / 'site-current'}",
                "bash",
                str(config.deploy_script),
            ],
            cwd=config.project_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=600,
            check=False,
        )
        deploy_output = deploy.stdout.strip()
        if deploy.returncode != 0:
            detail = f": {deploy_output}" if deploy_output else ""
            raise RuntimeError(f"deploy failed with code {deploy.returncode}{detail}")
        return (
            f"site rebuilt: {site.artifact_count} artifacts; hidden papers: {len(hidden)}; "
            f"published: {published.entrypoint}\nsite deployed: {deploy_output or 'completed'}"
        )


def _blog_provider_from_options(options: dict[str, Any]):
    provider_name = _safe_text(options.get("provider") or "openai-compatible", limit=80)
    if provider_name == "fixture":
        return FixtureBlogProvider(chars_per_section=int(options.get("fixture_chars_per_section") or 520)), "fixture-blog"
    if provider_name == "openai-compatible":
        model = _safe_text(
            options.get("model")
            or os.environ.get("AIRESEARCH_BLOG_MODEL")
            or os.environ.get("NIU_ASSISTANT_MODEL")
            or DEFAULT_BLOG_MODEL,
            limit=120,
        )
        base_url = _safe_text(
            os.environ.get("AIRESEARCH_BLOG_BASE_URL")
            or os.environ.get("OPENCODE_GO_BASE_URL")
            or os.environ.get("TRANSLATE_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("NIU_ASSISTANT_API_BASE")
            or "",
            limit=500,
        )
        api_style = os.environ.get("AIRESEARCH_BLOG_API_STYLE", "").strip()
        proxy_url = (
            os.environ.get("AIRESEARCH_BLOG_PROXY")
            or os.environ.get("OPENCODE_GO_PROXY")
            or ""
        ).strip()
        return (
            OpenAICompatibleBlogProvider.from_env(
                model=model,
                base_url=base_url or None,
                api_style=api_style or None,
                proxy_url=proxy_url,
            ),
            model,
        )
    raise ValueError(f"unsupported paper blog provider: {provider_name}")


def run_blog_generation_job(config: AdminConfig, *, job_id: int, options: dict[str, Any]) -> str:
    paper_key = _safe_text(options.get("paperKey") or options.get("paper_key"), limit=300)
    if not paper_key:
        raise ValueError("paperKey is required")
    provider, default_model = _blog_provider_from_options(options)
    model = _safe_text(options.get("model") or default_model, limit=120)
    target_chars = int(options.get("targetWordCount") or options.get("target_chars") or 5000)
    force = bool(options.get("force"))
    _job_message(config.db_path, job_id, "generating paper blog")
    result = generate_and_publish_blog(
        config.db_path,
        paper_key,
        provider=provider,
        model=model,
        target_chars=target_chars,
        force=force,
    )
    result_payload = {
        "paperKey": result.paper_key,
        "versionId": result.version_id,
        "versionNumber": result.version_number,
        "wordCount": result.word_count,
        "status": result.status,
    }
    _job_message(config.db_path, job_id, "paper blog generated")
    try:
        _job_message(config.db_path, job_id, "publishing paper blog site")
        publish_log = _rebuild_paper_blog_site(config)
    except Exception as exc:
        raise PaperBlogPublishError(
            f"paper blog version {result.version_number} was saved, but static site publish failed: {exc}",
            result=result_payload,
        ) from exc
    return (
        f"paper_blog_generate completed: paper_key={result.paper_key} "
        f"version={result.version_number} word_count={result.word_count}\n{publish_log}"
    )


def _layout_options_from_config(config: AdminConfig, options: dict[str, Any]) -> LayoutParserOptions:
    output_dir = config.layout_output_dir or (config.project_dir / "data" / "layout")
    max_pages = options.get("maxPages") or options.get("max_pages") or config.layout_max_pages
    ocr_mode = str(options.get("ocrMode") or options.get("ocr_mode") or config.layout_ocr_mode).strip().lower()
    ocr_languages = str(options.get("ocrLanguages") or options.get("ocr_languages") or config.layout_ocr_languages).strip()
    ocr_dpi = int(options.get("ocrDpi") or options.get("ocr_dpi") or config.layout_ocr_dpi)
    formula_ocr_mode = str(
        options.get("formulaOcrMode") or options.get("formula_ocr_mode") or config.layout_formula_ocr_mode
    ).strip().lower()
    formula_ocr_dpi = int(options.get("formulaOcrDpi") or options.get("formula_ocr_dpi") or config.layout_formula_ocr_dpi)
    formula_ocr_min_confidence = float(
        options.get("formulaOcrMinConfidence")
        or options.get("formula_ocr_min_confidence")
        or config.layout_formula_ocr_min_confidence
    )
    return LayoutParserOptions(
        output_dir=output_dir,
        max_pages=int(max_pages) if max_pages else None,
        ocr_mode=ocr_mode,
        ocr_languages=ocr_languages,
        ocr_dpi=ocr_dpi,
        ocr_executable=config.layout_ocr_executable,
        formula_ocr_mode=formula_ocr_mode,
        formula_ocr_dpi=formula_ocr_dpi,
        formula_ocr_min_confidence=formula_ocr_min_confidence,
    )


def run_layout_parse_job(config: AdminConfig, *, job_id: int, options: dict[str, Any]) -> str:
    paper_key = _safe_text(options.get("paperKey") or options.get("paper_key"), limit=300)
    if not paper_key:
        raise ValueError("paperKey is required")
    force = bool(options.get("force"))
    _job_message(config.db_path, job_id, "parsing paper layout")
    result = parse_paper_layout(
        db_path=config.db_path,
        paper_key=paper_key,
        options=_layout_options_from_config(config, options),
        force=force,
    )
    graph_refresh = _refresh_paper_evidence_graph(config.db_path, paper_key)
    if graph_refresh["status"] == "completed":
        graph_message = (
            f"graph_facts={graph_refresh['facts']} graph_evidence={graph_refresh['evidence']} "
            f"graph_supported={graph_refresh['supported']}"
        )
    else:
        graph_message = f"graph_refresh_failed={graph_refresh['error']}"
    _job_message(config.db_path, job_id, f"paper layout parsed; {graph_message}")
    return (
        f"paper_layout_parse completed: paper_key={result.paper_key} "
        f"run_id={result.run_id} status={result.status} "
        f"artifacts={result.artifact_count} blocks={result.block_count} "
        f"output_dir={result.output_dir} {graph_message}"
    )


def update_fact(db_path: Path, fact_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    fact_type = _safe_text(payload.get("fact_type"), limit=40)
    if fact_type not in FACT_TYPES:
        raise ValueError("unsupported fact_type")
    name = _safe_text(payload.get("name"), limit=500)
    statement = _safe_text(payload.get("statement"), limit=5000)
    if not statement:
        raise ValueError("statement is required")
    confidence = float(payload.get("confidence", 0.9))
    confidence = max(0.0, min(1.0, confidence))
    metadata = payload.get("metadata", {})
    if isinstance(metadata, str):
        metadata = _json_loads(metadata, {})
    if not isinstance(metadata, dict):
        metadata = {}
    now = _admin_now()
    paper_key = ""
    with connect(db_path) as conn:
        row = conn.execute("select id, paper_key from research_facts where id = ?", (fact_id,)).fetchone()
        if row is None:
            raise KeyError(str(fact_id))
        paper_key = str(row["paper_key"])
        conn.execute(
            """
            update research_facts
            set fact_type = ?, name = ?, statement = ?, confidence = ?, metadata_json = ?, updated_at = ?
            where id = ?
            """,
            (fact_type, name, statement, confidence, _json_dumps(metadata), now, fact_id),
        )
        conn.execute("delete from research_fact_translations where fact_id = ?", (fact_id,))
        conn.commit()
    return {
        "id": fact_id,
        "status": "updated",
        "graph_refresh": _refresh_paper_evidence_graph(db_path, paper_key),
    }


def create_fact(db_path: Path, paper_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    fact_type = _safe_text(payload.get("fact_type"), limit=40)
    if fact_type not in FACT_TYPES:
        raise ValueError("unsupported fact_type")
    statement = _safe_text(payload.get("statement"), limit=5000)
    if not statement:
        raise ValueError("statement is required")
    now = _admin_now()
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            insert into research_facts (
                paper_key, fact_type, name, statement, confidence, metadata_json,
                provider_name, extractor_version, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, 'admin', 'admin.1', ?, ?)
            """,
            (
                paper_key,
                fact_type,
                _safe_text(payload.get("name"), limit=500),
                statement,
                float(payload.get("confidence", 0.9)),
                _json_dumps(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}),
                now,
                now,
            ),
        )
        conn.commit()
        fact_id = int(cursor.lastrowid)
    return {
        "id": fact_id,
        "status": "created",
        "graph_refresh": _refresh_paper_evidence_graph(db_path, paper_key),
    }


def delete_fact(db_path: Path, fact_id: int) -> dict[str, Any]:
    with connect(db_path) as conn:
        row = conn.execute("select paper_key from research_facts where id = ?", (fact_id,)).fetchone()
        if row is None:
            raise KeyError(str(fact_id))
        paper_key = str(row["paper_key"])
        conn.execute("delete from research_facts where id = ?", (fact_id,))
        conn.commit()
    return {
        "id": fact_id,
        "status": "deleted",
        "graph_refresh": _refresh_paper_evidence_graph(db_path, paper_key),
    }


def update_profile(db_path: Path, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    keywords = _safe_list(payload.get("keywords"))
    description = _safe_text(payload.get("description"), limit=1000)
    primary_since = _safe_text(payload.get("primary_since"), limit=40)
    exception_since = _safe_text(payload.get("exception_since"), limit=40)
    with connect(db_path) as conn:
        if conn.execute("select 1 from research_profiles where name = ?", (name,)).fetchone() is None:
            raise KeyError(name)
        conn.execute(
            """
            update research_profiles
            set description = ?, keywords_json = ?, primary_since = ?, exception_since = ?, updated_at = ?
            where name = ?
            """,
            (description, _json_dumps(keywords), primary_since, exception_since, _admin_now(), name),
        )
        conn.commit()
    return {"name": name, "status": "updated"}


def create_profile(db_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    name = _safe_text(payload.get("name"), limit=100)
    if not PROFILE_NAME_RE.match(name):
        raise ValueError("方向 key 只能使用小写字母、数字和下划线，且必须以字母开头")
    description = _safe_text(payload.get("description"), limit=1000)
    keywords = _safe_list(payload.get("keywords"))
    primary_since = _safe_text(payload.get("primary_since"), limit=40) or "2025-06-08"
    exception_since = _safe_text(payload.get("exception_since"), limit=40) or "2024-01-01"
    now = _admin_now()
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into research_profiles (
                name, description, keywords_json, preferred_venues_json,
                preferred_organizations_json, preferred_scholars_json, exception_keywords_json,
                primary_since, exception_since, created_at, updated_at
            ) values (?, ?, ?, '[]', '[]', '[]', '[]', ?, ?, ?, ?)
            """,
            (name, description, _json_dumps(keywords), primary_since, exception_since, now, now),
        )
        conn.commit()
    return {"name": name, "status": "created"}


def delete_profile(db_path: Path, name: str) -> dict[str, Any]:
    with connect(db_path) as conn:
        row = conn.execute("select count(*) as c from research_profiles").fetchone()
        if row and int(row["c"]) <= 1:
            raise ValueError("至少需要保留一个搜索方向")
        cursor = conn.execute("delete from research_profiles where name = ?", (name,))
        if cursor.rowcount == 0:
            raise KeyError(name)
        conn.commit()
    return {"name": name, "status": "deleted"}


def _apply_search_task_dates(db_path: Path, profile_names: list[str], options: dict[str, Any]) -> None:
    primary_since = _safe_text(options.get("primary_since"), limit=40)
    exception_since = _safe_text(options.get("exception_since"), limit=40)
    if not primary_since and not exception_since:
        return
    with connect(db_path) as conn:
        for name in profile_names:
            if primary_since:
                conn.execute(
                    "update research_profiles set primary_since = ?, updated_at = ? where name = ?",
                    (primary_since, _admin_now(), name),
                )
            if exception_since:
                conn.execute(
                    "update research_profiles set exception_since = ?, updated_at = ? where name = ?",
                    (exception_since, _admin_now(), name),
                )
        conn.commit()


def cancel_job(db_path: Path, job_id: int) -> dict[str, Any]:
    ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        row = conn.execute("select status from admin_jobs where id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(str(job_id))
        if row["status"] != "queued":
            raise ValueError("only queued jobs can be canceled")
        conn.execute(
            """
            update admin_jobs
            set status = 'canceled', message = 'canceled by admin', finished_at = ?
            where id = ?
            """,
            (_admin_now(), job_id),
        )
        conn.commit()
    return {"id": job_id, "status": "canceled"}


def delete_paper(db_path: Path, paper_db_path: Path, paper_key: str) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute("select paper_dir from papers where paper_key = ?", (paper_key,)).fetchone()
        if row is None:
            raise KeyError(paper_key)
        paper_dir = Path(row["paper_dir"] or "")
        conn.execute("delete from papers where paper_key = ?", (paper_key,))
        conn.execute("delete from admin_paper_overrides where paper_key = ?", (paper_key,))
        conn.execute("delete from admin_paper_drafts where paper_key = ?", (paper_key,))
        conn.commit()
    moved_to = ""
    if paper_dir.exists() and paper_dir.is_dir():
        trash_root = paper_db_path / ".trash" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        trash_root.mkdir(parents=True, exist_ok=True)
        target = trash_root / paper_key
        shutil.move(str(paper_dir), str(target))
        moved_to = str(target)
    index_path = paper_db_path / "index.json"
    if index_path.exists():
        index = _json_loads(index_path.read_text(encoding="utf-8"), {})
        if isinstance(index, dict) and paper_key in index:
            index.pop(paper_key, None)
            index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"paper_key": paper_key, "status": "deleted", "trash_path": moved_to}


def search_arxiv_title(query: str, limit: int = 10) -> list[dict[str, Any]]:
    import urllib.request as arxiv_request
    import xml.etree.ElementTree as ET_lib

    params = {
        "search_query": f"all:({query})",
        "start": "0",
        "max_results": str(max(1, min(limit, 20))),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    try:
        req_obj = arxiv_request.Request(url, headers={"User-Agent": "airesearch/0.1"})
        with arxiv_request.urlopen(req_obj, timeout=15) as resp:
            xml_text = resp.read().decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"arXiv API request failed: {exc}") from exc

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET_lib.fromstring(xml_text)
    except ET_lib.ParseError as exc:
        raise RuntimeError(f"arXiv API returned invalid XML: {exc}") from exc

    results: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        raw_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
        arxiv_id = raw_id.rsplit("/abs/", 1)[-1] if "/abs/" in raw_id else raw_id.rsplit("/", 1)[-1]
        if arxiv_id and arxiv_id.count(".") == 1 and len(arxiv_id) > 8:
            pass
        else:
            arxiv_id = ""
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()[:10]
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        authors = [
            (author.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for author in entry.findall("atom:author", ns)
        ]
        results.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": [a for a in authors if a],
            "published": published,
            "abstract": summary[:600],
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else raw_id,
        })
    return results


def _normalize_single_paper_input(paper_input: str) -> str:
    text = _safe_text(paper_input, limit=1000)
    github_blob = re.match(r"^https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$", text)
    if github_blob:
        owner, repo, branch, path = github_blob.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    github_raw_alias = re.match(r"^https://github\.com/([^/]+)/([^/]+)/raw/([^/]+)/(.+)$", text)
    if github_raw_alias:
        owner, repo, branch, path = github_raw_alias.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    return text


def _title_from_pdf_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    filename = urllib.parse.unquote(Path(parsed.path).name)
    if not filename.lower().endswith(".pdf"):
        return ""
    title = filename[:-4]
    title = re.sub(r"[_-]+", " ", title).strip()
    return title or "Imported PDF"


def _paper_keys(db_path: Path) -> set[str]:
    init_db(db_path)
    with connect(db_path) as conn:
        return {str(row["paper_key"]) for row in conn.execute("select paper_key from papers").fetchall()}


def ingest_single_paper(
    db_path: Path,
    paper_db_path: Path,
    papi_executable: str,
    paper_input: str,
    *,
    config: AdminConfig | None = None,
    auto_layout: bool = True,
) -> dict[str, Any]:
    init_db(db_path)
    paper_db_path.mkdir(parents=True, exist_ok=True)
    normalized_input = _normalize_single_paper_input(paper_input)
    before_keys = _paper_keys(db_path)

    env = os.environ.copy()
    env["PAPER_DB_PATH"] = str(paper_db_path)
    add_command = [papi_executable, "add", normalized_input]
    pdf_title = _title_from_pdf_url(normalized_input)
    if URL_RE.match(normalized_input) and pdf_title:
        add_command = [papi_executable, "add", "--pdf", normalized_input, "--title", pdf_title]
    completed = subprocess.run(
        add_command,
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    stdout_text = (completed.stdout or "").strip()
    stderr_text = (completed.stderr or "").strip()
    combined = stdout_text + "\n" + stderr_text

    if completed.returncode != 0:
        error_msg = stderr_text or f"papi exited with code {completed.returncode}"
        return {"status": "failed", "input": paper_input, "normalized_input": normalized_input, "error": error_msg, "stdout": combined}

    sync_result = sync_paperpipe(db_path=db_path, paper_db_path=paper_db_path)
    after_keys = _paper_keys(db_path)

    paper_key = ""
    # Try to extract paper_key from combined output: arXiv-derived keys or local PDF names.
    m = re.search(r"(\d{4,5}_\d{5,})", combined)
    if not m:
        m = re.search(r"(?:Added|Already added)[^:\n]*:\s*([A-Za-z0-9][A-Za-z0-9_.-]{1,200})", combined)
    if m:
        paper_key = m.group(1)
    if not paper_key:
        new_keys = sorted(after_keys - before_keys)
        if len(new_keys) == 1:
            paper_key = new_keys[0]

    layout_job: dict[str, Any] = {"job_id": None, "status": "skipped", "reason": "disabled"}
    if auto_layout and config is not None and paper_key:
        layout_job = enqueue_layout_parse_if_needed(config, paper_key)

    return {
        "status": "success",
        "input": paper_input,
        "normalized_input": normalized_input,
        "paper_key": paper_key,
        "stdout": stdout_text,
        "synced": sync_result.papers_seen > 0,
        "layout_job_id": layout_job.get("job_id"),
        "layout_job_status": layout_job.get("status"),
        "layout_job_reason": layout_job.get("reason", ""),
    }


def _hidden_paper_keys(db_path: Path) -> list[str]:
    init_db(db_path)
    with connect(db_path) as conn:
        return [
            str(row["paper_key"])
            for row in conn.execute("select paper_key from admin_paper_overrides where hidden = 1").fetchall()
        ]


def _copy_db_without_hidden(config: AdminConfig, target_db: Path) -> list[str]:
    shutil.copy2(config.db_path, target_db)
    init_db(target_db)
    hidden = _hidden_paper_keys(target_db)
    with connect(target_db) as conn:
        for paper_key in hidden:
            conn.execute("delete from papers where paper_key = ?", (paper_key,))
        conn.commit()
    return hidden


def publish_with_overrides(config: AdminConfig, *, job_id: int, job_type: str, options: dict[str, Any]) -> str:
    logs: list[str] = []

    def progress(step: str) -> None:
        _job_message(config.db_path, job_id, step)

    normalized_type = {"refresh": "search_ingest", "rebuild": "rebuild_deploy"}.get(job_type, job_type)
    should_refresh = normalized_type == "search_ingest"
    should_rebuild = normalized_type in {"search_ingest", "rebuild_site", "rebuild_deploy"}
    should_deploy = normalized_type in {"search_ingest", "deploy_site", "rebuild_deploy"} and bool(
        options.get("auto_deploy", True)
    )

    if should_refresh:
        with _BLOG_PUBLISH_LOCK:
            progress("discovering candidates")
            providers = _build_discovery_providers(
                _safe_list(options.get("providers")) or ["arxiv", "openalex", "semantic_scholar"],
                db_path=config.db_path,
                refresh_provider_cache=bool(options.get("refresh_provider_cache")),
            )
            profiles = _safe_list(options.get("profiles")) or [profile.name for profile in default_profiles()]
            _apply_search_task_dates(config.db_path, profiles, options)
            result = run_launch_refresh(
                db_path=config.db_path,
                paper_db_path=config.paper_db_path,
                providers=providers,
                profile_names=profiles,
                limit_per_profile=int(options.get("limit_per_profile") or 30),
                select_limit=int(options.get("select_limit") or 10),
                min_score=float(options.get("min_score") or 0.6),
                papi_executable=config.papi_executable,
                out_dir=config.project_dir / "exports" / "mvp-current",
                site_dir=config.project_dir / "exports" / "site-current",
                semantic=bool(options.get("semantic", False)),
                refresh_facts=bool(options.get("refresh_facts", False)),
                fact_error_policy="warn",
                progress_callback=progress,
            )
            logs.append(f"refresh completed: papers={result.mvp.papers_seen} approved={result.approved_count}")

    publish_lock_acquired = should_rebuild or should_deploy
    if publish_lock_acquired:
        _BLOG_PUBLISH_LOCK.acquire()
    try:
        if should_rebuild:
            with tempfile.TemporaryDirectory(prefix="airesearch-admin-") as tmp:
                progress("preparing publish database")
                tmp_root = Path(tmp)
                tmp_db = tmp_root / "airesearch.sqlite3"
                tmp_out = tmp_root / "mvp"
                hidden = _copy_db_without_hidden(config, tmp_db)
                result = run_mvp_pipeline(
                    db_path=tmp_db,
                    paper_db_path=config.paper_db_path,
                    out_dir=tmp_out,
                    fact_error_policy="warn",
                    concurrency=5,
                    excluded_paper_keys=hidden,
                    progress_callback=progress,
                )
                logs.append(f"site generated: {result.site_path}")
                progress("publishing static site")
                publish = publish_static_site(tmp_out / "bundle", config.project_dir / "exports" / "site-current")
                logs.append(f"site published: {publish.entrypoint}")

        if should_deploy:
            progress("deploying to nginx root")
            deploy = subprocess.run(
                [
                    "sudo",
                    "env",
                    f"PROJECT_ROOT={config.project_dir}",
                    f"SITE_DIR={config.project_dir / 'exports' / 'site-current'}",
                    "bash",
                    str(config.deploy_script),
                ],
                cwd=config.project_dir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=600,
                check=False,
            )
            logs.append(deploy.stdout.strip())
            if deploy.returncode != 0:
                raise RuntimeError(f"deploy failed with code {deploy.returncode}")
    finally:
        if publish_lock_acquired:
            _BLOG_PUBLISH_LOCK.release()
    return "\n".join(logs)


def start_job(config: AdminConfig, job_type: str, options: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_schema(config.db_path)
    with connect(config.db_path) as conn:
        job_id = _job_insert(conn, job_type, options)
    _ensure_worker(config)
    return {"job_id": job_id, "status": "queued"}


def _layout_job_paper_key(row: Any) -> str:
    params = _json_loads(row["params_json"] if row is not None else "", {})
    if not isinstance(params, dict):
        return ""
    return str(params.get("paperKey") or params.get("paper_key") or "")


def enqueue_layout_parse_if_needed(config: AdminConfig, paper_key: str) -> dict[str, Any]:
    paper_key = _safe_text(paper_key, limit=300)
    if not paper_key:
        return {"job_id": None, "status": "skipped", "reason": "missing_paper_key"}
    ensure_admin_schema(config.db_path)
    with connect(config.db_path) as conn:
        paper = conn.execute("select 1 from papers where paper_key = ?", (paper_key,)).fetchone()
        if paper is None:
            return {"job_id": None, "status": "skipped", "reason": "paper_not_found"}
        completed = conn.execute(
            """
            select id from paper_layout_runs
            where paper_key = ? and status in ('completed', 'skipped')
            order by id desc
            limit 1
            """,
            (paper_key,),
        ).fetchone()
        if completed is not None:
            return {"job_id": None, "status": "skipped", "reason": "layout_exists", "run_id": completed["id"]}
        for row in conn.execute(
            """
            select id, params_json from admin_jobs
            where job_type = 'paper_layout_parse' and status in ('queued', 'running')
            order by id desc
            """
        ).fetchall():
            if _layout_job_paper_key(row) == paper_key:
                return {"job_id": row["id"], "status": "existing", "reason": "layout_job_active"}
    return start_job(config, "paper_layout_parse", {"paperKey": paper_key, "force": False, "priority": 0})


def _claim_next_job(db_path: Path) -> dict[str, Any] | None:
    ensure_admin_schema(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            select * from admin_jobs
            where status = 'queued'
            order by priority desc, id
            limit 1
            """
        ).fetchone()
        if row is None:
            return None
        now = _admin_now()
        conn.execute(
            """
            update admin_jobs
            set status = 'running', message = 'starting', current_step = 'starting', started_at = ?
            where id = ? and status = 'queued'
            """,
            (now, row["id"]),
        )
        conn.commit()
        payload = dict(row)
        payload["status"] = "running"
        payload["params"] = _json_loads(payload.get("params_json"), {})
        return payload


def _worker_loop(config: AdminConfig) -> None:
    global _WORKER_THREAD
    try:
        while True:
            job = _claim_next_job(config.db_path)
            if job is None:
                return
            job_id = int(job["id"])
            try:
                params = job.get("params") if isinstance(job.get("params"), dict) else {}
                if str(job["job_type"]) == "paper_blog_generate":
                    log = run_blog_generation_job(config, job_id=job_id, options=params)
                elif str(job["job_type"]) == "paper_layout_parse":
                    log = run_layout_parse_job(config, job_id=job_id, options=params)
                else:
                    log = publish_with_overrides(
                        config,
                        job_id=job_id,
                        job_type=str(job["job_type"]),
                        options=params,
                    )
            except Exception as exc:  # pragma: no cover - surfaced in admin UI
                status = "publish_failed" if isinstance(exc, PaperBlogPublishError) else "failed"
                _job_update(
                    config.db_path,
                    job_id,
                    status=status,
                    message=str(exc),
                    log=traceback.format_exc(),
                    result=getattr(exc, "result", None),
                )
                continue
            job_result = None
            if str(job["job_type"]) == "paper_blog_generate":
                detail = paper_blog_detail(config.db_path, str(params.get("paperKey") or params.get("paper_key") or ""))
                post = detail.get("post") or {}
                current_id = post.get("current_version_id")
                current = next(
                    (version for version in detail.get("versions") or [] if version.get("id") == current_id),
                    {},
                )
                job_result = {
                    "paperKey": post.get("paper_key"),
                    "versionId": current_id,
                    "versionNumber": current.get("version_number"),
                    "wordCount": post.get("word_count"),
                    "status": post.get("status"),
                }
            elif str(job["job_type"]) == "paper_layout_parse":
                detail = paper_layout_detail(config.db_path, str(params.get("paperKey") or params.get("paper_key") or ""))
                latest = detail.get("latest_run") or {}
                job_result = {
                    "paperKey": params.get("paperKey") or params.get("paper_key"),
                    "runId": latest.get("id"),
                    "status": latest.get("status"),
                    "artifactCount": (latest.get("stats") or {}).get("artifact_count"),
                    "blockCount": (latest.get("stats") or {}).get("block_count"),
                }
            _job_update(
                config.db_path,
                job_id,
                status="completed",
                message="done",
                log=log,
                result=job_result,
            )
    finally:
        with _WORKER_LOCK:
            _WORKER_THREAD = None


def _ensure_worker(config: AdminConfig) -> None:
    global _WORKER_THREAD
    with _WORKER_LOCK:
        if _WORKER_THREAD is not None and _WORKER_THREAD.is_alive():
            return
        _WORKER_THREAD = threading.Thread(target=_worker_loop, args=(config,), daemon=True)
        _WORKER_THREAD.start()


ADMIN_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIResearch Admin</title>
<style>
:root{color-scheme:light;--bg:#eee9df;--rail:#201f1b;--rail2:#2d2b25;--panel:#fffdf8;--ink:#24211c;--muted:#706a60;--line:#d7cec0;--soft:#eef4ef;--accent:#0f6b5f;--accent2:#b56a2b;--danger:#b42318;--ok:#167356}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
button,input,textarea,select{font:inherit}button{border:1px solid var(--line);background:#fffaf2;color:var(--ink);padding:9px 12px;border-radius:7px;cursor:pointer}button.primary{background:var(--accent);border-color:var(--accent);color:white}button.warning{background:#fff2df;border-color:#e2ba84;color:#804713}button.danger{color:var(--danger);border-color:#e2aaa5}button:disabled{opacity:.55;cursor:not-allowed}
input,textarea,select{width:100%;border:1px solid var(--line);border-radius:7px;background:white;padding:9px}textarea{min-height:86px;resize:vertical}label{display:block;font-size:12px;color:var(--muted);margin:12px 0 5px}.check{display:flex;gap:8px;align-items:center;margin-top:12px}.check input{width:auto}
.shell{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100dvh}.sidebar{background:linear-gradient(180deg,var(--rail),var(--rail2));color:#f7efe3;padding:20px 16px;position:sticky;top:0;height:100dvh}.brand{font-size:18px;font-weight:700;margin-bottom:6px}.brand-sub{font-size:12px;color:#bfb6a6;margin-bottom:24px}.nav{display:grid;gap:7px}.nav button{width:100%;text-align:left;border:0;background:transparent;color:#d8d0c3;padding:11px 12px;border-radius:7px}.nav button.active,.nav button:hover{background:rgba(255,255,255,.1);color:#fff}.sidebar-meta{position:absolute;left:16px;right:16px;bottom:18px;font-size:12px;color:#bfb6a6;line-height:1.6}
.workspace{min-width:0;padding:18px 22px 30px}.topline{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:16px}.topline h1{font-size:22px;margin:0}.topline-actions{display:flex;align-items:center;justify-content:flex-end;gap:10px;min-width:0}.home-link{display:inline-flex;align-items:center;justify-content:center;min-height:34px;padding:0 13px;border:1px solid var(--line);border-radius:999px;background:#fffaf2;color:var(--ink);text-decoration:none;white-space:nowrap}.home-link:hover{border-color:#b8a992;background:#fff}.notice{font-size:13px;color:var(--muted);min-height:20px}.notice.bad{color:var(--danger)}
.view{display:none}.view.active{display:block}.grid{display:grid;gap:14px}.grid.two{grid-template-columns:minmax(0,1fr) minmax(320px,420px)}.grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:15px;min-width:0}.card h2,.card h3{margin:0 0 10px}.metric{font-size:26px;font-weight:750}.muted{color:var(--muted)}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.chips{display:flex;gap:7px;flex-wrap:wrap}.chip{padding:6px 9px;border:1px solid var(--line);border-radius:999px;background:#fff;font-size:12px}.chip input{width:auto;margin-right:5px}
.job-list{display:grid;gap:10px}.job{border:1px solid var(--line);border-radius:8px;background:#fff;padding:12px}.job-head{display:flex;justify-content:space-between;gap:10px}.badge{font-size:12px;padding:4px 8px;border-radius:999px;background:#eee}.badge.queued{background:#efe6d4}.badge.running{background:#ddecff}.badge.completed{background:#dff3e8;color:var(--ok)}.badge.failed{background:#fae1de;color:var(--danger)}.badge.canceled{background:#eee}.job small{display:block;color:var(--muted);margin-top:5px}.job pre{max-height:180px;overflow:auto;background:#27241f;color:#fff6ea;border-radius:7px;padding:10px;white-space:pre-wrap}
.paper-layout{display:grid;grid-template-columns:330px minmax(0,1fr);gap:14px}.paper-sidebar-card,.paper-editor{background:var(--panel);border:1px solid var(--line);border-radius:8px;min-width:0}.paper-sidebar-card{padding:12px}.paper-search{display:grid;gap:8px}.paper-list{max-height:calc(100dvh - 230px);overflow:auto;border:1px solid var(--line);border-radius:8px;background:#fff;margin-top:10px}.paper-item{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid #eee4d7;border-radius:0;background:#fff;padding:12px 13px}.paper-item:hover,.paper-item.active{background:var(--soft)}.paper-item strong{display:block;font-size:13px;line-height:1.35}.paper-item small{display:block;color:var(--muted);margin-top:5px;line-height:1.35}.paper-tags{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.mini-tag{font-size:11px;border:1px solid #d9cbbc;background:#fff8eb;color:#6b4f2b;border-radius:999px;padding:2px 6px}.mini-tag.draft{background:#e9f2ee;color:#17453d;border-color:#c0d9ce}.mini-tag.hidden-tag{background:#fae1de;color:var(--danger);border-color:#e8b8b2}.hidden{opacity:.55}.paper-editor{padding:0;overflow:hidden}.paper-empty{padding:34px;text-align:center;color:var(--muted)}.paper-edit-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;padding:16px;border-bottom:1px solid var(--line);background:#fffaf2}.paper-edit-title{min-width:0}.paper-edit-title h2{font-size:19px;margin:0;line-height:1.25;overflow-wrap:anywhere}.paper-edit-title small{display:block;margin-top:6px;color:var(--muted);overflow-wrap:anywhere}.paper-status{display:grid;gap:8px;justify-items:end;min-width:260px}.paper-status-row{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}.paper-top-actions{margin-top:0;justify-content:flex-end}.paper-edit-body{display:grid;grid-template-columns:minmax(260px,320px) minmax(440px,1fr);gap:14px;padding:14px}.paper-panel{background:#fff;border:1px solid var(--line);border-radius:8px;padding:13px;min-width:0}.paper-panel h3{font-size:15px;margin:0 0 10px}.paper-dirty{font-size:12px;color:var(--accent2)}.paper-dirty.clean{color:var(--muted)}.fact{border:1px solid var(--line);border-radius:8px;padding:12px;margin:10px 0;background:#fff}.fact-head{display:grid;grid-template-columns:130px minmax(120px,1fr) 86px;gap:8px}.fact-toolbar{display:flex;justify-content:space-between;gap:10px;align-items:center}.fact-type-label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.status-tabs{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}.status-tabs button.active{background:var(--accent);color:white;border-color:var(--accent)}
.profile-shell{display:grid;grid-template-columns:310px minmax(0,1fr);gap:14px}.profile-rail{background:#f6f0e6;border:1px solid var(--line);border-radius:8px;padding:12px}.profile-toolbar{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:end}.profile-list{display:grid;gap:8px;margin-top:12px;max-height:calc(100dvh - 290px);overflow:auto}.profile-pill{width:100%;text-align:left;background:#fff;border:1px solid #e4d8c8;border-radius:8px;padding:11px}.profile-pill.active{background:#1f3d37;color:#fff;border-color:#1f3d37}.profile-pill strong{display:block;font-size:13px;overflow-wrap:anywhere}.profile-pill small{display:block;color:var(--muted);margin-top:5px;line-height:1.35}.profile-pill.active small{color:#d7e5df}.profile-editor{background:#fffdf8;border:1px solid var(--line);border-radius:8px;padding:16px;min-width:0}.profile-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:10px}.profile-head .danger{white-space:nowrap;min-width:82px;text-align:center}.profile-title{min-width:0}.profile-title h2{margin:0;font-size:20px;overflow-wrap:anywhere}.profile-title p{margin:6px 0 0;color:var(--muted);font-size:13px}.keyword-board{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px;margin-top:12px}.keyword-list{display:flex;flex-wrap:wrap;gap:8px;min-height:42px}.keyword-token{display:inline-flex;align-items:center;gap:7px;max-width:100%;padding:7px 9px;border-radius:999px;background:#e9f2ee;border:1px solid #c6ddd3;color:#173d35;font-size:12px}.keyword-token span{overflow-wrap:anywhere}.keyword-token button{border:0;background:transparent;padding:0;color:#406a60;line-height:1}.keyword-add{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;margin-top:10px}.profile-empty{border:1px dashed var(--line);border-radius:8px;padding:34px;text-align:center;background:#fff;color:var(--muted)}.danger-zone{margin-top:14px;padding-top:12px;border-top:1px solid #eaded0}
@media(max-width:1100px){.shell{grid-template-columns:1fr}.sidebar{position:static;height:auto}.sidebar-meta{position:static;margin-top:18px}.grid.two,.grid.three,.paper-layout,.paper-edit-body{grid-template-columns:1fr}.paper-list{max-height:none}}
@media(max-width:1100px){.profile-shell{grid-template-columns:1fr}.profile-list{max-height:none}}
.single-ingest-card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:15px;margin-bottom:14px}.ingest-input-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px}.ingest-input-row input{width:100%}.ingest-results{margin-top:12px;max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:8px}.ingest-result{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:start;padding:12px;border-bottom:1px solid #eee4d7;background:#fff}.ingest-result:last-child{border-bottom:0}.ingest-result-info{min-width:0}.ingest-result-info strong{display:block;font-size:13px;line-height:1.35;overflow-wrap:anywhere}.ingest-result-info small{display:block;color:var(--muted);margin-top:5px;line-height:1.4;overflow-wrap:anywhere}.ingest-result-info .arxiv-id{font-size:11px;color:var(--accent);margin-top:3px}.ingest-result-actions{display:flex;gap:6px;align-items:center;white-space:nowrap}.ingest-spinner{display:inline-block;width:14px;height:14px;border:2px solid #ccc;border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="shell">
  <aside class="sidebar">
    <div class="brand">AIResearch Admin</div>
    <div class="brand-sub">搜索、入库、发布与论文维护</div>
    <nav class="nav">
      <button data-view="overview">工作台</button>
      <button data-view="search">搜索入库</button>
      <button data-view="publish">重建部署</button>
      <button data-view="tasks">任务中心</button>
      <button data-view="papers" class="active">论文管理</button>
      <button data-view="profiles">搜索配置</button>
    </nav>
    <div class="sidebar-meta"><div id="sideStats">加载中</div><div>公网后台 · Basic Auth</div></div>
  </aside>
  <main class="workspace">
    <div class="topline"><h1 id="viewTitle">论文管理</h1><div class="topline-actions"><a class="home-link" href="/niu-secretary/">返回主页</a><div id="notice" class="notice" aria-live="polite"></div></div></div>

    <section id="view-overview" class="view">
      <div class="grid three">
        <div class="card"><div class="muted">论文总数</div><div id="mPapers" class="metric">0</div></div>
        <div class="card"><div class="muted">已隐藏</div><div id="mHidden" class="metric">0</div></div>
        <div class="card"><div class="muted">队列中 / 运行中</div><div id="mQueue" class="metric">0</div></div>
      </div>
      <div class="grid two" style="margin-top:14px">
        <div class="card"><h2>快速操作</h2><p class="muted">搜索入库和重建部署都会进入任务队列，不会阻塞当前页面。</p><div class="actions"><button class="primary" onclick="showView('search')">创建搜索任务</button><button onclick="showView('publish')">进入发布面板</button></div></div>
        <div class="card"><h2>最新任务</h2><div id="recentJobs" class="job-list"></div></div>
      </div>
    </section>

    <section id="view-search" class="view">
      <div class="single-ingest-card">
        <h2>单论文入库</h2>
        <p class="muted">输入论文标题、arXiv ID（如 1706.03762）、URL 或 DOI。搜索匹配 arXiv 后一键入库，也可直接入库（支持 URL 直接传给 papi）。</p>
        <div class="ingest-input-row">
          <input id="ingestInput" placeholder="论文标题 / arXiv ID / URL / DOI" onkeydown="if(event.key==='Enter')searchArxiv()">
          <button class="primary" onclick="searchArxiv()">搜索匹配</button>
          <button onclick="directIngest()">直接入库</button>
        </div>
        <div id="ingestResults" class="ingest-results" style="display:none"></div>
      </div>
      <div class="grid two">
        <div class="card">
          <h2>创建搜索入库任务</h2>
          <label>搜索 profile</label><div id="searchProfiles" class="chips"></div>
          <label>搜索来源</label><div id="searchProviders" class="chips"></div>
          <div class="row"><div><label>每个 profile 搜索数量</label><input id="limitPerProfile" type="number" min="1" max="200" value="30"></div><div><label>入库选择数量</label><input id="selectLimit" type="number" min="1" max="100" value="10"></div></div>
          <div class="row"><div><label>最低分数</label><input id="minScore" type="number" min="0" max="1" step="0.05" value="0.6"></div><div><label>优先级</label><input id="searchPriority" type="number" min="0" max="9" value="0"></div></div>
          <div class="row"><div><label>primary_since</label><input id="primarySince" type="date"></div><div><label>exception_since</label><input id="exceptionSince" type="date"></div></div>
          <label class="check"><input id="refreshProviderCache" type="checkbox">刷新 provider cache</label>
          <label class="check"><input id="refreshFacts" type="checkbox">重新抽取 facts</label>
          <label class="check"><input id="searchAutoDeploy" type="checkbox" checked>完成后自动部署上线</label>
          <div class="actions"><button class="primary" onclick="queueSearch()">加入搜索队列</button></div>
        </div>
        <div class="card"><h2>搜索队列</h2><div id="searchJobs" class="job-list"></div></div>
      </div>
    </section>

    <section id="view-publish" class="view">
      <div class="grid two">
        <div class="card">
          <h2>发布流水线</h2>
          <p class="muted">重建会应用隐藏论文规则并重新生成站点；部署会把当前 exports/site-current 发布到 nginx 目录。</p>
          <div class="actions"><button onclick="queuePublish('rebuild_site')">仅重建站点</button><button onclick="queuePublish('deploy_site')">仅部署当前站点</button><button class="primary" onclick="queuePublish('rebuild_deploy')">重建并部署</button></div>
        </div>
        <div class="card"><h2>发布任务</h2><div id="publishJobs" class="job-list"></div></div>
      </div>
    </section>

    <section id="view-tasks" class="view">
      <div class="card"><h2>任务中心</h2><div class="status-tabs" id="taskTabs"></div><div id="allJobs" class="job-list"></div></div>
    </section>

    <section id="view-papers" class="view active">
      <div class="paper-layout">
        <aside class="paper-sidebar-card">
          <div class="paper-search">
            <label>论文检索</label>
            <input id="q" placeholder="搜索标题、key、arXiv">
          </div>
          <div id="papers" class="paper-list"></div>
        </aside>
        <div id="detail" class="paper-editor"><div class="paper-empty">选择一篇论文开始编辑。</div></div>
      </div>
    </section>

    <section id="view-profiles" class="view">
      <div class="profile-shell">
        <aside class="profile-rail">
          <div class="profile-toolbar">
            <div><label>新建搜索方向</label><input id="newProfileName" placeholder="例如 diffusion_models"></div>
            <button class="primary" onclick="createProfile()">新建</button>
          </div>
          <div id="profiles" class="profile-list"></div>
        </aside>
        <div id="profileEditor" class="profile-editor"></div>
      </div>
    </section>
  </main>
</div>
<script>
const api = p => location.pathname.replace(/\/$/, "") + "/api" + p;
let state = null, selected = null, previousSelected = null, currentPaper = null, paperBaseline = null, taskFilter = "all", selectedProfile = null, draftKeywords = [], initialViewApplied = false;
const titles = {overview:"工作台", search:"搜索入库", publish:"重建部署", tasks:"任务中心", papers:"论文管理", profiles:"搜索配置"};
function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]))}
function setNotice(text,bad=false){notice.textContent=text||"";notice.className="notice"+(bad?" bad":"")}
async function req(path, opts={}){const r=await fetch(api(path),{headers:{"content-type":"application/json"},...opts});if(!r.ok){let t=await r.text();try{t=JSON.parse(t).error||t}catch{}throw new Error(t)}return r.json()}
async function load(){state=await req("/state"); renderAll(); if(!initialViewApplied){initialViewApplied=true;const requested=new URLSearchParams(location.search).get("view")||location.hash.replace("#","")||"papers";if(requested&&titles[requested])showView(requested,{skipDirty:true})}}
async function confirmPaperCommit(message="当前论文有未保存修改。是否先更新到数据库？"){if(!hasPaperDirty())return true;if(confirm(message)){await savePaper(selected);return !hasPaperDirty()}setNotice("已保留当前页面上的未保存修改",true);return false}
async function showView(name,opts={}){if(!opts.skipDirty&&name!=="papers"&&hasPaperDirty()){const ok=await confirmPaperCommit("当前论文有未保存修改。离开论文管理前是否更新到数据库？");if(!ok)return}document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));document.querySelector("#view-"+name).classList.add("active");document.querySelectorAll(".nav button").forEach(b=>b.classList.toggle("active",b.dataset.view===name));viewTitle.textContent=titles[name]||name}
function renderAll(){renderMetrics();renderSearchForm();renderJobs();renderPapers();renderProfiles()}
function renderMetrics(){const s=state.stats;mPapers.textContent=s.paper_count;mHidden.textContent=s.hidden_count;mQueue.textContent=(s.job_status_counts.queued||0)+" / "+(s.job_status_counts.running||0);sideStats.textContent=`${s.visible_count} 可见论文 · ${s.hidden_count} 隐藏`}
function selectedValues(sel){return Array.from(document.querySelectorAll(sel+":checked")).map(i=>i.value)}
function renderSearchForm(){searchProfiles.innerHTML=state.profiles.map((p,i)=>`<label class="chip"><input type="checkbox" name="searchProfile" value="${esc(p.name)}" ${i<2?"checked":""}>${esc(p.name)}</label>`).join("");searchProviders.innerHTML=state.providers.map((p,i)=>`<label class="chip"><input type="checkbox" name="searchProvider" value="${esc(p)}" ${i<3?"checked":""}>${esc(p)}</label>`).join("");const first=state.profiles[0]||{};if(!primarySince.value)primarySince.value=(first.primary_since||"").slice(0,10);if(!exceptionSince.value)exceptionSince.value=(first.exception_since||"").slice(0,10)}
function jobTypeLabel(t){return {search_ingest:"搜索入库",refresh:"搜索入库",rebuild_site:"重建站点",deploy_site:"部署站点",rebuild_deploy:"重建部署",rebuild:"重建部署"}[t]||t}
function statusLabel(s){return {queued:"待完成",running:"正在处理",completed:"已结束",failed:"失败",canceled:"已取消"}[s]||s}
function jobHtml(j){const p=j.params||{};const summary=j.job_type.includes("search")||j.job_type==="refresh"?`profiles=${(p.profiles||[]).length||"默认"} · limit=${p.limit_per_profile||30} · select=${p.select_limit||10}`:(p.auto_deploy===false?"不自动部署":"自动部署");return `<article class="job"><div class="job-head"><strong>${jobTypeLabel(j.job_type)} #${j.id}</strong><span class="badge ${esc(j.status)}">${statusLabel(j.status)}</span></div><small>${esc(j.message||j.current_step||"")}</small><small>${esc(summary)}</small><small>创建 ${esc(j.created_at||j.started_at||"")} ${j.finished_at?(" · 结束 "+esc(j.finished_at)):""}</small>${j.status==="queued"?`<div class="actions"><button class="danger" onclick="cancelJob(${j.id})">取消排队</button></div>`:""}${j.log?`<details><summary>日志</summary><pre>${esc(j.log)}</pre></details>`:""}</article>`}
function renderJobs(){const jobs=state.jobs||[];recentJobs.innerHTML=jobs.slice(0,4).map(jobHtml).join("")||"<p class='muted'>暂无任务</p>";searchJobs.innerHTML=jobs.filter(j=>["search_ingest","refresh"].includes(j.job_type)).map(jobHtml).join("")||"<p class='muted'>暂无搜索任务</p>";publishJobs.innerHTML=jobs.filter(j=>!["search_ingest","refresh"].includes(j.job_type)).map(jobHtml).join("")||"<p class='muted'>暂无发布任务</p>";taskTabs.innerHTML=["all",...state.job_statuses].map(s=>`<button class="${taskFilter===s?"active":""}" onclick="taskFilter='${s}';renderJobs()">${s==="all"?"全部":statusLabel(s)}</button>`).join("");allJobs.innerHTML=jobs.filter(j=>taskFilter==="all"||j.status===taskFilter).map(jobHtml).join("")||"<p class='muted'>没有匹配任务</p>"}
async function queueSearch(){try{setNotice("正在加入队列...");const body={profiles:selectedValues('input[name=searchProfile]'),providers:selectedValues('input[name=searchProvider]'),limit_per_profile:+limitPerProfile.value||30,select_limit:+selectLimit.value||10,min_score:+minScore.value||0.6,primary_since:primarySince.value,exception_since:exceptionSince.value,refresh_provider_cache:refreshProviderCache.checked,refresh_facts:refreshFacts.checked,auto_deploy:searchAutoDeploy.checked,priority:+searchPriority.value||0};await req("/jobs/search_ingest",{method:"POST",body:JSON.stringify(body)});await load();showView("tasks");setNotice("搜索任务已加入队列")}catch(e){setNotice(e.message,true)}}
async function queuePublish(type){try{setNotice("正在加入队列...");await req("/jobs/"+type,{method:"POST",body:JSON.stringify({auto_deploy:type!=="rebuild_site"})});await load();showView("tasks");setNotice("发布任务已加入队列")}catch(e){setNotice(e.message,true)}}
async function cancelJob(id){try{await req("/jobs/"+id+"/cancel",{method:"POST",body:"{}"});await load();setNotice("已取消排队任务")}catch(e){setNotice(e.message,true)}}
let ingestSearching=false;async function searchArxiv(){if(ingestSearching)return;const q=ingestInput.value.trim();if(!q){setNotice("请输入论文标题或ID",true);return}ingestSearching=true;setNotice("正在搜索 arXiv...");ingestResults.style.display="block";ingestResults.innerHTML=`<div style="padding:20px;text-align:center"><span class="ingest-spinner"></span> 搜索中...</div>`;try{const data=await req("/papers/search-arxiv",{method:"POST",body:JSON.stringify({query:q,limit:10})});renderIngestResults(data.results,q)}catch(e){setNotice(e.message,true);ingestResults.innerHTML=`<div class="paper-empty">搜索失败：${esc(e.message)}</div>`}finally{ingestSearching=false}}
function renderIngestResults(results,query){if(!results.length){ingestResults.innerHTML=`<div class="paper-empty">arXiv 未找到匹配论文："${esc(query)}"</div>`;setNotice("arXiv 未找到匹配论文",true);return}setNotice(`找到 ${results.length} 篇匹配论文`);ingestResults.innerHTML=results.map(r=>`<div class="ingest-result"><div class="ingest-result-info"><strong>${esc(r.title)}</strong><small>${(r.authors||[]).slice(0,3).map(esc).join("，")}${r.authors.length>3?" 等":""}</small><small>${esc(r.published||"")} · ${esc((r.abstract||"").slice(0,200))}</small>${r.arxiv_id?`<span class="arxiv-id">arXiv: ${esc(r.arxiv_id)}</span>`:""}</div><div class="ingest-result-actions"><button class="primary" onclick="ingestFromResult('${esc(r.arxiv_id||r.title)}')">入库</button></div></div>`).join("")}
async function ingestFromResult(input){if(!input)return;setNotice(`正在入库：${input}...`);try{const result=await req("/papers/ingest",{method:"POST",body:JSON.stringify({input})});if(result.status==="success"){setNotice(`入库成功：${result.paper_key||input}`);ingestInput.value="";await load()}else{setNotice(`入库失败：${result.error||"未知错误"}`,true)}}catch(e){setNotice(e.message,true)}}
async function directIngest(){const input=ingestInput.value.trim();if(!input){setNotice("请输入论文标题或ID",true);return}setNotice(`正在直接入库：${input}...`);try{const result=await req("/papers/ingest",{method:"POST",body:JSON.stringify({input})});if(result.status==="success"){setNotice(`入库成功：${result.paper_key||input}`);ingestInput.value="";await load()}else{setNotice(`入库失败：${result.error||"未知错误"}`,true)}}catch(e){setNotice(e.message,true)}}
async function queueSearch(){
function paperBasePayload(p){return {hidden:!!p.hidden,arxiv_id:p.arxiv_id||"",paper_url:p.paper_url||"",github_url:p.github_url||"",facts:(p.facts||[]).map(f=>({id:f.id,fact_type:f.fact_type||"",name:f.name||"",confidence:String(f.confidence??""),statement:f.statement||""})),new_fact_type:"method",new_fact_name:"",new_fact_confidence:"0.9",new_fact_statement:""}}
function normalizePaperPayload(v){return {hidden:!!v.hidden,arxiv_id:(v.arxiv_id||"").trim(),paper_url:(v.paper_url||"").trim(),github_url:(v.github_url||"").trim(),facts:(v.facts||[]).map(f=>({id:+f.id,fact_type:f.fact_type||"",name:f.name||"",confidence:String(f.confidence??"").trim(),statement:f.statement||""})),new_fact_type:v.new_fact_type||"method",new_fact_name:v.new_fact_name||"",new_fact_confidence:String(v.new_fact_confidence||"0.9").trim(),new_fact_statement:v.new_fact_statement||""}}
function collectPaperPayload(){return normalizePaperPayload({hidden:hidden.checked,arxiv_id:arxiv.value,paper_url:paperUrl.value,github_url:githubUrl.value,facts:Array.from(document.querySelectorAll(".fact[data-id]")).map(el=>({id:el.dataset.id,fact_type:el.querySelector(".ftype").value,name:el.querySelector(".fname").value,confidence:el.querySelector(".fconf").value,statement:el.querySelector(".fstmt").value})),new_fact_type:newType.value,new_fact_name:newName.value,new_fact_confidence:newConf.value,new_fact_statement:newStatement.value})}
function samePayload(a,b){return JSON.stringify(normalizePaperPayload(a||{}))===JSON.stringify(normalizePaperPayload(b||{}))}
function hasPaperDirty(){return !!(selected&&paperBaseline&&document.querySelector("#paperUrl")&&!samePayload(collectPaperPayload(),paperBaseline))}
function updatePaperDirty(){const el=document.querySelector("#paperDirty");if(!el)return;const dirty=hasPaperDirty();el.textContent=dirty?"有未保存修改":"已同步到数据库状态";el.className="paper-dirty"+(dirty?"":" clean")}
function bindPaperDirtyEvents(){detail.querySelectorAll("input,textarea,select").forEach(el=>el.addEventListener("input",updatePaperDirty));detail.querySelectorAll("input[type=checkbox],select").forEach(el=>el.addEventListener("change",updatePaperDirty));updatePaperDirty()}
async function openPaper(key, skipDirty=false){try{if(selected&&selected!==key&&!skipDirty&&hasPaperDirty()){const ok=await confirmPaperCommit("当前论文有未保存修改。切换论文前是否更新到数据库？");if(!ok)return}if(selected&&selected!==key)previousSelected=selected;selected=key;renderPapers();const p=await req("/papers/"+encodeURIComponent(key));currentPaper=p;paperBaseline=paperBasePayload(p);renderPaperEditor(p);setNotice(p.draft_updated_at?"这篇论文有草稿，可选择载入或丢弃。":"")}catch(e){setNotice(e.message,true)}}
function renderPaperEditor(p){detail.innerHTML=`<div class="paper-edit-head"><div class="paper-edit-title"><h2>${esc(p.title)}</h2><small>${esc(p.paper_key)}${p.draft_updated_at?(" · 草稿 "+esc(p.draft_updated_at)):""} · <span id="paperDirty" class="paper-dirty clean">已同步到数据库状态</span></small></div><div class="paper-status"><div class="paper-status-row">${p.draft_updated_at?`<span class="mini-tag draft">有草稿</span>`:""}${p.hidden?`<span class="mini-tag hidden-tag">已隐藏</span>`:""}${previousSelected?`<button onclick="openPaper('${esc(previousSelected)}')">返回上一论文</button>`:""}</div><div class="actions paper-top-actions"><button onclick="resetPaperEditor()">撤销修改</button><button onclick="savePaperDraft('${esc(p.paper_key)}')">保存草稿</button><button class="primary" onclick="savePaper('${esc(p.paper_key)}')">更新到数据库</button></div></div></div><div class="paper-edit-body"><section class="paper-panel"><h3>论文链接与状态</h3><label class="check"><input id="hidden" type="checkbox" ${p.hidden?"checked":""}>隐藏该论文</label><label>arXiv ID</label><input id="arxiv" value="${esc(p.arxiv_id)}"><label>论文链接</label><input id="paperUrl" value="${esc(p.paper_url)}"><label>GitHub 链接</label><input id="githubUrl" value="${esc(p.github_url)}"><div class="actions">${p.draft_updated_at?`<button onclick="loadPaperDraft()">载入草稿</button><button class="danger" onclick="discardPaperDraft('${esc(p.paper_key)}')">丢弃草稿</button>`:""}<button class="danger" onclick="deletePaper('${esc(p.paper_key)}')">删除论文</button></div></section><section class="paper-panel"><div class="fact-toolbar"><h3>Facts</h3><span class="muted">${(p.facts||[]).length} 条</span></div><div>${(p.facts||[]).map(factHtml).join("")||"<p class='muted'>暂无 facts</p>"}</div><div class="fact"><div class="fact-toolbar"><span class="fact-type-label">新增 fact</span></div><div class="fact-head"><select id="newType">${state.fact_types.map(t=>`<option>${t}</option>`).join("")}</select><input id="newName" placeholder="name"><input id="newConf" value="0.9"></div><label>statement</label><textarea id="newStatement"></textarea></div></section></div>`;bindPaperDirtyEvents()}
function applyPaperPayload(payload){const v=normalizePaperPayload(payload);hidden.checked=v.hidden;arxiv.value=v.arxiv_id;paperUrl.value=v.paper_url;githubUrl.value=v.github_url;document.querySelectorAll(".fact[data-id]").forEach((el,i)=>{const f=v.facts.find(x=>String(x.id)===String(el.dataset.id))||v.facts[i];if(!f)return;el.querySelector(".ftype").value=f.fact_type;el.querySelector(".fname").value=f.name;el.querySelector(".fconf").value=f.confidence;el.querySelector(".fstmt").value=f.statement});newType.value=v.new_fact_type;newName.value=v.new_fact_name;newConf.value=v.new_fact_confidence;newStatement.value=v.new_fact_statement;updatePaperDirty()}
function loadPaperDraft(){if(currentPaper&&currentPaper.draft){applyPaperPayload(currentPaper.draft);setNotice("草稿已载入，点击更新到数据库才会正式生效")}}
function resetPaperEditor(){if(currentPaper){renderPaperEditor(currentPaper);setNotice("已撤销本页未保存修改")}}
function factHtml(f){return `<div class="fact" data-id="${f.id}"><div class="fact-toolbar"><span class="fact-type-label">#${f.id}</span><button class="danger" onclick="deleteFact(${f.id})">删除</button></div><div class="fact-head"><select class="ftype">${state.fact_types.map(t=>`<option ${t===f.fact_type?"selected":""}>${t}</option>`).join("")}</select><input class="fname" value="${esc(f.name)}"><input class="fconf" value="${esc(f.confidence)}"></div><label>statement</label><textarea class="fstmt">${esc(f.statement)}</textarea></div>`}
async function savePaperDraft(key=selected){if(!key||!document.querySelector("#paperUrl"))return;await req("/papers/"+encodeURIComponent(key)+"/draft",{method:"POST",body:JSON.stringify(collectPaperPayload())});await load();setNotice("草稿已保存")}
async function discardPaperDraft(key=selected){if(!key)return;await req("/papers/"+encodeURIComponent(key)+"/draft",{method:"DELETE"});await load();await openPaper(key,true);setNotice("草稿已丢弃")}
async function savePaper(key){try{const payload=collectPaperPayload();await req("/papers/"+encodeURIComponent(key),{method:"PATCH",body:JSON.stringify({hidden:payload.hidden,arxiv_id:payload.arxiv_id,paper_url:payload.paper_url,github_url:payload.github_url})});for(const f of payload.facts){await req("/facts/"+f.id,{method:"PATCH",body:JSON.stringify({fact_type:f.fact_type,name:f.name,confidence:f.confidence,statement:f.statement})})}if(payload.new_fact_statement.trim()){await req("/papers/"+encodeURIComponent(key)+"/facts",{method:"POST",body:JSON.stringify({fact_type:payload.new_fact_type,name:payload.new_fact_name,confidence:payload.new_fact_confidence,statement:payload.new_fact_statement})})}await req("/papers/"+encodeURIComponent(key)+"/draft",{method:"DELETE"});await load();await openPaper(key,true);setNotice("论文已更新到数据库")}catch(e){setNotice(e.message,true)}}
async function deletePaper(key){if(confirm("确认删除 "+key+" ?")){await req("/papers/"+encodeURIComponent(key)+"/delete",{method:"POST",body:"{}"});selected=null;currentPaper=null;paperBaseline=null;await load();detail.innerHTML="<div class='paper-empty'>已删除。</div>"}}
async function saveFact(id){const el=document.querySelector(`.fact[data-id="${id}"]`);await req("/facts/"+id,{method:"PATCH",body:JSON.stringify({fact_type:el.querySelector(".ftype").value,name:el.querySelector(".fname").value,confidence:el.querySelector(".fconf").value,statement:el.querySelector(".fstmt").value})});if(selected)await openPaper(selected,true);setNotice("fact 已保存")}
async function deleteFact(id){if(confirm("确认删除 fact #"+id+" ?")){await req("/facts/"+id,{method:"DELETE"});if(selected)openPaper(selected,true)}}
async function createFact(key){await req("/papers/"+encodeURIComponent(key)+"/facts",{method:"POST",body:JSON.stringify({fact_type:newType.value,name:newName.value,confidence:newConf.value,statement:newStatement.value})});openPaper(key,true)}
function profileByName(name){return (state.profiles||[]).find(p=>p.name===name)}
function keywordCountText(p){const n=(p.keywords||[]).length;return n+" 个关键词"}
function renderProfiles(){if(!state.profiles.length){profiles.innerHTML="";profileEditor.innerHTML=`<div class="profile-empty">暂无搜索方向，请先新建一个。</div>`;return}if(!selectedProfile||!profileByName(selectedProfile)){selectedProfile=state.profiles[0].name;draftKeywords=[...(state.profiles[0].keywords||[])]}const current=profileByName(selectedProfile)||state.profiles[0];profiles.innerHTML=state.profiles.map(p=>`<button class="profile-pill ${p.name===current.name?"active":""}" onclick="selectProfile('${esc(p.name)}')"><strong>${esc(p.name)}</strong><small>${esc(keywordCountText(p))}${p.primary_since?(" · "+esc(p.primary_since)):""}</small></button>`).join("");renderProfileEditor(current)}
function renderProfileEditor(p){if(!draftKeywords.length&&p.keywords&&p.keywords.length)draftKeywords=[...p.keywords];profileEditor.innerHTML=`<div class="profile-head"><div class="profile-title"><h2>${esc(p.name)}</h2><p>用于搜索入库任务的研究方向。关键词会组合给 arXiv、OpenAlex、Semantic Scholar、Google Scholar 等 provider。</p></div><button class="danger" onclick="deleteProfile('${esc(p.name)}')">删除方向</button></div><label>方向说明</label><textarea id="profileDescription" placeholder="这个方向关注什么论文">${esc(p.description||"")}</textarea><div class="row"><div><label>primary_since</label><input type="date" id="profilePrimarySince" value="${esc((p.primary_since||"").slice(0,10))}"></div><div><label>exception_since</label><input type="date" id="profileExceptionSince" value="${esc((p.exception_since||"").slice(0,10))}"></div></div><div class="keyword-board"><label>关键词列表</label><div id="keywordList" class="keyword-list">${draftKeywords.map((kw,i)=>`<span class="keyword-token"><span>${esc(kw)}</span><button title="删除关键词" onclick="removeKeyword(${i})">×</button></span>`).join("")||"<span class='muted'>还没有关键词</span>"}</div><div class="keyword-add"><input id="keywordInput" placeholder="输入关键词，回车添加"><button onclick="addKeyword()">添加</button></div></div><div class="actions"><button class="primary" onclick="saveProfile('${esc(p.name)}')">保存配置</button><button onclick="resetProfileDraft()">恢复未保存内容</button></div><div class="danger-zone"><p class="muted">删除方向会同时删除该方向下的 discovery 历史记录；已经入库的论文不会被删除。</p></div>`;keywordInput.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();addKeyword()}})}
function selectProfile(name){selectedProfile=name;const p=profileByName(name);draftKeywords=[...((p&&p.keywords)||[])];renderProfiles()}
function addKeyword(){const value=(keywordInput.value||"").trim();if(!value)return;if(!draftKeywords.includes(value))draftKeywords.push(value);keywordInput.value="";const p=profileByName(selectedProfile);if(p)renderProfileEditor(p)}
function removeKeyword(index){draftKeywords.splice(index,1);const p=profileByName(selectedProfile);if(p)renderProfileEditor(p)}
function resetProfileDraft(){const p=profileByName(selectedProfile);draftKeywords=[...((p&&p.keywords)||[])];if(p)renderProfileEditor(p)}
async function saveProfile(name){await req("/profiles/"+encodeURIComponent(name),{method:"PATCH",body:JSON.stringify({description:profileDescription.value,keywords:draftKeywords,primary_since:profilePrimarySince.value,exception_since:profileExceptionSince.value})});await load();setNotice("搜索配置已保存")}
async function createProfile(){try{const name=(newProfileName.value||"").trim();await req("/profiles",{method:"POST",body:JSON.stringify({name,description:"",keywords:[],primary_since:"2025-06-08",exception_since:"2024-01-01"})});newProfileName.value="";selectedProfile=name;draftKeywords=[];await load();setNotice("搜索方向已创建")}catch(e){setNotice(e.message,true)}}
async function deleteProfile(name){try{if(!confirm("确认删除搜索方向 "+name+" ?"))return;await req("/profiles/"+encodeURIComponent(name),{method:"DELETE"});selectedProfile=null;draftKeywords=[];await load();setNotice("搜索方向已删除")}catch(e){setNotice(e.message,true)}}
document.querySelectorAll(".nav button").forEach(b=>b.addEventListener("click",()=>showView(b.dataset.view)));document.addEventListener("input",e=>{if(e.target&&e.target.id==="q")renderPapers()});window.addEventListener("beforeunload",e=>{if(hasPaperDirty()){e.preventDefault();e.returnValue="当前论文有未保存修改。离开前请更新到数据库或保存草稿。"}});setInterval(load,5000);load().catch(e=>setNotice(e.message,true));
</script>
</body>
</html>"""


class AdminHandler(BaseHTTPRequestHandler):
    config: AdminConfig

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"admin {self.address_string()} {fmt % args}")

    def _authorized(self) -> bool:
        header = self.headers.get("authorization", "")
        if not header.lower().startswith("basic "):
            return False
        try:
            raw = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        except Exception:
            return False
        username, _, password = raw.partition(":")
        return secrets.compare_digest(username, self.config.username) and secrets.compare_digest(password, self.config.password)

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("www-authenticate", 'Basic realm="AIResearch Admin"')
        self.send_header("content-length", "0")
        self.end_headers()
        return False

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _route(self) -> tuple[str, list[str]]:
        path = urllib.parse.urlparse(self.path).path
        base = self.config.base_path.rstrip("/")
        if path == base:
            path = base + "/"
        if not path.startswith(base + "/"):
            return "", []
        rest = path[len(base) + 1 :]
        return rest, [urllib.parse.unquote(part) for part in rest.split("/") if part]

    def do_GET(self) -> None:
        if not self._require_auth():
            return
        rest, parts = self._route()
        try:
            if rest == "" or rest == "index.html" or not rest.startswith("api/"):
                body = ADMIN_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("content-type", "text/html; charset=utf-8")
                self.send_header("cache-control", "no-store")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif parts == ["api", "state"]:
                self._send_json(list_state(self.config.db_path))
            elif len(parts) == 3 and parts[:2] == ["api", "papers"]:
                self._send_json(paper_detail(self.config.db_path, parts[2]))
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 500)

    def do_PATCH(self) -> None:
        if not self._require_auth():
            return
        _, parts = self._route()
        try:
            payload = self._read_json()
            if len(parts) == 3 and parts[:2] == ["api", "papers"]:
                self._send_json(update_paper(self.config.db_path, parts[2], payload))
            elif len(parts) == 3 and parts[:2] == ["api", "facts"]:
                self._send_json(update_fact(self.config.db_path, int(parts[2]), payload))
            elif len(parts) == 3 and parts[:2] == ["api", "profiles"]:
                self._send_json(update_profile(self.config.db_path, parts[2], payload))
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 400)

    def do_POST(self) -> None:
        if not self._require_auth():
            return
        _, parts = self._route()
        try:
            payload = self._read_json()
            if parts == ["api", "papers", "search-arxiv"]:
                query = _safe_text(payload.get("query"), limit=500)
                if not query:
                    raise ValueError("query is required")
                results = search_arxiv_title(query, limit=int(payload.get("limit", 10)))
                self._send_json({"results": results, "query": query})
            elif parts == ["api", "papers", "ingest"]:
                paper_input = _safe_text(payload.get("input"), limit=1000)
                if not paper_input:
                    raise ValueError("input is required")
                result = ingest_single_paper(
                    db_path=self.config.db_path,
                    paper_db_path=self.config.paper_db_path,
                    papi_executable=self.config.papi_executable,
                    paper_input=paper_input,
                    config=self.config,
                )
                self._send_json(result)
            elif len(parts) == 4 and parts[:2] == ["api", "papers"] and parts[3] == "delete":
                self._send_json(delete_paper(self.config.db_path, self.config.paper_db_path, parts[2]))
            elif len(parts) == 4 and parts[:2] == ["api", "papers"] and parts[3] == "facts":
                self._send_json(create_fact(self.config.db_path, parts[2], payload))
            elif len(parts) == 4 and parts[:2] == ["api", "papers"] and parts[3] == "draft":
                self._send_json(save_paper_draft(self.config.db_path, parts[2], payload))
            elif parts == ["api", "profiles"]:
                self._send_json(create_profile(self.config.db_path, payload), 201)
            elif len(parts) == 3 and parts[:2] == ["api", "jobs"] and parts[2] in {
                "rebuild",
                "refresh",
                "search_ingest",
                "rebuild_site",
                "deploy_site",
                "rebuild_deploy",
            }:
                self._send_json(start_job(self.config, parts[2], payload), 202)
            elif len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "cancel":
                self._send_json(cancel_job(self.config.db_path, int(parts[2])))
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 400)

    def do_DELETE(self) -> None:
        if not self._require_auth():
            return
        _, parts = self._route()
        try:
            if len(parts) == 3 and parts[:2] == ["api", "facts"]:
                self._send_json(delete_fact(self.config.db_path, int(parts[2])))
            elif len(parts) == 4 and parts[:2] == ["api", "papers"] and parts[3] == "draft":
                self._send_json(delete_paper_draft(self.config.db_path, parts[2]))
            elif len(parts) == 3 and parts[:2] == ["api", "profiles"]:
                self._send_json(delete_profile(self.config.db_path, parts[2]))
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 400)


def _normalize_base_path(base_path: str) -> str:
    normalized = "/" + base_path.strip("/") + "/"
    if normalized == "//":
        raise ValueError("base_path must not be empty")
    return normalized


def serve_admin(
    *,
    host: str,
    port: int,
    base_path: str,
    db_path: Path,
    paper_db_path: Path,
    project_dir: Path,
    deploy_script: Path,
    papi_executable: str,
) -> None:
    username = os.environ.get("AIRESEARCH_ADMIN_USER", "admin")
    password = os.environ.get("AIRESEARCH_ADMIN_PASSWORD", "")
    if not password:
        raise RuntimeError("AIRESEARCH_ADMIN_PASSWORD is required")
    config = AdminConfig(
        base_path=_normalize_base_path(base_path),
        db_path=db_path.resolve(),
        paper_db_path=paper_db_path.resolve(),
        project_dir=project_dir.resolve(),
        deploy_script=deploy_script.resolve(),
        papi_executable=papi_executable,
        username=username,
        password=password,
        layout_output_dir=Path(os.environ.get("AIRESEARCH_LAYOUT_OUTPUT_DIR", project_dir / "data" / "layout")),
        layout_max_pages=(
            int(os.environ["AIRESEARCH_LAYOUT_MAX_PAGES"])
            if os.environ.get("AIRESEARCH_LAYOUT_MAX_PAGES", "").isdigit()
            else None
        ),
        layout_ocr_mode=os.environ.get("AIRESEARCH_LAYOUT_OCR_MODE", "auto"),
        layout_ocr_languages=os.environ.get("AIRESEARCH_LAYOUT_OCR_LANGUAGES", "eng+chi_sim"),
        layout_ocr_dpi=(
            int(os.environ["AIRESEARCH_LAYOUT_OCR_DPI"])
            if os.environ.get("AIRESEARCH_LAYOUT_OCR_DPI", "").isdigit()
            else 220
        ),
        layout_ocr_executable=os.environ.get("AIRESEARCH_LAYOUT_OCR_EXECUTABLE", "tesseract"),
        layout_formula_ocr_mode=os.environ.get("AIRESEARCH_FORMULA_OCR_MODE", "off"),
        layout_formula_ocr_dpi=(
            int(os.environ["AIRESEARCH_FORMULA_OCR_DPI"])
            if os.environ.get("AIRESEARCH_FORMULA_OCR_DPI", "").isdigit()
            else 260
        ),
        layout_formula_ocr_min_confidence=float(os.environ.get("AIRESEARCH_FORMULA_OCR_MIN_CONFIDENCE", "0.7")),
    )
    ensure_admin_schema(config.db_path)
    _mark_interrupted_jobs(config.db_path)
    AdminHandler.config = config
    _ensure_worker(config)
    server = ThreadingHTTPServer((host, port), AdminHandler)
    print(f"airesearch admin listening on http://{host}:{port}{config.base_path}")
    server.serve_forever()
