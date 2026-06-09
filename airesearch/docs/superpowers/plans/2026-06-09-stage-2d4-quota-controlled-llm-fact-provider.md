# Stage 2D.4 Quota-Controlled LLM Fact Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real quota-controlled OpenAI-compatible research fact provider that can use OpenAI, Alibaba Bailian / DashScope, or any compatible endpoint without spending quota on dry-runs or cached reruns.

**Architecture:** Keep `research_facts` as the canonical fact table and add a dedicated `fact_extraction_cache` table for prompt/response caching. Extend `fact_extraction.py` with evidence-pack construction, model-call abstraction, cache lookup/write, and provider orchestration while preserving the fixture provider path. Wire the new provider into the existing argparse CLI with explicit opt-in flags.

**Tech Stack:** Python standard library, SQLite, argparse, injected fake client tests, optional real OpenAI-compatible HTTPS endpoint through environment variables.

---

## File Structure

- Modify: `airesearch/src/airesearch/schema.sql` - add `fact_extraction_cache` table and indexes.
- Modify: `airesearch/src/airesearch/fact_extraction.py` - add evidence packs, cache helpers, OpenAI-compatible provider flow, and richer result counts.
- Modify: `airesearch/src/airesearch/cli.py` - add `openai-compatible` provider choice and quota-control flags.
- Modify: `airesearch/tests/test_fact_extraction.py` - add no-network module tests using a fake client.
- Modify: `airesearch/tests/test_cli.py` - add CLI coverage for dry-run and provider options.
- Modify: `airesearch/PLAN.md` - mark Stage 2D.4 complete after implementation and record verification.

## Task 1: Add Fact Extraction Cache Schema

**Files:**
- Modify: `airesearch/src/airesearch/schema.sql`
- Test: `airesearch/tests/test_db.py`

- [ ] **Step 1: Write the failing schema test**

Add this test to `tests/test_db.py`:

```python
def test_init_db_creates_fact_extraction_cache(tmp_path):
    from airesearch.db import connect, init_db

    db_path = tmp_path / "airesearch.sqlite3"
    init_db(db_path)

    with connect(db_path) as conn:
        columns = {
            row["name"]
            for row in conn.execute("pragma table_info(fact_extraction_cache)").fetchall()
        }

    assert {
        "id",
        "paper_key",
        "provider_name",
        "extractor_version",
        "model",
        "evidence_hash",
        "prompt_json",
        "response_json",
        "status",
        "error",
        "created_at",
        "updated_at",
    }.issubset(columns)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_db.py::test_init_db_creates_fact_extraction_cache -v
```

Expected: FAIL because `fact_extraction_cache` does not exist.

- [ ] **Step 3: Add the schema**

Add this table near the existing fact extraction tables in `src/airesearch/schema.sql`:

```sql
create table if not exists fact_extraction_cache (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    provider_name text not null,
    extractor_version text not null,
    model text not null,
    evidence_hash text not null,
    prompt_json text not null,
    response_json text not null default '',
    status text not null,
    error text not null default '',
    created_at text not null,
    updated_at text not null,
    unique(paper_key, provider_name, extractor_version, model, evidence_hash)
);

create index if not exists idx_fact_extraction_cache_lookup
on fact_extraction_cache(provider_name, model, evidence_hash, status);
```

- [ ] **Step 4: Run schema test**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_db.py::test_init_db_creates_fact_extraction_cache -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/ubuntu/.openclaw/workspace/niu-secretary add airesearch/src/airesearch/schema.sql airesearch/tests/test_db.py
git -C /home/ubuntu/.openclaw/workspace/niu-secretary commit -m "feat: add fact extraction cache schema"
```

## Task 2: Build Deterministic Evidence Packs

**Files:**
- Modify: `airesearch/src/airesearch/fact_extraction.py`
- Test: `airesearch/tests/test_fact_extraction.py`

- [ ] **Step 1: Write failing evidence-pack tests**

Add imports:

```python
from airesearch.fact_extraction import build_evidence_pack
```

Add tests:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_fact_extraction.py::test_build_evidence_pack_includes_metadata_and_artifacts tests/test_fact_extraction.py::test_build_evidence_pack_hash_is_deterministic -v
```

Expected: FAIL because `build_evidence_pack` does not exist.

- [ ] **Step 3: Implement evidence-pack dataclass and builder**

In `src/airesearch/fact_extraction.py`, add imports:

```python
import hashlib
```

Add dataclass:

```python
@dataclass(frozen=True)
class EvidencePack:
    paper_key: str
    evidence_hash: str
    prompt_text: str
    prompt_json: dict[str, Any]
    artifact_texts: dict[str, str]
```

