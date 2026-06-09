from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import stable_json


EXTRACTOR_VERSION = "2026-06-08.1"
ALLOWED_FACT_TYPES = {"method", "dataset", "benchmark", "claim", "limitation"}
TEXT_ARTIFACT_TYPES = ("summary", "tldr", "notes", "source_tex")
FACT_EXTRACTION_SYSTEM_PROMPT = """Extract grounded research facts from the provided evidence pack.
Return only JSON with a top-level facts array. Each fact must use one of these
fact_type values: method, dataset, benchmark, claim, limitation. Each fact must
include statement, evidence_quote copied from the evidence pack,
evidence_artifact_type, confidence between 0 and 1, and metadata object.
Do not invent facts that are not supported by the evidence pack."""


class FactValidationError(ValueError):
    pass


@dataclass(frozen=True)
class EvidencePack:
    paper_key: str
    evidence_hash: str
    prompt_text: str
    prompt_json: dict[str, Any]
    artifact_texts: dict[str, str]


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
    cache_hits: int = 0
    llm_calls: int = 0
    dry_runs: int = 0


class OpenAICompatibleClient:
    def complete_json(self, *, model: str, base_url: str | None, api_key: str, prompt: str) -> dict[str, Any]:
        import urllib.error
        import urllib.request

        endpoint = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        body = stable_json({
            "model": model,
            "messages": [
                {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise FactValidationError(f"provider HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise FactValidationError(f"provider request failed: {exc}") from exc
        try:
            content = payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise FactValidationError(f"provider returned invalid JSON content: {exc}") from exc


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


def validate_provider_response(raw: dict[str, Any]) -> list[FactPayload]:
    if not isinstance(raw, dict):
        raise FactValidationError("provider response root must be an object")
    facts = raw.get("facts")
    if not isinstance(facts, list):
        raise FactValidationError("provider response facts must be a list")
    return [validate_fact(fact) for fact in facts]


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


def read_artifact_text(path_value: str, *, max_chars: int) -> str:
    path = Path(path_value)
    if not path.exists() or max_chars <= 0:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def build_evidence_pack(conn, paper_key: str, *, max_input_chars: int) -> EvidencePack:
    paper = conn.execute("select * from papers where paper_key = ?", (paper_key,)).fetchone()
    if paper is None:
        raise FactValidationError(f"paper not found: {paper_key}")
    remaining = max_input_chars
    meta = parse_json(paper["meta_json"], {})
    ids = parse_json(paper["ids_json"], {})
    authors = parse_json(paper["authors_json"], [])
    sections: list[str] = [
        f"paper_key: {paper_key}",
        f"title: {paper['title'] or ''}",
        f"authors: {', '.join(str(author) for author in authors)}",
        f"year: {paper['year'] or ''}",
        f"venue: {paper['venue'] or ''}",
        f"ids: {stable_json(ids)}",
        f"metadata: {stable_json(meta)}",
    ]
    remaining -= sum(len(section) for section in sections)
    artifact_texts: dict[str, str] = {}
    artifacts = conn.execute(
        """
        select artifact_type, path from paper_artifacts
        where paper_key = ? and artifact_type in ('summary', 'tldr', 'notes', 'source_tex')
        order by case artifact_type
            when 'summary' then 1
            when 'tldr' then 2
            when 'notes' then 3
            when 'source_tex' then 4
            else 5
        end, path
        """,
        (paper_key,),
    ).fetchall()
    for artifact in artifacts:
        budget = max(0, remaining)
        text = read_artifact_text(artifact["path"], max_chars=budget)
        if not text:
            continue
        artifact_texts[artifact["artifact_type"]] = text
        sections.append(f"artifact:{artifact['artifact_type']}\n{text}")
        remaining -= len(text)
        if remaining <= 0:
            break
    prompt_json = {
        "paper_key": paper_key,
        "title": paper["title"] or "",
        "authors": authors,
        "year": paper["year"],
        "venue": paper["venue"] or "",
        "ids": ids,
        "metadata": meta,
        "artifacts": artifact_texts,
    }
    prompt_text = "\n\n".join(sections)
    evidence_hash = hashlib.sha256(stable_json(prompt_json).encode("utf-8")).hexdigest()
    return EvidencePack(
        paper_key=paper_key,
        evidence_hash=evidence_hash,
        prompt_text=prompt_text,
        prompt_json=prompt_json,
        artifact_texts=artifact_texts,
    )


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


def find_successful_cache(conn, *, paper_key: str, provider_name: str, model: str, evidence_hash: str):
    return conn.execute(
        """
        select * from fact_extraction_cache
        where paper_key = ? and provider_name = ? and extractor_version = ?
          and model = ? and evidence_hash = ? and status = 'success'
        order by id desc limit 1
        """,
        (paper_key, provider_name, EXTRACTOR_VERSION, model, evidence_hash),
    ).fetchone()


def upsert_cache_row(
    conn,
    *,
    paper_key: str,
    provider_name: str,
    model: str,
    evidence_hash: str,
    prompt_json: dict[str, Any],
    response_json: dict[str, Any] | None,
    status: str,
    error: str,
    now: str,
) -> None:
    conn.execute(
        """
        insert into fact_extraction_cache (
            paper_key, provider_name, extractor_version, model, evidence_hash,
            prompt_json, response_json, status, error, created_at, updated_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(paper_key, provider_name, extractor_version, model, evidence_hash) do update set
            prompt_json = excluded.prompt_json,
            response_json = excluded.response_json,
            status = excluded.status,
            error = excluded.error,
            updated_at = excluded.updated_at
        """,
        (
            paper_key,
            provider_name,
            EXTRACTOR_VERSION,
            model,
            evidence_hash,
            stable_json(prompt_json),
            stable_json(response_json or {}),
            status,
            error,
            now,
            now,
        ),
    )


def write_facts(conn, *, paper_key: str, provider_name: str, facts: list[FactPayload], now: str) -> tuple[int, int]:
    clear_prior_facts(conn, paper_key=paper_key, provider_name=provider_name)
    facts_written = 0
    provenance_written = 0
    for fact in facts:
        fact_count, provenance_count = insert_fact(
            conn,
            paper_key=paper_key,
            provider_name=provider_name,
            fact=fact,
            now=now,
        )
        facts_written += fact_count
        provenance_written += provenance_count
    return facts_written, provenance_written


def extract_fixture_facts(
    db_path: Path,
    *,
    provider_name: str,
    fixture_path: Path,
    paper_key: str | None,
    limit: int | None,
) -> FactExtractionResult:
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
                fact_count, provenance_count = write_facts(
                    conn,
                    paper_key=target_paper_key,
                    provider_name=provider_name,
                    facts=facts,
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


def extract_openai_compatible_facts(
    db_path: Path,
    *,
    paper_key: str | None,
    limit: int | None,
    model: str | None,
    base_url: str | None,
    api_key_env: str,
    dry_run: bool,
    refresh_cache: bool,
    max_input_chars: int,
    client: Any | None,
) -> FactExtractionResult:
    provider_name = "openai-compatible"
    resolved_model = model or os.environ.get("AIRESEARCH_FACT_MODEL") or "gpt-4.1-mini"
    resolved_base_url = base_url or os.environ.get("OPENAI_BASE_URL")
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
            (provider_name, EXTRACTOR_VERSION, None, paper_key, limit, started_at, "running"),
        )
        run_id = run.lastrowid
        try:
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise FactValidationError(f"{api_key_env} is required for openai-compatible provider")
            target_papers = load_target_papers(conn, paper_key=paper_key, limit=limit)
            facts_written = 0
            provenance_written = 0
            cache_hits = 0
            llm_calls = 0
            dry_runs = 0
            active_client = client or OpenAICompatibleClient()
            for target_paper_key in target_papers:
                pack = build_evidence_pack(conn, target_paper_key, max_input_chars=max_input_chars)
                now = utc_now()
                if dry_run:
                    existing_success = find_successful_cache(
                        conn,
                        paper_key=target_paper_key,
                        provider_name=provider_name,
                        model=resolved_model,
                        evidence_hash=pack.evidence_hash,
                    )
                    if existing_success is None:
                        upsert_cache_row(
                            conn,
                            paper_key=target_paper_key,
                            provider_name=provider_name,
                            model=resolved_model,
                            evidence_hash=pack.evidence_hash,
                            prompt_json=pack.prompt_json,
                            response_json=None,
                            status="dry_run",
                            error="",
                            now=now,
                        )
                    dry_runs += 1
                    continue
                cached = None if refresh_cache else find_successful_cache(
                    conn,
                    paper_key=target_paper_key,
                    provider_name=provider_name,
                    model=resolved_model,
                    evidence_hash=pack.evidence_hash,
                )
                if cached is not None:
                    raw_response = parse_json(cached["response_json"], {})
                    facts = validate_provider_response(raw_response)
                    cache_hits += 1
                else:
                    try:
                        raw_response = active_client.complete_json(
                            model=resolved_model,
                            base_url=resolved_base_url,
                            api_key=api_key,
                            prompt=pack.prompt_text,
                        )
                        facts = validate_provider_response(raw_response)
                    except Exception as exc:
                        upsert_cache_row(
                            conn,
                            paper_key=target_paper_key,
                            provider_name=provider_name,
                            model=resolved_model,
                            evidence_hash=pack.evidence_hash,
                            prompt_json=pack.prompt_json,
                            response_json=None,
                            status="failed",
                            error=str(exc),
                            now=utc_now(),
                        )
                        raise
                    upsert_cache_row(
                        conn,
                        paper_key=target_paper_key,
                        provider_name=provider_name,
                        model=resolved_model,
                        evidence_hash=pack.evidence_hash,
                        prompt_json=pack.prompt_json,
                        response_json=raw_response,
                        status="success",
                        error="",
                        now=utc_now(),
                    )
                    llm_calls += 1
                fact_count, provenance_count = write_facts(
                    conn,
                    paper_key=target_paper_key,
                    provider_name=provider_name,
                    facts=facts,
                    now=utc_now(),
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
            return FactExtractionResult(
                len(target_papers),
                facts_written,
                provenance_written,
                cache_hits=cache_hits,
                llm_calls=llm_calls,
                dry_runs=dry_runs,
            )
        except Exception as exc:
            conn.execute(
                "update fact_extraction_runs set finished_at = ?, status = ?, error = ? where id = ?",
                (utc_now(), "failed", str(exc), run_id),
            )
            conn.commit()
            raise


def extract_research_facts(
    db_path: Path,
    *,
    provider_name: str,
    fixture_path: Path | None = None,
    paper_key: str | None = None,
    limit: int | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    dry_run: bool = False,
    refresh_cache: bool = False,
    max_input_chars: int = 24000,
    client: Any | None = None,
) -> FactExtractionResult:
    if provider_name == "fixture":
        if fixture_path is None:
            raise FactValidationError("fixture_path is required for fixture provider")
        return extract_fixture_facts(
            db_path,
            provider_name=provider_name,
            fixture_path=fixture_path,
            paper_key=paper_key,
            limit=limit,
        )
    if provider_name == "openai-compatible":
        return extract_openai_compatible_facts(
            db_path,
            paper_key=paper_key,
            limit=limit,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            dry_run=dry_run,
            refresh_cache=refresh_cache,
            max_input_chars=max_input_chars,
            client=client,
        )
    raise FactValidationError(f"unsupported fact extraction provider: {provider_name}")


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
