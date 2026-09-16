"""统一层「调用记录」测试（2026-09-16）。

覆盖：成功/失败/缺 key/降级到备选各记一行；可关闭；记账失败不影响业务；report/recent 可用。
全部 HTTP 用 mock，不联网。
"""
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from niu_core.llm_client import LLMConfig, NiuLLM, call_log  # noqa: E402

CFG = """\
default_endpoint: ep
endpoints:
  ep:
    base_url: https://ep.example/v1
    api_key_env: TEST_API_KEY
    style: chat_completions
    timeout_s: 5
  dead:
    base_url: https://dead.example/v1
    api_key_env: MISSING_KEY_ENV
    style: chat_completions
    timeout_s: 5
logic_models:
  simple:
    endpoint: ep
    model: model-a
  with_fb:
    endpoint: dead
    model: primary-model
    max_retries: 0
    fallback:
      - { endpoint: ep, model: fb-model }
"""


class MockTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post_json(self, url, *, headers, payload, timeout):
        self.calls.append({"url": url, "payload": payload})
        status, data = self.responses.pop(0)
        return status, data


def chat_ok(text="hello", model="model-a"):
    return 200, {"choices": [{"message": {"role": "assistant", "content": text}}],
                 "model": model, "usage": {"prompt_tokens": 7, "completion_tokens": 3}}


def write_cfg(tmp_path: Path, text: str = CFG) -> Path:
    p = tmp_path / "models.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def make_llm(tmp_path: Path, responses) -> NiuLLM:
    return NiuLLM(LLMConfig.load(write_cfg(tmp_path)), transport=MockTransport(responses))


@pytest.fixture(autouse=True)
def log_db(tmp_path, monkeypatch):
    """每条测试用独立记账库，避免污染真实库。"""
    db = tmp_path / "calls.sqlite3"
    monkeypatch.setenv("NIU_LLM_LOG_DB", str(db))
    monkeypatch.setenv("NIU_LLM_CALLER", "pytest-call-log")
    monkeypatch.delenv("NIU_LLM_LOG", raising=False)
    return db


def rows(db: Path) -> list[dict]:
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("select * from llm_calls order by id").fetchall()]
    finally:
        conn.close()


def test_ok_call_is_recorded(tmp_path, monkeypatch, log_db):
    monkeypatch.setenv("TEST_API_KEY", "sk-test")
    llm = make_llm(tmp_path, [chat_ok()])
    llm.chat("simple", [{"role": "user", "content": "hello"}])

    rec = rows(log_db)
    assert len(rec) == 1
    r = rec[0]
    assert r["status"] == "ok" and r["logic_model"] == "simple"
    assert r["endpoint"] == "ep" and r["model"] == "model-a"
    assert r["caller"] == "pytest-call-log" and r["is_fallback"] == 0 and r["attempt"] == 1
    assert r["prompt_chars"] == 5 and r["reply_chars"] == len("hello")
    assert r["input_tokens"] == 7 and r["output_tokens"] == 3
    assert r["error_type"] == ""


def test_missing_key_then_fallback_are_both_recorded(tmp_path, monkeypatch, log_db):
    """主选端点缺 key → skipped_no_key；降级到备选成功 → ok + is_fallback=1。"""
    monkeypatch.setenv("TEST_API_KEY", "sk-test")
    monkeypatch.delenv("MISSING_KEY_ENV", raising=False)
    llm = make_llm(tmp_path, [chat_ok("fb", "fb-model")])
    resp = llm.chat("with_fb", [{"role": "user", "content": "q"}])
    assert resp.via_fallback is True

    rec = rows(log_db)
    assert [r["status"] for r in rec] == ["skipped_no_key", "ok"]
    assert rec[0]["endpoint"] == "dead" and rec[0]["attempt"] == 1
    assert rec[0]["error_type"]  # 记录下为何跳过（缺 key）
    assert rec[1]["is_fallback"] == 1 and rec[1]["model"] == "fb-model"


def test_http_error_is_recorded(tmp_path, monkeypatch, log_db):
    monkeypatch.setenv("TEST_API_KEY", "sk-test")
    llm = make_llm(tmp_path, [(401, {"error": {"message": "bad key"}})])
    with pytest.raises(Exception):
        llm.chat("simple", [{"role": "user", "content": "hi"}])

    rec = rows(log_db)
    assert len(rec) == 1
    assert rec[0]["status"] == "error" and rec[0]["error_type"]


def test_embed_is_recorded(tmp_path, monkeypatch, log_db):
    monkeypatch.setenv("TEST_API_KEY", "sk-test")
    llm = make_llm(tmp_path, [(200, {"data": [{"embedding": [0.1]}], "usage": {"prompt_tokens": 2}})])
    llm.embed("simple", ["a", "bb"])

    rec = rows(log_db)
    assert len(rec) == 1
    assert rec[0]["logic_model"] == "simple" and rec[0]["status"] == "ok"
    assert rec[0]["prompt_chars"] == 3 and rec[0]["reply_chars"] == 1


def test_logging_can_be_disabled(tmp_path, monkeypatch, log_db):
    monkeypatch.setenv("TEST_API_KEY", "sk-test")
    monkeypatch.setenv("NIU_LLM_LOG", "off")
    make_llm(tmp_path, [chat_ok()]).chat("simple", [{"role": "user", "content": "hi"}])
    assert not log_db.exists()


def test_record_never_raises_when_db_unwritable(monkeypatch):
    """记账失败绝不能影响业务：库指到不可写路径也不能抛。"""
    monkeypatch.setenv("NIU_LLM_LOG_DB", "/proc/definitely/not/writable.sqlite3")
    call_log.record(logic_model="x", status="ok")   # 不抛即通过


def test_report_and_recent(tmp_path, monkeypatch, log_db):
    monkeypatch.setenv("TEST_API_KEY", "sk-test")
    make_llm(tmp_path, [chat_ok()]).chat("simple", [{"role": "user", "content": "hello"}])
    out = call_log.report(days=1)
    assert "simple" in out and "1 次调用" in out
    assert call_log.recent(5)[0]["logic_model"] == "simple"
