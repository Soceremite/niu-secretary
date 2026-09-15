from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from airesearch.db import connect, init_db
from airesearch.paperpipe_sync import stable_json
from airesearch.provider_config import responses_url

try:  # unified LLM gateway config (models.yaml) — optional, falls back gracefully
    from niu_core.llm_client import compat as _niu_compat
except Exception:  # pragma: no cover - niu_core not on path in some deploys
    _niu_compat = None  # type: ignore[assignment]


class _CompatProxy:
    """Duck-typed access to compat.resolve; no-op when niu_core is absent."""

    @staticmethod
    def resolve(name: str) -> tuple[str, str, str]:
        if _niu_compat is None:
            raise RuntimeError("niu_core unavailable")
        return _niu_compat.resolve(name)


compat = _CompatProxy()


EXTRACTOR_VERSION = "2026-06-08.1"
ALLOWED_FACT_TYPES = {"method", "dataset", "benchmark", "claim", "limitation"}
TEXT_ARTIFACT_TYPES = ("summary", "tldr", "notes", "source_tex")
FACT_EXTRACTION_SYSTEM_PROMPT = """Extract grounded research facts from the provided evidence pack.
Return only JSON with a top-level facts array. Each fact must use one of these
fact_type values: method, dataset, benchmark, claim, limitation. Each fact must
include statement, evidence_quote copied from the evidence pack,
evidence_artifact_type, confidence between 0 and 1, and metadata object.
Cover all five fact types when the evidence pack supports them, including an
explicit limitation grounded in the source rather than inferred by the model.
The response must be strict JSON: escape every backslash inside JSON strings as
a double backslash and do not emit raw LaTeX backslash escapes.
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
    failed_count: int = 0
    failed_errors: dict[str, str] | None = None


class OpenAICompatibleClient:
    @staticmethod
    def _endpoint(base_url: str | None) -> tuple[str, str]:
        value = (base_url or "https://api.openai.com/v1").rstrip("/")
        if value.endswith("/responses"):
            return value, "responses"
        if value.endswith("/chat/completions"):
            return value, "chat_completions"
        return value + "/chat/completions", "chat_completions"

    @staticmethod
    def _response_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            content = choices[0].get("message", {}).get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    str(item.get("text") or "") for item in content if isinstance(item, dict)
                )
        if isinstance(payload.get("output_text"), str):
            return str(payload["output_text"])
        output = payload.get("output")
        if isinstance(output, list):
            return "".join(
                str(content.get("text") or "")
                for item in output
                if isinstance(item, dict)
                for content in (item.get("content") or [])
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"}
            )
        return ""

    def complete_json(self, *, model: str, base_url: str | None, api_key: str, prompt: str) -> dict[str, Any]:
        endpoint, api_style = self._endpoint(base_url)
        if api_style == "responses":
            request_payload = {
                "model": model,
                "input": [
                    {"role": "system", "content": [{"type": "input_text", "text": FACT_EXTRACTION_SYSTEM_PROMPT}]},
                    {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
                ],
                "max_output_tokens": 6000,
            }
        else:
            request_payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }
        body = stable_json(request_payload).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "authorization": f"Bearer {api_key}",
                "content-type": "application/json",
                "user-agent": "OpenClaw/1.0",
                "accept": "application/json",
            },
            method="POST",
        )
        try:
            proxy_url = (
                os.environ.get("AIRESEARCH_FACT_PROXY")
                or os.environ.get("AIRESEARCH_FORMULA_OCR_PROXY")
                or os.environ.get("OPENCODE_GO_PROXY")
                or ""
            ).strip()
            if proxy_url:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
                )
                response_context = opener.open(request, timeout=300)
            else:
                response_context = urllib.request.urlopen(request, timeout=300)
            with response_context as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise FactValidationError(f"provider HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise FactValidationError(f"provider request failed: {exc}") from exc
        try:
            content = self._response_text(payload).strip()
            content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I)
            content = re.sub(r"\s*```$", "", content).strip()
            result = json.loads(content)
            if not isinstance(result, dict):
                raise TypeError("JSON root must be an object")
            return result
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


def build_evidence_pack(
    conn,
    paper_key: str,
    *,
    max_input_chars: int,
    required_fact_types: Iterable[str] | None = None,
) -> EvidencePack:
    paper = conn.execute("select * from papers where paper_key = ?", (paper_key,)).fetchone()
    if paper is None:
        raise FactValidationError(f"paper not found: {paper_key}")
    remaining = max_input_chars
    meta = parse_json(paper["meta_json"], {})
    ids = parse_json(paper["ids_json"], {})
    authors = parse_json(paper["authors_json"], [])
    required_types = sorted({str(value).strip() for value in (required_fact_types or ()) if str(value).strip()})
    sections: list[str] = [
        f"paper_key: {paper_key}",
        f"title: {paper['title'] or ''}",
        f"authors: {', '.join(str(author) for author in authors)}",
        f"year: {paper['year'] or ''}",
        f"venue: {paper['venue'] or ''}",
        f"ids: {stable_json(ids)}",
        f"metadata: {stable_json(meta)}",
    ]
    if required_types:
        sections.append(
            "REQUIRED FACT TYPES FOR THIS RETRY: "
            + ", ".join(required_types)
            + ". Return at least one grounded fact for every listed type and retain all other grounded types. "
            + "Do not invent a type when the evidence does not support it; quote the exact supporting evidence."
        )
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
        "required_fact_types": required_types,
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


def load_target_papers(
    conn,
    *,
    paper_key: str | None = None,
    paper_keys: Iterable[str] | None = None,
    limit: int | None = None,
):
    if paper_keys is not None:
        requested = []
        seen: set[str] = set()
        for value in paper_keys:
            key = str(value or "").strip()
            if key and key not in seen:
                requested.append(key)
                seen.add(key)
        if not requested:
            return []
        placeholders = ",".join("?" for _ in requested)
        rows = conn.execute(
            f"select paper_key from papers where paper_key in ({placeholders})",
            requested,
        ).fetchall()
        present = {str(row["paper_key"]) for row in rows}
        missing = [key for key in requested if key not in present]
        if missing:
            raise FactValidationError("paper list contains missing papers: " + ",".join(missing))
        return requested[:limit] if limit is not None else requested
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


def _required_retry_types(
    required_fact_types: Mapping[str, Iterable[str]] | None,
    paper_key: str,
) -> set[str]:
    """A targeted retry must be complete before it can replace prior facts."""
    configured = {
        str(value).strip()
        for value in (required_fact_types or {}).get(paper_key, ())
        if str(value).strip()
    }
    return set(ALLOWED_FACT_TYPES) if configured else set()


def _validate_required_retry_facts(
    facts: list[FactPayload],
    *,
    required_fact_types: Mapping[str, Iterable[str]] | None,
    paper_key: str,
) -> None:
    required = _required_retry_types(required_fact_types, paper_key)
    if not required:
        return
    returned = {fact.fact_type for fact in facts}
    missing = sorted(required - returned)
    if missing:
        raise FactValidationError(
            f"targeted retry requires all five fact types before write_facts: {','.join(missing)}"
        )


def extract_fixture_facts(
    db_path: Path,
    *,
    provider_name: str,
    fixture_path: Path,
    paper_key: str | None,
    paper_keys: Iterable[str] | None = None,
    required_fact_types: Mapping[str, Iterable[str]] | None = None,
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
            target_papers = load_target_papers(
                conn, paper_key=paper_key, paper_keys=paper_keys, limit=limit
            )
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
    paper_keys: Iterable[str] | None,
    required_fact_types: Mapping[str, Iterable[str]] | None = None,
    limit: int | None,
    model: str | None,
    base_url: str | None,
    api_key_env: str,
    dry_run: bool,
    refresh_cache: bool,
    max_input_chars: int,
    concurrency: int = 5,
    client: Any | None,
    error_policy: str = "strict",
) -> FactExtractionResult:
    if error_policy not in {"strict", "warn"}:
        raise ValueError("error_policy must be one of: strict, warn")
    provider_name = "openai-compatible"
    compat_default: tuple[str, str, str] | None = None
    if model is None or base_url is None:
        try:
            compat_default = compat.resolve("fact")
        except Exception:
            compat_default = None
    if compat_default is not None:
        _compat_base_url, _compat_key, _compat_model = compat_default
    else:
        _compat_base_url, _compat_key, _compat_model = "", "", ""
    resolved_model = (
        model
        or os.environ.get("AIRESEARCH_FACT_MODEL")
        or _compat_model
        or "gpt-4.1-mini"
    )
    resolved_base_url = (
        base_url
        or os.environ.get("AIRESEARCH_FACT_BASE_URL")
        or responses_url(os.environ.get("OPENCODE_GO_BASE_URL"))
        or os.environ.get("OPENAI_BASE_URL")
        or _compat_base_url
    )
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
            api_key = (
                os.environ.get(api_key_env)
                or os.environ.get("AIRESEARCH_FACT_API_KEY")
                or os.environ.get("OPENCODE_GO_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
            )
            if not api_key:
                raise FactValidationError(
                    f"{api_key_env} is required for openai-compatible provider "
                    "(fallbacks: AIRESEARCH_FACT_API_KEY, OPENAI_API_KEY, OPENCODE_GO_API_KEY)"
                )
            target_papers = load_target_papers(
                conn, paper_key=paper_key, paper_keys=paper_keys, limit=limit
            )
            active_client = client or OpenAICompatibleClient()

            # ── Phase 1: Build all evidence packs, identify workload ──
            llm_queue: list[tuple[str, EvidencePack]] = []
            cache_results: list[tuple[str, EvidencePack, list[FactPayload]]] = []
            dry_run_count = 0

            for pk in target_papers:
                pack = build_evidence_pack(
                    conn,
                    pk,
                    max_input_chars=max_input_chars,
                    required_fact_types=_required_retry_types(required_fact_types, pk),
                )
                now = utc_now()
                if dry_run:
                    existing_success = find_successful_cache(
                        conn,
                        paper_key=pk,
                        provider_name=provider_name,
                        model=resolved_model,
                        evidence_hash=pack.evidence_hash,
                    )
                    if existing_success is None:
                        upsert_cache_row(
                            conn,
                            paper_key=pk,
                            provider_name=provider_name,
                            model=resolved_model,
                            evidence_hash=pack.evidence_hash,
                            prompt_json=pack.prompt_json,
                            response_json=None,
                            status="dry_run",
                            error="",
                            now=now,
                        )
                    dry_run_count += 1
                    continue
                if not refresh_cache:
                    cached = find_successful_cache(
                        conn,
                        paper_key=pk,
                        provider_name=provider_name,
                        model=resolved_model,
                        evidence_hash=pack.evidence_hash,
                    )
                    if cached is not None:
                        raw_response = parse_json(cached["response_json"], {})
                        facts = validate_provider_response(raw_response)
                        _validate_required_retry_facts(
                            facts,
                            required_fact_types=required_fact_types,
                            paper_key=pk,
                        )
                        cache_results.append((pk, pack, facts))
                        continue
                llm_queue.append((pk, pack))

            # ── Phase 2: Concurrent LLM calls via ThreadPoolExecutor ──
            llm_results: dict[str, list[FactPayload]] = {}
            llm_errors: dict[str, str] = {}
            if llm_queue:
                workers = max(1, min(concurrency, len(llm_queue)))
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    future_map = {}
                    for pk, pack in llm_queue:
                        future = executor.submit(
                            active_client.complete_json,
                            model=resolved_model,
                            base_url=resolved_base_url,
                            api_key=api_key,
                            prompt=pack.prompt_text,
                        )
                        future_map[future] = (pk, pack)
                    for future in as_completed(future_map):
                        pk, pack = future_map[future]
                        try:
                            raw_response = future.result()
                            facts = validate_provider_response(raw_response)
                            _validate_required_retry_facts(
                                facts,
                                required_fact_types=required_fact_types,
                                paper_key=pk,
                            )
                            llm_results[pk] = facts
                        except Exception as exc:
                            llm_errors[pk] = f"{type(exc).__name__}: {exc}"

            # ── Phase 3: Sequential DB writes ──
            facts_written = 0
            provenance_written = 0
            cache_hits = 0
            llm_calls = 0
            now = utc_now()

            for pk, pack, facts in cache_results:
                fact_count, provenance_count = write_facts(
                    conn, paper_key=pk, provider_name=provider_name, facts=facts, now=now,
                )
                facts_written += fact_count
                provenance_written += provenance_count
                cache_hits += 1

            for pk, pack in llm_queue:
                if pk in llm_errors:
                    upsert_cache_row(
                        conn,
                        paper_key=pk,
                        provider_name=provider_name,
                        model=resolved_model,
                        evidence_hash=pack.evidence_hash,
                        prompt_json=pack.prompt_json,
                        response_json=None,
                        status="failed",
                        error=llm_errors[pk],
                        now=now,
                    )
                    continue
                facts = llm_results[pk]
                upsert_cache_row(
                    conn,
                    paper_key=pk,
                    provider_name=provider_name,
                    model=resolved_model,
                    evidence_hash=pack.evidence_hash,
                    prompt_json=pack.prompt_json,
                    response_json={"facts": [{
                        "fact_type": f.fact_type,
                        "name": f.name,
                        "statement": f.statement,
                        "evidence_quote": f.evidence_quote,
                        "evidence_artifact_type": f.evidence_artifact_type,
                        "confidence": f.confidence,
                        "metadata": f.metadata,
                    } for f in facts]},
                    status="success",
                    error="",
                    now=now,
                )
                fact_count, provenance_count = write_facts(
                    conn, paper_key=pk, provider_name=provider_name, facts=facts, now=now,
                )
                facts_written += fact_count
                provenance_written += provenance_count
                llm_calls += 1

            if llm_errors and error_policy == "strict":
                error_lines = [f"{pk}: {err}" for pk, err in llm_errors.items()]
                raise FactValidationError(
                    f"LLM extraction failed for {len(llm_errors)}/{len(llm_queue)} papers:\n"
                    + "\n".join(error_lines)
                )

            status = "partial_success" if llm_errors else "success"
            error_summary = ""
            if llm_errors:
                error_summary = (
                    f"LLM extraction failed for {len(llm_errors)}/{len(llm_queue)} papers:\n"
                    + "\n".join(f"{pk}: {err}" for pk, err in llm_errors.items())
                )
            conn.execute(
                """
                update fact_extraction_runs set
                    papers_seen = ?, facts_written = ?, provenance_written = ?,
                    finished_at = ?, status = ?, error = ?
                where id = ?
                """,
                (
                    len(target_papers),
                    facts_written,
                    provenance_written,
                    utc_now(),
                    status,
                    error_summary,
                    run_id,
                ),
            )
            conn.commit()
            return FactExtractionResult(
                len(target_papers),
                facts_written,
                provenance_written,
                cache_hits=cache_hits,
                llm_calls=llm_calls,
                dry_runs=dry_run_count,
                failed_count=len(llm_errors),
                failed_errors=dict(llm_errors) if llm_errors else None,
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
    paper_keys: Iterable[str] | None = None,
    required_fact_types: Mapping[str, Iterable[str]] | None = None,
    limit: int | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key_env: str = "AIRESEARCH_FACT_API_KEY",
    dry_run: bool = False,
    refresh_cache: bool = False,
    max_input_chars: int = 24000,
    concurrency: int = 5,
    client: Any | None = None,
    error_policy: str = "strict",
) -> FactExtractionResult:
    if provider_name == "fixture":
        if fixture_path is None:
            raise FactValidationError("fixture_path is required for fixture provider")
        return extract_fixture_facts(
            db_path,
            provider_name=provider_name,
            fixture_path=fixture_path,
            paper_key=paper_key,
            paper_keys=paper_keys,
            required_fact_types=required_fact_types,
            limit=limit,
        )
    if provider_name == "openai-compatible":
        return extract_openai_compatible_facts(
            db_path,
            paper_key=paper_key,
            paper_keys=paper_keys,
            required_fact_types=required_fact_types,
            limit=limit,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            dry_run=dry_run,
            refresh_cache=refresh_cache,
            max_input_chars=max_input_chars,
            concurrency=concurrency,
            client=client,
            error_policy=error_policy,
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
