# Stage 3F Report Bundle Design

## Goal

Add one deterministic CLI command that exports the complete Stage 3 reporting set into a single directory, with a machine-readable manifest and a human-readable index.

## Context

Stages 3A through 3E already generate independent Markdown and JSON reports from audited L2 `paper_cards`, `research_facts`, provenance, and code-link records:

- Research Digest
- Research Map
- Gap Analysis
- Research Synthesis
- Narrative Report

Today each report must be generated with a separate command. Stage 3F provides a repeatable bundle entrypoint so downstream review, sharing, and archival can use one output directory.

## Scope

In scope:

- A new `generate-report-bundle` CLI command.
- A new `research_bundle.py` module.
- Generation of Markdown and JSON artifacts for all five existing Stage 3 reports.
- A `manifest.json` that records generated files and headline counts.
- An `index.md` that links the bundle contents and summarizes counts.
- Unit and CLI coverage for successful export and empty-input failure.

Out of scope:

- New LLM calls.
- Network access.
- Database writes.
- Semantic clustering.
- Source-path repair.
- Rewriting report content from Stages 3A through 3E.

## CLI

Command:

```bash
python -m airesearch.cli generate-report-bundle --out-dir exports/research-report-current
```

Arguments:

- `--out-dir`: required output directory.

The command always exports both Markdown and JSON for each report. Keeping the command format-free makes the bundle stable and avoids partial bundles that are harder to archive.

Success output:

```text
report_bundle_exported=12 papers=11 facts=79 out_dir=exports/research-report-current
```

Failure behavior:

- If `paper_cards` is empty, return code `2` and print the existing `DigestInputError` message.
- Existing report export functions may raise `ValueError` for unsupported formats, but Stage 3F only calls supported formats.

## Output Layout

```text
exports/research-report-current/
  digest.md
  digest.json
  map.md
  map.json
  gap-analysis.md
  gap-analysis.json
  synthesis.md
  synthesis.json
  narrative.md
  narrative.json
  manifest.json
  index.md
```

## Data Model

`ReportArtifact`:

- `name`: stable report key, such as `digest`.
- `title`: human-readable title.
- `markdown_path`: path relative to the bundle directory.
- `json_path`: path relative to the bundle directory.
- `paper_count`: report paper count.
- `fact_count`: report fact count.
- `extra_counts`: report-specific headline counts.

`ReportBundle`:

- `generated_at`: UTC timestamp.
- `out_dir`: output directory path as a string.
- `paper_count`: corpus paper count from the digest export.
- `fact_count`: corpus fact count from the digest export.
- `artifacts`: report artifacts for the five reports.
- `manifest_path`: relative path `manifest.json`.
- `index_path`: relative path `index.md`.

## Report-Specific Extra Counts

- Digest: no extra counts.
- Map: `item_count`.
- Gap Analysis: `papers_missing_fact_types`, `papers_without_code_links`, `missing_evidence_source_path_count`.
- Synthesis: `extraction_target_count`.
- Narrative: `finding_count`, `action_count`.

## Implementation Notes

The bundle module should reuse existing export functions:

- `export_research_digest`
- `export_research_map`
- `export_gap_analysis`
- `export_research_synthesis`
- `export_narrative_report`

Each report is exported twice: once as Markdown and once as JSON. The returned Markdown report object provides the counts recorded in the manifest. This keeps Stage 3F a thin orchestration layer and avoids duplicating existing renderers.

## Testing

Unit tests should create the existing fixture-backed fact database, call `export_report_bundle`, and assert:

- all expected files exist,
- `manifest.json` parses as JSON,
- `paper_count == 1`,
- `fact_count == 2`,
- five report artifacts are listed,
- twelve files are counted,
- `index.md` contains the expected title and report links.

CLI tests should assert:

- `generate-report-bundle --out-dir ...` returns code `0`, prints the bundle summary, and writes the manifest.
- An empty DB returns code `2` with the existing `paper_cards is empty` message.

## Self-Review

- No placeholder requirements remain.
- Scope is limited to deterministic report bundling.
- Error handling matches the existing Stage 3 commands.
- Output filenames are explicit and stable.
