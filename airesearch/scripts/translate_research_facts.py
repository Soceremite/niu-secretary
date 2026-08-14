from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

from airesearch.db import connect, init_db
from airesearch.research_digest import utc_now


FACT_TYPES = ("method", "claim", "limitation", "dataset", "benchmark")
SYSTEM_PROMPT = (
    "Translate the provided research fact into concise, natural Simplified Chinese. "
    "Preserve technical terms, model names, URLs, formulas, and identifiers when appropriate. "
    "Return strict JSON with keys statement and evidence_quote."
)


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized == "https://api.deepseek.com":
        return normalized + "/v1"
    return normalized


def _extract_json_object(text: str) -> dict[str, str]:
    content = text.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3:
            content = "\n".join(lines[1:-1]).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"translation response is not JSON: {content[:200]}")
    payload = json.loads(content[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("translation response must be a JSON object")
    return {
        "statement": str(payload.get("statement") or "").strip(),
        "evidence_quote": str(payload.get("evidence_quote") or "").strip(),
    }


def translate_fact(*, base_url: str, api_key: str, model: str, statement: str, evidence_quote: str) -> dict[str, str]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"statement": statement, "evidence_quote": evidence_quote},
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.2,
    }
    req = request.Request(
        _normalize_base_url(base_url) + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"translation API error {exc.code}: {detail}") from exc
    choices = body.get("choices", [])
    if not choices:
        raise ValueError("translation API returned no choices")
    message = choices[0].get("message", {})
    return _extract_json_object(str(message.get("content") or ""))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--model", default=os.environ.get("TRANSLATE_MODEL", "deepseek-v4-pro"))
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TRANSLATE_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.deepseek.com/v1",
    )
    parser.add_argument("--api-key-env", default="TRANSLATE_API_KEY")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--lang", default="zh")
    parser.add_argument("--fact-type", action="append", dest="fact_types")
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key and args.api_key_env == "TRANSLATE_API_KEY":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(f"missing API key in {args.api_key_env}")

    fact_types = tuple(args.fact_types or FACT_TYPES)
    placeholders = ",".join("?" for _ in fact_types)

    init_db(args.db)
    with connect(args.db) as conn:
        rows = conn.execute(
            f"""
            select
                f.id,
                f.paper_key,
                f.fact_type,
                f.statement,
                coalesce((
                    select p.evidence_quote
                    from research_fact_provenance p
                    where p.fact_id = f.id
                    order by p.id
                    limit 1
                ), '') as evidence_quote,
                t.id as translation_id
            from research_facts f
            left join research_fact_translations t
                on t.fact_id = f.id and t.lang = ?
            where f.fact_type in ({placeholders})
            order by f.paper_key, f.fact_type, f.id
            """,
            (args.lang, *fact_types),
        ).fetchall()

    pending = [row for row in rows if args.overwrite or row["translation_id"] is None]

    def work(row: object) -> tuple[int, str, str, str, str]:
        translated = translate_fact(
            base_url=args.base_url,
            api_key=api_key,
            model=args.model,
            statement=str(row["statement"] or ""),
            evidence_quote=str(row["evidence_quote"] or ""),
        )
        return (
            int(row["id"]),
            str(row["paper_key"] or ""),
            str(row["fact_type"] or ""),
            translated["statement"],
            translated["evidence_quote"],
        )

    translated_count = 0
    with connect(args.db) as conn:
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
            futures = [pool.submit(work, row) for row in pending]
            for future in as_completed(futures):
                fact_id, paper_key, fact_type, statement_zh, evidence_quote_zh = future.result()
                now = utc_now()
                conn.execute(
                    """
                    insert into research_fact_translations (
                        fact_id, lang, statement, evidence_quote, model, created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?)
                    on conflict(fact_id, lang) do update set
                        statement = excluded.statement,
                        evidence_quote = excluded.evidence_quote,
                        model = excluded.model,
                        updated_at = excluded.updated_at
                    """,
                    (fact_id, args.lang, statement_zh, evidence_quote_zh, args.model, now, now),
                )
                conn.commit()
                translated_count += 1
                print(f"translated fact_id={fact_id} paper={paper_key} type={fact_type}")
    print(f"translated_facts={translated_count} total_candidates={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
