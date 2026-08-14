# AIResearch API Usage

Last updated: 2026-08-11

This document records the current AIResearch interfaces used by the Niu Secretary admin console, public paper pages, and paper workflows. AIResearch borrows selected MinerU design ideas without installing or embedding MinerU. The current production-ready subset includes native layout v2 parsing, structured layout status, representative visual selection, deterministic fact-to-layout evidence graphs, public evidence panels, the admin Layout Evidence Inspector, and deep-reading blog generation.

## Base API

Public web root:

```text
http://124.222.22.171/niu-secretary/
```

API root used by the Vue frontend:

```text
/niu-secretary/api
```

Admin requests require:

```http
Authorization: Bearer <admin-token>
```

The frontend obtains the token with `POST /niu-secretary/api/admin/session`.

## Public Static Paper API

Public paper detail pages are generated under:

```text
/niu-secretary/airesearch/papers/<paper_key>.html
```

Each paper also has a static JSON shard:

```http
GET /niu-secretary/airesearch/api/papers/<paper_key>.json
```

The JSON is public and does not require an admin token. It includes `layout_evidence` from the latest native layout v2 run and a bounded `evidence_graph` projection:

```json
{
  "paper_key": "maskalign",
  "layout_evidence": {
    "api_version": "layout-evidence-v1",
    "latest_run": { "status": "completed", "provider": "airesearch_layout" },
    "summary": {
      "document_type": "digital",
      "page_count": 14,
      "block_count": 516,
      "equation_blocks": 40,
      "structured_table_blocks": 1,
      "high_quality_evidence_blocks": 86
    },
    "ocr": {
      "mode": "auto",
      "languages": "eng+chi_sim",
      "pages_attempted": 0,
      "pages_succeeded": 0,
      "block_count": 0
    },
    "formula_ocr": {
      "mode": "auto",
      "blocks_succeeded": 0,
      "models": []
    },
    "equations": [
      {
        "equation_id": "eq-1",
        "page": 4,
        "source_reference": "page 4, block 12",
        "latex": "..."
      }
    ],
    "tables": [
      {
        "page": 6,
        "source_reference": "page 6, block 2",
        "caption": "Benchmark results...",
        "table_markdown": "| Model | Score |",
        "table_rows": [["Model", "Score"], ["Ours", "78.4"]],
        "display_quality": "good",
        "preview_truncated": false
      }
    ]
  },
  "evidence_graph": {
    "schema_version": "evidence-graph-v1",
    "extractor_version": "2026-08-10.1",
    "available": true,
    "summary": {
      "fact_count": 9,
      "evidence_count": 128,
      "supported_relation_count": 7,
      "unlinked_fact_count": 4,
      "truncated": true
    },
    "facts": [
      {
        "key": "research_fact:maskalign:1431",
        "fact_type": "method",
        "statement": "...",
        "linked": true,
        "evidence": [
          {
            "evidence_key": "layout_evidence:maskalign:147:88955",
            "match_method": "normalized_containment",
            "score": 0.96
          }
        ]
      }
    ],
    "evidence": [],
    "relations": []
  }
}
```

Frontend usage:

- Paper detail workbench renders `实验与评测`, `证据关系`, `公式`, `表格`, and `OCR / Layout` from these fields.
- The static API should be used by public Vue/HTML views that need read-only formulas, table reconstruction, OCR status, or layout counters.
- Admin/debug views should still use `airesearch.admin.paper.layout.detail` for full raw blocks, visual candidates, job context, and artifact paths.
- Do not render `table_html` from layout metadata directly in public pages. Public HTML is generated from escaped `table_rows`; escaped `table_markdown` is the fallback only.

### Public Evidence Display Contract

The public bundle intentionally exposes bounded previews instead of full parser artifacts:

- `tables[].table_rows` contains at most 12 rows and 8 columns. Each normalized cell is at most 160 characters.
- `tables[].preview_truncated` is true when rows, columns, or cell text were bounded.
- `tables[].display_quality` is `good`, `review`, or `fallback`. It combines real row/column shape, reconstruction method, quality score, and caption evidence.
- `good` renders as `结构化预览`; `review` renders as `需要复核`; `fallback` renders as `文本降级`.
- Formula display quality is semantic. Malformed, unbalanced, or implausibly short LaTeX is shown as `低可信文本`; completed high-score OCR is `高可信公式`; other usable extraction is `自动提取`.
- Formula cards use escaped `\\[...\\]` MathJax input and retain escaped raw LaTeX in a collapsible detail block.
- Structured tables render escaped semantic `<table>` markup inside a local horizontal scroll container. They never create page-level horizontal overflow.
- Public graph caps are 24 facts, 48 evidence nodes, 72 relations, three links per fact, and 240 characters per preview. It excludes local paths, raw table HTML, full metadata, provider internals, and provenance.
- Match targets with the same evidence type, page, and normalized content are collapsed before the three-link cap, so adjacent parser fragments do not appear as duplicate fact links.

