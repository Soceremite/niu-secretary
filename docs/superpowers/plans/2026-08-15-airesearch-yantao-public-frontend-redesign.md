# AIResearch Yantao-Style Public Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign every public AIResearch page with one Yantao-inspired Memphis research-blog visual system while preserving public URLs, static JSON APIs, research content, and all administration pages.

**Architecture:** The public site is generated from `airesearch/src/airesearch/research_site.py`; page HTML, `SITE_CSS`, and `SITE_JS` are emitted into `exports/site-current/`. The redesign remains CSS-first, introducing scoped shared theme primitives and limited semantic classes in the existing HTML generators. No new frontend runtime, routes, API payloads, or administration UI are introduced.

**Tech Stack:** Python 3 static-site generator, generated HTML/CSS/vanilla JavaScript, pytest, Playwright, nginx static deployment.

---

## File Structure

- Modify: `airesearch/src/airesearch/research_site.py`
  - Owns public page shell, page-specific markup, `SITE_CSS`, `SITE_JS`, cache asset version, and static output.
- Modify: `airesearch/tests/test_research_site.py`
  - Owns generated-page HTML/CSS/JS structural regression tests.
- Reference: `docs/superpowers/specs/2026-08-15-airesearch-yantao-public-frontend-redesign-design.md`
  - Defines visual scope, exclusions, phases, and acceptance criteria.
- Generated only, never manually edit: `airesearch/exports/mvp-current/bundle/`, `airesearch/exports/site-current/`, `/var/www/html/niu-secretary/airesearch/`.

## Guardrails

- Do not edit `web/`, `admin_server.py`, admin routes, or login styles.
- Do not change data attributes consumed by `SITE_JS`, URLs, API JSON shapes, generated report filenames, or MathJax setup.
- Keep research data surfaces dense: graph canvases, formulas, tables, code blocks, and OCR evidence panels receive themed framing but no rotation.
- Use no rounded rectangles for major cards. Allow 8-12px radius only for thumbnails, small tags, and tactile controls.
- Maintain zero horizontal overflow at 1440px, 768px, and 390px widths.

### Task 1: Add Regression Tests for the Public Theme Contract

**Files:**
- Modify: `airesearch/tests/test_research_site.py:1048-1068`
- Modify: `airesearch/src/airesearch/research_site.py:4054-7402`

- [ ] **Step 1: Add failing assertions for the shared public theme primitives**

Insert below the existing published-site assertions:

```python
    assert "--theme-ink: #111;" in css
    assert "--theme-cream: #fff9ee;" in css
    assert ".theme-card" in css
    assert ".theme-panel" in css
    assert ".theme-control" in css
    assert ".topbar {" in css
    assert "border-bottom: 3px solid var(--theme-ink);" in css
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
cd /home/ubuntu/vibe_proj/niu-secretary/airesearch
.venv/bin/python -m pytest tests/test_research_site.py::test_report_site_acceptance_budgets -q
```

Expected: `FAIL` because the public theme primitive selectors do not yet exist.

- [ ] **Step 3: Add the theme variables and primitive selectors**

At the final theme override area of `SITE_CSS`, add:

```css
:root {
  --theme-ink: #111;
  --theme-cream: #fff9ee;
  --theme-paper: #fff;
  --theme-yellow: #f7d358;
  --theme-pink: #ff71ce;
  --theme-teal: #86ccca;
  --theme-blue: #5d8bd8;
  --theme-red: #ef476f;
  --theme-shadow-black: 6px 6px 0 #111;
}
.theme-card,
.theme-panel {
  border: 3px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: var(--theme-shadow-black);
}
.theme-control {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  color: var(--theme-ink);
}
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py::test_report_site_acceptance_budgets -q
```

Expected: `1 passed`.

