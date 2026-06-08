from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import utc_now


ARXIV_RE = re.compile(r"(?:arxiv:|arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s\"'<>]+)", re.I)


@dataclass(frozen=True)
class CanonicalMaterializationResult:
    candidates_seen: int
    canonical_count: int
    links_count: int
    skipped_count: int


ALLOWED_STATUSES = {"candidate", "selected", "rejected"}


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalize_title(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(text.split())


def clean_doi(value: str) -> str:
    doi = value.strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = doi.rstrip(".,);]")
    return doi


def extract_arxiv_id(*values: str) -> str:
    for value in values:
        match = ARXIV_RE.search(value or "")
        if match:
            return match.group(1).lower()
    return ""


def extract_doi(*values: str) -> str:
    for value in values:
        match = DOI_RE.search(value or "")
        if match:
            return clean_doi(match.group(1))
        cleaned = clean_doi(value or "")
        if cleaned.startswith("10.") and "/" in cleaned:
            return cleaned
    return ""


def canonical_key_for_candidate(row: dict[str, Any]) -> str:
    source = str(row.get("source") or "").lower()
    source_id = str(row.get("source_id") or "")
    url = str(row.get("url") or "")
    title = str(row.get("title") or "")
    abstract = str(row.get("abstract") or "")

    arxiv_id = extract_arxiv_id(source_id, url, title, abstract)
    if arxiv_id:
        return f"arxiv:{arxiv_id}"

    doi = extract_doi(source_id, url)
    if doi:
        return f"doi:{doi}"

    if source == "semantic_scholar" and source_id:
        return f"semantic_scholar:{source_id.lower()}"

    if source == "openalex" and source_id:
        openalex_id = source_id.rstrip("/").rsplit("/", 1)[-1].lower()
        return f"openalex:{openalex_id}"

    normalized = normalize_title(title)
    year = row.get("year") or ""
    if normalized:
        return f"title_year:{normalized}:{year}"
    return ""


def best_identifier(row: dict[str, Any]) -> str:
    if row.get("url"):
        return str(row["url"])
    key = str(row.get("canonical_key") or "")
    if key.startswith("arxiv:"):
        return "https://arxiv.org/abs/" + key.split(":", 1)[1]
    return key


def materialize_candidate_papers(db_path: Path) -> CanonicalMaterializationResult:
    init_db(db_path)
    now = utc_now()
    with connect(db_path) as conn:
        existing_status = {
            row["canonical_key"]: row["status"]
            for row in conn.execute("select canonical_key, status from candidate_papers")
        }
        rows = [
            dict(row)
            for row in conn.execute(
                """
                select *
                from research_candidates
                where status in ('candidate', 'selected')
                order by score desc, published_date desc, id asc
                """
            )
        ]

        grouped: dict[str, list[dict[str, Any]]] = {}
        skipped = 0
        for row in rows:
            key = canonical_key_for_candidate(row)
            if not key:
                skipped += 1
                continue
            row["canonical_key"] = key
            grouped.setdefault(key, []).append(row)

        conn.execute("delete from candidate_papers")
        links_count = 0
        for key, group in grouped.items():
            best = sorted(
                group,
                key=lambda item: (
                    float(item.get("score") or 0),
                    str(item.get("published_date") or ""),
                    -int(item.get("id") or 0),
                ),
                reverse=True,
            )[0]
            profiles = sorted({str(item["profile_name"]) for item in group})
            sources = sorted({str(item["source"]) for item in group})
            source_urls = sorted({str(item["url"]) for item in group if item.get("url")})
            candidate_ids = sorted(int(item["id"]) for item in group)
            conn.execute(
                """
                insert into candidate_papers (
                    canonical_key, title, url, venue, published_date, year, abstract,
                    best_score, profiles_json, sources_json, source_urls_json,
                    candidate_ids_json, status, created_at, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    best["title"],
                    best["url"],
                    best["venue"],
                    best["published_date"],
                    best["year"],
                    best["abstract"],
                    best["score"],
                    stable_json(profiles),
                    stable_json(sources),
                    stable_json(source_urls),
                    stable_json(candidate_ids),
                    existing_status.get(key, "candidate"),
                    now,
                    now,
                ),
            )
            for item in group:
                conn.execute(
                    """
                    insert into candidate_paper_links (
                        canonical_key, research_candidate_id, profile_name,
                        source, score, created_at
                    )
                    values (?, ?, ?, ?, ?, ?)
                    """,
                    (key, item["id"], item["profile_name"], item["source"], item["score"], now),
                )
                links_count += 1
        conn.commit()

    return CanonicalMaterializationResult(
        candidates_seen=len(rows),
        canonical_count=len(grouped),
        links_count=links_count,
        skipped_count=skipped,
    )


def list_canonical_candidates(db_path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select *
            from candidate_papers
            where status in ('candidate', 'selected')
            order by best_score desc, published_date desc, canonical_key asc
            limit ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def validate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in ALLOWED_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_STATUSES))
        raise ValueError(f"invalid canonical candidate status: {status}; expected one of: {allowed}")
    return normalized


def set_canonical_status(db_path: Path, canonical_key: str, status: str) -> bool:
    init_db(db_path)
    normalized = validate_status(status)
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            update candidate_papers
            set status = ?, updated_at = ?
            where canonical_key = ?
            """,
            (normalized, utc_now(), canonical_key),
        )
        conn.commit()
    return cursor.rowcount > 0


def select_top_canonical_candidates(db_path: Path, limit: int, min_score: float | None = None) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    init_db(db_path)
    params: list[Any] = []
    score_filter = ""
    if min_score is not None:
        score_filter = "and best_score >= ?"
        params.append(min_score)
    params.append(limit)
    with connect(db_path) as conn:
        rows = conn.execute(
            f"""
            select canonical_key
            from candidate_papers
            where status = 'candidate'
            {score_filter}
            order by best_score desc, published_date desc, canonical_key asc
            limit ?
            """,
            params,
        ).fetchall()
        keys = [row["canonical_key"] for row in rows]
        now = utc_now()
        for key in keys:
            conn.execute(
                """
                update candidate_papers
                set status = 'selected', updated_at = ?
                where canonical_key = ?
                """,
                (now, key),
            )
        conn.commit()
    return len(keys)


def list_approved_candidates(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select *
            from candidate_papers
            where status = 'selected'
            order by best_score desc, published_date desc, canonical_key asc
            """
        ).fetchall()
    return [dict(row) for row in rows]


def export_approved_candidates(db_path: Path, out_path: Path) -> int:
    rows = list_approved_candidates(db_path)
    lines = [best_identifier(row) for row in rows if best_identifier(row)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def export_canonical_candidates(db_path: Path, limit: int, out_path: Path) -> int:
    rows = list_canonical_candidates(db_path, limit)
    lines = [best_identifier(row) for row in rows if best_identifier(row)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)
