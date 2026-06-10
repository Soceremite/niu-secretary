# Stage 3J Live Semantic Clusters Design

## Goal

Wire the Stage 3I semantic clustering substrate to the existing `.env` / `activate.sh` embedding configuration so `generate-research-clusters --mode semantic` can use the configured OpenAI-compatible embedding endpoint.

## Scope

Stage 3J adds a live embedding provider for semantic clustering. It reads `AIRESEARCH_EMBEDDING_MODEL`, `AIRESEARCH_EMBEDDING_BASE_URL`, and `AIRESEARCH_EMBEDDING_API_KEY`, with fallback to compatible OpenAI environment variable names. The existing token mode remains the default for report bundles.

## Architecture

- `embeddings.py` owns the OpenAI-compatible `/embeddings` request and response validation.
- `cli.py` creates `OpenAICompatibleEmbeddingProvider.from_env()` only when `--mode semantic` is selected.
- `research_clusters.py` continues to receive an injected provider and does not read environment variables directly.
- Embeddings are requested in one batch for the current fact list.

## Error Handling

- Missing model or API key returns a clear CLI error with exit code `2`.
- Provider HTTP or network failures are wrapped as `EmbeddingProviderError`.
- Malformed provider responses fail before writing output.

## Testing

Tests use fake URL openers and monkeypatched providers. No test calls the real embedding endpoint.
