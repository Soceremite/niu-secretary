# Stage 3D Research Synthesis Design

## Purpose

Stage 3D adds a deterministic research synthesis report on top of the audited L2 facts and Stage 3A-3C reporting primitives. The report should help a reader quickly see what the current local corpus strongly supports, where coverage is weak, what evidence quality gaps remain, and which paper-level extraction targets should be handled next.

This stage does not call an LLM, does not perform semantic clustering, and does not write to SQLite. It is a reproducible export layer.

## Inputs

- `paper_cards` from Stage 2D.0.
- `research_facts` and `research_fact_provenance` from Stage 2D.1/2D.4.
- `paper_code_links` from deterministic code-link extraction.
- Existing builders:
  - `build_research_digest(db_path)`
  - `build_gap_analysis(db_path)`

If `paper_cards` is empty, synthesis must raise the same `DigestInputError` message used by the digest path: `paper_cards is empty; run extract-paper-cards before generating a digest`.

## Output

Add a CLI command:

```bash
.venv/bin/python -m airesearch.cli generate-research-synthesis --out exports/research-synthesis-current.md
.venv/bin/python -m airesearch.cli generate-research-synthesis --format json --out exports/research-synthesis-current.json
```

The Markdown report must include:

- Corpus snapshot: papers, facts, required fact types, papers missing fact types, papers without code links, missing evidence source paths.
- Strong coverage: fact types with at least 80% paper coverage.
- Weak coverage: fact types below 50% paper coverage.
- Moderate coverage: fact types from 50% to below 80% coverage.
- Evidence quality: missing source path count and affected papers.
- Code availability: papers without code links.
- Next extraction targets: per-paper missing fact types sorted by largest gap first.
- Fact type synthesis notes: deterministic one-line notes for each required fact type.

The JSON report must expose the same content as structured fields.

## Data Model

Create `airesearch.research_synthesis` with:

- `CoverageBand`: `name`, `fact_types`.
- `ExtractionTarget`: `paper_key`, `title`, `year`, `venue`, `missing_fact_types`, `missing_evidence_source_path_count`, `has_code_links`, `priority_score`.
- `SynthesisNote`: `fact_type`, `coverage_ratio`, `paper_count`, `fact_count`, `note`.
- `ResearchSynthesis`: generated timestamp, corpus counts, strong/moderate/weak bands, evidence/code summary counts, extraction targets, and synthesis notes.

Priority score is deterministic:

```text
len(missing_fact_types) * 10
+ missing_evidence_source_path_count
+ 5 if no code links
```

Sort extraction targets by descending priority score, then title, then paper key.

## Coverage Rules

- Strong: `coverage_ratio >= 0.8`
- Moderate: `0.5 <= coverage_ratio < 0.8`
- Weak: `coverage_ratio < 0.5`

Synthesis notes:

- Strong: `Well covered across the current corpus; use these facts as the backbone for synthesis.`
- Moderate: `Partially covered; use with paper-level caveats and prioritize missing papers before broad claims.`
- Weak: `Under-covered; treat conclusions as provisional until more papers include this fact type.`

## Testing

Add module tests using the existing fixture-backed one-paper database:

- Builds synthesis from fixture facts and classifies method/claim as strong, dataset/benchmark/limitation as weak.
- Renders Markdown with snapshot, weak coverage, code availability, and next extraction targets.
- Exports JSON and verifies structured fields.
- Raises `DigestInputError` when `paper_cards` is empty.

Add CLI tests:

- `generate-research-synthesis` writes Markdown and JSON.
- Empty `paper_cards` returns code 2 with the digest input error message.

## Non-Goals

- No LLM summarization.
- No semantic clustering or embedding search.
- No edits to fact extraction, audit, or graph schema.
- No database persistence for synthesis output.
