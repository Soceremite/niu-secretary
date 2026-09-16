# AIResearch Yantao-Style Theme Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the entire AIResearch UI so the site keeps its current functionality but adopts the yantao.wiki article-driven visual language across dashboard, paper views, deep reading, and admin surfaces.

**Architecture:** Keep the existing Python static-site generator and generated vanilla CSS/JS bundle. Introduce a shared theme layer first, then retune page shells and reusable content components so all pages inherit the same type scale, spacing, surface treatment, and article layout. Use the existing deep-reading/blog data pipeline; only the presentation layer changes.

**Tech Stack:** Python static-site generation, vanilla HTML/CSS/JavaScript, pytest, Playwright screenshots for verification.

---

### Task 1: Establish the Shared Yantao-Style Theme

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`
- Test: `airesearch/tests/test_research_site.py`

- [ ] **Step 1: Add a shared theme token block**

Add a new CSS block near `SITE_CSS` with warm light surfaces, serif display text, flatter borders, smaller radii, and the article-theme spacing used across yantao-style pages:

```python
:root {
  --bg-base: #fafaf8;
  --bg-surface: #ffffff;
  --bg-sunken: #f3f2ef;
  --bg-sidebar: #f7f6f3;
  --ink-primary: #1a1a1a;
  --ink-body: #37352f;
  --ink-secondary: #6b6b6b;
  --border: #e8e7e4;
  --border-strong: #d4d3cf;
  --shadow-sm: 0 1px 3px rgba(15, 45, 40, 0.05);
  --shadow-md: 0 10px 24px rgba(15, 45, 40, 0.09);
  --font-heading: "Source Serif 4", "Noto Serif SC", Georgia, serif;
  --font-body: "Aptos", "Noto Sans SC", system-ui, sans-serif;
}
```

- [ ] **Step 2: Align the global shell to the reference page**

Update `body`, `main`, `.topbar`, `.site-footer`, `.hero`, `.page-heading`, `.metrics-grid`, `.paper-card`, `.cluster-card`, `.blog-card`, `.gap-panel`, and `.related-panel` so the whole site reads like a blog theme rather than a dashboard theme. Keep all navigation and actions intact.

- [ ] **Step 3: Add regression assertions**

Extend `test_research_site.py` to assert the generated CSS contains the new warm theme tokens and the narrower article layout values, and that the top-level page shell still includes all existing nav destinations.

- [ ] **Step 4: Run the focused regression test**

Run:

```bash
cd airesearch && .venv/bin/python -m pytest tests/test_research_site.py -k 'site_shell or page_shell or blog' -q
```

Expected: at least the targeted assertions pass after the theme layer lands.

### Task 2: Rebuild the Paper and Blog Layouts

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`
- Test: `airesearch/tests/test_research_site.py`

- [ ] **Step 1: Convert paper detail and deep-reading pages to an article layout**

Refactor `_paper_blog_section`, `_paper_detail_page`, and the deep-reading mode markup so they use the yantao-like structure: article body on the left, sticky TOC on the right, footer tags, neighbor cards, and comments block below the content.

```python
<div class="article-layout">
  <article class="article-main">...</article>
  <aside class="article-aside">...</aside>
</div>
<footer class="article-footer">...</footer>
```

- [ ] **Step 2: Restyle code, figures, equations, and tables**

Retune `.paper-blog-code-block`, `.paper-blog-image`, `.paper-layout-formula`, `.paper-layout-table-wrap`, and `.paper-layout-data-table` to match the cleaner article styling while preserving the existing OCR/formula/table features.

- [ ] **Step 3: Keep the deep-reading behavior**

Preserve `#deep-reading` routing, TOC activation, copy buttons, and back links. The behavior stays the same; only the presentation should change.

- [ ] **Step 4: Add page-shape tests**

Add assertions that the rendered deep-reading HTML includes `article-layout`, `article-main`, `article-aside`, `article-footer`, and that the sticky TOC/comments/nav blocks still render in the expected order.

### Task 3: Retune Listings, Dashboard, and Admin Surfaces

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`
- Test: `airesearch/tests/test_research_site.py`

- [ ] **Step 1: Restyle the dashboard and list pages**

Update `_dashboard_page`, `_papers_page`, `_blog_index_card`, `_cluster_card`, and the filter/tool surfaces so the cards, controls, and result lists share the same flat, warm, editorial look as the reference site.

- [ ] **Step 2: Make admin and supporting panels visually consistent**

Apply the same theme tokens to admin dashboards, navigation panels, evidence panels, and workbench panels so the site does not fall back to the old green-heavy UI outside the public pages.

- [ ] **Step 3: Verify no functionality changed**

Keep search, filters, tabs, modes, and links untouched. Only adjust CSS and wrapper markup where needed for alignment.

### Task 4: Verify, Screenshot, and Deploy

**Files:**
- Test: `airesearch/tests/test_research_site.py`

- [ ] **Step 1: Run the full research-site test file**

Run:

```bash
cd airesearch && .venv/bin/python -m pytest tests/test_research_site.py -q
```

- [ ] **Step 2: Build and inspect screenshots**

Render the static site locally, open `wall-wm.html#deep-reading` and one or two list/detail pages in Playwright, and compare them against `yantao.wiki/archives/16/` at desktop and mobile widths.

- [ ] **Step 3: Deploy the regenerated static site**

Publish the rebuilt site with the existing deploy script only after the screenshots match the intended article-driven layout and the tests pass.
