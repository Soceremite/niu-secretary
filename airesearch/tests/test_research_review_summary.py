import json
from pathlib import Path

import pytest

from airesearch.research_cluster_review import build_cluster_review_packet, cluster_review_packet_to_dict
from airesearch.research_review_summary import (
    ClusterReviewSummaryError,
    build_reviewed_cluster_summary,
    export_reviewed_cluster_summary,
    render_markdown,
    reviewed_cluster_summary_to_dict,
)
from test_research_clusters import make_cluster_db


def _write_review_packet(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_build_reviewed_cluster_summary_extracts_only_accepted_items(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    payload = cluster_review_packet_to_dict(build_cluster_review_packet(db_path))
    payload["items"][0]["review_status"] = "accepted"
    payload["items"][0]["review_notes"] = "Cross-paper method match confirmed."
    review_path = _write_review_packet(tmp_path / "review.json", payload)

    summary = build_reviewed_cluster_summary(review_path)

    assert summary.review_item_count == 1
    assert summary.status_counts["accepted"] == 1
    assert summary.status_counts["pending"] == 0
    assert summary.accepted_count == 1
    assert summary.accepted_fact_count == 2
    assert summary.accepted_paper_count == 2
    assert summary.accepted_items[0].review_notes == "Cross-paper method match confirmed."
    assert {fact.paper_key for fact in summary.accepted_items[0].facts} == {"paper_a", "paper_b"}


def test_build_reviewed_cluster_summary_counts_rejected_and_pending_without_accepting(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    payload = cluster_review_packet_to_dict(build_cluster_review_packet(db_path))
    payload["items"].append(dict(payload["items"][0], cluster_id="method:second", review_status="rejected"))
    review_path = _write_review_packet(tmp_path / "review.json", payload)

    summary = build_reviewed_cluster_summary(review_path)

    assert summary.review_item_count == 2
    assert summary.status_counts["pending"] == 1
    assert summary.status_counts["rejected"] == 1
    assert summary.accepted_count == 0
    assert summary.accepted_items == []


def test_render_markdown_and_json_export_include_accepted_clusters(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    payload = cluster_review_packet_to_dict(build_cluster_review_packet(db_path))
    payload["items"][0]["review_status"] = "accepted"
    review_path = _write_review_packet(tmp_path / "review.json", payload)
    markdown_path = tmp_path / "review-summary.md"
    json_path = tmp_path / "review-summary.json"

    markdown_summary = export_reviewed_cluster_summary(review_path, markdown_path)
    json_summary = export_reviewed_cluster_summary(review_path, json_path, output_format="json")

    markdown = markdown_path.read_text(encoding="utf-8")
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    direct = reviewed_cluster_summary_to_dict(json_summary)
    assert markdown_summary.accepted_count == 1
    assert "# AIResearch Reviewed Cluster Summary" in markdown
    assert "Accepted clusters: 1" in markdown
    assert "Attention World Model" in markdown
    assert exported["accepted_count"] == 1
    assert direct["accepted_items"][0]["facts"][0]["paper_key"] in {"paper_a", "paper_b"}
    assert render_markdown(json_summary).startswith("# AIResearch Reviewed Cluster Summary")


def test_build_reviewed_cluster_summary_rejects_unknown_status(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    payload = cluster_review_packet_to_dict(build_cluster_review_packet(db_path))
    payload["items"][0]["review_status"] = "approved"
    review_path = _write_review_packet(tmp_path / "review.json", payload)

    with pytest.raises(ClusterReviewSummaryError, match="unsupported review_status"):
        build_reviewed_cluster_summary(review_path)
