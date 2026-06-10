from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.research_review_summary import VALID_REVIEW_STATUSES


class ClusterReviewEditError(ValueError):
    pass


@dataclass(frozen=True)
class ClusterReviewEditResult:
    cluster_id: str
    previous_status: str
    new_status: str
    notes: str
    out_path: str


def _load_packet(review_packet_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(review_packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ClusterReviewEditError(f"invalid review packet JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ClusterReviewEditError("review packet must be a JSON object")
    items = payload.get("items")
    if not isinstance(items, list):
        raise ClusterReviewEditError("review packet.items must be a list")
    return payload


def set_cluster_review_status(
    review_packet_path: Path,
    out_path: Path,
    *,
    cluster_id: str,
    status: str,
    notes: str | None = None,
) -> ClusterReviewEditResult:
    if status not in VALID_REVIEW_STATUSES:
        valid = ", ".join(sorted(VALID_REVIEW_STATUSES))
        raise ClusterReviewEditError(f"unsupported review_status={status!r}; expected one of: {valid}")

    payload = _load_packet(review_packet_path)
    matched_item: dict[str, Any] | None = None
    for raw_item in payload["items"]:
        if not isinstance(raw_item, dict):
            raise ClusterReviewEditError("review packet.items entries must be JSON objects")
        if raw_item.get("cluster_id") == cluster_id:
            matched_item = raw_item
            break

    if matched_item is None:
        raise ClusterReviewEditError(f"cluster_id not found: {cluster_id}")

    previous_status = matched_item.get("review_status")
    if not isinstance(previous_status, str):
        raise ClusterReviewEditError(f"item.review_status must be a string for cluster_id={cluster_id}")

    matched_item["review_status"] = status
    if notes is not None:
        matched_item["review_notes"] = notes
    current_notes = matched_item.get("review_notes", "")
    if not isinstance(current_notes, str):
        raise ClusterReviewEditError(f"item.review_notes must be a string for cluster_id={cluster_id}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ClusterReviewEditResult(
        cluster_id=cluster_id,
        previous_status=previous_status,
        new_status=status,
        notes=current_notes,
        out_path=str(out_path),
    )

