from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from airesearch.provider_config import responses_url


FORMULA_PROMPT = (
    "Recognize only the mathematical formula in this image and reconstruct valid LaTeX. "
    "Preserve subscripts, superscripts, fractions, roots, matrices, accents, Greek letters, and operators. "
    "Do not explain the formula. Return JSON only with keys latex and confidence, where confidence is 0 to 1."
)
FORMULA_REPAIR_PROMPT = (
    "Repair exactly one LaTeX formula that failed MathJax compilation. "
    "Use the PDF image as the visual source of truth and use the supplied local text only as context. "
    "Preserve the formula's mathematical meaning; expand unsupported document-specific macros when needed. "
    "Do not rewrite prose and do not explain the answer. Return JSON only with keys latex and confidence."
)
Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


class FormulaOCRError(RuntimeError):
    pass


class FormulaOCRValidationError(FormulaOCRError):
    pass


FORMULA_RELATION_RE = re.compile(r"(?:=|<=|>=|!=|:=|\\leq?|\\geq?|\\approx|\\sim|\\in|[≤≥≈∈])")
FORMULA_COMMAND_RE = re.compile(r"\\[A-Za-z]+")
FORMULA_STRUCTURE_RE = re.compile(r"(?:[_^{}]|[+\-*/|]|[∑∫√±×])")
FORMULA_TIMELINE_LINE_RE = re.compile(
    r"(?:initial\s+frame\s+)?(?:[A-Za-z]?\s*\d*)?\s*(?:T\s*=\s*\d+(?:\.\d+)?\s*(?:ms|s))?",
    re.I,
)
FORMULA_SAMPLE_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z /-]{1,40}\s*\(\s*N\s*=\s*\d+\s*\)", re.I)
HTML_TAG_RE = re.compile(
    r"</?(?:script|style|iframe|object|embed|img|svg|math|table|tr|td|div|span|p|br|a)"
    r"(?:\s+[^>]*)?/?>",
    re.I,
)


def is_likely_formula(value: str) -> bool:
    """Return whether extracted text is suitable for display as a standalone formula."""
    raw = str(value or "").strip()
    compact = re.sub(r"\s+", " ", raw)
    if not compact or len(compact) > 500:
        return False
    lowered = compact.lower()
    if re.match(r"^(?:table|figure|fig\.|表|图)\s*[\divx一二三四五六七八九十]+\s*[:.：、-]", compact, re.I):
        return False
    if any(token in lowered for token in ("http://", "https://", "www.", "doi.org", "accessed:")):
        return False
    if FORMULA_SAMPLE_LABEL_RE.match(compact):
        return False
    if re.fullmatch(r"\{?[A-Z][A-Za-z ]{1,30}:\s*[A-Za-z+ ]+\}?", compact):
        return False

    lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines() if line.strip()]
    if lines and all(FORMULA_TIMELINE_LINE_RE.fullmatch(line) for line in lines):
        return False
    timeline_tokens = re.findall(r"\bT\s*=\s*\d+(?:\.\d+)?\s*(?:ms|s)\b", compact, re.I)
    if timeline_tokens and re.sub(
        r"(?:initial\s+frame\s+[A-Za-z]?\d*\s*)|(?:\bT\s*=\s*\d+(?:\.\d+)?\s*(?:ms|s)\b)",
        "",
        compact,
        flags=re.I,
    ).strip(" ,;:/-") == "":
        return False

    if re.search(r"(?:=|<=|>=|:=|[≤≥≈∈+\-−*/])\s*$", compact):
        return False
    relation = bool(FORMULA_RELATION_RE.search(compact))
    command_count = len(FORMULA_COMMAND_RE.findall(compact))
    structure_count = len(FORMULA_STRUCTURE_RE.findall(compact))
    math_words = len(re.findall(r"\b(?:arg|min|max|log|ln|exp|softmax|loss|rank|det|cat)\b", lowered))
    prose_words = len(re.findall(r"\b[A-Za-z]{3,}\b", FORMULA_COMMAND_RE.sub("", compact)))
    symbol_ratio = sum(char in "=+-*/()[]{}_^<>|≤≥≈∈∑∫√±×" for char in compact) / max(1, len(compact))

    prose_cue = re.search(
        r"\b(?:for each|where|denotes?|has the|is used|the following|we (?:use|define|compute))\b",
        lowered,
    )
    if prose_cue and prose_words >= 5:
        return False
    if prose_words >= 10 and command_count == 0 and symbol_ratio < 0.12:
        return False
    if relation and (prose_words <= 8 or command_count > 0 or symbol_ratio >= 0.08):
        return True
    if command_count >= 1 and (structure_count >= 1 or math_words >= 1):
        return True
    return structure_count >= 3 and symbol_ratio >= 0.12 and prose_words <= 5


