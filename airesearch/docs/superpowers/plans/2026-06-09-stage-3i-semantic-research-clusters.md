# Stage 3I Semantic Research Clusters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional embedding-based semantic clustering to Stage 3 research clusters without changing default report behavior.

**Architecture:** Extend `research_clusters.py` with a provider-injected semantic clustering mode and keep the existing token/Jaccard path as `mode="token"`. Expose the mode metadata in Markdown/JSON and add CLI flags that validate semantic mode cleanly until a live embedding provider exists.

**Tech Stack:** Python dataclasses, injected embedding provider protocol, cosine similarity, argparse, pytest.

---

## File Map

- Modify: `airesearch/src/airesearch/research_clusters.py` for semantic clustering mode, metadata, validation, rendering, and export parameters.
- Modify: `airesearch/src/airesearch/cli.py` for `generate-research-clusters --mode --semantic-threshold`.
- Modify: `airesearch/tests/test_research_clusters.py` for semantic clustering unit tests.
- Modify: `airesearch/tests/test_cli.py` for CLI flag/error coverage.
- Modify: `airesearch/PLAN.md` to record Stage 3I completion after verification.

## Tasks

### Task 1: Add Semantic Clustering Core

- [x] Add `SemanticClusteringError`, embedding provider protocol, cosine similarity, and semantic draft structures.
- [x] Extend `ResearchClusters` with `mode` and `semantic_threshold`.
- [x] Implement `_cluster_facts_semantic()` using greedy same-fact-type centroid assignment.
- [x] Dispatch from `build_research_clusters()` based on `mode`.

### Task 2: Update Exports

- [x] Include `mode` and `semantic_threshold` in Markdown headers.
- [x] Include `mode` and `semantic_threshold` in JSON payloads.
- [x] Add optional `mode`, `embedding_provider`, and `semantic_threshold` parameters to `export_research_clusters()`.

### Task 3: Add CLI Coverage

- [x] Add `--mode token|semantic` and `--semantic-threshold` to `generate-research-clusters`.
- [x] Return exit code `2` with a clear message for semantic mode without a provider.
- [x] Keep token mode output unchanged except for metadata lines.

### Task 4: Verify

- [x] Run focused research cluster and CLI tests.
- [x] Run full airesearch test suite.
- [x] Regenerate token-mode cluster exports and bundle from the real DB.
- [x] Update `PLAN.md` with counts and test results.
