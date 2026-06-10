# Stage 3I Semantic Research Clusters Design

## Goal

Add optional embedding-based semantic clustering to the existing Stage 3H research cluster report while preserving the current deterministic token/Jaccard clustering as the default offline path.

## Scope

Stage 3I adds a second clustering mode named `semantic`. It clusters facts within the same `fact_type` using cosine similarity over embeddings of `fact.name + fact.statement`. The default `token` mode remains unchanged, so report bundles and existing CLI calls keep their current behavior unless the caller opts into semantic clustering.

This stage does not add live cloud embedding calls. The embedding provider is an injected Python interface so tests and future API providers can use the same clustering path without network dependency.

## Architecture

- `research_clusters.py` owns both clustering modes.
- `build_research_clusters(db_path, mode="token", embedding_provider=None, semantic_threshold=0.82)` loads the existing digest and dispatches to token or semantic clustering.
- Semantic clustering uses deterministic greedy assignment within each fact type. A fact joins the cluster with the highest cosine similarity to that cluster centroid when the score is at least the threshold.
- The report carries `mode` and `semantic_threshold` metadata. Markdown and JSON exports expose these fields.
- CLI adds `--mode token|semantic` and `--semantic-threshold`. Semantic mode requires a provider when called from Python; the CLI returns a clear error until a live embedding provider is added.
- Report bundle stays on default token mode for now.

## Error Handling

- Unknown modes raise `ValueError`.
- Semantic mode without an embedding provider raises `SemanticClusteringError`.
- Invalid thresholds outside `[0.0, 1.0]` raise `ValueError`.
- Empty or zero-length embeddings are treated as unusable and receive zero similarity.

## Testing

Tests cover:

- Default token mode remains backward compatible.
- Semantic mode clusters lexically different but embedding-similar facts with a fixture provider.
- Semantic mode rejects missing providers and invalid thresholds.
- Markdown and JSON include mode metadata.
- CLI accepts the new flags and surfaces the missing-provider semantic error with exit code `2`.