### Task 2: Rebuild the Global Public Shell

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py:1695-1804`
- Modify: `airesearch/src/airesearch/research_site.py:4054-4215`
- Modify: `airesearch/tests/test_research_site.py:1048-1068`

- [ ] **Step 1: Add failing shell markup and CSS assertions**

Add assertions:

```python
    assert 'class="topbar theme-topbar"' in index_html
    assert 'class="site-footer theme-footer"' in index_html
    assert ".theme-topbar" in css
    assert ".theme-footer" in css
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py::test_report_site_acceptance_budgets -q
```

Expected: `FAIL` because the existing shell lacks the theme classes.

- [ ] **Step 3: Add semantic shell classes without changing links or controls**

Change only the outer elements in `_page_shell`:

```html
<header class="topbar theme-topbar">
```

```html
<footer class="site-footer theme-footer">
```

Add CSS:

```css
.theme-topbar {
  min-height: 78px;
  padding: 0 36px;
  border-bottom: 3px solid var(--theme-ink);
  background: var(--theme-cream);
  box-shadow: 0 4px 0 rgba(17, 17, 17, 0.1);
}
.theme-topbar .brand strong {
  color: var(--theme-ink);
  font-family: "Archivo Black", "Noto Sans SC", system-ui, sans-serif;
}
.theme-topbar nav a[aria-current="page"] {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-yellow);
  color: var(--theme-ink);
}
.theme-footer {
  padding: 18px 20px;
  border: 3px solid var(--theme-ink);
  border-width: 3px 0 0;
  background: var(--theme-cream);
}
```

- [ ] **Step 4: Run the focused test and full static-site test file**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py -q
```

Expected: all tests pass.

### Task 3: Normalize Controls, Chips, Metrics, and Repeated Panels

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py:1806-1910`
- Modify: `airesearch/src/airesearch/research_site.py:4054-4370`
- Modify: `airesearch/src/airesearch/research_site.py:6600-7050`
- Modify: `airesearch/tests/test_research_site.py:1048-1068`

- [ ] **Step 1: Add failing assertions for high-traffic shared components**

Add:

```python
    assert ".metric-card {" in css
    assert "box-shadow: 5px 5px 0 var(--theme-yellow);" in css
    assert ".toolbar input," in css
    assert ".pager button {" in css
    assert ".fact-chip.method" in css
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py::test_report_site_acceptance_budgets -q
```

Expected: `FAIL` until theme colors and controls are represented by the required rules.

- [ ] **Step 3: Apply the shared theme to existing components**

Add scoped overrides:

```css
.metric-card,
.cluster-card,
.gap-panel,
.related-panel,
.global-search,
.toolbar {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: 4px 4px 0 rgba(17, 17, 17, 0.18);
}
.metric-card:nth-child(2n) { box-shadow: 5px 5px 0 var(--theme-yellow); }
.metric-card:nth-child(3n) { box-shadow: 5px 5px 0 var(--theme-teal); }
.toolbar input,
.toolbar select,
.global-search input,
.global-search select,
.pager button {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: #fff;
}
.pager button:hover,
.pager button:focus-visible {
  background: var(--theme-yellow);
  color: var(--theme-ink);
}
.fact-chip {
  border: 1px solid rgba(17, 17, 17, 0.52);
  border-radius: 0;
}
```

- [ ] **Step 4: Run all site tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py -q
```

Expected: all tests pass.

### Task 4: Convert the Blog Index to a Post Stack

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py:1957-2045`
- Modify: `airesearch/src/airesearch/research_site.py:4250-4370`
- Modify: `airesearch/src/airesearch/research_site.py:6170-6326`
- Modify: `airesearch/tests/test_research_site.py:980-1046`

- [ ] **Step 1: Add failing blog-card structural assertions**

In `test_blog_index_lists_published_deep_reading_posts`, add:

```python
    assert 'class="blog-card blog-post-card reveal"' in blogs_html
    assert "blog-card-media" in blogs_html
```

- [ ] **Step 2: Run the blog-index test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py::test_blog_index_lists_published_deep_reading_posts -q
```

Expected: `FAIL` because blog cards do not have the post-stack semantic classes.

