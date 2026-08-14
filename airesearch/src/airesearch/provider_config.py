from __future__ import annotations

from typing import Mapping


OPENCODE_BASE_ENV = "OPENCODE_GO_BASE_URL"
OPENCODE_KEY_ENV = "OPENCODE_GO_API_KEY"
OPENCODE_PROXY_ENV = "OPENCODE_GO_PROXY"


def api_root(value: str | None) -> str:
    normalized = str(value or "").strip().rstrip("/")
    lowered = normalized.casefold()
    for suffix in ("/chat/completions", "/responses"):
        if lowered.endswith(suffix):
            return normalized[: -len(suffix)].rstrip("/")
    return normalized


def chat_completions_url(value: str | None) -> str:
    root = api_root(value)
    return root + "/chat/completions" if root else ""


def responses_url(value: str | None) -> str:
    root = api_root(value)
    return root + "/responses" if root else ""


def opencode_base(env: Mapping[str, str]) -> str:
    return api_root(env.get(OPENCODE_BASE_ENV))


def opencode_key(env: Mapping[str, str]) -> str:
    return str(env.get(OPENCODE_KEY_ENV) or "").strip()


def opencode_proxy(env: Mapping[str, str]) -> str:
    return str(env.get(OPENCODE_PROXY_ENV) or "").strip()
