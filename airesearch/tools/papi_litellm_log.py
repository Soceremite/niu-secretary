"""litellm 调用 → 统一层调用记录（给 papi / paperpipe 这类第三方链路用）。

背景：paperpipe 内部直接用 litellm（不经过 niu_core.llm_client），它的 summary/tldr/tags
调用因此不会出现在管理台「API 用量」页。litellm 支持全局回调，于是用 sitecustomize
在解释器启动时把下面两个函数挂到 litellm.success_callback / failure_callback 上，
覆盖该 shell 里所有 litellm 调用。

约束：任何异常都吞掉——记账绝不能影响 papi 的正常工作。
"""
from __future__ import annotations

MODEL_LABEL = "blog"      # papi 的 summary/tldr/tags 走 yaml 的 blog 路由
CALLER_LABEL = "papi(litellm)"


def _as_dict(value):
    if isinstance(value, dict):
        return value
    return {}


def _attr_or_key(obj, name):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _usage_pair(kwargs, response):
    usage = _as_dict(_attr_or_key(response, "usage")) or _as_dict(_attr_or_key(kwargs, "usage"))
    if not usage:
        # 有些路径把 usage 放在 kwargs["litellm_params"]/original_response 里
        original = _attr_or_key(response, "_hidden_params")
        usage = _as_dict(_attr_or_key(original, "usage"))
    prompt = usage.get("prompt_tokens") or usage.get("input_tokens")
    completion = usage.get("completion_tokens") or usage.get("output_tokens")
    return prompt, completion


def _elapsed_ms(kwargs, start_time, end_time):
    try:
        if kwargs and kwargs.get("start_time") and kwargs.get("end_time"):
            return int((kwargs["end_time"] - kwargs["start_time"]).total_seconds() * 1000)
        if start_time and end_time:
            return int((end_time - start_time).total_seconds() * 1000)
    except Exception:
        pass
    return 0


def _endpoint_label(payload):
    """litellm 的回调不一定带 api_base → 回落到 yaml 里该路由的 base（再归一成 host）。"""
    base = str(payload.get("api_base") or payload.get("base_url") or "")
    if not base:
        try:
            from niu_core.llm_client import compat

            base, _key, _model = compat.resolve(MODEL_LABEL)
        except Exception:
            base = ""
    return base


def log_success(kwargs=None, completion_response=None, start_time=None, end_time=None, **_extra):
    try:
        from niu_core.llm_client import call_log

        payload = _as_dict(kwargs)
        prompt_tokens, completion_tokens = _usage_pair(payload, completion_response)
        model = str(payload.get("model") or _attr_or_key(completion_response, "model") or "")
        call_log.record(
            logic_model=MODEL_LABEL, status="ok", caller=CALLER_LABEL,
            endpoint=_endpoint_label(payload),
            model=model, style="litellm",
            latency_ms=_elapsed_ms(payload, start_time, end_time),
            input_tokens=prompt_tokens, output_tokens=completion_tokens,
        )
    except Exception:
        pass


def log_failure(kwargs=None, completion_response=None, start_time=None, end_time=None, **_extra):
    try:
        from niu_core.llm_client import call_log

        payload = _as_dict(kwargs)
        error = payload.get("exception") or completion_response
        call_log.record(
            logic_model=MODEL_LABEL, status="error", caller=CALLER_LABEL,
            endpoint=_endpoint_label(payload),
            model=str(payload.get("model") or ""), style="litellm",
            latency_ms=_elapsed_ms(payload, start_time, end_time),
            error=error if isinstance(error, BaseException) else RuntimeError(str(error)[:200]),
        )
    except Exception:
        pass
