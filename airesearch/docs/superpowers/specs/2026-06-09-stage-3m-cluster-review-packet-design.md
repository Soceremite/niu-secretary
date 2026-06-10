# Stage 3M Cluster Review Packet Design

## Context

Stage 3I-3L added semantic research clusters, live embedding provider wiring, threshold calibration, and deterministic default threshold recommendation. The next step is to make machine-generated clusters reviewable before downstream reports or graph enrichment treat them as curated research structure.

## Goal

Add a deterministic cluster review packet export that turns current research clusters into Markdown and JSON artifacts with explicit review fields, evidence facts, and conservative recommended statuses.

## Non-Goals

- Do not add a SQLite review table in this stage.
- Do not mutate research facts or clusters.
- Do not require an interactive editor.
- Do not change the existing `generate-research-clusters` output contract.

## Approach

Create a new `airesearch.research_cluster_review` module that builds on `build_research_clusters`. It will support both token and semantic modes using the same embedding provider interface as research clusters.

Each review item represents one multi-fact cluster and includes:

- `cluster_id`, `label`, `fact_type`, `token_signature`
- `paper_count`, `fact_count`, `average_confidence`
- `recommended_status`
- `review_status`, defaulting to `pending`
- `review_notes`, defaulting to an empty string
- deterministic rationale
- fact references with paper metadata, statements, confidence, and evidence source paths

Recommended statuses are intentionally simple:

- `accept_candidate`: at least two papers, at least two facts, and average confidence at least `0.85`
- `needs_review`: all other clusters

The export is designed for a human or future tool to edit `review_status` and `review_notes` outside this command. A later stage can ingest an edited packet into SQLite if the workflow proves useful.

## CLI

Add:

```bash
python -m airesearch.cli generate-cluster-review --mode semantic --out exports/research-cluster-review-current.md
python -m airesearch.cli generate-cluster-review --mode semantic --format json --out exports/research-cluster-review-current.json
```

Arguments:

- `--out`, required path
- `--format`, `markdown` or `json`, default `markdown`
- `--mode`, `token` or `semantic`, default `token`
- `--semantic-threshold`, default `0.82`

Semantic mode uses `OpenAICompatibleEmbeddingProvider.from_env()` just like `generate-research-clusters`.

## Data Flow

1. Load paper cards and research facts through `build_research_clusters`.
2. Convert each cluster to a review item.
3. Render Markdown or JSON.
4. Write to the requested path.
5. Print summary counts from the CLI.

## Error Handling

- Reuse `DigestInputError` when paper cards or facts are missing.
- Reuse `SemanticClusteringError`, `EmbeddingProviderError`, and `ValueError` for semantic provider or threshold failures.
- Reject unsupported output formats with `ValueError`.

## Testing

- Unit-test review packet construction from the existing fixture cluster DB.
- Unit-test JSON and Markdown render/export contracts.
- CLI-test token mode with the fixture pipeline.
- CLI-test semantic mode using a fake embedding provider.
- CLI-test missing paper cards returns exit code `2`.

## Documentation

Update:

- `PLAN.md` current status and Stage 3M completion notes
- `DEVELOPMENT.md` report commands, verification command, and feature log

