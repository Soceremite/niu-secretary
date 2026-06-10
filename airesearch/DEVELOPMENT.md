# AIResearch Development Notes

This document is the maintained developer reference for AIResearch. Update it whenever a new feature changes commands, environment variables, outputs, testing expectations, or operating assumptions.

## Environment

Activate the local environment before running real workflows:

```bash
cd /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch
source ./activate.sh
```

Important variables loaded from `.env`:

```bash
PAPER_DB_PATH
AIRESEARCH_DB_PATH
AIRESEARCH_FACT_MODEL
OPENAI_BASE_URL
OPENAI_API_KEY
AIRESEARCH_EMBEDDING_MODEL
AIRESEARCH_EMBEDDING_BASE_URL
AIRESEARCH_EMBEDDING_API_KEY
AIRESEARCH_EMBEDDING_BATCH_SIZE
SERPAPI_API_KEY
```

Do not print API keys in logs, docs, or test output.

## Verification Commands

Run focused tests from `airesearch/`:

```bash
.venv/bin/python -m pytest tests/test_launch_ops.py tests/test_launch_refresh.py tests/test_static_publish.py tests/test_research_site.py tests/test_research_relations.py tests/test_mvp_pipeline.py tests/test_cli.py -q
```

Run the full suite:

```bash
.venv/bin/python -m pytest -q
```

Validate generated JSON:

```bash
.venv/bin/python -m json.tool exports/research-clusters-current.json >/tmp/research-clusters.json
```

## Completed Feature Inventory

This section records the code and behavior that already exists. Keep it current when new modules, commands, or export contracts are added.

### L0 Paperpipe Grounding

- Local paper storage lives under `data/paperpipe/` through `PAPER_DB_PATH`.
- `paperpipe==1.9.3` is installed in `.venv` with focused extras `llm,figures,mcp`.
- `papi add/list/show/search/index/ask` was smoke-tested on `1706.03762`.
- AIResearch treats paperpipe as the L0 source of paper artifacts, not as the owner of scheduled discovery, provenance, knowledge graph, or reporting.

### Stage 2A SQLite Ledger And Batch Ingest

- Core modules: `config.py`, `db.py`, `paperpipe_sync.py`, `batch.py`, `cli.py`.
- SQLite schema tracks papers, paper artifacts, sync events, ingest runs, discovery, candidates, graph rows, provenance, facts, cache, and report inputs.
- Commands implemented:
  - `init-db`
  - `sync-paperpipe`
  - `batch-ingest`
  - `status`
- Batch ingest shells out to `papi`, records success/failure/duplicate/skipped counts, then syncs paperpipe state into the AIResearch ledger.

### Stage 2B Discovery

- Core modules: `profiles.py`, `discovery.py`, `providers.py`, `provider_cache.py`, `candidates.py`.
- Default profiles cover multimodal foundation models, unified multimodal understanding/generation, world models, diffusion models, and embodied AI / VLA robotics.
- Providers implemented:
  - OpenAlex
  - arXiv
  - Semantic Scholar
  - opt-in Google Scholar through SerpAPI with SQLite cache and quota guard
- Provider request caps per profile: OpenAlex up to 200, arXiv up to 100, Semantic Scholar up to 100, and Google Scholar / SerpAPI up to 50.
- Candidate scoring uses recency, backing, source/venue, topic relevance, and artifact signals.
- Source-specific tuning prefers directly resolvable arXiv, Semantic Scholar, OpenAlex DOI/proceedings, and resolvable Google Scholar entries over weak provider-only identifiers.
- Provider names are not included in semantic topic/backing text matching; source quality is scored separately so `google_scholar` does not accidentally count as a Google backing signal.
- Automatic Top-N canonical selection skips papers already present in the local `papers`/`paper_sources` ledger by matching arXiv ID, DOI, Semantic Scholar ID, OpenAlex ID, and title/year.
- Commands implemented:
  - `seed-profiles`
  - `discover-candidates`
  - `list-candidates`
  - `export-candidates`
- Real local discovery stored 237 arXiv candidates and exported Top 100 manifests for all 5 profiles.

### Stage 2C Canonical Candidate Workflow

- Core module: `canonical_candidates.py`.
- Candidate papers are deduplicated into deterministic canonical identities with provider/profile aggregation.
- Review statuses: `candidate`, `selected`, `rejected`.
- Commands implemented:
  - `dedupe-candidates`
  - `list-canonical-candidates`
  - `export-canonical-candidates`
  - `set-canonical-status`
  - `select-canonical-candidates`
  - `export-approved-candidates`
  - `export-candidate-review`
- Candidate review exports write JSON/Markdown reason reports for selected, already-ingested, manually rejected, below-threshold, and Top-N overflow candidates.
- Real local workflow selected top canonical candidates, exported `manifests/approved-stage-2c.txt`, batch-ingested 10 approved papers, and synced the ledger.

### Stage 2D Knowledge Graph, Code Links, And Facts

- Core modules: `knowledge_graph.py`, `code_links.py`, `artifact_ledger.py`, `fact_extraction.py`, `claim_trace.py`, `fact_audit.py`, `evidence_repair.py`.
- Paper cards create deterministic L2 paper summaries, graph nodes, graph edges, and provenance rows from paperpipe artifacts.
- Code-link extraction normalizes GitHub repository URLs from metadata and source text, then integrates repositories into paper cards and KG rows.
- Artifact ledger extraction creates deterministic `paper_chunks`, `paper_equations`, and `paper_citations` rows from registered paperpipe artifacts.
- Research fact extraction supports:
  - fixture provider for tests
  - OpenAI-compatible provider for real extraction
  - response caching by evidence-pack hash
  - dry-run mode
  - concurrent LLM calls with serial DB writes
  - `--fact-error-policy warn` to continue when isolated LLM provider calls fail
