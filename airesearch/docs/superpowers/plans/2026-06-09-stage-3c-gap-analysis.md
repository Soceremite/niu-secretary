# Stage 3C Gap Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic L3 gap analysis report for AIResearch coverage and missing evidence.

**Architecture:** Add one new report module that reuses `build_research_digest()` and exports Markdown/JSON. Add one CLI command and narrow tests matching the existing Research Digest and Research Map patterns.

**Tech Stack:** Python dataclasses, SQLite-backed AIResearch digest objects, pytest, argparse CLI.

---

## File Structure

- Create: `airesearch/src/airesearch/research_gap_analysis.py`
  - Builds gap analysis objects from `ResearchDigest`, renders Markdown, serializes JSON, writes export files.
- Modify: `airesearch/src/airesearch/cli.py`
  - Imports `export_gap_analysis`, adds `generate-gap-analysis`, handles `DigestInputError`.
- Create: `airesearch/tests/test_research_gap_analysis.py`
  - Focused module tests for build, render, JSON export, and empty input.
- Modify: `airesearch/tests/test_cli.py`
  - CLI coverage for Markdown/JSON export and empty input.
- Modify: `airesearch/PLAN.md`
  - Update L3 status and Stage 3C completion notes after verification.

## Tasks

### Task 1: Add Gap Analysis Module

- [x] Create `airesearch/src/airesearch/research_gap_analysis.py`.
- [x] Define dataclasses:
  - `FactTypeCoverage`
  - `PaperGap`
  - `GapAnalysis`
- [x] Implement `build_gap_analysis(db_path: Path) -> GapAnalysis` by calling `build_research_digest(db_path)`.
- [x] Implement `render_markdown(analysis: GapAnalysis) -> str`.
- [x] Implement `gap_analysis_to_dict(analysis: GapAnalysis) -> dict[str, Any]`.
- [x] Implement `export_gap_analysis(db_path: Path, out_path: Path, *, output_format: str = "markdown") -> GapAnalysis`.

### Task 2: Add Module Tests

- [x] Create `airesearch/tests/test_research_gap_analysis.py`.
- [x] Reuse the existing fixture setup pattern from `test_research_map.py`.
- [x] Assert the fixture paper has `method=1`, `claim=1`, and missing `dataset`, `benchmark`, `limitation`.
- [x] Assert Markdown includes `# AIResearch Gap Analysis`, low coverage, missing types, and evidence source path summary.
- [x] Assert JSON export contains expected top-level counts and paper gaps.
- [x] Assert empty paper cards raises `DigestInputError`.

### Task 3: Add CLI Command

- [x] Import `export_gap_analysis` in `airesearch/src/airesearch/cli.py`.
- [x] Add `generate-gap-analysis` parser with `--out` and `--format markdown|json`.
- [x] Add command handler that prints:

```text
gap_analysis_exported={papers} facts={facts} missing_papers={missing_papers} format={format} out={out}
```

- [x] Return code `2` on `DigestInputError`.

### Task 4: Add CLI Tests

- [x] Add `test_cli_generate_gap_analysis_markdown_and_json`.
- [x] Add `test_cli_generate_gap_analysis_requires_paper_cards`.
- [x] Run:

```bash
.venv/bin/pytest tests/test_research_gap_analysis.py tests/test_cli.py -q
```

Expected: all selected tests pass.

### Task 5: Verify Real Corpus And Update Plan

- [x] Run the full suite:

```bash
.venv/bin/pytest -q
```

- [x] Generate real exports:

```bash
.venv/bin/python -m airesearch.cli generate-gap-analysis --out exports/research-gap-analysis-current.md
.venv/bin/python -m airesearch.cli generate-gap-analysis --format json --out exports/research-gap-analysis-current.json
```

- [x] Validate JSON:

```bash
python3 -m json.tool airesearch/exports/research-gap-analysis-current.json
```

- [x] Update `airesearch/PLAN.md` with Stage 3C status, real export paths, real counts, and full-suite result.
