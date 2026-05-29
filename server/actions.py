"""Action registry and dispatcher for Niu Secretary 2.0."""

from __future__ import annotations

from typing import Callable

from server.capabilities import get_capability
from server import store


class ActionError(Exception):
    """Action execution error with structured payload."""
    
    def __init__(self, error: str, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.error = error
        self.message = message
        self.status = status
        self.details = details or {}

    def to_payload(self) -> dict:
        payload = {"ok": False, "error": self.error, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


# Action handler registry
_HANDLERS: dict[str, Callable] = {}


def register_handler(action_name: str):
    """Decorator to register an action handler."""
    def decorator(func: Callable):
        _HANDLERS[action_name] = func
        return func
    return decorator


def execute_action(action_name: str, payload: dict, context: dict | None = None) -> dict:
    """Execute an action with validation, logging, and error handling."""
    payload = payload or {}
    context = context or {}
    
    try:
        result = _dispatch(action_name, payload, context)
        store.log_action(action_name, "ok", {"input": payload, "context": context}, result)
        return result
    except ActionError as exc:
        store.log_action(action_name or "unknown", "error", {"input": payload, "context": context}, {}, exc.error)
        raise
    except Exception as exc:
        store.log_action(action_name or "unknown", "error", {"input": payload, "context": context}, {}, "action_failed")
        raise ActionError("action_failed", "动作执行失败，请稍后重试。", 500, {"detail": str(exc)}) from exc


def _dispatch(action_name: str, payload: dict, context: dict) -> dict:
    """Validate and dispatch to the appropriate handler."""
    capability = get_capability(action_name)
    if not capability:
        raise ActionError("unknown_action", f"未知动作：{action_name}", 404, {"action": action_name})
    
    validate_required(capability, payload)
    
    handler = _HANDLERS.get(action_name)
    if not handler:
        raise ActionError("unknown_action", f"动作尚未实现：{action_name}", 404, {"action": action_name})
    
    return handler(payload, context)


def validate_required(capability: dict, payload: dict) -> None:
    """Validate that all required fields are present."""
    required = capability.get("inputSchema", {}).get("required", [])
    for field in required:
        value = payload.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ActionError("validation_failed", f"缺少 {field} 字段。", 400, {"field": field})


# Import handlers to trigger registration
from server import action_handlers  # noqa: E402, F401
