# AIResearch Evidence Rendering Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing formula and table evidence on all public paper pages into readable, safe, responsive content while preserving provenance and fallbacks.

**Architecture:** Extend the bounded static evidence export with normalized table rows and display quality, then render semantic escaped HTML and MathJax formulas in the existing static site generator. Keep full parser artifacts behind the existing admin detail API.

**Tech Stack:** Python, SQLite, static HTML/CSS, MathJax 3, pytest, Playwright, nginx deployment scripts.

---

### Task 1: Lock The Evidence Contract With Tests

**Files:**
- Modify: `airesearch/tests/test_research_bundle.py`
- Modify: `airesearch/tests/test_research_site.py`

- [x] Add a bundle fixture table with structured rows, a quality score, and provenance.
- [x] Assert exported rows are bounded to 12 rows, 8 columns, and bounded cell text.
- [x] Assert `display_quality` distinguishes structured and fallback evidence.
- [x] Add site assertions for semantic table markup, escaped cells, formula MathJax delimiters, and raw fallback.
- [x] Run the focused tests and confirm they fail for the missing behavior.

### Task 2: Export Safe Structured Table Previews

**Files:**
- Modify: `airesearch/src/airesearch/research_bundle.py`

- [x] Normalize `metadata.table_rows` into a bounded JSON-safe matrix.
- [x] Derive `display_quality` from row shape, reconstruction method, and quality score.
- [x] Preserve existing fields so current API consumers remain compatible.
- [x] Run bundle tests and confirm the export contract passes.

### Task 3: Render Reader-Friendly Formula And Table Evidence

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`

- [x] Typeset layout formulas with the page's existing MathJax runtime while preserving escaped fallback text.
- [x] Render exported rows as escaped `<table>` markup with caption, provenance, method, dimensions, and quality.
- [x] Keep a visibly labelled text fallback when rows are unavailable.
- [x] Add responsive overflow, stable card dimensions, and high-contrast quality labels.
- [x] Run site tests and confirm all public API and HTML assertions pass.

### Task 4: Run Cross-Layer Regression

**Files:**
- Modify only when a failing regression proves a scoped fix is required.

- [x] Run layout, bundle, site, blog, and workflow pytest suites.
- [x] Run the complete AIResearch pytest suite.
- [x] Build the Vue frontend.
- [x] Run the platform audit and Playwright admin smoke test.
- [x] Fix scoped regressions and rerun each failing suite.

### Task 5: Rebuild, Inspect, And Deploy

**Files:**
- Generated: `airesearch/exports/mvp-current/bundle/paper-layout-evidence.json`
- Generated: `airesearch/exports/site-current/papers/*.html`
- Generated: `airesearch/exports/site-current/api/papers/*.json`
- Modify: `docs/airesearch-api.md`
- Modify: `airesearch/SKILL.md`
- Modify: `airesearch/DEVELOPMENT.md`

- [x] Rebuild the report bundle and static site for all 209 papers.
- [x] Run desktop and mobile headless DOM/layout checks for `colavla`, `world2vlm`, and `world-model-self-distillation`.
- [x] Verify the admin Layout Evidence Inspector geometry, tabs, close target, and responsive behavior with Playwright.
- [x] Back up the current deployed static site and deploy the verified build.
- [x] Confirm production HTML, JSON, assets, and external-link targets over HTTP.
- [x] Document the enhanced fields, rendering behavior, commands, and residual limitations.

The host Chromium screenshot API hangs even on blank pages, so acceptance used bounding-box, overflow, image-load, interaction, and canvas-independent DOM checks. The existing inspector screenshot was retained; no new screenshot artifact was claimed.

### Task 6: Final Review

**Files:**
- Review the exact diff for files changed by this plan.

- [x] Review data-contract compatibility, HTML escaping, accessibility, and responsive behavior.
- [x] Search for placeholders, accidental absolute paths, unsafe parser HTML, and unrelated edits.
- [x] Rerun the smallest affected tests after review fixes.
- [x] Record completed checks and any remaining model/parser limitations in the handoff.
