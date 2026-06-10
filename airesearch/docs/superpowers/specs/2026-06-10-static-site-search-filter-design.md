# Static Site Search And Filter Design

## Goal

Add a lightweight static search and filter layer to the generated AIResearch report site so larger paper batches remain browsable without adding a server.

## Scope

The report site generator will create a `search-index.json` file next to `index.html`. The index will contain one entry per report artifact with stable fields for name, title, markdown path, JSON path, type, text snippet, and keyword text. The generated HTML will include a search input, a type filter, a result count, and report sections tagged with searchable metadata.

## Architecture

`research_site.py` remains the only implementation module. It already owns static site rendering from a bundle manifest, so it will also own index construction and HTML controls. The frontend filtering logic will be plain inline JavaScript that fetches `search-index.json`, applies case-insensitive substring matching, filters sections by `data-report-type`, and keeps the navigation links in sync.

## Data Flow

1. Load `manifest.json` from the bundle directory.
2. Read each artifact Markdown file when present.
3. Build a compact search entry from artifact metadata and a normalized Markdown snippet.
4. Export `search-index.json` and `index.html`.
5. In the browser, load the index and filter the already-rendered sections and navigation links.

## Error Handling

Missing Markdown files keep the existing behavior: the rendered report shows a missing artifact message. The search index still includes a searchable entry for that artifact using its manifest metadata and missing-file message. Malformed manifest structure continues to raise `ValueError`.

## Testing

Tests cover index generation, HTML controls, tagged sections and nav links, exported `search-index.json`, and report counts. The implementation is intentionally static-only so existing `serve-report-site` and `publish-static-site` flows continue to work.
