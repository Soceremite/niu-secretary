# AIResearch Roadmap

**Goal:** Build 牛秘书 AIResearch 研知库 as a launchable local research-paper system on top of `paperpipe` / `papi`, with discovery, auditable ingestion, knowledge extraction, provenance, reports, and static publishing.

**Current launch artifact:** `exports/site-current/index.html` after publish; source bundle is `exports/mvp-current/bundle/index.html`.

**Current real corpus:** 202 papers, 1553 extracted facts, 0 fact-audit hard failures, 0 MVP pipeline fact failures.

**Operating principle:** do not skip launch-critical capability, but avoid getting stuck on tiny polish items. Build the whole usable path first, then harden the highest-risk submodules.

---

## Status Overview

| Layer | Status | What Exists | Main Gap |
| --- | --- | --- | --- |
| L0 paper grounding | Done | `paperpipe==1.9.3`, local paper DB, `papi add/list/show/search/index/ask` smoke-tested | None for MVP |
| L1 discovery and ingest | Mostly done | profiles, OpenAlex/arXiv/Semantic Scholar/SerpAPI providers, scoring, candidate export, canonical review, approved ingest, one-command launch refresh, scheduled wrapper | real corpus expansion run beyond the current 11-paper local corpus |
| L2 knowledge graph and provenance | Done for MVP | paper cards, code links, graph rows, fact extraction, audit, evidence repair, artifact ledger, claim trace | trace lookup UI polish |
| L3 reports | Done for MVP | digest, map, gap analysis, synthesis, narrative, clustering, review packets, report bundle, cross-paper relations, static navigation | report quality/editorial polish |
| Launch pipeline | Done for MVP | `run-launch-refresh` with optional unified progress, run history/log output, publish diff metadata, `run-mvp-pipeline`, static HTML site export, local publish/serve commands, static-host config generation, deploy/rollback script generation | None for MVP |
| Operations | MVP ready | launch runbook, DB backup command, health check command, scheduled refresh wrapper generator, local env and developer docs, external deploy rollback scripts | None for MVP |

---

## Development Order

This is the intended order from foundation to launch. Completed work stays checked; incomplete work is ordered by上线 priority.

### 0. Scope And Foundation

- [x] Audit upstream `paperpipe` / `papi` capability boundary.
- [x] Create `REQUIREMENTS.md`, `SKILL.md`, and ingestion-stack decision note.
- [x] Keep SQLite as MVP ledger; keep Kuzu, separate vector DB, GROBID, MinerU, and heavy local GPU dependencies optional.
- [x] Create local `.venv`, `.env.example`, and `activate.sh` workflow.

### 1. L0 Paperpipe Integration

- [x] Install `paperpipe==1.9.3` with focused extras `llm,figures,mcp`.
- [x] Store local paper artifacts under `data/paperpipe/`.
- [x] Verify `papi add/list/show/search/index/ask` on `1706.03762`.
- [x] Confirm separated LLM and embedding configuration works through local environment variables.

### 2. L1 Ledger, Discovery, Candidate Review, Ingest

- [x] Implement SQLite bootstrap and config loading.
- [x] Sync paperpipe metadata and artifacts into `data/airesearch.sqlite3`.
- [x] Implement batch ingest manifest workflow with per-item success/failure/duplicate/skipped accounting.
- [x] Implement discovery profiles for multimodal, unified multimodal, world models, diffusion, and embodied AI / VLA robotics.
- [x] Implement OpenAlex, arXiv, Semantic Scholar, and opt-in SerpAPI Google Scholar providers.
- [x] Support Google Scholar / SerpAPI result requests up to 50 per profile, still quota-guarded and opt-in.
- [x] Implement provider cache and provider-level error handling.
- [x] Implement candidate scoring by recency, backing, venue/source, topic match, and artifact signals.
- [x] Implement canonical candidate dedupe, selected/rejected review state, approved manifest export, and approved batch ingestion.
- [x] Filter already-ingested papers out of automatic Top-N canonical selection so corpus expansion targets new papers.
- [x] Add one-command fresh corpus refresh: discover across all profiles, dedupe, select by threshold, export approved manifest, ingest, sync, then run MVP pipeline and publish.
- [x] Add scheduled execution wrapper for daily/weekly discovery refresh with run logs.
- [x] Implement URL normalization pipeline for non-arxiv sources (NeurIPS proceedings, CVPR openaccess, preprints.org, figshare, generic DOIs) that ``papi add`` cannot resolve directly. (2026-06-10)
- [x] Add clearer candidate rejection reasons in exports for fast manual review.

