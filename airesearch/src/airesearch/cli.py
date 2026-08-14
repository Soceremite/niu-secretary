from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TextIO

from airesearch.admin_server import serve_admin
from airesearch.artifact_ledger import export_artifact_ledger, extract_artifact_ledger
from airesearch.archive_remote import RcloneRemote
from airesearch.archive_service import ArchiveService, ArchiveWorkflowError
from airesearch.batch import run_batch_ingest
from airesearch.url_normalizer import categorize_url, normalize_url_raw, normalize_manifest
from airesearch.candidates import export_candidates, list_candidates
from airesearch.canonical_candidates import (
    export_candidate_review,
    export_approved_candidates,
    export_canonical_candidates,
    list_canonical_candidates,
    materialize_candidate_papers,
    select_top_canonical_candidates,
    set_canonical_status,
)
from airesearch.claim_trace import ClaimTraceNotFound, export_claim_trace
from airesearch.code_links import export_code_links, extract_code_links, list_code_links
from airesearch.config import Settings
from airesearch.db import connect, init_db
from airesearch.embeddings import EmbeddingProviderError, OpenAICompatibleEmbeddingProvider
from airesearch.evidence_repair import export_evidence_source_path_repairs
from airesearch.fact_audit import audit_research_facts
from airesearch.fact_extraction import (
    FactValidationError,
    export_research_facts,
    extract_research_facts,
    list_research_facts,
)
from airesearch.knowledge_graph import export_paper_cards, extract_paper_cards, list_paper_cards
from airesearch.launch_ops import backup_sqlite_db, run_health_check, write_scheduled_refresh_wrapper
from airesearch.launch_refresh import MVP_PROGRESS_STEPS, run_launch_refresh
from airesearch.layout_evidence_graph import export_layout_evidence_graph, extract_layout_evidence_graph
from airesearch.layout_parse import layout_detail, parse_missing_layouts, parse_paper_layout
from airesearch.layout_parser import LayoutParserOptions
from airesearch.mvp_pipeline import run_mvp_pipeline
from airesearch.research_digest import DigestInputError, export_research_digest
from airesearch.research_gap_analysis import export_gap_analysis
from airesearch.research_map import export_research_map
from airesearch.research_narrative import export_narrative_report
from airesearch.research_bundle import export_report_bundle
from airesearch.research_cluster_calibration import DEFAULT_THRESHOLDS, export_cluster_calibration_report
from airesearch.research_cluster_review import export_cluster_review_packet
from airesearch.research_clusters import SemanticClusteringError, export_research_clusters
from airesearch.research_review_editor import ClusterReviewEditError, set_cluster_review_status
from airesearch.research_review_summary import ClusterReviewSummaryError, export_reviewed_cluster_summary
from airesearch.research_relations import export_research_relations
from airesearch.research_site import export_report_site
from airesearch.research_synthesis import export_research_synthesis
from airesearch.discovery import run_discovery
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.profiles import default_profiles, seed_profiles
from airesearch.providers import ArxivProvider, GoogleScholarProvider, OpenAlexProvider, SemanticScholarProvider
from airesearch.static_publish import publish_static_site, serve_report_site, write_static_deploy_scripts, write_static_host_config
from airesearch.workflow_check import dumps_check, run_full_workflow_check


