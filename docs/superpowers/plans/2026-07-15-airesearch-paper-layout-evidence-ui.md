# AIResearch Paper Layout Evidence UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Expose layout v2 evidence, OCR status, formulas, reconstructed tables, and experiment signals on public paper detail pages and per-paper static JSON APIs.

**Architecture:** Export a compact `paper-layout-evidence.json` alongside existing bundle artifacts, merge it into the paper payload in `research_site.py`, and render lightweight evidence panels in the existing workbench and immersive detail views. The UI reuses current static HTML/CSS/JS patterns and does not add a new frontend framework.

**Tech Stack:** Python static site generator, SQLite layout tables, HTML/CSS, pytest.

---

### Task 1: Export Compact Layout Evidence

**Files:**
- Modify: `airesearch/src/airesearch/research_bundle.py`
- Test: `airesearch/tests/test_research_bundle.py`

- [x] Add helper functions that read the latest completed `paper_layout_runs` row per paper and collect top equation/table blocks from `paper_layout_blocks`.
- [x] Write `paper-layout-evidence.json` in `export_report_bundle`.
- [x] Include summary counters, OCR stats, formula OCR stats, equations, tables, and experiment hints from dataset/benchmark facts.

### Task 2: Merge Evidence Into Paper Payloads

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`
- Test: `airesearch/tests/test_research_site.py`

- [x] Load `paper-layout-evidence.json` in `_site_payloads`.
- [x] Add a lookup by `paper_key`.
- [x] Attach `layout_evidence` to enriched paper dictionaries and to `_paper_detail_payload`.
- [x] Ensure `api/papers/<slug>.json` contains the same evidence visible on the HTML page.

### Task 3: Render Detail Evidence Panels

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`
- Test: `airesearch/tests/test_research_site.py`

- [x] Add “实验与评测”, “公式”, “表格”, and “OCR / Layout” sections below the hero/facts area in workbench mode.
- [x] Add a compact evidence summary in immersive mode.
- [x] Show empty states when a paper has no parsed formula/table/OCR evidence.
- [x] Render table Markdown in `<pre>` blocks and formulas in safe text blocks to avoid unsafe HTML injection.

### Task 4: Style and Verify

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`
- Test: `airesearch/tests/test_research_site.py`

- [x] Add CSS for dense evidence panels, counters, code-like formula/table blocks, and mobile stacking.
- [x] Run targeted tests for bundle export and site rendering.
- [x] Rebuild the report bundle and static site, then spot-check `world2vlm`, `world-model-self-distillation`, `2606_00269`, and `colavla`.