Use the static JSON for public display. Use the authenticated layout detail endpoint when full blocks, cell geometry, OCR errors, candidates, or artifact paths are required.

## Admin Data Endpoint

Read-only admin resources use:

```http
GET /niu-secretary/api/admin/data?resource=<resource>&key=value
Authorization: Bearer <admin-token>
```

### Admin State

```http
GET /niu-secretary/api/admin/data?resource=airesearch.admin.state
Authorization: Bearer <admin-token>
```

Purpose:

- Feeds the AIResearch admin overview and paper-management list.
- Returns compact per-paper blog and layout status without loading large layout artifacts.
- Lets the frontend show layout v2 coverage before the user opens a paper detail panel.

Per-paper layout fields in `state.papers[]`:

```json
{
  "paper_key": "world-action-models",
  "title": "World Action Models",
  "blog_status": "published",
  "layout_status": "completed",
  "layout_latest_run_id": 123,
  "layout_parser_version": "v2",
  "layout_artifact_count": 14,
  "layout_block_count": 88,
  "layout_evidence_ready_blocks": 11,
  "layout_captioned_visual_blocks": 3,
  "layout_structured_table_blocks": 1,
  "layout_equation_blocks": 4,
  "layout_page_count": 12,
  "layout_finished_at": "2026-07-11T00:00:00+00:00",
  "layout_latest_job_status": "completed",
  "layout_latest_job_message": "paper layout parsed"
}
```

Frontend usage:

- Paper list badges use `layout_status`, `layout_evidence_ready_blocks`, `layout_captioned_visual_blocks`, `layout_structured_table_blocks`, and `layout_equation_blocks`.
- The top paper stats card counts papers where `layout_status == "completed"`.
- Detail, blog-generation, and Layout Evidence Inspector panels call layout detail for full artifacts, evidence blocks, visual candidates, OCR/read-order status, and latest job context.

### Layout V2 Detail

```http
GET /niu-secretary/api/admin/data?resource=airesearch.admin.paper.layout.detail&paperKey=<paper_key>
Authorization: Bearer <admin-token>
```

Purpose:

- Shows whether a paper has been parsed by native layout v2.
- Returns parser artifacts, block counts, evidence-ready blocks, visual candidates, and the latest parse job.
- Feeds the admin blog preflight panel and the paper-management `Layout Evidence Inspector`.

Important response fields:

