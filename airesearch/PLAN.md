# AIResearch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 牛秘书 AIResearch 研知库 as a local research-paper system on top of `paperpipe` / `papi`, with scheduled paper discovery, auditable ingestion, knowledge graph extraction, provenance, and research reports.

**Architecture:** `paperpipe` is the L0 paper grounding substrate for single-paper ingestion, artifacts, search, RAG, export, and agent skills. AIResearch adds L1 scheduled discovery, L2 SQLite-backed knowledge graph and provenance, and L3 research reports. Start with SQLite and paperpipe outputs; only evaluate Kuzu or a separate vector store after scale or query requirements demand it.

**Tech Stack:** Python, `paperpipe` / `papi`, SQLite, OpenAlex API, Semantic Scholar API, cloud LLM, cloud embedding, optional PaperQA2, optional GROBID, optional Kuzu.

---

## Current Status

| Area | Status | Notes |
| --- | --- | --- |
| paperpipe capability audit | Done | GitHub/PyPI capability boundary reviewed; `SKILL.md`, `REQUIREMENTS.md`, and decision note updated. |
| local `PLAN.md` | Done | This file is now the implementation and status tracker. |
| local `papi` install | Done | Installed `paperpipe==1.9.3` in local `.venv` with narrow extras `llm,figures,mcp`; avoided `all` because it pulls LEANN/torch/CUDA/docling/qdrant. |
| L0 paperpipe smoke test | Done | `papi add/list/show/search/index/ask` pass on `1706.03762` using separated LLM and embedding API config. |
| AIResearch SQLite ledger | Done | Stage 2A implemented: SQLite schema, paperpipe sync, batch ingest, CLI, tests, and local verification. |
| L1 discovery | Done | Stage 2B profiles, scoring, candidate storage, discovery orchestration, CLI, OpenAlex/arXiv/Semantic Scholar providers, opt-in quota-safe Google Scholar provider, provider-level error handling, and Top 100 manifest export implemented. |
| L2 knowledge graph | Not started | Extraction service and graph tables not implemented. |
| L3 reports | Not started | Paper Card/Digest/Map/Gap Analysis not implemented. |

## Completed