def build_parser() -> argparse.ArgumentParser:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(prog="airesearch")
    parser.add_argument("--db", type=Path, default=settings.sqlite_path)
    parser.add_argument("--paper-db", type=Path, default=settings.paper_db_path)
    parser.add_argument("--papi", default=settings.papi_executable)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db")
    subparsers.add_parser("sync-paperpipe")
    batch = subparsers.add_parser("batch-ingest")
    batch.add_argument("manifest", type=Path)
    batch.add_argument(
        "--normalize-urls",
        action="store_true",
        default=True,
        help="Normalize problematic URLs before passing to papi (default).",
    )
    batch.add_argument(
        "--no-normalize-urls",
        action="store_false",
        dest="normalize_urls",
        help="Disable URL normalization.",
    )
    normalize_cmd = subparsers.add_parser("normalize-url")
    normalize_cmd.add_argument("url", help="URL or raw input to normalize.")
    subparsers.add_parser("status")
    subparsers.add_parser("seed-profiles")
    discover = subparsers.add_parser("discover-candidates")
    discover.add_argument("--profile", required=True)
    discover.add_argument("--limit", type=int, default=50)
    discover.add_argument(
        "--provider",
        action="append",
        choices=["openalex", "arxiv", "semantic_scholar", "google_scholar"],
        help="Discovery provider to use. Repeat for multiple providers. Defaults to all.",
    )
    discover.add_argument(
        "--refresh-provider-cache",
        action="store_true",
        help="Bypass provider response cache for cache-aware providers while still respecting quota limits.",
    )
    listing = subparsers.add_parser("list-candidates")
    listing.add_argument("--profile", required=True)
    listing.add_argument("--limit", type=int, default=20)
    export = subparsers.add_parser("export-candidates")
    export.add_argument("--profile", required=True)
    export.add_argument("--limit", type=int, default=100)
    export.add_argument("--out", type=Path, required=True)
    subparsers.add_parser("dedupe-candidates")
    canonical_listing = subparsers.add_parser("list-canonical-candidates")
    canonical_listing.add_argument("--limit", type=int, default=20)
    canonical_export = subparsers.add_parser("export-canonical-candidates")
    canonical_export.add_argument("--limit", type=int, default=100)
    canonical_export.add_argument("--out", type=Path, required=True)
    candidate_review = subparsers.add_parser("export-candidate-review")
    candidate_review.add_argument("--out", type=Path, required=True)
    candidate_review.add_argument("--markdown-out", type=Path)
    candidate_review.add_argument("--limit", type=int)
    candidate_review.add_argument("--min-score", type=float)
    set_status = subparsers.add_parser("set-canonical-status")
    set_status.add_argument("canonical_key")
    set_status.add_argument("--status", choices=["candidate", "selected", "rejected"], required=True)
    select_canonical = subparsers.add_parser("select-canonical-candidates")
    select_canonical.add_argument("--limit", type=int, required=True)
    select_canonical.add_argument("--min-score", type=float)
    approved_export = subparsers.add_parser("export-approved-candidates")
    approved_export.add_argument("--out", type=Path, required=True)
    extract_cards = subparsers.add_parser("extract-paper-cards")
    extract_cards.add_argument("--limit", type=int)
    extract_cards.add_argument("--paper-key")
    card_listing = subparsers.add_parser("list-paper-cards")
    card_listing.add_argument("--limit", type=int, default=20)
    card_export = subparsers.add_parser("export-paper-cards")
    card_export.add_argument("--out", type=Path, required=True)
    graph_extract = subparsers.add_parser("extract-layout-evidence-graph")
    graph_extract.add_argument("--paper-key")
    graph_extract.add_argument("--limit", type=int)
    graph_export = subparsers.add_parser("export-layout-evidence-graph")
    graph_export.add_argument("--out", type=Path, required=True)
    fact_extract = subparsers.add_parser("extract-research-facts")
    fact_extract.add_argument("--provider", choices=["fixture", "openai-compatible"], required=True)
    fact_extract.add_argument("--fixture", type=Path)
    fact_extract.add_argument("--paper-key")
    fact_extract.add_argument("--paper-list", type=Path, help="newline-delimited paper keys")
    fact_extract.add_argument(
        "--required-fact-types-file",
        type=Path,
        help="lines formatted as paper_key=type[,type] for targeted retries",
    )
    fact_extract.add_argument("--limit", type=int)
    fact_extract.add_argument("--model")
    fact_extract.add_argument("--base-url")
    fact_extract.add_argument("--api-key-env", default="AIRESEARCH_FACT_API_KEY")
    fact_extract.add_argument("--dry-run", action="store_true")
    fact_extract.add_argument("--refresh-cache", action="store_true")
    fact_extract.add_argument("--max-input-chars", type=int, default=24000)
    fact_extract.add_argument("--concurrency", type=int, default=5)
    fact_extract.add_argument("--fact-error-policy", choices=["strict", "warn"], default="strict")
    fact_listing = subparsers.add_parser("list-research-facts")
    fact_listing.add_argument("--paper-key")
    fact_listing.add_argument("--type", choices=["method", "dataset", "benchmark", "claim", "limitation"])
    fact_listing.add_argument("--limit", type=int, default=20)
    fact_export = subparsers.add_parser("export-research-facts")
    fact_export.add_argument("--out", type=Path, required=True)
    trace = subparsers.add_parser("claim-trace")
    trace.add_argument("--fact-id", type=int)
    trace.add_argument("--paper-key")
    trace.add_argument("--type", choices=["method", "dataset", "benchmark", "claim", "limitation"])
    trace.add_argument("--query")
    trace.add_argument("--format", choices=["markdown", "json"], default="markdown")
    trace.add_argument("--out", type=Path)
    ledger_extract = subparsers.add_parser("extract-artifact-ledger")
    ledger_extract.add_argument("--paper-key")
    ledger_extract.add_argument("--limit", type=int)
    ledger_export = subparsers.add_parser("export-artifact-ledger")
    ledger_export.add_argument("--out", type=Path, required=True)
    ledger_export.add_argument("--format", choices=["markdown", "json", "jsonl"], default="markdown")
    subparsers.add_parser("audit-research-facts")
    layout_parse_cmd = subparsers.add_parser("parse-layout")
    layout_parse_cmd.add_argument("--paper-key", required=True)
    layout_parse_cmd.add_argument("--force", action="store_true")
    layout_parse_cmd.add_argument("--layout-output-dir", type=Path, default=settings.layout_output_dir)
    layout_parse_cmd.add_argument("--max-pages", type=int, default=settings.layout_max_pages)
    layout_parse_cmd.add_argument("--ocr-mode", choices=["off", "auto", "force"], default=settings.layout_ocr_mode)
    layout_parse_cmd.add_argument("--ocr-languages", default=settings.layout_ocr_languages)
    layout_parse_cmd.add_argument("--ocr-dpi", type=int, default=settings.layout_ocr_dpi)
    layout_parse_cmd.add_argument("--ocr-executable", default=settings.layout_ocr_executable)
    layout_parse_cmd.add_argument("--formula-ocr-mode", choices=["off", "auto", "force"], default=settings.layout_formula_ocr_mode)
    layout_parse_cmd.add_argument("--formula-ocr-dpi", type=int, default=settings.layout_formula_ocr_dpi)
    layout_parse_cmd.add_argument("--formula-ocr-min-confidence", type=float, default=settings.layout_formula_ocr_min_confidence)
    layout_status = subparsers.add_parser("layout-status")
    layout_status.add_argument("--paper-key", required=True)
    layout_missing = subparsers.add_parser("parse-missing-layouts")
    layout_missing.add_argument("--limit", type=int, default=10)
    layout_missing.add_argument("--layout-output-dir", type=Path, default=settings.layout_output_dir)
    layout_missing.add_argument("--max-pages", type=int, default=settings.layout_max_pages)
    layout_missing.add_argument("--ocr-mode", choices=["off", "auto", "force"], default=settings.layout_ocr_mode)
    layout_missing.add_argument("--ocr-languages", default=settings.layout_ocr_languages)
    layout_missing.add_argument("--ocr-dpi", type=int, default=settings.layout_ocr_dpi)
    layout_missing.add_argument("--ocr-executable", default=settings.layout_ocr_executable)
    layout_missing.add_argument("--formula-ocr-mode", choices=["off", "auto", "force"], default=settings.layout_formula_ocr_mode)
    layout_missing.add_argument("--formula-ocr-dpi", type=int, default=settings.layout_formula_ocr_dpi)
    layout_missing.add_argument("--formula-ocr-min-confidence", type=float, default=settings.layout_formula_ocr_min_confidence)
    workflow_check = subparsers.add_parser("workflow-check")
    workflow_check.add_argument("--paper-key", required=True)
    workflow_check.add_argument("--site-dir", type=Path)
    evidence_repair = subparsers.add_parser("repair-evidence-source-paths")
    evidence_repair.add_argument("--out", type=Path, required=True)
    evidence_repair.add_argument("--paper-key")
    evidence_repair.add_argument("--apply", action="store_true")
    digest = subparsers.add_parser("generate-research-digest")
    digest.add_argument("--out", type=Path, required=True)
    digest.add_argument("--format", choices=["markdown", "json"], default="markdown")
    research_map = subparsers.add_parser("generate-research-map")
    research_map.add_argument("--out", type=Path, required=True)
    research_map.add_argument("--format", choices=["markdown", "json"], default="markdown")
    relations = subparsers.add_parser("generate-research-relations")
    relations.add_argument("--out", type=Path, required=True)
    relations.add_argument("--format", choices=["markdown", "json"], default="markdown")
    gap_analysis = subparsers.add_parser("generate-gap-analysis")
    gap_analysis.add_argument("--out", type=Path, required=True)
    gap_analysis.add_argument("--format", choices=["markdown", "json"], default="markdown")
    synthesis = subparsers.add_parser("generate-research-synthesis")
    synthesis.add_argument("--out", type=Path, required=True)
    synthesis.add_argument("--format", choices=["markdown", "json"], default="markdown")
    narrative = subparsers.add_parser("generate-narrative-report")
    narrative.add_argument("--out", type=Path, required=True)
    narrative.add_argument("--format", choices=["markdown", "json"], default="markdown")
    clusters = subparsers.add_parser("generate-research-clusters")
    clusters.add_argument("--out", type=Path, required=True)
    clusters.add_argument("--format", choices=["markdown", "json"], default="markdown")
    clusters.add_argument("--mode", choices=["token", "semantic"], default="token")
    clusters.add_argument("--semantic-threshold", type=float, default=0.82)
    cluster_review = subparsers.add_parser("generate-cluster-review")
    cluster_review.add_argument("--out", type=Path, required=True)
    cluster_review.add_argument("--format", choices=["markdown", "json"], default="markdown")
    cluster_review.add_argument("--mode", choices=["token", "semantic"], default="token")
    cluster_review.add_argument("--semantic-threshold", type=float, default=0.82)
    review_summary = subparsers.add_parser("summarize-cluster-review")
    review_summary.add_argument("--review-packet", type=Path, required=True)
    review_summary.add_argument("--out", type=Path, required=True)
    review_summary.add_argument("--format", choices=["markdown", "json"], default="markdown")
    review_edit = subparsers.add_parser("set-cluster-review-status")
    review_edit.add_argument("--review-packet", type=Path, required=True)
    review_edit.add_argument("--cluster-id", required=True)
    review_edit.add_argument(
        "--status",
        choices=["pending", "accepted", "rejected", "needs_revision"],
        required=True,
    )
    review_edit.add_argument("--notes")
    review_edit.add_argument("--out", type=Path, required=True)
    calibration = subparsers.add_parser("calibrate-research-clusters")
    calibration.add_argument("--out", type=Path, required=True)
    calibration.add_argument("--format", choices=["markdown", "json"], default="markdown")
    calibration.add_argument(
        "--threshold",
        action="append",
        type=float,
        help="Semantic cosine threshold to evaluate. Repeat for multiple thresholds. Defaults to 0.70,0.75,0.80,0.82,0.85,0.90.",
    )
    bundle = subparsers.add_parser("generate-report-bundle")
    bundle.add_argument("--out-dir", type=Path, required=True)
    bundle.add_argument("--review-packet", type=Path)
    site = subparsers.add_parser("generate-report-site")
    site.add_argument("--bundle-dir", type=Path, required=True)
    site.add_argument("--out", type=Path)
    mvp = subparsers.add_parser("run-mvp-pipeline")
    mvp.add_argument("--out-dir", type=Path, default=Path("exports/mvp-current"))
    mvp.add_argument("--fact-provider", choices=["fixture", "openai-compatible"], default="openai-compatible")
    mvp.add_argument("--fixture", type=Path)
    mvp.add_argument("--model")
    mvp.add_argument("--base-url")
    mvp.add_argument("--api-key-env", default="AIRESEARCH_FACT_API_KEY")
    mvp.add_argument("--concurrency", type=int, default=5)
    mvp.add_argument("--refresh-facts", action="store_true")
    mvp.add_argument("--fact-error-policy", choices=["strict", "warn"], default="strict")
    mvp.add_argument("--semantic", action="store_true")
    mvp.add_argument("--semantic-threshold", type=float, default=0.82)
    refresh = subparsers.add_parser("run-launch-refresh")
    refresh.add_argument(
        "--profile",
        action="append",
        help="Research profile to refresh. Repeat for multiple profiles. Defaults to all seeded profiles.",
    )
    refresh.add_argument("--limit-per-profile", type=int, default=50)
    refresh.add_argument("--select-limit", type=int, default=10)
    refresh.add_argument("--min-score", type=float, default=0.6)
    refresh.add_argument("--approved-manifest", type=Path, default=Path("manifests/approved-launch-refresh-current.txt"))
    refresh.add_argument("--out-dir", type=Path, default=Path("exports/mvp-current"))
    refresh.add_argument("--site-dir", type=Path, default=Path("exports/site-current"))
    refresh.add_argument("--run-manifest", type=Path, default=Path("exports/launch-refresh-current.json"))
    refresh.add_argument("--candidate-review", type=Path)
    refresh.add_argument("--candidate-review-md", type=Path)
    refresh.add_argument("--history-dir", type=Path, default=Path("exports/run-history"))
    refresh.add_argument("--log-dir", type=Path, default=Path("logs"))
    refresh.add_argument("--fact-provider", choices=["fixture", "openai-compatible"], default="openai-compatible")
    refresh.add_argument("--fixture", type=Path)
    refresh.add_argument("--model")
    refresh.add_argument("--base-url")
    refresh.add_argument("--api-key-env", default="AIRESEARCH_FACT_API_KEY")
    refresh.add_argument("--concurrency", type=int, default=5)
    refresh.add_argument("--refresh-facts", action="store_true")
    refresh.add_argument("--fact-error-policy", choices=["strict", "warn"], default="strict")
    refresh.add_argument("--semantic", action="store_true")
    refresh.add_argument("--semantic-threshold", type=float, default=0.82)
    refresh.add_argument(
        "--progress",
        action="store_true",
        help="Show a unified progress bar on stderr while the launch refresh runs.",
    )
    refresh.add_argument(
        "--provider",
        action="append",
        choices=["openalex", "arxiv", "semantic_scholar", "google_scholar"],
        help="Discovery provider to use. Repeat for multiple providers. Defaults to openalex, arxiv, semantic_scholar.",
    )
    refresh.add_argument(
        "--refresh-provider-cache",
        action="store_true",
        help="Bypass provider response cache for cache-aware providers while still respecting quota limits.",
    )
    publish = subparsers.add_parser("publish-static-site")
    publish.add_argument("--source-dir", type=Path, default=Path("exports/mvp-current/bundle"))
    publish.add_argument("--out-dir", type=Path, default=Path("exports/site-current"))
    publish.add_argument("--no-clean", action="store_true")
    serve = subparsers.add_parser("serve-report-site")
    serve.add_argument("--dir", type=Path, default=Path("exports/site-current"))
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    host_config = subparsers.add_parser("write-static-host-config")
    host_config.add_argument("--site-dir", type=Path, default=Path("exports/site-current"))
    host_config.add_argument("--out-dir", type=Path, default=Path("deploy"))
    host_config.add_argument("--base-path", default="/niu-secretary/airesearch/")
    host_config.add_argument("--deploy-root", type=Path, default=Path("/var/www/html/niu-secretary/airesearch"))
    deploy_scripts = subparsers.add_parser("write-static-deploy-scripts")
    deploy_scripts.add_argument("--site-dir", type=Path, default=Path("exports/site-current"))
    deploy_scripts.add_argument("--out-dir", type=Path, default=Path("deploy"))
    deploy_scripts.add_argument("--deploy-root", type=Path, default=Path("/var/www/html/niu-secretary/airesearch"))
    deploy_scripts.add_argument("--snapshot-root", type=Path)
    health = subparsers.add_parser("health-check")
    health.add_argument("--site-dir", type=Path, default=Path("exports/site-current"))
    health.add_argument("--require-fact-provider", action="store_true")
    health.add_argument("--require-embedding", action="store_true")
    health.add_argument(
        "--env",
        action="append",
        dest="required_env",
        help="Additional required environment variable name to check without printing its value.",
    )
    backup = subparsers.add_parser("backup-db")
    backup.add_argument("--out-dir", type=Path, default=Path("backups"))
    backup.add_argument("--label")
    wrapper = subparsers.add_parser("write-refresh-wrapper")
    wrapper.add_argument("--out", type=Path, default=Path("scripts/airesearch-refresh.sh"))
    wrapper.add_argument("--project-dir", type=Path, default=Path("."))
    wrapper.add_argument("--schedule", choices=["manual", "daily", "weekly"], default="manual")
    wrapper.add_argument("--log-dir", type=Path, default=Path("logs"))
    wrapper.add_argument("--history-dir", type=Path, default=Path("exports/run-history"))
    wrapper.add_argument(
        "--refresh-command",
        help="Custom run-launch-refresh command to embed before the wrapper appends --run-manifest.",
    )
    code_extract = subparsers.add_parser("extract-code-links")
    code_extract.add_argument("--paper-key")
    code_extract.add_argument("--limit", type=int)
    code_listing = subparsers.add_parser("list-code-links")
    code_listing.add_argument("--paper-key")
    code_listing.add_argument("--limit", type=int, default=20)
    code_export = subparsers.add_parser("export-code-links")
    code_export.add_argument("--out", type=Path, required=True)
    admin = subparsers.add_parser("serve-admin")
    admin.add_argument("--host", default="127.0.0.1")
    admin.add_argument("--port", type=int, default=8791)
    admin.add_argument("--base-path", default="/niu-secretary/airesearch/admin/")
    admin.add_argument("--project-dir", type=Path, default=Path("."))
    admin.add_argument("--deploy-script", type=Path, default=Path("deploy/deploy-airesearch.sh"))
    archive = subparsers.add_parser("archive")
    archive_commands = archive.add_subparsers(dest="archive_command", required=True)
    archive_plan = archive_commands.add_parser("plan")
    archive_plan.add_argument("--paper-key", action="append")
    archive_plan.add_argument("--record", action="store_true")
    archive_status = archive_commands.add_parser("status")
    archive_status.add_argument("--paper-key", action="append")
    for name in ("upload", "verify", "evict", "restore"):
        command = archive_commands.add_parser(name)
        command.add_argument("--paper-key", action="append", required=True)
        command.add_argument("--concurrency", type=int)
    archive_commands.choices["evict"].add_argument("--apply", action="store_true")
    return parser


