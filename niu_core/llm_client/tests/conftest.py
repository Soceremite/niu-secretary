"""测试隔离：本目录下的测试**不得**写进真实调用记录库。

统一层的客户端会在每次调用时记账（默认落 <repo>/data/llm_calls.sqlite3）。
测试跑起来会产生大量假调用（fake-model-a / test_ep …），因此统一改到临时库。
单个测试仍可用 monkeypatch.setenv("NIU_LLM_LOG_DB", ...) 覆盖。
"""
import os
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = Path(tempfile.mkdtemp(prefix="niu-llm-log-tests-"))
os.environ.setdefault("NIU_LLM_LOG_DB", str(_TMP_DIR / "calls.sqlite3"))
os.environ.setdefault("NIU_LLM_CALLER", "pytest")


@pytest.fixture(autouse=True)
def _isolate_call_log(tmp_path, monkeypatch):
    monkeypatch.setenv("NIU_LLM_LOG_DB", str(tmp_path / "calls.sqlite3"))
    monkeypatch.setenv("NIU_LLM_CALLER", "pytest")
    monkeypatch.delenv("NIU_LLM_LOG", raising=False)
