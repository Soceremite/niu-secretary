#!/usr/bin/env bash
set -a
source /home/ubuntu/vibe_proj/niu-secretary/airesearch/.env
set +a

# litellm 调用记账（2026-09-16）：papi/paperpipe 内部直接用 litellm、不经过 niu_core，
# 通过 sitecustomize 把回调挂上，使其调用也出现在管理台「API 用量」页。
# 只在看起来是 papi 调用时生效（否则会给每条 python 命令加 litellm 启动开销）。
_AIRESEARCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$_AIRESEARCH_DIR/tools:$_AIRESEARCH_DIR/papi_hooks:${PYTHONPATH:-}"

_airesearch_litellm_models() {
  # 2026-09-16：papi 的 LLM/embedding 配置改由 config/models.yaml（管理台可改）决定。
  # 原先依赖 AIRESEARCH_LLM_BASE_URL / AIRESEARCH_LLM_API_KEY，这两个变量在 .env 里
  # 从来没有值 → 生成的 litellm 配置是空的（model=""、key=""），papi 的 summary/tldr/tags
  # 因此长期不可用，且完全绕开管理台。
  local repo_root resolved
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  local py="$repo_root/airesearch/.venv/bin/python"
  [ -x "$py" ] || py="python3"
  resolved="$("$py" - <<PY
import sys
sys.path.insert(0, "$repo_root")
from niu_core.llm_client import compat
for name in ("blog", "embed"):          # blog=长文生成（summary/tldr/tags），embed=向量
    try:
        base, key, model = compat.resolve(name)
    except Exception:
        base = key = model = ""
    print("\t".join((base or "", key or "", model or "")))
PY
)"
  AIRESEARCH_LLM_BASE_URL="$(printf '%s\n' "$resolved" | sed -n 1p | cut -f1)"
  AIRESEARCH_LLM_API_KEY="$(printf '%s\n' "$resolved" | sed -n 1p | cut -f2)"
  AIRESEARCH_EFFECTIVE_LLM_MODEL="$(printf '%s\n' "$resolved" | sed -n 1p | cut -f3)"
  AIRESEARCH_EMBEDDING_BASE_URL="$(printf '%s\n' "$resolved" | sed -n 2p | cut -f1)"
  AIRESEARCH_EMBEDDING_API_KEY="$(printf '%s\n' "$resolved" | sed -n 2p | cut -f2)"
  AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL="$(printf '%s\n' "$resolved" | sed -n 2p | cut -f3)"
  export AIRESEARCH_LLM_BASE_URL AIRESEARCH_LLM_API_KEY
  case "$AIRESEARCH_EFFECTIVE_LLM_MODEL" in */*) ;; *) AIRESEARCH_EFFECTIVE_LLM_MODEL="openai/$AIRESEARCH_EFFECTIVE_LLM_MODEL";; esac
  case "$AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL" in */*) ;; *) AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL="openai/$AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL";; esac
  export AIRESEARCH_EFFECTIVE_LLM_MODEL
  export AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL
}

_airesearch_llm_config_json() {
  # OpenCode relay 硬要求（2026-09-16）：litellm 默认 UA 会被 Cloudflare 拦（403），
  # 且缺 x-opencode-session 会被拒（400 MissingSessionID）→ 必须显式带上这两个头。
  # 对其它服务商这两个头无副作用。
  printf '{"model_list":[{"model_name":"%s","litellm_params":{"model":"%s","api_base":"%s","api_key":"%s","custom_llm_provider":"openai","extra_headers":{"User-Agent":"NiuSecretary-LLM/1.0 (AIResearch)","x-opencode-session":"niu-airesearch-papi"}}}]}' \
    "$AIRESEARCH_EFFECTIVE_LLM_MODEL" \
    "$AIRESEARCH_EFFECTIVE_LLM_MODEL" \
    "$AIRESEARCH_LLM_BASE_URL" \
    "$AIRESEARCH_LLM_API_KEY"
}

_airesearch_embedding_config_json() {
  printf '{"kwargs":{"api_base":"%s","api_key":"%s","custom_llm_provider":"openai","encoding_format":"float"}}' \
    "$AIRESEARCH_EMBEDDING_BASE_URL" \
    "$AIRESEARCH_EMBEDDING_API_KEY"
}

airesearch_papi_index() {
  _airesearch_litellm_models
  export OPENAI_API_KEY="$AIRESEARCH_LLM_API_KEY"
  export OPENAI_API_BASE="$AIRESEARCH_LLM_BASE_URL"
  local llm_config embedding_config
  llm_config="$(_airesearch_llm_config_json)"
  embedding_config="$(_airesearch_embedding_config_json)"
  papi index --backend pqa --pqa-retry-failed \
    --pqa-llm "$AIRESEARCH_EFFECTIVE_LLM_MODEL" \
    --pqa-embedding "$AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL" \
    --llm_config "$llm_config" \
    --summary_llm_config "$llm_config" \
    --embedding_config "$embedding_config"
}

airesearch_papi_ask() {
  _airesearch_litellm_models
  export OPENAI_API_KEY="$AIRESEARCH_LLM_API_KEY"
  export OPENAI_API_BASE="$AIRESEARCH_LLM_BASE_URL"
  local llm_config embedding_config
  llm_config="$(_airesearch_llm_config_json)"
  embedding_config="$(_airesearch_embedding_config_json)"
  papi ask "$1" --pqa-retry-failed \
    --pqa-llm "$AIRESEARCH_EFFECTIVE_LLM_MODEL" \
    --pqa-summary-llm "$AIRESEARCH_EFFECTIVE_LLM_MODEL" \
    --pqa-embedding "$AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL" \
    --llm_config "$llm_config" \
    --summary_llm_config "$llm_config" \
    --agent.agent_llm "$AIRESEARCH_EFFECTIVE_LLM_MODEL" \
    --agent.agent_llm_config "$llm_config" \
    --embedding_config "$embedding_config"
}
