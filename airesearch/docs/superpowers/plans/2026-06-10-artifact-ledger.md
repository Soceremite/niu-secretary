# Artifact Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic artifact ledger for chunks, equations, and citation mentions, then surface it through CLI exports, claim tracing, relation reports, and report bundles.

**Architecture:** Add derived ledger tables to the SQLite schema and a focused `artifact_ledger.py` module that can rebuild rows per paper from registered `paper_artifacts`. Existing report modules consume those stable tables instead of reparsing artifacts.

**Tech Stack:** Python standard library, SQLite, existing `airesearch.db`, existing CLI parser in `src/airesearch/cli.py`, pytest.

---

## File Structure

- Modify `src/airesearch/schema.sql`: add `paper_chunks`, `paper_equations`, `paper_citations`, and indexes.
- Create `src/airesearch/artifact_ledger.py`: extraction, export, render, and ledger lookup helpers.
- Modify `src/airesearch/cli.py`: add `extract-artifact-ledger` and `export-artifact-ledger`.
- Modify `src/airesearch/claim_trace.py`: include deterministic `ledger_matches`.
- Modify `src/airesearch/research_relations.py`: report citation ledger availability from `paper_citations`.
- Modify `src/airesearch/research_bundle.py`: bundle `artifact-ledger.md/json`.
- Create `tests/test_artifact_ledger.py`: unit and integration coverage for ledger extraction/export.
- Modify `tests/test_cli.py`, `tests/test_claim_trace.py`, `tests/test_research_relations.py`, `tests/test_research_bundle.py`: integration coverage.
- Modify `PLAN.md` and `DEVELOPMENT.md`: mark roadmap progress and document commands.

## Task 1: Schema And Ledger Tests

**Files:**
- Modify: `src/airesearch/schema.sql`
- Create: `tests/test_artifact_ledger.py`

- [ ] **Step 1: Write failing tests for schema initialization**

Add a test that initializes a temp DB and verifies all three ledger tables exist.

- [ ] **Step 2: Add schema tables and indexes**

Add the three derived tables with foreign keys to `papers(paper_key)`, unique constraints for idempotency, and indexes on `paper_key`.

- [ ] **Step 3: Run schema test**

Run: `source ./activate.sh && pytest -q tests/test_artifact_ledger.py`

Expected: the schema test passes while later extraction tests are not present yet.

## Task 2: Extraction Module

**Files:**
- Create: `src/airesearch/artifact_ledger.py`
- Modify: `tests/test_artifact_ledger.py`

- [ ] **Step 1: Write failing parser and extraction tests**

Cover:

- Text chunk extraction from `summary.md`.
- Equation extraction from `equations.md`.
- TeX citation extraction from a temp `source.tex` containing `\cite{vaswani2017attention,devlin2019bert}`.
- Idempotent rebuild: running extraction twice keeps row counts stable.

- [ ] **Step 2: Implement `artifact_ledger.py`**

Provide:

- `ArtifactLedgerResult`
- `LedgerReport`
- `extract_artifact_ledger(db_path, limit=None, paper_key=None)`
- `build_artifact_ledger_report(db_path)`
- `export_artifact_ledger(db_path, out_path, output_format="markdown")`
- `find_ledger_matches(conn, paper_key, evidence_text, fallback_text="")`

- [ ] **Step 3: Run extraction tests**

Run: `source ./activate.sh && pytest -q tests/test_artifact_ledger.py`

Expected: all artifact ledger tests pass.

## Task 3: CLI Commands

**Files:**
- Modify: `src/airesearch/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

Add tests for:

- `extract-artifact-ledger` output count line.
- `export-artifact-ledger --format markdown`.
- `export-artifact-ledger --format json`.
- `export-artifact-ledger --format jsonl`.

- [ ] **Step 2: Implement CLI parser and handlers**

Add:

```bash
extract-artifact-ledger --paper-key optional --limit optional
export-artifact-ledger --out PATH --format markdown|json|jsonl
```

- [ ] **Step 3: Run CLI focused tests**

Run: `source ./activate.sh && pytest -q tests/test_artifact_ledger.py tests/test_cli.py`

Expected: focused CLI tests pass without regressing existing CLI coverage.

## Task 4: Claim Trace Integration

**Files:**
- Modify: `src/airesearch/claim_trace.py`
- Modify: `tests/test_claim_trace.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing claim trace tests**

Create ledger rows in the existing claim trace fixture and assert JSON output includes `ledger_matches` with a chunk or equation match. Assert Markdown output includes an `Artifact Ledger Matches` section.

- [ ] **Step 2: Add ledger matches to trace payload**

Use `find_ledger_matches` from `artifact_ledger.py`. Keep the result bounded and deterministic.

- [ ] **Step 3: Run claim trace tests**

Run: `source ./activate.sh && pytest -q tests/test_artifact_ledger.py tests/test_claim_trace.py tests/test_cli.py`

Expected: trace payload and Markdown include ledger matches.

## Task 5: Relation And Bundle Integration

**Files:**
- Modify: `src/airesearch/research_relations.py`
- Modify: `src/airesearch/research_bundle.py`
- Modify: `tests/test_research_relations.py`
- Modify: `tests/test_research_bundle.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing relation tests**

Add citation ledger rows to the relation fixture and assert citation status becomes `citation_ledger_available` with citation row and paper counts.

- [ ] **Step 2: Update relation report**

Replace artifact-type based citation coverage with `paper_citations` based status. Keep warning text clear that true citation edges require citation-key matching.

- [ ] **Step 3: Add bundle artifact**

Insert `artifact-ledger.md/json` in `export_report_bundle` and update expected artifact/report counts.

- [ ] **Step 4: Run report tests**

Run: `source ./activate.sh && pytest -q tests/test_research_relations.py tests/test_research_bundle.py tests/test_cli.py`

Expected: relation status and bundle counts are updated.

## Task 6: Docs, Smoke Tests, And Review

**Files:**
- Modify: `PLAN.md`
- Modify: `DEVELOPMENT.md`

- [ ] **Step 1: Update docs**

Mark the roadmap item complete and document:

```bash
python -m airesearch.cli extract-artifact-ledger
python -m airesearch.cli export-artifact-ledger --out exports/artifact-ledger.md
```

- [ ] **Step 2: Run format and full tests**

Run:

```bash
source ./activate.sh && python -m compileall -q src tests
source ./activate.sh && pytest -q
```

Expected: compile succeeds and full test suite passes.

- [ ] **Step 3: Real DB smoke**

Run:

```bash
source ./activate.sh && python -m airesearch.cli extract-artifact-ledger --limit 5
source ./activate.sh && python -m airesearch.cli export-artifact-ledger --out /tmp/airesearch-artifact-ledger-smoke.md
```

Expected: command prints non-negative counts and writes a Markdown report.

- [ ] **Step 4: Local review**

Review the diff for schema compatibility, idempotency, deterministic ordering, bounded trace output, and docs accuracy.