def count_table(db_path: Path, table: str) -> int:
    if not db_path.exists():
        return 0
    try:
        with connect(db_path) as conn:
            row = conn.execute(f"select count(*) as count from {table}").fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row["count"])


def latest_value(db_path: Path, sql: str) -> str:
    if not db_path.exists():
        return "none"
    with connect(db_path) as conn:
        row = conn.execute(sql).fetchone()
    if row is None:
        return "none"
    return str(row[0])


def print_status(db_path: Path) -> None:
    print(f"db: {db_path}")
    print(f"papers: {count_table(db_path, 'papers')}")
    print(f"artifacts: {count_table(db_path, 'paper_artifacts')}")
    print(f"profiles: {count_table(db_path, 'research_profiles')}")
    print(f"candidates: {count_table(db_path, 'research_candidates')}")
    print(f"canonical_candidates: {count_table(db_path, 'candidate_papers')}")
    print(f"paper_cards: {count_table(db_path, 'paper_cards')}")
    print(f"kg_nodes: {count_table(db_path, 'kg_nodes')}")
    print(f"kg_edges: {count_table(db_path, 'kg_edges')}")
    print(f"research_facts: {count_table(db_path, 'research_facts')}")
    print(f"code_links: {count_table(db_path, 'paper_code_links')}")
    print(
        "latest_sync: "
        + latest_value(
            db_path,
            "select finished_at from sync_events order by id desc limit 1",
        )
    )
    print(
        "latest_ingest_run: "
        + latest_value(
            db_path,
            "select status || ' ' || coalesce(finished_at, started_at) from ingest_runs order by id desc limit 1",
        )
    )


