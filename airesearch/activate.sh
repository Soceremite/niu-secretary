#!/usr/bin/env bash
set -a
source /home/ubuntu/.openclaw/workspace/niu-secretary/airesearch/.env
set +a

_airesearch_litellm_models() {
  AIRESEARCH_EFFECTIVE_LLM_MODEL="${AIRESEARCH_LLM_MODEL:-$PAPERPIPE_LLM_MODEL}"
  AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL="${AIRESEARCH_EMBEDDING_MODEL:-$PAPERPIPE_EMBEDDING_MODEL}"
  case "$AIRESEARCH_EFFECTIVE_LLM_MODEL" in */*) ;; *) AIRESEARCH_EFFECTIVE_LLM_MODEL="openai/$AIRESEARCH_EFFECTIVE_LLM_MODEL";; esac
  case "$AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL" in */*) ;; *) AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL="openai/$AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL";; esac
  export AIRESEARCH_EFFECTIVE_LLM_MODEL
  export AIRESEARCH_EFFECTIVE_EMBEDDING_MODEL
}

_airesearch_llm_config_json() {
  printf '{"model_list":[{"model_name":"%s","litellm_params":{"model":"%s","api_base":"%s","api_key":"%s","custom_llm_provider":"openai"}}]}' \
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
