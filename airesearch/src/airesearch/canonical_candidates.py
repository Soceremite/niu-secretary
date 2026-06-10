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


@dataclass(frozen=True)
class CandidateReviewResult:
    total_count: int
    selected_count: int
    already_in_database_count: int
    manually_rejected_count: int
    below_min_score_count: int
    not_in_top_limit_count: int
    missing_identifier_count: int
    json_path: Path
    markdown_path: Path | None = None


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


def _json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def canonical_keys_for_existing_papers(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()
    keys: set[str] = set()
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select paper_key, title, year, ids_json, meta_json
            from papers
            """
        ).fetchall()
        source_rows = conn.execute(
            """
            select ps.source_type, ps.source_value, p.year
            from paper_sources ps
            left join papers p on p.paper_key = ps.paper_key
            """
        ).fetchall()

    for row in rows:
        ids = _json_object(row["ids_json"])
        meta = _json_object(row["meta_json"])
        title = str(row["title"] or meta.get("title") or "")
        year = row["year"] or meta.get("year") or ""
        source_values = [
            str(row["paper_key"] or ""),
            str(ids.get("arxiv_id") or ""),
            str(ids.get("doi") or ""),
            str(ids.get("s2_id") or ""),
            str(ids.get("url") or ""),
            str(meta.get("arxiv_id") or ""),
            str(meta.get("doi") or ""),
            str(meta.get("s2_id") or ""),
            str(meta.get("url") or ""),
        ]

        arxiv_id = extract_arxiv_id(*source_values)
        if arxiv_id:
            keys.add(f"arxiv:{arxiv_id}")
        doi = extract_doi(*source_values)
        if doi:
            keys.add(f"doi:{doi}")
        s2_id = ids.get("s2_id") or meta.get("s2_id")
        if s2_id:
            keys.add(f"semantic_scholar:{str(s2_id).lower()}")
        openalex_id = ids.get("openalex_id") or meta.get("openalex_id") or meta.get("openalex")
        if openalex_id:
            keys.add(f"openalex:{str(openalex_id).rstrip('/').rsplit('/', 1)[-1].lower()}")
        normalized_title = normalize_title(title)
        if normalized_title:
            year_text = str(year or "")
            keys.add(f"title_year:{normalized_title}:{year_text}")

    for source_row in source_rows:
        source_type = str(source_row["source_type"] or "").lower()
        source_value = str(source_row["source_value"] or "")
        arxiv_id = extract_arxiv_id(source_value)
        if arxiv_id:
            keys.add(f"arxiv:{arxiv_id}")
        doi = extract_doi(source_value)
        if doi:
            keys.add(f"doi:{doi}")
        if source_type == "s2_id" and source_value:
            keys.add(f"semantic_scholar:{source_value.lower()}")
        if source_type in {"openalex", "openalex_id"} and source_value:
            keys.add(f"openalex:{source_value.rstrip('/').rsplit('/', 1)[-1].lower()}")
        if source_type == "title" and source_value:
            normalized_title = normalize_title(source_value)
            year_text = str(source_row["year"] or "")
            keys.add(f"title_year:{normalized_title}:{year_text}")

    return keys


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
    existing_keys = canonical_keys_for_existing_papers(db_path)
    params: list[Any] = []
    score_filter = ""
    if min_score is not None:
        score_filter = "and best_score >= ?"
        params.append(min_score)
    with connect(db_path) as conn:
        rows = conn.execute(
            f"""
            select canonical_key
            from candidate_papers
            where status = 'candidate'
            {score_filter}
            order by best_score desc, published_date desc, canonical_key asc
            """,
            params,
        ).fetchall()
        keys = [
            row["canonical_key"]
            for row in rows
            if row["canonical_key"] not in existing_keys
        ][:limit]
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


def _decode_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _candidate_review_reason(
    row: dict[str, Any],
    *,
    existing_keys: set[str],
    min_score: float | None,
) -> str:
    identifier = best_identifier(row)
    if not identifier:
        return "missing_identifier"
    status = str(row.get("status") or "")
    canonical_key = str(row.get("canonical_key") or "")
    if status == "selected":
        return "selected"
    if canonical_key in existing_keys:
        return "already_in_database"
    if status == "rejected":
        return "manually_rejected"
    score = float(row.get("best_score") or 0)
    if min_score is not None and score < min_score:
        return "below_min_score"
    return "not_in_top_limit"


def build_candidate_review(
    db_path: Path,
    *,
    min_score: float | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    init_db(db_path)
    existing_keys = canonical_keys_for_existing_papers(db_path)
    with connect(db_path) as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                select *
                from candidate_papers
                order by best_score desc, published_date desc, canonical_key asc
                """
            )
        ]

    items: list[dict[str, Any]] = []
    counts = {
        "selected": 0,
        "already_in_database": 0,
        "manually_rejected": 0,
        "below_min_score": 0,
        "not_in_top_limit": 0,
        "missing_identifier": 0,
    }
    for index, row in enumerate(rows, start=1):
        reason = _candidate_review_reason(row, existing_keys=existing_keys, min_score=min_score)
        counts[reason] += 1
        items.append(
            {
                "rank": index,
                "canonical_key": row["canonical_key"],
                "title": row["title"],
                "identifier": best_identifier(row),
                "status": row["status"],
                "review_reason": reason,
                "best_score": row["best_score"],
                "published_date": row["published_date"],
                "year": row["year"],
                "profiles": _decode_list(row.get("profiles_json")),
                "sources": _decode_list(row.get("sources_json")),
                "source_urls": _decode_list(row.get("source_urls_json")),
            }
        )

    return {
        "generated_at": utc_now(),
        "selection": {
            "limit": limit,
            "min_score": min_score,
            "selected_count": counts["selected"],
        },
        "summary": {
            "total_count": len(items),
            **counts,
        },
        "items": items,
    }


