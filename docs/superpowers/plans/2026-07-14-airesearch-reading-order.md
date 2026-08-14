# AIResearch Reading Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add native geometry-based reading-order reconstruction to AIResearch layout v2.

**Architecture:** Extend `layout_parser.py` with a post-enrichment reading-order pass that groups captions with visuals, uses cross-column anchors to segment pages, and records auditable metadata. Surface summary and capability fields through `layout_parse.py`, `admin_server.py`, and the Vue admin pages.

**Tech Stack:** Python, PyMuPDF, SQLite-backed layout artifacts, Vue 3 admin UI, pytest.

---

### Task 1: Parser Reading Order Pass

**Files:**
- Modify: `airesearch/src/airesearch/layout_parser.py`
- Test: `airesearch/tests/test_layout_parse.py`

- [x] Add `_block_bbox`, `_reading_region_for_bbox`, `_group_bbox`, and `_visual_caption_groups`.
- [x] Add `_apply_reading_order(page_blocks, page_width, page_height)`.
- [x] Call `_apply_reading_order()` after `_enrich_page_blocks()` and before Markdown/content JSON writing.
- [x] Write `metadata.reading_order_*` fields on every block.
- [x] Write `summary.reading_order`.
- [x] Add tests for cross-column anchors and caption adjacency.

### Task 2: API And Admin Contract

**Files:**
- Modify: `airesearch/src/airesearch/layout_parse.py`
- Modify: `airesearch/src/airesearch/admin_server.py`
- Modify: `server/capabilities.py`

- [x] Add reading-order capability booleans.
- [x] Add compact reading-order counters to latest layout run summaries.
- [x] Add per-paper compact reading-order fields for list badges.
- [x] Update capability descriptions.

### Task 3: Frontend Indicators

**Files:**
- Modify: `web/src/modules/admin/AdminAIResearchPage.vue`
- Modify: `web/src/modules/admin/AdminAIResearchBlogsPage.vue`

- [x] Show multi-column and reading-order warning badges in the paper list.
- [x] Show reading-order metrics in layout detail counts.
- [x] Show reading-order metrics and capability tags in blog evidence preflight.

### Task 4: Documentation And Verification

**Files:**
- Modify: `airesearch/SKILL.md`
- Modify: `airesearch/DEVELOPMENT.md`
- Modify: `docs/airesearch-api.md`
- Create: `docs/superpowers/specs/2026-07-14-airesearch-reading-order-design.md`

- [x] Update current capability boundaries.
- [x] Document new fields and remaining limitations.
- [x] Run focused parser tests.
- [x] Run broader regression tests and frontend build.
- [x] Deploy and smoke health check.
