"""Admin console handlers for the unified LLM gateway (niu_core.llm_client).

Read-only introspection of config/models.yaml (logic models + endpoints) plus
safe write-back of model routing and new endpoints. API keys are NEVER
returned or stored — only their env var names.
"""
from __future__ import annotations

import copy
import json
import os
import re
import time
import urllib.request
from pathlib import Path

from niu_core.llm_client import NiuLLM, ConfigError
from niu_core.llm_client.compat import reset_for_tests as _compat_reset

from server.action_handlers import register_handler

_MODELS_YAML_HINTS = (
    "Set NIU_LLM_CONFIG or create config/models.yaml",
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODELS_YAML = _REPO_ROOT / "config" / "models.yaml"


def _safe_name(value: str, limit: int = 64) -> str:
    value = str(value or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_\-]{1,%d}" % limit, value):
        raise ValueError("只允许小写字母数字下划线且不超过 %d 字符" % limit)
    return value


def _safe_env_name(value: str, limit: int = 80) -> str:
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]{0,%d}" % (limit - 1), str(value)):
        raise ValueError("API key 环境变量名必须是大写字母数字下划线")
    return str(value)


def _safe_url(value: str) -> str:
    value = str(value or "").strip().rstrip("/")
    if not re.match(r"^https?://[A-Za-z0-9.\-]+(?::\d+)?(/[^?]*)?$", value):
        raise ValueError("base_url 必须是 http(s) URL")
    return value


def _config_data() -> dict:
    try:
        import yaml
        return yaml.safe_load(_MODELS_YAML.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        raise ConfigError(f"models.yaml not found: {_MODELS_YAML}")
    except Exception as exc:
        raise ConfigError(f"models.yaml parse error: {exc}")


def _write_config(data: dict) -> None:
    import yaml
    tmp = _MODELS_YAML.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(_MODELS_YAML)
    # 让服务进程内的路由表立刻跟随本次写入：compat 缓存着 NiuLLM（旧路由），
    # 不失效的话管理台改完仍走老模型，必须重启服务才生效（2026-09-16 item 2）
    try:
        from niu_core.llm_client import compat as _compat
        _compat.reload()
    except Exception:
        pass


def _is_safe_endpoint_reference(endpoint: str, data: dict) -> tuple[bool, str]:
    if endpoint in (data.get("endpoints") or {}):
        return True, ""
    return False, f"endpoint '{endpoint}' 未定义"


def _routes_payload(data: dict) -> dict:
    endpoints = data.get("endpoints") or {}
    logic = data.get("logic_models") or {}
    configured_keys = []
    for name, spec in endpoints.items():
        env_name = spec.get("api_key_env") or ""
        key_present = False
        if env_name in os.environ:
            key_present = True
        else:
            env_source = Path("/home/ubuntu/vibe_proj/niu-secretary/config/.env")
            try:
                for line in env_file(env_name).read_text(encoding="utf-8").splitlines():
                    if line.startswith(f"{env_name}="):
                        key_present = True
            except Exception:
                pass
        configured_keys.append({
            "name": name,
            "baseUrl": spec.get("base_url", ""),
            "style": spec.get("style", "chat_completions"),
            "api_key_env": env_name,
            "apiKeySet": key_present,
            "timeout": spec.get("timeout_s", 120),
            "allowedModels": spec.get("allowed_models") or [],
        })
    items = []
    for name, spec in logic.items():
        fallbacks = spec.get("fallback") or []
        items.append({
            "name": name,
            "endpoint": spec.get("endpoint"),
            "model": spec.get("model"),
            "style": spec.get("style", ""),
            "maxRetries": spec.get("max_retries", 2),
            "timeout": spec.get("timeout_s") or endpoints.get(spec.get("endpoint"), {}).get("timeout_s", 120),
            "fallbacks": fallbacks,
        })
    return {"ok": True, "action": "llm.routes.list", "routes": items, "endpoints": configured_keys}


def registry():
    return []


def env_file(name: str) -> Path:
    return _REPO_ROOT / "config" / ".env"


@register_handler("llm.routes.list")
def llm_routes_list_handler(payload: dict, context: dict) -> dict:
    """Read-only dump of logic-model routes + endpoints (keys masked)."""
    data = _config_data()
    return _routes_payload(data)


@register_handler("llm.usage.report")
def llm_usage_report_handler(payload: dict, context: dict) -> dict:
    """统一层调用记录汇总（只读）——谁在用什么模型、失败率、备选率、token 用量。"""
    from niu_core.llm_client import call_log

    days = int(payload.get("days") or 7)
    limit = int(payload.get("limit") or 20)
    if days not in (1, 7, 30, 90):
        days = 7
    return {"ok": True, "action": "llm.usage.report", **call_log.summary(days=days, limit=limit)}


def _live_probe(endpoint_name: str, base_url: str, api_key: str, timeout: float = 10.0) -> dict:
    """Try GET {base_url}/models; return status + model ids."""
    url = f"{base_url.rstrip('/')}/models"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "NiuSecretary-LLM/1.0 (Hermes)",
            "Accept": "application/json",
        },
        method="GET",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            latency = int((time.monotonic() - started) * 1000)
            ids = [m.get("id") for m in (body.get("data") or []) if m.get("id")]
            return {"ok": True, "status": "reachable", "http": resp.status,
                    "latencyMs": int((time.monotonic() - started) * 1000),
                    "modelCount": len(ids), "models": ids[:100]}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:200]
        return {"ok": False, "status": "auth_or_url_error", "http": exc.code, "detail": detail}
    except Exception as exc:
        return {"ok": False, "status": "unreachable", "detail": str(exc)[:200]}