```json
{
  "ok": true,
  "result": {
    "api_version": "layout-v2",
    "paper_key": "world-action-models",
    "enabled": true,
    "latest_run": {
      "id": 123,
      "paper_key": "world-action-models",
      "provider": "airesearch_layout",
      "provider_version": "v2",
      "backend": "pymupdf",
      "method": "native",
      "status": "completed",
      "input_pdf_path": ".../paper.pdf",
      "output_dir": ".../data/layout/world-action-models/...",
      "stats": {
        "block_count": 88,
        "artifact_count": 14,
        "summary": {
          "parser": "airesearch_layout",
          "parser_version": "v2",
          "captioned_visual_blocks": 3,
          "structured_table_blocks": 1,
          "equation_blocks": 4,
          "evidence_ready_blocks": 11
        }
      }
    },
    "summary": {
      "parser": "airesearch_layout",
      "parser_version": "v2",
      "captioned_visual_blocks": 3,
      "structured_table_blocks": 1,
      "geometry_table_blocks": 1,
      "text_fallback_table_blocks": 0,
      "spanning_table_blocks": 1,
      "reading_order": {
        "method": "geometry_columns_v2",
        "pages_completed": 12,
        "multi_column_pages": 9,
        "cross_column_blocks": 18,
        "caption_paired_blocks": 3,
        "low_confidence_blocks": 0,
        "average_confidence": 0.88
      },
      "equation_blocks": 4,
      "evidence_ready_blocks": 11,
      "high_quality_evidence_blocks": 7,
      "high_quality_visual_blocks": 2,
      "high_quality_table_blocks": 1,
      "high_quality_equation_blocks": 3
    },
    "capabilities": {
      "has_markdown": true,
      "has_content_list": true,
      "has_structure_json": true,
      "has_assets": true,
      "has_visual_blocks": true,
      "has_captioned_visual_blocks": true,
      "has_structured_tables": true,
      "has_geometry_tables": true,
      "has_spanning_table_cells": true,
      "has_text_fallback_tables": false,
      "has_reading_order": true,
      "has_multi_column_reading_order": true,
      "has_caption_paired_reading_order": true,
      "needs_reading_order_attention": false,
      "has_equations": true,
      "has_evidence_blocks": true,
      "has_high_quality_evidence": true,
      "has_high_quality_tables": true,
      "has_high_quality_equations": true
    },
    "block_counts": {
      "image": 3,
      "interline_equation": 4,
      "table": 1,
      "text": 70,
      "title": 10
    },
    "artifacts_by_type": {
      "layout_markdown": [{ "path": "..._layout.md" }],
      "layout_content_list": [{ "path": "..._content_list.json" }],
      "layout_structure_json": [{ "path": "..._layout.json" }],
      "layout_summary_json": [{ "path": "..._layout_summary.json" }],
      "layout_asset": [{ "path": ".../assets/page-1-image-..." }]
    },
    "sample_blocks": [
      {
        "page_index": 0,
        "block_index": 0,
        "block_type": "title",
        "bbox": [72.0, 56.0, 420.0, 80.0],
        "text": "Paper Title",
        "asset_path": "",
        "source_reference": "page=1 block=0",
        "metadata": { "parser": "airesearch_layout" }
      }
    ],
    "evidence_blocks": [
      {
        "page_index": 0,
        "block_index": 5,
        "block_type": "image",
        "asset_path": "assets/page-1-image-5.png",
        "source_reference": "page=1 block=5",
        "evidence_kind": "figure",
        "evidence_confidence": 0.86,
        "metadata": {
          "caption": "Figure 1. System overview.",
          "caption_kind": "figure",
          "quality_score": 0.86,
          "quality_reasons": ["evidence-kind", "caption-linked", "figure-caption", "asset", "usable-bbox"]
        }
      },
      {
        "page_index": 1,
        "block_index": 6,
        "block_type": "table",
        "source_reference": "page=2 block=6",
        "evidence_kind": "table",
        "metadata": {
          "table_rows": [["Method", "Score"], ["Baseline", "71.2"], ["Ours", "78.4"]],
          "table_cells": [
            {"row": 0, "column": 0, "row_span": 1, "column_span": 1, "bbox": [72, 100, 118, 112], "text": "Method", "confidence": 0.97},
            {"row": 0, "column": 1, "row_span": 1, "column_span": 1, "bbox": [250, 100, 286, 112], "text": "Score", "confidence": 0.96}
          ],
          "table_header_row_count": 1,
          "table_column_anchors": [95.0, 268.0],
          "table_column_boundaries": [72.0, 181.5, 300.0],
          "table_has_spanning_cells": false,
          "table_reconstruction_method": "word_geometry_v2",
          "table_reconstruction_confidence": 0.91,
          "table_reconstruction_reasons": ["word-bbox-geometry", "repeated-column-anchors"],
          "table_markdown": "| Method | Score |\n| --- | --- |\n| Baseline | 71.2 |\n| Ours | 78.4 |",
          "table_html": "<table><thead><tr><th>Method</th><th>Score</th></tr></thead><tbody><tr><td>Baseline</td><td>71.2</td></tr><tr><td>Ours</td><td>78.4</td></tr></tbody></table>"
        }
      }
    ],
    "representative_visual": {
      "source_kind": "pdf_figure_crop",
      "asset_kind": "figure",
      "source_reference": "pdf page=2 figure=1 caption_window",
      "reason": "pdf_figure_crop, figure=1, page=2, 1244x827"
    },
    "visual_candidates": [],
    "evidence_graph": {
      "schema_version": "evidence-graph-v1",
      "summary": {
        "fact_count": 9,
        "evidence_count": 128,
        "supported_relation_count": 7,
        "unlinked_fact_count": 4
      },
      "facts": [],
      "evidence": [],
      "relations": []
    }
  }
}
```

Use in frontend:

- In the blog generator, show `capabilities` as the evidence preflight status.
- Use `summary.captioned_visual_blocks`, `summary.structured_table_blocks`, `summary.geometry_table_blocks`, `summary.text_fallback_table_blocks`, `summary.spanning_table_blocks`, `summary.reading_order.*`, `summary.equation_blocks`, and `summary.high_quality_evidence_blocks` for compact metrics.
- Treat `summary.reading_order.method == "geometry_columns_v2"` as the native reading-order pass. Show `multi_column_pages`, `cross_column_blocks`, and `caption_paired_blocks` as positive coverage; show `low_confidence_blocks` as a review signal.
- Treat `table_reconstruction_method` values `word_geometry_v2` and `pymupdf_table_lines` as geometry-backed. `text_spacing_v1` is a compatibility fallback and should be shown as lower reliability in inspection UI.
- `pymupdf_table_lines` requires `PyMuPDF>=1.27.0` with runtime `page.find_tables()` support. Older runtimes skip line-based region detection and retain word-geometry/fallback parsing without changing the API schema.
- Use `representative_visual` for the selected cover/hero candidate.
- Treat `representative_visual.source_reference` values ending in `figure_bbox` as tight crops around a caption-linked visual block, and values ending in `caption_window` as PDF re-rendered whole-figure crops generated from the Figure caption. Both are intended to avoid embedded layout assets that are missing, duplicated, pure text, or only contain a partial arrow/layer.
- Prefer `evidence_blocks` with `metadata.quality_score >= 0.72` for deep-reading prompts and admin evidence inspectors.
- The paper-management `Layout Evidence Inspector` renders six tabs from this response:
  - `事实关联`: `evidence_graph` fact rows, linked/unlinked state, evidence page/type, matching method/score, node keys, and provenance.
  - `证据块`: `evidence_blocks` with `metadata.quality_score`, `metadata.quality_reasons`, `source_reference`, and source paths.
  - `公式 OCR`: `evidence_blocks` / `sample_blocks` where `block_type == "interline_equation"`, using `metadata.formula_latex`, `formula_ocr_candidate_latex`, model, status, confidence, and crop provenance.
  - `表格结构`: table blocks with `metadata.table_markdown`, `table_rows`, `table_cells`, reconstruction method, confidence, and quality reasons.
  - `OCR / 读序`: `summary.ocr`, `summary.formula_ocr`, `summary.reading_order`, and sample blocks where `metadata.ocr == true`.
  - `视觉候选`: `representative_visual` plus `visual_candidates`.
