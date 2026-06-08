from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import stable_json


EXTRACTOR_VERSION = "2026-06-08.1"
ALLOWED_FACT_TYPES = {"method", "dataset", "benchmark", "claim", "limitation"}


class FactValidationError(ValueError):
    pass


@dataclass(frozen=True)
class FactPayload:
    fact_type: str
    name: str
    statement: str
    evidence_quote: str
    evidence_artifact_type: str
    confidence: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class FactExtractionResult:
    papers_seen: int
    facts_written: int
    provenance_written: int


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def parse_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def validate_fact(raw: dict[str, Any]) -> FactPayload:
    fact_type = str(raw.get("fact_type") or "").strip()
    if fact_type not in ALLOWED_FACT_TYPES:
        raise FactValidationError(f"unsupported fact_type: {fact_type}")
    statement = str(raw.get("statement") or "").strip()
    if not statement:
        raise FactValidationError("fact statement is required")
    evidence_quote = str(raw.get("evidence_quote") or "").strip()
    if not evidence_quote:
        raise FactValidationError("evidence_quote is required")
    confidence_raw = raw.get("confidence", 0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError) as exc:
        raise FactValidationError("confidence must be numeric") from exc
    if confidence < 0 or confidence > 1:
        raise FactValidationError("confidence must be between 0 and 1")
    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise FactValidationError("metadata must be an object")
    return FactPayload(
        fact_type=fact_type,
        name=str(raw.get("name") or "").strip(),
        statement=statement,
        evidence_quote=evidence_quote,
        evidence_artifact_type=str(raw.get("evidence_artifact_type") or "").strip(),
        confidence=confidence,
        metadata=metadata,
    )


def load_fixture_provider(fixture_path: Path) -> dict[str, list[FactPayload]]:
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise FactValidationError("fixture root must be an object keyed by paper_key")
    result: dict[str, list[FactPayload]] = {}
    for paper_key, facts in raw.items():
        if not isinstance(facts, list):
            raise FactValidationError(f"facts for {paper_key} must be a list")
        result[str(paper_key)] = [validate_fact(fact) for fact in facts]
    return result


def load_target_papers(conn, *, paper_key: str | None, limit: int | None):
    sql = "select paper_key from papers"
    params: list[Any] = []
    if paper_key:
        sql += " where paper_key = ?"
        params.append(paper_key)
    sql += " order by updated_at desc, paper_key"
    if limit is not None:
        sql += " limit ?"
        params.append(limit)
    return [row["paper_key"] for row in conn.execute(sql, params).fetchall()]


def artifact_path_for(conn, paper_key: str, artifact_type: str) -> str:
    if not artifact_type:
        return ""
    row = conn.execute(
        """
        select path from paper_artifacts
        where paper_key = ? and artifact_type = ?
        order by path limit 1
        """,
        (paper_key, artifact_type),
    ).fetchone()
    return str(row["path"]) if row else ""


def clear_prior_facts(conn, *, paper_key: str, provider_name: str) -> None:
    conn.execute(
        """
        delete from research_facts
        where paper_key = ? and provider_name = ? and extractor_version = ?
        """,
        (paper_key, provider_name, EXTRACTOR_VERSION),
    )


def insert_fact(conn, *, paper_key: str, provider_name: str, fact: FactPayload, now: str) -> tuple[int, int]:
    row = conn.execute(
        """
        insert into research_facts (
            paper_key, fact_type, name, statement, confidence, metadata_json,
            provider_name, extractor_version, created_at, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(paper_key, fact_type, statement, provider_name, extractor_version) do update set
            name = excluded.name,
            confidence = excluded.confidence,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        returning id
        """,
        (
            paper_key,
            fact.fact_type,
            fact.name,
            fact.statement,
            fact.confidence,
            stable_json(fact.metadata),
            provider_name,
            EXTRACTOR_VERSION,
            now,
            now,
        ),
    ).fetchone()
    fact_id = int(row["id"])
    conn.execute(
        "delete from research_fact_provenance where fact_id = ?",
        (fact_id,),
    )
    conn.execute(
        """
        insert into research_fact_provenance (
            fact_id, evidence_quote, evidence_artifact_type,
            evidence_source_path, created_at
        ) values (?, ?, ?, ?, ?)
        """,
        (
            fact_id,
            fact.evidence_quote,
            fact.evidence_artifact_type,
            artifact_path_for(conn, paper_key, fact.evidence_artifact_type),
            now,
        ),
    )
    return 1, 1