- [x] Created `airesearch/REQUIREMENTS.md`.
- [x] Created `airesearch/SKILL.md`.
- [x] Created decision note: `airesearch/decisions/2026-06-08-ingestion-stack-selection.md`.
- [x] Re-audited `paperpipe` / `papi` against the GitHub/PyPI project.
- [x] Clarified that `papi ask`, MCP, figures, PaperQA2, and LEANN are conditional extras, not unconditional capabilities.
- [x] Clarified that AIResearch owns scheduled discovery, run audit, knowledge graph, provenance, and reports.
- [x] Confirmed `paperpipe` was not installed locally before Phase 1.
- [x] Created local project plan: `airesearch/PLAN.md`.
- [x] Created local `.venv` and installed `paperpipe==1.9.3`.
- [x] Installed Phase 1 extras with `paperpipe[llm,figures,mcp]` instead of `paperpipe[all]` to avoid LEANN/torch/CUDA heavy dependencies.
- [x] Created `airesearch/data/paperpipe/` and `airesearch/.env.example`.
- [x] Added arXiv paper `1706.03762` (`Attention Is All You Need`) to the local paperpipe database.
- [x] Verified `papi list`, `papi show --level summary`, `papi show --level eq`, `papi search`, and `papi index --backend search`.
- [x] Verified `papi index --backend pqa` and `papi ask` with separated LLM and embedding API config.
- [x] Created Stage 2A design spec: `docs/superpowers/specs/2026-06-08-stage-2a-ledger-batch-ingest-design.md`.
- [x] Created Stage 2A implementation plan: `docs/superpowers/plans/2026-06-08-stage-2a-ledger-batch-ingest.md`.
- [x] Implemented AIResearch Python package skeleton under `src/airesearch/`.
- [x] Created SQLite ledger schema and DB helpers.
- [x] Implemented paperpipe sync into `data/airesearch.sqlite3`.
- [x] Implemented batch ingest manifest workflow with per-item success/failure/duplicate tracking.
- [x] Implemented CLI commands: `init-db`, `sync-paperpipe`, `batch-ingest`, and `status`.
- [x] Added local `.gitignore` for `.env`, `.venv`, caches, and generated data.
- [x] Verified Stage 2A with `pytest -v`: 10 tests passed.
- [x] Synced real paperpipe DB: `papers_seen=1 artifacts_seen=6`.
- [x] Verified duplicate batch path: `total=1 success=0 failed=0 duplicate=1 skipped=0`.
- [x] Created Stage 2B design spec: `docs/superpowers/specs/2026-06-08-stage-2b-research-candidate-discovery-design.md`.
- [x] Created Stage 2B implementation plan: `docs/superpowers/plans/2026-06-08-stage-2b-research-candidate-discovery.md`.
- [x] Extended SQLite schema with `research_profiles`, `discovery_runs`, and `research_candidates`.
- [x] Implemented default Stage 2B research profiles with 12-month primary window and 2024 strong-backing exception window.
- [x] Implemented deterministic candidate scoring by recency, backing, venue/source, topic relevance, and artifacts.
- [x] Implemented candidate storage, listing, and manifest export.
- [x] Implemented discovery provider abstraction and offline orchestration.
- [x] Added CLI commands: `seed-profiles`, `discover-candidates`, `list-candidates`, and `export-candidates`.
- [x] Seeded real local ledger with 5 research profiles.
- [x] Verified Stage 2B local implementation with `pytest -v`: 18 tests passed.
- [x] Implemented Stage 2B network providers for OpenAlex, arXiv, and Semantic Scholar.
- [x] Added provider-level error handling so Semantic Scholar 429/rate-limit failures are recorded without blocking other sources.
- [x] Added candidate quality filters for future dates, topicless primary-window papers, obvious non-paper OpenAlex locations, and duplicate titles.
- [x] Ran real arXiv discovery for 5 profiles and stored 237 candidates: multimodal 50, unified 39, world models 50, diffusion 48, embodied/VLA 50.
- [x] Exported Top 100 manifests under `manifests/` for all 5 Stage 2B profiles.
- [x] Verified Stage 2B provider implementation with `pytest -v`: 22 tests passed.
- [x] Designed quota-safe Google Scholar provider through SerpAPI and Paper Copilot venue-guide policy.
- [x] Implemented opt-in Google Scholar provider with SQLite cache and monthly usage guard.
- [x] Paper Copilot is treated as a human venue/source guide only; AIResearch does not automatically scrape Paper Copilot.

## In Progress

- [ ] Stage 2C: review exported candidate manifests, select papers for batch ingestion, and ingest the approved batch through Stage 2A.

## Stage 2B Completed Tasks

- [x] Stage 2B Task 1: extend SQLite schema for profiles, discovery runs, and candidates.
- [x] Stage 2B Task 2: seed default research profiles for multimodal, unified generation/understanding, world models, diffusion, and embodied AI.
- [x] Stage 2B Task 3: implement recency/backing/venue/topic/artifact candidate scoring.
- [x] Stage 2B Task 4: implement discovery orchestration with provider abstraction.
- [x] Stage 2B Task 5: add `seed-profiles`, `discover-candidates`, `list-candidates`, and `export-candidates` CLI commands.
- [x] Stage 2B Task 6: implement network providers for OpenAlex, arXiv, and Semantic Scholar.
- [x] Stage 2B Task 7: run real arXiv discovery and export Top 100 manifests for all 5 research profiles.
- [x] Stage 2B Task 8: add opt-in Google Scholar discovery through SerpAPI with SQLite cache and monthly usage guard.
- [x] Stage 2B Task 9: document Paper Copilot as a human venue/source guide only, not an automatic scraping provider.

---

## File Map

