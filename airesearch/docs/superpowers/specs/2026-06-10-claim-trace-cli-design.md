# Claim Trace CLI Design

## Goal

Add a read-only `claim-trace` CLI command that traces one extracted research fact back to its paper metadata, evidence provenance, artifact path, code links, and knowledge-graph relations.

## Scope

The first implementation is a local CLI and JSON/Markdown exporter. It does not change the SQLite schema, regenerate facts, call LLM providers, or build a web UI. It uses existing tables only:

- `research_facts`
- `research_fact_provenance`
- `papers`
- `paper_artifacts`
- `paper_code_links`
- `kg_edges`
- `kg_nodes`
- `kg_provenance`

## User Interface

Primary exact lookup:

```bash
python -m airesearch.cli claim-trace --fact-id 123
```

Search lookup:

```bash
python -m airesearch.cli claim-trace --paper-key 1706_03762 --type claim --query attention --format markdown
```

File export:

```bash
python -m airesearch.cli claim-trace --fact-id 123 --format json --out exports/claim-trace.json
```

`--format` supports `markdown` and `json`, defaulting to `markdown`. `--out` writes the rendered payload to disk; without `--out`, the command prints to stdout.

## Selection Rules

`--fact-id` is exact and takes precedence. If no fact exists for the id, the command exits with code `2` and prints a concise not-found message.

Without `--fact-id`, the command requires `--paper-key`. Optional filters are:

- `--type`: one of `method`, `dataset`, `benchmark`, `claim`, `limitation`
- `--query`: case-insensitive substring match against `statement` and `name`

Search mode returns the first deterministic match ordered by `paper_key`, `fact_type`, and `id`. If no match exists, it exits with code `2`.

## Trace Payload

The trace includes:

- `fact`: id, paper key, type, name, statement, confidence, metadata, provider, extractor version.
- `paper`: title, authors, year, venue, ids, source directory.
- `provenance`: evidence quote, evidence artifact type, evidence source path.
- `artifact`: matching artifact record when evidence artifact type or source path maps to `paper_artifacts`.
- `code_links`: all known code links for the paper.
- `graph_relations`: paper-scoped KG edges with source and target node labels/properties.
- `graph_provenance`: paper-scoped KG provenance rows, including rows tied to evidence artifact or code-link sources when available.

## Error Handling

The command initializes the DB if necessary so the error is a clean not-found result rather than a missing table crash. Malformed JSON stored in ledger fields is rendered as safe empty objects or arrays using the same fallback behavior used by existing modules.

## Testing

Tests cover:

- exact trace by fact id;
- search trace by paper key, type, and query;
- Markdown rendering;
- JSON file export;
- not-found CLI return code.

The implementation must pass the focused claim-trace tests, related fact/graph/CLI tests, and the full test suite.
