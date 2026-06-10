from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from airesearch.research_clusters import (
    EmbeddingProvider,
    cluster_facts_semantic_from_embeddings,
)
from airesearch.research_digest import DigestFact, DigestPaper, build_research_digest


DEFAULT_THRESHOLDS = (0.70, 0.75, 0.80, 0.82, 0.85, 0.90)
MIN_RECOMMENDED_CLUSTER_COUNT = 3
MIN_RECOMMENDED_CLUSTERED_FACT_COUNT = 6
MAX_RECOMMENDED_LARGEST_CLUSTER_SIZE = 3
RECOMMENDATION_POLICY = "highest_threshold_with_minimum_coverage"


@dataclass(frozen=True)
class ClusterCalibrationPoint:
    threshold: float
    cluster_count: int
    clustered_fact_count: int
    singleton_count: int
    largest_cluster_size: int
    clustered_paper_count: int


@dataclass(frozen=True)
class ClusterThresholdRecommendation:
    threshold: float
    policy: str
    rationale: str
    cluster_count: int
    clustered_fact_count: int
    singleton_count: int
    largest_cluster_size: int
    clustered_paper_count: int


@dataclass(frozen=True)
class ClusterCalibrationReport:
    generated_at: str
    paper_count: int
    fact_count: int
    embedding_model: str
    points: list[ClusterCalibrationPoint]
    recommendation: ClusterThresholdRecommendation


def _fact_items_from_digest(db_path: Path) -> tuple[str, int, int, list[tuple[str, DigestPaper, DigestFact]]]:
    digest = build_research_digest(db_path)
    items: list[tuple[str, DigestPaper, DigestFact]] = []
    for paper in digest.papers:
        for fact_type, facts in paper.facts.items():
            for fact in facts:
                items.append((fact_type, paper, fact))
    return digest.generated_at, digest.paper_count, digest.fact_count, items


def _normalize_thresholds(thresholds: Sequence[float]) -> list[float]:
    normalized = sorted({round(float(threshold), 4) for threshold in thresholds})
    if not normalized:
        raise ValueError("at least one threshold is required")
    invalid = [threshold for threshold in normalized if threshold < 0.0 or threshold > 1.0]
    if invalid:
        raise ValueError("threshold values must be between 0.0 and 1.0")
    return normalized


def recommend_threshold(points: Sequence[ClusterCalibrationPoint]) -> ClusterThresholdRecommendation:
    if not points:
        raise ValueError("at least one calibration point is required")
    eligible = [
        point
        for point in points
        if point.cluster_count >= MIN_RECOMMENDED_CLUSTER_COUNT
        and point.clustered_fact_count >= MIN_RECOMMENDED_CLUSTERED_FACT_COUNT
        and point.largest_cluster_size <= MAX_RECOMMENDED_LARGEST_CLUSTER_SIZE
    ]
    if eligible:
        selected = max(eligible, key=lambda point: point.threshold)
        rationale = (
            "Selected the highest threshold that keeps at least "
            f"{MIN_RECOMMENDED_CLUSTER_COUNT} clusters and "
            f"{MIN_RECOMMENDED_CLUSTERED_FACT_COUNT} clustered facts while limiting the largest cluster to "
            f"{MAX_RECOMMENDED_LARGEST_CLUSTER_SIZE} facts."
        )
    else:
        selected = max(
            points,
            key=lambda point: (
                point.clustered_fact_count + point.cluster_count + point.clustered_paper_count - point.largest_cluster_size,
                point.threshold,
            ),
        )
        rationale = (
            "No threshold met all conservative gates; selected the highest scoring fallback point by "
            "clustered_fact_count + cluster_count + clustered_paper_count - largest_cluster_size."
        )
    return ClusterThresholdRecommendation(
        threshold=selected.threshold,
        policy=RECOMMENDATION_POLICY,
        rationale=rationale,
        cluster_count=selected.cluster_count,
        clustered_fact_count=selected.clustered_fact_count,
        singleton_count=selected.singleton_count,
        largest_cluster_size=selected.largest_cluster_size,
        clustered_paper_count=selected.clustered_paper_count,
    )


