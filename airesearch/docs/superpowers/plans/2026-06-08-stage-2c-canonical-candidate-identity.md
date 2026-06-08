# Stage 2C.0 Canonical Candidate Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deduplicated canonical candidate layer so Stage 2C reviews and exports each discovered paper once.

**Architecture:** Keep `research_candidates` as provider/profile discovery evidence. Add canonical tables and a pure local materialization module that derives canonical papers and links from existing candidate rows. Wire this into the CLI with no provider calls and no quota usage.

**Tech Stack:** Python, SQLite, argparse, pytest.

---

## File Structure

- Modify: `airesearch/src/airesearch/schema.sql` for canonical tables and indexes.
- Create: `airesearch/src/airesearch/canonical_candidates.py` for identity extraction, materialization, listing, and export.
- Modify: `airesearch/src/airesearch/cli.py` for three canonical candidate commands and status count.
- Create: `airesearch/tests/test_canonical_candidates.py` for unit coverage.
- Modify: `airesearch/tests/test_cli.py` for CLI smoke coverage.
- Modify: `airesearch/PLAN.md` to mark Stage 2C.0 as in progress/done.

## Task 1: Schema

**Files:**
- Modify: `airesearch/src/airesearch/schema.sql`

- [ ] **Step 1: Add canonical tables**

Add `candidate_papers` and `candidate_paper_links` with `canonical_key` as the stable identity and link rows back to `research_candidates.id`.

- [ ] **Step 2: Add indexes**

Add indexes for `candidate_papers(best_score desc)`, `candidate_papers(status)`, and `candidate_paper_links(research_candidate_id)`.

- [ ] **Step 3: Run schema tests**

Run: `.venv/bin/pytest tests/test_db.py -v`

Expected: PASS.

## Task 2: Canonical Candidate Module

**Files:**
- Create: `airesearch/src/airesearch/canonical_candidates.py`
- Create: `airesearch/tests/test_canonical_candidates.py`

- [ ] **Step 1: Write tests for identity extraction**

Cover arXiv IDs from source IDs and URLs, DOI normalization, Semantic Scholar IDs, OpenAlex IDs, and title/year fallback.

- [ ] **Step 2: Implement identity helpers**

Add `canonical_key_for_candidate(row)` and supporting normalization functions.

- [ ] **Step 3: Write tests for materialization**

Insert duplicate candidates across providers and profiles, materialize, and assert one canonical paper with aggregated profiles and sources.

- [ ] **Step 4: Implement materialization**

Add `materialize_candidate_papers(db_path)` that recomputes links and upserts canonical summaries.

- [ ] **Step 5: Write tests for listing and export**

Assert canonical papers are ordered by `best_score` and exported once.

- [ ] **Step 6: Implement list/export functions**

Add `list_canonical_candidates(db_path, limit)` and `export_canonical_candidates(db_path, limit, out_path)`.

- [ ] **Step 7: Run focused tests**

Run: `.venv/bin/pytest tests/test_canonical_candidates.py -v`

Expected: PASS.

## Task 3: CLI

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/tests/test_cli.py`

- [ ] **Step 1: Add CLI tests**

Add coverage for `dedupe-candidates`, `list-canonical-candidates`, and `export-canonical-candidates`.

- [ ] **Step 2: Wire parser and command handlers**

Import canonical functions, add commands, and print concise counts.

- [ ] **Step 3: Run CLI tests**

Run: `.venv/bin/pytest tests/test_cli.py -v`

Expected: PASS.

## Task 4: Documentation And Verification

**Files:**
- Modify: `airesearch/PLAN.md`

- [ ] **Step 1: Update plan status**

Add Stage 2C.0 canonical candidate identity to completed/current status.

- [ ] **Step 2: Run full tests**

Run: `.venv/bin/pytest -v`

Expected: PASS.

- [ ] **Step 3: Run local dedupe smoke**

Run: `.venv/bin/python -m airesearch.cli dedupe-candidates`

Expected: prints a nonzero canonical paper count without network calls.

- [ ] **Step 4: Commit**

Commit the spec, plan, code, tests, and docs.