- Fact types: `method`, `dataset`, `benchmark`, `claim`, `limitation`.
- Commands implemented:
  - `extract-paper-cards`
  - `list-paper-cards`
  - `export-paper-cards`
  - `extract-code-links`
  - `list-code-links`
  - `export-code-links`
  - `extract-artifact-ledger`
  - `export-artifact-ledger`
  - `extract-research-facts`
  - `list-research-facts`
  - `export-research-facts`
  - `claim-trace`
  - `audit-research-facts`
  - `repair-evidence-source-paths`
- `claim-trace` is read-only and traces one fact by `--fact-id`, or by `--paper-key` with optional `--type` and `--query`, to paper metadata, evidence quote, evidence source path, matching artifacts, artifact ledger matches, code links, KG relations, and KG provenance. It supports Markdown and JSON output.
- Initial real extraction produced 79 facts across 11 papers using `qwen3.7-max` through a Bailian/DashScope-compatible endpoint.
- Current expanded local corpus has 202 papers and 1553 facts.
- Evidence repair resolved all missing source paths; the latest fact audit has 0 hard failures and 0 soft warnings.

### Stage 3A-3G Deterministic Research Reports

- Core modules: `research_digest.py`, `research_map.py`, `research_relations.py`, `research_gap_analysis.py`, `research_synthesis.py`, `research_narrative.py`, `research_bundle.py`, `research_site.py`.
- Reports are generated deterministically from audited paper cards, code links, research facts, and provenance.
- Commands implemented:
  - `generate-research-digest`
  - `generate-research-map`
  - `generate-research-relations`
  - `generate-gap-analysis`
  - `generate-research-synthesis`
  - `generate-narrative-report`
  - `generate-report-bundle`
  - `generate-report-site`
- `generate-research-relations` summarizes cross-paper shared code repositories, shared method facts, shared dataset facts, shared benchmark facts, and citation-ledger coverage from `paper_citations` without claiming real citation edges before citation keys are matched to papers.
- Each report supports Markdown and JSON output except the bundle command, which writes a directory containing both formats plus `manifest.json` and `index.md`.
- `generate-report-site` adds a dependency-free `index.html` plus `search-index.json`, `provenance-index.json`, and `navigation-index.json` for local preview or static hosting.
- Static sites include browser-only search/filter controls. The search index is generated from bundle artifact metadata and Markdown snippets; no backend service is required.
- Static sites include a Provenance section built from report JSON `paper_key`, `evidence_source_path`, and `code_links` fields, with jump links back to the source report and JSON artifact.
- Static sites include a Corpus Navigation section built from report JSON papers and clusters so larger corpora can be browsed without scanning every report.
- Current report corpus: 202 papers and 1553 facts.

### Stage 3H-3P Clusters And Human Review

- Core modules: `embeddings.py`, `research_clusters.py`, `research_cluster_calibration.py`, `research_cluster_review.py`, `research_review_editor.py`, `research_review_summary.py`.
- Token clustering groups facts by deterministic token/Jaccard similarity.
- Semantic clustering uses an OpenAI-compatible embedding provider loaded from:
  - `AIRESEARCH_EMBEDDING_MODEL`
  - `AIRESEARCH_EMBEDDING_BASE_URL`
  - `AIRESEARCH_EMBEDDING_API_KEY`
  - `AIRESEARCH_EMBEDDING_BATCH_SIZE`
- Real semantic embedding uses DashScope `text-embedding-v4` with batch size 10.
- Semantic threshold calibration evaluates `0.70, 0.75, 0.80, 0.82, 0.85, 0.90` in one embedding pass.
- Default recommendation policy chooses the highest threshold with at least 3 clusters, at least 6 clustered facts, and largest cluster size at most 3; current recommendation is `0.82`.
- Cluster review packets are human-editable JSON/Markdown artifacts with `review_status` and `review_notes`.
- Valid review statuses: `pending`, `accepted`, `rejected`, `needs_revision`.
- `set-cluster-review-status` updates one cluster review item into a new JSON file; it does not mutate the source packet.
- Reviewed cluster summary exports only `accepted` clusters as downstream-approved evidence.
- `generate-report-bundle --review-packet` optionally includes `reviewed-clusters.md` and `reviewed-clusters.json` in the report bundle.
- Commands implemented:
  - `generate-research-clusters`
  - `calibrate-research-clusters`
  - `generate-cluster-review`
  - `set-cluster-review-status`
  - `summarize-cluster-review`

### Stage 4A MVP Launch Pipeline

- Core modules: `mvp_pipeline.py`, `research_site.py`.
- `run-mvp-pipeline` is the fast publish path for launch: it syncs paperpipe, extracts cards/code links/artifact ledger rows, reuses existing facts unless `--refresh-facts` is set, audits facts, repairs evidence paths, generates clusters/review packet/report bundle, and writes a static `index.html`.
- Default output is `exports/mvp-current/`; the deployable entry point is `exports/mvp-current/bundle/index.html`.
- Latest real local MVP export completed over 202 papers and 1553 facts with no new LLM calls.

### Stage 4B Static Publish And Local Preview