@register_handler("llm.endpoint.test")
def llm_endpoint_test_handler(payload: dict, context: dict) -> dict:
    """Test catalog / reachability for one endpoint (existing or probe new)."""
    data = _config_data()
    endpoints = data.get("endpoints") or {}
    name = _safe_name(payload.get("endpoint") or "")
    spec = endpoints.get(name)
    api_key = payload.get("apiKey") or ""
    api_key_env = payload.get("apiKeyEnv") or ""
    if not api_key and spec:
        api_key_env = api_key_env or spec.get("api_key_env") or ""
        if api_key_env in os.environ:
            api_key = os.environ[api_key_env]
        else:
            for line in env_file(api_key_env).read_text(encoding="utf-8").splitlines():
                if line.startswith(f"{api_key_env}="):
                    api_key = line.split("=", 1)[1].strip()
                    api_key = api_key.strip('"').strip("'")
    base_url = _safe_url(payload.get("baseUrl") or (spec.get("base_url") if spec else ""))
    if not api_key:
        return {"ok": False, "action": "llm.endpoint.test",
                "error": "missing_key",
                "message": f"缺少 API key：环境变量 {api_key_env} 未设置或请求体未带 apiKey"}
    result = _live_probe(name, base_url, api_key,
                         timeout=float(payload.get("timeout_s") or 10))
    return {"ok": True, "action": "llm.endpoint.test", "endpoint": name,
            "baseUrl": base_url, **result}


@register_handler("llm.endpoint.whitelist")
def llm_endpoint_whitelist_handler(payload: dict, context: dict) -> dict:
    """Set the exposed-model whitelist for an endpoint.

    Empty/absent list = expose everything (passthrough). Stored in
    models.yaml as endpoint.allowed_models. Route dropdowns honour this.
    """
    data = _config_data()
    endpoints = data.get("endpoints") or {}
    name = _safe_name(payload.get("endpoint") or "")
    if name not in endpoints:
        raise ValueError(f"endpoint '{name}' 不存在")
    raw = payload.get("models")
    if raw is None or raw == "":
        endpoints[name].pop("allowed_models", None)
    else:
        if not isinstance(raw, list):
            raise ValueError("models 需要数组")
        cleaned = []
        for m in raw:
            m = str(m).strip()[:80]
            if m and m not in cleaned:
                cleaned.append(m)
        endpoints[name]["allowed_models"] = cleaned
    _write_config(data)
    return {"ok": True, "action": "llm.endpoint.whitelist", "endpoint": name,
            "allowedModels": endpoints[name].get("allowed_models") or []}


@register_handler("llm.endpoint.upsert")
def llm_endpoint_upsert_handler(payload: dict, context: dict) -> dict:
    """Add/update third-party endpoint. Only updates env var NAME never the key value."""
    data = _config_data()
    endpoints = data.setdefault("endpoints", {})
    name = _safe_name(payload.get("endpoint") or "")
    if not name:
        raise ValueError("endpoint 名必填")
    base_url = _safe_url(payload.get("baseUrl"))
    env_var = _safe_env_name(payload.get("apiKeyEnv") or f"{name.upper()}_API_KEY")
    if payload.get("apiKey"):
        _patch_env_file(env_var, payload["apiKey"])

    # 合并写回：整体覆盖会连带抹掉 allowed_models（模型白名单）等未在表单里的键（2026-09-16 修）
    merged = dict(endpoints.get(name) or {})
    merged.update({
        "base_url": base_url,
        "api_key_env": env_var,
        "style": payload.get("style") or "chat_completions",
        "timeout_s": float(payload.get("timeout_s") or 120),
    })
    endpoints[name] = merged
    _write_config(data)
    return {"ok": True, "action": "llm.endpoint.upsert", "endpoint": name, "baseUrl": base_url,
            "apiKeyEnv": env_var}


@register_handler("llm.endpoint.delete")
def llm_endpoint_delete_handler(payload: dict, context: dict) -> dict:
    """Delete endpoint; block if any logic model still references it."""
    data = _config_data()
    endpoints = data.get("endpoints") or {}
    name = _safe_name(payload.get("endpoint") or "")
    if name not in endpoints:
        raise ValueError(f"endpoint '{name}' 不存在")
    for lname, spec in (data.get("logic_models") or {}).items():
        if spec.get("endpoint") == name:
            raise ValueError(f"逻辑模型 {lname} 还在使用该 endpoint，先改路由再删除")
    endpoints.pop(name)
    _write_config(data)
    return {"ok": True, "action": "llm.endpoint.delete", "endpoint": name}


