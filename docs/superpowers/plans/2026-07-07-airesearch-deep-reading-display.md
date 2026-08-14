# AIResearch Deep Reading Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make paper deep-reading links behave like a focused blog reading page so `#deep-reading` does not show the Workbench or Immersive controls.

**Architecture:** Keep the existing static paper detail page and mode-switching JavaScript. Add explicit deep-reading-only markup/state so hash links render the blog section as the primary view and hide the workbench/immersive switcher in the visible UI.

**Tech Stack:** Python static-site generator, pytest, vanilla HTML/CSS/JavaScript.

---

### Task 1: Test The Deep Reading State

**Files:**
- Modify: `airesearch/tests/test_research_site.py`

- [ ] **Step 1: Extend the existing blog-detail test**

Add assertions to `test_paper_detail_renders_single_deep_reading_tab_with_inline_local_images` that verify:

```python
assert 'data-paper-deep-reading-only-label="深度解读"' in html_text
assert "paper-detail-deep-reading-back" in html_text
assert "paper-detail.is-deep-reading-only .paper-mode-toggle" in site_css
assert "paper-detail.is-deep-reading-only .paper-mode-workbench" in site_css
assert "paper-detail.is-deep-reading-only .paper-mode-immersive" in site_css
```

- [ ] **Step 2: Run the targeted test**

Run:

```bash
cd airesearch && .venv/bin/python -m pytest tests/test_research_site.py::test_paper_detail_renders_single_deep_reading_tab_with_inline_local_images -q
```

Expected before implementation: fail on missing deep-reading-only label or CSS selectors.

### Task 2: Implement Focused Deep Reading Markup

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`

- [ ] **Step 1: Add a focused header inside the paper detail topbar**

In `_paper_detail_page`, render a `paper-detail-deep-reading-back` link and a hidden label that can become visible when the hash is `#deep-reading`.

- [ ] **Step 2: Hide non-blog UI in deep-reading-only mode**

Extend CSS so `.paper-detail.is-deep-reading-only` hides `.paper-mode-toggle`, `.paper-mode-workbench`, and `.paper-mode-immersive`, and shows the deep-reading back/label row.

- [ ] **Step 3: Keep JavaScript hash routing**

Keep `modeFromHash()` and `deepReadingOnly` logic so `#deep-reading` applies the CSS state on initial load and hash changes.

- [ ] **Step 4: Run the targeted test again**

Run:

```bash
cd airesearch && .venv/bin/python -m pytest tests/test_research_site.py::test_paper_detail_renders_single_deep_reading_tab_with_inline_local_images -q
```

Expected after implementation: pass.

### Task 3: Regression Check

**Files:**
- Test: `airesearch/tests/test_research_site.py`

- [ ] **Step 1: Run the relevant test file**

Run:

```bash
cd airesearch && .venv/bin/python -m pytest tests/test_research_site.py -q
```

Expected: pass.

- [ ] **Step 2: Report unrelated dirty files**

Do not revert unrelated Hermes changes. Summarize that this task only touched the focused plan, `research_site.py`, and `test_research_site.py`.
