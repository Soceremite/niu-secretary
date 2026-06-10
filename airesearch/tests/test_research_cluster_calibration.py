import json
from pathlib import Path

import pytest

from airesearch.research_cluster_calibration import (
    ClusterCalibrationPoint,
    build_cluster_calibration_report,
    cluster_calibration_to_dict,
    export_cluster_calibration_report,
    recommend_threshold,
    render_markdown,
)
from test_research_clusters import make_cluster_db


class CountingEmbeddingProvider:
    def __init__(self):
        self.calls = 0
        self.text_count = 0

    def embed_texts(self, texts):
        self.calls += 1
        self.text_count = len(texts)
        vectors = []
        for text in texts:
            lower = text.lower()
            if "attention world model" in lower:
                vectors.append([1.0, 0.0])
            elif "transformer attention predictor" in lower:
                vectors.append([0.8, 0.2])
            else:
                vectors.append([0.0, 1.0])
        return vectors


def test_build_cluster_calibration_report_reuses_embeddings_for_thresholds(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    provider = CountingEmbeddingProvider()

    report = build_cluster_calibration_report(
        db_path,
        embedding_provider=provider,
        thresholds=[0.99, 0.5, 0.9, 0.9],
        embedding_model="fixture-embedding",
    )

    assert provider.calls == 1
    assert provider.text_count == 4
    assert report.paper_count == 2
    assert report.fact_count == 4
    assert report.embedding_model == "fixture-embedding"
    assert [point.threshold for point in report.points] == [0.5, 0.9, 0.99]
    assert report.points[0].cluster_count == 1
    assert report.points[0].clustered_fact_count == 2
    assert report.points[-1].cluster_count == 0
    assert report.points[-1].singleton_count == 4
    assert report.recommendation.threshold == 0.9
    assert report.recommendation.policy == "highest_threshold_with_minimum_coverage"


def test_cluster_calibration_markdown_and_json_export(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)
    markdown_path = tmp_path / "calibration.md"
    json_path = tmp_path / "calibration.json"

    markdown_report = export_cluster_calibration_report(
        db_path,
        markdown_path,
        embedding_provider=CountingEmbeddingProvider(),
        thresholds=[0.9],
        embedding_model="fixture-embedding",
    )
    json_report = export_cluster_calibration_report(
        db_path,
        json_path,
        embedding_provider=CountingEmbeddingProvider(),
        thresholds=[0.9],
        embedding_model="fixture-embedding",
        output_format="json",
    )

    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    direct_payload = cluster_calibration_to_dict(json_report)
    assert markdown_report.points[0].threshold == 0.9
    assert "# AIResearch Semantic Cluster Calibration" in markdown
    assert "Recommended threshold: 0.9000" in markdown
    assert "| 0.9000 |" in markdown
    assert payload["embedding_model"] == "fixture-embedding"
    assert payload["recommendation"]["threshold"] == 0.9
    assert direct_payload["points"][0]["threshold"] == 0.9
    assert render_markdown(markdown_report).startswith("# AIResearch Semantic Cluster Calibration")


def test_build_cluster_calibration_report_rejects_invalid_thresholds(tmp_path: Path):
    db_path = make_cluster_db(tmp_path)

    with pytest.raises(ValueError, match="at least one threshold"):
        build_cluster_calibration_report(db_path, embedding_provider=CountingEmbeddingProvider(), thresholds=[])

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        build_cluster_calibration_report(db_path, embedding_provider=CountingEmbeddingProvider(), thresholds=[1.2])


def test_recommend_threshold_selects_highest_eligible_point():
    recommendation = recommend_threshold([
        ClusterCalibrationPoint(0.70, 6, 14, 20, 3, 5),
        ClusterCalibrationPoint(0.82, 3, 6, 28, 2, 2),
        ClusterCalibrationPoint(0.85, 1, 2, 32, 2, 1),
    ])

    assert recommendation.threshold == 0.82
    assert "highest threshold" in recommendation.rationale


def test_recommend_threshold_uses_scored_fallback_when_no_point_is_eligible():
    recommendation = recommend_threshold([
        ClusterCalibrationPoint(0.70, 2, 5, 20, 3, 4),
        ClusterCalibrationPoint(0.90, 1, 2, 23, 1, 1),
    ])

    assert recommendation.threshold == 0.70
    assert "fallback" in recommendation.rationale
