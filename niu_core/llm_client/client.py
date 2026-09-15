"""HTTP client for the unified LLM layer.

Uses only stdlib (urllib) plus optional httpx passthrough — keep the platform
dependency footprint zero; every module already has PyYAML available.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from .config import LLMConfig, EndpointConfig, LogicModel, FallbackEntry
from .errors import (
    AuthenticationError,
    BadResponseError,
    LLMError,
    RateLimitError,
    TimeoutError as LLMTimeoutError,
)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    endpoint: str
    usage: Dict[str, Any]
    raw: Dict[str, Any]
    latency_ms: int
    via_fallback: bool = False


class KeyPool:
    """Tracks consecutive failures per endpoint for cooldown/coalescing."""

    def __init__(self) -> None:
        self._fail_counts: Dict[str, int] = {}
        self._cooldown_until: Dict[str, float] = {}

    def note_success(self, endpoint_name: str) -> None:
        self._fail_counts.pop(endpoint_name, None)
        self._cooldown_until.pop(endpoint_name, None)

    def note_failure(self, endpoint_name: str, *, cooldown_s: float = 0.0) -> None:
        self._fail_counts[endpoint_name] = self._fail_counts.get(endpoint_name, 0) + 1
        if cooldown_s > 0 and self._fail_counts[endpoint_name] >= 3:
            self._cooldown_until[endpoint_name] = time.monotonic() + cooldown_s

    def in_cooldown(self, endpoint_name: str) -> bool:
        until = self._cooldown_until.get(endpoint_name)
        if until is None:
            return False
        if time.monotonic() >= until:
            self._cooldown_until.pop(endpoint_name, None)
            return False
        return True

    def failures(self, endpoint_name: str) -> int:
        return self._fail_counts.get(endpoint_name, 0)


class _HTTPTransport:
    """Thin urllib wrapper; subclass/mocking seam for tests."""

    def post_json(
        self,
        url: str,
        *,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        timeout: float,
    ) -> tuple[int, Dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            return exc.code, {"_detail": detail}
        except urllib.error.URLError as exc:
            raise LLMTimeoutError(f"{url}: connection error: {exc.reason}") from exc
        except TimeoutError:
            raise LLMTimeoutError(f"{url}: request timed out after {timeout}s")
        return status, data

    def get_json(self, url: str, *, headers: Dict[str, str], timeout: float) -> tuple[int, Dict[str, Any]]:
        headers = {**headers, "User-Agent": "NiuSecretary-LLM/1.0 (Hermes)"}
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            return exc.code, {"_detail": detail}
        except urllib.error.URLError as exc:
            raise LLMTimeoutError(f"{url}: connection error: {exc.reason}") from exc


class NiuLLM:
    """Unified client over config-defined logic models."""

    def __init__(
        self,
        config: LLMConfig,
        *,
        transport: Optional[_HTTPTransport] = None,
        key_pool: Optional[KeyPool] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self.config = config
        self.http = transport or _HTTPTransport()
        self.pool = key_pool or KeyPool()
        import uuid
        self.session_id = session_id or f"niu-{uuid.uuid4().hex[:16]}"

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, config_path: Optional[str] = None, **kwargs: Any) -> "NiuLLM":
        return cls(LLMConfig.load(config_path), **kwargs)

    # ------------------------------------------------------------------ chat
    def chat(self, logic_name: str, messages: Sequence[Dict[str, Any]], **overrides: Any) -> LLMResponse:
        """Send a chat request under a logic model name, with fallback chain."""
        lm = self.config.model(logic_name)
        attempts: List[tuple] = [(lm, False)]
        attempts += [(self._fallback_to_spec(fb), True) for fb in lm.fallback]

        last_error: Optional[Exception] = None
        for spec, is_fallback in attempts:
            endpoint = self.config.endpoint_for(spec)
            try:
                self.config.resolve_key(endpoint)
            except Exception as exc:
                last_error = exc
                continue
            if self.pool.in_cooldown(endpoint.name):
                last_error = LLMError(f"endpoint '{endpoint.name}' is cooling down")
                continue
            try:
                return self._call_chat(endpoint, spec.model, messages, spec.timeout_s,
                                       spec.style, lm.max_retries, is_fallback, **overrides)
            except (RateLimitError, LLMError, AuthenticationError) as exc:
                last_error = exc
                continue
        raise last_error or LLMError(f"no usable endpoint for logic model '{logic_name}'")

    def _fallback_to_spec(self, fb: FallbackEntry) -> "LogicModel":
        return LogicModel(
            name=f"__fallback__", endpoint=fb.endpoint, model=fb.model,
            style=self.config.endpoint_for(fb).style,
            timeout_s=self.config.endpoint_for(fb).timeout_s,
        )

    # ---------------------------------------------------------------- embed
    def embed(self, logic_name: str, texts: Sequence[str]) -> List[List[float]]:
        lm = self.config.model(logic_name)
        endpoint = self.config.endpoint_for(lm)
        api_key = self.config.resolve_key(endpoint)
        payload = {"model": lm.model, "input": list(texts)}
        status, data = self._request(
            endpoint, f"{endpoint.base_url}/embeddings", payload, api_key, lm.timeout_s
        )
        rows = data.get("data") or []
        if not rows or not all("embedding" in r for r in rows):
            raise BadResponseError(f"{endpoint.name}: embedding response missing 'data[].embedding'")
        return [r["embedding"] for r in rows]

    # --------------------------------------------------------------- vision
    def vision(self, logic_name: str, image_url: str, prompt: str) -> LLMResponse:
        """Image understanding over a vision-capable logic model."""
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }]
        return self.chat(logic_name, messages)

    # --------------------------------------------------------------- internals
    def _call_chat(
        self,
        endpoint: EndpointConfig,
        model: str,
        messages: Sequence[Dict[str, Any]],
        timeout_s: float,
        style: str,
        max_retries: int,
        is_fallback: bool,
        **overrides: Any,
    ) -> LLMResponse:
        api_key = self.config.resolve_key(endpoint)
        payload: Dict[str, Any] = {"model": model, "messages": list(messages)}
        payload.update({k: v for k, v in overrides.items() if v is not None})

        if style == "responses":
            url = f"{endpoint.base_url}/responses"
            payload = self._chat_to_responses(payload, url)
        else:
            url = f"{endpoint.base_url}/chat/completions"

        attempt = 0
        while True:
            attempt += 1
            status, data = self._request(endpoint, url, payload, api_key, timeout_s)
            if status == 200:
                text, usage = self._extract_text(data)
                self.pool.note_success(endpoint.name)
                return LLMResponse(
                    text=text, model=data.get("model") or model, endpoint=endpoint.name,
                    usage=usage or {}, raw=data, latency_ms=0, via_fallback=is_fallback,
                )
            error = self._http_error(status, endpoint, data)
            self.pool.note_failure(endpoint.name)
            retryable = isinstance(error, (RateLimitError,)) or status >= 500
            if retryable and attempt <= max_retries:
                time.sleep(min(2 ** attempt, 8))
                continue
            # Non-retryable or retries exhausted — raise; caller (chat) tries fallback
            raise error

    def _request(
        self,
        endpoint: EndpointConfig,
        url: str,
        payload: Dict[str, Any],
        api_key: str,
        timeout_s: float,
    ) -> tuple[int, Dict[str, Any]]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "NiuSecretary-LLM/1.0 (Hermes)",
        }
        # OpenCode relay requires a routing-affinity session header
        if "opencode.ai" in endpoint.base_url:
            headers["x-opencode-session"] = self.session_id
        try:
            status, data = self.http.post_json(url, headers=headers, payload=payload,
                                               timeout=timeout_s)
        except urllib.error.TimeoutError:
            raise LLMTimeoutError(f"{url}: timed out after {timeout_s}s")
        return status, data

    # -------------------------------------------------------------- parsing
    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> tuple[str, Optional[Dict[str, Any]]]:
        """Parse chat.completions or responses-style payloads."""
        if "choices" in data:
            choices = data["choices"] or []
            if not choices:
                raise BadResponseError("empty choices[] in response")
            msg = choices[0].get("message") or {}
            content = msg.get("content") or choices[0].get("text")
            if content is None:
                raise BadResponseError("missing message.content in choices[0]")
            return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False), data.get("usage")
        if "output" in data:
            texts = []
            for item in (data.get("output") or []):
                if item.get("type") == "message":
                    for part in item.get("content") or []:
                        if part.get("type") == "output_text":
                            texts.append(part.get("text") or "")
            if not texts:
                # responses API failure detail
                if data.get("error"):
                    raise BadResponseError(str(data["error"])[:300])
                raise BadResponseError("no output_text in responses payload")
            return "\n".join(texts), data.get("usage")
        raise BadResponseError(f"unrecognized response shape: {json.dumps(data)[:200]}")

    @staticmethod
    def _chat_to_responses(payload: Dict[str, Any], url: str) -> Dict[str, Any]:
        """If the caller switched style to 'responses', convert chat payload."""
        input_text = ""
        for msg in payload.get("messages", []):
            role = msg.get("role", "user")
            content = msg.get("content")
            if isinstance(content, str):
                input_text += f"{role}: {content}\n"
        out = {"model": payload["model"], "input": input_text.strip()}
        if "max_tokens" in payload:
            out["max_output_tokens"] = payload.pop("max_tokens")
        return out

    @staticmethod
    def _http_error(status: int, endpoint: EndpointConfig, data: Dict[str, Any]) -> Exception:
        detail = str(data.get("_detail") or data.get("error") or data)[:300]
        if status in (401, 403):
            return AuthenticationError(
                f"{endpoint.name}: auth failed ({status}). Check {endpoint.api_key_env}. {detail}"
            )
        if status == 429:
            return RateLimitError(f"{endpoint.name}: rate limited (429): {detail}")
        if status >= 500:
            return LLMError(f"{endpoint.name}: server error ({status}): {detail}")
        return BadResponseError(f"{endpoint.name}: HTTP {status}: {detail}")

    # -------------------------------------------------------------------- doctor
    def doctor(self) -> Dict[str, Dict[str, str]]:
        """Probe each endpoint's /models endpoint, report per-endpoint status."""
        report: Dict[str, Dict[str, str]] = {}
        for name, ep in self.config.endpoints.items():
            try:
                api_key = self.config.resolve_key(ep)
            except Exception as exc:
                report[name] = {"status": "no_key", "detail": str(exc)}
                continue
            url = f"{ep.base_url}/models"
            try:
                status, data = self.http.get_json(
                    url, headers={"Authorization": f"Bearer {api_key}"}, timeout=8.0
                )
            except LLMError as exc:
                report[name] = {"status": "unreachable", "detail": str(exc)}
                continue
            report[name] = {
                "status": "ok" if status == 200 else f"http_{status}",
                "detail": str(data.get("_detail") or data)[:200]
                if status != 200 else f"{ep.base_url} reachable",
            }
        return report
