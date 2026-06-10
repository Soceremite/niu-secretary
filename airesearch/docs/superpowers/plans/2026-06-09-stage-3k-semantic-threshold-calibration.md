# Stage 3K Semantic Threshold Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add semantic cluster threshold calibration and start a maintained developer document for future feature work.

**Architecture:** Reuse Stage 3J embeddings once per calibration run, then evaluate multiple semantic thresholds against the same precomputed vectors. Keep calibration separate from default report bundle generation.

**Tech Stack:** Python dataclasses, argparse, pytest, Markdown/JSON exports.

---

## File Map

- Modify: `airesearch/src/airesearch/research_clusters.py` for precomputed semantic embedding clustering helper.
- Create: `airesearch/src/airesearch/research_cluster_calibration.py` for calibration reports.
- Modify: `airesearch/src/airesearch/cli.py` for `calibrate-research-clusters`.
- Create: `airesearch/tests/test_research_cluster_calibration.py`.
- Modify: `airesearch/tests/test_cli.py`.
- Create: `airesearch/DEVELOPMENT.md`.
- Modify: `airesearch/PLAN.md`.

## Tasks

### Task 1: Reusable Semantic Clustering Helper

- [x] Expose semantic clustering from precomputed embeddings.
- [x] Keep existing `build_research_clusters(... mode="semantic")` behavior unchanged.

### Task 2: Calibration Report Module

- [x] Add calibration dataclasses and default threshold grid.
- [x] Request embeddings once and evaluate all thresholds.
- [x] Render Markdown and JSON exports.

### Task 3: CLI And Developer Doc

- [x] Add `calibrate-research-clusters`.
- [x] Add tests for CLI success and error handling.
- [x] Create `DEVELOPMENT.md` with environment, workflow, and feature log conventions.

### Task 4: Verification

- [x] Run focused tests.
- [x] Run full test suite.
- [x] Run real calibration export with sourced local environment.
- [x] Update `PLAN.md` and this checklist.
