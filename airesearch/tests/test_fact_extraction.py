import json
from pathlib import Path

import pytest

from airesearch.db import connect, init_db
from airesearch.fact_extraction import (
    FactValidationError,
    build_evidence_pack,
    export_research_facts,
    extract_research_facts,
    list_research_facts,
)
from airesearch.paperpipe_sync import sync_paperpipe


FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"


def synced_fixture_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    init_db(db_path)
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    return db_path


def test_extract_research_facts_from_fixture_creates_facts_and_provenance(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)

    result = extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)

    assert result.papers_seen == 1
    assert result.facts_written == 2
    assert result.provenance_written == 2
    with connect(db_path) as conn:
        facts = conn.execute("select * from research_facts order by fact_type").fetchall()
        provenance = conn.execute("select * from research_fact_provenance order by fact_id").fetchall()

    assert [row["fact_type"] for row in facts] == ["claim", "method"]
    assert facts[0]["statement"]
    assert provenance[0]["evidence_artifact_type"] == "summary"
    assert "attention" in provenance[0]["evidence_quote"].lower()


def test_extract_research_facts_is_idempotent_for_provider_version(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)

    first = extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)
    second = extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)

    assert first.facts_written == 2
    assert second.facts_written == 2
    with connect(db_path) as conn:
        fact_count = conn.execute("select count(*) as count from research_facts").fetchone()["count"]
        provenance_count = conn.execute("select count(*) as count from research_fact_provenance").fetchone()["count"]

    assert fact_count == 2
    assert provenance_count == 2


def test_list_and_export_research_facts(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)
    out_path = tmp_path / "facts.jsonl"
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)

    rows = list_research_facts(db_path, paper_key="1706_03762", fact_type="method", limit=10)
    exported = export_research_facts(db_path, out_path)

    assert len(rows) == 1
    assert rows[0]["fact_type"] == "method"
    assert exported == 2
    payloads = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    assert payloads[0]["paper_key"] == "1706_03762"
    assert payloads[0]["evidence_quote"]


def test_extract_research_facts_rejects_invalid_fact_type(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)
    bad_fixture = tmp_path / "bad.json"
    bad_fixture.write_text(json.dumps({
        "1706_03762": [
            {
                "fact_type": "opinion",
                "name": "bad",
                "statement": "bad",
                "evidence_quote": "bad",
                "evidence_artifact_type": "summary",
                "confidence": 0.5,
            }
        ]
    }), encoding="utf-8")

    with pytest.raises(FactValidationError):
        extract_research_facts(db_path, provider_name="fixture", fixture_path=bad_fixture)

def test_build_evidence_pack_includes_metadata_and_artifacts(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)

    with connect(db_path) as conn:
        pack = build_evidence_pack(conn, "1706_03762", max_input_chars=4000)

    assert pack.paper_key == "1706_03762"
    assert pack.evidence_hash
    assert "Attention Is All You Need" in pack.prompt_text
    assert "summary" in pack.artifact_texts
    assert "source_tex" in pack.artifact_texts
    assert len(pack.prompt_text) <= 4000 + 1000


def test_build_evidence_pack_hash_is_deterministic(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)

    with connect(db_path) as conn:
        first = build_evidence_pack(conn, "1706_03762", max_input_chars=4000)
        second = build_evidence_pack(conn, "1706_03762", max_input_chars=4000)

    assert first.evidence_hash == second.evidence_hash
    assert first.prompt_json == second.prompt_json

