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
AIRESEARCH_ARCHIVE_REMOTE=gdrive:niu-secretary/airesearch/v1
AIRESEARCH_ARCHIVE_STAGING=/home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/data/archive-staging
AIRESEARCH_RCLONE=rclone
AIRESEARCH_ARCHIVE_WORKERS=2
AIRESEARCH_ARCHIVE_CACHE_GB=1
AIRESEARCH_BLOG_API_STYLE=chat_completions
AIRESEARCH_BLOG_BASE_URL=https://provider.example/v1
AIRESEARCH_BLOG_MODEL=deepseek-v4-pro
AIRESEARCH_BLOG_API_KEY=loaded-from-protected-environment-file
AIRESEARCH_BLOG_PROXY=http://127.0.0.1:7890
```

`AIRESEARCH_BLOG_API_STYLE` accepts `chat_completions` or `responses`. Chat
Completions accepts an API root and appends `/chat/completions`; Responses accepts
an API root or a complete `/responses` endpoint. When the style is unset, an
endpoint ending in `/responses` selects Responses and other endpoints select Chat
Completions. `AIRESEARCH_BLOG_PROXY` applies to the Responses transport only. An
explicitly injected test transport takes precedence over protocol selection.

The general blog provider resolves each setting independently:

- Model: explicit `model`, `AIRESEARCH_BLOG_MODEL`, `NIU_ASSISTANT_MODEL`, then
  `deepseek-v4-pro`.
- Base URL: explicit `base_url`, `AIRESEARCH_BLOG_BASE_URL`,
  `OPENCODE_GO_BASE_URL`, `TRANSLATE_BASE_URL`, `OPENAI_BASE_URL`, then the
  built-in DeepSeek base URL.
- API key: `AIRESEARCH_BLOG_API_KEY`, the requested `api_key_env`,
  `OPENCODE_GO_API_KEY`, `OPENAI_API_KEY`, then `TRANSLATE_API_KEY`.

Duplicate key variable names are evaluated only once. The admin action reads API
style, endpoint, and proxy only from trusted server environment variables, never
from request URL fields.

The A/B runner has stricter named arms. The DeepSeek arm always uses Chat
Completions. Its model precedence is `AIRESEARCH_DEEPSEEK_BLOG_MODEL`,
`AIRESEARCH_BLOG_MODEL`, then the fixed `deepseek-v4-pro` default; it never reads
`NIU_ASSISTANT_MODEL`. The production runner binds its base URL and key to
`OPENCODE_GO_BASE_URL` and `OPENCODE_GO_API_KEY`. The Luna arm uses the same
credential with the Responses endpoint and `AIRESEARCH_FORMULA_OCR_MODEL`.
Production currently supplies `gpt-5.6-luna` and the local
`http://127.0.0.1:7890` proxy through the canonical `OPENCODE_GO_PROXY` in
the ignored `airesearch/.env` file.
`gpt-5.6-luna` remains the formula OCR model and is not the default deep-reading
model unless the A/B result selects Luna or `AIRESEARCH_BLOG_*` explicitly
configures it.

Optional arm-specific overrides are `AIRESEARCH_DEEPSEEK_BLOG_MODEL`,
`AIRESEARCH_DEEPSEEK_BLOG_BASE_URL`, and `AIRESEARCH_DEEPSEEK_BLOG_API_KEY`, plus
`AIRESEARCH_LUNA_BLOG_MODEL`,
`AIRESEARCH_LUNA_BLOG_BASE_URL` (or `AIRESEARCH_LUNA_BLOG_API_BASE`),
`AIRESEARCH_LUNA_BLOG_API_KEY`, and `AIRESEARCH_LUNA_BLOG_PROXY`. The named arms
remain fixed to Chat Completions and Responses respectively.

Do not print API keys in logs, docs, or test output. Keep production secrets in
the Git-ignored `airesearch/.env` with mode `600`; never pass keys in CLI
arguments, admin payloads, generated reports, or database fields.

Google Drive OAuth credentials remain outside the repository in
`~/.config/rclone/rclone.conf`; keep that file at mode `600`. SQLite databases,
search indexes, metadata, covers, source text, and current published assets stay
local. Public web and API requests must never depend on Drive availability.

## Verification Commands

Run focused launch and documentation-surface tests from `airesearch/`:

```bash
.venv/bin/python -m pytest tests/test_url_normalizer.py tests/test_launch_ops.py tests/test_launch_refresh.py tests/test_static_publish.py tests/test_research_site.py tests/test_research_relations.py tests/test_mvp_pipeline.py tests/test_cli.py -q
```

Run the full suite:

```bash
.venv/bin/python -m pytest -q
```

## Google Drive Cold Archive

Archive operations are explicit per paper. Upload does not remove local data,
and verification downloads the remote tar to calculate SHA-256 independently.
Use this sequence:

```bash
airesearch archive plan
airesearch archive plan --record --paper-key 1706_03762
airesearch archive upload --paper-key 1706_03762
airesearch archive verify --paper-key 1706_03762
airesearch archive evict --paper-key 1706_03762
airesearch archive evict --paper-key 1706_03762 --apply
airesearch archive restore --paper-key 1706_03762
```

The first `evict` command is a read-only preview. Only `--apply` moves the local
PDF and figure tree into a same-filesystem quarantine before committing the
`evicted` state. Restore validates the archive and every manifest entry before
installing files. Unreferenced paperpipe directories are reported and never
selected for mutation.

For the first production rehearsal, stop after `archive verify` and confirm the
local PDF and figures still exist. Production eviction requires separate review
of the verification record and public API smoke test.

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

### Stage 2A SQLite Ledger, URL Normalization, And Batch Ingest

- Core modules: `config.py`, `db.py`, `paperpipe_sync.py`, `batch.py`, `url_normalizer.py`, `cli.py`.
- SQLite schema tracks papers, paper artifacts, sync events, ingest runs, discovery, candidates, graph rows, provenance, facts, cache, and report inputs.
- URL normalization resolves problematic non-arXiv sources before `papi add`, including NeurIPS proceedings, CVPR OpenAccess, preprints.org, figshare, generic DOI URLs, direct arXiv links, and raw titles.
- Commands implemented:
  - `init-db`
  - `sync-paperpipe`
  - `batch-ingest`
  - `normalize-url`
  - `status`
