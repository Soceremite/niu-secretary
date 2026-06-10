# Static Site Search And Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add client-side search and type filtering to generated AIResearch static report sites.

**Architecture:** Keep the feature inside `src/airesearch/research_site.py`, which already owns static site rendering. Build a deterministic `search-index.json` from the report bundle manifest and Markdown artifacts, then add plain HTML/CSS/JavaScript controls to filter report sections and navigation links.

**Tech Stack:** Python 3.11+, stdlib `json`/`html`/`pathlib`, static HTML/CSS/JavaScript, pytest.

---

### Task 1: Search Index Tests

**Files:**
- Modify: `tests/test_research_site.py`
- Modify: `src/airesearch/research_site.py`

- [ ] Add a fixture bundle with at least two report artifacts and different artifact names.
- [ ] Add a test that `build_search_index(bundle_dir)` returns entries with `name`, `title`, `type`, `markdown_path`, `json_path`, `snippet`, and `search_text`.
- [ ] Add a test that `export_report_site(bundle_dir)` writes `search-index.json` next to `index.html`.
- [ ] Run `source ./activate.sh && pytest -q tests/test_research_site.py` and confirm the new tests fail before implementation.

### Task 2: Search Index Implementation

**Files:**
- Modify: `src/airesearch/research_site.py`
- Modify: `tests/test_research_site.py`

- [ ] Add a `SearchIndexEntry` dataclass.
- [ ] Add `_artifact_type(name)` to classify report artifacts as `digest`, `map`, `gap`, `synthesis`, `narrative`, `cluster`, `review`, or `report`.
- [ ] Add `_snippet(text, limit=260)` to collapse whitespace and cap long Markdown.
- [ ] Add `build_search_index(bundle_dir)` to load the manifest and return deterministic entries.
- [ ] Update `export_report_site()` to write pretty JSON to `search-index.json` and count it as an exported artifact.
- [ ] Run `source ./activate.sh && pytest -q tests/test_research_site.py`.

### Task 3: Static Filter UI

**Files:**
- Modify: `src/airesearch/research_site.py`
- Modify: `tests/test_research_site.py`

- [ ] Add search controls to the generated `index.html`: `<input id="site-search">`, `<select id="site-filter">`, and `<span id="site-result-count">`.
- [ ] Add `data-report-name`, `data-report-type`, and `data-search-text` attributes to each report section.
- [ ] Add matching `data-nav-name` and `data-report-type` attributes to navigation links.
- [ ] Add inline JavaScript that fetches `search-index.json`, filters sections and nav links, and updates the count.
- [ ] Add tests asserting the generated HTML contains the controls, tagged sections, and `search-index.json` reference.
- [ ] Run `source ./activate.sh && pytest -q tests/test_research_site.py`.

### Task 4: Docs And Roadmap

**Files:**
- Modify: `PLAN.md`
- Modify: `DEVELOPMENT.md`

- [ ] Mark static-site search/filter as implemented in `PLAN.md`.
- [ ] Document the `search-index.json` output and browser-only filtering behavior in `DEVELOPMENT.md`.
- [ ] Run `git diff --check -- src/airesearch/research_site.py tests/test_research_site.py PLAN.md DEVELOPMENT.md`.

### Task 5: Verification

**Files:**
- No new files.

- [ ] Run focused tests: `source ./activate.sh && pytest -q tests/test_research_site.py tests/test_mvp_pipeline.py tests/test_static_publish.py`.
- [ ] Run full tests: `source ./activate.sh && pytest -q`.
- [ ] Inspect `git diff --stat` and summarize only files touched for this feature.