@register_handler("llm.route.update")
def llm_route_update_handler(payload: dict, context: dict) -> dict:
    """Update a logic model's primary endpoint/model or its fallback list."""
    data = _config_data()
    logic = data.setdefault("logic_models", {})
    name = _safe_name(payload.get("route") or "")
    if name not in logic:
        raise ValueError(f"logic model '{name}' 不存在")
    spec = logic[name]
    new_endpoint = _safe_name(payload.get("endpoint") or "")
    ok, err = _is_safe_endpoint_reference(new_endpoint, data)
    if not ok:
        raise ValueError(err)
    spec["endpoint"] = new_endpoint
    if payload.get("model"):
        spec["model"] = str(payload["model"]).strip()[:80]
    if payload.get("style") in ("chat_completions", "responses"):
        spec["style"] = payload["style"]
    raw_fb = payload.get("fallbacks") or []
    cleaned_fb = []
    for fb in raw_fb:
        if not isinstance(fb, dict):
            continue
        fb_ep = _safe_name(fb.get("endpoint") or "")
        f_ok, f_err = _is_safe_endpoint_reference(fb_ep, data)
        if not f_ok:
            raise ValueError(f"fallback 引用无效 endpoint: {f_err}")
        fb_model = str(fb.get("model") or "").strip()[:80]
        if fb_model:
            cleaned_fb.append({"endpoint": fb_ep, "model": fb_model})
    if cleaned_fb:
        spec["fallback"] = cleaned_fb
    else:
        spec.pop("fallback", None)
    _write_config(data)
    return {"ok": True, "action": "llm.route.update", "route": name,
            "endpoint": spec["endpoint"], "model": spec.get("model"), "fallbacks": spec.get("fallback", [])}


@register_handler("llm.probe.live")
def llm_probe_live_handler(payload: dict, context: dict) -> dict:
    """Send a tiny live chat against a logic model (or explicit endpoint+model)."""
    logic_name = _safe_name(payload.get("route") or "")
    lm_specs = _config_data().get("logic_models") or {}
    if logic_name not in lm_specs:
        raise ValueError(f"logic model '{logic_name}' 不存在")
    prompt = str(payload.get("prompt") or "回复: pong")
    llm = NiuLLM.load()
    t0 = time.monotonic()
    try:
        rsp = llm.chat(logic_name, [{"role": "user", "content": prompt}], temperature=0)
        took_ms = int((time.monotonic() - t0) * 1000)
        return {"ok": True, "action": "llm.probe.live", "route": logic_name,
                "endpoint": rsp.endpoint, "model": rsp.model,
                "latencyMs": took_ms, "reply": rsp.text[:300]}
    except Exception as exc:
        return {"ok": False, "action": "llm.probe.live", "route": logic_name,
                "error": str(exc)[:300]}


@register_handler("llm.endpoint.models")
def llm_endpoint_models_handler(payload: dict, context: dict) -> dict:
    """Fetch the live model catalog for an endpoint (for select dropdowns).

    Same credential resolution as llm.endpoint.test but returns only the ids,
    trimmed/sorted for dropdown use. Not cached server-side: the payload is
    tiny and users expect «refresh = fresh».
    """
    data = _config_data()
    endpoints = data.get("endpoints") or {}
    name = _safe_name(payload.get("endpoint") or "")
    spec = endpoints.get(name)
    if not spec:
        raise ValueError(f"endpoint '{name}' 不存在")
    api_key = payload.get("apiKey") or ""
    api_key_env = spec.get("api_key_env") or ""
    if not api_key:
        if api_key_env in os.environ:
            api_key = os.environ[api_key_env]
        else:
            for line in env_file(api_key_env).read_text(encoding="utf-8").splitlines():
                if line.startswith(f"{api_key_env}="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
    base_url = _safe_url(payload.get("baseUrl") or spec.get("base_url") or "")
    result = _live_probe(name, base_url, api_key,
                         timeout=float(payload.get("timeout_s") or 10))
    if not result.get("ok"):
        return {"ok": False, "action": "llm.endpoint.models", "endpoint": name,
                "error": result.get("status") or result.get("detail", "unreachable")}
    models = sorted(result.get("models") or [])
    return {"ok": True, "action": "llm.endpoint.models", "endpoint": name,
            "modelCount": len(models), "models": models}


def _patch_env_file(key: str, value: str) -> None:
    env = env_file(key)
    lines = env.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(r"^" + re.escape(key) + "=")
    replacement = f"{key}={value}"
    replaced = False
    out = []
    for line in lines:
        if pattern.match(line):
            out.append(replacement)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(replacement)
    env.write_text("\n".join(out) + "\n", encoding="utf-8")
    env.chmod(0o600)
