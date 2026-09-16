from __future__ import annotations

import base64

import pytest

from airesearch.formula_ocr import (
    FormulaOCRConfig,
    FormulaOCRValidationError,
    OpenAICompatibleFormulaOCRProvider,
    is_likely_formula,
    normalize_formula_latex,
)


def test_formula_ocr_config_reuses_existing_vision_environment(monkeypatch):
    """yaml 没给出 formula_ocr 路由时，回落到塑形馆的视觉环境变量。

    2026-09-16 item 2 后，FITNESS_VISION_* 属于「历史通用兜底」，排在 compat(yaml) 之后，
    所以这里把 compat 断空来专门验证这条兜底路径。
    """
    monkeypatch.setattr(
        "niu_core.llm_client.compat.resolve",
        lambda logic_model, env=None: ("", "", ""),
    )
    config = FormulaOCRConfig.from_env(
        {
            "FITNESS_VISION_API_BASE": "https://vision.example/v1",
            "FITNESS_VISION_API_KEY": "secret",
            "FITNESS_VISION_MODEL": "vision-model",
            "FITNESS_VISION_TIMEOUT_MS": "45000",
            "AIRESEARCH_FORMULA_OCR_PROXY": "http://127.0.0.1:7890",
        }
    )

    assert config.configured is True
    assert config.endpoint == "https://vision.example/v1/chat/completions"
    assert config.model == "vision-model"
    assert config.timeout_seconds == 45
    assert config.proxy_url == "http://127.0.0.1:7890"


def test_formula_ocr_config_uses_unified_opencode_credentials():
    """默认凭据/模型/端点来自 config/models.yaml（compat），而非历史 OPENCODE_GO_* 变量。"""
    from niu_core.llm_client import compat

    base, key, model = compat.resolve("formula_ocr")
    config = FormulaOCRConfig.from_env(
        {
            # 历史通用变量故意指向别处：不应再生效（yaml 优先）
            "OPENCODE_GO_BASE_URL": "https://opencode.example/v1",
            "OPENCODE_GO_API_KEY": "generic-should-lose",
            "AIRESEARCH_FORMULA_OCR_PROXY": "http://127.0.0.1:7890",
        }
    )

    assert config.api_base.rstrip("/") == base.rstrip("/")
    assert config.api_key == key
    assert config.model == model
    assert "opencode.example" not in config.api_base
    assert config.proxy_url == "http://127.0.0.1:7890"


def test_openai_formula_ocr_payload_and_result():
    requests = []

    def transport(url, headers, payload, timeout):
        requests.append((url, headers, payload, timeout))
        return {"choices": [{"message": {"content": '{"latex":"$$\\\\mathcal{L}=-\\\\log p(y|x)$$","confidence":0.93}'}}]}

    provider = OpenAICompatibleFormulaOCRProvider(
        FormulaOCRConfig(
            api_base="https://vision.example/v1",
            api_key="secret",
            model="vision-model",
            timeout_seconds=30,
        ),
        transport=transport,
    )

    result = provider.recognize(b"formula-png", mime_type="image/png", context="loss function")

    assert result.latex == r"\mathcal{L}=-\log p(y|x)"
    assert result.confidence == 0.93
    assert result.model == "vision-model"
    url, headers, payload, timeout = requests[0]
    assert url.endswith("/chat/completions")
    assert headers["Authorization"] == "Bearer secret"
    # OpenCode relay 硬要求：正常 UA + x-opencode-session 路由亲和头，缺失会被 400 MissingSessionID 拒绝
    assert headers["User-Agent"] == "NiuSecretary-LLM/1.0 (AIResearch)"
    assert headers["Accept"] == "application/json"
    assert headers["x-opencode-session"] == "niu-airesearch-formula-ocr"
    image_url = payload["messages"][0]["content"][1]["image_url"]["url"]
    assert image_url == "data:image/png;base64," + base64.b64encode(b"formula-png").decode("ascii")
    assert timeout == 30


def test_anthropic_formula_ocr_payload():
    requests = []

    def transport(url, headers, payload, timeout):
        requests.append((url, headers, payload, timeout))
        return {"content": [{"type": "text", "text": '{"latex":"x^2+y^2=z^2","confidence":0.88}'}]}

    provider = OpenAICompatibleFormulaOCRProvider(
        FormulaOCRConfig(
            api_base="https://vision.example/v1/messages",
            api_key="secret",
            model="vision-model",
            timeout_seconds=20,
        ),
        transport=transport,
    )

    result = provider.recognize(b"formula-png", mime_type="image/png")

    assert result.latex == "x^2+y^2=z^2"
    _url, headers, payload, _timeout = requests[0]
    assert headers["x-api-key"] == "secret"
    assert payload["messages"][0]["content"][1]["source"]["data"] == base64.b64encode(b"formula-png").decode("ascii")


