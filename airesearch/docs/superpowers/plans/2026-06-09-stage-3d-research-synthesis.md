# Stage 3D Research Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic research synthesis report that turns audited paper cards, facts, gap analysis, and code-link coverage into Markdown/JSON outputs.

**Architecture:** Reuse `build_research_digest` and `build_gap_analysis` instead of issuing new SQL queries. Keep synthesis as a pure export module with dataclasses, Markdown rendering, JSON serialization, and one CLI command.

**Tech Stack:** Python dataclasses, existing SQLite-backed AIResearch builders, argparse CLI, pytest.

---

## File Structure

- Create: `airesearch/src/airesearch/research_synthesis.py`
  - Build synthesis dataclasses from digest and gap analysis.
  - Render Markdown and JSON payloads.
  - Export Markdown/JSON files.
- Modify: `airesearch/src/airesearch/cli.py`
  - Import `export_research_synthesis`.
  - Add `generate-research-synthesis`.
  - Handle `DigestInputError` with exit code 2.
- Create: `airesearch/tests/test_research_synthesis.py`
  - Unit tests for builder, Markdown, JSON export, and empty input.
- Modify: `airesearch/tests/test_cli.py`
  - CLI coverage for Markdown/JSON and empty input.
- Modify: `airesearch/PLAN.md`
  - Record Stage 3D status, real export stats, and test count.

## Tasks

### Task 1: Add Synthesis Module

**Files:**
- Create: `airesearch/src/airesearch/research_synthesis.py`

- [x] Define dataclasses for `CoverageBand`, `ExtractionTarget`, `SynthesisNote`, and `ResearchSynthesis`.
- [x] Implement `build_research_synthesis(db_path: Path) -> ResearchSynthesis`.
- [x] Implement coverage banding thresholds: strong `>= 0.8`, moderate `>= 0.5`, weak `< 0.5`.
- [x] Implement deterministic extraction target priority score.
- [x] Implement `render_markdown`, `research_synthesis_to_dict`, and `export_research_synthesis`.

### Task 2: Add Module Tests

**Files:**
- Create: `airesearch/tests/test_research_synthesis.py`

- [x] Reuse fixture-backed synced fact DB helper.
- [x] Test fixture coverage band classification.
- [x] Test Markdown contains snapshot, weak coverage, code availability, and next extraction targets.
- [x] Test JSON export fields.
- [x] Test empty `paper_cards` raises `DigestInputError`.

### Task 3: Add CLI Command And Tests

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/tests/test_cli.py`

- [x] Add parser command `generate-research-synthesis --out PATH --format markdown|json`.
- [x] Add handler output: `research_synthesis_exported={papers} facts={facts} targets={targets} format={format} out={out}`.
- [x] Add CLI tests for Markdown and JSON export.
- [x] Add CLI test for empty `paper_cards`.

### Task 4: Verify, Export, And Update Tracker

**Files:**
- Modify: `airesearch/PLAN.md`
- Create: `airesearch/exports/research-synthesis-current.md`
- Create: `airesearch/exports/research-synthesis-current.json`

- [x] Run focused tests: `.venv/bin/pytest tests/test_research_synthesis.py tests/test_cli.py -q`.
- [x] Run full suite: `.venv/bin/pytest -q`.
- [x] Generate real Markdown and JSON exports.
- [x] Validate JSON with `python3 -m json.tool`.
- [x] Update `PLAN.md` with real counts and test result.

## Self-Review

- Spec coverage: all design sections map to tasks above.
- Placeholder scan: no placeholder tasks remain.
- Type consistency: CLI and module names use `research_synthesis` / `generate-research-synthesis` consistently.
