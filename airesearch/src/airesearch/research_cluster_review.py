from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.research_clusters import (
    SEMANTIC_CLUSTER_THRESHOLD,
    ClusterFactRef,
    EmbeddingProvider,
    ResearchCluster,
    build_research_clusters,
)


REVIEW_STATUS_PENDING = "pending"
RECOMMENDED_ACCEPT = "accept_candidate"
RECOMMENDED_NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class ClusterReviewItem:
    cluster_id: str
    fact_type: str
    label: str
    token_signature: list[str]
    paper_count: int
    fact_count: int
    average_confidence: float
    recommended_status: str
    review_status: str
    review_notes: str
    rationale: str
    facts: list[ClusterFactRef]


@dataclass(frozen=True)
class ClusterReviewPacket:
    generated_at: str
    paper_count: int
    fact_count: int
    mode: str
    semantic_threshold: float | None
    cluster_count: int
    review_item_count: int
    accept_candidate_count: int
    needs_review_count: int
    items: list[ClusterReviewItem]


def _recommended_status(cluster: ResearchCluster) -> str:
    if cluster.paper_count >= 2 and cluster.fact_count >= 2 and cluster.average_confidence >= 0.85:
        return RECOMMENDED_ACCEPT
    return RECOMMENDED_NEEDS_REVIEW


def _rationale(cluster: ResearchCluster, recommended_status: str) -> str:
    evidence = (
        f"{cluster.fact_count} facts across {cluster.paper_count} papers "
        f"with average confidence {cluster.average_confidence:.2f}"
    )
    if recommended_status == RECOMMENDED_ACCEPT:
        return f"Accept candidate because it has cross-paper support: {evidence}."
    return f"Needs review because support is narrow or confidence is below the accept threshold: {evidence}."


def _review_item(cluster: ResearchCluster) -> ClusterReviewItem:
    recommended = _recommended_status(cluster)
    return ClusterReviewItem(
        cluster_id=cluster.cluster_id,
        fact_type=cluster.fact_type,
        label=cluster.label,
        token_signature=cluster.token_signature,
        paper_count=cluster.paper_count,
        fact_count=cluster.fact_count,
        average_confidence=cluster.average_confidence,
        recommended_status=recommended,
        review_status=REVIEW_STATUS_PENDING,
        review_notes="",
        rationale=_rationale(cluster, recommended),
        facts=cluster.facts,
    )


def build_cluster_review_packet(
    db_path: Path,
    *,
    mode: str = "token",
    embedding_provider: EmbeddingProvider | None = None,
    semantic_threshold: float = SEMANTIC_CLUSTER_THRESHOLD,
) -> ClusterReviewPacket:
    clusters = build_research_clusters(
        db_path,
        mode=mode,
        embedding_provider=embedding_provider,
        semantic_threshold=semantic_threshold,
    )
    items = [_review_item(cluster) for cluster in clusters.clusters]
    accept_count = sum(1 for item in items if item.recommended_status == RECOMMENDED_ACCEPT)
    needs_review_count = sum(1 for item in items if item.recommended_status == RECOMMENDED_NEEDS_REVIEW)
    return ClusterReviewPacket(
        generated_at=clusters.generated_at,
        paper_count=clusters.paper_count,
        fact_count=clusters.fact_count,
        mode=clusters.mode,
        semantic_threshold=clusters.semantic_threshold,
        cluster_count=clusters.cluster_count,
        review_item_count=len(items),
        accept_candidate_count=accept_count,
        needs_review_count=needs_review_count,
        items=items,
    )


def _fact_type_title(fact_type: str) -> str:
    return fact_type.replace("_", " ").title()


def render_markdown(packet: ClusterReviewPacket) -> str:
    lines = [
        "# AIResearch Cluster Review Packet",
        "",
        f"Generated: {packet.generated_at}",
        f"Papers: {packet.paper_count}",
        f"Facts: {packet.fact_count}",
        f"Mode: {packet.mode}",
        f"Clusters: {packet.cluster_count}",
        f"Review items: {packet.review_item_count}",
        f"Accept candidates: {packet.accept_candidate_count}",
        f"Needs review: {packet.needs_review_count}",
        "",
    ]
    if packet.semantic_threshold is not None:
        lines.insert(6, f"Semantic threshold: {packet.semantic_threshold:.2f}")

    lines.extend(["## Review Items", ""])
    if not packet.items:
        lines.extend(["No cluster review items found.", ""])
    for item in packet.items:
        lines.extend(
            [
                f"### {item.label}",
                "",
                f"`{item.cluster_id}` | {_fact_type_title(item.fact_type)}",
                f"Recommended status: `{item.recommended_status}`",
                f"Review status: `{item.review_status}`",
                "Review notes: ",
                (
                    f"Papers: {item.paper_count} | Facts: {item.fact_count} | "
                    f"Average confidence: {item.average_confidence:.2f}"
                ),
                "Tokens: " + ", ".join(item.token_signature),
                f"Rationale: {item.rationale}",
                "",
            ]
        )
        for fact in item.facts:
            title = fact.paper_title
            if fact.year:
                title += f" | {fact.year}"
            lines.append(
                f"- `{fact.paper_key}` {title}: {fact.fact_name} - {fact.statement} "
                f"(confidence: {fact.confidence:.2f})"
            )
            if fact.evidence_source_path:
                lines.append(f"  Evidence source: {fact.evidence_source_path}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cluster_review_packet_to_dict(packet: ClusterReviewPacket) -> dict[str, Any]:
    return {
        "generated_at": packet.generated_at,
        "paper_count": packet.paper_count,
        "fact_count": packet.fact_count,
        "mode": packet.mode,
        "semantic_threshold": packet.semantic_threshold,
        "cluster_count": packet.cluster_count,
        "review_item_count": packet.review_item_count,
        "accept_candidate_count": packet.accept_candidate_count,
        "needs_review_count": packet.needs_review_count,
        "items": [
            {
                "cluster_id": item.cluster_id,
                "fact_type": item.fact_type,
                "label": item.label,
                "token_signature": item.token_signature,
                "paper_count": item.paper_count,
                "fact_count": item.fact_count,
                "average_confidence": item.average_confidence,
                "recommended_status": item.recommended_status,
                "review_status": item.review_status,
                "review_notes": item.review_notes,
                "rationale": item.rationale,
                "facts": [
                    {
                        "paper_key": fact.paper_key,
                        "paper_title": fact.paper_title,
                        "year": fact.year,
                        "fact_name": fact.fact_name,
                        "statement": fact.statement,
                        "confidence": fact.confidence,
                        "evidence_source_path": fact.evidence_source_path,
                    }
                    for fact in item.facts
                ],
            }
            for item in packet.items
        ],
    }


def export_cluster_review_packet(
    db_path: Path,
    out_path: Path,
    *,
    output_format: str = "markdown",
    mode: str = "token",
    embedding_provider: EmbeddingProvider | None = None,
    semantic_threshold: float = SEMANTIC_CLUSTER_THRESHOLD,
) -> ClusterReviewPacket:
    packet = build_cluster_review_packet(
        db_path,
        mode=mode,
        embedding_provider=embedding_provider,
        semantic_threshold=semantic_threshold,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(packet), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(cluster_review_packet_to_dict(packet), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported cluster review packet format: {output_format}")
    return packet