- Batch ingest shells out to `papi`, normalizes manifest entries by default, records success/failure/duplicate/skipped counts, then syncs paperpipe state into the AIResearch ledger. Use `--no-normalize-urls` only when debugging the raw `papi add` input.
- Admin action `airesearch.paper.ingest_single` shells out to `papi add`, syncs PaperPipe, detects `paper_key`, and automatically queues a `paper_layout_parse` job when no completed layout run or active layout job exists. The response includes `layout_job_id`, `layout_job_status`, and `layout_job_reason`.

### Stage 2A2 Native Layout V2

- Core modules: `layout_parser.py`, `layout_parse.py`, and `layout_service.py`.
- This is a MinerU-inspired native implementation, not a MinerU install. It uses PyMuPDF to produce Markdown, content list JSON, layout structure JSON, debug JSON, summary JSON, and extracted assets.
- The parser removes repeated headers, repeated footers, and pure page-number blocks before writing Markdown/content list/layout JSON. Removed counts are recorded under `summary.removed_margin_blocks`.
- Page blocks run through `geometry_columns_v2` reading-order reconstruction before Markdown generation. The pass recognizes left/right columns, cross-column anchors, and figure/table caption pairs, then records `metadata.reading_order_index`, region, confidence, and reasons on every block.
- Complex table reconstruction is isolated in `table_reconstruction.py`. Borderless tables use PyMuPDF word bboxes to cluster visual rows, split cells, infer repeated column anchors, preserve sparse cells, detect multi-row headers, and infer column spans. Ruled tables use `page.find_tables()` to establish the whole-table region. Booktabs tables use horizontal PDF rules to recover complete, tall, colored, borderless, and stacked-subtable regions; overlapping fragments and prose/caption collapse candidates are rejected before the same native geometry reconstruction runs.
- `PyMuPDF>=1.27.0` plus runtime `page.find_tables()` support is required for ruled-table region detection. Ubuntu's packaged `1.23.7` produced a native crash on a real corpus PDF, so layout v2 version-gates `find_tables()` and safely keeps word-geometry parsing when an older runtime is detected.
- Table blocks retain the compatible `metadata.table_rows`, `table_markdown`, and `table_html` fields and additionally expose `table_cells`, row/column/span/bbox/confidence per cell, header row count, column anchors/boundaries, reconstruction method, confidence, and reasons. Markdown flattens multi-row headers; HTML preserves inferred `colspan`.
- If geometry cannot prove at least two rows and two columns, the parser keeps the previous whitespace splitter and marks it as `table_reconstruction_method = "text_spacing_v1"` with lower confidence. Summary counters distinguish geometry, spanning, and fallback table blocks.
- Representative visual selection now creates `pdf_figure_crop` candidates from early Figure captions even when PyMuPDF exposes no embedded image blocks. Caption matching is strict enough to reject inline prose references such as `Figure 2 presents ...`, while accepting captions split across PDF text lines. Same-page Figure 1/2 captions are assigned to nearby visual block groups, then adjacent uncaptioned layers and short in-figure labels are included up to the real caption boundary so composite diagrams remain complete without importing neighboring column prose. Complete and fragmented visual groups use tight PDF crops; crop digest version changes force new assets, and partial arrows/vector-only figures fall back to caption-window PDF re-rendering.
- Summary stats include `reading_order.method`, completed pages, multi-column pages, cross-column blocks, caption-paired blocks, low-confidence reading-order blocks, and average confidence. Admin state exposes compact reading-order counters for paper list badges and blog evidence preflight.
- Evidence blocks now carry `metadata.quality_score` and `metadata.quality_reasons`. The current high-quality threshold is `0.72`; summary stats include high-quality evidence, visual, table, and equation counts.
- Each page is classified as `digital`, `scanned`, or `mixed`. In `auto` mode, pages without a sufficient text layer are rendered at the configured DPI and sent to the local Tesseract CLI; OCR blocks retain engine, language, confidence, page, and bbox provenance.
- OCR configuration: `AIRESEARCH_LAYOUT_OCR_MODE` (`off|auto|force`), `AIRESEARCH_LAYOUT_OCR_LANGUAGES` (default `eng+chi_sim`), `AIRESEARCH_LAYOUT_OCR_DPI` (default `220`), and `AIRESEARCH_LAYOUT_OCR_EXECUTABLE` (default `tesseract`).
- Formula OCR is isolated in `formula_ocr.py`. It supports OpenAI-compatible Chat Completions, OpenAI Responses, and Anthropic image message formats, validates returned LaTeX, rejects non-formula labels and low-confidence output, and records crop/model/confidence/source provenance on equation blocks. Candidate filtering and digital-PDF table/formula extraction remain local and deterministic; API OCR is a scanned-formula fallback in `auto` mode.
- Canonical formulas come from the artifact ledger before layout candidates. `extract_equations_from_text()` groups complete fenced LaTeX blocks, deduplicates normalized LaTeX per paper, skips explicit missing-source placeholders, and salvages only complete display-math environments from fences polluted with full TeX documents. `paper-layout-evidence.json` reports `summary.canonical_equation_count` and emits `source_kind=paperpipe_equations`; layout equations are used only when a paper has no valid canonical formulas.
- Formula OCR configuration: `AIRESEARCH_FORMULA_OCR_MODE`, `AIRESEARCH_FORMULA_OCR_DPI`, `AIRESEARCH_FORMULA_OCR_MIN_CONFIDENCE`, plus optional `AIRESEARCH_FORMULA_OCR_API_BASE`, `AIRESEARCH_FORMULA_OCR_API_KEY`, `AIRESEARCH_FORMULA_OCR_MODEL`, and OCR-only `AIRESEARCH_FORMULA_OCR_PROXY`. The provider can fall back to loaded `FITNESS_VISION_*` values.
- Production formula OCR is enabled with `AIRESEARCH_FORMULA_OCR_MODE=auto` and uses the OpenCode Go Responses endpoint derived from `OPENCODE_GO_BASE_URL` with `AIRESEARCH_FORMULA_OCR_MODEL=gpt-5.6-luna`. Formula requests use `OPENCODE_GO_PROXY` without changing other service traffic. The single OpenCode credential is `OPENCODE_GO_API_KEY` in the ignored `airesearch/.env`, which must retain mode `600`.
- Do not use Luna to rewrite every formula or table. Preserve source TeX and geometry-derived cell values as ground truth; route only missing, scanned, malformed, or low-confidence candidates to a model. A future table-review queue must store the raw extraction, model candidate, verified value, crop/page/bbox, model, confidence, and issues separately, and must validate JSON shape plus every numeric cell before promotion.
- SQLite tables:
  - `paper_layout_runs`: parser provider/version, input PDF, output directory, status, stats, and error.
  - `paper_layout_blocks`: page index, block index, block type, bbox, text, asset path, and metadata.
  - `paper_artifacts`: layout artifact files under artifact types such as `layout_markdown`, `layout_content_list`, `layout_structure_json`, `layout_debug_json`, `layout_summary_json`, and `layout_asset`.
