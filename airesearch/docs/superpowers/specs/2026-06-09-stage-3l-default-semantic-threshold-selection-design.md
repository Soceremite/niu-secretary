# Stage 3L Default Semantic Threshold Selection Design

## Goal

Add a deterministic recommendation to the semantic cluster calibration report so AIResearch can justify the default semantic threshold from measured corpus behavior.

## Scope

Stage 3L extends the Stage 3K calibration report. It does not change `SEMANTIC_CLUSTER_THRESHOLD`; it adds a recommended threshold, policy metadata, and rationale to Markdown/JSON exports.

## Selection Policy

Prefer the highest threshold that satisfies all conservative quality gates:

- `cluster_count >= 3`
- `clustered_fact_count >= 6`
- `largest_cluster_size <= 3`

If no threshold satisfies all gates, choose the point with the highest deterministic score:

```text
clustered_fact_count + cluster_count + clustered_paper_count - largest_cluster_size
```

This keeps recommendations explainable and avoids over-clustering when lower thresholds produce broad clusters.

## Testing

Tests cover normal recommendation, fallback recommendation, Markdown/JSON serialization, and real CLI output shape with fake embeddings.