def extract_research_facts(
    db_path: Path,
    *,
    provider_name: str,
    fixture_path: Path | None = None,
    paper_key: str | None = None,
    limit: int | None = None,
) -> FactExtractionResult:
    if provider_name != "fixture":
        raise FactValidationError(f"unsupported fact extraction provider: {provider_name}")
    if fixture_path is None:
        raise FactValidationError("fixture_path is required for fixture provider")
    provider_payload = load_fixture_provider(fixture_path)
    init_db(db_path)
    started_at = utc_now()
    with connect(db_path) as conn:
        run = conn.execute(
            """
            insert into fact_extraction_runs (
                provider_name, extractor_version, fixture_path, paper_key,
                limit_count, started_at, status
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (provider_name, EXTRACTOR_VERSION, str(fixture_path), paper_key, limit, started_at, "running"),
        )
        run_id = run.lastrowid
        try:
            target_papers = load_target_papers(conn, paper_key=paper_key, limit=limit)
            facts_written = 0
            provenance_written = 0
            now = utc_now()
            for target_paper_key in target_papers:
                facts = provider_payload.get(target_paper_key, [])
                clear_prior_facts(conn, paper_key=target_paper_key, provider_name=provider_name)
                for fact in facts:
                    fact_count, provenance_count = insert_fact(
                        conn,
                        paper_key=target_paper_key,
                        provider_name=provider_name,
                        fact=fact,
                        now=now,
                    )
                    facts_written += fact_count
                    provenance_written += provenance_count
            conn.execute(
                """
                update fact_extraction_runs set
                    papers_seen = ?, facts_written = ?, provenance_written = ?,
                    finished_at = ?, status = ?
                where id = ?
                """,
                (len(target_papers), facts_written, provenance_written, utc_now(), "success", run_id),
            )
            conn.commit()
            return FactExtractionResult(len(target_papers), facts_written, provenance_written)
        except Exception as exc:
            conn.execute(
                "update fact_extraction_runs set finished_at = ?, status = ?, error = ? where id = ?",
                (utc_now(), "failed", str(exc), run_id),
            )
            conn.commit()
            raise


def list_research_facts(
    db_path: Path,
    *,
    paper_key: str | None = None,
    fact_type: str | None = None,
    limit: int = 20,
):
    init_db(db_path)
    sql = """
        select f.*, p.evidence_quote, p.evidence_artifact_type, p.evidence_source_path
        from research_facts f
        left join research_fact_provenance p on p.fact_id = f.id
    """
    clauses = []
    params: list[Any] = []
    if paper_key:
        clauses.append("f.paper_key = ?")
        params.append(paper_key)
    if fact_type:
        clauses.append("f.fact_type = ?")
        params.append(fact_type)
    if clauses:
        sql += " where " + " and ".join(clauses)
    sql += " order by f.paper_key, f.fact_type, f.id limit ?"
    params.append(limit)
    with connect(db_path) as conn:
        return conn.execute(sql, params).fetchall()


def export_research_facts(db_path: Path, out_path: Path) -> int:
    rows = list_research_facts(db_path, limit=1_000_000)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {
                "paper_key": row["paper_key"],
                "fact_type": row["fact_type"],
                "name": row["name"],
                "statement": row["statement"],
                "confidence": row["confidence"],
                "metadata": parse_json(row["metadata_json"], {}),
                "provider_name": row["provider_name"],
                "extractor_version": row["extractor_version"],
                "evidence_quote": row["evidence_quote"],
                "evidence_artifact_type": row["evidence_artifact_type"],
                "evidence_source_path": row["evidence_source_path"],
            }
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)
