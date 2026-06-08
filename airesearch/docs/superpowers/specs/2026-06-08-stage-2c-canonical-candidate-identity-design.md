# Stage 2C.0 Canonical Candidate Identity Design

## Goal

Add a canonical candidate identity layer before Stage 2C batch ingestion so the same paper discovered through multiple providers or profiles is reviewed and ingested once.

## Problem

`research_candidates` stores discovery records keyed by `(profile_name, source, source_id)`. This preserves provenance, but it means one paper can appear multiple times when it is found by several providers or belongs to several research profiles. Stage 2C needs a deduplicated review and export surface without losing the original discovery evidence.

## Approach

Keep `research_candidates` as the append/update discovery table. Add a derived `candidate_papers` table keyed by `canonical_key`, plus a `candidate_paper_links` table that maps each canonical paper to all source candidate rows.

Canonical keys are deterministic and use the strongest available identity:

1. `arxiv:<id>` from arXiv source IDs, arXiv URLs, or arXiv links in candidate text.
2. `doi:<doi>` from DOI URLs or DOI-like source IDs.
3. `semantic_scholar:<id>` for Semantic Scholar paper IDs.
4. `openalex:<id>` for OpenAlex IDs.
5. `title_year:<normalized_title>:<year>` as the fallback.

The materialization command recomputes canonical candidates from current `research_candidates`. It is safe to rerun. It upserts canonical paper summaries, refreshes link rows, and preserves source discovery records.

## Data Model

`candidate_papers` stores the reviewable canonical paper:

- `canonical_key`
- representative `title`, `url`, `venue`, `published_date`, `year`, `abstract`
- `best_score`
- JSON lists for `profiles`, `sources`, `source_urls`, and source candidate IDs
- `status`, defaulting to `candidate`
- timestamps

`candidate_paper_links` stores normalized provenance:

- `canonical_key`
- `research_candidate_id`
- `profile_name`
- `source`
- `score`

## CLI

Add three commands:

- `dedupe-candidates`: materialize canonical papers from current candidate records.
- `list-canonical-candidates`: list deduplicated papers ranked by `best_score`.
- `export-canonical-candidates`: export deduplicated identifiers for batch ingestion.

Export priority is URL first, then canonical key fallback. This keeps current paperpipe batch ingestion behavior simple while avoiding duplicate candidate exports.

## Error Handling

Candidates without a title and without a usable source identity are skipped. Existing candidate discovery and provider behavior is unchanged. Materialization should not spend provider quota and should not make network calls.

## Testing

Unit tests cover canonical key extraction, cross-provider deduplication, cross-profile aggregation, export ordering, and CLI smoke paths.