Add helper functions:

```python
TEXT_ARTIFACT_TYPES = ("summary", "tldr", "notes", "source_tex")


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
        sections.append(f"artifact:{artifact['artifact_type']}\\n{text}")
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
    prompt_text = "\\n\\n".join(sections)
    evidence_hash = hashlib.sha256(stable_json(prompt_json).encode("utf-8")).hexdigest()
    return EvidencePack(
        paper_key=paper_key,
        evidence_hash=evidence_hash,
        prompt_text=prompt_text,
        prompt_json=prompt_json,
        artifact_texts=artifact_texts,
    )
```

- [ ] **Step 4: Run evidence-pack tests**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_fact_extraction.py::test_build_evidence_pack_includes_metadata_and_artifacts tests/test_fact_extraction.py::test_build_evidence_pack_hash_is_deterministic -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/ubuntu/.openclaw/workspace/niu-secretary add airesearch/src/airesearch/fact_extraction.py airesearch/tests/test_fact_extraction.py
git -C /home/ubuntu/.openclaw/workspace/niu-secretary commit -m "feat: build fact extraction evidence packs"
```

## Task 3: Add OpenAI-Compatible Provider Core And Cache

**Files:**
- Modify: `airesearch/src/airesearch/fact_extraction.py`
- Test: `airesearch/tests/test_fact_extraction.py`

- [ ] **Step 1: Write failing provider tests**

Add test helpers:

```python
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
```

Add tests:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_fact_extraction.py -v
```

Expected: FAIL because new parameters, result fields, cache flow, and provider are not implemented.

- [ ] **Step 3: Extend result dataclass and provider parameters**

Change `FactExtractionResult`:

```python
@dataclass(frozen=True)
class FactExtractionResult:
    papers_seen: int
    facts_written: int
    provenance_written: int
    cache_hits: int = 0
    llm_calls: int = 0
    dry_runs: int = 0
```

Extend `extract_research_facts` signature:

```python
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
```

Fixture calls should ignore the new optional fields and continue to return zero cache/LLM/dry-run counters.

- [ ] **Step 4: Implement response validation and cache helpers**

Add:

```python
def validate_provider_response(raw: dict[str, Any]) -> list[FactPayload]:
    if not isinstance(raw, dict):
        raise FactValidationError("provider response root must be an object")
    facts = raw.get("facts")
    if not isinstance(facts, list):
        raise FactValidationError("provider response facts must be a list")
    return [validate_fact(fact) for fact in facts]


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


def upsert_cache_row(conn, *, paper_key: str, provider_name: str, model: str, evidence_hash: str, prompt_json: dict[str, Any], response_json: dict[str, Any] | None, status: str, error: str, now: str) -> None:
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
```

- [ ] **Step 5: Implement real client and provider flow**

Add:

```python
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
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
```

Add a concise `FACT_EXTRACTION_SYSTEM_PROMPT` that requires the JSON shape from the spec, forbids unsupported fact types, and asks for evidence quotes from the provided evidence pack.

In `extract_research_facts`, branch:

```python
if provider_name == "fixture":
    ...
elif provider_name == "openai-compatible":
    return extract_openai_compatible_facts(...)
else:
    raise FactValidationError(...)
```

Implement `extract_openai_compatible_facts` so it:

- Resolves `model = model or os.environ.get("AIRESEARCH_FACT_MODEL") or "gpt-4.1-mini"`.
- Reads `api_key = os.environ.get(api_key_env)`.
- Fails with `FactValidationError(f"{api_key_env} is required for openai-compatible provider")` if missing.
- Builds `EvidencePack` per target paper.
- Writes `dry_run` cache rows and skips client calls when `dry_run=True`.
- Uses successful cache rows when `refresh_cache=False`.
- Calls `client.complete_json(...)` only on cache misses or refresh.
- Validates response before clearing/writing facts.
- Clears prior facts only after a valid fact list exists.
- Records failed cache rows and failed run status on errors.

- [ ] **Step 6: Run module tests**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_fact_extraction.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git -C /home/ubuntu/.openclaw/workspace/niu-secretary add airesearch/src/airesearch/fact_extraction.py airesearch/tests/test_fact_extraction.py
git -C /home/ubuntu/.openclaw/workspace/niu-secretary commit -m "feat: add openai compatible fact provider"
```

## Task 4: Wire CLI Flags

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Test: `airesearch/tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Add:

