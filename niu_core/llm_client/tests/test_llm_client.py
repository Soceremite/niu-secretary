"""Tests for niu_core.llm_client — all HTTP is mocked."""
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from niu_core.llm_client import (          # noqa: E402
    NiuLLM, LLMConfig, KeyPool, ConfigError,
    RateLimitError, AuthenticationError,
)


class MockTransport:
    """Returns queued (status, payload) tuples per call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post_json(self, url, *, headers, payload, timeout):
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        status, data = self.responses.pop(0)
        if not isinstance(data, dict):
            data = {"_detail": str(data)}
        return status, data

    def get_json(self, url, *, headers, timeout):
        self.calls.append({"url": url})
        status, data = self.responses.pop(0)
        return status, data if isinstance(data, dict) else {}


def chat_ok(text="hello", model="m1"):
    return 200, {"choices": [{"message": {"role": "assistant", "content": text}}],
                 "model": model, "usage": {"total_tokens": 10}}


def responses_ok(text="hello"):
    return 200, {"output": [{"type": "message",
                             "content": [{"type": "output_text", "text": text}]}],
                 "usage": {}}


def write_cfg(tmp_path, overrides=None):
    base = """
default_endpoint: test_ep
endpoints:
  test_ep:
    base_url: http://fake.test/v1
    api_key_env: TEST_API_KEY
    style: chat_completions
    timeout_s: 5
logic_models:
  simple:
    endpoint: test_ep
    model: fake-model-a
  styled:
    endpoint: test_ep
    model: fake-model-b
    style: responses
  with_fb:
    endpoint: test_ep
    model: primary-model
    max_retries: 0
    fallback:
      - { endpoint: test_ep, model: fb-model }
"""
    if overrides:
        base = base + overrides
    p = tmp_path / "models.yaml"
    p.write_text(base, encoding="utf-8")
    return str(p)


@pytest.fixture
def env_key(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "sk-test-123")


def make_llm(tmp_path, env_key, transport_responses):
    cfg = LLMConfig.load(write_cfg(tmp_path))
    return NiuLLM(cfg, transport=MockTransport(transport_responses))


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        LLMConfig.load(tmp_path / "nope.yaml")


def test_unknown_logic_model_raises(tmp_path, env_key):
    llm = make_llm(tmp_path, env_key, [])
    with pytest.raises(ConfigError) as info:
        llm.chat("does_not_exist", [])
    assert "does_not_exist" in str(info.value)


# --------------------------------------------------------------- chat
def test_chat_success(tmp_path, env_key):
    llm = make_llm(tmp_path, env_key, [chat_ok("hi there")])
    rsp = llm.chat("simple", [{"role": "user", "content": "hey"}])
    assert rsp.text == "hi there"
    assert rsp.model == "m1"
    assert rsp.endpoint == "test_ep"
    assert not rsp.via_fallback
    assert llm.http.calls[0]["payload"]["model"] == "fake-model-a"
    assert llm.http.calls[0]["url"].endswith("/chat/completions")


def test_chat_responses_style(tmp_path, env_key):
    llm = make_llm(tmp_path, env_key, [responses_ok("resp text")])
    rsp = llm.chat("styled", [{"role": "user", "content": "x"}])
    assert rsp.text == "resp text"
    assert llm.http.calls[0]["url"].endswith("/responses")
    assert "messages" not in llm.http.calls[0]["payload"]


def test_fallback_on_rate_limit(tmp_path, env_key):
    llm = make_llm(tmp_path, env_key, [
        (429, {"_detail": "rate limited"}),
        chat_ok("from fallback"),
    ])
    rsp = llm.chat("with_fb", [{"role": "user", "content": "x"}])
    assert rsp.via_fallback
    assert rsp.text == "from fallback"
    assert llm.http.calls[0]["payload"]["model"] == "primary-model"
    assert llm.http.calls[1]["payload"]["model"] == "fb-model"


def test_auth_error_falls_through_then_raises(tmp_path, env_key):
    llm = make_llm(tmp_path, env_key, [
        (401, {"_detail": "bad key"}),
        (401, {"_detail": "bad key too"}),
    ])
    with pytest.raises(AuthenticationError):
        llm.chat("with_fb", [])  # 401 is non-retryable -> fallback tried -> both fail


def test_missing_key_raises_config_error(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    cfg = LLMConfig.load(write_cfg(tmp_path))
    client = NiuLLM(cfg)
    with pytest.raises(ConfigError):
        client.chat("simple", [{"role": "user", "content": "hi"}])


# --------------------------------------------------------------- embed
def test_embed_parses(tmp_path, env_key):
    llm = make_llm(tmp_path, env_key, [(
        200, {"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}
    )])
    vecs = llm.embed("simple", ["a", "b"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]
    assert llm.http.calls[0]["url"].endswith("/embeddings")


# --------------------------------------------------------------- key pool
def test_keypool_cooldown():
    pool = KeyPool()
    pool.note_failure("ep")
    pool.note_failure("ep")
    pool.note_failure("ep", cooldown_s=60)
    assert pool.in_cooldown("ep")
    assert not pool.in_cooldown("other")


# --------------------------------------------------------------- doctor
def test_doctor_reports(tmp_path, env_key):
    llm = make_llm(tmp_path, env_key, [(200, {"data": []})])
    report = llm.doctor()
    assert report["test_ep"]["status"] == "ok"
