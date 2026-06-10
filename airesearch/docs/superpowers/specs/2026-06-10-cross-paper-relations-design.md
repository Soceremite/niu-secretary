# Cross-Paper Relations Design

## Goal

Add deterministic cross-paper relation summaries so AIResearch can identify shared code repositories, shared datasets, and citation-ledger coverage gaps across the current corpus.

## Scope

This feature is a read-only report generator. It does not change the SQLite schema, call LLM providers, or parse full citation graphs. It uses existing report inputs:

- `paper_cards`
- `paper_code_links`
- `research_facts`
- `research_fact_provenance`
- existing report bundle infrastructure

## User Interface

New CLI command:

```bash
python -m airesearch.cli generate-research-relations --out exports/research-relations-current.md
python -m airesearch.cli generate-research-relations --format json --out exports/research-relations-current.json
```

The command requires paper cards, like the other deterministic reports. If `paper_cards` is empty, it returns the existing `DigestInputError` message.

## Report Content

The report contains three sections:

1. **Code Relations**
   - Groups papers by exact normalized GitHub repository.
   - Also groups papers by repository owner and host when the grouping spans more than one paper.
   - Includes paper references and source URLs.

2. **Dataset Relations**
   - Groups `dataset` facts by normalized fact name, falling back to statement text when `name` is empty.
   - Includes paper references, evidence source paths, evidence quotes, and confidence values.

3. **Citation Ledger Status**
   - Reports that true citation edges are not yet available until the richer citation ledger is implemented.
   - Counts citation-like artifacts if they exist under artifact types such as `references`, `citations`, or `bibtex`.
   - Lists papers still missing citation artifacts.

Only relation groups spanning at least two distinct papers are emitted as cross-paper relations. Singletons are counted in JSON for auditability but not presented as cross-paper claims.

## Bundle Integration

`generate-report-bundle` includes `relations.md` and `relations.json` between Research Map and Gap Analysis. The manifest records extra counts for code relations, dataset relations, and citation artifact coverage.

## Error Handling

The report uses the same input validation as existing reports by building on `build_research_digest`. Malformed JSON in existing ledger fields is handled by existing digest parsing fallbacks.

## Testing

Tests cover:

- code repository grouping across two papers;
- dataset fact grouping across two papers;
- citation ledger gap summary when no citation artifact exists;
- Markdown and JSON export;
- CLI command;
- report bundle artifact counts and manifest ordering.
