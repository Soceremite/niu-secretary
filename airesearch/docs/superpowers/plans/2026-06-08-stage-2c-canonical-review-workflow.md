# Stage 2C.1 Canonical Review Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CLI review controls so only approved canonical papers are exported for Stage 2C ingestion.

**Architecture:** Reuse `candidate_papers.status` for review state. Add pure SQLite helpers in `canonical_candidates.py`, expose them through `cli.py`, and cover behavior with pytest.

**Tech Stack:** Python, SQLite, argparse, pytest.

---

## File Structure

- Modify: `airesearch/src/airesearch/canonical_candidates.py` for review state helpers and approved export.
- Modify: `airesearch/src/airesearch/cli.py` for review commands.
- Modify: `airesearch/tests/test_canonical_candidates.py` for review workflow tests.
- Modify: `airesearch/tests/test_cli.py` for CLI tests.
- Modify: `airesearch/PLAN.md` for Stage 2C.1 status.

## Task 1: Review Helpers

**Files:**
- Modify: `airesearch/src/airesearch/canonical_candidates.py`
- Modify: `airesearch/tests/test_canonical_candidates.py`

- [ ] Add tests for `set_canonical_status`, `select_top_canonical_candidates`, and `export_approved_candidates`.
- [ ] Implement allowed status validation.
- [ ] Implement single-row status update that returns `False` for unknown keys.
- [ ] Implement top-N selection that skips rejected rows and already selected rows.
- [ ] Implement approved-only export.
- [ ] Run `.venv/bin/pytest tests/test_canonical_candidates.py -v`.

## Task 2: CLI

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/tests/test_cli.py`

- [ ] Add parser commands for status update, top-N selection, and approved export.
- [ ] Add CLI tests for the happy path and unknown-key failure.
- [ ] Run `.venv/bin/pytest tests/test_cli.py -v`.

## Task 3: Verification And Commit

**Files:**
- Modify: `airesearch/PLAN.md`

- [ ] Update project plan to record Stage 2C.1 review workflow.
- [ ] Run `.venv/bin/pytest -v`.
- [ ] Run a real-db smoke command that selects a tiny sample and exports approved candidates.
- [ ] Commit all Stage 2C.1 files.