```python
def test_cli_openai_compatible_dry_run(tmp_path: Path, capsys, monkeypatch):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "openai-compatible",
        "--paper-key",
        "1706_03762",
        "--model",
        "qwen3.7-max",
        "--dry-run",
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "papers_seen=1" in out
    assert "dry_runs=1" in out
    assert "llm_calls=0" in out


def test_cli_openai_compatible_missing_key_returns_2(tmp_path: Path, capsys, monkeypatch):
    db_path = tmp_path / "airesearch.sqlite3"
    paper_db = Path(__file__).parent / "fixtures" / "paperpipe_db"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    main(["--db", str(db_path), "--paper-db", str(paper_db), "sync-paperpipe"])
    capsys.readouterr()

    code = main([
        "--db",
        str(db_path),
        "extract-research-facts",
        "--provider",
        "openai-compatible",
        "--paper-key",
        "1706_03762",
        "--model",
        "gpt5.5",
    ])
    out = capsys.readouterr().out

    assert code == 2
    assert "OPENAI_API_KEY" in out
```

- [ ] **Step 2: Run CLI tests to verify they fail**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_cli.py::test_cli_openai_compatible_dry_run tests/test_cli.py::test_cli_openai_compatible_missing_key_returns_2 -v
```

Expected: FAIL because parser and output do not support the new provider/options.

- [ ] **Step 3: Update parser and command invocation**

In `src/airesearch/cli.py`, change:

```python
fact_extract.add_argument("--provider", choices=["fixture"], required=True)
fact_extract.add_argument("--fixture", type=Path, required=True)
```

to:

```python
fact_extract.add_argument("--provider", choices=["fixture", "openai-compatible"], required=True)
fact_extract.add_argument("--fixture", type=Path)
fact_extract.add_argument("--model")
fact_extract.add_argument("--base-url")
fact_extract.add_argument("--api-key-env", default="OPENAI_API_KEY")
fact_extract.add_argument("--dry-run", action="store_true")
fact_extract.add_argument("--refresh-cache", action="store_true")
fact_extract.add_argument("--max-input-chars", type=int, default=24000)
```

Pass the new args into `extract_research_facts`.

Change output to:

```python
print(
    "papers_seen={seen} facts={facts} provenance={provenance} cache_hits={cache_hits} llm_calls={llm_calls} dry_runs={dry_runs}".format(
        seen=result.papers_seen,
        facts=result.facts_written,
        provenance=result.provenance_written,
        cache_hits=result.cache_hits,
        llm_calls=result.llm_calls,
        dry_runs=result.dry_runs,
    )
)
```

Existing fixture CLI tests can keep asserting `"facts=2"` because the new output still contains it.

- [ ] **Step 4: Run CLI tests**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/ubuntu/.openclaw/workspace/niu-secretary add airesearch/src/airesearch/cli.py airesearch/tests/test_cli.py
git -C /home/ubuntu/.openclaw/workspace/niu-secretary commit -m "feat: expose compatible fact provider cli"
```

## Task 5: Verify Full Suite And Real Dry-Run

**Files:**
- Modify: `airesearch/PLAN.md`

- [ ] **Step 1: Run focused tests**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest tests/test_fact_extraction.py tests/test_cli.py tests/test_db.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full suite**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
.venv/bin/pytest -v
```

Expected: PASS without network access or real API keys.

- [ ] **Step 3: Run real DB dry-run only**

Run:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
OPENAI_API_KEY=dry-run-dummy-key .venv/bin/python -m airesearch.cli extract-research-facts --provider openai-compatible --paper-key 1706_03762 --model gpt5.5 --dry-run
```

Expected:

```text
papers_seen=1 facts=0 provenance=0 cache_hits=0 llm_calls=0 dry_runs=1
```

This spends no model quota because `--dry-run` avoids the client call.

- [ ] **Step 4: Update PLAN.md**

In `airesearch/PLAN.md`:

- Mark Stage 2D.4 complete.
- Record that `openai-compatible` supports OpenAI and compatible endpoints such as Alibaba Bailian / DashScope through `--base-url`, `--api-key-env`, and opaque `--model`.
- Record the test and dry-run verification results.

- [ ] **Step 5: Commit**

```bash
git -C /home/ubuntu/.openclaw/workspace/niu-secretary add airesearch/PLAN.md
git -C /home/ubuntu/.openclaw/workspace/niu-secretary commit -m "docs: record stage 2d4 completion"
```

## Self-Review

- Spec coverage: cache table, dry-run, cache hits, refresh flag, OpenAI-compatible model passthrough, Alibaba Bailian / DashScope endpoint support, missing-key handling, validation, and no-network tests are covered.
- Red-flag scan: no deferred-work markers remain.
- Type consistency: `FactExtractionResult`, `EvidencePack`, `OpenAICompatibleClient.complete_json`, and CLI flags are named consistently across tasks.
