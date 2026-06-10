# Stage 3J Live Semantic Clusters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make semantic research clustering work from CLI with the configured OpenAI-compatible embedding provider.

**Architecture:** Add a focused `embeddings.py` provider module and instantiate it only for `generate-research-clusters --mode semantic`. Keep report bundle defaults unchanged.

**Tech Stack:** Python urllib, dataclasses, argparse, pytest monkeypatch fixtures.

---

## File Map

- Create: `airesearch/src/airesearch/embeddings.py` for OpenAI-compatible embedding calls.
- Create: `airesearch/tests/test_embeddings.py` for provider request and response validation.
- Modify: `airesearch/src/airesearch/cli.py` to instantiate the provider for semantic mode.
- Modify: `airesearch/tests/test_cli.py` for semantic CLI success and missing-env errors.
- Modify: `airesearch/PLAN.md` after verification.

## Tasks

### Task 1: Add OpenAI-Compatible Embedding Provider

- [x] Implement `OpenAICompatibleEmbeddingProvider.from_env()`.
- [x] Implement batched `/embeddings` request with `encoding_format=float`.
- [x] Validate response shape, ordering, numeric vectors, and count.

### Task 2: Wire CLI Semantic Mode

- [x] Instantiate the provider only when `--mode semantic`.
- [x] Pass the provider into `export_research_clusters()`.
- [x] Return exit code `2` for provider configuration or request errors.

### Task 3: Verify

- [x] Add no-network provider tests.
- [x] Add CLI semantic success and missing-env tests.
- [x] Run full test suite.
- [x] Run a real semantic export using sourced local environment.
- [x] Update `PLAN.md` with counts and verification.