@dataclass(frozen=True)
class FormulaOCRConfig:
    api_base: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 45.0
    proxy_url: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    @property
    def endpoint(self) -> str:
        value = self.api_base.rstrip("/")
        if value.endswith(("/messages", "/chat/completions", "/responses")):
            return value
        return value + "/chat/completions" if value else ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "FormulaOCRConfig":
        values = os.environ if env is None else env
        timeout_raw = values.get("AIRESEARCH_FORMULA_OCR_TIMEOUT_MS") or values.get("FITNESS_VISION_TIMEOUT_MS") or "45000"
        try:
            timeout_seconds = max(1.0, float(timeout_raw) / 1000.0)
        except (TypeError, ValueError):
            timeout_seconds = 45.0
        # Legacy env chain first; unified gateway (config/models.yaml) fills
        # gaps that explicit env vars (incl. OPENCODE_GO_*) did not provide.
        compat_base, compat_key, compat_model = "", "", ""
        try:
            from niu_core.llm_client import compat as _niuo_compat
            compat_base, compat_key, compat_model = _niuo_compat.resolve("formula_ocr")
        except Exception:
            pass
        return cls(
            api_base=(
                values.get("AIRESEARCH_FORMULA_OCR_API_BASE")
                or values.get("FITNESS_VISION_API_BASE")
                or responses_url(values.get("OPENCODE_GO_BASE_URL"))
                or compat_base
            ).strip(),
            api_key=(
                values.get("AIRESEARCH_FORMULA_OCR_API_KEY")
                or values.get("FITNESS_VISION_API_KEY")
                or values.get("OPENCODE_GO_API_KEY")
                or compat_key
                or ""
            ).strip(),
            model=(
                values.get("AIRESEARCH_FORMULA_OCR_MODEL")
                or values.get("FITNESS_VISION_MODEL")
                or compat_model
                or ""
            ).strip(),
            timeout_seconds=timeout_seconds,
            proxy_url=(values.get("AIRESEARCH_FORMULA_OCR_PROXY") or values.get("OPENCODE_GO_PROXY") or "").strip(),
        )


@dataclass(frozen=True)
class FormulaOCRResult:
    latex: str
    confidence: float
    model: str
    provider: str = "openai-compatible-vision"


def _balanced_braces(value: str) -> bool:
    depth = 0
    escaped = False
    for char in value:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def normalize_formula_latex(value: str) -> str:
    latex = str(value or "").strip()
    latex = re.sub(r"^```(?:latex|tex)?\s*", "", latex, flags=re.I)
    latex = re.sub(r"\s*```$", "", latex)
    if latex.startswith("$$") and latex.endswith("$$") and len(latex) >= 4:
        latex = latex[2:-2].strip()
    if latex.startswith(r"\[") and latex.endswith(r"\]"):
        latex = latex[2:-2].strip()
    if not latex or len(latex) > 4000:
        raise FormulaOCRValidationError("formula LaTeX is empty or too long")
    if not _balanced_braces(latex):
        raise FormulaOCRValidationError("formula LaTeX has unbalanced braces")
    if HTML_TAG_RE.search(latex):
        raise FormulaOCRValidationError("formula LaTeX contains HTML")
    word_count = len(re.findall(r"\b[A-Za-z]{3,}\b", latex))
    math_signal = bool(re.search(r"[=+\-*/_^{}\\]|\d", latex))
    if word_count >= 3 and not math_signal:
        raise FormulaOCRValidationError("formula OCR returned explanatory prose")
    return latex


