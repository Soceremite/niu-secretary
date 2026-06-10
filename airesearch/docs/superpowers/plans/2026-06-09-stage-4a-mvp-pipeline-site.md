# Stage 4A MVP Pipeline And Static Site Implementation Plan

> **For agentic workers:** This is a compressed launch plan for the MVP path. Keep future changes focused on end-to-end usability before adding fine-grained review tooling.

**Goal:** Ship an end-to-end command and deployable static report site.

**Architecture:** `mvp_pipeline.py` orchestrates existing modules. `research_site.py` renders an HTML entry point from an existing bundle manifest and Markdown artifacts.

**Tech Stack:** Python stdlib, SQLite, existing AIResearch report modules.

---

- [x] Add `research_site.py` to render `bundle/index.html` from `manifest.json`.
- [x] Add `mvp_pipeline.py` to run the local publish chain and reuse existing facts by default.
- [x] Add CLI commands `generate-report-site` and `run-mvp-pipeline`.
- [x] Add smoke tests for the site renderer, MVP pipeline, and CLI commands.
- [x] Run real MVP export to `exports/mvp-current`.
- [x] Update `DEVELOPMENT.md` and `PLAN.md`.
