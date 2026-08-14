# AIResearch Complex Table Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruct complex PDF tables into stable rows, cells, headers, spans, and quality metadata using native AIResearch code.

**Architecture:** Add geometry-only helpers to `layout_parser.py`, feed them PyMuPDF page words at parse time, and preserve the text-spacing parser as a fallback. Keep all output additive so the database, API, deep-reading prompts, and admin frontend continue consuming `table_rows` and rendered table formats.

**Tech Stack:** Python 3.12, PyMuPDF, pytest, JSON/Markdown/HTML layout artifacts.

---

### Task 1: Geometry Reconstruction Contract

**Files:**
- Modify: `airesearch/tests/test_layout_parse.py`
- Modify: `airesearch/src/airesearch/layout_parser.py`

- [ ] Add failing tests for adaptive row clustering, uneven column gaps, sparse cells, multi-row headers, and spanning cells.
- [ ] Implement word normalization, visual-row clustering, row segmentation, column-anchor inference, and cell assignment.
- [ ] Return an empty result when geometry cannot prove at least two rows and two columns.
- [ ] Run focused helper tests.

### Task 2: Parser Integration And Evidence Quality

**Files:**
- Modify: `airesearch/src/airesearch/layout_parser.py`
- Modify: `airesearch/tests/test_layout_parse.py`

- [ ] Read `page.get_text("words", sort=True)` once per page.
- [ ] Attach geometry output to table blocks before page cleanup and enrichment.
- [ ] Preserve whitespace fallback and record its lower confidence explicitly.
- [ ] Include reconstruction confidence and reasons in table evidence scoring.
- [ ] Add summary counters for geometry-reconstructed and fallback tables.
- [ ] Verify generated PDF structure JSON and Markdown.

### Task 3: Consumer And Documentation Regression

**Files:**
- Modify: `airesearch/SKILL.md`
- Modify: `airesearch/DEVELOPMENT.md`
- Modify: `docs/airesearch-api.md`

- [ ] Document the additive metadata contract and confidence semantics.
- [ ] Run layout, service, workflow, blog, API, and CLI tests.
- [ ] Build the Vue frontend to catch contract regressions.
- [ ] Restart the API, verify health, and inspect one generated table artifact.