- Do not read `paper_layout_*` tables directly from frontend code.

## Admin Action Endpoint

Mutating admin work uses:

```http
POST /niu-secretary/api/admin/actions/execute
Authorization: Bearer <admin-token>
Content-Type: application/json
```

Payload shape:

```json
{
  "action": "airesearch.admin.paper.layout.generate",
  "input": {
    "paperKey": "world-action-models",
    "force": false
  },
  "context": {
    "confirmed": true
  }
}
```

### Single Paper Ingest

Action:

```text
airesearch.paper.ingest_single
```

Input:

```json
{
  "input": "2607.00001"
}
```

Purpose:

- Runs `papi add <input>` for a single title, arXiv ID, PDF URL, or supported paper URL.
- Synchronizes PaperPipe into the AIResearch database.
- Detects the ingested `paper_key` from `papi` output or from the newly synchronized paper.
- Automatically queues `paper_layout_parse` when the paper does not already have a completed layout run or active layout job.

Important response fields:

```json
{
  "ok": true,
  "action": "airesearch.paper.ingest_single",
  "paper_key": "2607_00001",
  "status": "success",
  "layout_job_id": 456,
  "layout_job_status": "queued",
  "layout_job_reason": "",
  "message": "论文已入库，版面解析任务已加入队列 #456。"
}
```

Deduplication:

- If a completed/skipped layout run already exists, `layout_job_status` is `skipped` and `layout_job_reason` is `layout_exists`.
- If a queued/running layout job already exists, `layout_job_status` is `existing` and `layout_job_id` points to the active job.
- If `paper_key` cannot be detected, ingest can still succeed but layout auto-queue is skipped.

### Trigger Layout Parse

Action:

```text
airesearch.admin.paper.layout.generate
```

Input:

```json
{
  "paperKey": "world-action-models",
  "force": false,
  "maxPages": 6,
  "ocrMode": "auto",
  "ocrLanguages": "eng+chi_sim",
  "ocrDpi": 220,
  "formulaOcrMode": "off",
  "formulaOcrDpi": 260,
  "formulaOcrMinConfidence": 0.7
}
```

Behavior:

- Creates an `admin_jobs` row with job type `paper_layout_parse`.
- The background worker runs `parse_paper_layout`.
- If `force` is false and a completed layout v2 run already exists, the job reuses it.
- If `force` is true, a new run is created.

After calling the action, poll:

```http
GET /niu-secretary/api/admin/data?resource=airesearch.admin.paper.layout.detail&paperKey=world-action-models
```

Completion signal:

- `result.latest_job.status == "completed"`
- `result.latest_run.status == "completed"`

Failure signal:

- `result.latest_job.status == "failed"`
- or `result.latest_run.status == "failed"`
- `latest_run.error` contains the parser error when available.

### Generate Deep-Reading Blog

Action:

```text
airesearch.admin.paper.blog.generate
```

Input:

```json
{
  "paperKey": "world-action-models",
  "force": false,
  "targetWordCount": 5000,
  "model": "deepseek-v4-pro"
}
```

`model` is optional. The server chooses the configured/default model when it is
omitted. Clients cannot supply the provider endpoint, proxy, protocol, or API key;
those values come only from trusted server environment variables.

Recommended flow:

1. Call layout detail.
2. If `capabilities.has_evidence_blocks` is false, call layout generate first.
3. Call blog generate.
4. Poll `airesearch.admin.paper.blog.detail`.

During generation, the evidence pack evaluates native layout PDF crops and layout
visuals before invoking source resolvers. The source figure resolver runs only
when fewer than two publishable layout figures are available, and the source
table resolver runs only when no publishable layout table is available. This
fallback gate avoids unnecessary arXiv source downloads and PDF rasterization
when layout evidence already supplies the required visual categories.

Final deep-reading Markdown has deterministic publication guarantees. Every
required section is normalized to a visible H2 heading. Valid section `image_ids`
are rendered as local Markdown images and de-duplicated across the whole blog. If
selected image evidence exists but the final Markdown contains zero embedded
images, validation and batch audit fail.