def build_discovery_providers(
    names: list[str] | None,
    *,
    db_path: Path | None = None,
    refresh_provider_cache: bool = False,
):
    provider_names = names or ["openalex", "arxiv", "semantic_scholar"]
    providers = []
    for name in provider_names:
        if name == "openalex":
            providers.append(OpenAlexProvider())
        elif name == "arxiv":
            providers.append(ArxivProvider())
        elif name == "semantic_scholar":
            providers.append(SemanticScholarProvider())
        elif name == "google_scholar":
            providers.append(
                GoogleScholarProvider(
                    db_path=db_path,
                    refresh_cache=refresh_provider_cache,
                )
            )
        else:
            raise ValueError(f"unknown discovery provider: {name}")
    return providers


class LaunchRefreshProgress:
    def __init__(self, *, total: int, stream: TextIO | None = None) -> None:
        self.total = max(1, total)
        self.stream = stream or sys.stderr
        self.current = 0
        self.last_length = 0

    def __call__(self, step: str) -> None:
        self.current = min(self.current + 1, self.total)
        filled = round(24 * self.current / self.total)
        bar = "#" * filled + "-" * (24 - filled)
        percent = round(100 * self.current / self.total)
        line = f"airesearch progress [{bar}] {self.current}/{self.total} {percent:3d}% {step}"
        padding = " " * max(0, self.last_length - len(line))
        ending = "\n" if self.current >= self.total else ""
        self.stream.write("\r" + line + padding + ending)
        self.stream.flush()
        self.last_length = len(line)


def launch_refresh_progress_total(*, profile_count: int, provider_count: int) -> int:
    discovery_steps = profile_count * provider_count
    outer_steps = 2 + 6 + 1
    return outer_steps + discovery_steps + MVP_PROGRESS_STEPS


def build_archive_service(args, settings: Settings) -> ArchiveService:
    if not settings.archive_remote:
        raise ArchiveWorkflowError("configuration", "archive_remote_not_configured")
    remote = RcloneRemote(
        executable=settings.rclone_executable,
        remote_root=settings.archive_remote,
    )
    return ArchiveService(
        db_path=args.db,
        paper_db_path=args.paper_db,
        staging_path=settings.archive_staging_path,
        remote=remote,
        lock_root=settings.archive_staging_path / "locks",
    )


def build_layout_options(args) -> LayoutParserOptions:
    return LayoutParserOptions(
        output_dir=args.layout_output_dir,
        max_pages=args.max_pages,
        ocr_mode=args.ocr_mode,
        ocr_languages=args.ocr_languages,
        ocr_dpi=args.ocr_dpi,
        ocr_executable=args.ocr_executable,
        formula_ocr_mode=args.formula_ocr_mode,
        formula_ocr_dpi=args.formula_ocr_dpi,
        formula_ocr_min_confidence=args.formula_ocr_min_confidence,
    )