def _candidate_review_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    selection = payload["selection"]
    lines = [
        "# Candidate Review",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- selection_limit: {selection['limit']}",
        f"- min_score: {selection['min_score']}",
        f"- total: {summary['total_count']}",
        f"- selected: {summary['selected']}",
        f"- already_in_database: {summary['already_in_database']}",
        f"- manually_rejected: {summary['manually_rejected']}",
        f"- below_min_score: {summary['below_min_score']}",
        f"- not_in_top_limit: {summary['not_in_top_limit']}",
        f"- missing_identifier: {summary['missing_identifier']}",
        "",
        "| Rank | Reason | Score | Status | Title | Identifier |",
        "| ---: | --- | ---: | --- | --- | --- |",
    ]
    for item in payload["items"]:
        title = str(item["title"] or "").replace("|", "\\|")
        identifier = str(item["identifier"] or "").replace("|", "\\|")
        lines.append(
            "| {rank} | {reason} | {score:.3f} | {status} | {title} | {identifier} |".format(
                rank=item["rank"],
                reason=item["review_reason"],
                score=float(item["best_score"] or 0),
                status=item["status"],
                title=title,
                identifier=identifier,
            )
        )
    return "\n".join(lines) + "\n"


def export_candidate_review(
    db_path: Path,
    json_path: Path,
    *,
    markdown_path: Path | None = None,
    min_score: float | None = None,
    limit: int | None = None,
) -> CandidateReviewResult:
    payload = build_candidate_review(db_path, min_score=min_score, limit=limit)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if markdown_path is not None:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_candidate_review_markdown(payload), encoding="utf-8")
    summary = payload["summary"]
    return CandidateReviewResult(
        total_count=summary["total_count"],
        selected_count=summary["selected"],
        already_in_database_count=summary["already_in_database"],
        manually_rejected_count=summary["manually_rejected"],
        below_min_score_count=summary["below_min_score"],
        not_in_top_limit_count=summary["not_in_top_limit"],
        missing_identifier_count=summary["missing_identifier"],
        json_path=json_path,
        markdown_path=markdown_path,
    )
