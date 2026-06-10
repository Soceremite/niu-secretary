# Stage 3G Evidence Source-Path Repair Design

## Goal

Add a deterministic workflow that finds research fact provenance rows with missing `evidence_source_path`, searches local text artifacts for their copied evidence quote, and exports auditable repair candidates. The workflow may optionally apply only high-confidence single-path repairs.

## Context

The Stage 2D.6 audit reports 20 soft warnings for missing evidence source paths. Inspection shows all 20 rows have `evidence_artifact_type = abstract`, while the local `paper_artifacts` table contains `summary`, `tldr`, `notes`, `source_tex`, `equations`, and `paper_pdf` artifacts. Because there is no stored `abstract` artifact path, the original extraction could not map those provenance rows to a file path.

The local text artifacts often contain the same abstract quote in `source_tex` and/or `summary`. A narrow deterministic quote search can repair these paths without re-running an LLM.

## Scope

In scope:

- New `repair-evidence-source-paths` CLI command.
- New `evidence_repair.py` module.
- Dry-run candidate generation by default.
- Optional `--apply` mode that updates `research_fact_provenance.evidence_source_path`.
- JSONL export of all missing-path rows and candidate matches.
- Tests for exact matching, no-match handling, apply behavior, and CLI behavior.

Out of scope:

- LLM repair.
- Network access.
- PDF OCR or PDF text extraction.
- Changing `research_facts`.
- Changing `evidence_quote`.
- Semantic or fuzzy matching beyond normalized whitespace containment.

## CLI

Dry run:

```bash
python -m airesearch.cli repair-evidence-source-paths --out exports/evidence-source-path-repair-current.jsonl
```

Apply:

```bash
python -m airesearch.cli repair-evidence-source-paths --apply --out exports/evidence-source-path-repair-current.jsonl
```

Optional filters:

- `--paper-key`: restrict to one paper.

Success output:

```text
evidence_source_path_repair candidates=20 repairable=20 applied=0 out=exports/evidence-source-path-repair-current.jsonl
```

In apply mode, `applied` is the number of DB rows updated.

## Matching Rules

For each provenance row where `evidence_source_path` is empty:

1. Read local text artifacts for the same paper.
2. Normalize quote and artifact text by collapsing whitespace.
3. If the normalized quote is contained in the normalized artifact text, create a match.
4. Select a recommended path by artifact priority:
   - `source_tex`
   - `summary`
   - `notes`
   - `tldr`
5. Mark the row repairable only when at least one exact normalized containment match exists.

The output records every match, not only the recommendation. If multiple artifacts match, the workflow still has a deterministic recommendation, but the report makes the ambiguity visible.

## Apply Rules

`--apply` updates only rows with a recommended path. The update is limited to the target `research_fact_provenance.id` and only fills `evidence_source_path`; it does not alter `evidence_artifact_type` or any research fact fields.

This keeps the original provider-reported artifact type as historical extraction context while repairing the missing path to a local file that actually contains the copied quote.

## JSONL Output

Each line contains:

- `provenance_id`
- `fact_id`
- `paper_key`
- `fact_type`
- `fact_name`
- `statement`
- `evidence_artifact_type`
- `evidence_quote`
- `recommended_source_path`
- `recommended_artifact_type`
- `repairable`
- `applied`
- `matches`

Each match contains:

- `artifact_type`
- `source_path`
- `match_type`
- `score`

For Stage 3G, `match_type` is `normalized_exact_contains` and `score` is `1.0`.

## Testing

Unit tests should cover:

- Candidate generation from a fixture DB with a missing path and quote present in an artifact.
- JSONL export and dry-run behavior.
- Apply mode updates `evidence_source_path`.
- No-match rows remain unrepaired and unapplied.

CLI tests should cover:

- Dry-run export prints candidates, repairable, applied `0`, and writes JSONL.
- Apply mode prints a positive applied count and updates the DB.

## Self-Review

- No placeholder requirements remain.
- The repair boundary is explicit and deterministic.
- Apply mode is narrow and auditable.
- The workflow does not infer new scientific content.