def build_cluster_calibration_report(
    db_path: Path,
    *,
    embedding_provider: EmbeddingProvider,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    embedding_model: str = "unknown",
) -> ClusterCalibrationReport:
    threshold_values = _normalize_thresholds(thresholds)
    generated_at, paper_count, fact_count, items = _fact_items_from_digest(db_path)
    sorted_items = sorted(
        items,
        key=lambda item: (
            item[0],
            -item[2].confidence,
            item[1].title.lower(),
            item[1].paper_key,
            item[2].name.lower(),
            item[2].statement.lower(),
        ),
    )
    texts = [f"{fact.name}\n{fact.statement}" for _fact_type, _paper, fact in sorted_items]
    embeddings = embedding_provider.embed_texts(texts)

    points: list[ClusterCalibrationPoint] = []
    for threshold in threshold_values:
        clusters, singleton_summaries = cluster_facts_semantic_from_embeddings(
            sorted_items,
            embeddings,
            threshold=threshold,
        )
        clustered_paper_keys = {
            fact.paper_key
            for cluster in clusters
            for fact in cluster.facts
        }
        largest_cluster_size = max((cluster.fact_count for cluster in clusters), default=0)
        points.append(
            ClusterCalibrationPoint(
                threshold=threshold,
                cluster_count=len(clusters),
                clustered_fact_count=sum(cluster.fact_count for cluster in clusters),
                singleton_count=sum(summary.fact_count for summary in singleton_summaries),
                largest_cluster_size=largest_cluster_size,
                clustered_paper_count=len(clustered_paper_keys),
            )
        )
    return ClusterCalibrationReport(
        generated_at=generated_at,
        paper_count=paper_count,
        fact_count=fact_count,
        embedding_model=embedding_model,
        points=points,
        recommendation=recommend_threshold(points),
    )


def render_markdown(report: ClusterCalibrationReport) -> str:
    lines = [
        "# AIResearch Semantic Cluster Calibration",
        "",
        f"Generated: {report.generated_at}",
        f"Papers: {report.paper_count}",
        f"Facts: {report.fact_count}",
        f"Embedding model: {report.embedding_model}",
        f"Recommended threshold: {report.recommendation.threshold:.4f}",
        f"Recommendation policy: {report.recommendation.policy}",
        f"Recommendation rationale: {report.recommendation.rationale}",
        "",
        "| Threshold | Clusters | Clustered facts | Singletons | Largest cluster | Clustered papers |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for point in report.points:
        lines.append(
            "| {threshold:.4f} | {cluster_count} | {clustered_fact_count} | {singleton_count} | "
            "{largest_cluster_size} | {clustered_paper_count} |".format(
                threshold=point.threshold,
                cluster_count=point.cluster_count,
                clustered_fact_count=point.clustered_fact_count,
                singleton_count=point.singleton_count,
                largest_cluster_size=point.largest_cluster_size,
                clustered_paper_count=point.clustered_paper_count,
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def cluster_calibration_to_dict(report: ClusterCalibrationReport) -> dict[str, Any]:
    return {
        "generated_at": report.generated_at,
        "paper_count": report.paper_count,
        "fact_count": report.fact_count,
        "embedding_model": report.embedding_model,
        "recommendation": {
            "threshold": report.recommendation.threshold,
            "policy": report.recommendation.policy,
            "rationale": report.recommendation.rationale,
            "cluster_count": report.recommendation.cluster_count,
            "clustered_fact_count": report.recommendation.clustered_fact_count,
            "singleton_count": report.recommendation.singleton_count,
            "largest_cluster_size": report.recommendation.largest_cluster_size,
            "clustered_paper_count": report.recommendation.clustered_paper_count,
        },
        "points": [
            {
                "threshold": point.threshold,
                "cluster_count": point.cluster_count,
                "clustered_fact_count": point.clustered_fact_count,
                "singleton_count": point.singleton_count,
                "largest_cluster_size": point.largest_cluster_size,
                "clustered_paper_count": point.clustered_paper_count,
            }
            for point in report.points
        ],
    }


def export_cluster_calibration_report(
    db_path: Path,
    out_path: Path,
    *,
    embedding_provider: EmbeddingProvider,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    embedding_model: str = "unknown",
    output_format: str = "markdown",
) -> ClusterCalibrationReport:
    report = build_cluster_calibration_report(
        db_path,
        embedding_provider=embedding_provider,
        thresholds=thresholds,
        embedding_model=embedding_model,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(report), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(cluster_calibration_to_dict(report), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported cluster calibration format: {output_format}")
    return report
