from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import utc_now
from airesearch.profiles import ResearchProfile


@dataclass(frozen=True)
class CandidatePaper:
    source: str
    source_id: str
    title: str
    url: str = ""
    authors: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    venue: str = ""
    published_date: str = ""
    year: int | None = None
    abstract: str = ""
    artifact_links: list[str] = field(default_factory=list)


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def parse_date(value: str, year: int | None) -> date | None:
    if value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    if year:
        return date(year, 1, 1)
    return None


def text_blob(candidate: CandidatePaper) -> str:
    parts = [
        candidate.title,
        candidate.abstract,
        candidate.venue,
        candidate.source,
        " ".join(candidate.authors),
        " ".join(candidate.organizations),
        " ".join(candidate.artifact_links),
    ]
    return " ".join(parts).lower()


def hit_count(needles: list[str], haystack: str) -> int:
    return sum(1 for needle in needles if needle.lower() in haystack)


def matched_terms(needles: list[str], haystack: str) -> list[str]:
    return [needle for needle in needles if needle.lower() in haystack]


def recency_score(profile: ResearchProfile, candidate: CandidatePaper, reasons: list[str]) -> float:
    published = parse_date(candidate.published_date, candidate.year)
    if published is None:
        return 0.1
    primary = date.fromisoformat(profile.primary_since)
    exception = date.fromisoformat(profile.exception_since)
    if published >= primary:
        if published.year >= 2026:
            reasons.append("recency:2026_or_newer")
            return 1.0
        reasons.append("recency:primary_window")
        return 0.85
    if published >= exception:
        reasons.append("recency:exception_window")
        return 0.45
    reasons.append("recency:background_only")
    return 0.0


def backing_score(profile: ResearchProfile, candidate: CandidatePaper, blob: str, reasons: list[str]) -> float:
    org_hits = matched_terms(profile.preferred_organizations, blob)
    scholar_hits = matched_terms(profile.preferred_scholars, blob)
    score = min(1.0, 0.25 * len(org_hits) + 0.35 * len(scholar_hits))
    if org_hits:
        reasons.append("backing:organizations=" + ",".join(org_hits[:4]))
    if scholar_hits:
        reasons.append("backing:scholars=" + ",".join(scholar_hits[:4]))
    return score


def venue_score(profile: ResearchProfile, candidate: CandidatePaper, blob: str, reasons: list[str]) -> float:
    hits = matched_terms(profile.preferred_venues, blob)
    if hits:
        reasons.append("venue:" + ",".join(hits[:3]))
        return 1.0
    if candidate.source.lower() in {"arxiv", "openreview", "semantic_scholar", "openalex", "google_scholar"}:
        reasons.append("venue:trusted_source=" + candidate.source)
        return 0.35
    return 0.0


def topic_score(profile: ResearchProfile, blob: str, reasons: list[str]) -> float:
    hits = matched_terms(profile.keywords, blob)
    if hits:
        reasons.append("topic:" + ",".join(hits[:5]))
    return min(1.0, len(hits) / 3)


def artifact_score(candidate: CandidatePaper, blob: str, reasons: list[str]) -> float:
    artifact_words = ["github", "code", "project", "model", "dataset", "huggingface", "demo"]
    hits = matched_terms(artifact_words, blob)
    if candidate.artifact_links:
        reasons.append("artifact:links")
        return 1.0
    if hits:
        reasons.append("artifact:" + ",".join(hits[:3]))
        return 0.6
    if candidate.url:
        reasons.append("artifact:url")
        return 0.2
    return 0.0


def is_candidate_allowed(profile: ResearchProfile, candidate: CandidatePaper) -> bool:
    published = parse_date(candidate.published_date, candidate.year)
    if published is None:
        return False
    if published > date.today():
        return False
    primary = date.fromisoformat(profile.primary_since)
    exception = date.fromisoformat(profile.exception_since)
    blob = text_blob(candidate)
    topic_signal = hit_count(profile.keywords, blob) > 0 or hit_count(profile.exception_keywords, blob) > 0
    backing_signal = (
        hit_count(profile.preferred_organizations, blob) > 0
        or hit_count(profile.preferred_scholars, blob) > 0
        or hit_count(profile.preferred_venues, blob) > 0
    )
    if published >= primary:
        return topic_signal
    if published < exception:
        return False
    return topic_signal and backing_signal


def score_candidate(profile: ResearchProfile, candidate: CandidatePaper) -> tuple[float, list[str]]:
    reasons: list[str] = []
    blob = text_blob(candidate)
    if not is_candidate_allowed(profile, candidate):
        reasons.append("filtered:outside_recency_policy")
        return 0.0, reasons
    score = (
        recency_score(profile, candidate, reasons) * 0.35
        + backing_score(profile, candidate, blob, reasons) * 0.25
        + venue_score(profile, candidate, blob, reasons) * 0.20
        + topic_score(profile, blob, reasons) * 0.15
        + artifact_score(candidate, blob, reasons) * 0.05
    )
    return round(score, 4), reasons


def upsert_candidate(
    db_path: Path,
    *,
    profile_name: str,
    candidate: CandidatePaper,
    score: float,
    reasons: list[str],
    status: str = "candidate",
) -> None:
    init_db(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into research_candidates (
                profile_name, source, source_id, title, url, authors_json,
                organizations_json, venue, published_date, year, abstract,
                score, score_reasons_json, status, created_at, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(profile_name, source, source_id) do update set
                title = excluded.title,
                url = excluded.url,
                authors_json = excluded.authors_json,
                organizations_json = excluded.organizations_json,
                venue = excluded.venue,
                published_date = excluded.published_date,
                year = excluded.year,
                abstract = excluded.abstract,
                score = excluded.score,
                score_reasons_json = excluded.score_reasons_json,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                profile_name,
                candidate.source,
                candidate.source_id,
                candidate.title,
                candidate.url,
                stable_json(candidate.authors),
                stable_json(candidate.organizations),
                candidate.venue,
                candidate.published_date,
                candidate.year,
                candidate.abstract,
                score,
                stable_json(reasons),
                status,
                now,
                now,
            ),
        )
        conn.commit()


def list_candidates(db_path: Path, profile_name: str, limit: int = 20) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select * from research_candidates
            where profile_name = ? and status in ('candidate', 'selected')
            order by score desc, published_date desc, id asc
            limit ?
            """,
            (profile_name, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def candidate_identifier(row: dict[str, Any]) -> str:
    if row.get("url"):
        return str(row["url"])
    source = str(row.get("source") or "")
    source_id = str(row.get("source_id") or "")
    if source == "arxiv" and source_id:
        return source_id
    return source_id or str(row.get("title") or "")


def export_candidates(db_path: Path, profile_name: str, limit: int, out_path: Path) -> int:
    rows = list_candidates(db_path, profile_name, limit)
    lines = [candidate_identifier(row) for row in rows if candidate_identifier(row)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)