- Admin data endpoints:
  - `airesearch.admin.state`: compact per-paper layout status for paper-management lists.
  - `airesearch.admin.paper.layout.detail`: full layout detail including artifacts, block counts, capabilities, evidence blocks, `evidence_graph`, representative visual, visual candidates, and latest job.
- Admin UI:
  - `/niu-secretary/admin/airesearch/papers` includes the paper-management Layout Evidence Inspector.
  - The inspector uses `airesearch.admin.paper.layout.detail` and renders `事实关联`, `证据块`, `公式 OCR`, `表格结构`, `OCR / 读序`, and `视觉候选` tabs from `evidence_graph`, `evidence_blocks`, `sample_blocks`, `summary`, `representative_visual`, and `visual_candidates`.
  - Keep the inspector read-only. Mutations still go through `airesearch.admin.paper.layout.generate` for parsing/reruns and the artifact dialog for raw artifact paths.
- Admin action:
  - `airesearch.admin.paper.layout.generate`: queues `paper_layout_parse`; supports `force` and `maxPages`.
- Automatic ingestion behavior:
  - `airesearch.paper.ingest_single` queues layout parsing after successful single-paper ingest.
  - Deduplication skips queueing when a completed/skipped layout run exists.
  - Deduplication reuses queued/running `paper_layout_parse` jobs for the same paper.
- Current production scope: structure JSON, page/block coordinates, geometry-based reading-order reconstruction, captioned visual blocks, caption-window PDF figure crops, geometry-based complex table reconstruction, equation blocks, evidence quality scoring, deterministic fact-to-layout evidence graph extraction, representative visual selection, public rendering, and admin UI integration.
- Not yet implemented: an operational local formula model, advanced orientation/low-quality OCR, reliable arbitrary row-span recovery, arbitrary complex floating-layout semantic ordering, vector search over layout blocks, or a separate graph database.

### Stage 2A3 Layout Evidence Knowledge Graph

- Core module: `layout_evidence_graph.py`; schema version: `evidence-graph-v1`; extractor version is recorded in every API payload.
- It reuses `kg_nodes`, `kg_edges`, and `kg_provenance`. No schema migration, vector database, graph database, MinerU runtime, or LLM call is required.
- Node keys are `research_fact:<paper_key>:<fact_id>` and `layout_evidence:<paper_key>:<run_id>:<block_id>`. The extractor reuses `paper:<paper_key>` with `insert or ignore` and never updates or deletes the shared paper node.
- Eligible layout blocks are image/chart/table/interline_equation from the latest completed/reused run. Graph inclusion requires usable content and quality `>=0.55`; lexical matching additionally requires quality `>=0.72`.
- Match order is deterministic: direct provenance path `paper_layout_blocks:<id>`; normalized containment with at least 24 characters; strict token overlap with 4 shared tokens, source coverage `>=0.72`, and Jaccard `>=0.30`.
- Type compatibility prevents equation-only lexical evidence from supporting dataset, benchmark, or limitation facts. At most three ranked evidence links are stored per fact; same-page evidence with identical type and normalized content is deduplicated first.
- Public projection caps are 24 facts, 48 evidence nodes, 72 relations, three links per fact, and 240 characters per preview. Local paths, raw table HTML, full metadata, provider internals, and provenance are removed.
- `layout-evidence-graph.json` is a bundle data artifact and is listed under `manifest.json.data_artifacts`. Every public paper API shard has an `evidence_graph` object; old bundles without the artifact receive an empty versioned object.
- Admin `evidence_graph` is bounded to 200 facts/evidence/relations and retains match properties, node keys, and provenance for diagnosis.
- Fact create/update/delete responses include `graph_refresh`. A failed refresh is reported without rolling back the already committed fact mutation.
- Troubleshooting:
  - No evidence nodes: verify a completed layout run, block quality, and usable caption/table/formula content.
  - Facts are unlinked: inspect fact provenance, compatibility, block quality, and lexical thresholds in the admin `事实关联` tab.
  - Public graph is stale: rerun extraction, regenerate the report bundle/site, then deploy the generated static assets.
  - Admin graph is stale after a job: inspect `admin_jobs.message` for `graph_refresh_failed` and rerun the single-paper extractor.

### Full Workflow Acceptance Check

