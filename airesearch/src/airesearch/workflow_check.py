from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.admin_server import blog_detail as admin_blog_detail
from airesearch.admin_server import layout_detail as admin_layout_detail
from airesearch.db import connect, init_db


REQUIRED_FACT_TYPES = ("method", "dataset", "benchmark", "claim", "limitation")


@dataclass(frozen=True)
class CheckItem:
    key: str
    ok: bool
    message: str
    details: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"key": self.key, "ok": self.ok, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


def _count_rows(conn: Any, query: str, params: tuple[Any, ...]) -> int:
    row = conn.execute(query, params).fetchone()
    return int(row["count"] if row is not None else 0)


def _artifact_map(conn: Any, paper_key: str) -> dict[str, list[dict[str, Any]]]:
    rows = conn.execute(
        """
        select artifact_type, path, size_bytes
        from paper_artifacts
        where paper_key = ?
        order by artifact_type, path
        """,
        (paper_key,),
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["artifact_type"]), []).append(
            {"path": row["path"], "size_bytes": int(row["size_bytes"] or 0)}
        )
    return grouped


def _fact_counts(conn: Any, paper_key: str) -> dict[str, int]:
    rows = conn.execute(
        """
        select fact_type, count(*) as count
        from research_facts
        where paper_key = ?
        group by fact_type
        """,
        (paper_key,),
    ).fetchall()
    return {str(row["fact_type"]): int(row["count"]) for row in rows}


def _search_matches(conn: Any, paper_key: str) -> int:
    paper = conn.execute("select title from papers where paper_key = ?", (paper_key,)).fetchone()
    title = str(paper["title"] or "") if paper is not None else ""
    tokens = [paper_key]
    if title:
        tokens.extend(part for part in title.replace(":", " ").split() if len(part) >= 4)
    seen: set[str] = set()
    total = 0
    for token in tokens[:6]:
        normalized = token.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        like = f"%{normalized}%"
        total += _count_rows(
            conn,
            """
            select count(*) as count
            from papers
            where lower(paper_key) like ? or lower(coalesce(title, '')) like ?
            """,
            (like, like),
        )
    return total


def _blog_current_version(detail: dict[str, Any]) -> dict[str, Any]:
    current_id = (detail.get("post") or {}).get("current_version_id")
    for version in detail.get("versions") or []:
        if version.get("id") == current_id:
            return version
    return {}


