"""Compatibility shims: resolve airesearch-style settings from the unified config.

Each function keeps the SAME return contract as the legacy env-lookup chain it
replaces, so call sites change one import and keep their behavior. If
config/models.yaml cannot be loaded the caller falls back to the legacy chain.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

from .client import NiuLLM
from .errors import ConfigError, LLMError

_LLM: NiuLLM | None = None
_LOAD_FAILED = False


def _llm() -> NiuLLM | None:
    """Lazily load the unified config; None on failure (callers fall back)."""
    global _LLM, _LOAD_FAILED
    if _LOAD_FAILED:
        return None
    if _LLM is None:
        try:
            _LLM = NiuLLM.load()
        except ConfigError:
            _LOAD_FAILED = True
            return None
    return _LLM


def reset_for_tests() -> None:
    global _LLM, _LOAD_FAILED
    _LLM = None
    _LOAD_FAILED = False


def reload() -> None:
    """丢弃缓存的 NiuLLM，使下一次 resolve() 重新读 config/models.yaml。

    管理台/脚本改完 models.yaml 后必须调用：服务进程内缓存着旧路由表，
    否则表现为「管理台改了模型但要重启服务才生效」（2026-09-16 item 2）。
    """
    reset_for_tests()


def resolve(logic_model: str, env: Mapping[str, str] | None = None) -> tuple[str, str, str]:
    """Return (base_url, api_key, model) for a logic model, or raise LLMError.

    Prefer NIU_LLM_<NAME>_* env overrides when present so any single job can
    redirect its route without touching models.yaml.
    """
    values = env if env is not None else os.environ
    prefix = f"NIU_LLM_{logic_model.upper()}"
    manual = (
        values.get(f"{prefix}_BASE_URL"),
        values.get(f"{prefix}_API_KEY") or values.get(f"{prefix}_API_KEY_ENV"),
        values.get(f"{prefix}_MODEL"),
    )
    manual_url, manual_key, manual_model = (m or "" for m in manual)

    client = _llm()
    lm = client.config.model(logic_model)
    ep = client.config.endpoint_for(lm)
    base_url = manual_url or ep.base_url
    api_key = manual_key or client.config.resolve_key(ep)
    model = manual_model or lm.model
    return base_url, api_key, model


def logic_endpoint_style(logic_model: str) -> str:
    """Return 'chat_completions' or 'responses' for a logic model."""
    client = _llm()
    if client is None:
        raise ConfigError("models.yaml unavailable")
    return client.config.model(logic_model).style
