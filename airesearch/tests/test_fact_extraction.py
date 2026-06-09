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


class FakeFactClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = []

    def complete_json(self, *, model: str, base_url: str | None, api_key: str, prompt: str) -> dict:
        self.calls.append({
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "prompt": prompt,
        })
        return self.payload


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

def test_openai_compatible_dry_run_writes_cache_without_calling_client(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    client = FakeFactClient({"facts": []})
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        paper_key="1706_03762",
        model="qwen3.7-max",
        dry_run=True,
        client=client,
    )

    assert result.papers_seen == 1
    assert result.dry_runs == 1
    assert result.llm_calls == 0
    assert client.calls == []
    with connect(db_path) as conn:
        row = conn.execute("select * from fact_extraction_cache").fetchone()
    assert row["model"] == "qwen3.7-max"
    assert row["status"] == "dry_run"


def test_openai_compatible_writes_facts_and_uses_cache(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash-key")
    payload = {
        "facts": [
            {
                "fact_type": "method",
                "name": "Transformer",
                "statement": "The paper uses a Transformer architecture.",
                "evidence_quote": "Attention Is All You Need",
                "evidence_artifact_type": "summary",
                "confidence": 0.8,
                "metadata": {"rationale": "title and summary evidence"},
            }
        ]
    }
    client = FakeFactClient(payload)

    first = extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        paper_key="1706_03762",
        model="qwen3.7-max",
        api_key_env="DASHSCOPE_API_KEY",
        base_url="https://dashscope.example/compatible-mode/v1",
        client=client,
    )
    second = extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        paper_key="1706_03762",
        model="qwen3.7-max",
        api_key_env="DASHSCOPE_API_KEY",
        base_url="https://dashscope.example/compatible-mode/v1",
        client=client,
    )

    assert first.llm_calls == 1
    assert second.cache_hits == 1
    assert len(client.calls) == 1
    assert client.calls[0]["model"] == "qwen3.7-max"
    assert client.calls[0]["base_url"] == "https://dashscope.example/compatible-mode/v1"
    facts = list_research_facts(db_path, paper_key="1706_03762", limit=10)
    assert len(facts) == 1
    assert facts[0]["provider_name"] == "openai-compatible"


def test_openai_compatible_missing_api_key_fails(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(FactValidationError, match="OPENAI_API_KEY"):
        extract_research_facts(
            db_path,
            provider_name="openai-compatible",
            paper_key="1706_03762",
            model="gpt5.5",
            client=FakeFactClient({"facts": []}),
        )


def test_openai_compatible_invalid_response_does_not_write_partial_facts(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(FactValidationError):
        extract_research_facts(
            db_path,
            provider_name="openai-compatible",
            paper_key="1706_03762",
            model="gpt5.5",
            client=FakeFactClient({"facts": [{"fact_type": "opinion"}]}),
        )

    assert list_research_facts(db_path, paper_key="1706_03762", limit=10) == []

def test_openai_compatible_dry_run_does_not_overwrite_success_cache(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = {
        "facts": [
            {
                "fact_type": "method",
                "name": "Transformer",
                "statement": "The paper uses a Transformer architecture.",
                "evidence_quote": "Attention Is All You Need",
                "evidence_artifact_type": "summary",
                "confidence": 0.8,
                "metadata": {},
            }
        ]
    }
    client = FakeFactClient(payload)
    extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        paper_key="1706_03762",
        model="gpt5.5",
        client=client,
    )

    dry_run = extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        paper_key="1706_03762",
        model="gpt5.5",
        dry_run=True,
        client=client,
    )

    assert dry_run.dry_runs == 1
    with connect(db_path) as conn:
        row = conn.execute("select status, response_json from fact_extraction_cache").fetchone()
    assert row["status"] == "success"
    assert row["response_json"]

