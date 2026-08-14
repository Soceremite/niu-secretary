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
    module = action_name.split(".", 1)[0] if action_name else "unknown"
    source = str(context.get("source") or context.get("client") or "api")
    request_id = str(context.get("requestId") or context.get("request_id") or "")
    capability = get_capability(action_name)
    requires_confirmation = _requires_confirmation(capability, context)
    confirmed = _is_confirmed(context)
    assistant_action = store.create_assistant_action(
        action_name or "unknown",
        payload,
        requires_confirmation,
        source,
        request_id,
        confirmed=confirmed,
    )
    module_run = store.start_module_run(
        module,
        action_name or "unknown",
        source,
        {"input": payload, "context": context, "actionId": assistant_action["id"]},
    )
    if requires_confirmation and not confirmed:
        result = {
            "ok": False,
            "error": "confirmation_required",
            "message": "该动作需要用户确认后才能执行。",
            "action": action_name,
            "actionId": assistant_action["id"],
            "auditId": module_run["id"],
            "requiresConfirmation": True,
            "warnings": [],
        }
        store.finish_assistant_action(assistant_action["id"], "blocked", result, "confirmation_required")
        store.finish_module_run(module_run["id"], "blocked", result, "confirmation_required")
        store.log_action(action_name or "unknown", "blocked", {"input": payload, "context": context}, result, "confirmation_required")
        return result
    
    try:
        result = _dispatch(action_name, payload, context)
        result.setdefault("actionId", assistant_action["id"])
        result.setdefault("auditId", module_run["id"])
        result.setdefault("warnings", [])
        store.finish_assistant_action(assistant_action["id"], "passed", result)
        store.finish_module_run(module_run["id"], "passed", result)
        store.log_action(action_name, "ok", {"input": payload, "context": context}, result)
        return result
    except ActionError as exc:
        store.finish_assistant_action(assistant_action["id"], "failed", {}, exc.error)
        store.finish_module_run(module_run["id"], "failed", {}, exc.error)
        store.log_action(action_name or "unknown", "error", {"input": payload, "context": context}, {}, exc.error)
        raise
    except Exception as exc:
        store.finish_assistant_action(assistant_action["id"], "failed", {}, "action_failed")
        store.finish_module_run(module_run["id"], "failed", {}, "action_failed")
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


def _requires_confirmation(capability: dict | None, context: dict) -> bool:
    explicit = context.get("requiresConfirmation")
    if explicit is None:
        explicit = context.get("requires_confirmation")
    if explicit is not None:
        return bool(explicit)
    if not capability or not capability.get("confirmByDefault"):
        return False
    # CLI/cron direct calls are explicit operational entrypoints. Web and assistant
    # calls must carry a confirmation flag before mutating high-risk state.
    source = str(context.get("source") or context.get("client") or "").lower()
    if not source:
        return False
    return source not in {"cli", "cron", "test"}


def _is_confirmed(context: dict) -> bool:
    return bool(
        context.get("confirmed")
        or context.get("confirmedAt")
        or context.get("confirmed_at")
        or context.get("userConfirmed")
        or context.get("user_confirmed")
    )


def validate_required(capability: dict, payload: dict) -> None:
    """Validate that all required fields are present."""
    required = capability.get("inputSchema", {}).get("required", [])
    for field in required:
        value = payload.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ActionError("validation_failed", f"缺少 {field} 字段。", 400, {"field": field})


# Import handlers to trigger registration
from server import action_handlers  # noqa: E402, F401
