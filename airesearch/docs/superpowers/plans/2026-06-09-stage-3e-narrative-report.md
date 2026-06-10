# Stage 3E Narrative Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic narrative research report that summarizes current corpus support, provisional areas, representative facts, and follow-up actions.

**Architecture:** Build on `build_research_digest` and `build_research_synthesis`; keep report generation pure and export-only. The module owns deterministic finding selection, fixed prose templates, Markdown rendering, JSON serialization, and CLI integration.

**Tech Stack:** Python dataclasses, existing AIResearch Stage 3 builders, argparse CLI, pytest.

---

## File Structure

- Create: `airesearch/src/airesearch/research_narrative.py`
  - Build report dataclasses from digest and synthesis.
  - Select representative findings by confidence and stable tie-breakers.
  - Render Markdown and JSON.
- Modify: `airesearch/src/airesearch/cli.py`
  - Import `export_narrative_report`.
  - Add `generate-narrative-report`.
  - Handle `DigestInputError` with exit code 2.
- Create: `airesearch/tests/test_research_narrative.py`
  - Unit tests for report builder, Markdown, JSON export, and empty input.
- Modify: `airesearch/tests/test_cli.py`
  - CLI tests for Markdown/JSON and empty input.
- Modify: `airesearch/PLAN.md`
  - Record Stage 3E status, real export stats, and test count.

## Tasks

### Task 1: Add Narrative Module

**Files:**
- Create: `airesearch/src/airesearch/research_narrative.py`

- [x] Define `NarrativeFinding`, `PriorityAction`, and `NarrativeReport`.
- [x] Implement `build_narrative_report(db_path: Path) -> NarrativeReport`.
- [x] Implement representative finding selection with two findings per fact type.
- [x] Implement priority action text from top five synthesis extraction targets.
- [x] Implement `render_markdown`, `narrative_report_to_dict`, and `export_narrative_report`.

### Task 2: Add Module Tests

**Files:**
- Create: `airesearch/tests/test_research_narrative.py`

- [x] Reuse fixture-backed synced fact DB setup.
- [x] Test supported/provisional areas and representative finding counts.
- [x] Test Markdown sections and deterministic priority action wording.
- [x] Test JSON export fields.
- [x] Test empty `paper_cards` raises `DigestInputError`.

### Task 3: Add CLI Command And Tests

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/tests/test_cli.py`

- [x] Add parser command `generate-narrative-report --out PATH --format markdown|json`.
- [x] Add handler output: `narrative_report_exported={papers} facts={facts} findings={findings} actions={actions} format={format} out={out}`.
- [x] Add CLI tests for Markdown and JSON export.
- [x] Add CLI test for empty `paper_cards`.

### Task 4: Verify, Export, And Update Tracker

**Files:**
- Modify: `airesearch/PLAN.md`
- Create: `airesearch/exports/research-narrative-current.md`
- Create: `airesearch/exports/research-narrative-current.json`

- [x] Run focused tests: `.venv/bin/pytest tests/test_research_narrative.py tests/test_cli.py -q`.
- [x] Run full suite: `.venv/bin/pytest -q`.
- [x] Generate real Markdown and JSON exports.
- [x] Validate JSON with `python3 -m json.tool`.
- [x] Update `PLAN.md` with real counts and test result.

## Self-Review

- Spec coverage: every output, data model, and testing requirement maps to a task above.
- Placeholder scan: no placeholder tasks remain.
- Type consistency: CLI, module, and export names use `narrative_report` / `generate-narrative-report` consistently.
