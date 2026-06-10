# Static Site Provenance Jump Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add static provenance indexes and jump links to generated AIResearch report sites.

**Architecture:** Keep the implementation inside `src/airesearch/research_site.py`. Build a deterministic `provenance-index.json` by recursively reading artifact JSON files, then render a Provenance section in the static HTML that links each source entry back to its report section and raw JSON.

**Tech Stack:** Python 3.11+, stdlib `json`/`html`/`pathlib`, static HTML/CSS, pytest.

---

### Task 1: Provenance Index Tests

**Files:**
- Modify: `tests/test_research_site.py`
- Modify: `src/airesearch/research_site.py`

- [ ] Extend the report-site test bundle so artifact JSON includes `paper_key`, `evidence_source_path`, and `code_links`.
- [ ] Add a test for `build_provenance_index(bundle_dir)` returning deterministic provenance entries.
- [ ] Run `source ./activate.sh && pytest -q tests/test_research_site.py` and confirm the new test fails before implementation.

### Task 2: Provenance Index Implementation

**Files:**
- Modify: `src/airesearch/research_site.py`

- [ ] Add a `ProvenanceIndexEntry` dataclass with `id`, `report_name`, `report_title`, `json_path`, `type`, `paper_key`, `source_path`, `url`, and `label`.
- [ ] Add recursive provenance extraction helpers for dictionaries and lists.
- [ ] De-duplicate entries by report, type, paper key, source path, and URL.
- [ ] Export `build_provenance_index(bundle_dir)` as a public helper.
- [ ] Run `source ./activate.sh && pytest -q tests/test_research_site.py`.

### Task 3: Static Provenance HTML

**Files:**
- Modify: `src/airesearch/research_site.py`
- Modify: `tests/test_research_site.py`

- [ ] Render a Provenance section below search tools with a count and list of source entries.
- [ ] Link each provenance entry back to its report section and raw JSON artifact.
- [ ] Write `provenance-index.json` from `export_report_site()`.
- [ ] Update tests for HTML markers, exported JSON, and artifact count.
- [ ] Run `source ./activate.sh && pytest -q tests/test_research_site.py`.

### Task 4: Docs And Roadmap

**Files:**
- Modify: `PLAN.md`
- Modify: `DEVELOPMENT.md`

- [ ] Mark provenance jump links as implemented in `PLAN.md`.
- [ ] Document `provenance-index.json` and static Provenance links in `DEVELOPMENT.md`.
- [ ] Run `git diff --check -- src/airesearch/research_site.py tests/test_research_site.py PLAN.md DEVELOPMENT.md docs/superpowers`.

### Task 5: Verification

**Files:**
- No new files.

- [ ] Run focused tests: `source ./activate.sh && pytest -q tests/test_research_site.py tests/test_mvp_pipeline.py tests/test_static_publish.py`.
- [ ] Run full tests: `source ./activate.sh && pytest -q`.
- [ ] Summarize changed files and generated behavior.
