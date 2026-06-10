from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_ACCEPTED = "accepted"
REVIEW_STATUS_REJECTED = "rejected"
REVIEW_STATUS_NEEDS_REVISION = "needs_revision"
VALID_REVIEW_STATUSES = {
    REVIEW_STATUS_PENDING,
    REVIEW_STATUS_ACCEPTED,
    REVIEW_STATUS_REJECTED,
    REVIEW_STATUS_NEEDS_REVISION,
}


class ClusterReviewSummaryError(ValueError):
    pass


@dataclass(frozen=True)
class ReviewedFactRef:
    paper_key: str
    paper_title: str
    year: int | None
    fact_name: str
    statement: str
    confidence: float
    evidence_source_path: str | None


@dataclass(frozen=True)
class ReviewedClusterItem:
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
    facts: list[ReviewedFactRef]


@dataclass(frozen=True)
class ReviewedClusterSummary:
    source_generated_at: str
    source_mode: str
    source_semantic_threshold: float | None
    source_paper_count: int
    source_fact_count: int
    review_item_count: int
    status_counts: dict[str, int]
    accepted_count: int
    accepted_fact_count: int
    accepted_paper_count: int
    accepted_items: list[ReviewedClusterItem]


def _require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ClusterReviewSummaryError(f"{context} must be a JSON object")
    return value


