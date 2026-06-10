# Cross-Paper Relations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic cross-paper relation summaries for shared code repositories, shared datasets, and citation-ledger coverage gaps.

**Architecture:** Add a focused `research_relations.py` module that builds on `build_research_digest` and existing code-link/fact data. Wire the report into `cli.py` and `research_bundle.py` using the same Markdown/JSON export pattern as the current reports. Keep all behavior read-only and schema-free.

**Tech Stack:** Python dataclasses, SQLite via existing digest/report modules, pytest, existing AIResearch CLI/report bundle conventions.

---

### Task 1: Relation Report Module

**Files:**
- Create: `src/airesearch/research_relations.py`
- Create: `tests/test_research_relations.py`

- [ ] **Step 1: Add tests**

Create a two-paper fixture DB in the test file. Sync the existing fixture paper, insert a synthetic second paper/card with the same GitHub repo and same dataset fact name, then assert `build_research_relations` emits one shared repo relation and one shared dataset relation.

- [ ] **Step 2: Implement data model**

Add dataclasses for `RelationPaperRef`, `RelationEvidence`, `RelationGroup`, `CitationLedgerStatus`, and `ResearchRelations`.

- [ ] **Step 3: Implement builders**

Implement normalized code grouping by repo/owner/host, dataset grouping by normalized dataset label, and citation status from artifact types. Include only groups with at least two distinct papers in relation lists.

- [ ] **Step 4: Implement render/export**

Add `render_markdown`, `research_relations_to_dict`, and `export_research_relations`.

### Task 2: CLI And Bundle Integration

**Files:**
- Modify: `src/airesearch/cli.py`
- Modify: `src/airesearch/research_bundle.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_research_bundle.py`

- [ ] **Step 1: Add CLI parser and handler**

Add `generate-research-relations --out --format markdown|json`, call `export_research_relations`, and print relation counts.

- [ ] **Step 2: Add bundle artifact**

Add `relations.md` and `relations.json` to `export_report_bundle` after map and before gap analysis. Add manifest extra counts.

- [ ] **Step 3: Update tests**

Update bundle expected files and artifact counts. Add CLI test for Markdown/JSON relation export.

### Task 3: Docs And Verification

**Files:**
- Modify: `PLAN.md`
- Modify: `DEVELOPMENT.md`

- [ ] **Step 1: Update roadmap and command inventory**

Mark the cross-paper relation summary item complete. Document `generate-research-relations`.

- [ ] **Step 2: Run focused tests**

Run:

```bash
source ./activate.sh && pytest -q tests/test_research_relations.py tests/test_research_bundle.py tests/test_cli.py
```

- [ ] **Step 3: Run full suite**

Run:

```bash
source ./activate.sh && pytest -q
```

- [ ] **Step 4: Run diff whitespace check**

Run:

```bash
git diff --check -- src/airesearch/research_relations.py src/airesearch/cli.py src/airesearch/research_bundle.py tests/test_research_relations.py tests/test_research_bundle.py tests/test_cli.py PLAN.md DEVELOPMENT.md docs/superpowers/specs/2026-06-10-cross-paper-relations-design.md docs/superpowers/plans/2026-06-10-cross-paper-relations.md
```
