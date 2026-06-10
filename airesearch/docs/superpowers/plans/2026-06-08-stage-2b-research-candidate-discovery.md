# Stage 2B Research Candidate Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build local research profiles, deterministic candidate scoring, SQLite candidate storage, and CLI review/export commands for recent high-signal AI research papers.

**Architecture:** Stage 2B extends the Stage 2A SQLite ledger with profile and candidate tables. Discovery sources are isolated behind small provider functions, while scoring remains deterministic and testable offline. The first implementation focuses on local profiles, scoring, storage, list/export commands, and a source adapter interface; network-backed provider calls can be added without changing the scoring or CLI contracts.

**Tech Stack:** Python 3.12, SQLite, argparse, pytest, optional urllib JSON APIs for OpenAlex/arXiv/Semantic Scholar.

---

## File Structure

- Modify `src/airesearch/schema.sql`: add `research_profiles`, `discovery_runs`, and `research_candidates`.
- Create `src/airesearch/profiles.py`: default profile definitions and seeding.
- Create `src/airesearch/candidates.py`: candidate model, scoring, storage, listing, exporting.
- Create `src/airesearch/discovery.py`: provider interface and run orchestration.
- Modify `src/airesearch/cli.py`: add `seed-profiles`, `discover-candidates`, `list-candidates`, and `export-candidates`.
- Create `tests/test_profiles.py`: profile seeding tests.
- Create `tests/test_candidates.py`: scoring and export tests.
- Create `tests/test_discovery.py`: fake provider orchestration tests.
- Modify `tests/test_cli.py`: CLI coverage for new commands.
- Modify `PLAN.md`: record Stage 2B status and verification.

## Task 1: Schema Extension

**Files:**
- Modify: `src/airesearch/schema.sql`
- Test: `tests/test_db.py`

- [ ] **Step 1: Extend schema test**

Add assertions that `research_profiles`, `discovery_runs`, and `research_candidates` are created by `init_db`.

- [ ] **Step 2: Add tables**

Add:

```sql
create table if not exists research_profiles (...);
create table if not exists discovery_runs (...);
create table if not exists research_candidates (...);
```

Candidate rows must include `profile_name`, `source`, `source_id`, `title`, `url`, `authors_json`, `organizations_json`, `venue`, `published_date`, `year`, `abstract`, `score`, `score_reasons_json`, `status`, `created_at`, and `updated_at`.

- [ ] **Step 3: Run DB tests**

Run: `.venv/bin/python -m pytest tests/test_db.py -v`

Expected: schema tests pass.

## Task 2: Default Research Profiles

**Files:**
- Create: `src/airesearch/profiles.py`
- Test: `tests/test_profiles.py`

- [ ] **Step 1: Write tests**

Test that default profiles include:

- `multimodal_foundation_models`
- `unified_multimodal_understanding_generation`
- `world_models_physical_ai`
- `diffusion_models`
- `embodied_ai_vla_robotics`

Also test that `seed_profiles(db_path)` writes exactly these profile names into SQLite.

- [ ] **Step 2: Implement profiles**

Create dataclass `ResearchProfile` with fields:

- `name`
- `description`
- `keywords`
- `preferred_venues`
- `preferred_organizations`
- `preferred_scholars`
- `exception_keywords`
- `primary_since`
- `exception_since`

Use `primary_since="2025-06-08"` and `exception_since="2024-01-01"` for the current Stage 2B default.

- [ ] **Step 3: Run profile tests**

Run: `.venv/bin/python -m pytest tests/test_profiles.py -v`

Expected: profile tests pass.

## Task 3: Candidate Scoring And Storage

**Files:**
- Create: `src/airesearch/candidates.py`
- Test: `tests/test_candidates.py`

- [ ] **Step 1: Write scoring tests**

Test that:

- A 2026 candidate with NVIDIA or Google backing outranks a generic 2024 candidate.
- A 2024 candidate is accepted only when it has exception keywords or strong backing.
- Export writes one identifier or URL per line.

- [ ] **Step 2: Implement candidate model and scoring**

Create dataclass `CandidatePaper` and functions:

- `score_candidate(profile, candidate) -> tuple[float, list[str]]`
- `is_candidate_allowed(profile, candidate) -> bool`
- `upsert_candidate(db_path, profile_name, candidate, score, reasons)`
- `list_candidates(db_path, profile_name, limit)`
- `export_candidates(db_path, profile_name, limit, out_path)`

- [ ] **Step 3: Run candidate tests**

Run: `.venv/bin/python -m pytest tests/test_candidates.py -v`

Expected: candidate scoring and export tests pass.

## Task 4: Discovery Orchestration

**Files:**
- Create: `src/airesearch/discovery.py`
- Test: `tests/test_discovery.py`

- [ ] **Step 1: Write fake provider test**

Use a fake provider that returns three candidates. Verify `run_discovery` creates one `discovery_runs` row and stores only allowed candidates.

- [ ] **Step 2: Implement orchestration**

Implement:

- `DiscoveryProvider` protocol.
- `run_discovery(db_path, profile_name, providers, limit)`.

The function loads the profile from SQLite, calls providers, scores candidates, stores allowed rows, and records counts.

- [ ] **Step 3: Run discovery tests**

Run: `.venv/bin/python -m pytest tests/test_discovery.py -v`

Expected: discovery tests pass.

## Task 5: CLI Integration

**Files:**
- Modify: `src/airesearch/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add CLI tests**

Add tests for:

- `seed-profiles`
- `list-candidates`
- `export-candidates`

Use seeded fake candidate data, not network access.

- [ ] **Step 2: Implement CLI commands**

Add commands:

- `seed-profiles`
- `discover-candidates --profile <name> --limit <n>`
- `list-candidates --profile <name> --limit <n>`
- `export-candidates --profile <name> --limit <n> --out <path>`

- [ ] **Step 3: Run CLI tests**

Run: `.venv/bin/python -m pytest tests/test_cli.py -v`

Expected: CLI tests pass.

## Task 6: Verification And PLAN Update

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: Run full tests**

Run: `.venv/bin/python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Seed local profiles**

Run: `.venv/bin/python -m airesearch.cli seed-profiles`

Expected: output includes `profiles_seeded=5`.

- [ ] **Step 3: Show candidate status**

Run: `.venv/bin/python -m airesearch.cli status`

Expected: status includes candidate/profile counts after CLI status is extended.

- [ ] **Step 4: Update `PLAN.md`**

Record Stage 2B scope, implemented files, verification commands, and whether network discovery providers are implemented or still pending.

## Self-Review

- Spec coverage: The plan covers profile seeding, recency/exception policy, scoring, candidate storage, list/export commands, and no automatic paper download.
- Scope control: Google Scholar automation is excluded; network providers are isolated so source reliability issues do not affect the rest of the system.
- Type consistency: Public names are fixed as `ResearchProfile`, `CandidatePaper`, `score_candidate`, `is_candidate_allowed`, `seed_profiles`, `run_discovery`, `list_candidates`, and `export_candidates`.