- Core module: `workflow_check.py`.
- CLI command: `workflow-check --paper-key <paper_key> [--site-dir <published_site>]`.
- The check is read-only and returns JSON with one item per capability.
- It validates that a paper is searchable, has a PDF artifact, covers all five required fact types (`method`, `dataset`, `benchmark`, `claim`, `limitation`), has Chinese artifacts (`summary_zh` or `tldr_zh`), has completed/reused layout v2, layout evidence blocks, visual candidates, table/equation capability, and a published deep-reading blog version. With `--site-dir`, it also validates the public static API shard, `evidence-graph-v1`, the paper HTML, and its `证据关系` section.
- A failed check exits with status code `2`, so it can be used in deployment or post-ingest smoke tests.
- Blog generation consumes the same quality signal: layout-derived image/table candidates carry `quality_score` and `quality_reasons`, visual selection prefers candidates at or above `0.72`, and OpenAI-compatible prompt payloads include `evidence_quality_policy`.
- Deep-reading evidence-pack construction first collects native layout PDF crops and layout-block visuals, deduplicates them by content fingerprint, and measures publishable category coverage. It invokes the source figure resolver only when fewer than two publishable figures are available and the source table resolver only when no publishable table is available. This layout-first gate keeps full PDF crops ahead of repeated fragments and avoids unnecessary arXiv source downloads or PDF rasterization when layout evidence already covers the required categories.
- High-quality native layout equations are merged into `BlogEvidencePack.equations` with source references and quality provenance. High-quality structured table Markdown is exposed as `artifact_texts.layout_structured_tables`; prompt bounding reserves up to one quarter of the artifact budget (capped at 2000 characters) so table evidence is not displaced by long source text.

### Deep-Reading Providers And Controlled Batch

- `paper_blog.py` supports OpenAI-compatible Chat Completions and Responses while preserving the same required-section generation, validation, cache, and version tables.
- Final Markdown is post-processed deterministically: every required section receives a visible H2 heading, valid section `image_ids` become local Markdown image elements, and each valid referenced image is embedded at most once across the blog. Validation fails when selected image evidence exists but the final Markdown embeds zero images; the batch audit applies the same hard gate.
- Evidence-pack equation input rejects U+FFFD, C0 controls except tab/newline/CR, and DEL/C1 (`U+007F`-`U+009F`) before `source_hash` is computed. The filtered publishable-equation set is part of the hash, so a filtering change that alters that set invalidates outline and section caches.
- With facts present, runtime outline enrichment assigns facts by `fact_type` to semantic sections, removes cross-section duplicates, and covers at least `ceil(50%)` of valid facts. Capacity defaults to four facts per section and grows dynamically for large fact sets. A section request receives only its assigned facts; its response must return exactly the same `fact_ids` set. Sections assigned no facts receive no fallback facts.
- `blog_batch.py` provides evidence preflight, named DeepSeek/Luna model arms, selected-row backup/restore, deterministic A/B auditing, sanitized JSONL logs, and resumable batch generation.
- Batch eligibility still requires valid fact coverage `>= 0.5`, no U+FFFD or unescaped model-control token in final Markdown, and enough display-math blocks only for the publishable formulas that survived evidence filtering.
- `scripts/generate_deep_readings.py` exposes `preflight`, `backup`, `ab`, `batch`, and `restore`. It never accepts an API key argument. Exit `0` means complete success; preflight or partial batch failure exits `2`.
- The ready gate requires an existing paper, summary or TLDR grounding, all five fact types, at least one selected local image, and a completed layout run. Formula and table counts are reported but are not universal readiness requirements.
- The runner never exports or deploys the site. Admin single-paper generation is intentionally different: `airesearch.admin.paper.blog.generate` creates one version and rebuilds/publishes the site after that job succeeds.
- A successful `ab` run automatically writes the machine-scoring decision to `winner.json` and promotes that arm's versions for both sample papers as their database current versions. If no arm wins, it restores the original current versions and removes stale `winner.json`. Before `batch`, winner validation binds the run to the backup `backup_id`, the complete ordered paper selection, prompt version, runtime model arm/model/API style, and the current source hashes of both A/B samples.
- Batch generation is resumable by paper key, source hash, model, and prompt version. One failed paper is recorded without erasing successful versions or stopping later papers; a partial run is never eligible for public publication.

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
- Current expanded local corpus has 209 papers and 2081 facts.
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
- `generate-report-site` adds a dependency-free multi-page Academic Calm static site: `index.html`, `papers/`, `clusters/`, compact Digest, interactive Research Map, visual Gap Analysis, structured Research Synthesis, structured Narrative, external `assets/site.css`, `assets/site.js`, lightweight `api/` JSON shards, plus compatibility `search-index.json`, `provenance-index.json`, and `navigation-index.json`.
- Static sites include browser-only search/filter controls. The dashboard search uses `api/search-index.json`, generated from compact paper and cluster metadata rather than full Markdown dumps; no backend service is required.
- Paper detail pages expose fact tabs by type, confidence, evidence quotes, evidence source paths, code links, and arXiv links when available.
- Research Digest renders timeline, recent papers, high-confidence findings, and top topic clusters without embedding the full Markdown export.
- Research Map uses `api/relations-graph.json` to render a capped SVG topic-paper graph with fact-type filters and node inspection.
- Gap Analysis renders coverage bars, priority paper queues, evidence path gaps, and code-link gaps from compact JSON summaries, while linking to raw Markdown/JSON artifacts for the full export.
- Research Synthesis renders coverage bands, readiness checks, synthesis notes, and extraction targets from compact JSON summaries, while linking to raw Markdown/JSON artifacts for the full export.
- Narrative renders executive summary, supported/provisional areas, representative evidence, priority actions, and evidence cautions from compact JSON summaries, while linking to raw Markdown/JSON artifacts for the full export.
- `site-manifest.json` lists the files required for public static hosting so publish can exclude heavy intermediate bundle artifacts.
- Compatibility provenance and navigation indexes remain available for tooling and jump-link workflows.
- Current report corpus: 209 papers and 2081 facts.

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
- `run-mvp-pipeline` is the fast publish path for launch: it syncs paperpipe, extracts cards/code links/artifact ledger rows, reuses existing facts unless `--refresh-facts` is set, audits facts, repairs evidence paths, generates clusters/review packet/report bundle, and writes the multi-page static Web export.
- Default output is `exports/mvp-current/`; the deployable entry point is `exports/mvp-current/bundle/index.html`.
- Latest real local MVP export completed over 202 papers and 1553 facts with no new LLM calls.

### Stage 4B Static Publish And Local Preview

