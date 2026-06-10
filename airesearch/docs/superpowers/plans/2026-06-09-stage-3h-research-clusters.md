# Stage 3H Research Clusters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic cross-paper fact clustering and include it in the Stage 3 report bundle.

**Architecture:** Implement a new `research_clusters.py` module that builds on `build_research_digest()` and mirrors the existing Stage 3 report API: build, render Markdown, serialize JSON, and export. Add a CLI subcommand and register the report in `research_bundle.py`.

**Tech Stack:** Python dataclasses, SQLite-backed existing digest reader, pytest, JSON/Markdown file exports.

---

## File Map

- Create: `src/airesearch/research_clusters.py` for clustering dataclasses, deterministic tokenization, build/render/serialize/export functions.
- Create: `tests/test_research_clusters.py` for module-level tests with a synthetic two-paper fixture.
- Modify: `src/airesearch/cli.py` to add `generate-research-clusters`.
- Modify: `src/airesearch/research_bundle.py` to export `clusters.md` and `clusters.json`.
- Modify: `tests/test_cli.py` to cover the new CLI command and updated bundle counts.
- Modify: `tests/test_research_bundle.py` to include cluster artifacts.
- Modify: `PLAN.md` to record Stage 3H completion after verification.

## Tasks

### Task 1: Add Research Clusters Module

**Files:**

- Create: `src/airesearch/research_clusters.py`
- Test: `tests/test_research_clusters.py`

- [x] Define dataclasses for cluster fact references, clusters, singleton summaries, and the full report.
- [x] Implement deterministic tokenization with a fixed stopword list and alphanumeric tokens.
- [x] Implement greedy per-fact-type Jaccard clustering with threshold `0.22`.
- [x] Add Markdown renderer, dictionary serializer, and export function.

### Task 2: Add CLI Command

**Files:**

- Modify: `src/airesearch/cli.py`
- Modify: `tests/test_cli.py`

- [x] Import `export_research_clusters`.
- [x] Add `generate-research-clusters --out --format markdown|json`.
- [x] Print `research_clusters_exported={papers} facts={facts} clusters={clusters} singletons={singletons} format={format} out={out}`.
- [x] Return exit code `2` for `DigestInputError`.

### Task 3: Add Bundle Integration

**Files:**

- Modify: `src/airesearch/research_bundle.py`
- Modify: `tests/test_research_bundle.py`
- Modify: `tests/test_cli.py`

- [x] Import `export_research_clusters`.
- [x] Add bundle artifacts `clusters.md` and `clusters.json`.
- [x] Add manifest extra counts: `cluster_count`, `clustered_fact_count`, and `singleton_count`.
- [x] Update expected report count and artifact count from 5/12 to 6/14.

### Task 4: Verify And Export

**Files:**

- Modify: `PLAN.md`
- Create generated exports under `exports/`

- [x] Run focused tests for research clusters, bundle, and CLI.
- [x] Run the full test suite.
- [x] Generate Markdown and JSON cluster exports against the real database.
- [x] Regenerate the report bundle.
- [x] Validate generated JSON.
- [x] Update `PLAN.md` with real counts and test results.

