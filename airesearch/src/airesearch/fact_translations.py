from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db


def list_fact_translations(db_path: Path, *, lang: str = "zh") -> list[dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select
                t.fact_id,
                t.lang,
                t.statement,
                t.evidence_quote,
                t.model,
                f.paper_key,
                f.fact_type
            from research_fact_translations t
            join research_facts f on f.id = t.fact_id
            where t.lang = ?
            order by f.paper_key, f.fact_type, t.fact_id
            """,
            (lang,),
        ).fetchall()
    return [
        {
            "fact_id": int(row["fact_id"]),
            "lang": str(row["lang"] or ""),
            "statement": str(row["statement"] or ""),
            "evidence_quote": str(row["evidence_quote"] or ""),
            "model": str(row["model"] or ""),
            "paper_key": str(row["paper_key"] or ""),
            "fact_type": str(row["fact_type"] or ""),
        }
        for row in rows
    ]


def export_fact_translations(db_path: Path, out_path: Path, *, lang: str = "zh") -> int:
    payload = list_fact_translations(db_path, lang=lang)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return len(payload)