- Core module: `static_publish.py`.
- `publish-static-site` copies a generated bundle to a stable publish directory, defaulting from `exports/mvp-current/bundle/` to `exports/site-current/`.
- The publish step validates that the source contains both `index.html` and `manifest.json`.
- The publish directory is cleaned by default so stale files from old reports do not remain; use `--no-clean` only for debugging.
- `publish.json` records `generated_at`, source bundle, output directory, entrypoint, file count, and the published file list.
- `publish-diff.json` records added, removed, changed, and unchanged site files versus the previous publish, ignoring generated publish manifests.
- `serve-report-site` serves the published directory over local HTTP for preview.
- `write-static-host-config` writes a niu-secretary nginx `location` snippet and manifest under `deploy/` by default. It does not copy files into `/var/www`, modify system nginx files, or reload services.
- `write-static-deploy-scripts` writes `deploy-airesearch.sh`, `rollback-airesearch.sh`, and `static-deploy-scripts.json`. The deploy script snapshots the current external deploy root before rsync; the rollback script restores the latest or named snapshot.

### Stage 5A Launch Refresh Automation

- Core module: `launch_refresh.py`.
- `run-launch-refresh` is the one-command refresh-and-publish path for launch.
- The command seeds profiles, runs discovery across all profiles by default, materializes canonical candidates, selects by `--select-limit` and `--min-score`, exports `manifests/approved-launch-refresh-current.txt`, writes candidate review reports, runs batch ingest when approved papers exist, syncs paperpipe, runs the MVP pipeline, publishes to `exports/site-current/`, and writes `exports/launch-refresh-current.json`.
- `--select-limit` targets not-yet-ingested canonical candidates. Existing local papers are skipped before the approved manifest is written, so `--select-limit 100` attempts to add 100 new papers when enough fresh candidates are available.
- Candidate review reports are written to `exports/mvp-current/candidate-review.json` and `exports/mvp-current/candidate-review.md` by default. Override with `--candidate-review` and `--candidate-review-md`.
- Default discovery providers are OpenAlex, arXiv, and Semantic Scholar. Google Scholar / SerpAPI is opt-in with `--provider google_scholar`.
- Use `--progress` for long refreshes to show one unified progress bar on stderr while keeping the final stdout summary machine-readable.
- If no approved candidates are exported, batch ingest is skipped and the command still syncs, regenerates the MVP bundle, and republishes the current site.
- The run manifest records profile names, provider names, discovery counts and provider errors, canonical/selected/approved counts, batch result, sync result, MVP result, publish result, and the ordered step list.
- Each refresh also writes a timestamped run history JSON under `exports/run-history/` and a concise text log under `logs/` by default. Override with `--history-dir` and `--log-dir`.

### Stage 5B Launch Operations

