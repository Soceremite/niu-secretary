# Stage 2B Research Candidate Discovery Design

## Goal

Build AIResearch's candidate discovery layer for recent high-signal research papers. The system should search predefined research profiles, score candidates, store them locally, and let the user review Top 100 before batch ingestion.

This stage does not automatically call `papi add`. It produces an auditable candidate pool for manual selection.

## User Preferences

- Default search window: the last 12 months from the current date.
- Exception window: 2024-01-01 onward only for famous or strongly backed models.
- Older papers are background references only and must not enter the Top 100 candidate pool by default.
- Prefer newest papers with strong backing:
  - Top venues: CVPR, ICCV, ECCV, ICLR, ICML, NeurIPS, CoRL, RSS, ICRA, IROS, Science Robotics.
  - Companies: Google, Google DeepMind, Meta, NVIDIA, OpenAI, Anthropic, Microsoft, ByteDance, DeepSeek, Apple, Tesla, Figure AI, Physical Intelligence.
  - Schools/labs: MIT, Stanford, Berkeley, CMU, Princeton, Harvard, Oxford, Cambridge, ETH, EPFL, Tsinghua, PKU, Shanghai AI Lab, NTU, NUS.
  - Scholars: Kaiming He, Fei-Fei Li, Pieter Abbeel, Sergey Levine, Chelsea Finn, Jitendra Malik, Yann LeCun, Yoshua Bengio, Dieter Fox, Anima Anandkumar.

## Research Profiles

Stage 2B ships with five profiles:

- `multimodal_foundation_models`
- `unified_multimodal_understanding_generation`
- `world_models_physical_ai`
- `diffusion_models`
- `embodied_ai_vla_robotics`

Each profile stores keywords, preferred venues, preferred organizations, preferred scholars, and exception model keywords.

## Sources

MVP sources:

- OpenAlex API for broad metadata and institution/venue fields.
- Semantic Scholar API if available for citation count and paper IDs.
- arXiv search for very recent preprints.

Google Scholar is not a primary source because it is not reliable for automated access. It can be used manually for spot checks, but not as the pipeline dependency.

## Data Model

Add these SQLite tables:

- `research_profiles`: local profile definitions.
- `discovery_runs`: one row per discovery execution.
- `research_candidates`: candidate paper metadata, score, status, and reason fields.

The existing `ingest_runs` and `ingest_items` remain responsible for actual `papi add` batch ingestion.

## Scoring

Candidate score is deterministic and explainable:

```text
score = recency_score * 0.35
      + backing_score * 0.25
      + venue_score * 0.20
      + topic_score * 0.15
      + artifact_score * 0.05
```

Rules:

- Primary candidates must have a date within the last 12 months.
- Exception candidates from 2024-01-01 onward need strong backing or famous model keywords.
- Backing includes organization, school, scholar, source, and known lab names.
- Topic score comes from keyword hits in title, abstract, and source text.
- Artifact score rewards code, project page, model page, dataset page, or arXiv PDF availability.

## CLI

Add commands:

- `seed-profiles`: create or refresh default research profiles.
- `discover-candidates --profile <name> --limit <n>`: query sources and store candidates.
- `list-candidates --profile <name> --limit <n>`: print sorted candidate rows.
- `export-candidates --profile <name> --limit <n> --out <path>`: write a manifest for later `batch-ingest`.

## Acceptance Criteria

- Default profiles can be seeded into SQLite.
- Offline scoring tests rank newer, strongly backed candidates above generic old candidates.
- Candidate records store source, title, authors, year/date, venue, organizations, score, score reasons, and status.
- `list-candidates` can display Top N from SQLite.
- `export-candidates` writes identifiers or URLs that can be passed to Stage 2A `batch-ingest`.
- No candidate discovery automatically downloads papers.
