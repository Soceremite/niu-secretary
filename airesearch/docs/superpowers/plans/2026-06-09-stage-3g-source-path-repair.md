# Stage 3G Evidence Source-Path Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic dry-run/apply workflow that repairs missing `research_fact_provenance.evidence_source_path` values by matching copied evidence quotes against local text artifacts.

**Architecture:** Create a focused `evidence_repair.py` module for candidate generation, JSONL export, and optional DB updates. Add one CLI command that delegates to the module and prints summary counts; tests build small SQLite fixtures and verify dry-run/apply paths.

**Tech Stack:** Python dataclasses, SQLite, pathlib, JSONL, pytest, argparse.

---

## File Structure

- Create `airesearch/src/airesearch/evidence_repair.py`: matching logic, repair result dataclasses, JSONL export, optional apply.
- Modify `airesearch/src/airesearch/cli.py`: import repair exporter, add `repair-evidence-source-paths` parser and handler.
- Create `airesearch/tests/test_evidence_repair.py`: unit tests for matching, export, apply, no-match.
- Modify `airesearch/tests/test_cli.py`: CLI dry-run and apply coverage.
- Modify `airesearch/PLAN.md`: Stage 3G status and real run counts.

## Tasks

### Task 1: Implement Evidence Repair Module

**Files:**
- Create: `airesearch/src/airesearch/evidence_repair.py`

- [x] **Step 1: Define dataclasses**

Define `EvidenceSourceMatch`, `EvidenceRepairCandidate`, and `EvidenceRepairResult`.

- [x] **Step 2: Add normalized matching**

Implement whitespace-collapsed quote containment matching over `source_tex`, `summary`, `notes`, and `tldr`.

- [x] **Step 3: Add candidate loading**

Query missing-path provenance rows joined to `research_facts`, optionally filtered by `paper_key`.

- [x] **Step 4: Add export/apply orchestration**

Write candidates to JSONL. If `apply=True`, update only `research_fact_provenance.evidence_source_path` for candidates with a recommended path.

### Task 2: Add Unit Tests

**Files:**
- Create: `airesearch/tests/test_evidence_repair.py`

- [x] **Step 1: Test candidate generation**

Build a fixture DB where an evidence quote appears in `summary.md`, then assert the candidate is repairable.

- [x] **Step 2: Test dry-run export**

Assert JSONL is written and the DB row remains unchanged.

- [x] **Step 3: Test apply**

Assert apply updates the provenance row source path and summary counts.

- [x] **Step 4: Test no-match**

Assert a missing-path row with no matching artifact is not repairable and is not applied.

### Task 3: Add CLI Command

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/tests/test_cli.py`

- [x] **Step 1: Add parser and import**

Add `repair-evidence-source-paths` with required `--out`, optional `--paper-key`, and `--apply`.

- [x] **Step 2: Add CLI handler**

Print `evidence_source_path_repair candidates={candidates} repairable={repairable} applied={applied} out={out}`.

- [x] **Step 3: Add CLI tests**

Cover dry-run and apply mode with fixture DB rows.

### Task 4: Run Real Repair Workflow And Update Status

**Files:**
- Create: `airesearch/exports/evidence-source-path-repair-current.jsonl`
- Modify: `airesearch/PLAN.md`

- [x] **Step 1: Run focused tests**

Run `pytest tests/test_evidence_repair.py tests/test_cli.py -q`.

- [x] **Step 2: Run full suite**

Run `pytest -q`.

- [x] **Step 3: Run real dry-run export**

Run `python -m airesearch.cli repair-evidence-source-paths --out exports/evidence-source-path-repair-current.jsonl`.

- [x] **Step 4: Run real apply**

Run `python -m airesearch.cli repair-evidence-source-paths --apply --out exports/evidence-source-path-repair-current.jsonl`.

- [x] **Step 5: Re-run fact audit**

Run `python -m airesearch.cli audit-research-facts` and confirm missing source paths decrease.

- [x] **Step 6: Update reports if audit improves**

Regenerate affected Stage 3 exports and report bundle after repair.

- [x] **Step 7: Update PLAN.md**

Record Stage 3G implementation, real repair counts, audit result, regenerated reports, and test result.

## Self-Review

- The plan covers all Stage 3G design requirements.
- There are no TBD/TODO placeholders.
- Function names and CLI names are consistent across tasks.