### 3. L2 Knowledge Graph, Provenance, Facts

- [x] Generate deterministic paper cards from paperpipe artifacts.
- [x] Extract and normalize GitHub code links from metadata and source text.
- [x] Write paper, code repository, and relation rows into graph tables.
- [x] Implement fixture and OpenAI-compatible research fact providers.
- [x] Cache real extraction by evidence-pack hash.
- [x] Add dry-run mode and concurrent LLM calls with serial DB writes.
- [x] Extract real facts across the expanded local corpus with `qwen3.7-max` through the configured OpenAI-compatible endpoint.
- [x] Audit extracted facts with hard/soft issue classification.
- [x] Repair evidence source paths and reach 0 hard failures / 0 source-path warnings.
- [x] Add richer chunk/equation/citation ledger from paperpipe artifacts so reports can cite more than summary/source paths.
- [x] Add `claim-trace` command to inspect one claim/fact back to paper, artifact, source path, and graph relations.
- [x] Add citation/code/method/dataset/benchmark cross-paper relation summaries for stronger research maps.

### 4. L3 Reports, Clustering, Review

- [x] Generate deterministic Research Digest Markdown/JSON.
- [x] Generate deterministic Research Map Markdown/JSON.
- [x] Generate deterministic Gap Analysis Markdown/JSON.
- [x] Generate deterministic Research Synthesis Markdown/JSON.
- [x] Generate deterministic Narrative Report Markdown/JSON.
- [x] Generate Report Bundle with `manifest.json` and `index.md`.
- [x] Repair evidence source paths before bundle generation.
- [x] Generate token and semantic research clusters.
- [x] Add OpenAI-compatible embedding provider for semantic clusters.
- [x] Calibrate semantic thresholds and select default threshold `0.82`.
- [x] Generate cluster review packets, edit review status, summarize accepted clusters, and include reviewed clusters in bundles.
- [x] Generate dependency-free static `index.html` for report bundles.
- [x] Add static-site search/filter with generated `search-index.json`.
- [x] Add provenance jump links with generated `provenance-index.json`.
- [x] Improve static site navigation for larger corpora: paper list and cluster list.
- [x] Add report diff/regeneration metadata so a refreshed corpus can be compared with the previous publish.

### 5. MVP Launch Pipeline

- [x] Implement `run-mvp-pipeline` as the fast local publish path.
- [x] Pipeline steps: init DB, sync paperpipe, extract paper cards, extract code links, reuse or refresh facts, audit facts, repair evidence, cluster, review packet, bundle, static site.
- [x] Real local run produced `exports/mvp-current/bundle/index.html` with 202 papers, 1553 facts, and 21 launch artifacts.
- [x] Add `publish-static-site` command to copy the latest bundle to a stable public directory such as `exports/site-current/`.
- [x] Add `serve-report-site` command for local HTTP preview.
- [x] Add `publish.json` manifest with source bundle, output path, generated time, file count, and entrypoint.
- [x] Add `run-launch-refresh` command to discover, dedupe, select, export, ingest, sync, run the MVP pipeline, publish, and write a run manifest.
- [x] Add optional unified progress display for `run-launch-refresh --progress`.
- [x] Add optional deployment target for nginx or another static host after local publish is stable.
- [x] Add external static deploy scripts with pre-deploy snapshots and rollback automation.

### 6. Operations And Hardening