def run_archive_command(args, settings: Settings) -> int:
    try:
        service = build_archive_service(args, settings)
        if args.archive_command == "plan":
            result = service.plan(args.paper_key, record=args.record)
            print(
                f"eligible={result.eligible_count} excluded={result.excluded_count} "
                f"reclaimable_bytes={result.reclaimable_bytes}"
            )
            for item in result.items:
                print(
                    f"paper_key={item.paper_key} status={item.status} "
                    f"source_bytes={item.source_bytes} reason={item.reason or 'none'}"
                )
            for name in result.unreferenced_directories:
                print(f"unreferenced={name}")
            return 0
        if args.archive_command == "status":
            records = service.store.list_records(args.paper_key)
            for record in records:
                print(
                    f"paper_key={record.paper_key} status={record.status.value} "
                    f"remote_bytes={record.archive_size_bytes} pinned={int(record.pinned)}"
                )
            print(f"records={len(records)} cache_gb={settings.archive_cache_gb}")
            return 0

        concurrency = args.concurrency
        if concurrency is None:
            concurrency = (
                settings.archive_workers
                if args.archive_command in {"upload", "verify"}
                else 1
            )
        if concurrency < 1:
            raise ArchiveWorkflowError("configuration", "invalid_archive_concurrency")

        def execute(paper_key: str):
            if args.archive_command == "upload":
                return service.upload(paper_key)
            if args.archive_command == "verify":
                return service.verify(paper_key)
            if args.archive_command == "evict":
                return service.evict(paper_key, apply=args.apply)
            return service.restore(paper_key)

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(execute, key) for key in args.paper_key]
            results = []
            failed = False
            for key, future in zip(args.paper_key, futures, strict=True):
                try:
                    operation = future.result()
                    results.append(operation)
                    print(
                        f"paper_key={key} operation={operation.operation} "
                        f"prior={operation.prior_status.value if operation.prior_status else 'none'} "
                        f"status={operation.status.value} changed={int(operation.changed)} "
                        f"source_bytes={operation.source_bytes} remote_bytes={operation.remote_bytes} "
                        f"duration_ms={operation.duration_ms}"
                    )
                except ArchiveWorkflowError as exc:
                    failed = True
                    print(f"paper_key={key} error={exc.category}")
            return 2 if failed else 0
    except ArchiveWorkflowError as exc:
        print(f"error={exc.category}")
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "archive":
        return run_archive_command(args, Settings.from_env())

    if args.command == "init-db":
        init_db(args.db)
        print(f"initialized: {args.db}")
        return 0

    if args.command == "sync-paperpipe":
        result = sync_paperpipe(db_path=args.db, paper_db_path=args.paper_db)
        print(f"papers_seen={result.papers_seen} artifacts_seen={result.artifacts_seen}")
        return 0

    if args.command == "parse-layout":
        result = parse_paper_layout(
            db_path=args.db,
            paper_key=args.paper_key,
            options=build_layout_options(args),
            force=args.force,
        )
        graph = extract_layout_evidence_graph(args.db, paper_key=result.paper_key)
        print(
            "paper_key={paper_key} run_id={run_id} status={status} "
            "artifacts={artifacts} blocks={blocks} output_dir={output_dir} "
            "graph_facts={graph_facts} graph_evidence={graph_evidence} graph_supported={graph_supported}".format(
                paper_key=result.paper_key,
                run_id=result.run_id,
                status=result.status,
                artifacts=result.artifact_count,
                blocks=result.block_count,
                output_dir=result.output_dir,
                graph_facts=graph.fact_nodes_written,
                graph_evidence=graph.evidence_nodes_written,
                graph_supported=graph.supported_by_edges,
            )
        )
        return 0

    if args.command == "layout-status":
        print(json.dumps(layout_detail(args.db, args.paper_key), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.command == "parse-missing-layouts":
        results = parse_missing_layouts(db_path=args.db, options=build_layout_options(args), limit=args.limit)
        graph_facts = graph_evidence = graph_supported = 0
        for result in results:
            graph = extract_layout_evidence_graph(args.db, paper_key=result.paper_key)
            graph_facts += graph.fact_nodes_written
            graph_evidence += graph.evidence_nodes_written
            graph_supported += graph.supported_by_edges
            print(
                "paper_key={paper_key} run_id={run_id} status={status} "
                "artifacts={artifacts} blocks={blocks}".format(
                    paper_key=result.paper_key,
                    run_id=result.run_id,
                    status=result.status,
                    artifacts=result.artifact_count,
                    blocks=result.block_count,
                )
            )
        print(
            f"layout_runs={len(results)} graph_facts={graph_facts} "
            f"graph_evidence={graph_evidence} graph_supported={graph_supported}"
        )
        return 0

    if args.command == "workflow-check":
        payload = run_full_workflow_check(args.db, args.paper_key, site_dir=args.site_dir)
        print(dumps_check(payload))
        return 0 if payload["ok"] else 2

    if args.command == "batch-ingest":
        result = run_batch_ingest(
            db_path=args.db,
            paper_db_path=args.paper_db,
            manifest_path=args.manifest,
            papi_executable=args.papi,
            normalize_urls=args.normalize_urls,
        )
        print(
            "total={total} success={success} failed={failed} "
            "duplicate={duplicate} skipped={skipped}".format(
                total=result.total,
                success=result.success,
                failed=result.failed,
                duplicate=result.duplicate,
                skipped=result.skipped,
            )
        )
        return 0 if result.failed == 0 else 2

    if args.command == "normalize-url":
        result = normalize_url_raw(args.url)
        print(f"input: {args.url}")
        print(f"category: {result.category}")
        print(f"method: {result.method}")
        print(f"normalized: {result.normalized}")
        if result.messages:
            for msg in result.messages:
                print(f"message: {msg}")
        return 0 if result.normalized is not None else 1

    if args.command == "status":
        print_status(args.db)
        return 0

    if args.command == "seed-profiles":
        init_db(args.db)
        count = seed_profiles(args.db)
        print(f"profiles_seeded={count}")
        return 0

    if args.command == "discover-candidates":
        init_db(args.db)
        providers = build_discovery_providers(
            args.provider,
            db_path=args.db,
            refresh_provider_cache=args.refresh_provider_cache,
        )
        result = run_discovery(
            db_path=args.db,
            profile_name=args.profile,
            providers=providers,
            limit=args.limit,
        )
        print(
            "providers={providers} total_seen={total_seen} stored={stored} skipped={skipped} errors={errors}".format(
                providers=",".join(provider.name for provider in providers),
                total_seen=result.total_seen,
                stored=result.stored_count,
                skipped=result.skipped_count,
                errors=len(result.errors),
            )
        )
        for error in result.errors:
            print(f"provider_error: {error}")
        return 0 if result.stored_count > 0 or not result.errors else 2

    if args.command == "list-candidates":
        rows = list_candidates(args.db, args.profile, args.limit)
        for row in rows:
            print(
                f"{row['score']:.4f} | {row['published_date']} | "
                f"{row['source']} | {row['title']} | {row['url']}"
            )
        return 0

    if args.command == "export-candidates":
        count = export_candidates(args.db, args.profile, args.limit, args.out)
        print(f"candidates_exported={count} out={args.out}")
        return 0

    if args.command == "dedupe-candidates":
        result = materialize_candidate_papers(args.db)
        print(
            "candidates_seen={seen} canonical={canonical} links={links} skipped={skipped}".format(
                seen=result.candidates_seen,
                canonical=result.canonical_count,
                links=result.links_count,
                skipped=result.skipped_count,
            )
        )
        return 0

    if args.command == "list-canonical-candidates":
        rows = list_canonical_candidates(args.db, args.limit)
        for row in rows:
            print(
                f"{row['best_score']:.4f} | {row['published_date']} | "
                f"{row['sources_json']} | {row['profiles_json']} | {row['title']} | {row['url']}"
            )
        return 0

    if args.command == "export-canonical-candidates":
        count = export_canonical_candidates(args.db, args.limit, args.out)
        print(f"canonical_candidates_exported={count} out={args.out}")
        return 0

    if args.command == "export-candidate-review":
        result = export_candidate_review(
            args.db,
            args.out,
            markdown_path=args.markdown_out,
            min_score=args.min_score,
            limit=args.limit,
        )
        print(
            "candidate_review_exported total={total} selected={selected} already_in_database={existing} "
            "below_min_score={below} not_in_top_limit={not_top} out={out}".format(
                total=result.total_count,
                selected=result.selected_count,
                existing=result.already_in_database_count,
                below=result.below_min_score_count,
                not_top=result.not_in_top_limit_count,
                out=result.json_path,
            )
        )
        if result.markdown_path is not None:
            print(f"candidate_review_markdown={result.markdown_path}")
        return 0

    if args.command == "set-canonical-status":
        updated = set_canonical_status(args.db, args.canonical_key, args.status)
        if not updated:
            print(f"canonical_candidate_not_found={args.canonical_key}")
            return 2
        print(f"canonical_candidate_updated={args.canonical_key} status={args.status}")
        return 0

    if args.command == "select-canonical-candidates":
        try:
            count = select_top_canonical_candidates(args.db, args.limit, args.min_score)
        except ValueError as exc:
            print(str(exc))
            return 2
        print(f"canonical_candidates_selected={count}")
        return 0

    if args.command == "export-approved-candidates":
        count = export_approved_candidates(args.db, args.out)
        print(f"approved_candidates_exported={count} out={args.out}")
        return 0


    if args.command == "extract-paper-cards":
        result = extract_paper_cards(args.db, limit=args.limit, paper_key=args.paper_key)
        print(
            "papers_seen={seen} cards={cards} nodes={nodes} edges={edges} provenance={provenance}".format(
                seen=result.papers_seen,
                cards=result.cards_written,
                nodes=result.nodes_written,
                edges=result.edges_written,
                provenance=result.provenance_written,
            )
        )
        return 0

    if args.command == "list-paper-cards":
        rows = list_paper_cards(args.db, args.limit)
        for row in rows:
            print(
                f"{row['paper_key']} | {row['year'] or ''} | "
                f"{row['status']} | {row['title']}"
            )
        return 0

    if args.command == "export-paper-cards":
        count = export_paper_cards(args.db, args.out)
        print(f"paper_cards_exported={count} out={args.out}")
        return 0

    if args.command == "extract-layout-evidence-graph":
        result = extract_layout_evidence_graph(args.db, paper_key=args.paper_key, limit=args.limit)
        print(
            "layout_evidence_graph_extracted papers={papers} facts={facts} evidence={evidence} "
            "edges={edges} supported={supported} provenance={provenance}".format(
                papers=result.papers_seen,
                facts=result.fact_nodes_written,
                evidence=result.evidence_nodes_written,
                edges=result.edges_written,
                supported=result.supported_by_edges,
                provenance=result.provenance_written,
            )
        )
        return 0

    if args.command == "export-layout-evidence-graph":
        count = export_layout_evidence_graph(args.db, args.out)
        print(f"layout_evidence_graph_exported={count} out={args.out}")
        return 0


    if args.command == "extract-research-facts":
        try:
            paper_list = getattr(args, "paper_list", None)
            if args.paper_key and paper_list:
                raise FactValidationError("use only one of --paper-key and --paper-list")
            selected_paper_keys = None
            if paper_list:
                selected_paper_keys = [
                    line.split("#", 1)[0].strip()
                    for line in paper_list.read_text(encoding="utf-8").splitlines()
                    if line.split("#", 1)[0].strip()
                ]
                if not selected_paper_keys:
                    raise FactValidationError("--paper-list is empty")
            required_fact_types = {}
            required_file = getattr(args, "required_fact_types_file", None)
            if required_file:
                for raw_line in required_file.read_text(encoding="utf-8").splitlines():
                    line = raw_line.split("#", 1)[0].strip()
                    if not line:
                        continue
                    if "=" not in line:
                        raise FactValidationError("invalid required fact type line: " + line)
                    key, raw_types = (part.strip() for part in line.split("=", 1))
                    types = [value.strip() for value in raw_types.split(",") if value.strip()]
                    if not key or not types or any(value not in {"method", "dataset", "benchmark", "claim", "limitation"} for value in types):
                        raise FactValidationError("invalid required fact type line: " + line)
                    required_fact_types[key] = types
            result = extract_research_facts(
                args.db,
                provider_name=args.provider,
                fixture_path=args.fixture,
                paper_key=args.paper_key,
                paper_keys=selected_paper_keys,
                required_fact_types=required_fact_types,
                limit=args.limit,
                model=args.model,
                base_url=args.base_url,
                api_key_env=args.api_key_env,
                dry_run=args.dry_run,
                refresh_cache=args.refresh_cache,
                max_input_chars=args.max_input_chars,
                concurrency=args.concurrency,
                error_policy=args.fact_error_policy,
            )
        except FactValidationError as exc:
            print(str(exc))
            return 2
        graph = None
        if not args.dry_run:
            graph_results = [
                extract_layout_evidence_graph(args.db, paper_key=key, limit=1)
                for key in (selected_paper_keys or [args.paper_key])
            ]
            if len(graph_results) == 1:
                graph = graph_results[0]
            else:
                graph = type(graph_results[0])(
                    papers_seen=sum(item.papers_seen for item in graph_results),
                    fact_nodes_written=sum(item.fact_nodes_written for item in graph_results),
                    evidence_nodes_written=sum(item.evidence_nodes_written for item in graph_results),
                    edges_written=sum(item.edges_written for item in graph_results),
                    supported_by_edges=sum(item.supported_by_edges for item in graph_results),
                    provenance_written=sum(item.provenance_written for item in graph_results),
                )
        print(
            "papers_seen={seen} facts={facts} provenance={provenance} "
            "cache_hits={cache_hits} llm_calls={llm_calls} dry_runs={dry_runs} "
            "failed={failed}{graph_summary}".format(
                seen=result.papers_seen,
                facts=result.facts_written,
                provenance=result.provenance_written,
                cache_hits=result.cache_hits,
                llm_calls=result.llm_calls,
                dry_runs=result.dry_runs,
                failed=result.failed_count,
                graph_summary=(
                    " graph_facts={facts} graph_evidence={evidence} graph_supported={supported}".format(
                        facts=graph.fact_nodes_written,
                        evidence=graph.evidence_nodes_written,
                        supported=graph.supported_by_edges,
                    )
                    if graph is not None
                    else ""
                ),
            )
        )
        return 0

    if args.command == "list-research-facts":
        rows = list_research_facts(
            args.db,
            paper_key=args.paper_key,
            fact_type=args.type,
            limit=args.limit,
        )
        for row in rows:
            print(
                f"{row['paper_key']} | {row['fact_type']} | "
                f"{row['confidence']:.2f} | {row['statement']}"
            )
        return 0

    if args.command == "export-research-facts":
        count = export_research_facts(args.db, args.out)
        print(f"research_facts_exported={count} out={args.out}")
        return 0

    if args.command == "claim-trace":
        try:
            rendered = export_claim_trace(
                args.db,
                out_path=args.out,
                output_format=args.format,
                fact_id=args.fact_id,
                paper_key=args.paper_key,
                fact_type=args.type,
                query=args.query,
            )
        except (ClaimTraceNotFound, ValueError) as exc:
            print(str(exc))
            return 2
        if args.out is not None:
            print(f"claim_trace_exported format={args.format} out={args.out}")
        else:
            print(rendered, end="")
        return 0

    if args.command == "extract-artifact-ledger":
        result = extract_artifact_ledger(args.db, paper_key=args.paper_key, limit=args.limit)
        print(
            "artifact_ledger_extracted papers_seen={papers} chunks_written={chunks} "
            "equations_written={equations} citations_written={citations}".format(
                papers=result.papers_seen,
                chunks=result.chunks_written,
                equations=result.equations_written,
                citations=result.citations_written,
            )
        )
        return 0

    if args.command == "export-artifact-ledger":
        try:
            result = export_artifact_ledger(args.db, args.out, output_format=args.format)
        except ValueError as exc:
            print(str(exc))
            return 2
        print(
            "artifact_ledger_exported papers={papers} chunks={chunks} equations={equations} "
            "citations={citations} format={format} out={out}".format(
                papers=result.paper_count,
                chunks=result.chunk_count,
                equations=result.equation_count,
                citations=result.citation_count,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "audit-research-facts":
        result = audit_research_facts(args.db)
        print(f"total_facts={result.total_facts}")
        print(f"paper_count={result.paper_count}")
        for fact_type, count in result.fact_type_counts.items():
            print(f"fact_type.{fact_type}={count}")
        print(f"empty_statement={result.empty_statement}")
        print(f"missing_evidence_quote={result.missing_evidence_quote}")
        print(f"missing_evidence_artifact_type={result.missing_evidence_artifact_type}")
        print(f"missing_evidence_source_path={result.missing_evidence_source_path}")
        print(f"invalid_confidence={result.invalid_confidence}")
        print(f"invalid_fact_type={result.invalid_fact_type}")
        print(f"duplicate_statements={result.duplicate_statements}")
        print(f"hard_failures={result.hard_failures}")
        print(f"soft_warnings={result.soft_warnings}")
        return 1 if result.hard_failures else 0

    if args.command == "repair-evidence-source-paths":
        result = export_evidence_source_path_repairs(
            args.db,
            args.out,
            apply=args.apply,
            paper_key=args.paper_key,
        )
        print(
            "evidence_source_path_repair candidates={candidates} repairable={repairable} "
            "applied={applied} out={out}".format(
                candidates=result.candidate_count,
                repairable=result.repairable_count,
                applied=result.applied_count,
                out=args.out,
            )
        )
        return 0

    if args.command == "generate-research-digest":
        try:
            result = export_research_digest(args.db, args.out, output_format=args.format)
        except DigestInputError as exc:
            print(str(exc))
            return 2
        print(
            "research_digest_exported={papers} facts={facts} format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "generate-research-map":
        try:
            result = export_research_map(args.db, args.out, output_format=args.format)
        except DigestInputError as exc:
            print(str(exc))
            return 2
        print(
            "research_map_exported={papers} facts={facts} items={items} format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                items=result.item_count,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "generate-research-relations":
        try:
            result = export_research_relations(args.db, args.out, output_format=args.format)
        except DigestInputError as exc:
            print(str(exc))
            return 2
        print(
            "research_relations_exported={papers} facts={facts} relations={relations} "
            "code_relations={code_relations} dataset_relations={dataset_relations} "
            "format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                relations=result.relation_count,
                code_relations=result.code_relation_count,
                dataset_relations=result.dataset_relation_count,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "generate-gap-analysis":
        try:
            result = export_gap_analysis(args.db, args.out, output_format=args.format)
        except DigestInputError as exc:
            print(str(exc))
            return 2
        print(
            "gap_analysis_exported={papers} facts={facts} missing_papers={missing_papers} "
            "format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                missing_papers=len(result.papers_missing_fact_types),
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "generate-research-synthesis":
        try:
            result = export_research_synthesis(args.db, args.out, output_format=args.format)
        except DigestInputError as exc:
            print(str(exc))
            return 2
        print(
            "research_synthesis_exported={papers} facts={facts} targets={targets} "
            "format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                targets=result.extraction_target_count,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "generate-narrative-report":
        try:
            result = export_narrative_report(args.db, args.out, output_format=args.format)
        except DigestInputError as exc:
            print(str(exc))
            return 2
        print(
            "narrative_report_exported={papers} facts={facts} findings={findings} actions={actions} "
            "format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                findings=result.finding_count,
                actions=result.action_count,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "generate-research-clusters":
        try:
            embedding_provider = (
                OpenAICompatibleEmbeddingProvider.from_env()
                if args.mode == "semantic"
                else None
            )
            result = export_research_clusters(
                args.db,
                args.out,
                output_format=args.format,
                mode=args.mode,
                embedding_provider=embedding_provider,
                semantic_threshold=args.semantic_threshold,
            )
        except (DigestInputError, SemanticClusteringError, EmbeddingProviderError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "research_clusters_exported={papers} facts={facts} clusters={clusters} singletons={singletons} "
            "mode={mode} format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                clusters=result.cluster_count,
                singletons=result.singleton_count,
                mode=result.mode,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "generate-cluster-review":
        try:
            embedding_provider = (
                OpenAICompatibleEmbeddingProvider.from_env()
                if args.mode == "semantic"
                else None
            )
            result = export_cluster_review_packet(
                args.db,
                args.out,
                output_format=args.format,
                mode=args.mode,
                embedding_provider=embedding_provider,
                semantic_threshold=args.semantic_threshold,
            )
        except (DigestInputError, SemanticClusteringError, EmbeddingProviderError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "cluster_review_exported={papers} facts={facts} items={items} accept_candidates={accepts} "
            "needs_review={needs_review} mode={mode} format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                items=result.review_item_count,
                accepts=result.accept_candidate_count,
                needs_review=result.needs_review_count,
                mode=result.mode,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "summarize-cluster-review":
        try:
            result = export_reviewed_cluster_summary(
                args.review_packet,
                args.out,
                output_format=args.format,
            )
        except (ClusterReviewSummaryError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "cluster_review_summary_exported={items} accepted={accepted} accepted_facts={facts} "
            "accepted_papers={papers} format={format} out={out}".format(
                items=result.review_item_count,
                accepted=result.accepted_count,
                facts=result.accepted_fact_count,
                papers=result.accepted_paper_count,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "set-cluster-review-status":
        try:
            result = set_cluster_review_status(
                args.review_packet,
                args.out,
                cluster_id=args.cluster_id,
                status=args.status,
                notes=args.notes,
            )
        except ClusterReviewEditError as exc:
            print(str(exc))
            return 2
        print(
            "cluster_review_status_updated={cluster_id} previous={previous} status={status} out={out}".format(
                cluster_id=result.cluster_id,
                previous=result.previous_status,
                status=result.new_status,
                out=result.out_path,
            )
        )
        return 0

    if args.command == "generate-report-bundle":
        try:
            result = export_report_bundle(
                args.db,
                args.out_dir,
                review_packet_path=args.review_packet,
            )
        except (DigestInputError, ClusterReviewSummaryError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "report_bundle_exported={artifacts} papers={papers} facts={facts} out_dir={out_dir}".format(
                artifacts=result.artifact_count,
                papers=result.paper_count,
                facts=result.fact_count,
                out_dir=args.out_dir,
            )
        )
        return 0

    if args.command == "generate-report-site":
        try:
            result = export_report_site(args.bundle_dir, args.out)
        except (ValueError, OSError) as exc:
            print(str(exc))
            return 2
        print(
            "report_site_exported={reports} artifacts={artifacts} out={out}".format(
                reports=result.report_count,
                artifacts=result.artifact_count,
                out=result.out_path,
            )
        )
        return 0

    if args.command == "run-mvp-pipeline":
        try:
            result = run_mvp_pipeline(
                db_path=args.db,
                paper_db_path=args.paper_db,
                out_dir=args.out_dir,
                fact_provider=args.fact_provider,
                fixture_path=args.fixture,
                model=args.model,
                base_url=args.base_url,
                api_key_env=args.api_key_env,
                concurrency=args.concurrency,
                refresh_facts=args.refresh_facts,
                fact_error_policy=args.fact_error_policy,
                semantic=args.semantic,
                semantic_threshold=args.semantic_threshold,
            )
        except (
            DigestInputError,
            ClusterReviewSummaryError,
            FactValidationError,
            SemanticClusteringError,
            EmbeddingProviderError,
            ValueError,
            OSError,
        ) as exc:
            print(str(exc))
            return 2
        print(
            "mvp_pipeline_completed papers={papers} cards={cards} facts={facts} fact_failures={fact_failures} repaired={repaired} "
            "graph_facts={graph_facts} graph_evidence={graph_evidence} graph_supported={graph_supported} "
            "artifacts={artifacts} site={site}".format(
                papers=result.papers_seen,
                cards=result.cards_written,
                facts=result.facts_written,
                fact_failures=result.fact_failures,
                repaired=result.repaired_paths,
                graph_facts=result.graph_fact_nodes,
                graph_evidence=result.graph_evidence_nodes,
                graph_supported=result.graph_supported_edges,
                artifacts=result.bundle_artifacts,
                site=result.site_path,
            )
        )
        print("steps=" + ",".join(result.steps))
        return 0

    if args.command == "run-launch-refresh":
        try:
            providers = build_discovery_providers(
                args.provider,
                db_path=args.db,
                refresh_provider_cache=args.refresh_provider_cache,
            )
            profile_names = args.profile or [profile.name for profile in default_profiles()]
            progress = (
                LaunchRefreshProgress(
                    total=launch_refresh_progress_total(
                        profile_count=len(profile_names),
                        provider_count=len(providers),
                    )
                )
                if args.progress
                else None
            )
            result = run_launch_refresh(
                db_path=args.db,
                paper_db_path=args.paper_db,
                providers=providers,
                profile_names=profile_names,
                limit_per_profile=args.limit_per_profile,
                select_limit=args.select_limit,
                min_score=args.min_score,
                approved_manifest_path=args.approved_manifest,
                papi_executable=args.papi,
                out_dir=args.out_dir,
                site_dir=args.site_dir,
                run_manifest_path=args.run_manifest,
                candidate_review_json_path=args.candidate_review,
                candidate_review_markdown_path=args.candidate_review_md,
                fact_provider=args.fact_provider,
                fixture_path=args.fixture,
                model=args.model,
                base_url=args.base_url,
                api_key_env=args.api_key_env,
                concurrency=args.concurrency,
                refresh_facts=args.refresh_facts,
                fact_error_policy=args.fact_error_policy,
                semantic=args.semantic,
                semantic_threshold=args.semantic_threshold,
                history_dir=args.history_dir,
                log_dir=args.log_dir,
                progress_callback=progress,
            )
        except (
            DigestInputError,
            ClusterReviewSummaryError,
            FactValidationError,
            SemanticClusteringError,
            EmbeddingProviderError,
            ValueError,
            OSError,
        ) as exc:
            print(str(exc))
            return 2
        discovered = sum(item.stored_count for item in result.discovery)
        discovery_errors = sum(len(item.errors) for item in result.discovery)
        batch_failed = result.batch.failed if result.batch is not None else 0
        print(
            "launch_refresh_completed profiles={profiles} providers={providers} discovered={discovered} "
            "canonical={canonical} selected={selected} approved={approved} batch_failed={batch_failed} "
            "papers={papers} facts={facts} fact_failures={fact_failures} site={site} run_manifest={run_manifest}".format(
                profiles=len(result.profile_names),
                providers=",".join(result.provider_names),
                discovered=discovered,
                canonical=result.canonical.canonical_count,
                selected=result.selected_count,
                approved=result.approved_count,
                batch_failed=batch_failed,
                papers=result.mvp.papers_seen,
                facts=result.mvp.facts_written,
                fact_failures=result.mvp.fact_failures,
                site=result.publish.entrypoint,
                run_manifest=result.run_manifest_path,
            )
        )
        print(f"discovery_errors={discovery_errors}")
        print(f"run_history={result.run_history_path}")
        print(f"run_log={result.concise_log_path}")
        print(f"publish_diff={result.publish.diff_path}")
        print(f"candidate_review={result.candidate_review.json_path}")
        print(f"candidate_review_markdown={result.candidate_review.markdown_path}")
        print("steps=" + ",".join(result.steps))
        return 0 if batch_failed == 0 else 2

    if args.command == "publish-static-site":
        try:
            result = publish_static_site(args.source_dir, args.out_dir, clean=not args.no_clean)
        except (ValueError, OSError) as exc:
            print(str(exc))
            return 2
        print(
            "static_site_published files={files} out={out} entrypoint={entrypoint} manifest={manifest}".format(
                files=result.file_count,
                out=result.out_dir,
                entrypoint=result.entrypoint,
                manifest=result.manifest_path,
            )
        )
        return 0

    if args.command == "serve-report-site":
        url = f"http://{args.host}:{args.port}/"
        print(f"serving_report_site url={url} dir={args.dir}")
        try:
            serve_report_site(args.dir, args.host, args.port)
        except KeyboardInterrupt:
            print("serve_report_site_stopped")
            return 0
        except (ValueError, OSError) as exc:
            print(str(exc))
            return 2
        return 0

    if args.command == "write-static-host-config":
        try:
            result = write_static_host_config(
                args.site_dir,
                args.out_dir,
                base_path=args.base_path,
                deploy_root=args.deploy_root,
            )
        except (ValueError, OSError) as exc:
            print(str(exc))
            return 2
        print(
            "static_host_config_written config={config} manifest={manifest} site_dir={site_dir} base_path={base_path} deploy_root={deploy_root}".format(
                config=result.config_path,
                manifest=result.manifest_path,
                site_dir=result.site_dir,
                base_path=result.base_path,
                deploy_root=result.deploy_root,
            )
        )
        return 0

    if args.command == "write-static-deploy-scripts":
        try:
            result = write_static_deploy_scripts(
                args.site_dir,
                args.out_dir,
                deploy_root=args.deploy_root,
                snapshot_root=args.snapshot_root,
            )
        except (ValueError, OSError) as exc:
            print(str(exc))
            return 2
        print(
            "static_deploy_scripts_written deploy={deploy} rollback={rollback} manifest={manifest} deploy_root={deploy_root} snapshot_root={snapshot_root}".format(
                deploy=result.deploy_script_path,
                rollback=result.rollback_script_path,
                manifest=result.manifest_path,
                deploy_root=result.deploy_root,
                snapshot_root=result.snapshot_root,
            )
        )
        return 0

    if args.command == "health-check":
        result = run_health_check(
            db_path=args.db,
            paper_db_path=args.paper_db,
            site_dir=args.site_dir,
            require_fact_provider=args.require_fact_provider,
            require_embedding=args.require_embedding,
            required_env=args.required_env,
        )
        status = "ok" if result.ok else "fail"
        print(f"health_check status={status} checks={len(result.checks)} failed={result.failed_count}")
        for check in result.checks:
            check_status = "ok" if check.ok else "fail"
            print(f"{check_status} {check.name} {check.detail}")
        return 0 if result.ok else 1

    if args.command == "backup-db":
        try:
            result = backup_sqlite_db(db_path=args.db, out_dir=args.out_dir, label=args.label)
        except (ValueError, OSError, sqlite3.Error) as exc:
            print(str(exc))
            return 2
        print(
            "db_backup_created backup={backup} manifest={manifest} bytes={bytes} sha256={sha256}".format(
                backup=result.backup_path,
                manifest=result.manifest_path,
                bytes=result.size_bytes,
                sha256=result.sha256,
            )
        )
        return 0

    if args.command == "write-refresh-wrapper":
        try:
            result = write_scheduled_refresh_wrapper(
                wrapper_path=args.out,
                project_dir=args.project_dir,
                schedule=args.schedule,
                log_dir=args.log_dir,
                history_dir=args.history_dir,
                refresh_command=args.refresh_command,
            )
        except (ValueError, OSError) as exc:
            print(str(exc))
            return 2
        print(
            "refresh_wrapper_written path={path} schedule={schedule} log_dir={log_dir} history_dir={history_dir}".format(
                path=result.wrapper_path,
                schedule=result.schedule,
                log_dir=result.log_dir,
                history_dir=result.history_dir,
            )
        )
        return 0

    if args.command == "calibrate-research-clusters":
        try:
            embedding_provider = OpenAICompatibleEmbeddingProvider.from_env()
            result = export_cluster_calibration_report(
                args.db,
                args.out,
                embedding_provider=embedding_provider,
                thresholds=args.threshold or DEFAULT_THRESHOLDS,
                embedding_model=embedding_provider.model,
                output_format=args.format,
            )
        except (DigestInputError, SemanticClusteringError, EmbeddingProviderError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "cluster_calibration_exported={papers} facts={facts} thresholds={thresholds} "
            "recommended_threshold={recommended_threshold:.4f} model={model} format={format} out={out}".format(
                papers=result.paper_count,
                facts=result.fact_count,
                thresholds=len(result.points),
                recommended_threshold=result.recommendation.threshold,
                model=result.embedding_model,
                format=args.format,
                out=args.out,
            )
        )
        return 0

    if args.command == "extract-code-links":
        result = extract_code_links(args.db, paper_key=args.paper_key, limit=args.limit)
        print(f"papers_seen={result.papers_seen} code_links={result.links_written}")
        return 0

    if args.command == "list-code-links":
        rows = list_code_links(args.db, paper_key=args.paper_key, limit=args.limit)
        for row in rows:
            print(f"{row['paper_key']} | {row['source_type']} | {row['url']}")
        return 0

    if args.command == "export-code-links":
        count = export_code_links(args.db, args.out)
        print(f"code_links_exported={count} out={args.out}")
        return 0

    if args.command == "serve-admin":
        serve_admin(
            host=args.host,
            port=args.port,
            base_path=args.base_path,
            db_path=args.db,
            paper_db_path=args.paper_db,
            project_dir=args.project_dir,
            deploy_script=args.deploy_script,
            papi_executable=args.papi,
        )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
