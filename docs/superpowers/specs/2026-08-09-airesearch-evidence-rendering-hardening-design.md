# AIResearch Evidence Rendering Hardening Design

## Context

Native layout v2 has completed runs for all 209 papers and the public paper API already exports formula, table, OCR, and layout evidence. The public paper detail page currently exposes those fields, but formulas are rendered as raw text and tables are rendered as Markdown source. That is useful for debugging, not for reading a paper.

## Goal

Make the existing layout evidence readable and trustworthy on every public paper detail page without adding a runtime service or exposing unsafe parser HTML.

## Chosen Approach

Keep the static `paper-layout-evidence.json` contract and extend each bounded table payload with normalized rows and display-quality metadata. Render those rows into escaped semantic HTML tables, render formula LaTeX through the MathJax instance already loaded by paper pages, and preserve a compact raw-source fallback for malformed evidence.

This is preferred over two alternatives:

- Keeping raw Markdown/code blocks would preserve the current API but would not solve readability.
- Building a full PDF document viewer would add page rendering, zoom, synchronization, and runtime asset delivery well beyond the current evidence-panel scope.

## Data Contract

Each exported table may include:

- `table_rows`: at most 12 rows and 8 columns, with every cell collapsed and length-bounded.
- `display_quality`: `good`, `review`, or `fallback`, derived from structure, reconstruction confidence, and whether a real row/column shape is present.
- Existing provenance fields such as `page`, `block_id`, `source_reference`, `quality_score`, and `reconstruction_method` remain unchanged.

The exporter never emits parser-provided `table_html`. Public HTML is generated only from escaped normalized cells.

## Public Rendering

- Formula cards show a typeset display formula, source page, role, quality indicator, and a collapsible raw representation.
- Structured table cards show caption, dimensions, reconstruction method, quality indicator, and a horizontally scrollable semantic table.
- Table evidence without usable rows falls back to escaped Markdown/text and is visibly marked for review.
- Experiment evidence continues to combine benchmark/dataset facts with result-table captions. Its table references point readers to the structured table panel below.
- MathJax typesets both deep-reading prose and layout evidence after DOM readiness.

## Error Handling

- Empty, non-list, or malformed table rows are ignored.
- Oversized tables are truncated deterministically and labelled as previews.
- Empty formulas or tables keep the existing empty state.
- MathJax loading failure leaves readable escaped LaTeX in place.

## Testing And Acceptance

- Bundle tests assert bounded `table_rows` and display-quality metadata.
- Site tests assert semantic table markup, escaped cells, formula MathJax delimiters, raw fallback, and public API parity.
- Existing parser, blog, workflow, platform, frontend build, and admin smoke suites must remain green.
- Headless Chromium verifies desktop and mobile geometry, overflow, image loading, evidence controls, and admin inspector interaction. Screenshot capture is optional when the host browser supports it.
- Rebuild and deploy all static paper pages only after tests pass.

## Scope Boundary

This iteration does not add vector search, a graph database, a local formula model, or a PDF viewer. It improves the delivery of already-generated evidence and leaves parser/debug details in the admin inspector.
