"""Config loading for the unified LLM layer.

Reads config/models.yaml (endpoints + logic models) and resolves API keys
from the environment. Secrets never live in the yaml file.
"""
from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a hard dep of the platform
    yaml = None  # type: ignore[assignment]

from .errors import ConfigError

_STYLE_CHAT = "chat_completions"
_STYLE_RESPONSES = "responses"
_VALID_STYLES = (_STYLE_CHAT, _STYLE_RESPONSES)

# Search order: env override > repo-relative > ~/.niu/models.yaml
def default_config_paths() -> List[Path]:
    paths: List[Path] = []
    env_override = os.environ.get("NIU_LLM_CONFIG")
    if env_override:
        paths.append(Path(env_override))
    paths.append(Path(__file__).resolve().parents[2] / "config" / "models.yaml")
    paths.append(Path.home() / ".niu" / "models.yaml")
    return paths


@dataclasses.dataclass(frozen=True)
class EndpointConfig:
    name: str
    base_url: str
    api_key_env: str
    style: str = _STYLE_CHAT
    timeout_s: float = 120.0


@dataclasses.dataclass(frozen=True)
class FallbackEntry:
    endpoint: str
    model: str


@dataclasses.dataclass(frozen=True)
class LogicModel:
    name: str
    endpoint: str
    model: str
    style: str  # resolved from endpoint unless overridden
    timeout_s: float
    max_retries: int = 2
    fallback: Tuple[FallbackEntry, ...] = ()


@dataclasses.dataclass
class LLMConfig:
    endpoints: Dict[str, EndpointConfig]
    logic_models: Dict[str, LogicModel]
    default_endpoint: str

    @classmethod
    def load(cls, config_path: Optional[str | Path] = None) -> "LLMConfig":
        """Load and validate the models config.

        Raises ConfigError with an actionable message on any problem.
        Environment variables are NOT checked here (that happens at call time,
        so one missing key doesn't poison unrelated endpoints).
        """
        candidates = [Path(config_path)] if config_path else default_config_paths()
        yaml_path = next((p for p in candidates if p.is_file()), None)
        if yaml_path is None:
            tried = ", ".join(str(p) for p in candidates)
            raise ConfigError(
                f"models.yaml not found. Set NIU_LLM_CONFIG or place config at one of: {tried}"
            )
        if yaml is None:
            raise ConfigError("PyYAML is not installed; run: pip install pyyaml")

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {yaml_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"{yaml_path}: top level must be a mapping")

        raw_endpoints = data.get("endpoints") or {}
        if not raw_endpoints:
            raise ConfigError(f"{yaml_path}: 'endpoints' section is required")

        endpoints: Dict[str, EndpointConfig] = {}
        for name, spec in raw_endpoints.items():
            if not isinstance(spec, dict):
                raise ConfigError(f"endpoints.{name}: must be a mapping")
            missing = [k for k in ("base_url", "api_key_env") if not spec.get(k)]
            if missing:
                raise ConfigError(f"endpoints.{name}: missing required keys {missing}")
            style = str(spec.get("style") or _STYLE_CHAT)
            if style not in _VALID_STYLES:
                raise ConfigError(
                    f"endpoints.{name}: style must be one of {_VALID_STYLES}, got '{style}'"
                )
            endpoints[str(name)] = EndpointConfig(
                name=str(name),
                base_url=str(spec["base_url"]).rstrip("/"),
                api_key_env=str(spec["api_key_env"]),
                style=style,
                timeout_s=float(spec.get("timeout_s") or 120.0),
            )

        default_endpoint = str(data.get("default_endpoint") or "").strip() or None
        if default_endpoint and default_endpoint not in endpoints:
            raise ConfigError(
                f"{yaml_path}: default_endpoint '{default_endpoint}' is not a defined endpoint"
            )

        raw_models = data.get("logic_models") or {}
        if not raw_models:
            raise ConfigError(f"{yaml_path}: 'logic_models' section is required")

        logic_models: Dict[str, LogicModel] = {}
        for name, spec in raw_models.items():
            if not isinstance(spec, dict):
                raise ConfigError(f"logic_models.{name}: must be a mapping")
            endpoint = str(spec.get("endpoint") or default_endpoint or "")
            if not endpoint:
                raise ConfigError(
                    f"logic_models.{name}: no endpoint and no default_endpoint set"
                )
            if endpoint not in endpoints:
                raise ConfigError(
                    f"logic_models.{name}: references undefined endpoint '{endpoint}' "
                    f"(defined: {sorted(endpoints)})"
                )
            if not spec.get("model"):
                raise ConfigError(f"logic_models.{name}: 'model' is required")

            ep_cfg = endpoints[endpoint]
            style = str(spec.get("style") or ep_cfg.style)
            if style not in _VALID_STYLES:
                raise ConfigError(
                    f"logic_models.{name}: style must be one of {_VALID_STYLES}, got '{style}'"
                )

            fallback: Tuple[FallbackEntry, ...] = ()
            raw_fallback = spec.get("fallback") or []
            for i, fb in enumerate(raw_fallback):
                if not isinstance(fb, dict) or not fb.get("model"):
                    raise ConfigError(f"logic_models.{name}: fallback[{i}] must map with 'model'")
                fb_ep = str(fb.get("endpoint") or default_endpoint or "")
                if fb_ep not in endpoints:
                    raise ConfigError(
                        f"logic_models.{name}: fallback[{i}] references undefined endpoint '{fb_ep}'"
                    )
                fallback += (FallbackEntry(endpoint=fb_ep, model=str(fb["model"])),)

            logic_models[str(name)] = LogicModel(
                name=str(name),
                endpoint=endpoint,
                model=str(spec["model"]),
                style=style,
                timeout_s=float(spec.get("timeout_s") or ep_cfg.timeout_s),
                max_retries=2 if spec.get("max_retries") is None else int(spec["max_retries"]),
                fallback=fallback,
            )

        return cls(endpoints=endpoints, logic_models=logic_models,
                   default_endpoint=default_endpoint or "")

    def model(self, name: str) -> LogicModel:
        try:
            return self.logic_models[name]
        except KeyError:
            raise ConfigError(
                f"Unknown logic model '{name}'. Defined: {sorted(self.logic_models)}"
            ) from None

    def endpoint_for(self, entry: "LogicModel | FallbackEntry") -> EndpointConfig:
        return self.endpoints[entry.endpoint]

    def resolve_key(self, endpoint: EndpointConfig) -> str:
        """Resolve the API key for an endpoint at call time.

        api_key_env may list multiple env var names separated by commas —
        the first one that is set wins (reserve slot for key rotation).
        """
        value = os.environ.get(endpoint.api_key_env, "").strip()
        if not value:
            raise ConfigError(
                f"API key for endpoint '{endpoint.name}' is missing: set "
                f"{endpoint.api_key_env} in the environment (see config/.env)"
            )
        return value