def run_full_workflow_check(db_path: Path, paper_key: str, *, site_dir: Path | None = None) -> dict[str, Any]:
    init_db(db_path)
    items: list[CheckItem] = []
    with connect(db_path) as conn:
        paper = conn.execute("select paper_key, title from papers where paper_key = ?", (paper_key,)).fetchone()
        artifacts = _artifact_map(conn, paper_key)
        fact_counts = _fact_counts(conn, paper_key)
        search_count = _search_matches(conn, paper_key) if paper is not None else 0
        canonical_equation_count = _count_rows(
            conn,
            "select count(*) as count from paper_equations where paper_key = ?",
            (paper_key,),
        )

    items.append(
        CheckItem(
            "paper.exists",
            paper is not None,
            "paper exists in AIResearch ledger" if paper is not None else "paper is missing from AIResearch ledger",
            {"paper_key": paper_key, "title": paper["title"] if paper is not None else ""},
        )
    )
    items.append(
        CheckItem(
            "paper.search",
            search_count > 0,
            "paper is discoverable by key/title search" if search_count > 0 else "paper is not discoverable by key/title search",
            {"matches": search_count},
        )
    )
    items.append(
        CheckItem(
            "paper.ingest_artifacts",
            bool(artifacts.get("paper_pdf")),
            "paper PDF artifact is present" if artifacts.get("paper_pdf") else "paper PDF artifact is missing",
            {"artifact_types": sorted(artifacts)},
        )
    )
    missing_fact_types = [fact_type for fact_type in REQUIRED_FACT_TYPES if fact_counts.get(fact_type, 0) <= 0]
    items.append(
        CheckItem(
            "facts.required_types",
            not missing_fact_types,
            "all five required fact types are present"
            if not missing_fact_types
            else "missing required fact types: " + ", ".join(missing_fact_types),
            {"fact_counts": fact_counts, "required": list(REQUIRED_FACT_TYPES)},
        )
    )
    zh_artifacts = {key: artifacts.get(key, []) for key in ("summary_zh", "tldr_zh")}
    items.append(
        CheckItem(
            "translation.zh_artifacts",
            bool(zh_artifacts["summary_zh"] or zh_artifacts["tldr_zh"]),
            "Chinese translation artifacts are present"
            if (zh_artifacts["summary_zh"] or zh_artifacts["tldr_zh"])
            else "Chinese translation artifacts are missing",
            {"summary_zh": len(zh_artifacts["summary_zh"]), "tldr_zh": len(zh_artifacts["tldr_zh"])},
        )
    )

    layout = admin_layout_detail(db_path, paper_key)
    capabilities = layout.get("capabilities") or {}
    block_counts = layout.get("block_counts") or {}
    summary = layout.get("summary") or {}
    evidence_blocks = layout.get("evidence_blocks") if isinstance(layout.get("evidence_blocks"), list) else []
    high_quality_evidence_blocks = [
        block
        for block in evidence_blocks
        if isinstance(block.get("metadata"), dict) and float(block["metadata"].get("quality_score") or 0) >= 0.72
    ]
    structured_table_blocks = [
        block
        for block in evidence_blocks
        if block.get("block_type") == "table"
        and isinstance(block.get("metadata"), dict)
        and (block["metadata"].get("table_html") or block["metadata"].get("table_markdown"))
    ]
    high_quality_tables = [
        block
        for block in structured_table_blocks
        if isinstance(block.get("metadata"), dict) and float(block["metadata"].get("quality_score") or 0) >= 0.72
    ]
    high_quality_equations = [
        block
        for block in evidence_blocks
        if block.get("block_type") == "interline_equation"
        and isinstance(block.get("metadata"), dict)
        and float(block["metadata"].get("quality_score") or 0) >= 0.72
    ]
    representative = layout.get("representative_visual")
    visual_candidates = layout.get("visual_candidates") or []
    summary_high_quality_evidence = int(summary.get("high_quality_evidence_blocks") or 0)
    summary_high_quality_tables = int(summary.get("high_quality_table_blocks") or 0)
    summary_high_quality_equations = int(summary.get("high_quality_equation_blocks") or 0)
    evidence_check_count = max(len(high_quality_evidence_blocks), summary_high_quality_evidence)
    table_check_count = max(len(high_quality_tables), summary_high_quality_tables)
    table_required = bool(
        int(block_counts.get("table") or 0)
        or int(summary.get("structured_table_blocks") or 0)
        or int(summary.get("geometry_table_blocks") or 0)
        or int(summary.get("text_fallback_table_blocks") or 0)
        or int(summary.get("spanning_table_blocks") or 0)
    )
    equation_check_count = max(len(high_quality_equations), summary_high_quality_equations)
    formula_check_count = max(canonical_equation_count, equation_check_count)
    items.append(
        CheckItem(
            "layout.completed",
            (layout.get("latest_run") or {}).get("status") in {"completed", "skipped"},
            "layout v2 run is completed or reused"
            if (layout.get("latest_run") or {}).get("status") in {"completed", "skipped"}
            else "layout v2 has no completed run",
            {"status": (layout.get("latest_run") or {}).get("status") or "not_parsed"},
        )
    )
    items.append(
        CheckItem(
            "layout.evidence_blocks",
            bool(evidence_check_count),
            "high-quality layout evidence blocks are available" if evidence_check_count else "high-quality layout evidence blocks are missing",
            {
                "evidence_ready_blocks": int(summary.get("evidence_ready_blocks") or 0),
                "high_quality_evidence_blocks": evidence_check_count,
                "sample_high_quality_evidence_blocks": len(high_quality_evidence_blocks),
                "summary_high_quality_evidence_blocks": summary_high_quality_evidence,
            },
        )
    )
    items.append(
        CheckItem(
            "layout.visuals",
            bool(representative or visual_candidates or block_counts.get("image") or block_counts.get("chart")),
            "layout visual candidate is available" if (representative or visual_candidates or block_counts.get("image") or block_counts.get("chart")) else "layout visual candidate is missing",
            {"representative_visual": representative, "candidate_count": len(visual_candidates)},
        )
    )
    items.append(
        CheckItem(
            "layout.tables",
            not table_required or bool(capabilities.get("has_high_quality_tables") or table_check_count),
            (
                "high-quality structured table evidence is available"
                if table_required and (capabilities.get("has_high_quality_tables") or table_check_count)
                else "paper has no detected table; structured table evidence is not applicable"
                if not table_required
                else "high-quality structured table evidence is missing"
            ),
            {
                "required": table_required,
                "table_blocks": int(block_counts.get("table") or 0),
                "structured_table_blocks": int(summary.get("structured_table_blocks") or 0),
                "sample_html_or_markdown_tables": len(structured_table_blocks),
                "high_quality_tables": table_check_count,
                "capability": bool(capabilities.get("has_high_quality_tables")),
            },
        )
    )
    items.append(
        CheckItem(
            "layout.equations",
            bool(formula_check_count),
            "canonical or high-quality layout formula evidence is available"
            if formula_check_count
            else "canonical and high-quality layout formula evidence are missing",
            {
                "canonical_equations": canonical_equation_count,
                "equation_blocks": int(summary.get("equation_blocks") or 0),
                "interline_equation_blocks": int(block_counts.get("interline_equation") or 0),
                "high_quality_equations": equation_check_count,
                "capability": bool(capabilities.get("has_high_quality_equations")),
            },
        )
    )

    blog = admin_blog_detail(db_path, paper_key)
    current = _blog_current_version(blog)
    blog_meta = blog.get("generation_meta") or {}
    sections = blog_meta.get("sections") if isinstance(blog_meta.get("sections"), list) else []
    items.append(
        CheckItem(
            "blog.deep_reading",
            bool(current),
            "deep-reading blog version is available" if current else "deep-reading blog version is missing",
            {
                "version_id": current.get("id"),
                "word_count": current.get("word_count") or (blog.get("post") or {}).get("word_count") or 0,
                "section_count": len(sections),
            },
        )
    )

    if site_dir is not None:
        api_path = site_dir / "api" / "papers" / f"{paper_key}.json"
        html_path = site_dir / "papers" / f"{paper_key}.html"
        public_payload: dict[str, Any] = {}
        api_error = ""
        if api_path.is_file():
            try:
                loaded = json.loads(api_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    public_payload = loaded
            except (OSError, ValueError) as exc:
                api_error = str(exc)
        public_layout = public_payload.get("layout_evidence") if isinstance(public_payload.get("layout_evidence"), dict) else {}
        public_graph = public_payload.get("evidence_graph") if isinstance(public_payload.get("evidence_graph"), dict) else {}
        public_graph_ok = public_graph.get("schema_version") == "evidence-graph-v1"
        items.append(
            CheckItem(
                "public.api",
                bool(public_payload and public_layout and public_graph_ok),
                "public paper JSON includes layout and graph evidence"
                if (public_payload and public_layout and public_graph_ok)
                else "public paper JSON, layout evidence, or graph evidence is missing",
                {
                    "path": str(api_path),
                    "error": api_error,
                    "graph_schema_version": public_graph.get("schema_version") or "",
                },
            )
        )

        html_text = ""
        html_error = ""
        if html_path.is_file():
            try:
                html_text = html_path.read_text(encoding="utf-8")
            except OSError as exc:
                html_error = str(exc)
        required_markers = ["paper-layout-suite", "OCR / Layout", "证据关系"]
        if formula_check_count:
            required_markers.append("paper-layout-formula")
        if table_check_count:
            required_markers.append("paper-layout-table-card")
        if current:
            required_markers.append("paper-blog-prose")
        missing_markers = [marker for marker in required_markers if marker not in html_text]
        items.append(
            CheckItem(
                "public.page",
                bool(html_text) and not missing_markers,
                "public paper page renders workflow evidence"
                if (html_text and not missing_markers)
                else "public paper page is missing workflow evidence",
                {"path": str(html_path), "missing_markers": missing_markers, "error": html_error},
            )
        )

    payload_items = [item.as_dict() for item in items]
    return {
        "ok": all(item["ok"] for item in payload_items),
        "paper_key": paper_key,
        "checks": payload_items,
        "summary": {
            "passed": sum(1 for item in payload_items if item["ok"]),
            "failed": sum(1 for item in payload_items if not item["ok"]),
            "total": len(payload_items),
        },
    }


def dumps_check(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