- [ ] **Step 3: Add classes and card styling**

Change the blog card wrapper and media wrapper:

```html
<article class="blog-card blog-post-card reveal">
```

```html
<div class="blog-card-cover blog-card-media">
```

Add:

```css
.blog-index-list {
  width: min(850px, 100%);
  gap: 18px;
}
.blog-post-card {
  grid-template-columns: 170px minmax(0, 1fr);
  padding: 18px;
  overflow: visible;
  border: 3px solid var(--theme-ink);
  border-radius: 0;
  box-shadow: 8px 8px 0 var(--theme-ink);
  transform: rotate(-0.7deg);
}
.blog-post-card:nth-child(2n) {
  box-shadow: 8px 8px 0 var(--theme-pink);
  transform: rotate(0.7deg);
}
.blog-post-card:nth-child(3n) { box-shadow: 8px 8px 0 var(--theme-teal); }
.blog-post-card:hover { transform: rotate(0) translateY(-4px); }
.blog-post-card .blog-card-media {
  min-height: 128px;
  border: 1px solid var(--theme-ink);
  border-radius: 12px;
}
```

- [ ] **Step 4: Add responsive reset and run the blog-index test**

Add inside the existing `@media (max-width: 880px)` block:

```css
.blog-post-card,
.blog-post-card:nth-child(2n) {
  grid-template-columns: 1fr;
  transform: none;
}
.blog-post-card:hover { transform: translateY(-2px); }
```

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py::test_blog_index_lists_published_deep_reading_posts -q
```

Expected: `1 passed`.

### Task 5: Theme Paper Detail Research Surfaces Without Distorting Data

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py:2947-3136`
- Modify: `airesearch/src/airesearch/research_site.py:4370-5600`
- Modify: `airesearch/src/airesearch/research_site.py:6600-7050`
- Modify: `airesearch/tests/test_research_site.py:800-950`

- [ ] **Step 1: Add failing CSS contract assertions for research surfaces**

Add to the deep-reading/rendering test:

```python
    assert ".paper-layout-panel" in css
    assert ".paper-layout-table-wrap" in css
    assert ".paper-layout-formula" in css
    assert "border: 2px solid var(--theme-ink);" in css
    assert ".paper-evidence-graph" in css
```

- [ ] **Step 2: Run the deep-reading rendering test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py -k paper_blog -q
```

Expected: `FAIL` until science-content panel styling uses the shared theme token.

- [ ] **Step 3: Add non-rotating themed workbench panels**

Add:

```css
.paper-layout-panel,
.paper-summary-block,
.paper-layout-code-card,
.paper-layout-table-wrap,
.paper-layout-formula,
.paper-layout-data-table,
.paper-evidence-graph,
.paper-evidence-panel {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: 4px 4px 0 rgba(17, 17, 17, 0.13);
  transform: none;
}
.paper-layout-table-wrap,
.paper-layout-code-card,
.paper-layout-formula {
  overflow-x: auto;
}
.paper-layout-data-table th {
  background: var(--theme-yellow);
  color: var(--theme-ink);
}
```

- [ ] **Step 4: Run deep-reading and full-site tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py -k paper_blog -q
.venv/bin/python -m pytest tests/test_research_site.py -q
```

Expected: all selected and full tests pass.

### Task 6: Theme Reports, Map, and Starmap Tool Surfaces

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py:3137-4023`
- Modify: `airesearch/src/airesearch/research_site.py:5400-7150`
- Modify: `airesearch/tests/test_research_site.py:1048-1068`

- [ ] **Step 1: Add failing selectors for graph and report shell styling**

Add:

```python
    assert ".map-shell" in css
    assert ".starmap-shell" in css
    assert ".map-sidebar" in css
    assert ".starmap-sidebar" in css
    assert ".report-prose" in css
```

- [ ] **Step 2: Run the acceptance test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py::test_report_site_acceptance_budgets -q
```

Expected: `FAIL` until these public tool-surface theme rules are explicit.

