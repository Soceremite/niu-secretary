# Stage 2C.1 Canonical Review Workflow Design

## Goal

Add a small review workflow for canonical candidates so Stage 2C can approve papers intentionally before batch ingestion.

## Approach

Use `candidate_papers.status` as the review state. The allowed states are:

- `candidate`: discovered and deduplicated, not reviewed.
- `selected`: approved for batch ingestion.
- `rejected`: reviewed and excluded.

No network calls are made by review commands. Review operates only on the local SQLite candidate tables.

## CLI

Add these commands:

- `set-canonical-status <canonical_key> --status candidate|selected|rejected`
- `select-canonical-candidates --limit N [--min-score SCORE]`
- `export-approved-candidates --out PATH`

`select-canonical-candidates` marks the top ranked `candidate` rows as `selected`, respecting the minimum score when provided. It does not modify rows already marked `selected` or `rejected`.

`export-approved-candidates` writes only selected canonical candidates to a manifest suitable for the existing `batch-ingest` command.

## Safety

Unknown canonical keys raise a clear error and return a non-zero CLI exit code. Batch selection refuses non-positive limits. Materializing canonical candidates preserves existing status values, so review decisions survive re-running `dedupe-candidates`.

## Testing

Tests cover single status updates, rejection exclusion from batch selection, approved-only export, CLI success paths, and unknown-key failure.
