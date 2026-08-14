# AIResearch Layout V2 And Knowledge Design

## Context

AIResearch should not install, invoke, or expose MinerU as an external parser. The useful reference points are product and data-design patterns:

- MinerU core is a document parsing engine. The useful patterns are versioned structured layout artifacts, page/block coordinates, content lists, assets, and separate debug outputs.
- MinerU Document Explorer is a separate knowledge engine. The useful patterns are collection-based indexing, SQLite-backed BM25 search, optional vector search, provenance-aware wiki pages, wikilinks, backlink inspection, and linting for stale or broken knowledge.

## Layout V2 Scope

Build on the current native PyMuPDF parser and keep the same parse entry points:

- `parse-layout`
- `parse-missing-layouts`
- `airesearch.admin.paper.layout.generate`
- `airesearch.admin.paper.layout.detail`

The parser should add richer metadata without requiring new services:

- `layout_summary_json`: compact run summary for API and frontend status.
- Image caption pairing: associate visual blocks with nearby `Figure`, `Fig.`, `Table`, or Chinese `图/表` captions on the same page.
- Structured table rows: convert whitespace-aligned table text into `table_rows`, `column_count`, and `row_count` metadata.
- Equation metadata: assign stable per-run equation ids, source references, and coarse roles such as `loss`, `attention`, `optimization`, or `math`.
- Evidence readiness: mark blocks that are useful for deep-reading evidence with `evidence_kind` and confidence values.

## Database And Knowledge Direction

Keep AIResearch on SQLite. Do not add a graph database in this step.

Future knowledge upgrades should use existing AIResearch data first:

- Raw layer: `papers`, `paper_artifacts`, layout artifacts, facts, claims, relations.
- Search layer: SQLite FTS5 tables for paper cards, facts, layout text, and blog/wiki pages.
- Optional semantic layer: local `embeddings` tables or sqlite-vec if the deployment explicitly enables vector search later.
- Graph layer: ordinary SQLite edge tables, not Neo4j, for `paper -> fact`, `paper -> paper`, `paper -> concept`, `blog/wiki -> source`, and `concept -> concept` links.
- Wiki layer: Markdown pages with `[[wikilinks]]`, source provenance, stale-source checks, and backlink queries.

## Design Rules

- Keep parser outputs versioned with `parser`, `parser_version`, and artifact type names.
- Store every derived block with page index, block index, bbox, text, asset path, source artifact path, and metadata.
- Avoid absolute paths in frontend responses when a relative paper asset path exists.
- Preserve existing paper ingestion and deep-reading APIs.
- Treat vector search and LLM reranking as optional future enhancements, not required for baseline operation.
- Add tests at parser, persistence, CLI/API, blog evidence, and frontend build/smoke levels for every new artifact type.