def _strip_json_fence(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    return re.sub(r"\s*```$", "", text).strip()


def _response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if isinstance(choices, list) and choices:
        content = choices[0].get("message", {}).get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(str(item.get("text") or "") for item in content if isinstance(item, dict))
    content = payload.get("content") if isinstance(payload, dict) else None
    if isinstance(content, list):
        return "".join(str(item.get("text") or "") for item in content if isinstance(item, dict))
    if isinstance(payload.get("output_text"), str):
        return str(payload["output_text"])
    output = payload.get("output") if isinstance(payload, dict) else None
    if isinstance(output, list):
        return "".join(
            str(content.get("text") or "")
            for item in output
            if isinstance(item, dict)
            for content in (item.get("content") or [])
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}
        )
    return ""


def _http_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
    *,
    proxy_url: str = "",
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        if proxy_url:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
            )
            response_context = opener.open(request, timeout=timeout)
        else:
            response_context = urllib.request.urlopen(request, timeout=timeout)
        with response_context as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise FormulaOCRError(f"formula OCR HTTP {exc.code}: {detail}") from exc
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        raise FormulaOCRError(f"formula OCR request failed: {exc}") from exc
    if not isinstance(result, dict):
        raise FormulaOCRError("formula OCR response must be an object")
    return result


class OpenAICompatibleFormulaOCRProvider:
    def __init__(self, config: FormulaOCRConfig, *, transport: Transport | None = None):
        if not config.configured:
            raise FormulaOCRError("formula OCR provider is not configured")
        self.config = config
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        if self.config.endpoint.endswith("/messages"):
            return {
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "OpenClaw/1.0",
            "Accept": "application/json",
        }

    def _payload(
        self,
        image_bytes: bytes,
        *,
        mime_type: str,
        context: str,
        prompt_prefix: str = FORMULA_PROMPT,
    ) -> dict[str, Any]:
        image_base64 = base64.b64encode(image_bytes).decode("ascii")
        prompt = prompt_prefix + (f" Context: {context[:1600]}" if context else "")
        if self.config.endpoint.endswith("/responses"):
            return {
                "model": self.config.model,
                "max_output_tokens": 1800,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": f"data:{mime_type};base64,{image_base64}",
                            },
                        ],
                    }
                ],
            }
        if self.config.endpoint.endswith("/messages"):
            return {
                "model": self.config.model,
                "max_tokens": 1800,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": image_base64}},
                        ],
                    }
                ],
            }
        return {
            "model": self.config.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                    ],
                }
            ],
        }

    def _request(
        self,
        image_bytes: bytes,
        *,
        mime_type: str,
        context: str,
        prompt_prefix: str,
    ) -> FormulaOCRResult:
        request_args = (
            self.config.endpoint,
            self._headers(),
            self._payload(
                image_bytes,
                mime_type=mime_type,
                context=context,
                prompt_prefix=prompt_prefix,
            ),
            self.config.timeout_seconds,
        )
        payload = (
            self.transport(*request_args)
            if self.transport is not None
            else _http_transport(*request_args, proxy_url=self.config.proxy_url)
        )
        text = _strip_json_fence(_response_text(payload))
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"latex": text, "confidence": 0.5}
        if not isinstance(parsed, dict):
            raise FormulaOCRValidationError("formula OCR response payload is invalid")
        latex = normalize_formula_latex(str(parsed.get("latex") or parsed.get("formula") or ""))
        try:
            confidence = float(parsed.get("confidence") or 0.5)
        except (TypeError, ValueError):
            confidence = 0.5
        return FormulaOCRResult(
            latex=latex,
            confidence=max(0.0, min(1.0, confidence)),
            model=self.config.model,
        )

    def recognize(self, image_bytes: bytes, *, mime_type: str = "image/png", context: str = "") -> FormulaOCRResult:
        return self._request(
            image_bytes,
            mime_type=mime_type,
            context=context,
            prompt_prefix=FORMULA_PROMPT,
        )

    def repair(
        self,
        image_bytes: bytes,
        *,
        failed_latex: str,
        context: str = "",
        mime_type: str = "image/png",
    ) -> FormulaOCRResult:
        repair_context = f"Failed LaTeX:\n{failed_latex[:4000]}\n\nLocal text:\n{context[:1600]}"
        return self._request(
            image_bytes,
            mime_type=mime_type,
            context=repair_context,
            prompt_prefix=FORMULA_REPAIR_PROMPT,
        )
