# Stage 2D.3 Code Links In Paper Cards And Graph Design

## Goal

Promote extracted GitHub project links from the side table into first-class L2 outputs so each paper card and graph can expose implementation repositories.

## Context

Stage 2D.2 stores deterministic GitHub links in `paper_code_links` by scanning paper metadata and TeX source artifacts. Those rows are useful through dedicated CLI commands, but Paper Card exports and the knowledge graph do not yet include them. That means later report generation would need to know about a separate table instead of consuming the normal L2 paper representation.

## Scope

This stage only integrates existing `paper_code_links` rows. It does not re-scan abstracts or TeX, call external services, validate repository existence, or infer non-GitHub project pages.

## Design

`extract-paper-cards` will load code links for each paper after loading artifacts. For every code link, it will:

- Add a `code_repository` node keyed as `code_repository:<host>:<owner>:<repo>`.
- Add a `has_code_repository` edge from `paper:<paper_key>` to that repository node.
- Add provenance for both node and edge pointing back to the `paper_code_links` row.

`export-paper-cards` will add a `code_links` array to each exported paper card. Each item will include the normalized URL, host, owner, repo, source type, and source path.

The database schema does not need new tables. Existing graph tables already support the new node and edge types.

## Data Flow

1. Run `extract-code-links` to populate `paper_code_links`.
2. Run `extract-paper-cards`.
3. Paper card export includes `code_links`.
4. KG queries can traverse `paper -> has_code_repository -> code_repository`.

If `extract-paper-cards` runs before `extract-code-links`, the paper card remains valid and simply exports an empty `code_links` list. Re-running `extract-paper-cards` after code-link extraction refreshes deterministic graph rows for that paper.

## Error Handling

Missing or malformed code-link rows are skipped only if required fields are empty. Existing paper-card extraction behavior remains idempotent: graph rows created by the deterministic paper-card extractor for a paper are cleared and rebuilt on each run.

## Testing

Tests will cover:

- Paper-card export includes `code_links`.
- KG extraction creates `code_repository` nodes and `has_code_repository` edges.
- Papers without code links export `code_links: []`.
- Existing card extraction remains idempotent.
