# Stage 3O-3P Review Editor And Bundle Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe cluster review status editor and optional reviewed cluster summary inclusion in report bundles.

**Architecture:** Keep JSON editing isolated in `research_review_editor.py`. Extend `research_bundle.py` with an optional review packet path that appends reviewed cluster summary artifacts only when requested.

**Tech Stack:** Python, argparse CLI, JSON files, pytest.

---

### Task 1: Cluster Review Status Editor

**Files:**
- Create: `src/airesearch/research_review_editor.py`
- Modify: `src/airesearch/cli.py`
- Test: `tests/test_research_review_editor.py`, `tests/test_cli.py`

- [x] Add tests for updating one review item, preserving notes when omitted, rejecting invalid status, and rejecting missing cluster ids.
- [x] Implement JSON load/validate/update/write logic.
- [x] Add CLI command `set-cluster-review-status --review-packet ... --cluster-id ... --status ... [--notes ...] --out ...`.
- [x] Run focused tests.

### Task 2: Reviewed Cluster Bundle Integration

**Files:**
- Modify: `src/airesearch/research_bundle.py`
- Modify: `src/airesearch/cli.py`
- Test: `tests/test_research_bundle.py`, `tests/test_cli.py`

- [x] Add tests proving the default bundle remains unchanged.
- [x] Add tests proving `reviewed-clusters.md/json` are included when `review_packet_path` is supplied.
- [x] Add CLI flag `generate-report-bundle --review-packet`.
- [x] Run focused tests and full suite.

### Task 3: Docs And Current Exports

**Files:**
- Modify: `PLAN.md`
- Modify: `DEVELOPMENT.md`
- Optional export refresh under `exports/`

- [x] Document the new command and optional bundle flag.
- [x] Record focused and full test results.
- [x] Do not alter real review statuses unless explicitly requested by the user.