- Core module: `launch_ops.py`.
- `health-check` validates the launch DB, core tables, paperpipe directory/index, published static site entrypoint, bundle manifest, publish manifest, and required environment variable names.
- Health-check output never prints environment values. It only reports `present` or `missing` for each variable.
- Default required env name is `PAPER_DB_PATH`; the AIResearch DB path is validated by checking the actual `--db` path.
- `--require-fact-provider` also requires `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `AIRESEARCH_FACT_MODEL`.
- `--require-embedding` also requires `AIRESEARCH_EMBEDDING_API_KEY`, `AIRESEARCH_EMBEDDING_BASE_URL`, and `AIRESEARCH_EMBEDDING_MODEL`.
- `backup-db` uses SQLite's backup API to create `backups/airesearch-<label>.sqlite3` and `backups/airesearch-<label>.json`.
- The backup manifest records source DB path, backup path, manifest path, byte size, sha256, and generated time.

### Stage 5C Scheduled Refresh And Publish Observability

- Core modules: `launch_refresh.py`, `launch_ops.py`, and `static_publish.py`.
- `run-launch-refresh` persists the current manifest path plus timestamped history under `exports/run-history/`.
- `run-launch-refresh` writes concise logs under `logs/` with profile/provider counts, discovery errors, canonical/selected/approved counts, batch failures, paper/fact counts, site path, publish diff path, and ordered steps.
- `publish-static-site` writes `publish-diff.json` so refreshed sites can be compared against the previous publish.
- `write-refresh-wrapper` writes an executable shell wrapper suitable for manual, daily, or weekly cron execution. The wrapper runs backup, preflight health check, refresh, postflight health check, and tees output into `logs/launch-refresh-<timestamp>.log`.

## Launch Runbook

Run from `airesearch/` after `source ./activate.sh`.

1. Check current health:

```bash
python -m airesearch.cli health-check --site-dir exports/site-current --require-fact-provider
```

2. Create a DB backup before a large refresh:

```bash
python -m airesearch.cli backup-db --out-dir backups --label before-launch-refresh
```

3. Refresh discovery, ingest approved candidates, rebuild the MVP report, and publish:

```bash
python -m airesearch.cli run-launch-refresh --limit-per-profile 50 --select-limit 10 --min-score 0.60 --out-dir exports/mvp-current --site-dir exports/site-current --progress
```

For a larger 100-paper corpus expansion using all four discovery providers:

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

To generate a cron-friendly wrapper:

```bash
python -m airesearch.cli write-refresh-wrapper --out scripts/airesearch-refresh.sh --schedule daily
```

4. Check health again:

```bash
python -m airesearch.cli health-check --site-dir exports/site-current --require-fact-provider
```

5. Preview locally:

```bash
python -m airesearch.cli serve-report-site --dir exports/site-current --host 127.0.0.1 --port 8765
```

Rollback note: restore the latest good SQLite backup manually before rerunning `run-mvp-pipeline` or `publish-static-site`. For external static hosting rollback, generate scripts with `write-static-deploy-scripts` and run `rollback-airesearch.sh latest` to restore the newest pre-deploy snapshot.

## CLI Quick Reference

Run commands from `airesearch/` after `source ./activate.sh`.

Ledger and paperpipe sync:

```bash
python -m airesearch.cli init-db
python -m airesearch.cli sync-paperpipe
python -m airesearch.cli batch-ingest manifests/approved-stage-2c.txt
python -m airesearch.cli status
```

Discovery and canonical review:

```bash
python -m airesearch.cli seed-profiles
python -m airesearch.cli discover-candidates --profile diffusion_models --provider arxiv --limit 50
python -m airesearch.cli list-candidates --profile diffusion_models --limit 20
python -m airesearch.cli export-candidates --profile diffusion_models --limit 100 --out manifests/diffusion_models_top100.txt
python -m airesearch.cli dedupe-candidates
python -m airesearch.cli list-canonical-candidates --limit 20
python -m airesearch.cli select-canonical-candidates --limit 10 --min-score 0.70
python -m airesearch.cli export-approved-candidates --out manifests/approved-stage-2c.txt
```

Knowledge graph, code links, and facts:

```bash
python -m airesearch.cli extract-paper-cards
python -m airesearch.cli export-paper-cards --out exports/paper-cards-stage-2d.jsonl
python -m airesearch.cli extract-code-links
python -m airesearch.cli export-code-links --out exports/code-links-stage-2d2.jsonl
python -m airesearch.cli extract-artifact-ledger
python -m airesearch.cli export-artifact-ledger --out exports/artifact-ledger-current.md
python -m airesearch.cli export-artifact-ledger --format json --out exports/artifact-ledger-current.json
python -m airesearch.cli extract-research-facts --provider openai-compatible --model "$AIRESEARCH_FACT_MODEL" --base-url "$OPENAI_BASE_URL" --concurrency 5 --fact-error-policy warn
python -m airesearch.cli export-research-facts --out exports/research-facts-current.jsonl
python -m airesearch.cli claim-trace --fact-id 1
python -m airesearch.cli claim-trace --paper-key 1706_03762 --type claim --query attention --format json --out exports/claim-trace-current.json
python -m airesearch.cli audit-research-facts
python -m airesearch.cli repair-evidence-source-paths --out exports/evidence-source-path-repair-current.jsonl --apply
```

Reports:

```bash
python -m airesearch.cli generate-research-digest --out exports/research-digest-current.md
python -m airesearch.cli generate-research-digest --format json --out exports/research-digest-current.json
python -m airesearch.cli generate-research-map --out exports/research-map-current.md
python -m airesearch.cli generate-research-map --format json --out exports/research-map-current.json
python -m airesearch.cli generate-research-relations --out exports/research-relations-current.md
python -m airesearch.cli generate-research-relations --format json --out exports/research-relations-current.json
python -m airesearch.cli generate-gap-analysis --out exports/research-gap-analysis-current.md
python -m airesearch.cli generate-gap-analysis --format json --out exports/research-gap-analysis-current.json
python -m airesearch.cli generate-research-synthesis --out exports/research-synthesis-current.md
python -m airesearch.cli generate-research-synthesis --format json --out exports/research-synthesis-current.json
python -m airesearch.cli generate-narrative-report --out exports/research-narrative-current.md
python -m airesearch.cli generate-narrative-report --format json --out exports/research-narrative-current.json
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

Install `deploy/airesearch.nginx.conf` inside the existing `/etc/nginx/sites-enabled/control-center` server block, then reload nginx. The public path matches the rest of 牛秘书: `/niu-secretary/airesearch/`.

## Stage 3 Report Commands

Token clusters:

```bash
python -m airesearch.cli generate-research-clusters --out exports/research-clusters-current.md
python -m airesearch.cli generate-research-clusters --format json --out exports/research-clusters-current.json
```

Semantic clusters:

```bash
python -m airesearch.cli generate-research-clusters --mode semantic --out exports/research-clusters-semantic-current.md
python -m airesearch.cli generate-research-clusters --mode semantic --format json --out exports/research-clusters-semantic-current.json
```

Semantic threshold calibration:

```bash
python -m airesearch.cli calibrate-research-clusters --out exports/research-cluster-calibration-current.md
python -m airesearch.cli calibrate-research-clusters --format json --out exports/research-cluster-calibration-current.json
```

Cluster review packet:

```bash
python -m airesearch.cli generate-cluster-review --mode semantic --out exports/research-cluster-review-current.md
python -m airesearch.cli generate-cluster-review --mode semantic --format json --out exports/research-cluster-review-current.json
```

Reviewed cluster summary:

```bash
python -m airesearch.cli set-cluster-review-status --review-packet exports/research-cluster-review-current.json --cluster-id <cluster-id> --status accepted --notes "Confirmed by reviewer." --out exports/research-cluster-review-reviewed.json
python -m airesearch.cli summarize-cluster-review --review-packet exports/research-cluster-review-current.json --out exports/reviewed-cluster-summary-current.md
python -m airesearch.cli summarize-cluster-review --review-packet exports/research-cluster-review-current.json --format json --out exports/reviewed-cluster-summary-current.json
```

Valid editable `review_status` values are `pending`, `accepted`, `rejected`, and `needs_revision`. Only `accepted` clusters are treated as downstream-approved evidence.

Report bundle:

```bash
python -m airesearch.cli generate-report-bundle --out-dir exports/research-report-current
python -m airesearch.cli generate-report-bundle --out-dir exports/research-report-current --review-packet exports/research-cluster-review-current.json
```