| Path | Responsibility |
| --- | --- |
| `airesearch/PLAN.md` | Project implementation plan, phase status, and execution tracker. |
| `airesearch/SKILL.md` | Agent-facing instructions and capability boundaries. |
| `airesearch/REQUIREMENTS.md` | Product and architecture requirements. |
| `airesearch/decisions/*.md` | Architecture decision records. |
| `airesearch/docs/superpowers/specs/2026-06-08-stage-2a-ledger-batch-ingest-design.md` | Stage 2A accepted design. |
| `airesearch/docs/superpowers/plans/2026-06-08-stage-2a-ledger-batch-ingest.md` | Stage 2A implementation plan. |
| `airesearch/docs/superpowers/specs/2026-06-08-stage-2b-research-candidate-discovery-design.md` | Stage 2B candidate discovery design. |
| `airesearch/docs/superpowers/plans/2026-06-08-stage-2b-research-candidate-discovery.md` | Stage 2B implementation plan. |
| `airesearch/data/paperpipe/` | Planned `PAPER_DB_PATH` for paperpipe local paper database. |
| `airesearch/data/airesearch.sqlite3` | AIResearch SQLite ledger created by Stage 2A. |
| `airesearch/src/airesearch/` | Planned Python package for CLI, ledger sync, discovery, extraction, and reports. |
| `airesearch/tests/` | Planned tests for schema, adapters, discovery, and reporting. |

---

## Phase 0: Documentation And Scope Lock

**Status:** Done

**Technical Path:**

- Use `paperpipe` only as L0 local paper grounding.
- Keep `GROBID`, `MinerU`, `Kuzu`, and separate vector stores optional.
- Use SQLite for MVP ledger, candidates, graph adjacency, provenance, and jobs.
- Treat cloud LLM outputs as draft unless backed by provenance.

**Tasks:**

- [x] Audit upstream `paperpipe` capabilities.
- [x] Update `SKILL.md` with verified paperpipe boundary.
- [x] Update `REQUIREMENTS.md` with conditional extras and MVP scope.
- [x] Update ingestion-stack decision note.
- [x] Create this local `PLAN.md`.

**Verification:**

- [x] Search docs for stale claims: LEANN as unsupported, Neo4j as default, Qdrant as default, `papi ask` as zero-config.

---

## Phase 1: L0 paperpipe Integration

**Status:** Done

**Goal:** Install `paperpipe`, configure local storage and model access, then verify a small paper workflow.

**Technical Path:**

- Store all paperpipe artifacts under `airesearch/data/paperpipe`.
- Use cloud LLM and cloud embedding by default.
- Verify LLM-dependent and RAG-dependent paths separately.
- Do not build AIResearch custom ingestion before `papi add/show/search/ask` works.

### Task 1.1: Install paperpipe

**Files:**

- Create: `airesearch/data/paperpipe/`
- Create or modify: shell/profile environment only if needed

- [x] Check tool availability.

Run:

```bash
which uv
python3 --version
```

Expected:

- `uv` exists, or Python is available for venv fallback.

- [x] Install paperpipe.

Preferred:

```bash
uv tool install paperpipe --with "paperpipe[all]"
```

Fallback used:

```bash
python3 -m venv /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv
/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv/bin/pip install --index-url https://pypi.org/simple paperpipe
/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.venv/bin/pip install --index-url https://pypi.org/simple 'paperpipe[llm,figures,mcp]'
```

`paperpipe[all]` was attempted and stopped because it began pulling LEANN, torch, CUDA, docling, and qdrant dependencies that are outside the current no-local-GPU MVP path.

- [x] Verify install.

Run:

```bash
papi --help
papi models
```

Expected:

- `papi --help` prints CLI help.
- `papi models` prints configured or configurable model information.

### Task 1.2: Configure local paper database

**Files:**

- Create: `airesearch/data/paperpipe/`
- Create: `airesearch/.env.example`

- [x] Create the local paper database directory.

Run:

```bash
mkdir -p /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe
```

- [x] Create `.env.example`.

Content:

```bash
PAPER_DB_PATH=/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe
OPENAI_API_KEY=
GEMINI_API_KEY=
GOOGLE_API_KEY=
PAPERPIPE_LLM_MODEL=gpt-4o-mini
PAPERPIPE_EMBEDDING_MODEL=text-embedding-3-small
PAPERPIPE_PQA_INDEX_DIR=/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe/.pqa_index
```