Evidence-pack formulas are publishable only when they contain neither U+FFFD nor
C0 controls other than tab/newline/CR nor DEL/C1 (`U+007F`-`U+009F`). Filtering
happens before `source_hash`; the filtered equation set participates in that hash,
so a changed set invalidates stale outline and section cache entries.

When facts exist, runtime outline enrichment assigns them by `fact_type` to
semantic sections, de-duplicates IDs across sections, and guarantees at least
`ceil(50%)` valid-fact coverage. The per-section capacity is four by default and
grows for large fact sets. Each section request contains only its assigned facts,
and the model must return exactly the same `fact_ids` set; an empty assignment
remains empty instead of receiving fallback facts.

The admin action is the interactive single-paper path. A successful job writes a
version, makes it current, rebuilds the static site, and deploys the updated blog
surface. The controlled 40-paper runner below intentionally does not rebuild or
deploy per paper; it publishes once only after the complete batch passes.

### Deep-Reading Provider Protocols

The blog provider supports two OpenAI-compatible protocols:

- `chat_completions`: configure an API root; the transport appends
  `/chat/completions`.
- `responses`: configure an API root or full `/responses` endpoint; the transport
  normalizes string or structured response output before JSON validation.

Server configuration:

```dotenv
AIRESEARCH_BLOG_API_STYLE=chat_completions
AIRESEARCH_BLOG_BASE_URL=https://provider.example/v1
AIRESEARCH_BLOG_MODEL=deepseek-v4-pro
AIRESEARCH_BLOG_API_KEY=loaded-from-protected-environment-file
# Responses transport only
AIRESEARCH_BLOG_PROXY=http://127.0.0.1:7890
```

If `AIRESEARCH_BLOG_API_STYLE` is absent, an endpoint ending in `/responses`
selects Responses; all other endpoints use Chat Completions. The general provider
resolves the three setting classes independently:

- Model: explicit `model`, `AIRESEARCH_BLOG_MODEL`, `NIU_ASSISTANT_MODEL`, then
  `deepseek-v4-pro`.
- Base URL: explicit `base_url`, `AIRESEARCH_BLOG_BASE_URL`,
  `OPENCODE_GO_BASE_URL`, `TRANSLATE_BASE_URL`, `OPENAI_BASE_URL`, then the
  built-in DeepSeek base URL.
- API key: `AIRESEARCH_BLOG_API_KEY`, the requested key environment variable,
  `OPENCODE_GO_API_KEY`, `OPENAI_API_KEY`, then `TRANSLATE_API_KEY`.

The named DeepSeek batch arm always uses Chat Completions. Its model precedence is
`AIRESEARCH_DEEPSEEK_BLOG_MODEL`, `AIRESEARCH_BLOG_MODEL`, then the fixed
`deepseek-v4-pro` default; it does not read `NIU_ASSISTANT_MODEL`. Its base URL and
API key are bound by the production runner to `OPENCODE_GO_BASE_URL` and
`OPENCODE_GO_API_KEY`. The named Luna arm uses the same credential, derives the
Responses endpoint, and reads `AIRESEARCH_FORMULA_OCR_MODEL`. Luna is not the
default deep-reading model unless A/B selects it or `AIRESEARCH_BLOG_*`
explicitly configures it.

The runner also accepts DeepSeek-specific model/base/key overrides and
Luna-specific model/base/key/proxy overrides under `AIRESEARCH_DEEPSEEK_BLOG_*`
and `AIRESEARCH_LUNA_BLOG_*`. DeepSeek model resolution remains the fixed chain
above. Chat Completions remains direct; proxy configuration
applies only to Responses. These are environment-only controls, not HTTP fields.

Keep production AI provider keys in the Git-ignored `airesearch/.env` with mode
`600`. `OPENCODE_GO_BASE_URL`, `OPENCODE_GO_API_KEY`, and optional
`OPENCODE_GO_PROXY` are the single OpenCode Go source. Chat Completions appends
`/chat/completions`; Responses appends `/responses`. Keys
must not appear in this repository, HTTP payloads, CLI arguments, database rows,
JSONL logs, reports, or exception text. Logged provider failures redact all loaded
secret values.

### Controlled 40-Paper Batch

This is an operational CLI workflow, not an HTTP endpoint. The approved list is:

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

`what-if-world` and `world2vlm` are the A/B samples and count toward the total.
`omnivl-guard` is omitted because it currently lacks the required `benchmark`
fact. It must pass fact/provenance review before a future batch includes it.

Store the complete approved list at
`backups/airesearch-deep-readings-20260811-40/papers.txt` and use it unchanged for
preflight, backup, A/B, batch, and verification. In a protected shell that has
sourced `/home/ubuntu/vibe_proj/niu-secretary/airesearch/.env`, run:

```bash
sudo -s
set -euo pipefail
umask 077
set -a
source /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env
set +a

ROOT=/home/ubuntu/vibe_proj/niu-secretary
DB="$ROOT/airesearch/data/airesearch.sqlite3"
RUN_DIR="$ROOT/backups/airesearch-deep-readings-20260811-40"
PY="$ROOT/airesearch/.venv/bin/python"
SCRIPT="$ROOT/airesearch/scripts/generate_deep_readings.py"
export PYTHONPATH="$ROOT/airesearch/src"

"$PY" "$SCRIPT" preflight \
  --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR"

"$PY" "$SCRIPT" backup \
  --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR"

"$PY" "$SCRIPT" ab \
  --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR" \
  --target-chars 5000

MODEL_ARM="$(jq -r '.model_arm' "$RUN_DIR/winner.json")"
case "$MODEL_ARM" in deepseek|luna) ;; *) exit 2 ;; esac
"$PY" "$SCRIPT" batch \
  --db "$DB" --paper-list "$RUN_DIR/papers.txt" --out "$RUN_DIR" \
  --model-arm "$MODEL_ARM" --target-chars 5000 --concurrency 4
```

All commands use the same `RUN_DIR`. `manifest.json`, selected-row exports,
`assets.json`, `created-assets.json`, `ab.jsonl`, `ab-report.json`, `winner.json`,
`batch.jsonl`, and restore input must not be split across subdirectories.

The required order is preflight, incremental backup, two-paper A/B, operator
review, and resumable full-40 batch. Preflight must report all 40 ready. The
backup manifest hashes must verify and free disk must stay above 750 MB before
model calls. A successful `ab` automatically writes `winner.json` as its machine
scoring decision and promotes the winning arm's two sample versions as current in
the database. The operator must inspect all four outputs, `ab-report.json`, and
`winner.json` before invoking `batch`; do not edit or overwrite `winner.json` to
represent human approval. Before generation, `batch` requires `winner.json` and
`ab-report.json` to match the manifest `backup_id`, the complete ordered 40-paper
list, the current prompt version, the requested runtime model arm/model/API style,
and the current source hashes of both A/B samples. It then freshly audits those
two promoted versions, including visible required-section H2 headings and local
embedded-image coverage. A/B versions that predate these guarantees are treated
as stale and regenerated when they fail the audit; compliant versions are reused.
The hard gates also require valid fact coverage `>= 0.5`, no U+FFFD or unescaped
model-control token in final Markdown, and formula coverage based only on
publishable formulas that survived evidence filtering.
The runner uses one process with up to four paper workers; each worker owns its
provider, while JSONL and asset tracking remain main-thread writes. Existing
compliant versions are freshly audited and reused. Repeating the same full-list
batch command resumes matching completed papers. A shortened list is invalid. Exit status `2` indicates a
preflight or partial-batch failure; keep the existing public site unchanged.

Run artifacts:

- `preflight.json`: readiness, source hash, fact types/count, equation/image/table
  coverage, and per-paper errors.
- `manifest.json`, the three selected blog-table JSON exports, and
  `assets.json`: row counts, current version IDs, asset paths/hashes, and file
  SHA-256 values.
- `ab.jsonl`: four append-only, sanitized model/paper attempt rows.
- `ab-report.json`: hard gates, weighted components, raw metrics, tie breakers,
  visible H2/image coverage, and scoring version.
- `winner.json`: automatically written machine-scoring decision with
  `backup_id`, the complete 40-paper selection, A/B sample source hashes, prompt
  version, `model_arm`, runtime model/API style, scoring version, and selection
  time. Its existence does not record operator approval.
- `created-assets.json`: informational snapshot-diff inventory of blog assets
  observed after backup. Restore may report its tracked count but never treats it
  as proof of generator ownership and never deletes those files automatically.
- `batch.jsonl` and `batch-summary.json`: resumable attempts and final completion
  status.
`ab` and `batch` write database versions and local blog assets but never export or
deploy the public site. Publish exactly once after `batch-summary.json` reports
zero failures and all 40 versions pass database/workflow acceptance:

```bash
set -euo pipefail
cd /home/ubuntu/vibe_proj/niu-secretary/airesearch
source ./activate.sh
python -m airesearch.cli --db data/airesearch.sqlite3 \
  run-mvp-pipeline --out-dir exports/mvp-current
python -m airesearch.cli --db data/airesearch.sqlite3 \
  publish-static-site --source-dir exports/mvp-current/bundle \
  --out-dir exports/site-current
sudo ./deploy/deploy-airesearch.sh
```

Verification requires 13/13 `workflow-check` results for every selected paper
against `exports/site-current`, HTTP `200` for the blog index and all 40 paper
pages, and 41 published deep readings including the existing `colavla`. Desktop
and mobile checks cover at least `what-if-world`, `world2vlm`,
`world-model-self-distillation`, `2606_00269`, and `wbench`, including local image
loads, MathJax, table overflow, deep-reading navigation, and new-tab external
paper/GitHub links.

Restore the selected blog database rows:

```bash
"$PY" "$SCRIPT" restore --db "$DB" --backup-dir "$RUN_DIR"
```