## Module Map

| Module | Responsibility |
| --- | --- |
| `config.py` | Read runtime paths and provider settings from environment variables. |
| `db.py` | Initialize SQLite schema and provide DB connection helpers. |
| `paperpipe_sync.py` | Sync paperpipe papers and artifacts into the AIResearch ledger. |
| `batch.py` | Run manifest-based `papi` ingestion with integrated URL normalizer pre-pass. |
| `url_normalizer.py` | Resolve non-arxiv URLs (NeurIPS, CVPR, preprints, figshare, generic DOI) to arXiv IDs or titles via per-category resolver chains + OpenAlex/arXiv API fallback. |
| `profiles.py` | Seed default research profiles. |
| `providers.py` | Query OpenAlex, arXiv, Semantic Scholar, and Google Scholar providers. |
| `provider_cache.py` | Cache provider responses and enforce quota-aware provider behavior. |
| `discovery.py` | Orchestrate provider discovery for a profile and persist candidates. |
| `candidates.py` | List and export raw discovery candidates. |
| `canonical_candidates.py` | Materialize deduped candidates and manage review/approval status. |
| `knowledge_graph.py` | Build paper cards, graph nodes/edges, and provenance from paper records. |
| `code_links.py` | Extract and normalize repository links from paper metadata and source text. |
| `artifact_ledger.py` | Extract chunk, equation, and citation mention ledger rows from registered paper artifacts. |
| `fact_extraction.py` | Build evidence packs, call fact providers, validate facts, cache responses, and write provenance. |
| `fact_audit.py` | Audit research fact quality and evidence completeness. |
| `evidence_repair.py` | Repair missing evidence source paths with artifact text matching. |
| `embeddings.py` | Provide OpenAI-compatible embedding batches for semantic clustering. |
| `research_digest.py` | Generate corpus digest reports. |
| `research_map.py` | Generate fact-type research map reports. |
| `research_relations.py` | Generate cross-paper code, method, dataset, benchmark, and citation-ledger relation summaries. |
| `research_gap_analysis.py` | Generate coverage and missing-evidence analysis. |
| `research_synthesis.py` | Generate deterministic synthesis from coverage and evidence quality. |
| `research_narrative.py` | Generate narrative report with findings and follow-up actions. |
| `research_bundle.py` | Export report bundle directory, manifest, and index. |
| `research_site.py` | Render a static HTML report site plus search, provenance, and navigation indexes from a bundle manifest and report artifacts. |
| `mvp_pipeline.py` | Run the end-to-end local MVP publishing chain. |
| `static_publish.py` | Publish a generated static site to a stable directory, serve it for local preview, write optional static-host/nginx config files, and generate deploy/rollback scripts. |
| `launch_refresh.py` | Run discovery, candidate selection, approved ingest, MVP generation, static publish, and run-manifest export. |
| `launch_ops.py` | Run launch health checks and SQLite DB backups without printing secrets. |
| `research_clusters.py` | Generate token or semantic fact clusters. |
| `research_cluster_calibration.py` | Evaluate semantic clustering thresholds and recommend a default. |
| `research_cluster_review.py` | Export human-editable cluster review packets. |
| `research_review_editor.py` | Safely update one review item status and notes into a new review JSON file. |
| `research_review_summary.py` | Validate edited review packets and export accepted cluster summaries. |
| `cli.py` | Expose all workflows as `python -m airesearch.cli ...` commands. |

## Stable Local Outputs

Generated files are local workflow artifacts. Keep the `*-current` names as the latest reproducible run.

