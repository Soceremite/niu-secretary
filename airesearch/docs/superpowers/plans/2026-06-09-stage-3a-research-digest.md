# Stage 3A Research Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a deterministic L3 research digest generator that renders audited paper cards and research facts as Markdown or JSON.

**Architecture:** Create `research_digest.py` as a read-only report assembly and rendering module. It reads `paper_cards`, `paper_code_links`, `research_facts`, and `research_fact_provenance`, groups facts by type, and writes either Markdown or JSON through a new CLI command.

**Tech Stack:** Python, SQLite, argparse, pytest, existing AIResearch DB helpers and JSON parsing helpers.

---

### Task 1: Digest Module

**Files:**
- Create: `airesearch/src/airesearch/research_digest.py`
- Test: `airesearch/tests/test_research_digest.py`

- [x] **Step 1: Add tests for digest assembly and Markdown export**

Create `airesearch/tests/test_research_digest.py` with fixture DB setup that syncs paperpipe, extracts paper cards, and extracts fixture facts. Add assertions that the digest contains one paper, two facts, and grouped `method` / `claim` sections.

- [x] **Step 2: Implement data classes and loaders**

In `research_digest.py`, define `DigestInputError`, `DigestFact`, `DigestPaper`, and `ResearchDigest`. Implement `build_research_digest(db_path)` using `init_db`, `connect`, and existing `parse_json` / `code_link_payloads` helpers from `knowledge_graph.py`.

- [x] **Step 3: Implement renderers and export**

Add `render_markdown(digest)`, `digest_to_dict(digest)`, and `export_research_digest(db_path, out_path, output_format="markdown")`. Markdown should include a report title, generated summary, one paper section, metadata, grouped fact sections, confidence values, and evidence text.

- [x] **Step 4: Run focused tests**

Run:

```bash
.venv/bin/pytest tests/test_research_digest.py -q
```

Expected: all new digest tests pass.

### Task 2: CLI Integration

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Test: `airesearch/tests/test_cli.py`

- [x] **Step 1: Add CLI tests**

Add tests for:

- `generate-research-digest --out digest.md`
- `generate-research-digest --format json --out digest.json`
- failure with code `2` when no paper cards exist

- [x] **Step 2: Wire CLI command**

Import `DigestInputError` and `export_research_digest`. Add parser:

```python
digest = subparsers.add_parser("generate-research-digest")
digest.add_argument("--out", type=Path, required=True)
digest.add_argument("--format", choices=["markdown", "json"], default="markdown")
```

Handle the command in `main`:

```python
if args.command == "generate-research-digest":
    try:
        result = export_research_digest(args.db, args.out, output_format=args.format)
    except DigestInputError as exc:
        print(str(exc))
        return 2
    print(
        "research_digest_exported={papers} facts={facts} format={format} out={out}".format(
            papers=result.paper_count,
            facts=result.fact_count,
            format=args.format,
            out=args.out,
        )
    )
    return 0
```

- [x] **Step 3: Run CLI-focused tests**

Run:

```bash
.venv/bin/pytest tests/test_research_digest.py tests/test_cli.py -q
```

Expected: digest and CLI tests pass.

### Task 3: Real DB Verification And Project Status

**Files:**
- Modify: `airesearch/PLAN.md`
- Create: `airesearch/exports/research-digest-current.md`
- Create: `airesearch/exports/research-digest-current.json`

- [x] **Step 1: Generate real digest exports**

Run:

```bash
.venv/bin/python -m airesearch.cli generate-research-digest --out exports/research-digest-current.md
.venv/bin/python -m airesearch.cli generate-research-digest --format json --out exports/research-digest-current.json
```

Expected: both commands return `research_digest_exported=11 facts=79`.

- [x] **Step 2: Run full suite**

Run:

```bash
.venv/bin/pytest -q
```

Expected: full suite passes with no regressions.

- [x] **Step 3: Update `PLAN.md`**

Mark L3 reports as in progress with Stage 3A complete. Add the real export paths and test count to the In Progress section.

## Self-Review

- Spec coverage: The plan implements deterministic Markdown/JSON digest generation, CLI access, error handling for missing paper cards, and tests for module and CLI behavior.
- Placeholder scan: No `TBD`, `TODO`, or vague implementation placeholders remain.
- Type consistency: The plan uses `ResearchDigest.paper_count`, `ResearchDigest.fact_count`, and `output_format` consistently across module and CLI tasks.
