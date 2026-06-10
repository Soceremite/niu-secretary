# Stage 3E Narrative Report Design

## Purpose

Stage 3E adds a deterministic narrative report that turns existing L2 facts and Stage 3 synthesis into a readable research brief. The report is intended for a human reader who wants the current state of the corpus without reading every paper card, map item, or gap table.

The report must be transparent about evidence limits. It does not call an LLM, does not perform semantic inference, and does not write to SQLite.

## Inputs

- `build_research_digest(db_path)` for paper-level facts and provenance.
- `build_research_synthesis(db_path)` for coverage bands, extraction targets, and quality counters.

If `paper_cards` is empty, the report must raise the same `DigestInputError` used by the other Stage 3 reports.

## Output

Add a CLI command:

```bash
.venv/bin/python -m airesearch.cli generate-narrative-report --out exports/research-narrative-current.md
.venv/bin/python -m airesearch.cli generate-narrative-report --format json --out exports/research-narrative-current.json
```

The Markdown report must include:

- Report title and corpus snapshot.
- Executive summary with deterministic sentences derived from coverage bands and quality counters.
- What is well supported, based on strong coverage fact types.
- What is provisional, based on moderate/weak coverage fact types.
- Representative findings, selected from the highest-confidence facts per fact type.
- Priority follow-up actions, selected from the top extraction targets.
- Evidence caution section covering missing source paths and code-link gaps.

The JSON report must expose the same content as structured fields.

## Data Model

Create `airesearch.research_narrative` with:

- `NarrativeFinding`: fact type, paper key, paper title, fact name, statement, confidence, evidence quote, evidence source path.
- `PriorityAction`: paper key, title, priority score, action text.
- `NarrativeReport`: generated timestamp, paper/fact counts, executive summary, supported areas, provisional areas, representative findings, priority actions, evidence cautions.

Representative findings are selected deterministically:

- For each required fact type in `FACT_TYPE_ORDER`, collect all facts from the digest.
- Sort by descending confidence, then paper title, then fact name, then statement.
- Keep at most two findings per fact type.

Priority actions are selected from the top five synthesis extraction targets. Action text must mention missing fact types, missing evidence source paths, and code-link state.

## Wording Rules

All narrative wording must be deterministic and evidence-bound:

- Do not claim scientific conclusions beyond stored facts.
- Do not say a method, dataset, or benchmark is generally best.
- Use coverage language: “well represented in this corpus”, “partially represented”, “under-covered”.
- When facts lack source paths, explicitly caution against downstream quoting until repaired.

## Testing

Add module tests using the existing fixture-backed one-paper database:

- Builds a report with one paper, two facts, supported method/claim areas, provisional dataset/benchmark/limitation areas, and one priority action.
- Renders Markdown with executive summary, representative findings, priority actions, and evidence cautions.
- Exports JSON and verifies structured fields.
- Raises `DigestInputError` when `paper_cards` is empty.

Add CLI tests:

- `generate-narrative-report` writes Markdown and JSON.
- Empty `paper_cards` returns code 2 with the digest input error message.

## Non-Goals

- No LLM-generated prose.
- No embedding or semantic clustering.
- No citation graph reasoning.
- No database persistence.