- [x] Export `PAPER_DB_PATH` for smoke tests.

Run:

```bash
export PAPER_DB_PATH=/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe
papi path
```

Expected:

- `papi path` points to the AIResearch local paper DB path.

### Task 1.3: Run paperpipe smoke workflow

**Files:**

- Modify: `airesearch/data/paperpipe/`

- [x] Add one small test paper.

Run:

```bash
export PAPER_DB_PATH=/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/paperpipe
papi add 1706.03762
```

Expected:

- The paper is added or a clear model/API/config error is produced.

- [x] Verify formula/context access.

Run:

```bash
papi show 1706.03762 --level summary
papi show 1706.03762 --level eq
```

Expected:

- Summary and equation/context output are available, or missing capabilities are clearly identified.

- [x] Verify search.

Run:

```bash
papi search attention
papi index --backend search
papi search attention --backend search
```

Expected:

- Search finds the added paper.
- `papi index --backend search` builds `data/paperpipe/search.db` for 1 paper.

- [x] Verify RAG only after backend is configured.

Run:

```bash
papi ask "What problem does the Transformer solve?"
```

Expected:

- Answer cites paper evidence.
- Working config requires `text-embedding-v4`, `encoding_format=float`, explicit `--agent.agent_llm`, and LLM/embedding config JSON. Use `source activate.sh`, then call `airesearch_papi_index` and `airesearch_papi_ask`.

---

## Phase 2: AIResearch SQLite Ledger

**Status:** Done for Stage 2A ledger and batch ingest; later KG tables remain Phase 4 scope.

**Goal:** Create an auditable local ledger that maps paperpipe artifacts to AIResearch records.

**Technical Path:**

- Keep paperpipe as source of paper artifacts.
- Use AIResearch SQLite for supplementary state: source, run, candidate, provenance, graph, reports.
- Do not duplicate PDFs or raw paper content in SQLite.

### Task 2.1: Create package skeleton

**Files:**

- Create: `airesearch/pyproject.toml`
- Create: `airesearch/src/airesearch/__init__.py`
- Create: `airesearch/src/airesearch/config.py`
- Create: `airesearch/tests/test_config.py`

- [x] Define Python package metadata.
- [x] Implement config loading for `PAPER_DB_PATH` and `AIRESEARCH_DB_PATH`.
- [x] Test default path resolution.

### Task 2.2: Create SQLite schema

**Files:**

- Create: `airesearch/src/airesearch/schema.sql`
- Create: `airesearch/src/airesearch/db.py`
- Create: `airesearch/tests/test_schema.py`

**Tables:**

- `papers`
- `paper_sources`
- `paper_artifacts`
- `paper_chunks`
- `paper_equations`
- `paper_claims`
- `paper_citations`
- `research_topics`
- `research_runs`
- `research_candidates`
- `graph_entities`
- `graph_relations`
- `provenance`
- `api_cache`
- `jobs`

- [x] Write Stage 2A schema with stable primary keys and foreign keys.
- [x] Add migration/bootstrap function.
- [x] Test schema creation in a temporary SQLite database.

### Task 2.3: Sync paperpipe index

**Files:**

- Create: `airesearch/src/airesearch/paperpipe_sync.py`
- Create: `airesearch/tests/test_paperpipe_sync.py`

- [x] Read paperpipe `index.json`.
- [x] Upsert paper metadata into `papers`.
- [x] Hash and record `summary.md`, `equations.md`, `tldr.md`, `source.tex`, `paper.pdf` in `paper_artifacts`.
- [x] Preserve unknown paperpipe fields as JSON metadata.
- [x] Implement batch manifest parsing and per-item status tracking.
- [x] Implement CLI status summary for paper count, artifact count, latest sync, and latest ingest run.
- [x] Create local DB at `data/airesearch.sqlite3`.

---

## Phase 3: L1 Scheduled Discovery

**Status:** In progress for Stage 2B candidate discovery; automatic `papi add` remains disabled until user review.

**Goal:** Discover candidate papers automatically, score them, and add only selected papers through `papi add`.

