# Stage 3N Reviewed Cluster Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic consumer for edited Stage 3M cluster review packets.

**Architecture:** Add a small pure-file module that reads review packet JSON, validates human statuses, extracts accepted clusters, and exports Markdown/JSON. Wire it to a new CLI command without changing the database or report bundle yet.

**Tech Stack:** Python dataclasses, JSON, argparse, pytest.

---

### Task 1: Reviewed Cluster Summary Module

**Files:**
- Create: `airesearch/src/airesearch/research_review_summary.py`
- Test: `airesearch/tests/test_research_review_summary.py`

- [x] Define allowed statuses: `pending`, `accepted`, `rejected`, `needs_revision`.
- [x] Load a review packet JSON object from disk and validate that `items` is a list.
- [x] Convert accepted items into dataclasses while preserving fact references.
- [x] Count all status buckets and total accepted facts.
- [x] Raise `ClusterReviewSummaryError` on invalid input.

### Task 2: Rendering And Export

**Files:**
- Modify: `airesearch/src/airesearch/research_review_summary.py`
- Test: `airesearch/tests/test_research_review_summary.py`

- [x] Render a Markdown summary with source metadata, status counts, and accepted clusters.
- [x] Serialize a stable JSON object with counts and accepted item payloads.
- [x] Export either Markdown or JSON to the requested path.
- [x] Reject unsupported formats.

### Task 3: CLI Wiring

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Test: `airesearch/tests/test_cli.py`

- [x] Add `summarize-cluster-review`.
- [x] Add `--review-packet`, `--out`, and `--format markdown|json`.
- [x] Print summary counts on success.
- [x] Return exit code 2 on validation errors.

### Task 4: Documentation And Verification

**Files:**
- Modify: `airesearch/DEVELOPMENT.md`
- Modify: `airesearch/PLAN.md`

- [x] Document the new command and JSON validation expectation.
- [x] Update current L3 status and Stage 3N feature log.
- [x] Run focused tests for review summary, review packet, clusters, and CLI.
- [x] Run the full pytest suite.
