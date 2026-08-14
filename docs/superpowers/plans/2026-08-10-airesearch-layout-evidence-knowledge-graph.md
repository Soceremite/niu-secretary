# AIResearch Layout Evidence Knowledge Graph Implementation Plan

> **Execution note:** Follow this plan task by task with test-first changes. Keep all edits scoped to AIResearch graph, bundle, public paper detail, admin inspector, tests, and documentation. Do not stage or revert unrelated worktree changes.

**Goal:** Build a deterministic, traceable knowledge graph that links each paper's structured research facts to its parsed figures, tables, and equations, then expose the same graph through the bundle, public paper detail, and administrator inspector.

**Architecture:** Reuse the existing SQLite `kg_nodes`, `kg_edges`, and `kg_provenance` tables with a dedicated `layout_evidence_graph` extractor. The extractor owns only fact/evidence nodes and their edges; it reuses but never mutates the shared paper node. Bundle export produces a bounded public projection, while the admin API returns a larger diagnostic projection from the same loader.

**Tech Stack:** Python 3, SQLite, pytest, existing AIResearch CLI/pipeline/bundle/site modules, Vue 3 + Element Plus, Vitest/Vite, Playwright/headless Chromium.

---

## Task 1: Deterministic graph extractor

**Files:**
- Create: `airesearch/src/airesearch/layout_evidence_graph.py`
- Create: `airesearch/tests/test_layout_evidence_graph.py`
- Reference: `airesearch/src/airesearch/knowledge_graph.py`
- Reference: `airesearch/src/airesearch/db.py`

1. Add a minimal SQLite fixture containing one paper, one completed layout run, figure/table/equation blocks, research facts, and fact provenance.
2. Write failing tests for exact provenance matching, bounded lexical matching, type compatibility, quality thresholds, deterministic ordering, and at most three evidence links per fact.
3. Write failing tests that rerunning one paper replaces only extractor-owned rows and does not overwrite or delete the shared `paper:<paper_key>` node.
4. Implement constants and normalization helpers for extractor name/version, compatible fact/evidence types, usable-content checks, tokenization, containment, and lexical scoring.
5. Implement `extract_layout_evidence_graph(db_path, paper_key=None, limit=None)` using the latest completed/reused layout run and deterministic SQL/order rules.
6. Store nodes and edges with stable keys:
   - `research_fact:<paper_key>:<fact_id>`
   - `layout_evidence:<paper_key>:<run_id>:<block_id>`
   - `has_research_fact`, `has_layout_evidence`, `supported_by`
7. Copy source provenance from `research_fact_provenance` and layout block/run metadata into `kg_provenance`; include matching method and score on `supported_by` edges.
8. Implement `load_paper_evidence_graph(db_path, paper_key, public=False)` with deterministic node/edge ordering, summary counts, unlinked facts, and public projection limits/redaction.
9. Implement `export_layout_evidence_graph(db_path, out_path)` as a stable JSON artifact keyed by paper.
10. Run `pytest -q airesearch/tests/test_layout_evidence_graph.py` and fix all failures.

