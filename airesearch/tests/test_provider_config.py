from airesearch.provider_config import (
    api_root,
    chat_completions_url,
    opencode_base,
    opencode_key,
    opencode_proxy,
    responses_url,
)


def test_protocol_endpoints_share_one_normalized_root():
    root = "https://opencode.ai/zen/go/v1"
    assert api_root(root + "/") == root
    assert api_root(root + "/responses") == root
    assert api_root(root + "/chat/completions") == root
    assert responses_url(root + "/chat/completions") == root + "/responses"
    assert chat_completions_url(root + "/responses") == root + "/chat/completions"


def test_unified_opencode_values_are_explicit():
    env = {
        "OPENCODE_GO_BASE_URL": "https://opencode.example/v1/responses",
        "OPENCODE_GO_API_KEY": "secret",
        "OPENCODE_GO_PROXY": "http://127.0.0.1:7890",
    }
    assert opencode_base(env) == "https://opencode.example/v1"
    assert opencode_key(env) == "secret"
    assert opencode_proxy(env) == "http://127.0.0.1:7890"