- Core module: `static_publish.py`.
- `publish-static-site` copies a generated bundle to a stable publish directory, defaulting from `exports/mvp-current/bundle/` to `exports/site-current/`.
- The publish step validates that the source contains both `index.html` and `manifest.json`.
- If `site-manifest.json` is present, publish copies only its safe relative `publish_files`; this keeps public static hosting free of large intermediate artifacts such as artifact-ledger exports.
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

## 40-Paper Deep-Reading Runbook

Run this controlled workflow from the repository root. The approved list has the
two A/B papers first:

```text
what-if-world
world2vlm
world-action-models
world-model-self-distillation
2606_00269
3dthinkvla
actionmap
disco
latent-diffusion-policy
mpcot
multimodal-structure-learning
phail
simple
verispace
vla-os
physics-in-2-steps
vista
oscar
thinking-with-imagination
wbench
probeact
gem-4d
agenticnav
ttt-vla
flymirage
ouroboros-spatial
phyedit
mbench
2605_27817
2606_03784
2606_02735
2606_05737
2606_08881
2606_00253
2606_06002
2606_10348
mllm-for3d
2606_09644
tabverse
2606_10904
```

`omnivl-guard` is deliberately omitted because it lacks the required `benchmark`
research fact. Add it only after that fact and its provenance have been generated
and reviewed.

Create `backups/airesearch-deep-readings-20260811-40/papers.txt` with the complete
list above and keep that same list for preflight, backup, A/B, batch, and
verification:

```bash
ROOT=/home/ubuntu/vibe_proj/niu-secretary
RUN_DIR="$ROOT/backups/airesearch-deep-readings-20260811-40"
```

The protected API configuration must be loaded by the process without echoing
values. Use the following command shape for each operation:

```bash
sudo bash -lc 'set -euo pipefail
umask 077
set -a
source /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env
set +a
ROOT=/home/ubuntu/vibe_proj/niu-secretary
DB="$ROOT/airesearch/data/airesearch.sqlite3"
RUN_DIR="$ROOT/backups/airesearch-deep-readings-20260811-40"
PYTHONPATH="$ROOT/airesearch/src" "$ROOT/airesearch/.venv/bin/python" \
  "$ROOT/airesearch/scripts/generate_deep_readings.py" preflight \
  --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR"'
```

Do not continue unless preflight reports 40 ready papers and zero errors. Create
the selected-row backup before any model call:

```bash
sudo bash -lc 'set -euo pipefail; umask 077; set -a; source /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env; set +a; ROOT=/home/ubuntu/vibe_proj/niu-secretary; DB="$ROOT/airesearch/data/airesearch.sqlite3"; RUN_DIR="$ROOT/backups/airesearch-deep-readings-20260811-40"; PYTHONPATH="$ROOT/airesearch/src" "$ROOT/airesearch/.venv/bin/python" "$ROOT/airesearch/scripts/generate_deep_readings.py" backup --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR"'
```

Verify `manifest.json` hashes and keep at least 750 MB free. This backup is
limited to selected rows in `paper_blog_posts`, `paper_blog_versions`, and
`paper_blog_generation_cache`, plus the selected papers' blog asset manifest; it
is not another full database copy. Preflight output, backup files, A/B artifacts,
created-assets tracking, winner, batch logs, and restore inputs all remain in the
same `RUN_DIR`. In particular, `created-assets.json` stays beside `manifest.json`,
`winner.json`, `ab.jsonl`, and `batch.jsonl` as an informational snapshot-diff
inventory. Restore uses it only to report the tracked count; it does not use it to
delete generated files.

Run the two-paper A/B at the approved 5000-character target:

```bash
sudo bash -lc 'set -euo pipefail; umask 077; set -a; source /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env; set +a; ROOT=/home/ubuntu/vibe_proj/niu-secretary; DB="$ROOT/airesearch/data/airesearch.sqlite3"; RUN_DIR="$ROOT/backups/airesearch-deep-readings-20260811-40"; PYTHONPATH="$ROOT/airesearch/src" "$ROOT/airesearch/.venv/bin/python" "$ROOT/airesearch/scripts/generate_deep_readings.py" ab --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR" --target-chars 5000'
```

`ab` automatically writes its machine-scoring choice to `winner.json` and promotes
the winning versions for both sample papers as current in the database. Before
invoking `batch`, the operator must inspect all four generated outputs,
`ab-report.json`, and `winner.json`, confirming hard gates, factual/numerical
grounding, formula and table explanation, all required visible H2 sections,
local embedded-image coverage and de-duplication, Chinese quality,
retries, and latency. Do not edit or overwrite `winner.json`; read its
`model_arm` field for the resumable full-40 batch:

```bash
MODEL_ARM="$(jq -r '.model_arm' "$RUN_DIR/winner.json")"
case "$MODEL_ARM" in deepseek|luna) ;; *) echo "invalid model arm" >&2; exit 2 ;; esac
sudo bash -lc "set -euo pipefail; umask 077; set -a; source /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env; set +a; ROOT=/home/ubuntu/vibe_proj/niu-secretary; DB=\"\$ROOT/airesearch/data/airesearch.sqlite3\"; RUN_DIR=\"\$ROOT/backups/airesearch-deep-readings-20260811-40\"; PYTHONPATH=\"\$ROOT/airesearch/src\" \"\$ROOT/airesearch/.venv/bin/python\" \"\$ROOT/airesearch/scripts/generate_deep_readings.py\" batch --db \"\$DB\" --paper-list \"\$RUN_DIR/papers.txt\" --out \"\$RUN_DIR\" --model-arm '$MODEL_ARM' --target-chars 5000 --concurrency 4"
```