**Stage 2B Policy:** Default candidate search window is the last 12 months. Papers from 2024-01-01 onward are allowed only when they are famous models or have strong backing from preferred companies, schools, scholars, venues, or released artifacts. Older papers are background-only by default.

**Technical Path:**

- OpenAlex provides broad discovery and metadata.
- Semantic Scholar provides seed expansion and paper recommendations.
- API responses are cached for 7 days.
- Candidate scoring happens before `papi add`.
- Every skipped candidate gets a reason.

### Task 3.1: Research topic CRUD

**Files:**

- Create: `airesearch/src/airesearch/topics.py`
- Create: `airesearch/tests/test_topics.py`

- [ ] Add topic create/list/update/delete functions.
- [ ] Validate keywords, exclude keywords, seeds, authors, venues, and frequency.
- [ ] Test duplicate topic names and invalid frequency handling.

### Task 3.2: OpenAlex discovery

**Files:**

- Create: `airesearch/src/airesearch/openalex.py`
- Create: `airesearch/tests/test_openalex.py`

- [ ] Implement query construction from topic fields.
- [ ] Cache responses in `api_cache`.
- [ ] Normalize candidate records into `research_candidates`.
- [ ] Test cache hit and miss behavior with mocked HTTP responses.

### Task 3.3: Semantic Scholar expansion

**Files:**

- Create: `airesearch/src/airesearch/semantic_scholar.py`
- Create: `airesearch/tests/test_semantic_scholar.py`

- [ ] Implement seed paper lookup and recommendation expansion.
- [ ] Add token-bucket limit for free tier behavior.
- [ ] Respect `Retry-After` on 429 responses.
- [ ] Test rate limiting and retry behavior with mocked HTTP responses.

### Task 3.4: Candidate scoring and ingest

**Files:**

- Create: `airesearch/src/airesearch/candidates.py`
- Create: `airesearch/src/airesearch/papi_runner.py`
- Create: `airesearch/tests/test_candidates.py`
- Create: `airesearch/tests/test_papi_runner.py`

- [ ] Score candidates with metadata gate, duplicate check, and abstract similarity.
- [ ] Mark rejected candidates with `filtered`, `duplicate`, or `low_score`.
- [ ] Run `papi add <id>` only for selected candidates.
- [ ] Record subprocess command, exit code, stderr/stdout summary, and artifact sync result.

---

## Phase 4: L2 Knowledge Graph And Provenance

**Status:** Not started

**Goal:** Extract claims, methods, datasets, metrics, tasks, equations, and evidence links from paperpipe artifacts.

**Technical Path:**

- Start with SQLite adjacency tables.
- Extraction input comes from `summary.md`, `equations.md`, and selected chunks.
- Every extracted entity and relation carries provenance.
- LLM extraction is cached by text hash, task type, model, and prompt version.

### Task 4.1: Chunk and equation ledger

**Files:**

- Create: `airesearch/src/airesearch/artifacts.py`
- Create: `airesearch/tests/test_artifacts.py`

- [ ] Parse sections from `summary.md`.
- [ ] Parse equation blocks from `equations.md`.
- [ ] Create stable chunk IDs using paper ID, section, ordinal, and text hash.
- [ ] Record artifacts without storing full PDFs in SQLite.

### Task 4.2: Extraction service

**Files:**

- Create: `airesearch/src/airesearch/extraction.py`
- Create: `airesearch/tests/test_extraction.py`

- [ ] Define extraction input JSON with `paper_id`, `chunk_ids`, `task_type`, `source_files`, and `provenance_required`.
- [ ] Define output schema for claims, entities, relations, confidence, and evidence.
- [ ] Cache extraction outputs for 7 days.
- [ ] Test schema validation and cache reuse.

### Task 4.3: Graph writes and claim trace

**Files:**

- Create: `airesearch/src/airesearch/graph.py`
- Create: `airesearch/tests/test_graph.py`

- [ ] Upsert entities by normalized type/name.
- [ ] Upsert graph relations with provenance IDs.
- [ ] Implement `claim_trace` lookup from claim text to evidence.
- [ ] Test relation insertion and trace output.

---

## Phase 5: L3 Reports

**Status:** Not started