- [x] Maintain `DEVELOPMENT.md` for implemented modules, commands, environment, verification, and feature logs.
- [x] Add launch runbook: refresh corpus, run pipeline, publish, verify, rollback.
- [x] Add concise log files for discovery, ingest, extraction, report generation, and publish.
- [x] Add DB backup/export command before destructive or large refresh runs.
- [x] Add minimal health check that validates DB, paperpipe path, latest bundle, site entrypoint, and required environment variables without printing secrets.

---

## Phase 3.1-3.4 Reconciliation

The old `PLAN.md` listed Phase 3.1-3.4 as unchecked even though much of that work was later implemented under Stage 2B/2C modules. This section records the accurate status.

| Old Item | Current Status | Implemented By | Remaining Gap |
| --- | --- | --- | --- |
| 3.1 Research topic CRUD | Partially covered | `profiles.py`, `seed-profiles`, default research profiles | full arbitrary topic CRUD is still not built; for launch, profile-based discovery is enough |
| 3.2 OpenAlex discovery | Done for MVP | `providers.py`, `discovery.py`, provider cache | broader query tuning and source-specific quality tuning |
| 3.3 Semantic Scholar expansion | Done for MVP | `providers.py`, provider error handling and rate-limit behavior | deeper seed expansion and smarter retry/backoff telemetry |
| 3.4 Candidate scoring and ingest | Mostly done | `candidates.py`, `canonical_candidates.py`, `batch.py`, approved manifest ingest | one-command fresh corpus refresh and clearer rejection exports |

Conclusion: Phase 3 is no longer "not implemented"; it is "MVP implemented, automation/hardening pending."

---

## Completed Feature Inventory

### Core Modules

- `config.py`: local path and environment config.
- `db.py`, `schema.sql`: SQLite schema and bootstrap.
- `paperpipe_sync.py`: sync paperpipe paper/artifact state into AIResearch.
- `batch.py`: approved manifest ingestion through `papi`; integrated URL normalizer pre-pass (2026-06-10).
- `url_normalizer.py`: resolve NeurIPS/CVPR/preprints/figshare/DOI URLs to arXiv IDs or titles; 7-category classifier with per-category resolver chain + OpenAlex/arXiv API fallback (2026-06-10).
- `profiles.py`, `discovery.py`, `providers.py`, `provider_cache.py`: discovery profiles, provider calls, caching, and normalized candidates.
- `candidates.py`, `canonical_candidates.py`: scoring, dedupe, review status, and approved candidate export.
- `knowledge_graph.py`: deterministic paper cards and graph/provenance rows.
- `code_links.py`: GitHub repository extraction and graph integration.
- `fact_extraction.py`: fixture and OpenAI-compatible fact extraction, caching, concurrency.
- `fact_audit.py`: fact quality audit.
- `evidence_repair.py`: evidence source-path repair.
- `embeddings.py`: OpenAI-compatible embedding provider.
- `research_digest.py`, `research_map.py`, `research_gap_analysis.py`, `research_synthesis.py`, `research_narrative.py`: deterministic reports.
- `research_clusters.py`, `research_cluster_calibration.py`, `research_cluster_review.py`, `research_review_editor.py`, `research_review_summary.py`: clustering and human-review workflow.
- `research_bundle.py`, `research_site.py`: bundle, static site export, search/provenance/navigation indexes.
- `mvp_pipeline.py`: one-command MVP pipeline orchestration.
- `static_publish.py`: stable local static-site publish, preview support, and static-host config generation.
- `launch_refresh.py`: one-command corpus refresh and publish orchestration.
- `launch_ops.py`: launch health check and SQLite backup support.
- `cli.py`: command-line surface.

### Main Commands

