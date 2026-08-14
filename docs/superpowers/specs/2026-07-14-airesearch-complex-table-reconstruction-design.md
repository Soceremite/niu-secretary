# AIResearch Complex Table Reconstruction Design

## Goal

Extend native layout v2 so digital PDFs can produce cell-level table structure from word geometry while preserving the current text-spacing fallback and all existing API consumers.

## Scope

- Read PyMuPDF word tuples for each page and select words inside a detected table block.
- Cluster words into visual rows using vertical overlap and adaptive font-height tolerances.
- Split each row into cell segments using adaptive horizontal gaps.
- Infer stable columns from segment anchors observed across multiple rows.
- Preserve sparse cells as empty strings instead of shifting later values left.
- Mark wide cells with `col_span` when their geometry crosses inferred column bands.
- Infer one or more header rows from text/numeric patterns and spanning cells.
- Emit `table_cells`, `table_rows`, column boundaries, header row count, reconstruction method, confidence, and reasons.
- Continue emitting `table_markdown` and `table_html` for the blog evidence pipeline.

## Compatibility

`metadata.table_rows`, `table_markdown`, `table_html`, `row_count`, and `column_count` remain unchanged in meaning. New metadata is additive. If geometry cannot establish at least two rows and two columns, layout v2 uses the existing whitespace parser and marks the result as `text_fallback`.

## Quality Rules

Geometry confidence rewards repeated column support, multi-cell rows, useful occupancy, and stable alignment. It is reduced for one-off columns, very sparse matrices, and ambiguous anchors. Evidence scoring consumes this confidence but retains the existing `quality_score >= 0.72` high-quality threshold.

## Testing

- Pure coordinate tests cover uneven spacing, sparse cells, multi-line headers, and wide cells.
- A generated digital PDF verifies real PyMuPDF word tuples flow into structure JSON and Markdown.
- Existing layout, persistence, workflow, blog, API, CLI, and frontend tests remain green.

## Non-Goals

- No MinerU installation or invocation.
- No GPU table model.
- No claim of perfect merged-row or borderless-table recovery.
- No breaking database or frontend schema change.
