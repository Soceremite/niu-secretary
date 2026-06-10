# Artifact Ledger Design

## Goal

Add a reusable artifact ledger that turns paperpipe artifacts into queryable chunk, equation, and citation rows. The ledger should make claim tracing and research relation reports cite finer-grained evidence than raw artifact paths.

## Scope

This feature covers deterministic extraction from artifacts already registered in `paper_artifacts`.

In scope:

- Text chunks from `summary`, `tldr`, `notes`, and `source_tex`.
- Equations from `equations` artifacts.
- Citation mentions from TeX citation commands in `source_tex`.
- CLI commands to extract and export the ledger.
- Integration into `claim-trace`, `generate-research-relations`, and report bundles.
- Tests for idempotency, export formats, CLI behavior, and report integration.

Out of scope:

- PDF parsing.
- Full bibliography parsing.
- Matching citation keys to database paper records.
- LLM-based chunking or citation extraction.

## Data Model

Add three derived tables to `schema.sql`.

`paper_chunks` stores readable text units:

- `id`
- `paper_key`
- `artifact_type`
- `source_path`
- `chunk_index`
- `heading`
- `text`
- `char_start`
- `char_end`
- `sha256`
- `created_at`
- `updated_at`

`paper_equations` stores extracted formula rows:

- `id`
- `paper_key`
- `source_path`
- `equation_index`
- `label`
- `latex`
- `context`
- `created_at`
- `updated_at`

`paper_citations` stores citation mentions:

- `id`
- `paper_key`
- `source_path`
- `citation_index`
- `citation_key`
- `raw_text`
- `context`
- `created_at`
- `updated_at`

Each table is derived from artifact contents and can be rebuilt per paper. Rows use unique constraints on paper/source/index fields so extraction is idempotent.

## Extraction

Create `src/airesearch/artifact_ledger.py`.

The extractor reads papers from `papers`, then uses `paper_artifacts` to find eligible source files. For each processed paper it deletes old ledger rows for that paper, then inserts freshly parsed rows in a single transaction.

Chunk extraction:

- Read `summary`, `tldr`, `notes`, and `source_tex` as UTF-8 with replacement.
- Split Markdown artifacts on headings and blank-line paragraphs.
- Split TeX source on blank-line paragraphs after lightweight whitespace normalization.
- Skip empty chunks.
- Store source character offsets when available.

Equation extraction:

- Read `equations.md`.
- Ignore empty lines and Markdown headings.
- Store each remaining line as an equation.
- If the line contains a simple label prefix such as `label: equation`, store the prefix as `label`; otherwise label is empty.

Citation extraction:

- Read `source_tex`.
- Match TeX commands such as `\cite{key}`, `\citep{key}`, `\citet{key}`, and `\citealp{key}`.
- Split comma-separated keys.
- Store one row per key with the raw command and a compact context window.

## CLI

Add:

```bash
python -m airesearch.cli extract-artifact-ledger --paper-key 1706_03762 --limit 10
```

Output:

```text
artifact_ledger_extracted papers_seen=1 chunks_written=4 equations_written=1 citations_written=0
```

Add:

```bash
python -m airesearch.cli export-artifact-ledger --out exports/artifact-ledger.md
python -m airesearch.cli export-artifact-ledger --out exports/artifact-ledger.json --format json
python -m airesearch.cli export-artifact-ledger --out exports/artifact-ledger.jsonl --format jsonl
```

Export reads existing ledger rows. It does not implicitly run extraction, so command effects stay predictable.

## Integrations

`claim-trace` should include a `ledger_matches` section. Matching is deterministic:

- Normalize whitespace.
- Match evidence quotes against chunk/equation/citation context first.
- If no evidence quote is present, match the fact statement.
- Return a small bounded set ordered by match strength, type, source path, and index.

`generate-research-relations` should use `paper_citations` for citation ledger status:

- If citation rows exist, status becomes `citation_ledger_available`.
- Report papers with citation rows, citation row count, and papers still missing citation rows.
- It should still avoid claiming true citation edges until citation keys are matched to papers.

`export-report-bundle` should include `artifact-ledger.md` and `artifact-ledger.json` so the generated static site can expose the ledger as a first-class report artifact.

## Error Handling

- Missing or unreadable artifact files are skipped.
- Invalid UTF-8 is read with replacement.
- Empty databases return zero counts for extraction, but exports require initialized schema.
- Unsupported export formats raise `ValueError`.
- CLI validation errors return code `2`, following existing CLI style.

## Testing

Add focused tests:

- `tests/test_artifact_ledger.py` for parser behavior, extraction counts, idempotency, and exports.
- `tests/test_cli.py` for extraction/export commands.
- `tests/test_claim_trace.py` for ledger match output.
- `tests/test_research_relations.py` for citation ledger status based on `paper_citations`.
- `tests/test_research_bundle.py` for bundled ledger artifacts and updated counts.

Run focused tests first, then the full suite.
