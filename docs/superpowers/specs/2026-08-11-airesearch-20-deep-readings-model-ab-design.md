# AIResearch 20-Paper Deep-Reading Model A/B Design

## Objective

Generate and publish evidence-grounded Chinese deep readings for 20 existing
AIResearch papers. Before the batch run, compare `deepseek-v4-pro` and
`gpt-5.6-luna` on the same two papers and use the better model for the remaining
18 papers.

The batch must preserve the current paper ingestion, layout v2, research fact,
formula, table, image selection, blog versioning, and static-site publishing
contracts.

## Current State

- The only published deep reading is `colavla`. Its five stored versions use
  `deepseek-v4-pro` and prompt version `paper_blog.zh_engineer.v1`.
- The production assistant uses OpenCode Go with `deepseek-v4-pro` through an
  OpenAI-compatible Chat Completions endpoint.
- Formula OCR separately uses `gpt-5.6-luna` through the OpenCode Go Responses
  endpoint and the local `http://127.0.0.1:7890` proxy.
- The blog provider supports Chat Completions but does not yet support Responses
  or fall back to the production `NIU_ASSISTANT_*` configuration.
- All 209 papers have completed layout v2 runs. The selected papers have Chinese
  artifacts and structured visual evidence. `omnivl-guard` is excluded from this
  batch because it currently lacks a `benchmark` research fact.

## Selected Papers

The two A/B papers are included in the final total of 20:

1. `what-if-world` - table-heavy benchmark paper and A/B sample
2. `world2vlm` - formula- and visual-heavy method paper and A/B sample
3. `world-action-models`
4. `world-model-self-distillation`
5. `2606_00269`
6. `3dthinkvla`
7. `actionmap`
8. `disco`
9. `latent-diffusion-policy`
10. `mpcot`
11. `multimodal-structure-learning`
12. `phail`
13. `simple`
14. `verispace`
15. `vla-os`
16. `physics-in-2-steps`
17. `vista`
18. `oscar`
19. `thinking-with-imagination`
20. `wbench`

## Model Integration

### DeepSeek Arm

- Model: `deepseek-v4-pro`
- Protocol: OpenAI-compatible Chat Completions
- Base URL source: blog-specific configuration first, then the existing
  `NIU_ASSISTANT_API_BASE`
- API key source: blog-specific configuration first, then the existing
  `NIU_ASSISTANT_API_KEY`

### Luna Arm

- Model: `gpt-5.6-luna`
- Protocol: OpenAI-compatible Responses API
- Endpoint source: explicit blog A/B configuration, using the current OpenCode
  Go Responses endpoint
- Proxy: `http://127.0.0.1:7890`
- API key: loaded from the existing protected `/etc` environment file at runtime

No secret value is written to source files, logs, generated artifacts, or the
database. Model, protocol, endpoint class, latency, retry count, and validation
results may be logged.

The Responses transport will normalize both string and structured response
content, extract the requested JSON object, and raise the existing
`BlogValidationError` for malformed or incomplete responses. Chat Completions
behavior remains backward compatible.

## Controlled A/B Procedure

For `what-if-world` and `world2vlm`, build the evidence pack once per source hash
and provide both models with identical:

- prompt version
- seven required sections
- target character count
- research facts and provenance-safe excerpts
- structured tables
- canonical formulas
- selected local image metadata
- source character budgets

Each model generates one complete version of each sample paper. Generation uses
the normal blog validation and version tables but does not rebuild or deploy the
public static site during the comparison. The four versions remain available as
an audit trail; the winning version is made current before final publication.

### Hard Gates

An A/B output is ineligible if any of these checks fail:

- provider request and JSON decoding succeed
- all seven required sections are present
- generated length satisfies the existing blog validator
- cited fact IDs and image IDs come from the supplied evidence pack
- papers with canonical equations contain at least two display-math blocks
- referenced local images exist and stay inside publishable paper assets
- no unresolved placeholder, replacement character, or raw local filesystem path
  appears in the output

### Weighted Score

- factual and numerical grounding: 35 points
- method, formula, and table explanation: 25 points
- seven-section coverage: 15 points
- Chinese technical writing quality: 15 points
- request success rate, retries, and latency: 10 points

The model with the higher mean score across both papers wins. If scores differ by
three points or fewer, use fewer validation failures first, then fewer retries,
then lower median latency as tie breakers. The decision and component scores are
saved in a non-secret JSON report.

## Batch Generation

A resumable batch runner generates the remaining 18 papers with the winning
model. It records one JSONL row per attempt with paper key, source hash, model,
status, version ID, word count, validation result, duration, and sanitized error.

The runner skips an already successful paper when its source hash, model, and
prompt version match. A failed paper is retried with bounded provider retries;
failure does not stop completed papers or publish a partial site. Existing blog
generation cache and versioning remain authoritative.

## Backup And Rollback

Only blog generation data changes during this operation. Before A/B generation,
create a timestamped backup containing:

- SQL/JSON exports of `paper_blog_posts`, `paper_blog_versions`, and
  `paper_blog_generation_cache`
- a manifest of existing blog asset paths and hashes for the 20 papers
- the selected paper list and pre-run current version IDs

This incremental backup avoids another full 568 MB database copy while the root
filesystem has about 1.2 GB free. Rollback restores the three blog tables,
removes only newly created blog assets listed by the run manifest, rebuilds the
site, and redeploys the previous state.

## Publishing

The public site is rebuilt only after all 20 papers have a validated winning-model
version. Publishing then:

1. exports the report bundle and `paper-blogs.json`
2. regenerates `exports/site-current`
3. deploys the static site through the existing deployment script
4. verifies the blog index and all 20 paper detail pages

If one or more papers still fail after bounded retries, keep the public site on
its previous version and report the failed paper keys. Do not publish a silently
partial 20-paper batch.

## Verification

Automated tests cover:

- Responses request construction and response parsing
- Chat Completions compatibility and production environment fallback
- secret redaction from errors and logs
- deterministic A/B scoring and tie breakers
- resumable batch behavior and failure isolation
- backup manifest completeness
- existing blog validation, versioning, and export behavior

Operational acceptance covers:

- focused and full AIResearch test suites
- workflow checks for all 20 papers
- database assertions for 20 published posts and correct current version/model
- static API and HTML checks for every selected paper
- formula, table, and local image presence on representative pages
- desktop and mobile Playwright checks for the two A/B samples plus at least
  three additional papers
- HTTP checks for the blog index and all 20 deployed detail URLs

## Documentation

Update `airesearch/SKILL.md`, `airesearch/DEVELOPMENT.md`, and
`docs/airesearch-api.md` with:

- the two supported blog protocols
- model and environment selection rules
- batch generation and resume procedure
- A/B report and run log locations
- backup, rollback, verification, and publishing commands

