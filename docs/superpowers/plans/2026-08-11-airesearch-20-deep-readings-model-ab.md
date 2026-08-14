# AIResearch 20-Paper Deep-Reading Model A/B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare DeepSeek and Luna on two grounded paper deep readings, select the stronger model, and publish validated deep readings for 20 existing papers.

**Architecture:** Extend the existing `OpenAICompatibleBlogProvider` with a Responses transport while preserving Chat Completions. Add a focused batch module that performs evidence preflight, selected-table backup, deterministic scoring, resumable generation, and sanitized run logging; expose it through one operational script. Generate against the production database without rebuilding the public site until all 20 papers pass acceptance.

**Tech Stack:** Python 3.11, SQLite, urllib, pytest, existing AIResearch blog/layout/report pipeline, OpenCode Go Chat Completions and Responses APIs, Playwright.

---

## File Map

- Modify `airesearch/src/airesearch/paper_blog.py`: Responses JSON transport, protocol selection, production environment fallback, and sanitized provider failures.
- Create `airesearch/src/airesearch/blog_batch.py`: model-arm configuration, evidence preflight, incremental backup, scoring, A/B comparison, resumable batch generation, and rollback.
- Create `airesearch/scripts/generate_deep_readings.py`: command-line entry point for preflight, backup, A/B, batch, score, and restore operations.
- Modify `airesearch/tests/test_paper_blog.py`: transport and environment regression tests.
- Create `airesearch/tests/test_blog_batch.py`: backup, scoring, resume, and failure-isolation tests.
- Modify `config/niu-secretary-api.env.example`: document non-secret blog protocol variables.
- Modify `airesearch/SKILL.md`, `airesearch/DEVELOPMENT.md`, and `docs/airesearch-api.md`: operating and API documentation.

## Task 1: Add Responses Transport Tests

**Files:**
- Modify: `airesearch/tests/test_paper_blog.py`
- Test: `airesearch/tests/test_paper_blog.py`

- [ ] **Step 1: Add imports and a recording Responses HTTP callable**

Add `OpenAIResponsesBlogTransport` to the existing imports and add this helper near `RecordingOpenAITransport`:

```python
class RecordingResponsesHTTP:
    def __init__(self, response: dict[str, object]):
        self.response = response
        self.requests: list[dict[str, object]] = []

    def __call__(
        self,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout: float,
        proxy_url: str,
    ) -> dict[str, object]:
        self.requests.append(
            {
                "endpoint": endpoint,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
                "proxy_url": proxy_url,
            }
        )
        return self.response
```

- [ ] **Step 2: Add Responses request and parsing tests**

Add tests that assert endpoint normalization, `input_text` message conversion,
Bearer authentication, proxy propagation, and output extraction:

```python
def test_responses_blog_transport_builds_request_and_parses_output():
    http = RecordingResponsesHTTP(
        {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": '{"title":"测试","sections":[]}'},
                    ]
                }
            ]
        }
    )
    transport = OpenAIResponsesBlogTransport(
        proxy_url="http://127.0.0.1:7890",
        http_transport=http,
    )

    result = transport.complete_json(
        model="gpt-5.6-luna",
        base_url="https://opencode.ai/zen/go/v1/responses",
        api_key="secret-test-key",
        messages=[{"role": "system", "content": "Return JSON only."}],
        max_output_tokens=4000,
    )

    assert result == {"title": "测试", "sections": []}
    request = http.requests[0]
    assert request["endpoint"] == "https://opencode.ai/zen/go/v1/responses"
    assert request["proxy_url"] == "http://127.0.0.1:7890"
    assert request["payload"]["model"] == "gpt-5.6-luna"
    assert request["payload"]["input"][0]["content"][0] == {
        "type": "input_text",
        "text": "Return JSON only.",
    }
```

Also cover `output_text` at the top level, fenced JSON, malformed JSON, empty
output, and an endpoint supplied as the `/v1` base.

