# Stage 3A Research Digest Design

## Purpose

Stage 3A adds the first L3 report output for AIResearch: a deterministic research digest generated from audited L2 data. The digest turns existing `paper_cards` and `research_facts` rows into a human-readable Markdown report and a machine-readable JSON payload without making new LLM calls.

## Scope

The digest includes one section per paper with paper metadata, artifact availability, code links, grouped research facts, and evidence snippets. It is read-only with respect to SQLite: it only reads L2 tables and writes the requested output file.

This stage does not perform cross-paper synthesis, ranking, gap analysis, or new fact extraction. Those belong in later L3 stages after the basic report surface is stable.

## Architecture

Add a focused `research_digest.py` module that owns report assembly and rendering. It will:

- Read paper cards ordered by year descending, title, and paper key.
- Join each paper to `research_facts` and `research_fact_provenance`.
- Group facts by the existing fact types: `method`, `dataset`, `benchmark`, `claim`, and `limitation`.
- Render either Markdown or JSON.

The CLI exposes this as:

```bash
python -m airesearch.cli generate-research-digest --out exports/research-digest.md
python -m airesearch.cli generate-research-digest --format json --out exports/research-digest.json
```

The command exits with status `2` if there are no `paper_cards`, because the user needs to run `extract-paper-cards` first. It still succeeds when a paper has no facts, and the paper section will state that no facts are available.

## Data Shape

The in-memory digest payload is:

```json
{
  "generated_at": "2026-06-09T00:00:00+00:00",
  "paper_count": 1,
  "fact_count": 2,
  "papers": [
    {
      "paper_key": "1706_03762",
      "title": "Attention Is All You Need",
      "authors": ["Ashish Vaswani", "Noam Shazeer"],
      "year": 2017,
      "venue": "",
      "ids": {"arxiv": "1706.03762"},
      "artifact_types": ["summary"],
      "code_links": [],
      "facts": {
        "method": [
          {
            "name": "Transformer attention architecture",
            "statement": "The Transformer replaces recurrence and convolution with attention-based sequence modeling.",
            "confidence": 0.92,
            "evidence_quote": "The Transformer uses attention instead of recurrence or convolution.",
            "evidence_artifact_type": "summary",
            "evidence_source_path": null
          }
        ]
      }
    }
  ]
}
```

Markdown renders the same information compactly:

- Top-level title and generated summary.
- One `##` section per paper.
- Metadata line for authors, year, venue, artifacts, and code links.
- One `###` subsection per fact type that has facts.
- Bullet facts with confidence and evidence.

## Error Handling

- Missing database tables are initialized by the existing `init_db` path.
- Empty `paper_cards` returns a `DigestInputError` and CLI code `2`.
- Malformed JSON fields in `paper_cards` are treated as empty values, matching existing paper-card export behavior.
- Missing evidence fields are rendered as absent rather than crashing. Stage 2D.6 already distinguishes hard failures from soft warnings.

## Testing

Unit tests cover:

- Building a digest from the fixture paper card and fixture facts.
- Markdown rendering includes title, grouped fact type, statement, confidence, and evidence.
- JSON export writes stable fields and counts.
- Empty paper-card input raises `DigestInputError`.

CLI tests cover:

- `generate-research-digest --out digest.md` after fixture sync/card/fact extraction.
- `generate-research-digest --format json --out digest.json`.
- Missing paper cards returns code `2` and a clear message.