```bash
python -m airesearch.cli init-db
python -m airesearch.cli sync-paperpipe
python -m airesearch.cli batch-ingest manifests/approved-stage-2c.txt
python -m airesearch.cli normalize-url "https://proceedings.neurips.cc/..."
python -m airesearch.cli status
python -m airesearch.cli seed-profiles
python -m airesearch.cli discover-candidates --profile diffusion_models --provider arxiv --limit 50
python -m airesearch.cli dedupe-candidates
python -m airesearch.cli select-canonical-candidates --limit 10 --min-score 0.70
python -m airesearch.cli export-approved-candidates --out manifests/approved-stage-2c.txt
python -m airesearch.cli extract-paper-cards
python -m airesearch.cli extract-code-links
python -m airesearch.cli extract-artifact-ledger
python -m airesearch.cli export-artifact-ledger --out exports/artifact-ledger-current.md
python -m airesearch.cli extract-research-facts --provider openai-compatible --concurrency 5
python -m airesearch.cli claim-trace --fact-id 1
python -m airesearch.cli audit-research-facts
python -m airesearch.cli repair-evidence-source-paths --apply --out exports/evidence-source-path-repair-current.jsonl
python -m airesearch.cli generate-research-digest --out exports/research-digest-current.md
python -m airesearch.cli generate-research-map --out exports/research-map-current.md
python -m airesearch.cli generate-research-relations --out exports/research-relations-current.md
python -m airesearch.cli generate-gap-analysis --out exports/research-gap-analysis-current.md
python -m airesearch.cli generate-research-synthesis --out exports/research-synthesis-current.md
python -m airesearch.cli generate-narrative-report --out exports/research-narrative-current.md
python -m airesearch.cli generate-research-clusters --mode semantic --semantic-threshold 0.82 --out exports/research-clusters-semantic-current.md
python -m airesearch.cli generate-cluster-review --clusters exports/research-clusters-semantic-current.json --out exports/research-cluster-review-current.md
python -m airesearch.cli generate-report-bundle --out-dir exports/research-report-current
python -m airesearch.cli generate-report-site --bundle-dir exports/research-report-current
python -m airesearch.cli run-mvp-pipeline --out-dir exports/mvp-current
python -m airesearch.cli run-launch-refresh --limit-per-profile 50 --select-limit 10 --min-score 0.60 --out-dir exports/mvp-current --site-dir exports/site-current --progress
python -m airesearch.cli health-check --site-dir exports/site-current --require-fact-provider
python -m airesearch.cli backup-db --out-dir backups --label before-launch-refresh
python -m airesearch.cli write-refresh-wrapper --out scripts/airesearch-refresh.sh --schedule daily
python -m airesearch.cli publish-static-site --source-dir exports/mvp-current/bundle --out-dir exports/site-current
python -m airesearch.cli serve-report-site --dir exports/site-current --host 127.0.0.1 --port 8765
python -m airesearch.cli write-static-host-config --site-dir exports/site-current --out-dir deploy --base-path /niu-secretary/airesearch/ --deploy-root /var/www/html/niu-secretary/airesearch
python -m airesearch.cli write-static-deploy-scripts --site-dir exports/site-current --out-dir deploy --deploy-root /var/www/html/niu-secretary/airesearch
sudo rsync -av --delete /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/exports/site-current/ /var/www/html/niu-secretary/airesearch/
```

Large corpus expansion example:

`--select-limit 100` selects up to 100 not-yet-ingested canonical candidates; already-ingested papers are skipped before the approved manifest is written.

```bash
python -m airesearch.cli run-launch-refresh \
  --provider openalex \
  --provider arxiv \
  --provider semantic_scholar \
  --provider google_scholar \
  --limit-per-profile 100 \
  --select-limit 100 \
  --min-score 0.60 \
  --refresh-facts \
  --fact-error-policy warn \
  --semantic \
  --semantic-threshold 0.82 \
  --out-dir exports/mvp-current \
  --site-dir exports/site-current \
  --progress
```

---

## Current Focus

**2026-06-10:** URL normalization pipeline (`url_normalizer.py`) implemented and integrated into `batch.py` / `launch_refresh.py`. Of 14 previously-failed papers from the 100-paper batch, 10 now resolve (2 to exact arXiv IDs, 8 to searchable titles). 2 CVPR papers fail due to CVF server SSL issues; 2 are non-AI papers that should not be ingested. Static-site corpus navigation, static host config generation, source-specific discovery tuning, and method/dataset/benchmark relation analytics are implemented. Full test suite: 242 passed.