Restore replaces rows for the selected papers in `paper_blog_posts`,
`paper_blog_versions`, and `paper_blog_generation_cache`. It does not delete blog
assets or other generated files: the result reports `deleted_asset_count: 0`,
retains unowned/post-backup paths in `retained_unowned_assets`, and includes an
informational created-asset count when tracking is available. Review those paths
before any separate, ownership-aware cleanup. After database restore, rebuild and
deploy once so static output matches the restored state. For a deployment-only
failure, keep the database and use
`sudo airesearch/deploy/rollback-airesearch.sh latest` from the repository root
to restore the latest pre-deploy snapshot.

## CLI Equivalents

Parse one paper:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m airesearch.cli \
  --db airesearch/data/airesearch.sqlite3 \
  parse-layout \
  --paper-key world-action-models \
  --layout-output-dir airesearch/data/layout \
  --max-pages 6
```

Force reparse:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m airesearch.cli \
  --db airesearch/data/airesearch.sqlite3 \
  parse-layout \
  --paper-key world-action-models \
  --force
```

Read layout status:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m airesearch.cli \
  --db airesearch/data/airesearch.sqlite3 \
  layout-status \
  --paper-key world-action-models
```

Parse missing papers:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m airesearch.cli \
  --db airesearch/data/airesearch.sqlite3 \
  parse-missing-layouts \
  --limit 10 \
  --layout-output-dir airesearch/data/layout
```

Rebuild or export the fact-to-layout evidence graph:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m airesearch.cli \
  --db airesearch/data/airesearch.sqlite3 \
  extract-layout-evidence-graph --paper-key world-action-models

PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m airesearch.cli \
  --db airesearch/data/airesearch.sqlite3 \
  export-layout-evidence-graph \
  --out airesearch/exports/layout-evidence-graph-current.json
```

Run the complete read-only acceptance check, including generated public JSON and HTML:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m airesearch.cli \
  --db airesearch/data/airesearch.sqlite3 \
  workflow-check \
  --paper-key colavla \
  --site-dir airesearch/exports/site-current
```

This returns 13 checks covering searchability, PDF ingestion, all five fact types, Chinese output, completed layout, layout evidence, representative visual, tables, equations, deep reading, public static API, and the public paper page. The public checks require `evidence-graph-v1` and the visible `证据关系` section. A failure exits with status `2`.

## Integration With Existing Workflows

### Paper Ingestion

Current flow:

1. Add/sync paper into `papers`, `paper_artifacts`, and `paper_cards`.
2. Ensure a `paper_pdf` artifact exists.
3. Trigger `airesearch.admin.paper.layout.generate`.
4. Use layout detail to confirm `capabilities.has_structure_json`.
5. Use `representative_visual` to improve cover selection.
6. Use `evidence_blocks` as structured inputs for paper card enrichment and deep reading.

### Deep Reading

Before generating a blog:

- Prefer papers with `capabilities.has_high_quality_evidence == true`.
- Prefer `representative_visual.source_kind == "pdf_figure_crop"` or `"layout_block"` over stale `cover.webp`.
- Prefer `pdf_figure_crop` candidates with `source_reference` containing `figure_bbox` or `caption_window` when a layout block image looks partial; this is the native layout v2 path for complete Figure 1/2 screenshots. Deep-reading evidence-pack construction evaluates these crops and layout-block visuals first, then calls source figure/table resolvers only for missing required categories. This avoids unnecessary arXiv downloads or PDF rasterization. Candidates are deduplicated by content fingerprint, with a small ordering boost for overview/framework/roadmap/example/qualitative captions.
- `select_blog_images()` keeps `quality_score` and `quality_reasons` on selected image refs, and orders layout-derived candidates with `quality_score >= 0.72` ahead of low-quality fragments.
- OpenAI-compatible blog prompt payloads include `evidence_quality_policy` so the model is explicitly told to prefer high-quality evidence.
- High-quality `interline_equation` blocks are merged into the blog `equations` payload with `source_reference`, `quality_score`, `quality_reasons`, and `extraction_method = "airesearch_layout"`.
- High-quality table blocks with `metadata.table_markdown` are grouped under `artifact_texts.layout_structured_tables`. Prompt bounding reserves table space so long source files cannot silently remove all structured table evidence.
- Use captions from `evidence_blocks[].metadata.caption` as grounded image descriptions.
- Use `interline_equation` evidence blocks as formula evidence when `metadata.quality_score >= 0.72`.
- Use table evidence blocks only when `metadata.table_rows` exists and `metadata.quality_score >= 0.72`; prefer geometry-backed methods over `text_spacing_v1` when both are available.

### Compiler-confirmed formula repair

Formula repair is a local patch workflow, not a deep-reading regeneration workflow. It validates every Markdown formula with the same MathJax v3 TeX engine used by the public site. A formula that compiles is never sent to a model. A formula that fails compilation must be repaired with the configured OpenCode Go Responses provider using the failed LaTeX, local paragraph context, and a PDF page or layout-bbox crop.

