# Stage 2D.4 Quota-Controlled LLM Fact Provider Design

## Context

Stage 2D.1 created the `research_facts`, `research_fact_provenance`, and `fact_extraction_runs` substrate with a deterministic fixture provider. Stage 2D.2 and 2D.3 added deterministic GitHub project extraction and exposed those links through Paper Cards and the knowledge graph.

The remaining L2 gap is real fact extraction from paper evidence. We need a provider that can extract method, dataset, benchmark, claim, and limitation facts from paper metadata and artifacts without spending model quota on every rerun.

## Decision

Add an OpenAI-compatible fact extraction provider behind explicit CLI selection. The provider will be quota-controlled by default:

- No real LLM call happens unless the user passes `--provider openai-compatible`.
- `--dry-run` builds and records the evidence pack without calling the model.
- Calls are cached by `(paper_key, provider_name, extractor_version, model, evidence_hash)`.
- Cached successful responses are reused unless `--refresh-cache` is passed.
- Existing `--limit` and new `--max-input-chars` bound runtime and spend.
- Fixture extraction remains available and remains the default test path.

The provider name is `openai-compatible` because it should work with OpenAI and compatible endpoints configured through environment variables. The implementation will not hard-code a single vendor-specific client into the extraction core.

## Inputs

The evidence pack for each paper will use local data only:

- `papers` row: title, authors, year, venue, identifiers, and `meta_json` abstract-like fields.
- `paper_cards` row when available.
- `paper_artifacts` rows for text artifacts.
- Artifact text from `summary.md`, `tldr.md`, `notes.md`, and `source.tex` when present.
- Existing `paper_code_links` rows as optional context, not as facts.

The extractor will prefer concise sources first: metadata, summary, TLDR, notes, then bounded TeX excerpts. TeX is capped by `--max-input-chars` so long source files do not create uncontrolled prompts.

## Prompt Contract

The model must return a JSON object with this shape:

```json
{
  "facts": [
    {
      "fact_type": "method",
      "name": "short optional name",
      "statement": "one grounded factual statement",
      "evidence_quote": "short quote copied from the evidence pack",
      "evidence_artifact_type": "summary",
      "confidence": 0.8,
      "metadata": {
        "rationale": "short reason"
      }
    }
  ]
}
```

Accepted fact types stay unchanged: `method`, `dataset`, `benchmark`, `claim`, and `limitation`.

Validation rules:

- The root must be an object containing `facts`.
- `facts` must be a list.
- Each fact must pass the existing `FactPayload` validation.
- `evidence_quote` must be nonempty and should appear in the evidence pack. If an exact match cannot be enforced because the model shortened punctuation or whitespace, the fact is accepted only when the artifact type is present and the quote has meaningful overlap with that artifact text.
- Invalid provider responses fail the run and are recorded in `fact_extraction_runs.error`; partial writes for the failed paper are avoided.

## Storage

Add a cache table for real provider responses:

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
```

This cache is separate from Stage 2B provider query cache because it protects LLM extraction calls, not discovery API calls.

`research_facts` remains the canonical fact table. Cached LLM responses are parsed and written through the same validation and provenance path used by the fixture provider.

## CLI

Extend `extract-research-facts`:

```bash
airesearch extract-research-facts \
  --provider openai-compatible \
  --paper-key 2606_07342 \
  --model gpt-4.1-mini \
  --max-input-chars 24000
```

New options:

- `--provider fixture|openai-compatible`
- `--fixture PATH`, required only for `fixture`
- `--model MODEL`, defaults to `AIRESEARCH_FACT_MODEL` or a conservative configured default.
- `--base-url URL`, defaults to `OPENAI_BASE_URL` when set.
- `--api-key-env NAME`, defaults to `OPENAI_API_KEY`.
- `--dry-run`, builds cache rows with prompts and status `dry_run` but makes no network call.
- `--refresh-cache`, ignores successful cache rows and calls again.
- `--max-input-chars N`, defaults to 24000.

The command output should distinguish real calls from cache hits:

```text
papers_seen=1 facts=5 provenance=5 cache_hits=0 llm_calls=1 dry_runs=0
```

## Environment

The real provider reads credentials only from environment variables. API keys are never printed, written to git-tracked files, or stored in SQLite.

Supported variables:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `AIRESEARCH_FACT_MODEL`

If the selected provider lacks a required API key, the command exits with code 2 and records a clear validation error.

## Failure Handling

- Missing API key: fail before building network requests.
- Network/API failure: record cache row with `status='failed'`, store the sanitized error message, and mark the extraction run failed.
- Invalid JSON: record failure and do not write facts for that paper.
- Invalid fact payload: record failure and do not write facts for that paper.
- Cache hit with valid prior response: write facts from cache without calling the provider.
- Dry run: create/update cache prompt rows and return `facts=0`.

## Testing

Tests must not call the network. They will use a fake OpenAI-compatible transport injected into the provider.

Required coverage:

- Evidence pack includes metadata and artifact text with deterministic `evidence_hash`.
- Dry run writes cache rows and does not call the fake client.
- Cache hit reuses response and does not call the fake client.
- Refresh cache calls the fake client even when a successful cache row exists.
- Missing API key fails with a validation error.
- Valid fake provider response writes `research_facts` and provenance.
- Invalid fake JSON/invalid fact type fails without partial fact writes.
- Existing fixture provider behavior remains unchanged.

## Out Of Scope

- Report generation and L3 synthesis.
- Automatic LLM extraction during ingestion or discovery.
- Repository validation against GitHub.
- Full PDF OCR or figure/table extraction beyond existing paperpipe artifacts.
- Vendor-specific advanced OpenAI features that would make compatible endpoints harder to use.

## Acceptance Criteria

- `extract-research-facts --provider fixture` still passes existing tests.
- `extract-research-facts --provider openai-compatible --dry-run --limit 1` creates cache rows and spends no model quota.
- A fake OpenAI-compatible client can produce facts that pass validation and are persisted with provenance.
- Re-running with the same evidence hash uses cache and makes zero LLM calls.
- Full test suite passes without network access or real API keys.
