# Stage 2D.6 Fact Quality Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable, read-only quality audit for AIResearch `research_facts` so every extraction run can be checked for structural quality before downstream reports use it.

**Architecture:** Implement a small `fact_audit` module that reads `research_facts` joined with `research_fact_provenance`, computes deterministic counters, and classifies hard failures separately from soft warnings. Expose it through an `audit-research-facts` CLI command that prints machine-readable key-value lines and returns non-zero only for hard failures.

**Tech Stack:** Python, SQLite, existing AIResearch DB helpers, pytest.

---

### Task 1: Audit Core

**Files:**
- Create: `airesearch/src/airesearch/fact_audit.py`
- Test: `airesearch/tests/test_fact_audit.py`

- [ ] **Step 1: Write focused unit tests**

Create tests that seed a small SQLite DB with one valid fact and one invalid fact. Assert that the audit counts total rows, paper coverage, fact type coverage, missing evidence quotes, missing source paths, duplicate statements, empty statements, and invalid confidence values.

- [ ] **Step 2: Implement `audit_research_facts`**

Read facts through a single SQL query, compute counters with `collections.Counter`, and return a dataclass with `hard_failures` and `soft_warnings` properties.

- [ ] **Step 3: Run focused tests**

Run: `.venv/bin/pytest tests/test_fact_audit.py -q`

Expected: all tests pass.

### Task 2: CLI Wiring

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Test: `airesearch/tests/test_cli.py`

- [ ] **Step 1: Add parser command**

Add `audit-research-facts` with no required arguments.

- [ ] **Step 2: Print deterministic audit output**

Print one key-value line per summary metric and one line for each warning/failure counter. Return `1` when hard failures exist and `0` otherwise.

- [ ] **Step 3: Add CLI tests**

Assert the valid fixture exits `0` and prints `total_facts=2` for existing fixture-backed facts. Assert a DB with an empty statement exits `1`.

### Task 3: Real DB Verification And Tracker Update

**Files:**
- Modify: `airesearch/PLAN.md`

- [ ] **Step 1: Run the audit against the real DB**

Run: `.venv/bin/python -m airesearch.cli audit-research-facts`

Expected: `total_facts=79`, `hard_failures=0`, and soft warnings only for abstract rows with missing source paths.

- [ ] **Step 2: Run the test suite**

Run: `.venv/bin/pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Update `PLAN.md`**

Record Stage 2D.6 as complete with the real audit result and test count.