**Goal:** Generate auditable paper cards, research digests, research maps, and gap analyses.

**Technical Path:**

- Reports must separate extracted facts, model summaries, and speculative hypotheses.
- Every important claim must link to provenance.
- Start with Markdown reports; only add HTML/UI after content workflow is stable.

### Task 5.1: Paper Card

**Files:**

- Create: `airesearch/src/airesearch/reports/paper_card.py`
- Create: `airesearch/tests/test_paper_card.py`

- [ ] Generate one structured Markdown card per paper.
- [ ] Include title, authors, year, venue, IDs, summary, method, datasets, metrics, equations, claims, limitations, and provenance links.
- [ ] Test report rendering with fixture graph data.

### Task 5.2: Research Digest

**Files:**

- Create: `airesearch/src/airesearch/reports/digest.py`
- Create: `airesearch/tests/test_digest.py`

- [ ] Generate digest for a topic and time window.
- [ ] Include selected papers, skipped candidates, why each paper matters, and suggested reading order.
- [ ] Test digest rendering with fixture candidates and papers.

### Task 5.3: Research Map and Gap Analysis

**Files:**

- Create: `airesearch/src/airesearch/reports/map.py`
- Create: `airesearch/src/airesearch/reports/gap.py`
- Create: `airesearch/tests/test_map.py`
- Create: `airesearch/tests/test_gap.py`

- [ ] Group papers by method, dataset, task, and citation relation.
- [ ] Identify missing benchmark/method combinations from graph gaps.
- [ ] Mark hypotheses as speculative.
- [ ] Test map and gap output with fixture graph data.

---

## Phase 6: Scale And Optional Integrations

**Status:** Not started

**Trigger Conditions:**

- More than 5000 papers.
- More than 3-hop graph queries are common.
- SQLite recursive queries become too slow.
- Citation parsing quality becomes a blocker.
- PaperQA2 search latency or recall becomes a blocker.

**Optional Paths:**

- Kuzu for graph queries.
- GROBID for citation parsing.
- Separate vector store only if paperpipe RAG is insufficient.
- HTML dashboard only after reports are stable.

---

## Operating Rules

- Never bypass `papi add` for paper ingestion unless paperpipe cannot handle a specific source.
- Never treat `papi ask` as available until the RAG backend is verified.
- Never write cloud API keys into committed files.
- Never upload local PDFs, notes, or SQLite DBs to unknown services.
- Always record run inputs, selected candidates, skipped candidates, thresholds, errors, and report paths.
- Always keep generated hypotheses labeled as hypotheses.

## Status Update Procedure

When work progresses:

1. Move the active item into `In Progress`.
2. Check off completed task steps.
3. Add new blockers under the phase where they occurred.
4. Update `Current Status`.
5. Add a short entry under `Completed` when a phase or task is finished.


### Phase 1 Execution Notes

- `uv` is not installed, so Phase 1 used the local `.venv` fallback.
- Core install succeeded with `paperpipe==1.9.3`.
- Narrow extras installed: `llm`, `figures`, `mcp`.
- `paperpipe[all]` is not suitable for this MVP environment because it pulls LEANN, torch, CUDA, PaperQA full extras, docling, and qdrant.
- `papi path` resolves to `airesearch/data/paperpipe` when `PAPER_DB_PATH` is set.
- `papi models` runs but probes 0 combinations without provider credentials.
- `papi add 1706.03762` succeeded and downloaded PDF plus LaTeX source; LLM-generated name, TLDR, summary, equations, and tags failed only because no Gemini/Google API key was configured.
- `papi show 1706_03762 --level summary` returns metadata-derived summary fallback.
- `papi show 1706_03762 --level eq` returns extracted Transformer equations.
- `papi search attention` finds the paper across title, abstract, summary, and equations.
- `papi ask` reaches PaperQA2 when `.venv/bin` is on `PATH`.
- `papi index --backend search` succeeds and creates `search.db`.
- `papi index --backend pqa` succeeds with `text-embedding-v4` and `encoding_format=float`.
- `papi ask "What problem does the Transformer solve?"` succeeds and returns cited evidence from `1706_03762`.

