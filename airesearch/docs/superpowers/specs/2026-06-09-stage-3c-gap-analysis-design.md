# Stage 3C Gap Analysis Design

## Goal

Add a deterministic L3 gap analysis report that turns existing paper cards, research facts, code links, and provenance into a coverage and missing-evidence view for the current AIResearch corpus.

## Context

Stage 3A produces per-paper research digests. Stage 3B produces an exact-label research map. The next useful L3 report is not another summary, but a coverage audit: which fact types are scarce, which papers lack expected fact categories, where code links are absent, and where evidence source paths are missing.

The report must be reproducible and must not call an LLM. It should reuse `build_research_digest()` so it sees the same paper order, fact grouping, code links, and input validation as the existing L3 reports.

## User-Facing Command

```bash
.venv/bin/python -m airesearch.cli generate-gap-analysis --out exports/research-gap-analysis-current.md
.venv/bin/python -m airesearch.cli generate-gap-analysis --format json --out exports/research-gap-analysis-current.json
```

The command returns code `2` with the existing `paper_cards is empty; run extract-paper-cards before generating a digest` message when no paper cards exist.

## Data Model

The report is derived from `ResearchDigest`.

Required fact types are the existing ordered set:

- `method`
- `dataset`
- `benchmark`
- `claim`
- `limitation`

For each paper, compute:

- fact counts by required fact type
- missing fact types
- total fact count
- whether code links are present
- evidence source path missing count

For the corpus, compute:

- paper count
- fact count
- required fact type coverage: papers with at least one fact of that type, total facts of that type, and coverage ratio
- low-coverage fact types where coverage ratio is below `0.5`
- papers missing any required fact type
- papers with no code links
- total evidence records missing `evidence_source_path`

## Output

Markdown output starts with `# AIResearch Gap Analysis` and includes:

- summary counters
- fact type coverage table
- low-coverage fact types
- papers missing fact types
- papers with no code links
- evidence source path gaps

JSON output contains the same data in structured form:

- `generated_at`
- `paper_count`
- `fact_count`
- `required_fact_types`
- `fact_type_coverage`
- `low_coverage_fact_types`
- `papers`
- `papers_missing_fact_types`
- `papers_without_code_links`
- `missing_evidence_source_path_count`

## Sorting

Sorting is deterministic:

- fact types follow `FACT_TYPE_ORDER`
- paper rows follow the digest order
- low-coverage types follow `FACT_TYPE_ORDER`

## Non-Goals

- No semantic clustering.
- No LLM recommendations.
- No database writes beyond the requested export file.
- No changes to Stage 3A or Stage 3B output formats.

## Testing

Add focused module tests using the existing paperpipe fixture and fixture fact extractor:

- build report counts for one fixture paper with two facts
- render Markdown includes summary, missing types, and no-code/code-link status
- JSON export round-trips expected fields
- empty paper cards raises `DigestInputError`

Add CLI tests:

- Markdown and JSON export succeeds after sync, paper cards, and fixture facts
- empty input returns code `2`

Run focused tests and then the full suite.
