"""niu_core.llm — Niu Secretary unified LLM gateway client.

Exposes a thin layer over 「逻辑模型」defined in config/models.yaml:
callers name a purpose (content / vision / blog / ...), the config resolves
endpoint + real model API key (from env) + fallback chain.

Public API::

    from niu_core.llm import NiuLLM

    llm = NiuLLM.load()
    resp = llm.chat("content", messages)
    vecs = llm.embed("embed", ["text"])
    r    = llm.vision("vision", "https://...", "描述这张图")
"""

from .client import NiuLLM, LLMResponse, KeyPool
from .config import LLMConfig, LogicModel, EndpointConfig
from .errors import (
    LLMError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    BadResponseError,
    ConfigError,
)

__all__ = [
    "NiuLLM",
    "LLMResponse",
    "LLMConfig",
    "LogicModel",
    "EndpointConfig",
    "LLMError",
    "RateLimitError",
    "AuthenticationError",
    "TimeoutError",
    "BadResponseError",
    "ConfigError",
]
