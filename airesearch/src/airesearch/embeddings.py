from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from airesearch.paperpipe_sync import stable_json


class EmbeddingProviderError(ValueError):
    pass


UrlOpen = Callable[..., Any]


@dataclass(frozen=True)
class OpenAICompatibleEmbeddingProvider:
    model: str
    api_key: str
    base_url: str | None = None
    batch_size: int = 10
    timeout_seconds: int = 90
    urlopen: UrlOpen | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "OpenAICompatibleEmbeddingProvider":
        values = os.environ if env is None else env
        model = (
            values.get("AIRESEARCH_EMBEDDING_MODEL")
            or values.get("PAPERPIPE_EMBEDDING_MODEL")
            or values.get("OPENAI_EMBEDDING_MODEL")
            or ""
        ).strip()
        base_url = (
            values.get("AIRESEARCH_EMBEDDING_BASE_URL")
            or values.get("OPENAI_BASE_URL")
            or values.get("OPENAI_API_BASE")
            or None
        )
        api_key = (
            values.get("AIRESEARCH_EMBEDDING_API_KEY")
            or values.get("OPENAI_API_KEY")
            or ""
        ).strip()
        if not model:
            raise EmbeddingProviderError(
                "semantic clustering requires AIRESEARCH_EMBEDDING_MODEL or PAPERPIPE_EMBEDDING_MODEL"
            )
        if not api_key:
            raise EmbeddingProviderError("semantic clustering requires AIRESEARCH_EMBEDDING_API_KEY or OPENAI_API_KEY")
        batch_size_raw = values.get("AIRESEARCH_EMBEDDING_BATCH_SIZE", "10")
        try:
            batch_size = int(batch_size_raw)
        except ValueError as exc:
            raise EmbeddingProviderError("AIRESEARCH_EMBEDDING_BATCH_SIZE must be an integer") from exc
        if batch_size < 1:
            raise EmbeddingProviderError("AIRESEARCH_EMBEDDING_BATCH_SIZE must be at least 1")
        return cls(model=model, base_url=base_url, api_key=api_key, batch_size=batch_size)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            embeddings.extend(self._embed_batch(batch))
        return embeddings

    def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:

        import urllib.error
        import urllib.request

        endpoint = (self.base_url or "https://api.openai.com/v1").rstrip("/") + "/embeddings"
        body = stable_json({
            "model": self.model,
            "input": list(texts),
            "encoding_format": "float",
        }).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "authorization": f"Bearer {self.api_key}",
                "content-type": "application/json",
            },
            method="POST",
        )
        opener = self.urlopen or urllib.request.urlopen
        try:
            with opener(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise EmbeddingProviderError(f"embedding provider HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, TypeError, OSError) as exc:
            raise EmbeddingProviderError(f"embedding provider request failed: {exc}") from exc
        return _parse_embeddings(payload, expected_count=len(texts))


def _parse_embeddings(payload: dict[str, Any], *, expected_count: int) -> list[list[float]]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise EmbeddingProviderError("embedding provider response data must be a list")
    ordered_rows = sorted(data, key=lambda row: int(row.get("index", 0)) if isinstance(row, dict) else 0)
    embeddings: list[list[float]] = []
    for row in ordered_rows:
        if not isinstance(row, dict):
            raise EmbeddingProviderError("embedding provider response row must be an object")
        raw_embedding = row.get("embedding")
        if not isinstance(raw_embedding, list):
            raise EmbeddingProviderError("embedding provider response embedding must be a list")
        try:
            embeddings.append([float(value) for value in raw_embedding])
        except (TypeError, ValueError) as exc:
            raise EmbeddingProviderError("embedding provider response embedding values must be numeric") from exc
    if len(embeddings) != expected_count:
        raise EmbeddingProviderError(
            f"embedding provider returned {len(embeddings)} embeddings for {expected_count} texts"
        )
    return embeddings