`batch` first validates that `winner.json` and `ab-report.json` match the backup
manifest `backup_id`, the complete ordered 40-paper list, the current prompt
version, the requested runtime model arm/model/API style, and both A/B sample
source hashes. It then freshly audits the two promoted A/B winners, including the
visible-H2 and embedded-image hard gates. Versions created before these Markdown
guarantees are stale and are regenerated when they fail that audit; only compliant
versions are reused without provider calls. Existing compliant deep readings are
resumed; normally the 20 newly selected papers plus any stale original paper
trigger generation. Rerun the identical full-list `batch`
command after interruption;
matching completed rows are audited and reused. `batch-summary.json` must report
all 40 requested papers completed and zero failures. A shortened list is invalid.
Validated outline and section responses are persisted immediately in
`paper_blog_generation_cache`. Both `ab` and `batch` call the generator with
`force=False`, so a provider 502/503, timeout, process exit, or systemd restart
continues from those checkpoints when the paper source hash, prompt version,
model, and request hash still match. The published post/version remains atomic:
no new `paper_blog_versions` or current-version pointer is committed until the
complete Markdown passes all generation gates. Production launch scripts must
read `AIRESEARCH_FACT_MODEL` from `airesearch/.env`; they must not derive it from
`AIRESEARCH_FORMULA_OCR_MODEL`.
Before publishing, run `workflow-check` for all 40 keys. Database,
facts, Chinese artifacts, layout, image, formula, table, and blog checks must pass;
the public HTML checks remain stale until the one-time rebuild.

```bash
set -euo pipefail
mkdir -p "$RUN_DIR/workflow-before-publish"
while IFS= read -r paper_key; do
  PYTHONPATH="$ROOT/airesearch/src" "$ROOT/airesearch/.venv/bin/python" \
    -m airesearch.cli --db "$DB" workflow-check --paper-key "$paper_key" \
    > "$RUN_DIR/workflow-before-publish/$paper_key.json"
done < "$RUN_DIR/papers.txt"
```

Only after all 40 are validated, rebuild and deploy once:

```bash
set -euo pipefail
cd /home/ubuntu/vibe_proj/niu-secretary/airesearch
source ./activate.sh
python -m airesearch.cli --db data/airesearch.sqlite3 run-mvp-pipeline --out-dir exports/mvp-current
python -m airesearch.cli --db data/airesearch.sqlite3 publish-static-site --source-dir exports/mvp-current/bundle --out-dir exports/site-current
sudo ./deploy/deploy-airesearch.sh
```

Verify all 40 again with `--site-dir exports/site-current`, HTTP `200` for the blog
index and each paper page, 41 total published deep readings including the existing
`colavla`, and desktop/mobile rendering for at least `what-if-world`, `world2vlm`,
`world-model-self-distillation`, `2606_00269`, and `wbench`. Check no horizontal
overflow, failed local image, raw LaTeX, unusable table overflow, or same-tab
external paper/GitHub link.

```bash
set -euo pipefail
mkdir -p "$RUN_DIR/workflow-after-publish"
while IFS= read -r paper_key; do
  python -m airesearch.cli --db data/airesearch.sqlite3 workflow-check \
    --paper-key "$paper_key" --site-dir exports/site-current \
    > "$RUN_DIR/workflow-after-publish/$paper_key.json"
  curl --fail --silent --show-error \
    "http://127.0.0.1/niu-secretary/airesearch/papers/$paper_key.html" \
    > /dev/null
done < "$RUN_DIR/papers.txt"
curl --fail --silent --show-error \
  http://127.0.0.1/niu-secretary/airesearch/blogs/index.html > /dev/null
```

The run directory contains `preflight.json`, append-only sanitized `ab.jsonl` and
`batch.jsonl`, `ab-report.json`, the automatically written machine decision
`winner.json`, `batch-summary.json`, backup JSON files and manifest, and
workflow/HTTP/Playwright evidence.
JSONL rows record paper key, source hash, model arm/model, prompt version, status,
version IDs, character count, duration, audit result, and a sanitized error. No
artifact may contain API key values.

To roll back the selected blog database rows before or after generation, use the
incremental backup, then rebuild/publish once so static output matches the
restored database:

```bash
sudo bash -lc 'set -euo pipefail; ROOT=/home/ubuntu/vibe_proj/niu-secretary; DB="$ROOT/airesearch/data/airesearch.sqlite3"; RUN_DIR="$ROOT/backups/airesearch-deep-readings-20260811-40"; PYTHONPATH="$ROOT/airesearch/src" "$ROOT/airesearch/.venv/bin/python" "$ROOT/airesearch/scripts/generate_deep_readings.py" restore --db "$DB" --backup-dir "$RUN_DIR"'
```

Restore replaces the selected papers' rows in `paper_blog_posts`,
`paper_blog_versions`, and `paper_blog_generation_cache` with the backed-up rows.
It deliberately deletes no assets (`deleted_asset_count` is `0`), leaves all blog
files on disk, and reports post-backup paths as `retained_unowned_assets` plus the
informational `created-assets.json` count. Review that report and handle any file
cleanup separately only after establishing ownership.

For a deployment-only failure, leave the database intact and restore the most
recent pre-deploy static snapshot with `sudo airesearch/deploy/rollback-airesearch.sh latest`
from the repository root. Never use a static rollback as a substitute for database
restore when blog rows themselves must be reverted.

## CLI Quick Reference

Run commands from `airesearch/` after `source ./activate.sh`.

Ledger and paperpipe sync:

```bash
python -m airesearch.cli init-db
python -m airesearch.cli sync-paperpipe
python -m airesearch.cli batch-ingest manifests/approved-stage-2c.txt
python -m airesearch.cli batch-ingest manifests/approved-stage-2c.txt --no-normalize-urls
python -m airesearch.cli normalize-url "https://proceedings.neurips.cc/..."
python -m airesearch.cli status
```

Native layout v2:

```bash
python -m airesearch.cli parse-layout --paper-key world-action-models --layout-output-dir data/layout
python -m airesearch.cli parse-layout --paper-key world-action-models --force --layout-output-dir data/layout
python -m airesearch.cli layout-status --paper-key world-action-models
python -m airesearch.cli parse-missing-layouts --limit 10 --layout-output-dir data/layout
python -m airesearch.cli extract-layout-evidence-graph --paper-key world-action-models
python -m airesearch.cli extract-layout-evidence-graph
python -m airesearch.cli export-layout-evidence-graph --out exports/layout-evidence-graph-current.json
python scripts/rerun_all_layouts.py --db data/airesearch.sqlite3 --layout-output-dir data/layout --log-dir ../backups/airesearch-layout-full-rerun-$(date +%Y%m%d%H%M%S)
python -m airesearch.cli workflow-check --paper-key colavla --site-dir exports/site-current
```

