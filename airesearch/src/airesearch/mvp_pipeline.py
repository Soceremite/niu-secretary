from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from airesearch.artifact_ledger import extract_artifact_ledger
from airesearch.code_links import extract_code_links
from airesearch.db import connect, init_db
from airesearch.embeddings import OpenAICompatibleEmbeddingProvider
from airesearch.evidence_repair import export_evidence_source_path_repairs
from airesearch.fact_audit import audit_research_facts
from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import export_paper_cards, extract_paper_cards
from airesearch.layout_evidence_graph import extract_layout_evidence_graph
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_bundle import export_report_bundle
from airesearch.research_cluster_review import export_cluster_review_packet
from airesearch.research_clusters import export_research_clusters
from airesearch.research_site import export_report_site


@dataclass(frozen=True)
class MvpPipelineResult:
    out_dir: Path
    site_path: Path
    papers_seen: int
    cards_written: int
    facts_written: int
    fact_failures: int
    hard_failures: int
    repaired_paths: int
    graph_fact_nodes: int
    graph_evidence_nodes: int
    graph_supported_edges: int
    bundle_artifacts: int
    steps: list[str] = field(default_factory=list)


def _table_count(db_path: Path, table: str) -> int:
    if not db_path.exists():
        return 0
    with connect(db_path) as conn:
        row = conn.execute(f"select count(*) from {table}").fetchone()
    return int(row[0]) if row else 0


def _delete_excluded_papers(db_path: Path, paper_keys: list[str]) -> int:
    keys = sorted({key for key in paper_keys if key})
    if not keys:
        return 0
    with connect(db_path) as conn:
        for paper_key in keys:
            conn.execute("delete from papers where paper_key = ?", (paper_key,))
        conn.commit()
    return len(keys)


def run_mvp_pipeline(
    *,
    db_path: Path,
    paper_db_path: Path,
    out_dir: Path,
    fact_provider: str = "openai-compatible",
    fixture_path: Path | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key_env: str = "AIRESEARCH_FACT_API_KEY",
    concurrency: int = 5,
    refresh_facts: bool = False,
    fact_error_policy: str = "strict",
    semantic: bool = False,
    semantic_threshold: float = 0.82,
    excluded_paper_keys: list[str] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> MvpPipelineResult:
    steps: list[str] = []

    def mark(step: str) -> None:
        steps.append(step)
        if progress_callback is not None:
            progress_callback(step)

    init_db(db_path)
    mark("init-db")

    sync_result = sync_paperpipe(db_path=db_path, paper_db_path=paper_db_path)
    mark("sync-paperpipe")

    excluded_count = _delete_excluded_papers(db_path, excluded_paper_keys or [])
    if excluded_count:
        mark(f"exclude-papers:{excluded_count}")

    card_result = extract_paper_cards(db_path)
    mark("extract-paper-cards")

    extract_code_links(db_path)
    mark("extract-code-links")

    extract_artifact_ledger(db_path)
    mark("extract-artifact-ledger")

    facts_before = _table_count(db_path, "research_facts")
    fact_result = None
    if refresh_facts or facts_before == 0:
        fact_result = extract_research_facts(
            db_path,
            provider_name=fact_provider,
            fixture_path=fixture_path,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            concurrency=concurrency,
            error_policy=fact_error_policy,
        )
        mark("extract-research-facts")
    else:
        mark("reuse-research-facts")

    audit = audit_research_facts(db_path)
    mark("audit-research-facts")
    if audit.hard_failures:
        raise ValueError(f"research fact audit failed: hard_failures={audit.hard_failures}")

    out_dir.mkdir(parents=True, exist_ok=True)
    repair = export_evidence_source_path_repairs(
        db_path,
        out_dir / "evidence-source-path-repair.jsonl",
        apply=True,
    )
    mark("repair-evidence-source-paths")

    graph = extract_layout_evidence_graph(db_path)
    mark("extract-layout-evidence-graph")

    export_paper_cards(db_path, out_dir / "paper-cards.jsonl")
    mark("export-paper-cards")

    embedding_provider = OpenAICompatibleEmbeddingProvider.from_env() if semantic else None
    mode = "semantic" if semantic else "token"
    export_research_clusters(
        db_path,
        out_dir / "research-clusters.md",
        mode=mode,
        embedding_provider=embedding_provider,
        semantic_threshold=semantic_threshold,
    )
    export_research_clusters(
        db_path,
        out_dir / "research-clusters.json",
        output_format="json",
        mode=mode,
        embedding_provider=embedding_provider,
        semantic_threshold=semantic_threshold,
    )
    mark("generate-research-clusters")

    review_packet = out_dir / "research-cluster-review.json"
    export_cluster_review_packet(
        db_path,
        out_dir / "research-cluster-review.md",
        mode=mode,
        embedding_provider=embedding_provider,
        semantic_threshold=semantic_threshold,
    )
    export_cluster_review_packet(
        db_path,
        review_packet,
        output_format="json",
        mode=mode,
        embedding_provider=embedding_provider,
        semantic_threshold=semantic_threshold,
    )
    mark("generate-cluster-review")

    bundle = export_report_bundle(
        db_path,
        out_dir / "bundle",
        review_packet_path=review_packet,
        concurrency=max(1, min(concurrency, 6)),
    )
    mark("generate-report-bundle")

    site = export_report_site(out_dir / "bundle")
    mark("generate-report-site")

    facts_after = _table_count(db_path, "research_facts")
    return MvpPipelineResult(
        out_dir=out_dir,
        site_path=site.out_path,
        papers_seen=sync_result.papers_seen,
        cards_written=card_result.cards_written,
        facts_written=fact_result.facts_written if fact_result is not None else facts_after,
        fact_failures=fact_result.failed_count if fact_result is not None else 0,
        hard_failures=audit.hard_failures,
        repaired_paths=repair.applied_count,
        graph_fact_nodes=graph.fact_nodes_written,
        graph_evidence_nodes=graph.evidence_nodes_written,
        graph_supported_edges=graph.supported_by_edges,
        bundle_artifacts=bundle.artifact_count + 1,
        steps=steps,
    )