- [ ] **Step 3: Add themed frames and controls**

Add:

```css
.map-shell,
.starmap-shell,
.digest-sidebar,
.synthesis-aside,
.narrative-aside {
  border: 3px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-paper);
  box-shadow: 6px 6px 0 var(--theme-blue);
}
.map-sidebar,
.starmap-sidebar,
.map-controls,
.starmap-controls,
.map-legend,
.starmap-legend {
  border: 2px solid var(--theme-ink);
  border-radius: 0;
  background: var(--theme-cream);
}
.report-prose,
.digest-prose,
.synthesis-prose,
.narrative-prose {
  border-left: 5px solid var(--theme-yellow);
}
```

- [ ] **Step 4: Run all tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_research_site.py -q
```

Expected: all tests pass.

### Task 7: Generate, Screenshot, Deploy, and Perform Visual Regression Checks

**Files:**
- Generated: `airesearch/exports/mvp-current/bundle/`
- Generated: `airesearch/exports/site-current/`
- Deployed: `/var/www/html/niu-secretary/airesearch/`

- [ ] **Step 1: Bump the cache asset version**

Set:

```python
SITE_ASSET_VERSION = "20260815-yantao-public-theme-v1"
```

- [ ] **Step 2: Generate the static site and publish**

Run:

```bash
cd /home/ubuntu/vibe_proj/niu-secretary/airesearch
.venv/bin/python -m airesearch.cli generate-report-site --bundle-dir exports/mvp-current/bundle
.venv/bin/python -m airesearch.cli publish-static-site --source-dir exports/mvp-current/bundle --out-dir exports/site-current
sudo bash deploy/deploy-airesearch.sh
```

Expected: `report_site_exported`, `static_site_published`, and `static_site_deployed`.

- [ ] **Step 3: Run Playwright desktop checks**

Use a 1440px wide page for:

```text
/niu-secretary/airesearch/
/niu-secretary/airesearch/papers/index.html
/niu-secretary/airesearch/blogs/index.html
/niu-secretary/airesearch/papers/wall-wm.html#deep-reading
/niu-secretary/airesearch/map/index.html
/niu-secretary/airesearch/starmap/index.html
/niu-secretary/airesearch/gaps/index.html
/niu-secretary/airesearch/synthesis/index.html
/niu-secretary/airesearch/narrative/index.html
```

For every page assert:

```javascript
document.documentElement.scrollWidth === window.innerWidth
```

For the deep-reading page additionally assert:

```javascript
getComputedStyle(document.querySelector('.paper-blog-aside')).position === 'fixed'
```

For map and starmap additionally assert that their SVG/canvas bounding box has a nonzero width and height.

- [ ] **Step 4: Run Playwright mobile checks**

Repeat the home, papers, blogs, deep-reading, map, and gaps checks at `390x844`.

For every page assert:

```javascript
document.documentElement.scrollWidth === window.innerWidth
```

For paper/blog cards additionally assert:

```javascript
getComputedStyle(document.querySelector('.paper-post-card, .blog-post-card')).transform === 'none'
```

- [ ] **Step 5: Run final backend-generated-site tests**

Run:

```bash
cd /home/ubuntu/vibe_proj/niu-secretary/airesearch
.venv/bin/python -m pytest tests/test_research_site.py -q
```

Expected: all tests pass.

## Final Review Checklist

- [ ] All public navigation links remain present and resolve.
- [ ] All generated pages use `SITE_ASSET_VERSION = "20260815-yantao-public-theme-v1"`.
- [ ] The paper post stack remains visually distinct and retains its current API-driven rendering.
- [ ] Blog index uses the same post-stack visual vocabulary.
- [ ] Scientific formula/table/image/OCR panels are not rotated and remain horizontally scrollable when needed.
- [ ] Map and starmap canvases remain visible and interactive.
- [ ] Admin UI files have no changes.
- [ ] Desktop and mobile screenshots show no clipped text or horizontal overflow.
- [ ] No generated files were manually edited.