The full-rerun script is resumable from `rerun.jsonl`, enforces a free-space guard, validates non-empty pages/blocks, and prunes old runs only after the replacement commits successfully. The 2026-08-11 production run processed 209/209 papers with zero failures; the post-run audit found 2,263 valid canonical equations across 207 papers and 1,705 structured table blocks, with zero invalid LaTeX, replacement characters, duplicate canonical formulas, collapsed tables, column mismatches, or overlapping duplicate tables.

Discovery and canonical review:

```bash
python -m airesearch.cli seed-profiles
python -m airesearch.cli discover-candidates --profile diffusion_models --provider arxiv --limit 50
python -m airesearch.cli list-candidates --profile diffusion_models --limit 20
python -m airesearch.cli export-candidates --profile diffusion_models --limit 100 --out manifests/diffusion_models_top100.txt
python -m airesearch.cli dedupe-candidates
python -m airesearch.cli list-canonical-candidates --limit 20
python -m airesearch.cli export-canonical-candidates --limit 100 --out exports/canonical-candidates-current.json
python -m airesearch.cli set-canonical-status <canonical-key> --status rejected
python -m airesearch.cli select-canonical-candidates --limit 10 --min-score 0.70
python -m airesearch.cli export-approved-candidates --out manifests/approved-stage-2c.txt
python -m airesearch.cli export-candidate-review --out exports/candidate-review-current.json --markdown-out exports/candidate-review-current.md --limit 100 --min-score 0.60
```

Knowledge graph, code links, and facts:

