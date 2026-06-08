# Stage 2D L2 Paper Card And Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic paper card and provenance graph extraction for already-ingested paperpipe papers.

**Architecture:** Extend the existing SQLite ledger with L2 extraction tables, then add a focused `knowledge_graph.py` module that reads `papers` and `paper_artifacts` and writes idempotent paper cards, graph nodes, graph edges, and provenance. Wire the module through CLI commands for extraction, listing, and JSONL export.

**Tech Stack:** Python, SQLite, argparse, pytest.

---

## File Map

- Modify: `src/airesearch/schema.sql` - add L2 extraction and graph tables.
- Create: `src/airesearch/knowledge_graph.py` - deterministic extraction, list, export functions.
- Modify: `src/airesearch/cli.py` - add L2 CLI commands and status counts.
- Create: `tests/test_knowledge_graph.py` - module tests.
- Modify: `tests/test_cli.py` - CLI coverage for L2 commands.
- Modify: `PLAN.md` - mark Stage 2D.0 progress.

## Tasks

### Task 1: Schema And Module Tests

- [ ] Add tests that initialize a fixture DB, sync paperpipe fixture data, run paper card extraction, and assert one paper card, graph nodes, graph edges, and provenance records exist.
- [ ] Add idempotency test that runs extraction twice and asserts counts remain stable.
- [ ] Add export test that writes JSONL with one object per paper card.

### Task 2: L2 Schema

- [ ] Add `extraction_runs`, `paper_cards`, `kg_nodes`, `kg_edges`, and `kg_provenance` tables to `schema.sql`.
- [ ] Add indexes for paper card score/order, graph node type, edge relation, and provenance source.

### Task 3: Deterministic Extractor

- [ ] Implement `extract_paper_cards(db_path, limit=None, paper_key=None)`.
- [ ] Implement stable node key generation and JSON parsing helpers.
- [ ] Replace prior deterministic graph rows for a paper before writing refreshed rows.
- [ ] Record successful and failed extraction runs.

### Task 4: CLI

- [ ] Add `extract-paper-cards`, `list-paper-cards`, and `export-paper-cards` commands.
- [ ] Add paper card/node/edge counts to `status`.
- [ ] Add CLI tests for extraction and export.

### Task 5: Verification And Commit

- [ ] Run focused tests.
- [ ] Run full pytest.
- [ ] Run extraction on the real local DB.
- [ ] Update `PLAN.md`.
- [ ] Commit the implementation.
