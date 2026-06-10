# Stage 3B Research Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a deterministic cross-paper Research Map report from audited L2 paper cards and research facts.

**Architecture:** Add a focused `research_map.py` reporting module that reuses `build_research_digest()` for all database loading. The module groups facts by fact type and normalized label, renders Markdown/JSON, and exposes one export function used by a new CLI command.

**Tech Stack:** Python dataclasses, SQLite-backed existing AIResearch helpers, pytest, argparse CLI.

---

## File Structure

- Create: `airesearch/src/airesearch/research_map.py`
  - Owns map dataclasses, deterministic grouping, Markdown rendering, JSON serialization, and export.
- Create: `airesearch/tests/test_research_map.py`
  - Owns focused module tests for grouping, rendering, export, and empty input.
- Modify: `airesearch/src/airesearch/cli.py`
  - Adds `generate-research-map` parser and handler.
- Modify: `airesearch/tests/test_cli.py`
  - Adds CLI coverage for Markdown/JSON export and empty input.
- Modify: `airesearch/PLAN.md`
  - Records Stage 3B status and real export counts after verification.

## Task 1: Research Map Module

**Files:**
- Create: `airesearch/src/airesearch/research_map.py`
- Test: `airesearch/tests/test_research_map.py`

- [x] **Step 1: Write module tests**

Create tests that build a fixture DB with `sync_paperpipe`, `extract_paper_cards`, and fixture `extract_research_facts`. Assert:

```python
research_map.paper_count == 1
research_map.fact_count == 2
research_map.item_count == 2
research_map.fact_type_counts == {"method": 1, "claim": 1}
research_map.sections["method"][0].label == "Transformer attention architecture"
```

- [x] **Step 2: Implement dataclasses and grouping**

Define:

```python
@dataclass(frozen=True)
class MapEvidence: ...

@dataclass(frozen=True)
class MapPaperRef: ...

@dataclass(frozen=True)
class ResearchMapItem: ...

@dataclass(frozen=True)
class ResearchMap: ...
```

Implement `build_research_map(db_path: Path) -> ResearchMap` by iterating through `build_research_digest(db_path).papers`.

- [x] **Step 3: Implement Markdown and JSON export**

Implement:

```python
render_markdown(research_map: ResearchMap) -> str
research_map_to_dict(research_map: ResearchMap) -> dict[str, Any]
export_research_map(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> ResearchMap
```

- [x] **Step 4: Run focused module tests**

Run:

```bash
.venv/bin/pytest tests/test_research_map.py -q
```

Expected: all tests pass.

## Task 2: CLI Integration

**Files:**
- Modify: `airesearch/src/airesearch/cli.py`
- Modify: `airesearch/tests/test_cli.py`

- [x] **Step 1: Add CLI tests**

Add tests that call:

```python
main(["--db", str(db_path), "generate-research-map", "--out", str(markdown_path)])
main(["--db", str(db_path), "generate-research-map", "--format", "json", "--out", str(json_path)])
```

Assert output includes `research_map_exported=1 facts=2 items=2 format=markdown` and JSON has `item_count == 2`.

- [x] **Step 2: Add parser and handler**

Add parser:

```python
research_map = subparsers.add_parser("generate-research-map")
research_map.add_argument("--out", type=Path, required=True)
research_map.add_argument("--format", choices=["markdown", "json"], default="markdown")
```

Add handler that catches `DigestInputError` and returns `2`, matching `generate-research-digest`.

- [x] **Step 3: Run CLI tests**

Run:

```bash
.venv/bin/pytest tests/test_research_map.py tests/test_cli.py -q
```

Expected: all tests pass.

## Task 3: Real Export And Status Update

**Files:**
- Create: `airesearch/exports/research-map-current.md`
- Create: `airesearch/exports/research-map-current.json`
- Modify: `airesearch/PLAN.md`

- [x] **Step 1: Run full suite**

Run:

```bash
.venv/bin/pytest -q
```

Expected: all tests pass.

- [x] **Step 2: Generate real exports**

Run:

```bash
.venv/bin/python -m airesearch.cli generate-research-map --out exports/research-map-current.md
.venv/bin/python -m airesearch.cli generate-research-map --format json --out exports/research-map-current.json
```

Expected: command output includes 11 papers and 79 facts.

- [x] **Step 3: Validate JSON and preview Markdown**

Run:

```bash
python3 -m json.tool airesearch/exports/research-map-current.json
sed -n '1,100p' airesearch/exports/research-map-current.md
```

Expected: JSON parses and Markdown contains `# AIResearch Research Map`.

- [x] **Step 4: Update tracker**

Update `airesearch/PLAN.md` to mark Stage 3B Research Map complete, including real export paths, paper count, fact count, item count, and full test result.