Stage 5C is implemented. Candidate review exports, static-site search/filter, provenance jump links, claim trace, larger-corpus navigation, static-host config generation, external deploy rollback scripts, source-specific discovery tuning, and richer relation analytics are now available. Optional graph/vector/parser backends are deferred until measured scale or artifact-quality limits justify them.

Why this is next:

- Stage 5A provides one command for discovery, canonical selection, approved ingest, MVP generation, and static publish.
- Stage 5B adds the runbook, preflight/postflight health check, and DB backup before large refreshes.
- Stage 5C adds unattended-run support with a refresh wrapper, concise logs, run history, and publish diff metadata.

Stage 5A deliverables:

- [x] `run-launch-refresh` CLI command.
- [x] Discover across all seeded profiles or a selected profile list.
- [x] Dedupe candidates and select by threshold/limit.
- [x] Export approved manifest, run batch ingest, sync paperpipe, run MVP pipeline, and publish static site.
- [x] Write a run manifest/log with counts, selected papers, skipped papers, provider errors, and output paths.
- [x] Show optional unified progress for long refresh runs, including discovery, ingest, facts, report generation, and publish.

Stage 5B deliverables:

- [x] Launch runbook in `DEVELOPMENT.md`.
- [x] `health-check` command that validates DB, paperpipe path, output site, and required env names without printing secrets.
- [x] `backup-db` command before large refreshes.

Stage 5C deliverables:

- [x] Optional scheduled wrapper for daily/weekly refresh with concise logs.
- [x] Persist launch run history under `logs/` and `exports/run-history/`.
- [x] Add report/site diff metadata so the latest publish can be compared with the previous publish.

---

## Backlog By Priority

### P0: Required Before First Real上线

- [x] Fresh corpus refresh command across all profiles.
- [x] Launch runbook in `DEVELOPMENT.md`.
- [x] Environment/health check command that does not print secrets.
- [x] DB backup/export before large refreshes.

### P1: Required For A Useful Research Product

- [x] Larger corpus expansion beyond the initial 11 papers.
- [x] Candidate rejection reason export and faster manual review.
- [x] Search/filter in static site.
- [x] Provenance jump links from reports to paper/artifact/source path.
- [x] Static-site paper and cluster navigation for larger corpora.
- [x] Claim trace CLI.
- [x] Report regeneration diff.

### P2: Scale And Quality

- [x] Richer citation parsing, equations ledger, and chunk ledger.
- [x] Cross-paper method/dataset/benchmark/citation analytics.
- [x] Better source-specific discovery tuning.

Deferred optional evaluations:

- Kuzu graph backend only if SQLite graph queries become too slow.
- GROBID/MinerU only if paperpipe artifacts are insufficient.
- Separate vector store only if paperpipe RAG becomes insufficient.

---

## Operating Rules

- Never bypass `papi add` for paper ingestion unless paperpipe cannot handle a specific source.
- Never treat `papi ask` as available until the RAG backend is verified.
- Never write cloud API keys into committed files.
- Never print API keys in logs, docs, test output, or final answers.
- Always record run inputs, selected candidates, skipped candidates, thresholds, errors, and report paths.
- Always label generated hypotheses as hypotheses.
- Keep `DEVELOPMENT.md` updated when commands, modules, outputs, environment variables, or launch procedures change.

---

## Historical Notes

- `paperpipe[all]` was intentionally avoided because it pulls heavy optional dependencies such as LEANN, torch/CUDA, docling, and qdrant.
- Real arXiv discovery previously stored 237 candidates across 5 profiles and exported Top 100 manifests.
- Approved canonical candidate workflow ingested 10 additional papers through paperpipe.
- Initial real Stage 2D extraction produced 79 facts over 11 papers using `qwen3.7-max` through a Bailian/DashScope-compatible endpoint.
- Latest real Stage 4A MVP pipeline completed with:

```text
papers=202 cards=202 facts=1553 repaired=0 artifacts=21 site=exports/mvp-current/bundle/index.html
```
