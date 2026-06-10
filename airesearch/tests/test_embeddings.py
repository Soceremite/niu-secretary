import json
from dataclasses import dataclass

import pytest

from airesearch.embeddings import EmbeddingProviderError, OpenAICompatibleEmbeddingProvider


@dataclass
class FakeResponse:
    payload: dict

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_openai_compatible_embedding_provider_posts_embedding_request():
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({
            "data": [
                {"index": 1, "embedding": [0.0, 1.0]},
                {"index": 0, "embedding": [1.0, 0.0]},
            ]
        })

    provider = OpenAICompatibleEmbeddingProvider(
        model="text-embedding-v4",
        base_url="https://dashscope.example/compatible-mode/v1",
        api_key="secret",
        timeout_seconds=12,
        urlopen=fake_urlopen,
    )

    embeddings = provider.embed_texts(["alpha", "beta"])

    assert embeddings == [[1.0, 0.0], [0.0, 1.0]]
    assert captured["url"] == "https://dashscope.example/compatible-mode/v1/embeddings"
    assert captured["timeout"] == 12
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["body"] == {
        "encoding_format": "float",
        "input": ["alpha", "beta"],
        "model": "text-embedding-v4",
    }


def test_embedding_provider_from_env_uses_airesearch_variables():
    provider = OpenAICompatibleEmbeddingProvider.from_env({
        "AIRESEARCH_EMBEDDING_MODEL": "text-embedding-v4",
        "AIRESEARCH_EMBEDDING_BASE_URL": "https://dashscope.example/compatible-mode/v1",
        "AIRESEARCH_EMBEDDING_API_KEY": "secret",
        "AIRESEARCH_EMBEDDING_BATCH_SIZE": "7",
    })

    assert provider.model == "text-embedding-v4"
    assert provider.base_url == "https://dashscope.example/compatible-mode/v1"
    assert provider.api_key == "secret"
    assert provider.batch_size == 7


def test_openai_compatible_embedding_provider_splits_batches():
    batch_lengths = []

    def fake_urlopen(request, timeout):
        body = json.loads(request.data.decode("utf-8"))
        batch_lengths.append(len(body["input"]))
        return FakeResponse({
            "data": [
                {"index": index, "embedding": [float(index), 1.0]}
                for index, _text in enumerate(body["input"])
            ]
        })

    provider = OpenAICompatibleEmbeddingProvider(
        model="text-embedding-v4",
        api_key="secret",
        batch_size=10,
        urlopen=fake_urlopen,
    )

    embeddings = provider.embed_texts([f"text-{index}" for index in range(25)])

    assert batch_lengths == [10, 10, 5]
    assert len(embeddings) == 25
    assert embeddings[10] == [0.0, 1.0]


def test_embedding_provider_from_env_requires_model_and_key():
    with pytest.raises(EmbeddingProviderError, match="AIRESEARCH_EMBEDDING_MODEL"):
        OpenAICompatibleEmbeddingProvider.from_env({})

    with pytest.raises(EmbeddingProviderError, match="AIRESEARCH_EMBEDDING_API_KEY"):
        OpenAICompatibleEmbeddingProvider.from_env({"AIRESEARCH_EMBEDDING_MODEL": "text-embedding-v4"})


def test_embedding_provider_rejects_wrong_embedding_count():
    def fake_urlopen(request, timeout):
        return FakeResponse({"data": [{"index": 0, "embedding": [1.0, 0.0]}]})

    provider = OpenAICompatibleEmbeddingProvider(
        model="text-embedding-v4",
        api_key="secret",
        urlopen=fake_urlopen,
    )

    with pytest.raises(EmbeddingProviderError, match="returned 1 embeddings for 2 texts"):
        provider.embed_texts(["alpha", "beta"])