## Task 2: CLI and pipeline orchestration

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/src/airesearch/mvp_pipeline.py`
- Modify: `airesearch/src/airesearch/schema.sql`
- Modify: `airesearch/tests/test_cli.py`
- Modify: `airesearch/tests/test_db.py`
- Modify: `airesearch/tests/test_mvp_pipeline.py`

1. Write failing CLI tests for:
   - `extract-layout-evidence-graph [--paper-key] [--limit]`
   - `export-layout-evidence-graph --out`
2. Add parsers, imports, handlers, JSON summaries, and nonzero failure behavior consistent with existing AIResearch commands.
3. Write a failing MVP pipeline test asserting graph extraction runs after fact provenance repair and before bundle/site export.
4. Add the graph extraction step to the MVP pipeline and include its counts/status in the pipeline report.
5. Refresh the affected paper graph after CLI fact extraction and after single/batch layout parsing completes successfully.
6. Index `kg_edges.target_key` so extractor-owned node cleanup does not repeatedly scan the full edge table during an idempotent rebuild.
7. Run `pytest -q airesearch/tests/test_cli.py airesearch/tests/test_db.py airesearch/tests/test_mvp_pipeline.py`.

## Task 3: Admin API and mutation refresh

**Files:**
- Modify: `airesearch/src/airesearch/admin_server.py`
- Modify: `server/action_handlers.py` only if action pass-through changes are required
- Modify: `airesearch/tests/test_layout_evidence_graph.py`
- Modify: `airesearch/tests/test_paper_blog.py`
- Modify: `server/test_platform_audit.py`

1. Write failing tests that the paper layout detail response includes `evidence_graph` with fact/evidence/relation summaries and diagnostic matching metadata.
2. Attach `load_paper_evidence_graph(..., public=False)` to the existing layout detail response without changing current formulas/tables/OCR fields.
3. Write failing tests that successful layout parsing and admin fact create/update/delete operations refresh the affected paper graph.
4. Add narrowly scoped refresh calls after successful commits/jobs; graph refresh failures must be reported and must not silently corrupt the original operation.
5. Extend platform route/contract audit assertions for the new payload.
6. Run the focused admin tests from `airesearch/`, then run `airesearch/.venv/bin/python -m pytest -q server/test_platform_audit.py` from the repository root.

## Task 4: Bundle and public paper API

**Files:**
- Modify: `airesearch/src/airesearch/research_bundle.py`
- Modify: `airesearch/src/airesearch/research_site.py`
- Modify: `airesearch/tests/test_research_bundle.py`
- Modify: `airesearch/tests/test_research_site.py`

1. Write a failing bundle test for `layout-evidence-graph.json`, its manifest entry, stable schema/version, and bounded public fields.
2. Export the graph artifact during report bundle creation after current layout evidence export.
3. Load and index the graph artifact in site generation, then add `evidence_graph` to each public paper JSON payload.
4. Write failing API tests for caps: 24 facts, 48 evidence nodes, 3 links per fact, 72 relations, 240-character previews, and no local paths/raw HTML/admin-only fields.
5. Preserve graceful degradation when old bundles have no graph artifact by returning an empty versioned graph.
6. Run `pytest -q airesearch/tests/test_research_bundle.py airesearch/tests/test_research_site.py`.

## Task 5: Public paper-detail visualization

**Files:**
- Modify: `airesearch/src/airesearch/research_site.py`
- Modify: `airesearch/tests/test_research_site.py`
- Modify generated assets only through the existing site build command.

1. Write failing HTML tests for a new `证据关系` section containing fact rows, relation method labels, evidence type/page labels, and unlinked-fact state.
2. Add stable anchors to formula/table/visual evidence targets without changing current card dimensions or image resolution.
3. Render each fact as an unframed row with compact evidence links; clicking a target scrolls to an existing formula/table/visual block when rendered.
4. Render unresolved or capped evidence as a non-link reference rather than a broken anchor.
5. Add responsive CSS for desktop/mobile and verify the section does not create nested cards, oversized images, clipped text, or horizontal overflow.
6. Run `pytest -q airesearch/tests/test_research_site.py`.

## Task 6: Administrator inspector visualization

**Files:**
- Modify: `web/src/modules/admin/AdminAIResearchPage.vue`
- Modify: `web/src/shared/styles/global.css`
- Modify: `server/test_platform_audit.py`

1. Add or extend a component test for a `事实关联` inspector tab populated from `layoutDetail.evidence_graph`.
2. Implement computed rows for facts, evidence links, unlinked status, match method, score, source keys, and provenance.
3. Add the tab beside existing evidence/formula/table/OCR/visual tabs using current Element Plus patterns.
4. Style it as a dense diagnostic table/list with high-contrast status text and no nested cards.
5. Add empty, loading, and stale-data states while preserving current inspector behavior.
6. Run the focused frontend test, `npm run build`, and the platform audit.

## Task 7: Documentation and operator workflow

**Files:**
- Modify: `airesearch/SKILL.md`
- Modify: `airesearch/DEVELOPMENT.md`
- Modify: `docs/superpowers/specs/2026-08-10-airesearch-layout-evidence-knowledge-graph-design.md` only if implementation details require an explicit amendment

1. Document graph semantics, matching thresholds, node/edge keys, provenance, public redaction, and ownership rules.
2. Document both CLI commands with examples and expected JSON output.
3. Document the admin/public payloads and how the graph participates in paper ingestion, layout parsing, fact extraction, detailed interpretation, bundle generation, and site deployment.
4. Add troubleshooting guidance for missing layout runs, missing facts, low-quality blocks, unlinked facts, and stale bundles.
5. Run documentation link/path checks already present in the repository, or use targeted `rg` validation when no checker exists.

## Task 8: Backup, full rebuild, visual verification, and deployment

**Files:**
- Create: timestamped SQLite backup under `backups/`
- Regenerate: AIResearch bundle/site output through supported commands
- Deploy: through existing deployment scripts only

1. Record `git status --short` and protect all unrelated dirty files.
2. Create and verify a timestamped SQLite backup before any all-paper graph mutation.
3. Run graph extraction for all papers; verify paper/node/edge/provenance counts and rerun idempotency.
4. Rebuild all 209 paper JSON/detail pages and verify known samples:
   - `world2vlm`
   - `world-model-self-distillation`
   - `world-action-models`
   - `2606_00269`
   - `colavla`
5. Run focused tests, the full AIResearch suite, platform audit, Vue build, admin smoke tests, and the existing full workflow check.
6. Start or reuse a local server and run headless checks at desktop and mobile widths for public paper detail and admin inspector.
7. Capture screenshots and DOM geometry; verify no overlap, horizontal overflow, broken dynamic imports, blank panels, or inaccessible evidence targets.
8. Deploy static and Vue assets using existing scripts, preserving deployment snapshots.
9. Verify production HTTP status, asset loading, public payload schema, visible graph section, admin inspector tab, and new-tab behavior for paper/GitHub links.
10. Run the requesting-code-review checklist against the scoped diff, fix substantive findings, and report tests, backup, artifact counts, deployment snapshots, and residual risks.

## Acceptance Criteria

- The same deterministic graph can be regenerated with identical keys/order and without duplicate owned rows.
- Shared paper nodes remain untouched by extractor cleanup or upsert behavior.
- Every relation is traceable to fact/layout provenance and records its matching method and score.
- Public output is bounded, redacted, versioned, and visible in both paper JSON and paper detail HTML.
- Admin output exposes complete bounded diagnostics and refreshes after relevant mutations.
- Existing formulas, tables, OCR, experiments, image selection, translation, five-section generation, and detailed interpretation remain functional.
- All targeted/full tests, builds, headless checks, and production checks pass after an all-paper rebuild.
