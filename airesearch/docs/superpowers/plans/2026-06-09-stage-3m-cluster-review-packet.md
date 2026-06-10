# Stage 3M Cluster Review Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic Markdown/JSON cluster review packet so semantic research clusters can be reviewed before downstream use.

**Architecture:** Add a focused `research_cluster_review.py` module that wraps `build_research_clusters` and converts clusters into review items with default human-editable review fields. Add a CLI command that mirrors the existing research cluster command and uses the live embedding provider only for semantic mode.

**Tech Stack:** Python dataclasses, argparse CLI, existing SQLite-backed AIResearch digest and cluster modules, pytest.

---

## File Map

- Create: `src/airesearch/research_cluster_review.py`
- Create: `tests/test_research_cluster_review.py`
- Modify: `src/airesearch/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `PLAN.md`
- Modify: `DEVELOPMENT.md`

## Tasks

### Task 1: Review Packet Module

- [x] Add review packet dataclasses for packet and item metadata.
- [x] Build review packets from `build_research_clusters`.
- [x] Add deterministic `recommended_status` and rationale helpers.
- [x] Add Markdown and JSON render/export functions.

### Task 2: CLI Wiring

- [x] Add `generate-cluster-review` parser options.
- [x] In semantic mode, instantiate `OpenAICompatibleEmbeddingProvider.from_env()`.
- [x] Catch the same errors as `generate-research-clusters`.
- [x] Print packet summary counts.

### Task 3: Tests

- [x] Unit-test review packet construction and recommended statuses.
- [x] Unit-test Markdown/JSON export payloads.
- [x] CLI-test token mode export.
- [x] CLI-test semantic mode with a fake provider.
- [x] CLI-test missing paper cards failure.

### Task 4: Real Export And Docs

- [x] Run focused tests.
- [x] Run full test suite.
- [x] Generate real semantic Markdown and JSON review packet exports.
- [x] Update `PLAN.md` with real counts and tests.
- [x] Update `DEVELOPMENT.md` with commands and feature log.

