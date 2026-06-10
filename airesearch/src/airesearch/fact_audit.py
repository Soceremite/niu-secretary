from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from airesearch.db import connect, init_db
from airesearch.fact_extraction import ALLOWED_FACT_TYPES


@dataclass(frozen=True)
class FactAuditResult:
    total_facts: int
    paper_count: int
    fact_type_counts: dict[str, int]
    empty_statement: int
    missing_evidence_quote: int
    missing_evidence_artifact_type: int
    missing_evidence_source_path: int
    invalid_confidence: int
    invalid_fact_type: int
    duplicate_statements: int

    @property
    def hard_failures(self) -> int:
        return (
            self.empty_statement
            + self.missing_evidence_quote
            + self.missing_evidence_artifact_type
            + self.invalid_confidence
            + self.invalid_fact_type
            + self.duplicate_statements
        )

    @property
    def soft_warnings(self) -> int:
        return self.missing_evidence_source_path


def audit_research_facts(db_path: Path) -> FactAuditResult:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            select
                f.paper_key,
                f.fact_type,
                f.statement,
                f.confidence,
                p.evidence_quote,
                p.evidence_artifact_type,
                p.evidence_source_path
            from research_facts f
            left join research_fact_provenance p on p.fact_id = f.id
            """
        ).fetchall()

    type_counts = Counter(str(row["fact_type"] or "").strip() for row in rows)
    paper_keys = {str(row["paper_key"] or "").strip() for row in rows if str(row["paper_key"] or "").strip()}
    statement_keys = Counter(_statement_key(row) for row in rows if _statement_key(row))

    return FactAuditResult(
        total_facts=len(rows),
        paper_count=len(paper_keys),
        fact_type_counts=dict(sorted(type_counts.items())),
        empty_statement=sum(not str(row["statement"] or "").strip() for row in rows),
        missing_evidence_quote=sum(not str(row["evidence_quote"] or "").strip() for row in rows),
        missing_evidence_artifact_type=sum(
            not str(row["evidence_artifact_type"] or "").strip() for row in rows
        ),
        missing_evidence_source_path=sum(not str(row["evidence_source_path"] or "").strip() for row in rows),
        invalid_confidence=sum(not _valid_confidence(row["confidence"]) for row in rows),
        invalid_fact_type=sum(str(row["fact_type"] or "").strip() not in ALLOWED_FACT_TYPES for row in rows),
        duplicate_statements=sum(count - 1 for count in statement_keys.values() if count > 1),
    )


def _statement_key(row: Any) -> tuple[str, str, str] | None:
    paper_key = str(row["paper_key"] or "").strip()
    fact_type = str(row["fact_type"] or "").strip()
    statement = str(row["statement"] or "").strip().lower()
    if not paper_key or not fact_type or not statement:
        return None
    return (paper_key, fact_type, statement)


def _valid_confidence(value: Any) -> bool:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return False
    return 0 <= confidence <= 1
