# Stage 2D.1 LLM Fact Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add quota-safe, provenance-backed research fact extraction infrastructure for method, dataset, benchmark, claim, and limitation facts.

**Architecture:** Extend SQLite with research fact tables and a fact extraction audit table. Add `fact_extraction.py` with a provider-shaped fixture input path, validation, idempotent persistence, listing, and JSONL export. Wire commands into the existing argparse CLI.

**Tech Stack:** Python, SQLite, argparse, pytest, JSONL.

---

## File Map

- Modify: `src/airesearch/schema.sql` - add fact extraction run, fact, and provenance tables.
- Create: `src/airesearch/fact_extraction.py` - validation, fixture provider, persistence, listing, export.
- Modify: `src/airesearch/cli.py` - add extraction/list/export commands and status counts.
- Create: `tests/test_fact_extraction.py` - module tests.
- Modify: `tests/test_cli.py` - CLI tests.
- Create: `tests/fixtures/fact_extraction_fixture.json` - deterministic fact payload.
- Modify: `PLAN.md` - record Stage 2D.1 completion and next step.

## Tasks

### Task 1: Tests And Fixture

- [ ] Create a JSON fixture with one claim and one method for `1706_03762`, each including evidence quote, artifact type, and confidence.
- [ ] Add module tests for extraction, provenance rows, idempotency, export, and invalid fact type rejection.
- [ ] Add CLI test for fixture extraction, list output, export output, and status count.

### Task 2: Schema

- [ ] Add `fact_extraction_runs`, `research_facts`, and `research_fact_provenance` tables.
- [ ] Add indexes for paper key, fact type, run status, and provenance artifact type.

### Task 3: Module Implementation

- [ ] Implement `FactPayload` validation.
- [ ] Implement `load_fixture_provider(path)`.
- [ ] Implement `extract_research_facts(db_path, provider_name, fixture_path, paper_key=None, limit=None)`.
- [ ] Implement idempotent replacement for facts from the same paper/provider/extractor version.
- [ ] Implement `list_research_facts` and `export_research_facts`.

### Task 4: CLI And Status

- [ ] Add `extract-research-facts`, `list-research-facts`, and `export-research-facts`.
- [ ] Add `research_facts` count to `status`.

### Task 5: Verification

- [ ] Run focused tests.
- [ ] Run full pytest.
- [ ] Run fixture extraction on the real local DB.
- [ ] Export `exports/research-facts-stage-2d1.jsonl`.
- [ ] Update `PLAN.md`.
- [ ] Commit implementation.
