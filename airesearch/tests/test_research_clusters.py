import json
from pathlib import Path

import pytest

from airesearch.db import connect, init_db
from airesearch.research_clusters import (
    SemanticClusteringError,
    build_research_clusters,
    export_research_clusters,
    render_markdown,
    research_clusters_to_dict,
)
from airesearch.research_digest import DigestInputError


def make_cluster_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    now = "2026-06-09T00:00:00+00:00"
    with connect(db_path) as conn:
        for paper_key, title, year in [
            ("paper_a", "Attention World Model", 2026),
            ("paper_b", "Transformer World Model", 2025),
        ]:
            conn.execute(
                """
                insert into papers (
                    paper_key, title, authors_json, year, venue, ids_json, paper_dir,
                    meta_json, created_at, updated_at
                ) values (?, ?, '[]', ?, '', '{}', ?, '{}', ?, ?)
                """,
                (paper_key, title, year, f"/tmp/{paper_key}", now, now),
            )
            conn.execute(
                """
                insert into paper_cards (
                    paper_key, title, authors_json, year, venue, ids_json,
                    artifact_types_json, source_dir, status, extractor_version, created_at, updated_at
                ) values (?, ?, '[]', ?, '', '{}', '["summary"]', ?, 'complete', 'test', ?, ?)
                """,
                (paper_key, title, year, f"/tmp/{paper_key}", now, now),
            )

        facts = [
            (
                "paper_a",
                "method",
                "Attention world model",
                "The method uses transformer attention for world model state prediction planning.",
                0.94,
                "/tmp/paper_a/summary.md",
            ),
            (
                "paper_b",
                "method",
                "Transformer attention predictor",
                "The method uses transformer attention for world model state prediction planning.",
                0.91,
                "/tmp/paper_b/summary.md",
            ),
            (
                "paper_a",
                "claim",
                "Attention improves planning",
                "Attention world model components improve planning accuracy.",
                0.88,
                "/tmp/paper_a/summary.md",
            ),
            (
                "paper_b",
                "dataset",
                "Robot kitchen dataset",
                "The dataset contains robot kitchen manipulation episodes.",
                0.86,
                "/tmp/paper_b/summary.md",
            ),
        ]
        for paper_key, fact_type, name, statement, confidence, source_path in facts:
            cursor = conn.execute(
                """
                insert into research_facts (
                    paper_key, fact_type, name, statement, confidence, metadata_json,
                    provider_name, extractor_version, created_at, updated_at
                ) values (?, ?, ?, ?, ?, '{}', 'fixture', 'test', ?, ?)
                """,
                (paper_key, fact_type, name, statement, confidence, now, now),
            )
            conn.execute(
                """
                insert into research_fact_provenance (
                    fact_id, evidence_quote, evidence_artifact_type, evidence_source_path, created_at
                ) values (?, ?, 'summary', ?, ?)
                """,
                (cursor.lastrowid, statement, source_path, now),
            )
        conn.commit()
    return db_path


def test_build_research_clusters_groups_similar_same_type_facts(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)

    report = build_research_clusters(db_path)

    assert report.paper_count == 2
    assert report.fact_count == 4
    assert report.cluster_count == 1
    assert report.clustered_fact_count == 2
    assert report.singleton_count == 2
    cluster = report.clusters[0]
    assert cluster.fact_type == "method"
    assert cluster.paper_count == 2
    assert cluster.fact_count == 2
    assert "attention" in cluster.token_signature
    assert "transformer" in cluster.token_signature
    assert {fact.paper_key for fact in cluster.facts} == {"paper_a", "paper_b"}
    assert {summary.fact_type: summary.fact_count for summary in report.singleton_summaries} == {
        "dataset": 1,
        "claim": 1,
    }
    assert report.mode == "token"
    assert report.semantic_threshold is None


class FixtureEmbeddingProvider:
    def embed_texts(self, texts):
        vectors = []
        for text in texts:
            if "attention world model" in text.lower():
                vectors.append([1.0, 0.0, 0.0])
            elif "transformer attention predictor" in text.lower():
                vectors.append([0.97, 0.03, 0.0])
            else:
                vectors.append([0.0, 1.0, 0.0])
        return vectors


def test_build_research_clusters_semantic_mode_uses_embedding_provider(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)

    report = build_research_clusters(
        db_path,
        mode="semantic",
        embedding_provider=FixtureEmbeddingProvider(),
        semantic_threshold=0.9,
    )

    assert report.mode == "semantic"
    assert report.semantic_threshold == 0.9
    assert report.cluster_count == 1
    cluster = report.clusters[0]
    assert cluster.fact_type == "method"
    assert {fact.paper_key for fact in cluster.facts} == {"paper_a", "paper_b"}


def test_build_research_clusters_semantic_mode_requires_provider(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)

    with pytest.raises(SemanticClusteringError, match="requires an embedding provider"):
        build_research_clusters(db_path, mode="semantic")


def test_build_research_clusters_rejects_invalid_semantic_threshold(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)

    with pytest.raises(ValueError, match="semantic_threshold must be between"):
        build_research_clusters(
            db_path,
            mode="semantic",
            embedding_provider=FixtureEmbeddingProvider(),
            semantic_threshold=1.5,
        )


def test_render_markdown_includes_clusters_and_singletons(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    report = build_research_clusters(db_path)

    markdown = render_markdown(report)

    assert "# AIResearch Research Clusters" in markdown
    assert "Clusters: 1" in markdown
    assert "Mode: token" in markdown
    assert "Singletons: 2" in markdown
    assert "Tokens: attention" in markdown
    assert "`paper_a` Attention World Model" in markdown
    assert "## Singleton Summary" in markdown
    assert "- Dataset: 1 facts across 1 papers" in markdown


def test_research_clusters_to_dict_and_export_json(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    markdown_path = tmp_path / "research-clusters.md"
    json_path = tmp_path / "research-clusters.json"

    markdown_report = export_research_clusters(db_path, markdown_path)
    json_report = export_research_clusters(db_path, json_path, output_format="json")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    direct_payload = research_clusters_to_dict(json_report)
    assert markdown_report.cluster_count == 1
    assert payload["paper_count"] == 2
    assert payload["fact_count"] == 4
    assert payload["mode"] == "token"
    assert payload["semantic_threshold"] is None
    assert payload["cluster_count"] == 1
    assert payload["clustered_fact_count"] == 2
    assert payload["singleton_count"] == 2
    assert payload["clusters"][0]["facts"][0]["paper_key"] in {"paper_a", "paper_b"}
    assert direct_payload["singleton_summaries"][0]["fact_type"] == "dataset"
    assert "# AIResearch Research Clusters" in markdown_path.read_text(encoding="utf-8")


def test_build_research_clusters_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        build_research_clusters(db_path)
