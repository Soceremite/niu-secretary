import json
from pathlib import Path

import pytest

from airesearch.claim_trace import (
    ClaimTraceNotFound,
    export_claim_trace,
    render_claim_trace_markdown,
    trace_claim,
)
from airesearch.artifact_ledger import extract_artifact_ledger
from airesearch.code_links import extract_code_links
from airesearch.db import connect, init_db
from airesearch.fact_extraction import extract_research_facts
from airesearch.knowledge_graph import extract_paper_cards
from airesearch.paperpipe_sync import sync_paperpipe


FIXTURE = Path(__file__).parent / "fixtures" / "fact_extraction_fixture.json"


def traced_fixture_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    init_db(db_path)
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    extract_artifact_ledger(db_path)
    extract_research_facts(db_path, provider_name="fixture", fixture_path=FIXTURE)
    extract_code_links(db_path)
    extract_paper_cards(db_path)
    return db_path


def first_fact_id(db_path: Path, fact_type: str = "claim") -> int:
    with connect(db_path) as conn:
        row = conn.execute(
            "select id from research_facts where fact_type = ? order by id limit 1",
            (fact_type,),
        ).fetchone()
    return int(row["id"])


def test_trace_claim_by_fact_id_includes_evidence_artifacts_code_and_graph(tmp_path: Path):
    db_path = traced_fixture_db(tmp_path)
    fact_id = first_fact_id(db_path)

    trace = trace_claim(db_path, fact_id=fact_id)

    assert trace["fact"]["id"] == fact_id
    assert trace["fact"]["paper_key"] == "1706_03762"
    assert trace["paper"]["title"] == "Attention Is All You Need"
    assert trace["paper"]["ids"]["arxiv_id"] == "1706.03762"
    assert "attention" in trace["provenance"][0]["evidence_quote"].lower()
    assert trace["provenance"][0]["evidence_source_path"].endswith("summary.md")
    assert trace["artifacts"][0]["artifact_type"] == "summary"
    assert trace["ledger_matches"][0]["kind"] == "chunk"
    assert trace["ledger_matches"][0]["artifact_type"] == "summary"
    assert trace["code_links"][0]["url"] == "https://github.com/attention/transformer"
    assert any(row["relation"] == "has_artifact" for row in trace["graph_relations"])
    assert any(row["relation"] == "has_code_repository" for row in trace["graph_relations"])
    assert any(row["source_table"] == "paper_artifacts" for row in trace["graph_provenance"])


def test_trace_claim_can_select_by_paper_type_and_query(tmp_path: Path):
    db_path = traced_fixture_db(tmp_path)

    trace = trace_claim(
        db_path,
        paper_key="1706_03762",
        fact_type="method",
        query="recurrence",
    )

    assert trace["fact"]["fact_type"] == "method"
    assert "recurrence" in trace["fact"]["statement"].lower()


def test_render_claim_trace_markdown_has_trace_sections(tmp_path: Path):
    db_path = traced_fixture_db(tmp_path)
    trace = trace_claim(db_path, fact_id=first_fact_id(db_path))

    rendered = render_claim_trace_markdown(trace)

    assert "# Claim Trace" in rendered
    assert "## Evidence" in rendered
    assert "## Artifact Ledger Matches" in rendered
    assert "summary.md" in rendered
    assert "https://github.com/attention/transformer" in rendered
    assert "[has_code_repository]" in rendered


def test_export_claim_trace_writes_json(tmp_path: Path):
    db_path = traced_fixture_db(tmp_path)
    out_path = tmp_path / "claim-trace.json"

    rendered = export_claim_trace(
        db_path,
        out_path=out_path,
        output_format="json",
        fact_id=first_fact_id(db_path),
    )

    payload = json.loads(rendered)
    file_payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["fact"]["paper_key"] == "1706_03762"
    assert payload["ledger_matches"][0]["kind"] == "chunk"
    assert file_payload["artifacts"][0]["artifact_type"] == "summary"


def test_trace_claim_not_found_raises_clear_error(tmp_path: Path):
    db_path = traced_fixture_db(tmp_path)

    with pytest.raises(ClaimTraceNotFound, match="claim_trace_not_found fact_id=999999"):
        trace_claim(db_path, fact_id=999999)
