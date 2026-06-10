# Stage 3F Report Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic `generate-report-bundle` CLI command that exports all Stage 3 reports, a JSON manifest, and a Markdown index into one directory.

**Architecture:** Implement a thin `research_bundle.py` orchestration module that reuses the existing Stage 3 export functions. The CLI owns argument parsing and summary printing, while the module owns file layout, manifest serialization, and index rendering.

**Tech Stack:** Python dataclasses, SQLite-backed existing AIResearch report builders, pytest, argparse.

---

## File Structure

- Create `airesearch/src/airesearch/research_bundle.py`: data model, bundle export orchestration, manifest JSON, and index Markdown.
- Modify `airesearch/src/airesearch/cli.py`: import bundle exporter, add `generate-report-bundle`, handle `DigestInputError`, print summary.
- Create `airesearch/tests/test_research_bundle.py`: fixture-backed unit coverage.
- Modify `airesearch/tests/test_cli.py`: CLI success and empty-input failure coverage.
- Modify `airesearch/PLAN.md`: status and real export summary.

## Tasks

### Task 1: Add Bundle Module

**Files:**
- Create: `airesearch/src/airesearch/research_bundle.py`
- Test: `airesearch/tests/test_research_bundle.py`

- [x] **Step 1: Define dataclasses and constants**

Create `ReportArtifact`, `ReportBundle`, `BUNDLE_ARTIFACT_COUNT`, and output filename metadata.

- [x] **Step 2: Implement report exports**

Call each existing report exporter for Markdown and JSON. Build `ReportArtifact` objects from the Markdown export results.

- [x] **Step 3: Implement manifest and index rendering**

Write stable, sorted JSON for `manifest.json`. Write an `index.md` with bundle counts and report links.

### Task 2: Add Unit Tests

**Files:**
- Create: `airesearch/tests/test_research_bundle.py`

- [x] **Step 1: Build fixture-backed database**

Reuse the same sync, paper-card extraction, and fixture fact extraction pattern used by Stage 3E tests.

- [x] **Step 2: Test successful bundle export**

Assert all twelve files exist, manifest counts are correct, five report artifacts are listed, and index content links the reports.

- [x] **Step 3: Test empty input failure**

Assert `export_report_bundle` raises `DigestInputError` when `paper_cards` is empty.

### Task 3: Add CLI Command

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/tests/test_cli.py`

- [x] **Step 1: Add parser and import**

Import `export_report_bundle`, add `generate-report-bundle`, and require `--out-dir`.

- [x] **Step 2: Add CLI handler**

Catch `DigestInputError`, return code `2`, and print `report_bundle_exported={artifacts} papers={papers} facts={facts} out_dir={out_dir}` on success.

- [x] **Step 3: Add CLI tests**

Cover success with fixture facts and failure on an empty DB.

### Task 4: Generate Real Bundle And Update Status

**Files:**
- Create: `airesearch/exports/research-report-current/*`
- Modify: `airesearch/PLAN.md`

- [x] **Step 1: Run focused tests**

Run `pytest tests/test_research_bundle.py tests/test_cli.py -q`.

- [x] **Step 2: Run full suite**

Run `pytest -q`.

- [x] **Step 3: Generate real bundle**

Run `python -m airesearch.cli generate-report-bundle --out-dir exports/research-report-current`.

- [x] **Step 4: Validate manifest JSON**

Run `python3 -m json.tool exports/research-report-current/manifest.json`.

- [x] **Step 5: Update PLAN.md**

Record Stage 3F status, real counts, generated bundle path, and test result.

## Self-Review

- The plan covers all requirements in the Stage 3F design.
- There are no TBD/TODO placeholders.
- Function names and CLI names are consistent across tasks.
