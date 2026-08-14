# AIResearch Provider Environment Unification Design

## Goal

Use `/home/ubuntu/vibe_proj/niu-secretary/airesearch/.env` as the single runtime source for AI provider credentials used by Niu Secretary and AIResearch. Prevent service and batch jobs from selecting different OpenCode Go keys or endpoint forms.

## Configuration Boundary

`airesearch/.env` owns AI provider credentials and model routing. OpenCode Go has one root URL, one API key, and one optional proxy:

- `OPENCODE_GO_BASE_URL`
- `OPENCODE_GO_API_KEY`
- `OPENCODE_GO_PROXY`

Feature-specific variables select models and behavior, but do not duplicate the OpenCode credential. Existing non-OpenCode providers remain explicit feature-specific entries in the same file.

`/etc/niu-secretary-api.env` retains only service port, database path, administrator credentials, and session secrets. `/etc/niu-secretary-formula-ocr.env` no longer stores a duplicate provider key.

The project `.env` remains ignored by Git, is never exported to generated reports, and must retain mode `0600`.

## Runtime Loading

Interactive AIResearch commands continue to load `.env` through `airesearch/activate.sh`. The Niu Secretary API service starts through a checked shell wrapper that sources the same file before executing Python. Deep-reading batch runners source the same file directly.

The wrapper fails before starting Python when the unified OpenCode URL or key is absent. This makes a missing configuration visible in systemd instead of allowing a later provider call to choose an unrelated fallback.

## Endpoint Derivation

`OPENCODE_GO_BASE_URL` is always the API root, currently `https://opencode.ai/zen/go/v1`. Shared code derives protocol endpoints deterministically:

- Chat Completions: `<root>/chat/completions`
- Responses: `<root>/responses`

Supplying a full protocol endpoint is normalized back to the root before deriving the required endpoint. DeepSeek A/B uses Chat Completions. Luna fact retry, formula OCR, and the Luna A/B arm use Responses.

## Compatibility

Generic blog, fact, and OCR configuration keeps feature-specific overrides for non-OpenCode providers. When those overrides are absent, the code uses the unified OpenCode variables. Legacy `NIU_ASSISTANT_API_BASE`, `NIU_ASSISTANT_API_KEY`, and `AIRESEARCH_FORMULA_OCR_API_KEY` remain accepted temporarily in code but are removed from production configuration.

## Migration And Verification

Before migration, copy the project `.env` and both `/etc` environment files into a root-readable timestamped backup directory. Move the existing OpenCode key without printing it. Remove duplicate AI variables from `/etc`, install the service wrapper override, reload systemd, and restart the API.

Verification checks Git ignore state, file permissions, variable names, endpoint derivation unit tests, API service health, and a minimal OpenCode request. A `401 CreditsError` is an upstream billing failure and still proves the service found and used the unified credentials; a missing-variable error is a migration failure.
