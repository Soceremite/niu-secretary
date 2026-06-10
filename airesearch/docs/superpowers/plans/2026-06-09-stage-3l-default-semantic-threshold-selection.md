# Stage 3L Default Semantic Threshold Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explainable default semantic threshold recommendation to the calibration report.

**Architecture:** Extend `research_cluster_calibration.py` with recommendation policy constants, recommendation dataclass, JSON/Markdown rendering, and CLI output metadata. Keep clustering behavior unchanged.

**Tech Stack:** Python dataclasses, deterministic scoring, pytest, Markdown/JSON exports.

---

## File Map

- Modify: `airesearch/src/airesearch/research_cluster_calibration.py`
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/tests/test_research_cluster_calibration.py`
- Modify: `airesearch/tests/test_cli.py`
- Modify: `airesearch/DEVELOPMENT.md`
- Modify: `airesearch/PLAN.md`

## Tasks

### Task 1: Recommendation Data Model

- [x] Add policy constants and `ClusterThresholdRecommendation`.
- [x] Compute recommendation from calibration points.
- [x] Add recommendation to `ClusterCalibrationReport`.

### Task 2: Export And CLI

- [x] Render recommendation in Markdown.
- [x] Serialize recommendation in JSON.
- [x] Print recommended threshold from CLI.

### Task 3: Verification

- [x] Add focused tests.
- [x] Run real calibration export.
- [x] Run full test suite.
- [x] Update `DEVELOPMENT.md`, `PLAN.md`, and this checklist.
