# Claim Trace CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only `claim-trace` command that traces one extracted research fact to paper metadata, evidence provenance, artifacts, code links, and KG relations.

**Architecture:** Add a focused `claim_trace.py` module that owns lookup, serialization, and rendering. Wire it into `cli.py` with narrow argparse options and nonzero not-found behavior. Keep schema unchanged and query only existing ledger tables.

**Tech Stack:** Python stdlib, SQLite through existing `airesearch.db.connect`, pytest, existing AIResearch CLI patterns.

---

### Task 1: Trace Module

**Files:**
- Create: `src/airesearch/claim_trace.py`
- Test: `tests/test_claim_trace.py`

- [ ] **Step 1: Write tests for exact trace, search trace, Markdown rendering, and not-found behavior**

Use the fixture paper DB, run `sync_paperpipe`, `extract_code_links`, `extract_paper_cards`, and fixture fact extraction. Assert the trace includes fact, paper, provenance, artifact, code link, graph relation, and graph provenance data.

- [ ] **Step 2: Implement `claim_trace.py` dataclasses and lookup helpers**

Define `ClaimTraceNotFound`, `parse_json`, `row_to_dict`, `find_fact_row`, `find_artifact`, `load_code_links`, `load_graph_relations`, `load_graph_provenance`, `trace_claim`, `trace_to_dict`, `render_claim_trace_markdown`, and `export_claim_trace`.

- [ ] **Step 3: Run focused trace tests**

Run:

```bash
source ./activate.sh && pytest -q tests/test_claim_trace.py
```

Expected: all claim trace tests pass.

### Task 2: CLI Wiring

**Files:**
- Modify: `src/airesearch/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add parser arguments**

Add `claim-trace` with `--fact-id`, `--paper-key`, `--type`, `--query`, `--format markdown|json`, and `--out`.

- [ ] **Step 2: Add command handler**

Call `export_claim_trace`; print to stdout when `--out` is omitted; print `claim_trace_exported out=<path>` when writing a file; return `2` for `ClaimTraceNotFound`.

- [ ] **Step 3: Add CLI tests**

Test stdout Markdown, JSON export, and not-found return code.

- [ ] **Step 4: Run CLI tests**

Run:

```bash
source ./activate.sh && pytest -q tests/test_cli.py
```

Expected: CLI tests pass.

### Task 3: Docs And Roadmap

**Files:**
- Modify: `PLAN.md`
- Modify: `DEVELOPMENT.md`

- [ ] **Step 1: Mark roadmap item complete**

Check off `Add claim-trace command to inspect one claim/fact back to paper, artifact, source path, and graph relations.`

- [ ] **Step 2: Update command inventory and feature notes**

Add `python -m airesearch.cli claim-trace --fact-id <id>` to the command list. Document what the command returns and that it is read-only.

### Task 4: Verification

**Files:**
- No source edits expected

- [ ] **Step 1: Run focused related tests**

Run:

```bash
source ./activate.sh && pytest -q tests/test_claim_trace.py tests/test_cli.py tests/test_fact_extraction.py tests/test_knowledge_graph.py
```

Expected: all pass.

- [ ] **Step 2: Run full suite**

Run:

```bash
source ./activate.sh && pytest -q
```

Expected: all pass.

- [ ] **Step 3: Check whitespace**

Run:

```bash
git diff --check -- src/airesearch/claim_trace.py src/airesearch/cli.py tests/test_claim_trace.py tests/test_cli.py PLAN.md DEVELOPMENT.md docs/superpowers/specs/2026-06-10-claim-trace-cli-design.md docs/superpowers/plans/2026-06-10-claim-trace-cli.md
```

Expected: no output.
