import json
from pathlib import Path

import pytest

from airesearch.research_review_editor import (
    ClusterReviewEditError,
    set_cluster_review_status,
)


def _review_packet(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-09T00:00:00+00:00",
                "paper_count": 2,
                "fact_count": 2,
                "mode": "semantic",
                "semantic_threshold": 0.82,
                "items": [
                    {
                        "cluster_id": "method:attention-world",
                        "fact_type": "method",
                        "label": "Attention World",
                        "token_signature": ["attention", "world"],
                        "paper_count": 2,
                        "fact_count": 2,
                        "average_confidence": 0.91,
                        "recommended_status": "accept_candidate",
                        "review_status": "pending",
                        "review_notes": "",
                        "rationale": "Cross-paper support.",
                        "facts": [],
                    },
                    {
                        "cluster_id": "claim:second",
                        "fact_type": "claim",
                        "label": "Second",
                        "token_signature": ["second"],
                        "paper_count": 1,
                        "fact_count": 1,
                        "average_confidence": 0.88,
                        "recommended_status": "needs_review",
                        "review_status": "needs_revision",
                        "review_notes": "Keep existing.",
                        "rationale": "Needs checking.",
                        "facts": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_set_cluster_review_status_updates_one_item_and_notes(tmp_path: Path):
    review_path = _review_packet(tmp_path / "review.json")
    out_path = tmp_path / "edited.json"

    result = set_cluster_review_status(
        review_path,
        out_path,
        cluster_id="method:attention-world",
        status="accepted",
        notes="Confirmed.",
    )

    assert result.cluster_id == "method:attention-world"
    assert result.previous_status == "pending"
    assert result.new_status == "accepted"
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["items"][0]["review_status"] == "accepted"
    assert payload["items"][0]["review_notes"] == "Confirmed."
    assert payload["items"][1]["review_status"] == "needs_revision"


def test_set_cluster_review_status_preserves_notes_when_omitted(tmp_path: Path):
    review_path = _review_packet(tmp_path / "review.json")
    out_path = tmp_path / "edited.json"

    set_cluster_review_status(
        review_path,
        out_path,
        cluster_id="claim:second",
        status="rejected",
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["items"][1]["review_status"] == "rejected"
    assert payload["items"][1]["review_notes"] == "Keep existing."


def test_set_cluster_review_status_rejects_invalid_status(tmp_path: Path):
    review_path = _review_packet(tmp_path / "review.json")

    with pytest.raises(ClusterReviewEditError, match="unsupported review_status"):
        set_cluster_review_status(
            review_path,
            tmp_path / "edited.json",
            cluster_id="method:attention-world",
            status="approved",
        )


def test_set_cluster_review_status_rejects_missing_cluster(tmp_path: Path):
    review_path = _review_packet(tmp_path / "review.json")

    with pytest.raises(ClusterReviewEditError, match="cluster_id not found"):
        set_cluster_review_status(
            review_path,
            tmp_path / "edited.json",
            cluster_id="missing",
            status="accepted",
        )

