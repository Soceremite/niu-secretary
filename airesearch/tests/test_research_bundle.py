import json
from pathlib import Path

import pytest

from airesearch.artifact_ledger import extract_artifact_ledger
from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe
from airesearch.research_bundle import export_report_bundle
from airesearch.research_digest import DigestInputError


FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"
EXPECTED_FILES = {
    "digest.md",
    "digest.json",
    "artifact-ledger.md",
    "artifact-ledger.json",
    "map.md",
    "map.json",
    "relations.md",
    "relations.json",
    "gap-analysis.md",
    "gap-analysis.json",
    "synthesis.md",
    "synthesis.json",
    "narrative.md",
    "narrative.json",
    "clusters.md",
    "clusters.json",
    "manifest.json",
    "index.md",
}


def synced_fact_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_artifact_ledger(db_path)
    extract_paper_cards(db_path)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)
    return db_path


def test_export_report_bundle_writes_manifest_index_and_reports(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    out_dir = tmp_path / "bundle"

    bundle = export_report_bundle(db_path, out_dir)

    assert bundle.paper_count == 1
    assert bundle.fact_count == 2
    assert bundle.report_count == 8
    assert bundle.artifact_count == 18
    assert {path.name for path in out_dir.iterdir()} == EXPECTED_FILES
    payload = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["paper_count"] == 1
    assert payload["fact_count"] == 2
    assert payload["report_count"] == 8
    assert payload["artifact_count"] == 18
    assert [artifact["name"] for artifact in payload["artifacts"]] == [
        "digest",
        "artifact-ledger",
        "map",
        "relations",
        "gap-analysis",
        "synthesis",
        "narrative",
        "clusters",
    ]
    assert payload["artifacts"][1]["extra_counts"]["equation_count"] == 1
    assert payload["artifacts"][2]["extra_counts"]["item_count"] == 2
    assert payload["artifacts"][3]["extra_counts"]["relation_count"] == 0
    assert payload["artifacts"][6]["extra_counts"]["action_count"] == 1
    assert payload["artifacts"][7]["extra_counts"]["singleton_count"] == 2
    index = (out_dir / "index.md").read_text(encoding="utf-8")
    assert "# AIResearch Report Bundle" in index
    assert "[digest.md](digest.md)" in index
    assert "[manifest.json](manifest.json)" in index


def test_export_report_bundle_can_include_reviewed_clusters(tmp_path: Path):
    db_path = synced_fact_db(tmp_path)
    out_dir = tmp_path / "bundle"
    review_path = tmp_path / "review.json"
    review_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 1,
                "fact_count": 2,
                "mode": "token",
                "semantic_threshold": None,
                "items": [
                    {
                        "cluster_id": "method:attention-world",
                        "fact_type": "method",
                        "label": "Attention World",
                        "token_signature": ["attention", "world"],
                        "paper_count": 1,
                        "fact_count": 2,
                        "average_confidence": 0.91,
                        "recommended_status": "accept_candidate",
                        "review_status": "accepted",
                        "review_notes": "Confirmed.",
                        "rationale": "Cross-paper support.",
                        "facts": [
                            {
                                "paper_key": "1706_03762",
                                "paper_title": "Attention Is All You Need",
                                "year": 2017,
                                "fact_name": "Transformer",
                                "statement": "Uses attention.",
                                "confidence": 0.91,
                                "evidence_source_path": "/tmp/summary.md",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    bundle = export_report_bundle(db_path, out_dir, review_packet_path=review_path)

    assert bundle.report_count == 9
    assert bundle.artifact_count == 20
    assert (out_dir / "reviewed-clusters.md").exists()
    assert (out_dir / "reviewed-clusters.json").exists()
    payload = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["artifacts"][3]["name"] == "relations"
    assert payload["artifacts"][-1]["name"] == "reviewed-clusters"
    assert payload["artifacts"][-1]["extra_counts"]["accepted_count"] == 1
    assert payload["artifacts"][-1]["extra_counts"]["accepted_fact_count"] == 2
    index = (out_dir / "index.md").read_text(encoding="utf-8")
    assert "[reviewed-clusters.md](reviewed-clusters.md)" in index


def test_export_report_bundle_requires_paper_cards(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"

    with pytest.raises(DigestInputError, match="paper_cards is empty"):
        export_report_bundle(db_path, tmp_path / "bundle")
