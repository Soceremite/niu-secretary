# AIResearch Provider Environment Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `airesearch/.env` the single source for OpenCode Go credentials across API services, OCR, fact extraction, and deep-reading batches.

**Architecture:** Add a small provider configuration module that normalizes one OpenCode API root and derives protocol endpoints. Runtime wrappers source the ignored project `.env`; `/etc` retains only system and administrator settings.

**Tech Stack:** Bash, systemd, Python 3, pytest, OpenAI-compatible Chat Completions and Responses APIs.

---

### Task 1: Provider Endpoint Contract

**Files:**
- Create: `airesearch/src/airesearch/provider_config.py`
- Create: `airesearch/tests/test_provider_config.py`

- [ ] Add tests proving root, `/responses`, and `/chat/completions` inputs normalize to one root.
- [ ] Add `api_root`, `chat_completions_url`, and `responses_url` helpers.
- [ ] Run `PYTHONPATH=airesearch/src airesearch/.venv/bin/pytest -q airesearch/tests/test_provider_config.py` and require all tests to pass.

### Task 2: Provider Consumers

**Files:**
- Modify: `airesearch/src/airesearch/blog_batch.py`
- Modify: `airesearch/src/airesearch/paper_blog.py`
- Modify: `airesearch/src/airesearch/formula_ocr.py`
- Modify: `airesearch/src/airesearch/fact_extraction.py`
- Modify: `airesearch/src/airesearch/admin_server.py`
- Modify: `server/assistant.py`
- Test: `airesearch/tests/test_blog_batch.py`
- Test: `airesearch/tests/test_paper_blog.py`
- Test: `airesearch/tests/test_formula_ocr.py`
- Test: `airesearch/tests/test_fact_extraction.py`

- [ ] Add failing tests for `OPENCODE_GO_BASE_URL`, `OPENCODE_GO_API_KEY`, and proxy fallback.
- [ ] Route named DeepSeek/Luna arms through the unified credential and protocol-specific endpoint.
- [ ] Add unified fallback to generic blog, fact extraction, formula OCR, admin generation, and assistant configuration.
- [ ] Run focused provider tests and require all tests to pass.

### Task 3: Runtime Loading

**Files:**
- Create: `scripts/run-niu-secretary-api.sh`
- Create: `deploy/niu-secretary-api-airesearch-env.conf`
- Modify: `airesearch/scripts/run_deep_reading_batch_20260812_40.sh`
- Modify: `airesearch/activate.sh`

- [ ] Make each entrypoint source the canonical `airesearch/.env` path.
- [ ] Validate required OpenCode variables before launching the API or batch.
- [ ] Use the unified key name in fact retry and derive its Responses endpoint from the root.
- [ ] Run `bash -n` on every changed shell script.

### Task 4: Protected Configuration Migration

**Files:**
- Modify locally, ignored: `airesearch/.env`
- Modify on host: `/etc/niu-secretary-api.env`
- Replace on host: `/etc/niu-secretary-formula-ocr.env`
- Install on host: `/etc/systemd/system/niu-secretary-api.service.d/airesearch-env.conf`

- [ ] Back up all three existing files without printing secrets.
- [ ] Add the unified OpenCode root/key/proxy and feature model variables to `airesearch/.env`.
- [ ] Remove provider credentials from `/etc`, retaining system and administrator variables.
- [ ] Enforce `0600` on all credential-bearing files and reload systemd.

### Task 5: Acceptance

**Files:**
- Modify: `airesearch/.env.example`
- Modify: `config/niu-secretary-api.env.example`
- Modify: `airesearch/SKILL.md`
- Modify: `airesearch/DEVELOPMENT.md`
- Modify: `docs/airesearch-api.md`

- [ ] Document the canonical variables and endpoint derivation.
- [ ] Run focused and full affected test suites.
- [ ] Restart `niu-secretary-api.service` and require `/api/health` to return HTTP 200.
- [ ] Inspect the service environment by variable name without printing secrets.
- [ ] Send a minimal OpenCode request and classify `401 CreditsError` as upstream billing rather than missing configuration.
