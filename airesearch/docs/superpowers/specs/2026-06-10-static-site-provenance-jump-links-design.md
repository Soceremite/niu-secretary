# Static Site Provenance Jump Links Design

## Goal

Add lightweight provenance jump links to generated AIResearch static report sites so readers can move from a report to the paper keys, evidence source paths, and code links behind the claims without running a backend.

## Scope

The report site generator will create a `provenance-index.json` file next to `index.html`. The index will contain one entry per extracted provenance reference from artifact JSON files. Entries include the report name and title, source JSON path, provenance type, paper key, evidence source path, code URL, and a compact label. The generated HTML will include a Provenance section with links back to the source report section and raw JSON artifact.

## Architecture

`research_site.py` remains the only implementation module. It already owns static site rendering and generated indexes, so it will also own provenance index construction. The index builder will recursively walk each artifact JSON object and extract recognized fields from dictionaries. The HTML renderer will render a small static provenance list and count, with no browser framework and no backend.

## Data Flow

1. Load `manifest.json` from the bundle directory.
2. For each artifact with a JSON path, parse the JSON when present and valid.
3. Recursively inspect dictionaries for `paper_key`, `evidence_source_path`, and `code_links` or direct `url` fields.
4. Emit deterministic, de-duplicated provenance entries.
5. Export `provenance-index.json` and render a Provenance section in `index.html`.

## Error Handling

Missing or malformed artifact JSON files are skipped for provenance extraction. The report HTML continues to render the raw Markdown sections as before. Empty provenance produces a zero-count message and an empty index file, preserving static-site generation.

## Testing

Tests cover recursive extraction from artifact JSON, deterministic de-duplication, generated HTML anchors and links, exported `provenance-index.json`, and updated artifact counts.
