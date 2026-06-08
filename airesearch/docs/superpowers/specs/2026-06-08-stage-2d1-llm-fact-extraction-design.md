# Stage 2D.1 LLM Fact Extraction Design

## Goal

Add the data contract and execution path for LLM-assisted paper fact extraction while keeping the first implementation reproducible and quota-safe. The system must store method, dataset, benchmark, claim, and limitation facts with explicit evidence provenance.

## Scope

This stage implements the extraction substrate, not production LLM calls. It includes:

- SQLite tables for structured research facts, fact provenance, and fact extraction run audit.
- A provider interface that returns validated JSON facts.
- A fixture/mock provider for deterministic tests and local smoke runs.
- CLI commands to run fixture extraction, list facts, and export facts as JSONL.
- Idempotent writes per paper/provider/extractor version.

Out of scope for this stage:

- Calling a real cloud LLM endpoint.
- Summarizing PDFs directly.
- Trusting facts without an evidence quote and artifact source.

## Fact Contract

Each fact has:

- `paper_key`
- `fact_type`: one of `method`, `dataset`, `benchmark`, `claim`, `limitation`
- `name`: short label suitable for graph node labels
- `statement`: one sentence fact text
- `evidence_quote`: exact or near-exact short quote from an artifact
- `evidence_artifact_type`: usually `summary`, `notes`, or future full-text chunk source
- `confidence`: numeric score from 0.0 to 1.0
- `metadata_json`: provider-specific structured details

The writer rejects facts with unsupported types, empty statements, missing evidence quotes, or confidence outside `[0, 1]`.

## Architecture

`fact_extraction.py` owns validation, fixture loading, idempotent persistence, listing, and export. It reads `papers`, `paper_cards`, and `paper_artifacts`; it writes `research_facts`, `research_fact_provenance`, and `fact_extraction_runs`.

The fixture provider is deliberately shaped like a real LLM response: a JSON object keyed by paper key, where each paper contains a list of facts. This lets tests exercise the same validation and storage path that a future OpenAI or PaperQA-backed provider will use.

## CLI

- `extract-research-facts --provider fixture --fixture PATH [--paper-key KEY] [--limit N]`
- `list-research-facts [--paper-key KEY] [--type TYPE] [--limit N]`
- `export-research-facts --out PATH`

## Error Handling

A bad fixture path, unsupported provider, unsupported fact type, or invalid fact payload returns a non-zero CLI status. Extraction run rows record `success` or `failed` with error text. Failed runs do not commit partial facts.

## Testing

Tests cover validation, idempotent persistence, provenance creation, CLI extraction/list/export, and rejection of unsupported fact types. Full existing tests must continue to pass.