| Path | Producer | Notes |
| --- | --- | --- |
| `manifests/*_top100.txt` | `export-candidates` | Top candidate manifest per research profile. |
| `manifests/approved-stage-2c.txt` | `export-approved-candidates` | Approved canonical candidates for batch ingestion. |
| `manifests/approved-launch-refresh-current.txt` | `run-launch-refresh` | Latest auto-selected approved manifest for launch refresh. |
| `exports/paper-cards-stage-2d.jsonl` | `export-paper-cards` | L2 paper card JSONL export. |
| `exports/code-links-stage-2d2.jsonl` | `export-code-links` | Extracted code repository links. |
| `exports/artifact-ledger-current.{md,json}` | `export-artifact-ledger` | Chunk, equation, and citation mention ledger export. |
| `exports/research-facts-current.jsonl` | `export-research-facts` | Current audited research fact export. |
| `exports/evidence-source-path-repair-current.jsonl` | `repair-evidence-source-paths` | Evidence source-path repair candidates/results. |
| `exports/research-digest-current.{md,json}` | `generate-research-digest` | Corpus-level digest. |
| `exports/research-map-current.{md,json}` | `generate-research-map` | Fact-type map. |
| `exports/research-relations-current.{md,json}` | `generate-research-relations` | Cross-paper code/method/dataset/benchmark relation summary and citation-ledger gap status. |
| `exports/research-gap-analysis-current.{md,json}` | `generate-gap-analysis` | Coverage and evidence gap analysis. |
| `exports/research-synthesis-current.{md,json}` | `generate-research-synthesis` | Deterministic synthesis. |
| `exports/research-narrative-current.{md,json}` | `generate-narrative-report` | Narrative findings and actions. |
| `exports/research-clusters-current.{md,json}` | `generate-research-clusters` | Token-mode clusters. |
| `exports/research-clusters-semantic-current.{md,json}` | `generate-research-clusters --mode semantic` | Semantic clusters at current default threshold. |
| `exports/research-cluster-calibration-current.{md,json}` | `calibrate-research-clusters` | Threshold grid and recommended threshold. |
| `exports/research-cluster-review-current.{md,json}` | `generate-cluster-review --mode semantic` | Human-editable cluster review packet. |
| `exports/reviewed-cluster-summary-current.{md,json}` | `summarize-cluster-review` | Accepted cluster summary from an edited review packet. |
| `exports/research-report-current/` | `generate-report-bundle` | Bundle directory with reports, `manifest.json`, and `index.md`; can include `reviewed-clusters.md/json` when `--review-packet` is supplied. |
| `exports/mvp-current/bundle/index.html` | `run-mvp-pipeline` | Static HTML entry point for the current launchable MVP report. |
| `exports/mvp-current/bundle/search-index.json` | `run-mvp-pipeline` | Client-side search/filter index used by the static report site. |
| `exports/mvp-current/bundle/provenance-index.json` | `run-mvp-pipeline` | Static provenance index used by report-site jump links. |
| `exports/mvp-current/bundle/navigation-index.json` | `run-mvp-pipeline` | Static paper and cluster navigation index for larger corpora. |
| `exports/launch-refresh-current.json` | `run-launch-refresh` | Run manifest with discovery, ingest, MVP, publish, paths, counts, and step list. |
| `exports/site-current/` | `publish-static-site` | Stable local publish directory for the current static site. |
| `exports/site-current/publish.json` | `publish-static-site` | Publish manifest with source bundle, output path, entrypoint, generated time, file count, and file list. |
| `deploy/airesearch.nginx.conf` | `write-static-host-config` | nginx `location` snippet for hosting the published site under `/niu-secretary/airesearch/`. |
| `deploy/static-host.json` | `write-static-host-config` | Static-host config manifest with base path, deploy root, deploy command, and site paths. |
| `deploy/deploy-airesearch.sh` | `write-static-deploy-scripts` | External deploy script that snapshots the current deploy root and rsyncs the published site. |
| `deploy/rollback-airesearch.sh` | `write-static-deploy-scripts` | External rollback script that restores the latest or named pre-deploy snapshot. |
| `deploy/static-deploy-scripts.json` | `write-static-deploy-scripts` | Manifest for generated deploy and rollback scripts. |
| `backups/airesearch-<label>.sqlite3` | `backup-db` | SQLite-safe backup before large refresh runs. |
| `backups/airesearch-<label>.json` | `backup-db` | Backup manifest with source, destination, size, sha256, and generated time. |

## Test Coverage Map

| Area | Tests |
| --- | --- |
| Ledger, config, sync, batch | `tests/test_config.py`, `tests/test_db.py`, `tests/test_paperpipe_sync.py`, `tests/test_batch.py` |
| Discovery and candidates | `tests/test_profiles.py`, `tests/test_providers.py`, `tests/test_provider_cache.py`, `tests/test_discovery.py`, `tests/test_candidates.py`, `tests/test_canonical_candidates.py` |
| L2 graph, code, artifact ledger, facts | `tests/test_knowledge_graph.py`, `tests/test_code_links.py`, `tests/test_artifact_ledger.py`, `tests/test_fact_extraction.py`, `tests/test_fact_audit.py`, `tests/test_evidence_repair.py`, `tests/test_claim_trace.py` |
| Reports | `tests/test_research_digest.py`, `tests/test_research_map.py`, `tests/test_research_gap_analysis.py`, `tests/test_research_synthesis.py`, `tests/test_research_narrative.py`, `tests/test_research_bundle.py`, `tests/test_research_site.py` |
| Clusters and review | `tests/test_embeddings.py`, `tests/test_research_clusters.py`, `tests/test_research_cluster_calibration.py`, `tests/test_research_cluster_review.py`, `tests/test_research_review_editor.py`, `tests/test_research_review_summary.py` |
| MVP launch pipeline | `tests/test_mvp_pipeline.py`, `tests/test_static_publish.py`, `tests/test_launch_refresh.py`, `tests/test_launch_ops.py` |
| CLI | `tests/test_cli.py` |

## Feature Documentation Rule

For each new feature:

- Add a design doc under `docs/superpowers/specs/YYYY-MM-DD-<stage>-<feature>-design.md`.
- Add an implementation plan under `docs/superpowers/plans/YYYY-MM-DD-<stage>-<feature>.md`.
- Update `PLAN.md` with status, real export counts, and test results.
- Update this `DEVELOPMENT.md` if commands, environment variables, outputs, or verification steps change.
- Keep generated exports under `exports/` with a stable `*-current` name for the latest local run.

## Feature Log

### 2026-06-09 Stage 3K Semantic Threshold Calibration

- Added `calibrate-research-clusters`.
- Calibration reuses one embedding batch set across all thresholds.
- Default threshold grid: `0.70, 0.75, 0.80, 0.82, 0.85, 0.90`.
- Real DashScope `text-embedding-v4` calls require batch size at most 10; default `AIRESEARCH_EMBEDDING_BATCH_SIZE` is 10.

### 2026-06-09 Stage 3L Default Semantic Threshold Selection

- Calibration exports now include `recommendation`.
- Recommendation policy: choose the highest threshold with at least 3 clusters, at least 6 clustered facts, and largest cluster size at most 3.
- Initial real recommendation was `0.82` for `text-embedding-v4` over 11 papers and 79 facts.

### 2026-06-09 Stage 3M Cluster Review Packet

