# Stage 3K Semantic Threshold Calibration Design

## Goal

Add a semantic cluster threshold calibration report so AIResearch can compare multiple cosine thresholds before choosing the default semantic clustering setting.

## Scope

Stage 3K adds a CLI command that evaluates semantic clustering over a threshold grid. It reuses the configured OpenAI-compatible embedding provider and requests embeddings once for the corpus, then applies the same vectors to each threshold. The report is diagnostic only; it does not change the default report bundle threshold.

Stage 3K also creates `DEVELOPMENT.md` as the ongoing developer document for future feature work.

## Architecture

- `research_clusters.py` exposes a reusable semantic clustering helper that accepts precomputed embeddings.
- `research_cluster_calibration.py` builds Markdown/JSON threshold reports.
- `cli.py` adds `calibrate-research-clusters --threshold ... --out --format`.
- `DEVELOPMENT.md` records workflow, environment variables, verification commands, and feature log expectations.

## Testing

Tests cover threshold sorting, embedding reuse, JSON/Markdown output, and CLI success with a monkeypatched provider. Real endpoint verification is run manually with `source ./activate.sh`.
