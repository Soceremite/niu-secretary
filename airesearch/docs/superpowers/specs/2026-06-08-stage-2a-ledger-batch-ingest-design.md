# Stage 2A Ledger And Batch Ingest Design

## Goal

Build the first AIResearch-owned runtime layer above paperpipe: a local SQLite ledger, a sync adapter for paperpipe artifacts, and a batch ingest command that can manage roughly 100 papers with auditability.

This stage does not implement automatic discovery, knowledge graph extraction, or research reports. It creates the state model those later stages need.

## Scope

In scope:

- Create `data/airesearch.sqlite3`.
- Define SQLite tables for papers, sources, artifacts, ingest jobs, batch runs, and batch items.
- Sync paperpipe `index.json` and each paper directory into the ledger.
- Provide a Python CLI for:
  - `init-db`
  - `sync-paperpipe`
  - `batch-ingest <manifest>`
  - `status`
- Support batch manifests containing arXiv IDs, URLs, DOI strings, title strings, or local paths.
- Call `papi add` through the configured local environment.
- Track duplicate, success, skipped, and failed items without losing history.

Out of scope:

- OpenAlex / Semantic Scholar discovery.
- Candidate ranking.
- Knowledge graph entities and relations.
- LLM extraction beyond paperpipe's own generation.
- Research Digest / Map / Gap Analysis.

## Architecture

AIResearch stores its own authoritative operational state in SQLite. Paper content remains under `data/paperpipe/`; the ledger only stores metadata, artifact paths, hashes, and run status.

The CLI reads `.env` through `activate.sh` conventions where possible, but it does not store secrets in SQLite. It shells out to `papi add` for ingestion and then syncs the resulting paperpipe state into the ledger.

## Components

- `src/airesearch/config.py`: Resolve project root, paperpipe DB path, SQLite DB path, and `papi` executable.
- `src/airesearch/schema.sql`: SQLite schema.
- `src/airesearch/db.py`: Connection, migration, and simple query helpers.
- `src/airesearch/paperpipe_sync.py`: Read `index.json`, inspect paper directories, hash artifacts, and upsert ledger rows.
- `src/airesearch/batch.py`: Parse manifest lines, create batch run records, call `papi add`, sync after each item, and record outcomes.
- `src/airesearch/cli.py`: User-facing commands.

## Data Model

Minimum tables:

- `papers`: one row per paperpipe paper key.
- `paper_sources`: source identifiers or input strings associated with a paper.
- `paper_artifacts`: local file paths and hashes for `paper.pdf`, `source.tex`, `summary.md`, `equations.md`, `tldr.md`, and `notes.md`.
- `ingest_runs`: one row per batch command execution.
- `ingest_items`: one row per manifest item with status, error, resolved paper key, and timestamps.
- `sync_events`: records full or per-paper sync actions.

All timestamps use UTC ISO-8601 strings. JSON payloads are stored as text to avoid adding dependencies.

## Error Handling

Batch ingest never aborts the whole run because one paper fails. Each item is marked:

- `success`: `papi add` completed and at least one paper record was synced.
- `duplicate`: the input appears already present before ingestion.
- `failed`: `papi add` returned non-zero or no synced paper could be matched.
- `skipped`: blank/comment manifest lines or unsupported rows.

Command output prints a concise summary and points to the SQLite ledger for details.

## Testing

Tests use temporary directories and fake paperpipe data. Batch tests use a fake `papi` executable so they do not call the network or third-party APIs.

Coverage target for this stage:

- Schema initialization creates expected tables.
- Paperpipe sync upserts paper and artifact rows.
- Manifest parsing handles comments, blank lines, and raw identifiers.
- Batch ingest records success and failure independently.
- CLI smoke tests cover `init-db`, `sync-paperpipe`, and `status`.

## Acceptance Criteria

- `python -m airesearch.cli init-db` creates `data/airesearch.sqlite3`.
- `python -m airesearch.cli sync-paperpipe` syncs the existing `1706_03762` paper into the ledger.
- A manifest of multiple papers can be processed without stopping on one failure.
- `python -m airesearch.cli status` reports paper count, artifact count, latest sync, and latest ingest run.
- No API keys are printed or written to SQLite.
