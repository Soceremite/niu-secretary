import json
from pathlib import Path

import pytest

from airesearch.db import connect, init_db
from airesearch.fact_extraction import (
    ALLOWED_FACT_TYPES,
    FactValidationError,
    OpenAICompatibleClient,
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


class PromptAwareFactClient:
    def __init__(self, payloads: dict[str, dict], failures: dict[str, Exception] | None = None):
        self.payloads = payloads
        self.failures = failures or {}
        self.calls = []

    def complete_json(self, *, model: str, base_url: str | None, api_key: str, prompt: str) -> dict:
        self.calls.append(prompt)
        for marker, error in self.failures.items():
            if marker in prompt:
                raise error
        for marker, payload in self.payloads.items():
            if marker in prompt:
                return payload
        return {"facts": []}


def synced_fixture_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    init_db(db_path)
    sync_paperpipe(db_path=db_path, paper_db_path=paper_db)
    return db_path


def add_synthetic_paper(db_path: Path, tmp_path: Path) -> None:
    paper_dir = tmp_path / "synthetic_paper"
    paper_dir.mkdir()
    summary_path = paper_dir / "summary.md"
    summary_path.write_text(
        "Synthetic Control Paper introduces a controlled benchmark for fact extraction.",
        encoding="utf-8",
    )
    now = "2026-06-09T00:00:00+00:00"
    with connect(db_path) as conn:
        conn.execute(
            """
            insert into papers (
                paper_key, title, authors_json, year, venue, ids_json,
                paper_dir, meta_json, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "synthetic_control",
                "Synthetic Control Paper",
                json.dumps(["Test Author"]),
                2026,
                "TestConf",
                json.dumps({"arxiv_id": "2606.00000"}),
                str(paper_dir),
                json.dumps({"abstract": "Controlled benchmark for fact extraction."}),
                now,
                now,
            ),
        )
        conn.execute(
            """
            insert into paper_artifacts (
                paper_key, artifact_type, path, sha256, size_bytes, updated_at
            ) values (?, ?, ?, ?, ?, ?)
            """,
            (
                "synthetic_control",
                "summary",
                str(summary_path),
                "0" * 64,
                summary_path.stat().st_size,
                now,
            ),
        )
        conn.commit()


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


def test_build_evidence_pack_records_required_fact_types(tmp_path: Path):
    db_path = synced_fixture_db(tmp_path)
    with connect(db_path) as conn:
        pack = build_evidence_pack(
            conn,
            "1706_03762",
            max_input_chars=4000,
            required_fact_types=["dataset", "limitation"],
        )
    assert pack.prompt_json["required_fact_types"] == ["dataset", "limitation"]
    assert "REQUIRED FACT TYPES FOR THIS RETRY" in pack.prompt_text


def test_required_fact_types_are_forwarded_to_openai_provider_and_prompt(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = FakeFactClient({"facts": []})

    from unittest.mock import patch

    with patch("airesearch.fact_extraction.extract_openai_compatible_facts") as extractor:
        extractor.return_value = type("Result", (), {
            "papers_seen": 1,
            "facts_written": 0,
            "provenance_written": 0,
            "cache_hits": 0,
            "llm_calls": 0,
            "dry_runs": 0,
            "failed_count": 0,
        })()
        extract_research_facts(
            db_path,
            provider_name="openai-compatible",
            paper_key="1706_03762",
            required_fact_types={"1706_03762": ["dataset"]},
            client=client,
        )

    assert extractor.call_args.kwargs["required_fact_types"] == {"1706_03762": ["dataset"]}


def test_targeted_retry_requires_all_five_types_before_write(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    original = {
        "facts": [{
            "fact_type": "method",
            "name": "Existing method",
            "statement": "The existing grounded method must survive a failed retry.",
            "evidence_quote": "Attention Is All You Need",
            "evidence_artifact_type": "summary",
            "confidence": 0.9,
            "metadata": {},
        }]
    }
    extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        paper_key="1706_03762",
        model="gpt-5.6-luna",
        client=FakeFactClient(original),
        refresh_cache=True,
    )
    partial = {
        "facts": [
            {
                "fact_type": fact_type,
                "name": fact_type,
                "statement": f"Grounded {fact_type}.",
                "evidence_quote": "Attention Is All You Need",
                "evidence_artifact_type": "summary",
                "confidence": 0.9,
                "metadata": {},
            }
            for fact_type in sorted(ALLOWED_FACT_TYPES - {"limitation"})
        ]
    }
    client = FakeFactClient(partial)

    with pytest.raises(FactValidationError, match="all five fact types"):
        extract_research_facts(
            db_path,
            provider_name="openai-compatible",
            paper_key="1706_03762",
            required_fact_types={"1706_03762": ["dataset"]},
            model="gpt-5.6-luna",
            client=client,
            refresh_cache=True,
        )

    retained = list_research_facts(db_path, paper_key="1706_03762", limit=10)
    assert [(fact["fact_type"], fact["name"]) for fact in retained] == [
        ("method", "Existing method")
    ]
    with connect(db_path) as conn:
        cache = conn.execute(
            "select status, error from fact_extraction_cache "
            "where paper_key='1706_03762' order by id desc limit 1"
        ).fetchone()
    assert cache["status"] == "failed"
    assert "limitation" in cache["error"]


def test_targeted_retry_prompt_requests_all_five_fact_types(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = FakeFactClient({"facts": []})

    with pytest.raises(FactValidationError, match="all five fact types"):
        extract_research_facts(
            db_path,
            provider_name="openai-compatible",
            paper_key="1706_03762",
            required_fact_types={"1706_03762": ["dataset"]},
            model="gpt-5.6-luna",
            client=client,
            refresh_cache=True,
        )

    prompt = client.calls[0]["prompt"]
    assert "REQUIRED FACT TYPES FOR THIS RETRY" in prompt
    assert all(fact_type in prompt for fact_type in ALLOWED_FACT_TYPES)


def test_openai_compatible_can_target_an_explicit_paper_list(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    add_synthetic_paper(db_path, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = PromptAwareFactClient({
        "Attention Is All You Need": {
            "facts": [{
                "fact_type": "method",
                "name": "Transformer",
                "statement": "The paper uses a Transformer architecture.",
                "evidence_quote": "Attention Is All You Need",
                "evidence_artifact_type": "summary",
                "confidence": 0.8,
                "metadata": {},
            }]
        },
        "Synthetic Control Paper": {
            "facts": [{
                "fact_type": "benchmark",
                "name": "Synthetic benchmark",
                "statement": "The paper defines a controlled benchmark.",
                "evidence_quote": "controlled benchmark for fact extraction",
                "evidence_artifact_type": "summary",
                "confidence": 0.9,
                "metadata": {},
            }]
        },
    })

    result = extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        paper_keys=["synthetic_control", "1706_03762"],
        model="gpt-5.6-luna",
        client=client,
        concurrency=2,
    )

    assert result.papers_seen == 2
    assert result.llm_calls == 2
    assert any("Attention Is All You Need" in prompt for prompt in client.calls)
    assert any("Synthetic Control Paper" in prompt for prompt in client.calls)

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


def test_openai_compatible_client_supports_responses_endpoint(monkeypatch):
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "output": [{
                    "type": "message",
                    "content": [{
                        "type": "output_text",
                        "text": "```json\n{\"facts\": []}\n```",
                    }],
                }]
            }).encode("utf-8")

    def urlopen(request, timeout):
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    result = OpenAICompatibleClient().complete_json(
        model="gpt-5.6-luna",
        base_url="https://opencode.example/v1/responses",
        api_key="secret",
        prompt="paper evidence",
    )

    assert result == {"facts": []}
    request, timeout = requests[0]
    assert request.full_url == "https://opencode.example/v1/responses"
    assert request.get_header("User-agent") == "OpenClaw/1.0"
    assert request.get_header("Accept") == "application/json"
    payload = json.loads(request.data)
    assert payload["input"][0]["role"] == "system"
    assert payload["input"][1]["content"][0]["text"] == "paper evidence"
    assert payload["max_output_tokens"] == 6000
    assert timeout == 300


def test_openai_compatible_client_uses_configured_proxy_for_responses(monkeypatch):
    opened = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"output_text":"{\\\"facts\\\": []}"}'

    class Opener:
        def open(self, request, timeout):
            opened.append((request.full_url, timeout))
            return Response()

    handlers = []

    def build_opener(handler):
        handlers.append(handler)
        return Opener()

    monkeypatch.setenv("AIRESEARCH_FACT_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setattr("urllib.request.build_opener", build_opener)

    result = OpenAICompatibleClient().complete_json(
        model="gpt-5.6-luna",
        base_url="https://opencode.example/v1/responses",
        api_key="secret",
        prompt="paper evidence",
    )

    assert result == {"facts": []}
    assert handlers
    assert opened == [("https://opencode.example/v1/responses", 300)]


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
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)

    with pytest.raises(FactValidationError, match="OPENAI_API_KEY"):
        extract_research_facts(
            db_path,
            provider_name="openai-compatible",
            paper_key="1706_03762",
            model="gpt5.5",
            client=FakeFactClient({"facts": []}),
        )


def test_openai_compatible_uses_unified_opencode_fallback(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    monkeypatch.delenv("AIRESEARCH_FACT_API_KEY", raising=False)
    monkeypatch.delenv("AIRESEARCH_FACT_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "one-secret")
    monkeypatch.setenv("OPENCODE_GO_BASE_URL", "https://opencode.example/v1")
    client = FakeFactClient({"facts": []})

    result = extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        paper_key="1706_03762",
        model="gpt-5.6-luna",
        client=client,
        refresh_cache=True,
    )

    assert result.llm_calls == 1
    assert client.calls[0]["api_key"] == "one-secret"
    assert client.calls[0]["base_url"] == "https://opencode.example/v1/responses"


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

def test_openai_compatible_processes_multiple_papers_with_concurrency(tmp_path: Path, monkeypatch):
    db_path = synced_fixture_db(tmp_path)
    add_synthetic_paper(db_path, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = PromptAwareFactClient({
        "Attention Is All You Need": {
            "facts": [
                {
                    "fact_type": "method",
                    "name": "Transformer",
                    "statement": "The paper uses an attention-based Transformer architecture.",
                    "evidence_quote": "Attention Is All You Need",
                    "evidence_artifact_type": "summary",
                    "confidence": 0.8,
                    "metadata": {},
                }
            ]
        },
        "Synthetic Control Paper": {
            "facts": [
                {
                    "fact_type": "benchmark",
                    "name": "Synthetic benchmark",
                    "statement": "The paper introduces a controlled benchmark for fact extraction.",
                    "evidence_quote": "controlled benchmark for fact extraction",
                    "evidence_artifact_type": "summary",
                    "confidence": 0.9,
                    "metadata": {},
                }
            ]
        },
    })

    result = extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        model="qwen3.7-max",
        client=client,
        concurrency=2,
    )

    assert result.papers_seen == 2
    assert result.llm_calls == 2
    assert result.facts_written == 2
    assert len(client.calls) == 2
    with connect(db_path) as conn:
        statuses = [
            row["status"]
            for row in conn.execute("select status from fact_extraction_cache order by paper_key").fetchall()
        ]
    assert statuses == ["success", "success"]


def test_openai_compatible_concurrent_failure_marks_only_failed_paper_cache(
    tmp_path: Path, monkeypatch
):
    db_path = synced_fixture_db(tmp_path)
    add_synthetic_paper(db_path, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = PromptAwareFactClient(
        {
            "Attention Is All You Need": {
                "facts": [
                    {
                        "fact_type": "method",
                        "name": "Transformer",
                        "statement": "The paper uses an attention-based Transformer architecture.",
                        "evidence_quote": "Attention Is All You Need",
                        "evidence_artifact_type": "summary",
                        "confidence": 0.8,
                        "metadata": {},
                    }
                ]
            }
        },
        failures={"Synthetic Control Paper": FactValidationError("provider failed")},
    )

    with pytest.raises(FactValidationError, match="synthetic_control"):
        extract_research_facts(
            db_path,
            provider_name="openai-compatible",
            model="qwen3.7-max",
            client=client,
            concurrency=2,
        )

    assert len(client.calls) == 2
    facts = list_research_facts(db_path, limit=10)
    assert [row["paper_key"] for row in facts] == ["1706_03762"]
    with connect(db_path) as conn:
        cache_rows = conn.execute(
            """
            select paper_key, status, error from fact_extraction_cache
            order by paper_key
            """
        ).fetchall()
    assert [(row["paper_key"], row["status"]) for row in cache_rows] == [
        ("1706_03762", "success"),
        ("synthetic_control", "failed"),
    ]
    assert "provider failed" in cache_rows[1]["error"]


def test_openai_compatible_warn_policy_keeps_successes_when_one_paper_fails(
    tmp_path: Path, monkeypatch
):
    db_path = synced_fixture_db(tmp_path)
    add_synthetic_paper(db_path, tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = PromptAwareFactClient(
        {
            "Attention Is All You Need": {
                "facts": [
                    {
                        "fact_type": "method",
                        "name": "Transformer",
                        "statement": "The paper uses an attention-based Transformer architecture.",
                        "evidence_quote": "Attention Is All You Need",
                        "evidence_artifact_type": "summary",
                        "confidence": 0.8,
                        "metadata": {},
                    }
                ]
            }
        },
        failures={"Synthetic Control Paper": FactValidationError("provider failed")},
    )

    result = extract_research_facts(
        db_path,
        provider_name="openai-compatible",
        model="qwen3.7-max",
        client=client,
        concurrency=2,
        error_policy="warn",
    )

    assert result.papers_seen == 2
    assert result.llm_calls == 1
    assert result.failed_count == 1
    assert result.failed_errors is not None
    assert "synthetic_control" in result.failed_errors
    facts = list_research_facts(db_path, limit=10)
    assert [row["paper_key"] for row in facts] == ["1706_03762"]
    with connect(db_path) as conn:
        run_row = conn.execute(
            "select status, error from fact_extraction_runs order by id desc limit 1"
        ).fetchone()
        cache_rows = conn.execute(
            """
            select paper_key, status, error from fact_extraction_cache
            order by paper_key
            """
        ).fetchall()
    assert run_row["status"] == "partial_success"
    assert "synthetic_control" in run_row["error"]
    assert [(row["paper_key"], row["status"]) for row in cache_rows] == [
        ("1706_03762", "success"),
        ("synthetic_control", "failed"),
    ]