```bash
python -m airesearch.cli extract-paper-cards
python -m airesearch.cli list-paper-cards --limit 20
python -m airesearch.cli export-paper-cards --out exports/paper-cards-stage-2d.jsonl
python -m airesearch.cli extract-code-links
python -m airesearch.cli list-code-links --limit 20
python -m airesearch.cli export-code-links --out exports/code-links-stage-2d2.jsonl
python -m airesearch.cli extract-artifact-ledger
python -m airesearch.cli export-artifact-ledger --out exports/artifact-ledger-current.md
python -m airesearch.cli export-artifact-ledger --format json --out exports/artifact-ledger-current.json
python -m airesearch.cli extract-research-facts --provider openai-compatible --model "$AIRESEARCH_FACT_MODEL" --base-url "$OPENAI_BASE_URL" --concurrency 5 --fact-error-policy warn
python -m airesearch.cli list-research-facts --type claim --limit 20
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
| `layout_evidence_graph.py` | Deterministically link research facts to layout figures, tables, and equations with bounded public/admin projections. |
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
| `paper_blog.py` | Build grounded evidence packs and generate/version deep readings over Chat Completions or Responses. |
| `blog_batch.py` | Preflight, back up, A/B audit, resume, and restore controlled deep-reading batches. |
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
| `exports/canonical-candidates-current.json` | `export-canonical-candidates` | Reviewable canonical candidate export with deduped identities and scores. |
| `exports/candidate-review-current.{json,md}` | `export-candidate-review` | Candidate selection/rejection reason report for manual review. |
| `exports/mvp-current/candidate-review.{json,md}` | `run-launch-refresh` | Latest launch-refresh candidate review reports written automatically unless overridden. |
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
| `exports/mvp-current/bundle/index.html` | `run-mvp-pipeline` | Static HTML dashboard entry point for the current launchable MVP report site. |
| `exports/mvp-current/bundle/api/` | `run-mvp-pipeline` | Lightweight static API shards for dashboard metrics, paper list/details, clusters, client-side search, and the Research Map graph. |
| `exports/mvp-current/bundle/assets/` | `run-mvp-pipeline` | Shared Academic Calm CSS and vanilla JS for the generated static site. |
| `exports/mvp-current/bundle/site-manifest.json` | `run-mvp-pipeline` | Publish file list used to exclude heavy intermediate artifacts from `exports/site-current/`. |
| `exports/mvp-current/bundle/search-index.json` | `run-mvp-pipeline` | Compatibility report search index used by older tooling; compacted to report metadata and snippets. |
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
| `backups/airesearch-deep-readings-<date>/` | `generate_deep_readings.py` | Selected paper lists, incremental blog backup, sanitized A/B and batch logs, score reports, verification evidence, and final summary. |

## Test Coverage Map

| Area | Tests |
| --- | --- |
| Ledger, config, sync, batch, URL normalization | `tests/test_config.py`, `tests/test_db.py`, `tests/test_paperpipe_sync.py`, `tests/test_batch.py`, `tests/test_url_normalizer.py` |
| Discovery and candidates | `tests/test_profiles.py`, `tests/test_providers.py`, `tests/test_provider_cache.py`, `tests/test_discovery.py`, `tests/test_candidates.py`, `tests/test_canonical_candidates.py` |
| L2 graph, layout evidence, code, artifact ledger, facts | `tests/test_knowledge_graph.py`, `tests/test_layout_evidence_graph.py`, `tests/test_code_links.py`, `tests/test_artifact_ledger.py`, `tests/test_fact_extraction.py`, `tests/test_fact_audit.py`, `tests/test_evidence_repair.py`, `tests/test_claim_trace.py` |
| Reports and full workflow | `tests/test_research_digest.py`, `tests/test_research_map.py`, `tests/test_research_gap_analysis.py`, `tests/test_research_synthesis.py`, `tests/test_research_narrative.py`, `tests/test_research_bundle.py`, `tests/test_research_site.py`, `tests/test_workflow_check.py` |
| Clusters and review | `tests/test_embeddings.py`, `tests/test_research_clusters.py`, `tests/test_research_cluster_calibration.py`, `tests/test_research_cluster_review.py`, `tests/test_research_review_editor.py`, `tests/test_research_review_summary.py` |
| MVP launch pipeline | `tests/test_mvp_pipeline.py`, `tests/test_static_publish.py`, `tests/test_launch_refresh.py`, `tests/test_launch_ops.py` |
| Deep-reading providers and batch operations | `tests/test_paper_blog.py`, `tests/test_blog_batch.py` |
| CLI | `tests/test_cli.py` |

## Feature Documentation Rule

For each new feature:

- Add a design doc under `docs/superpowers/specs/YYYY-MM-DD-<stage>-<feature>-design.md`.
- Add an implementation plan under `docs/superpowers/plans/YYYY-MM-DD-<stage>-<feature>.md`.
- Update `PLAN.md` with status, real export counts, and test results.
- Update this `DEVELOPMENT.md` if commands, environment variables, outputs, or verification steps change.
- Keep generated exports under `exports/` with a stable `*-current` name for the latest local run.

## Feature Log

### 2026-08-10 Layout Evidence Knowledge Graph

- Added deterministic fact-to-layout evidence extraction over existing SQLite graph tables with stable node keys, type compatibility, quality gates, provenance, and three-stage matching.
- Added CLI extraction/export commands and automatic refresh from fact extraction, layout parsing, admin fact mutations, MVP pipeline, and bundle generation.
- Added bounded `layout-evidence-graph.json`, public paper API `evidence_graph`, the public `证据关系` section, and the admin `事实关联` inspector tab.
- Public output is redacted and capped; admin output retains matching diagnostics and provenance.
- Added `idx_kg_edges_target_key` for foreign-key cascade cleanup; the 209-paper idempotent graph rebuild dropped from roughly five minutes to 35 seconds on the production database.
- Deduplicated identical same-page relation targets and guarded Vue paper/layout requests with selection tokens so stale responses cannot overwrite the currently selected paper inspector.
- Production verification: 209 papers, 2081 facts, 31226 extractor-owned nodes, 31275 extractor-owned edges, 49 conservative `supported_by` links across 34 papers; 438 AIResearch tests, 86 platform tests plus 32 subtests, Vue build, admin Playwright smoke, `colavla` workflow 13/13, and desktop/mobile production checks all passed.
- Design and implementation plan: `../docs/superpowers/specs/2026-08-10-airesearch-layout-evidence-knowledge-graph-design.md` and `../docs/superpowers/plans/2026-08-10-airesearch-layout-evidence-knowledge-graph.md`.

### 2026-08-09 Public Layout Evidence Rendering And Full Workflow Check

- Public paper JSON now exports bounded structured table previews with `table_rows`, `display_quality`, and `preview_truncated`; parser-provided HTML is never rendered publicly.
- Public paper pages render escaped semantic tables, MathJax formulas, provenance, and explicit high-confidence/review/fallback labels.
- `workflow-check --site-dir` validates the generated public JSON and HTML in addition to ingest, five fact types, Chinese output, layout, visual, table, equation, and deep-reading capabilities.
- Current production corpus is 209 papers and 2081 facts. The deployed site contains 209 paper JSON shards and 209 paper detail pages.
- Verification: 425 AIResearch tests, 86 platform audit tests, Vue production build, admin Playwright smoke, real `colavla` workflow 13/13, and desktop/mobile production DOM checks for three representative papers.
- Reusable production check: `node scripts/verify_airesearch_public_production.mjs`. Override `AIRESEARCH_PUBLIC_BASE_URL` or `AIRESEARCH_PUBLIC_PAPERS` when needed.

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
- New tests: 30 (`tests/test_url_normalizer.py`), including categorization of all 14 failed papers as a regression suite. Current full suite: 248 passed after the Web redesign v2 and CLI coverage additions.

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

### 2026-06-10 Web Redesign V2

- `research_site.py` now renders the AIResearch Web export as a multi-page Academic Calm static site instead of embedding full report Markdown into one large HTML page.
- Generated pages include dashboard, paper list, per-paper details, cluster list/details, digest, map, gaps, synthesis, and narrative report views.
- The map page renders a self-hosted D3 v7 force-directed topic-paper graph from `api/relations-graph.json` with fact-type filters, node dragging, and click-to-inspect behavior. Current graph shard: 107 nodes, 60 edges, 44KB.
- Research Digest now renders as a 16KB compact page instead of an 892KB raw Markdown dump.
- Gap Analysis now renders as a 32KB visual page rather than a raw report dump.
- Research Synthesis now renders as an 8KB structured readiness page instead of a 44KB raw report view.
- Narrative now renders as a structured evidence/action page instead of a generic raw Markdown report view.
- `papers/index.html` now loads paper cards from `api/papers.json` at runtime, reducing the published index from 152KB to 4KB while keeping the 172KB paper metadata shard cacheable.
- Web acceptance budgets are covered in `tests/test_research_site.py`: initial DOM node count below 2,000, mobile viewport/media-query presence, papers index below 30KB, and lightweight search filtering below 100ms.
- Generated assets include `assets/site.css`, `assets/site.js`, `assets/d3.v7.min.js`, and lightweight `api/` shards. On the current 202-paper corpus, published `index.html` is 8.7KB, `digest/index.html` is 16KB, `papers/index.html` is 2.6KB, `map/index.html` is 3KB, `gaps/index.html` is 32KB, `synthesis/index.html` is 8KB, `narrative/index.html` is 12KB, `api/search-index.json` is 368KB, `api/papers.json` is 172KB, and self-hosted D3 is 274KB.
- `static_publish.py` honors `site-manifest.json` so `exports/site-current/` contains only publishable Web files. The current published site is 13MB instead of copying the full bundle with heavy intermediate artifacts.
- Final public-host verification passed on `/niu-secretary/airesearch/`: nginx serves the updated site, gzip returns `Content-Encoding: gzip`, Lighthouse scores are Performance 100 / Accessibility 96 / Best Practices 96 / SEO 100, and Chrome iPhone 12 viewport screenshots render without page-level horizontal overflow.
- Focused verification passed: `tests/test_research_site.py tests/test_static_publish.py tests/test_cli.py tests/test_mvp_pipeline.py` with 77 tests. Full suite passed with 249 tests.

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