- Added `generate-cluster-review`.
- Review packets export each cluster with `review_status=pending`, editable `review_notes`, deterministic `recommended_status`, rationale, and fact evidence.
- Initial real semantic review packet used threshold `0.82` and exported 3 review items over 11 papers and 79 facts.
- Current recommendations are conservative: 0 `accept_candidate`, 3 `needs_review`.

### 2026-06-09 Stage 3N Reviewed Cluster Summary

- Added `summarize-cluster-review`.
- The command reads edited Stage 3M JSON review packets and validates `review_status`.
- Only `accepted` review items are exported as downstream-approved clusters.
- Current real summary over `exports/research-cluster-review-current.json` has 3 review items and 0 accepted clusters because the source packet remains pending.

### 2026-06-09 Stage 3O-3P Review Editor And Bundle Integration

- Added `set-cluster-review-status`.
- The command writes an edited review packet to `--out`, preserving the original generated packet.
- Added optional `generate-report-bundle --review-packet` support.
- When a review packet is supplied, the bundle includes `reviewed-clusters.md` and `reviewed-clusters.json`.
- Current real bundle export over `exports/research-cluster-review-current.json` has report_count=7, artifact_count=16, and accepted_count=0 because the review packet remains pending.
- Focused tests passed: 55. Full suite passed: 160.

### 2026-06-09 Stage 4A MVP Pipeline And Static Site

- Added `run-mvp-pipeline` as the launch-focused end-to-end command.
- Added `generate-report-site` and `research_site.py` to create static `index.html` from any report bundle.
- Added `mvp_pipeline.py` to orchestrate existing sync, extraction, audit, repair, clustering, review packet, bundle, and site generation modules.
- Latest real local command completed: `papers=202`, `cards=202`, `facts=1553`, `repaired=0`, `artifacts=21`, `site=exports/mvp-current/bundle/index.html`.
- Focused tests passed: 52.

### 2026-06-09 Stage 4B Static Publish And Serve

- Added `publish-static-site`.
- Added `serve-report-site`.
- Added `static_publish.py` with source validation, clean publish, recursive copy, and `publish.json` generation.
- Default launch publish path is `exports/site-current/index.html`.

### 2026-06-09 Stage 5A Launch Refresh Automation

- Added `run-launch-refresh`.
- Added `launch_refresh.py` to orchestrate discovery, canonical dedupe, selection, approved manifest export, batch ingest, sync, MVP pipeline, static publish, and run-manifest export.
- Default command refreshes all profiles with OpenAlex, arXiv, and Semantic Scholar; Google Scholar remains opt-in to protect SerpAPI quota.
- Added `exports/launch-refresh-current.json` and `manifests/approved-launch-refresh-current.txt` as stable launch outputs.
- Focused tests passed: 56.

### 2026-06-09 Stage 5A Refresh Progress And Provider Caps

- Added `run-launch-refresh --progress`.
- Progress is rendered as one unified stderr progress bar so stdout keeps the final `launch_refresh_completed ...` summary.
- Progress covers launch refresh setup, per-profile/per-provider discovery, canonical selection, manifest export, batch ingest, sync, MVP pipeline stages, and static publish.
- Google Scholar / SerpAPI per-profile request cap is 50; this is still quota-guarded and opt-in through `--provider google_scholar`.
- Focused tests passed: 16. Discovery/MVP focused tests passed: 3. CLI tests passed: 50.

### 2026-06-09 Stage 5B Launch Operations

- Added `health-check`.
- Added `backup-db`.
- Added `launch_ops.py` for non-destructive health validation and SQLite-safe DB backups.
- Added the launch runbook with preflight health check, backup, refresh/publish, postflight health check, preview, and manual rollback notes.
- Latest health check passed with 202 papers, 1212 artifacts, 1553 facts, and a complete `exports/site-current/` when `PAPER_DB_PATH` is present.
- Real backup created `backups/airesearch-stage5b-launch-ops.sqlite3` plus `backups/airesearch-stage5b-launch-ops.json`.
- Focused tests passed: 61.

### 2026-06-09 Stage 5C Scheduled Refresh And Publish Observability

- Added `publish-diff.json` during static publish to record added, removed, changed, and unchanged site files versus the previous publish.
- Added timestamped `run-launch-refresh` history manifests under `exports/run-history/`.
- Added concise `run-launch-refresh` logs under `logs/` with discovery, ingest, extraction, report, publish, and output path summaries.
- Added `write-refresh-wrapper` to generate a cron-friendly shell wrapper with backup, preflight health check, refresh, postflight health check, and tee'd run logs.
- Focused tests passed: 13.

### 2026-06-10 URL Normalization Pipeline

- Added `url_normalizer.py`: 7-category classifier (arxiv / proceedings / cvpr_openaccess / preprints / figshare / doi / title) with per-category resolver chains.
- Each resolver tries to extract a paper title from the page HTML (citation_title → DC.Title → og:title → <title> → <h1>), then searches arXiv API for a matching arXiv ID.
- `preprints` and `figshare` resolvers include OpenAlex/API fallback when the source blocks direct scraping (403).
- Generic DOIs go through OpenAlex API to find arxiv landing pages, or title→arxiv search as second fallback.
- `batch.py` integrated: `run_batch_ingest(normalize_urls=True)` automatically normalizes each manifest line before passing to `papi add`; same flag passed through from `launch_refresh.py`.
- New CLI subcommand: `python -m airesearch.cli normalize-url <url>` for manual inspection.
- Validation against 14 previously-failed papers from the 100-paper batch: 10 resolve (2 to exact arXiv IDs via API lookup, 8 to searchable titles). 2 CVPR papers fail due to CVF server SSL rejection; 2 are non-AI papers that should not be ingested.
- Fallback from `_FetchError` logging when pages return 403 or SSL errors, with explicit method-trace messages in the database.
- New tests: 30 (`tests/test_url_normalizer.py`), including categorization of all 14 failed papers as a regression suite. Full suite at 211.