- [ ] **Step 3: Add environment precedence and redaction tests**

Assert this precedence:

```text
AIRESEARCH_BLOG_* -> requested api_key_env -> OPENAI/TRANSLATE -> NIU_ASSISTANT_* -> defaults
```

Verify `AIRESEARCH_BLOG_API_STYLE=responses` selects the Responses transport,
`AIRESEARCH_BLOG_PROXY` reaches it, and a provider error containing the configured
key is rendered with `[REDACTED]` instead of the key.

- [ ] **Step 4: Run focused tests and confirm failure**

Run:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest \
  airesearch/tests/test_paper_blog.py \
  -k 'responses_blog or production_assistant or provider_error_redacts' -q
```

Expected: collection or assertion failures because the Responses transport and
fallback behavior do not exist yet.

## Task 2: Implement Responses And Environment Selection

**Files:**
- Modify: `airesearch/src/airesearch/paper_blog.py`
- Modify: `airesearch/src/airesearch/admin_server.py`
- Test: `airesearch/tests/test_paper_blog.py`

- [ ] **Step 1: Add shared response and sanitization helpers**

Add helpers before the transport classes:

```python
def _strip_json_fence(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    return re.sub(r"\s*```$", "", text).strip()


def _responses_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return str(payload["output_text"])
    output = payload.get("output")
    if not isinstance(output, list):
        return ""
    return "".join(
        str(content.get("text") or "")
        for item in output
        if isinstance(item, dict)
        for content in (item.get("content") or [])
        if isinstance(content, dict) and content.get("type") in {"output_text", "text"}
    )


def _redact_provider_detail(value: str, api_key: str) -> str:
    detail = str(value or "")[:800]
    return detail.replace(api_key, "[REDACTED]") if api_key else detail
```

- [ ] **Step 2: Implement the Responses HTTP transport**

Add `OpenAIResponsesBlogTransport` with the same `complete_json` signature as the
current Chat Completions transport. Its constructor accepts `proxy_url`,
`timeout_seconds`, and an optional five-argument `http_transport` callable. The
default HTTP function uses `urllib.request.ProxyHandler` only when `proxy_url` is
non-empty.

Use this request shape:

```python
payload = {
    "model": model,
    "input": [
        {
            "role": message["role"],
            "content": [{"type": "input_text", "text": str(message["content"])}],
        }
        for message in messages
    ],
    "max_output_tokens": max_output_tokens,
}
```

Normalize a `/v1` base to `/v1/responses`, preserve an already complete
`/responses` endpoint, parse `_responses_output_text`, strip a JSON fence, and
require the decoded result to be an object.

- [ ] **Step 3: Extend provider environment resolution**

Extend `OpenAICompatibleBlogProvider.from_env` with optional `api_style` and
`proxy_url` parameters. Apply this resolution order:

```python
resolved_model = (
    model
    or os.environ.get("AIRESEARCH_BLOG_MODEL")
    or os.environ.get("NIU_ASSISTANT_MODEL")
    or DEFAULT_BLOG_MODEL
)
resolved_base_url = (
    base_url
    or os.environ.get("AIRESEARCH_BLOG_BASE_URL")
    or os.environ.get("TRANSLATE_BASE_URL")
    or os.environ.get("OPENAI_BASE_URL")
    or os.environ.get("NIU_ASSISTANT_API_BASE")
    or DEFAULT_BLOG_BASE_URL
)
```

Use `NIU_ASSISTANT_API_KEY` only after the existing blog, explicit key-env,
OpenAI, and translation key sources. Infer `responses` when the endpoint ends in
`/responses`; otherwise default to `chat_completions`. An explicitly injected
transport always wins.

- [ ] **Step 4: Pass trusted protocol options from the admin server**

In `_blog_provider_from_options`, read protocol, endpoint, and proxy only from
server environment variables, not request payload URL fields:

```python
api_style = os.environ.get("AIRESEARCH_BLOG_API_STYLE", "").strip()
proxy_url = os.environ.get("AIRESEARCH_BLOG_PROXY", "").strip()
```

Pass them to `from_env` and update the monkeypatched test signature accordingly.

- [ ] **Step 5: Run focused and existing blog tests**

Run:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest \
  airesearch/tests/test_paper_blog.py -q
```

Expected: all paper blog tests pass.

## Task 3: Add Batch Preflight And Model Arms

**Files:**
- Create: `airesearch/src/airesearch/blog_batch.py`
- Create: `airesearch/tests/test_blog_batch.py`

- [ ] **Step 1: Write model-arm configuration tests**

Test a frozen configuration object with these fields:

```python
@dataclass(frozen=True)
class BlogModelArm:
    name: str
    model: str
    api_style: str
    base_url: str
    api_key_env: str
    proxy_url: str = ""
```

Assert `model_arm_from_env("deepseek", env)` resolves from `NIU_ASSISTANT_*`, and
`model_arm_from_env("luna", env)` resolves from `AIRESEARCH_FORMULA_OCR_*` with
the OCR proxy. Assert missing model, base URL, or key raises a sanitized
`BlogBatchError` naming only the missing environment variable.

- [ ] **Step 2: Write evidence preflight tests**

Define `preflight_papers(db_path, paper_keys)` and assert every returned row has:

```python
{
    "paper_key": "...",
    "source_hash": "...",
    "fact_types": ["benchmark", "claim", "dataset", "limitation", "method"],
    "fact_count": 5,
    "equation_count": 2,
    "image_count": 1,
    "structured_table_chars": 100,
    "ready": True,
    "errors": [],
}
```

The ready gate requires the paper to exist, summary or TLDR grounding, all five
fact types, at least one selected local image, and a completed layout run.
Equations and tables are measured and reported but are not universally required.

- [ ] **Step 3: Implement model arms and preflight**

Use `build_blog_evidence_pack` and existing DB tables. Implement
`provider_for_arm(arm, env)` by reading the key value at runtime and constructing
`OpenAICompatibleBlogProvider` with either `OpenAICompatibleBlogTransport` or
`OpenAIResponsesBlogTransport`. Never store the key on the arm object or include
it in `repr`, JSON, exceptions, or logs.

- [ ] **Step 4: Run the new tests**

Run:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest \
  airesearch/tests/test_blog_batch.py -k 'model_arm or preflight' -q
```

Expected: all selected tests pass.

## Task 4: Add Incremental Backup And Restore

**Files:**
- Modify: `airesearch/src/airesearch/blog_batch.py`
- Modify: `airesearch/tests/test_blog_batch.py`

- [ ] **Step 1: Write selected-row backup tests**

Create existing blog rows for one selected fixture paper, run
`backup_blog_state`, and assert the backup directory contains:

```text
manifest.json
paper_blog_posts.json
paper_blog_versions.json
paper_blog_generation_cache.json
assets.json
```

Assert the manifest contains database path, UTC timestamp, selected paper keys,
current version IDs, table row counts, and SHA-256 hashes of every backup file.
Assert no environment key value occurs in any backup file.

- [ ] **Step 2: Write restore tests**

After backup, insert a new selected-paper version and a new file below that
paper's `blog-assets` directory. Call `restore_blog_state` and assert:

- pre-backup selected rows are restored exactly
- post-backup selected rows are removed
- the newly created asset is removed
- pre-existing assets and non-selected blog rows remain unchanged

- [ ] **Step 3: Implement backup and restore**

Use column-name JSON objects obtained from `sqlite3.Row`; write atomically through
`path.with_suffix(path.suffix + ".tmp")` and `Path.replace`. Restore in one SQLite
transaction, deleting selected rows in foreign-key-safe order and reinserting
versions before posts. Asset rollback compares the current selected-paper asset
manifest with the pre-run manifest and deletes only newly introduced paths below
the recorded paper directory.

- [ ] **Step 4: Run backup tests**

Run:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest \
  airesearch/tests/test_blog_batch.py -k 'backup or restore' -q
```

Expected: all selected tests pass.

## Task 5: Add Deterministic Audit And A/B Selection

**Files:**
- Modify: `airesearch/src/airesearch/blog_batch.py`
- Modify: `airesearch/tests/test_blog_batch.py`

- [ ] **Step 1: Write hard-gate audit tests**

Define `audit_blog_version(db_path, paper_key, version_id, duration_seconds)`.
Test rejection for missing sections, too-short text, invalid local image paths,
raw absolute paths, replacement characters, unresolved placeholder markers, and
fewer than two display math blocks when the evidence pack has equations.

- [ ] **Step 2: Write scoring and tie-break tests**

Return this stable score contract:

```python
{
    "eligible": True,
    "hard_gate_errors": [],
    "score": 91.5,
    "components": {
        "grounding": 33.0,
        "technical_evidence": 23.5,
        "section_coverage": 15.0,
        "chinese_quality": 12.0,
        "reliability": 8.0,
    },
    "metrics": {},
}
```

Grounding measures valid cited-fact coverage and the ratio of prose numeric
tokens present in supplied facts/artifacts. Technical evidence measures formula
blocks, table/image evidence use, and method/benchmark fact coverage. Chinese
quality penalizes repeated paragraphs, replacement characters, raw HTML, and
extreme non-Chinese ratio. Reliability uses duration and `llm_calls` without
rewarding a model for omitting content.

Test `select_ab_winner(report)` with score, hard-gate, retry, and latency tie
breakers exactly as specified in the design.

- [ ] **Step 3: Implement audit and scoring**

Keep all scoring functions pure except the version/evidence loader. Round public
component scores to two decimals, save raw metrics, and include the formula for
each component in `scoring_version = "deep-reading-ab-v1"` so results remain
auditable.

- [ ] **Step 4: Run scoring tests**

Run:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest \
  airesearch/tests/test_blog_batch.py -k 'audit or score or winner' -q
```

Expected: all selected tests pass.

## Task 6: Add Resumable A/B And Batch Runner

**Files:**
- Modify: `airesearch/src/airesearch/blog_batch.py`
- Modify: `airesearch/tests/test_blog_batch.py`
- Create: `airesearch/scripts/generate_deep_readings.py`

- [ ] **Step 1: Write resume and isolation tests**

Inject fixture providers into `run_ab` and `run_batch`. Assert:

- A/B runs both arms for both sample papers
- an arm failure is logged and does not erase a successful arm
- the public site export is never called by the runner
- a completed JSONL row with matching paper/source/model/prompt skips regeneration
- a changed source hash causes regeneration
- one paper failure does not stop subsequent papers
- final batch status is `completed` only when every requested paper has a valid
  current version for the winning model

- [ ] **Step 2: Implement sanitized JSONL logging**

Use one append-only row per event:

```python
{
    "event": "paper",
    "paper_key": "world2vlm",
    "model_arm": "luna",
    "model": "gpt-5.6-luna",
    "source_hash": "...",
    "prompt_version": "paper_blog.zh_engineer.v1",
    "status": "completed",
    "version_id": 1,
    "version_number": 1,
    "word_count": 7000,
    "duration_seconds": 90.0,
    "audit": {},
    "created_at": "...",
}
```

Sanitize exceptions against all configured secret values before writing.

- [ ] **Step 3: Implement `run_ab` and `run_batch`**

`run_ab` calls `generate_and_publish_blog` with `force=True` and target 5000 for
each arm/sample pair, audits each resulting version, writes `ab-report.json`, and
selects a winner only when both sample papers have an eligible output from that
arm. It updates the two current versions to the winning arm using existing
rollback/version APIs without rebuilding the site.

`run_batch` processes the remaining paper list sequentially, uses the existing
provider retry behavior, resumes from JSONL, and writes `batch-summary.json`.
Neither function exports or deploys the static site.

- [ ] **Step 4: Add the operational CLI**

Expose these commands:

```text
preflight --db --paper-list --out
backup    --db --paper-list --out
ab        --db --paper-list --out --target-chars
batch     --db --paper-list --out --model-arm --target-chars
restore   --db --backup-dir
```

The script imports only `airesearch.blog_batch`, exits `0` on complete success,
`2` on preflight or partial batch failure, and never accepts API keys as command
line arguments.

- [ ] **Step 5: Run batch tests**

Run:

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest \
  airesearch/tests/test_blog_batch.py -q
```

Expected: all batch tests pass.

## Task 7: Update Configuration And Documentation

**Files:**
- Modify: `config/niu-secretary-api.env.example`
- Modify: `airesearch/SKILL.md`
- Modify: `airesearch/DEVELOPMENT.md`
- Modify: `docs/airesearch-api.md`

- [ ] **Step 1: Document blog environment variables**

Add non-secret examples:

```dotenv
# AIRESEARCH_BLOG_API_STYLE=chat_completions
# AIRESEARCH_BLOG_BASE_URL=https://provider.example/v1
# AIRESEARCH_BLOG_MODEL=deepseek-v4-pro
# AIRESEARCH_BLOG_API_KEY=replace-with-local-secret
# AIRESEARCH_BLOG_PROXY=http://127.0.0.1:7890
```

Document that DeepSeek may fall back to `NIU_ASSISTANT_*`, while the A/B runner's
Luna arm explicitly reads protected formula OCR configuration. Do not advise
placing production keys in the repository example.

- [ ] **Step 2: Document batch operation and API integration**

Add the selected 20-paper workflow, preflight/backup/A/B/batch/restore commands,
run artifact schemas, one-time site rebuild requirement, and admin single-paper
behavior. State that `gpt-5.6-luna` is not the default blog model unless selected
by A/B or configured explicitly.

- [ ] **Step 3: Check documentation consistency**

Run:

```bash
rg -n "AIRESEARCH_BLOG_|gpt-5.6-luna|deepseek-v4-pro|generate_deep_readings" \
  config/niu-secretary-api.env.example airesearch/SKILL.md \
  airesearch/DEVELOPMENT.md docs/airesearch-api.md
```

Expected: model roles, endpoints, secret handling, and commands agree across all
four files.

## Task 8: Run Code Verification

**Files:**
- Test: `airesearch/tests/test_paper_blog.py`
- Test: `airesearch/tests/test_blog_batch.py`
- Test: complete `airesearch/tests/`

- [ ] **Step 1: Run focused tests**

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest \
  airesearch/tests/test_paper_blog.py \
  airesearch/tests/test_blog_batch.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run static checks**

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m compileall -q \
  airesearch/src/airesearch airesearch/scripts/generate_deep_readings.py
git diff --check
```

Expected: both commands exit `0`.

- [ ] **Step 3: Run the complete suite**

```bash
PYTHONPATH=airesearch/src airesearch/.venv/bin/python -m pytest airesearch/tests -q
```

Expected: all existing and new tests pass.

## Task 9: Run Production Preflight, Backup, And A/B

**Files:**
- Runtime DB: `airesearch/data/airesearch.sqlite3`
- Runtime outputs: `backups/airesearch-deep-readings-20260811/`

- [ ] **Step 1: Create the exact paper list**

Create `backups/airesearch-deep-readings-20260811/papers.txt` containing the 20
paper keys from the approved design, one per line, with `what-if-world` and
`world2vlm` first.

- [ ] **Step 2: Run production preflight**

```bash
sudo bash -lc 'set -a; source /etc/niu-secretary-api.env; source /etc/niu-secretary-formula-ocr.env; set +a; \
PYTHONPATH=/home/ubuntu/vibe_proj/niu-secretary/airesearch/src \
/home/ubuntu/vibe_proj/niu-secretary/airesearch/.venv/bin/python \
/home/ubuntu/vibe_proj/niu-secretary/airesearch/scripts/generate_deep_readings.py \
preflight --db /home/ubuntu/vibe_proj/niu-secretary/airesearch/data/airesearch.sqlite3 \
--paper-list /home/ubuntu/vibe_proj/niu-secretary/backups/airesearch-deep-readings-20260811/papers.txt \
--out /home/ubuntu/vibe_proj/niu-secretary/backups/airesearch-deep-readings-20260811'
```

Expected: 20 ready, zero errors.

- [ ] **Step 3: Create and verify incremental backup**

Run the same script with `backup`, then verify manifest hashes, permissions, and
free disk space. Expected backup size is small relative to a full database copy,
and available disk must remain above 750 MB before model calls begin.

- [ ] **Step 4: Run the two-paper A/B**

Run `ab` with target 5000. Wait for completion, inspect all four sanitized log
rows, validate the four versions, and review the generated Markdown for
unsupported numbers, formula explanation, table interpretation, repetition, and
raw path leakage.

- [ ] **Step 5: Confirm and record the winner**

Verify `ab-report.json` includes both component and tie-break metrics. Record the
winning model arm in `winner.json`; verify the current versions for both sample
papers point to that arm. Do not rebuild or deploy the static site yet.

## Task 10: Generate The Remaining 18 Papers

**Files:**
- Runtime outputs: `backups/airesearch-deep-readings-20260811/batch.jsonl`
- Runtime outputs: `backups/airesearch-deep-readings-20260811/batch-summary.json`

- [ ] **Step 1: Run the resumable batch**

Invoke `batch` with the selected winner and target 5000. Keep the process attached
until it completes; if interrupted, rerun the identical command and verify it
skips matching completed rows.

- [ ] **Step 2: Validate database completion**

Assert all 20 selected keys have a published current post using the winning model,
all current version IDs resolve, all word counts are at least 3000 Chinese
characters, every paper with equations has at least two display math blocks, and
the summary reports zero failures.

- [ ] **Step 3: Run workflow checks before publishing**

Run `workflow-check` for all 20 against the current export. The deep-reading public
check is expected to remain stale until rebuild; every database, fact, Chinese,
layout, image, formula, and table check must already pass. Record results in the
run directory.

## Task 11: Build, Deploy, And Verify The Complete Site

**Files:**
- Generated: `airesearch/exports/mvp-current/bundle/`
- Generated: `airesearch/exports/site-current/`

- [ ] **Step 1: Export and regenerate once**

Use the existing report bundle and site generation commands, then run the existing
deployment script. Confirm the deploy script creates its normal static snapshot.

- [ ] **Step 2: Run all 20 workflow checks**

Expected: 13/13 checks pass for every selected paper, including `blog.deep_reading`,
public static API, and public HTML.

- [ ] **Step 3: Run HTTP acceptance**

Verify HTTP `200` for `/niu-secretary/airesearch/blogs/index.html` and every one of
the 20 `/niu-secretary/airesearch/papers/<paper-key>.html` URLs. Confirm the blog
index exposes 21 total published deep readings, including the existing `colavla`.

- [ ] **Step 4: Run Playwright visual checks**

Inspect desktop and mobile for `what-if-world`, `world2vlm`,
`world-model-self-distillation`, `2606_00269`, and `wbench`. Assert no horizontal
overflow, no failed local images, no raw LaTeX outside MathJax containers, usable
table overflow, visible deep-reading navigation, and external paper/GitHub links
opening in a new tab. Save screenshots and measurements in the run directory.

- [ ] **Step 5: Save final run summary**

Write `final-summary.json` with model winner, 20 paper keys, version IDs, word
counts, test results, workflow totals, deployment snapshot, HTTP results, and
Playwright artifact paths. Exclude environment values and local secret paths.