def test_responses_formula_ocr_payload_and_result():
    requests = []

    def transport(url, headers, payload, timeout):
        requests.append((url, headers, payload, timeout))
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"latex":"\\\\mathcal{L}=\\\\sum_i x_i","confidence":0.91}',
                        }
                    ],
                }
            ]
        }

    provider = OpenAICompatibleFormulaOCRProvider(
        FormulaOCRConfig(
            api_base="https://vision.example/v1/responses",
            api_key="secret",
            model="gpt-5.6-luna",
            timeout_seconds=30,
        ),
        transport=transport,
    )

    result = provider.recognize(b"formula-png", mime_type="image/png", context="loss")

    assert result.latex == r"\mathcal{L}=\sum_i x_i"
    assert result.model == "gpt-5.6-luna"
    url, headers, payload, timeout = requests[0]
    assert url.endswith("/responses")
    assert headers["Authorization"] == "Bearer secret"
    assert payload["input"][0]["content"][0]["type"] == "input_text"
    assert payload["input"][0]["content"][1]["type"] == "input_image"
    assert payload["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")
    assert payload["max_output_tokens"] == 1800
    assert timeout == 30


def test_responses_formula_repair_sends_failed_latex_context_and_image():
    requests = []

    def transport(url, headers, payload, timeout):
        requests.append((url, headers, payload, timeout))
        return {"output_text": '{"latex":"x=\\\\left[y\\\\right]","confidence":0.97}'}

    provider = OpenAICompatibleFormulaOCRProvider(
        FormulaOCRConfig(
            api_base="https://vision.example/v1/responses",
            api_key="secret",
            model="gpt-5.6-luna",
        ),
        transport=transport,
    )

    result = provider.repair(
        b"pdf-crop",
        failed_latex=r"x=\right]",
        context="local paragraph",
    )

    assert result.latex == r"x=\left[y\right]"
    prompt = requests[0][2]["input"][0]["content"][0]["text"]
    assert "Repair exactly one LaTeX formula" in prompt
    assert r"x=\right]" in prompt
    assert "local paragraph" in prompt
    assert requests[0][2]["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")


def test_formula_latex_validation_rejects_unbalanced_or_explanatory_text():
    assert normalize_formula_latex(r"\[\frac{a}{b}\]") == r"\frac{a}{b}"
    with pytest.raises(FormulaOCRValidationError):
        normalize_formula_latex(r"\frac{a}{b")
    with pytest.raises(FormulaOCRValidationError):
        normalize_formula_latex("The formula in the image is x plus y.")


def test_normalize_formula_latex_rejects_html_but_allows_math_angle_brackets():
    with pytest.raises(FormulaOCRValidationError, match="HTML"):
        normalize_formula_latex("<script>alert(1)</script>")
    assert normalize_formula_latex(r"P_c(x)=\exp(\cos<v,\mu_c>)") == r"P_c(x)=\exp(\cos<v,\mu_c>)"
    assert normalize_formula_latex(r"\texttt{<think>}\;x\;\texttt{</think>}") == (
        r"\texttt{<think>}\;x\;\texttt{</think>}"
    )


@pytest.mark.parametrize(
    "value",
    [
        r"\mathcal{L}_{off}=\mathbb{E}_{x_t}[\lVert v_\theta-v_{\theta'}\rVert_2^2]",
        "q(z_t | x) = Cat(z_t; alpha_t x + (1-alpha_t) pi)",
        "x_t = f(x_{t-1})",
        "i = 1",
    ],
)
def test_formula_signal_accepts_standalone_math(value: str):
    assert is_likely_formula(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "Initial frame X0\nT = 1s\nT = 3s\nT = 5s",
        "in psychology, 3(2):77-101, 2006.",
        "blog/genie-3-a-new-frontier-for-world-models/, 2025. Accessed: 2026-05-06.",
        "Table 4: Dataset composition. AD = Autonomous Driving; Rob = Robotic Manipulation.",
        "Single (N=2007)",
        "T in [0, 1]. For each intermediate latent variable, the model has the marginal:",
        "{Input: Prompt + Text}",
        "LCE = −",
        "The objective is evaluated for every sample in the benchmark and reported below.",
    ],
)
def test_formula_signal_rejects_timeline_caption_reference_and_prose(value: str):
    assert is_likely_formula(value) is False