```bash
set -a
source /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env
set +a
PYTHONPATH=airesearch/src airesearch/.venv/bin/python \
  airesearch/scripts/repair_blog_formulas.py \
  --db /path/to/airesearch.sqlite3 \
  --paper-key world-model-self-distillation
```

The Luna candidate is normalized for transport only and compiled again. A provider error, missing PDF evidence, low confidence, unavailable compiler, or failed candidate compilation leaves `paper_blog_posts.current_version_id` and all blog content unchanged. Use `--force-retry` to retry a failed audit row for the same source version. Successful runs publish one new version that differs only at the located formula spans and preserve the title, outline, images, tables, model, prompt version, and source hash.

Audit rows are stored in `paper_blog_formula_repairs`. They include paper/version/formula locators, original and repaired LaTeX, initial and candidate validation results, PDF page and bbox/crop, local context, model, confidence, timestamps, repair status, and applied version. The `(paper_key, source_version_id, input_hash)` uniqueness key makes repeated runs idempotent.

### Frontend Admin Console

Existing integration point:

```ts
fetchAdminData<Record<string, any>>(
  'airesearch.admin.paper.layout.detail',
  token,
  { paperKey }
)
```

Expected display:

- Evidence preflight: `capabilities`
- Metrics: `summary`
- Latest job: `latest_job`
- Current selected visual: `representative_visual`
- Evidence inspector tabs: `evidence_blocks`, `sample_blocks`, `summary.ocr`, `summary.formula_ocr`, `summary.reading_order`, `representative_visual`, and `visual_candidates`
- Artifact dialog: `artifacts`

Paper-management list integration:

```ts
fetchAdminData<Record<string, any>>('airesearch.admin.state', token)
```

Expected display:

- Compact status: `paper.layout_status`
- Coverage badges: `paper.layout_evidence_ready_blocks`, `paper.layout_captioned_visual_blocks`, `paper.layout_structured_table_blocks`, `paper.layout_equation_blocks`
- Detail entry point: open the selected paper and call `airesearch.admin.paper.layout.detail`

## Current MinerU-Inspired Coverage

Implemented:

- Versioned layout artifacts.
- Page/block coordinates.
- Content list JSON.
- Structure JSON.
- Markdown export.
- Asset extraction.
- Caption pairing for figures/tables.
- Coarse table row extraction from text blocks.
- Coarse equation detection and equation ids.
- Evidence-ready block metadata.
- Representative visual selection and PDF figure crop fallback.
- Per-page `digital` / `scanned` / `mixed` classification.
- Native Tesseract OCR fallback for scanned and mixed pages, with English and Simplified Chinese language data.
- OCR bbox, confidence, engine, language, page-count, and block-count provenance.
- Formula bbox crop assets and a configurable vision-provider formula-to-LaTeX pipeline with confidence gating and provenance. Production derives the OpenCode Go Responses endpoint from `OPENCODE_GO_BASE_URL`, uses `gpt-5.6-luna`, and routes through `OPENCODE_GO_PROXY=http://127.0.0.1:7890`; the one API key is `OPENCODE_GO_API_KEY` in the ignored `airesearch/.env`. In `auto` mode, local rules remain primary and API OCR is limited to eligible scanned-formula crops.
- Public formula evidence prefers complete artifact-ledger formulas from `equations.md`: `layout_evidence.summary.canonical_equation_count` reports the valid source count, and each selected source formula has `source_kind="paperpipe_equations"`, `equation_id="equation-<n>"`, `source_reference`, `latex`, and `quality_score=1.0`. PDF layout formula blocks are a fallback only when no valid canonical formula exists. Multiline fenced LaTeX is stored as one equation, duplicate artifact paths are deduplicated per paper, polluted full-document fences are reduced to complete display-math environments, and explicit missing-source placeholders are omitted.
- `gpt-5.6-luna` is not a universal formula/table source of truth. Existing source LaTeX and geometry-derived table cells remain authoritative. Model generation is appropriate for missing/scanned/low-confidence candidates only, and any future table candidate must return structured headers/rows/merged cells plus confidence/issues and pass schema and cell-value validation before publication.
- Geometry-based reading-order reconstruction for common two-column papers, cross-column anchors, and figure/table caption groups.
- Geometry-backed complex table reconstruction for borderless, ruled, Booktabs, tall, and stacked-subtable layouts, including sparse cells, multi-row headers, inferred column spans, overlap deduplication, and collapsed-prose rejection.

Not implemented yet:

- An operational local formula OCR model; production currently uses OpenCode Go `gpt-5.6-luna` instead of a local model.
- Advanced OCR for rotated, handwritten, very low-resolution, or unusually multilingual documents.
- Reliable arbitrary row-span recovery and arbitrary nested table semantics.
- Perfect semantic ordering for unusually complex floating layouts beyond the geometry-based page pass.
- Full document explorer/wiki/backlink engine.
- Vector search over layout blocks.
- Model-versioned OCR/layout model registry.
