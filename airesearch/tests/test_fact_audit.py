from pathlib import Path

from airesearch.db import connect, init_db
from airesearch.fact_audit import audit_research_facts


def insert_paper(conn, paper_key: str) -> None:
    now = "2026-06-09T00:00:00+00:00"
    conn.execute(
        """
        insert into papers (
            paper_key, title, authors_json, year, venue, ids_json,
            paper_dir, meta_json, created_at, updated_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paper_key,
            f"Paper {paper_key}",
            "[]",
            2026,
            "TestConf",
            "{}",
            f"/tmp/{paper_key}",
            "{}",
            now,
            now,
        ),
    )


def insert_fact(
    conn,
    *,
    paper_key: str,
    fact_type: str = "method",
    statement: str = "A grounded method statement.",
    confidence: float = 0.9,
    evidence_quote: str = "grounded quote",
    evidence_artifact_type: str = "summary",
    evidence_source_path: str = "/tmp/summary.md",
    provider_name: str = "test",
    extractor_version: str = "audit-test",
) -> None:
    now = "2026-06-09T00:00:00+00:00"
    cursor = conn.execute(
        """
        insert into research_facts (
            paper_key, fact_type, name, statement, confidence, metadata_json,
            provider_name, extractor_version, created_at, updated_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paper_key,
            fact_type,
            "",
            statement,
            confidence,
            "{}",
            provider_name,
            extractor_version,
            now,
            now,
        ),
    )
    conn.execute(
        """
        insert into research_fact_provenance (
            fact_id, evidence_quote, evidence_artifact_type, evidence_source_path, created_at
        ) values (?, ?, ?, ?, ?)
        """,
        (cursor.lastrowid, evidence_quote, evidence_artifact_type, evidence_source_path, now),
    )


def test_audit_research_facts_counts_valid_rows(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, "paper_a")
        insert_paper(conn, "paper_b")
        insert_fact(conn, paper_key="paper_a", fact_type="method")
        insert_fact(conn, paper_key="paper_b", fact_type="claim")

    result = audit_research_facts(db_path)

    assert result.total_facts == 2
    assert result.paper_count == 2
    assert result.fact_type_counts == {"claim": 1, "method": 1}
    assert result.hard_failures == 0
    assert result.soft_warnings == 0


def test_audit_research_facts_separates_hard_failures_and_soft_warnings(tmp_path: Path):
    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)
    with connect(db_path) as conn:
        insert_paper(conn, "paper_a")
        insert_fact(conn, paper_key="paper_a", statement="Duplicate statement.")
        insert_fact(
            conn,
            paper_key="paper_a",
            statement="Duplicate statement.",
            provider_name="other-test",
            extractor_version="audit-test-2",
        )
        insert_fact(
            conn,
            paper_key="paper_a",
            fact_type="unknown",
            statement="",
            confidence=1.2,
            evidence_quote="",
            evidence_artifact_type="",
            evidence_source_path="",
        )

    result = audit_research_facts(db_path)

    assert result.total_facts == 3
    assert result.empty_statement == 1
    assert result.missing_evidence_quote == 1
    assert result.missing_evidence_artifact_type == 1
    assert result.invalid_confidence == 1
    assert result.invalid_fact_type == 1
    assert result.duplicate_statements == 1
    assert result.missing_evidence_source_path == 1
    assert result.hard_failures == 6
    assert result.soft_warnings == 1
