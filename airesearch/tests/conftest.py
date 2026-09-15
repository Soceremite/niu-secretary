"""Shared test fixtures.

Tests must be hermetic: the unified gateway config (config/models.yaml) is
forced to a fixture file so test outcomes never depend on the developer's
real NIU keys or routing. Env vars pointing at a specific model/base_url
still win over the config (documented precedence).
"""
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FIXTURE_MODELS_YAML = """
default_endpoint: test_ep
endpoints:
  test_ep:
    base_url: http://gateway.test/v1
    api_key_env: TEST_NIU_GATEWAY_KEY
    style: chat_completions
    timeout_s: 5
logic_models:
  blog:
    endpoint: test_ep
    model: deepseek-v4-pro
  fact:
    endpoint: test_ep
    model: deepseek-v4-pro
  translate:
    endpoint: test_ep
    model: deepseek-v4-pro
  formula_ocr:
    endpoint: test_ep
    model: deepseek-v4-pro
"""


def pytest_configure(config):
    sys.path.insert(0, str(REPO_ROOT))
    cfg_dir = Path(tempfile.mkdtemp(prefix="niu-test-models-"))
    cfg_file = cfg_dir / "models.yaml"
    cfg_file.write_text(FIXTURE_MODELS_YAML, encoding="utf-8")
    os.environ["NIU_LLM_CONFIG"] = str(cfg_file)
    os.environ["TEST_NIU_GATEWAY_KEY"] = "sk-test-fixture"
