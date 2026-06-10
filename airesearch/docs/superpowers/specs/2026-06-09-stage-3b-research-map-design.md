# Stage 3B Research Map Design

## Purpose

Stage 3B adds the first cross-paper L3 report for AIResearch. It turns audited L2 paper cards and research facts into a deterministic research map that helps compare methods, datasets, benchmarks, claims, and limitations across the current corpus.

The map is a reporting layer only. It does not call an LLM, infer new facts, change the SQLite schema, or mutate source tables.

## Inputs

- `paper_cards`: paper metadata, artifact types, and paper ordering.
- `research_facts`: fact type, name, statement, confidence, and paper ownership.
- `research_fact_provenance`: evidence quote and source metadata.
- `paper_code_links`: code repository links, exposed through existing paper-card helpers.

The implementation should reuse `build_research_digest()` so the map shares Stage 3A's paper/fact loading behavior and empty-input validation.

## Output

The CLI writes either Markdown or JSON:

```bash
python -m airesearch.cli generate-research-map --out exports/research-map-current.md
python -m airesearch.cli generate-research-map --format json --out exports/research-map-current.json
```

The Markdown report contains:

- A summary header with generation time, paper count, fact count, mapped item count, and fact-type counts.
- One section per fact type in this order: method, dataset, benchmark, claim, limitation.
- Within each section, deterministic map items grouped by normalized fact name when available, otherwise normalized statement.
- Each item lists paper count, fact count, average confidence, supporting papers, code links, and concise evidence lines.

The JSON report contains the same information as structured data:

- `generated_at`
- `paper_count`
- `fact_count`
- `item_count`
- `fact_type_counts`
- `sections[]`

Each section has `fact_type`, `title`, and `items[]`. Each item has `key`, `label`, `paper_count`, `fact_count`, `average_confidence`, `papers[]`, and `evidence[]`.

## Grouping Rules

The report must be reproducible and transparent:

- Normalize labels by lowercasing, trimming whitespace, collapsing repeated whitespace, and stripping common Markdown emphasis characters.
- Prefer fact `name` as the item label. Fall back to fact `statement` when the name is empty.
- Group only exact normalized labels. No fuzzy matching or semantic clustering in Stage 3B.
- Preserve source statements and evidence; do not synthesize new claims.
- Sort items by descending paper count, descending fact count, descending average confidence, then label.
- Sort paper references by descending paper year, then title, then paper key.

## Error Handling

If `paper_cards` is empty, the command returns exit code `2` and prints the existing Stage 3A message:

```text
paper_cards is empty; run extract-paper-cards before generating a digest
```

Unsupported output formats raise `ValueError` at the module API level. The CLI constrains choices to `markdown` and `json`.

## Testing

Add focused module tests covering:

- grouping fixture facts into map sections,
- Markdown content for summary, section, item, paper, and evidence,
- JSON export shape,
- empty `paper_cards` input.

Add CLI tests covering:

- Markdown and JSON exports,
- exit code `2` for empty `paper_cards`.

Run focused tests first, then the full suite.

## Out Of Scope

- LLM summarization or semantic clustering.
- Gap analysis recommendations.
- New database tables.
- Cross-corpus trend scoring.
- HTML or dashboard rendering.
