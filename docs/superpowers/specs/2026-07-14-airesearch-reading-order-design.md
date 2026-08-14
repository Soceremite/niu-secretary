# AIResearch Reading Order Reconstruction Design

## Goal

Add a native MinerU-inspired reading-order pass to layout v2 so deep reading, table/formula evidence, and Markdown exports use a more natural order on common two-column research PDFs.

## Scope

The implementation stays inside the existing native PyMuPDF parser. It does not install MinerU and does not introduce a model dependency.

The first production scope handles:

- Left/right column ordering within a page segment.
- Cross-column anchors such as titles, wide figures, wide tables, and display equations.
- Figure/table caption pairing so visual blocks and captions remain adjacent.
- Auditable metadata on every block.
- Summary/capability fields for admin UI and blog evidence preflight.

Out of scope:

- Perfect semantic ordering for arbitrary floating layouts.
- Arbitrary row-span recovery in tables.
- Vector retrieval over layout blocks.

## Data Contract

Each layout block may include:

- `metadata.reading_order_method = "geometry_columns_v2"`
- `metadata.reading_order_index`
- `metadata.reading_order_region`: `left_column`, `right_column`, `full_width`, or `unknown`
- `metadata.reading_order_column`: `0`, `1`, or null
- `metadata.reading_order_confidence`
- `metadata.reading_order_reasons`

The layout summary includes:

- `summary.reading_order.method`
- `summary.reading_order.pages_completed`
- `summary.reading_order.multi_column_pages`
- `summary.reading_order.cross_column_blocks`
- `summary.reading_order.caption_paired_blocks`
- `summary.reading_order.low_confidence_blocks`
- `summary.reading_order.average_confidence`

Capabilities include:

- `has_reading_order`
- `has_multi_column_reading_order`
- `has_caption_paired_reading_order`
- `needs_reading_order_attention`

## Algorithm

1. Remove repeated headers, footers, and page numbers as before.
2. Enrich blocks with caption evidence and visual/table caption links.
3. Group each visual/table block with its linked caption when available.
4. Classify groups as `full_width`, `left_column`, or `right_column` from bbox geometry.
5. Use full-width groups as page segment anchors.
6. Within each segment, emit left-column groups top-to-bottom, then right-column groups top-to-bottom.
7. Emit full-width anchors between segments.
8. Assign final `block_index` and reading-order metadata.

## UI

The admin paper list shows multi-column coverage and low-confidence reading-order warnings. The layout detail and blog evidence preflight show multi-column pages, cross-column blocks, caption groups, and low-confidence block counts.

## Testing

Tests cover:

- Cross-column blocks splitting a two-column page into segments.
- Caption groups remaining adjacent to visual blocks.
- Parser summary metadata and layout detail capabilities.
- Existing OCR/table/formula layout regressions.