### 2026-06-10 Fact Extraction Warn Policy

- Added `--fact-error-policy strict|warn` to `extract-research-facts`, `run-mvp-pipeline`, and `run-launch-refresh`.
- Default `strict` keeps the previous behavior: any LLM extraction failure fails the command.
- `warn` records failed papers in `fact_extraction_cache`, marks the extraction run as `partial_success`, reports `fact_failures`, and continues report/site generation with successful facts.
- The 100-paper launch refresh runbook now includes `--fact-error-policy warn` so one provider-side content inspection rejection does not abort the whole corpus expansion.

### 2026-06-10 New-Paper Selection For Corpus Expansion

- Added existing-paper canonical key detection from `papers`, `paper_sources`, `ids_json`, and `meta_json`.
- `select_top_canonical_candidates` now skips already-ingested papers before applying the Top-N limit.
- Corpus expansion with `--select-limit 100` now attempts to approve 100 new papers instead of spending slots on duplicates already in the local database.

### 2026-06-10 Candidate Review Reason Export

- Added `export-candidate-review` to write machine-readable JSON and human-readable Markdown review reports.
- `run-launch-refresh` now writes candidate review reports automatically after approved manifest export.
- Review reasons explain whether a candidate was selected, already in the local database, manually rejected, below `--min-score`, outside the Top-N limit, or missing an ingest identifier.

### 2026-06-10 Source-Specific Discovery Tuning

- Candidate scoring now includes source-quality reasons such as `source:arxiv_direct`, `source:semantic_scholar_arxiv`, `source:openalex_resolvable`, `source:google_scholar_resolvable`, and `source:google_scholar_unverified`.
- Direct arXiv and resolvable DOI/proceedings/arXiv-backed records are preferred over weak provider-only identifiers.
- Provider names are excluded from topic/backing text matching; this prevents source names such as `google_scholar` from creating false organization/scholar backing hits.

### 2026-06-10 Static Site Search And Filter

- `research_site.py` now generates `search-index.json` alongside `index.html`.
- Static report pages include a search box, report-type filter, result count, and synchronized navigation visibility.
- Filtering is browser-only JavaScript over the generated static index, so `serve-report-site` and static hosting continue to work without a backend.

### 2026-06-10 Static Site Provenance Jump Links

- `research_site.py` now generates `provenance-index.json` alongside `index.html` and `search-index.json`.
- The static report page includes a Provenance section with paper, evidence source path, and code-link entries extracted from report JSON artifacts.
- Provenance entries link back to the source report section and raw JSON artifact, preserving static hosting compatibility.

### 2026-06-10 Static Site Corpus Navigation

- `research_site.py` now generates `navigation-index.json` alongside `index.html`, `search-index.json`, and `provenance-index.json`.
- The static report page includes a Corpus Navigation section with scrollable paper and cluster lists extracted from report JSON artifacts.
- Paper entries link back to the report section that exposed the paper; cluster entries show fact and paper counts for large-corpus browsing.

### 2026-06-10 Claim Trace CLI

- Added `claim_trace.py` and `python -m airesearch.cli claim-trace`.
- The command traces one extracted fact by exact `--fact-id`, or by `--paper-key` with optional `--type` and `--query`.
- Trace output includes fact metadata, paper metadata, evidence quote, evidence artifact/source path, matching artifact rows, code links, KG relations, and KG provenance.
- Output supports Markdown for inspection and JSON for downstream tooling through `--format json --out <path>`.

### 2026-06-10 Cross-Paper Relation Summaries

- Added `research_relations.py` and `python -m airesearch.cli generate-research-relations`.
- The report groups papers sharing the same GitHub repository/owner/host and papers sharing normalized `method`, `dataset`, or `benchmark` facts.
- Citation output is intentionally a ledger-status section: it records citation ledger coverage and does not claim true citation edges until citation keys are matched to papers.
- `generate-report-bundle` now includes `relations.md` and `relations.json` in the bundle manifest.

### 2026-06-10 Static Host Config

- Added `python -m airesearch.cli write-static-host-config`.
- The command writes `deploy/airesearch.nginx.conf` and `deploy/static-host.json` by default for optional nginx/static-host deployment under `/niu-secretary/airesearch/`.
- Added `python -m airesearch.cli write-static-deploy-scripts`.
- The command writes `deploy/deploy-airesearch.sh`, `deploy/rollback-airesearch.sh`, and `deploy/static-deploy-scripts.json`; generated scripts snapshot the external deploy root before publish and can restore the latest or named snapshot.
- Both commands validate the published site directory but do not copy files into `/var/www`, modify system nginx files, or reload services when generating config/scripts.

### 2026-06-10 Artifact Ledger

- Added `artifact_ledger.py` plus `extract-artifact-ledger` and `export-artifact-ledger`.
- The ledger builds deterministic `paper_chunks`, `paper_equations`, and `paper_citations` rows from registered paperpipe artifacts.
- `claim-trace` now includes artifact ledger matches alongside evidence, artifacts, code links, KG relations, and KG provenance.
- `generate-research-relations` now reads `paper_citations` for citation ledger coverage.
- `run-mvp-pipeline` now runs `extract-artifact-ledger` before report bundle generation, and `generate-report-bundle` includes `artifact-ledger.md` and `artifact-ledger.json`.