def _require_string(payload: dict[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ClusterReviewSummaryError(f"{context}.{key} must be a string")
    return value


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ClusterReviewSummaryError(f"fact.{key} must be a string or null")
    return value


def _number(payload: dict[str, Any], key: str, context: str) -> int | float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ClusterReviewSummaryError(f"{context}.{key} must be numeric")
    return value


def _reviewed_fact(payload: Any) -> ReviewedFactRef:
    fact = _require_mapping(payload, "fact")
    year = fact.get("year")
    if year is not None and not isinstance(year, int):
        raise ClusterReviewSummaryError("fact.year must be an integer or null")
    return ReviewedFactRef(
        paper_key=_require_string(fact, "paper_key", "fact"),
        paper_title=_require_string(fact, "paper_title", "fact"),
        year=year,
        fact_name=_require_string(fact, "fact_name", "fact"),
        statement=_require_string(fact, "statement", "fact"),
        confidence=float(_number(fact, "confidence", "fact")),
        evidence_source_path=_optional_string(fact, "evidence_source_path"),
    )


def _reviewed_item(payload: dict[str, Any]) -> ReviewedClusterItem:
    token_signature = payload.get("token_signature", [])
    if not isinstance(token_signature, list) or any(not isinstance(token, str) for token in token_signature):
        raise ClusterReviewSummaryError("item.token_signature must be a list of strings")
    facts_payload = payload.get("facts", [])
    if not isinstance(facts_payload, list):
        raise ClusterReviewSummaryError("item.facts must be a list")
    return ReviewedClusterItem(
        cluster_id=_require_string(payload, "cluster_id", "item"),
        fact_type=_require_string(payload, "fact_type", "item"),
        label=_require_string(payload, "label", "item"),
        token_signature=list(token_signature),
        paper_count=int(_number(payload, "paper_count", "item")),
        fact_count=int(_number(payload, "fact_count", "item")),
        average_confidence=float(_number(payload, "average_confidence", "item")),
        recommended_status=_require_string(payload, "recommended_status", "item"),
        review_status=_require_string(payload, "review_status", "item"),
        review_notes=_require_string(payload, "review_notes", "item"),
        rationale=_require_string(payload, "rationale", "item"),
        facts=[_reviewed_fact(fact) for fact in facts_payload],
    )


def _load_packet(review_packet_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(review_packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ClusterReviewSummaryError(f"invalid review packet JSON: {exc}") from exc
    return _require_mapping(payload, "review packet")


def build_reviewed_cluster_summary(review_packet_path: Path) -> ReviewedClusterSummary:
    packet = _load_packet(review_packet_path)
    items = packet.get("items")
    if not isinstance(items, list):
        raise ClusterReviewSummaryError("review packet.items must be a list")

    status_counts = Counter({status: 0 for status in VALID_REVIEW_STATUSES})
    accepted_items: list[ReviewedClusterItem] = []
    for index, raw_item in enumerate(items):
        item_payload = _require_mapping(raw_item, f"review packet.items[{index}]")
        item = _reviewed_item(item_payload)
        review_status = item.review_status
        if review_status not in VALID_REVIEW_STATUSES:
            valid = ", ".join(sorted(VALID_REVIEW_STATUSES))
            raise ClusterReviewSummaryError(f"unsupported review_status={review_status!r}; expected one of: {valid}")
        status_counts[review_status] += 1
        if review_status == REVIEW_STATUS_ACCEPTED:
            accepted_items.append(item)

    accepted_papers = {fact.paper_key for item in accepted_items for fact in item.facts}
    semantic_threshold = packet.get("semantic_threshold")
    if semantic_threshold is not None and not isinstance(semantic_threshold, (int, float)):
        raise ClusterReviewSummaryError("review packet.semantic_threshold must be numeric or null")

    return ReviewedClusterSummary(
        source_generated_at=str(packet.get("generated_at", "")),
        source_mode=str(packet.get("mode", "")),
        source_semantic_threshold=float(semantic_threshold) if semantic_threshold is not None else None,
        source_paper_count=int(packet.get("paper_count", 0)),
        source_fact_count=int(packet.get("fact_count", 0)),
        review_item_count=len(items),
        status_counts=dict(sorted(status_counts.items())),
        accepted_count=len(accepted_items),
        accepted_fact_count=sum(item.fact_count for item in accepted_items),
        accepted_paper_count=len(accepted_papers),
        accepted_items=accepted_items,
    )


def _fact_type_title(fact_type: str) -> str:
    return fact_type.replace("_", " ").title()


def render_markdown(summary: ReviewedClusterSummary) -> str:
    lines = [
        "# AIResearch Reviewed Cluster Summary",
        "",
        f"Source generated: {summary.source_generated_at}",
        f"Source mode: {summary.source_mode}",
        f"Source papers: {summary.source_paper_count}",
        f"Source facts: {summary.source_fact_count}",
        f"Review items: {summary.review_item_count}",
        f"Accepted clusters: {summary.accepted_count}",
        f"Accepted facts: {summary.accepted_fact_count}",
        f"Accepted papers: {summary.accepted_paper_count}",
        "",
        "## Status Counts",
        "",
    ]
    if summary.source_semantic_threshold is not None:
        lines.insert(4, f"Source semantic threshold: {float(summary.source_semantic_threshold):.2f}")
    for status, count in summary.status_counts.items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Accepted Clusters", ""])
    if not summary.accepted_items:
        lines.extend(["No accepted clusters found.", ""])
    for item in summary.accepted_items:
        lines.extend(
            [
                f"### {item.label}",
                "",
                f"`{item.cluster_id}` | {_fact_type_title(item.fact_type)}",
                f"Review notes: {item.review_notes}",
                (
                    f"Papers: {item.paper_count} | Facts: {item.fact_count} | "
                    f"Average confidence: {item.average_confidence:.2f}"
                ),
                "Tokens: " + ", ".join(item.token_signature),
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


def reviewed_cluster_summary_to_dict(summary: ReviewedClusterSummary) -> dict[str, Any]:
    return {
        "source_generated_at": summary.source_generated_at,
        "source_mode": summary.source_mode,
        "source_semantic_threshold": summary.source_semantic_threshold,
        "source_paper_count": summary.source_paper_count,
        "source_fact_count": summary.source_fact_count,
        "review_item_count": summary.review_item_count,
        "status_counts": summary.status_counts,
        "accepted_count": summary.accepted_count,
        "accepted_fact_count": summary.accepted_fact_count,
        "accepted_paper_count": summary.accepted_paper_count,
        "accepted_items": [
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
            for item in summary.accepted_items
        ],
    }


def export_reviewed_cluster_summary(
    review_packet_path: Path,
    out_path: Path,
    *,
    output_format: str = "markdown",
) -> ReviewedClusterSummary:
    summary = build_reviewed_cluster_summary(review_packet_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        out_path.write_text(render_markdown(summary), encoding="utf-8")
    elif output_format == "json":
        payload = json.dumps(reviewed_cluster_summary_to_dict(summary), ensure_ascii=False, indent=2, sort_keys=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        raise ValueError(f"unsupported reviewed cluster summary format: {output_format}")
    return summary
