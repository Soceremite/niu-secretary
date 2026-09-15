"""Error taxonomy for the unified LLM layer."""
from __future__ import annotations


class LLMError(Exception):
    """Base error for all unified LLM calls."""


class ConfigError(LLMError):
    """config/models.yaml missing, malformed, or references an undefined endpoint."""


class AuthenticationError(LLMError):
    """401/403 from the endpoint — API key missing or invalid."""


class RateLimitError(LLMError):
    """429 — rate limited after retries exhausted."""


class TimeoutError(LLMError):
    """Request exceeded the endpoint timeout."""


class BadResponseError(LLMError):
    """Endpoint returned an unparseable / structurally invalid payload."""
