"""Action validation and execution for Niu Secretary 2.0."""

from __future__ import annotations

import re
from datetime import date

from server.capabilities import get_capability
from server import store


class ActionError(Exception):
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


def execute_action(action_name: str, payload: dict, context: dict | None = None) -> dict:
    payload = payload or {}
    context = context or {}
    try:
        result = _execute(action_name, payload, context)
        store.log_action(action_name, "ok", {"input": payload, "context": context}, result)
        return result
    except ActionError as exc:
        store.log_action(action_name or "unknown", "error", {"input": payload, "context": context}, {}, exc.error)
        raise
    except Exception as exc:
        store.log_action(action_name or "unknown", "error", {"input": payload, "context": context}, {}, "action_failed")
        raise ActionError("action_failed", "动作执行失败，请稍后重试。", 500, {"detail": str(exc)}) from exc


def _execute(action_name: str, payload: dict, context: dict) -> dict:
    capability = get_capability(action_name)
    if not capability:
        raise ActionError("unknown_action", f"未知动作：{action_name}", 404, {"action": action_name})
    validate_required(capability, payload)

    if action_name == "fitness.nutrition.create":
        normalized = {
            "food": clean_text(payload.get("food"), 160),
            "date": clean_date(payload.get("date")),
            "calories": clamp(payload.get("calories"), 0, 5000),
            "proteinG": clamp(payload.get("proteinG"), 0, 300),
            "carbsG": clamp(payload.get("carbsG"), 0, 600),
            "fatG": clamp(payload.get("fatG"), 0, 300),
            "source": clean_source(payload.get("source") or context.get("client")),
        }
        record = store.insert_nutrition_log(normalized)
        return {
            "ok": True,
            "action": action_name,
            "record": record,
            "message": f"已记录到塑形馆营养：{record['food']}。",
        }

    if action_name == "fitness.nutrition.today_summary":
        summary = store.nutrition_summary(clean_date(payload.get("date")))
        return {
            "ok": True,
            "action": action_name,
            "summary": summary,
            "message": f"{summary['date']} 已记录 {summary['count']} 餐，共 {summary['calories']} 千卡。",
        }

    if action_name == "schedule.event.create":
        normalized = {
            "title": clean_text(payload.get("title"), 160),
            "date": clean_date(payload.get("date")),
            "time": clean_time(payload.get("time")),
            "note": clean_text(payload.get("note"), 300, allow_empty=True),
            "source": clean_source(payload.get("source") or context.get("client")),
        }
        record = store.insert_schedule_event(normalized)
        time_label = f" {record['time']}" if record["time"] else ""
        return {
            "ok": True,
            "action": action_name,
            "record": record,
            "message": f"已加入时务局日程：{record['date']}{time_label} {record['title']}。",
        }

    if action_name == "schedule.todo.create":
        normalized = {
            "title": clean_text(payload.get("title"), 160),
            "date": clean_optional_date(payload.get("date")),
            "priority": clean_priority(payload.get("priority")),
            "source": clean_source(payload.get("source") or context.get("client")),
        }
        record = store.insert_schedule_todo(normalized)
        return {
            "ok": True,
            "action": action_name,
            "record": record,
            "message": f"已加入时务局待办：{record['title']}。",
        }

    if action_name == "schedule.today_summary":
        summary = store.schedule_summary(clean_date(payload.get("date")))
        return {
            "ok": True,
            "action": action_name,
            "summary": summary,
            "message": f"{summary['date']} 有 {len(summary['events'])} 个日程、{len(summary['todos'])} 个待办。",
        }

    raise ActionError("unknown_action", f"动作尚未实现：{action_name}", 404, {"action": action_name})


def validate_required(capability: dict, payload: dict) -> None:
    required = capability.get("inputSchema", {}).get("required", [])
    for field in required:
        value = payload.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ActionError("validation_failed", f"缺少 {field} 字段。", 400, {"field": field})


def clean_text(value, limit: int, allow_empty: bool = False) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if not text and not allow_empty:
        raise ActionError("validation_failed", "文本字段不能为空。", 400)
    return text[:limit]


def clean_date(value) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ActionError("validation_failed", "日期必须使用 YYYY-MM-DD 格式。", 400, {"field": "date"})
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ActionError("validation_failed", "日期不是有效日期。", 400, {"field": "date"}) from exc
    return text


def clean_optional_date(value) -> str:
    text = str(value or "").strip()
    return clean_date(text) if text else ""


def clean_time(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"\d{2}:\d{2}", text):
        raise ActionError("validation_failed", "时间必须使用 HH:MM 格式。", 400, {"field": "time"})
    hour, minute = (int(part) for part in text.split(":"))
    if hour > 23 or minute > 59:
        raise ActionError("validation_failed", "时间不是有效时间。", 400, {"field": "time"})
    return text


def clean_priority(value) -> str:
    priority = str(value or "normal").strip().lower()
    return priority if priority in {"low", "normal", "high"} else "normal"


def clean_source(value) -> str:
    return clean_text(value or "action", 80)


def clamp(value, low: int, high: int) -> int:
    try:
        number = round(float(value or 0))
    except (TypeError, ValueError):
        number = 0
    return max(low, min(high, number))
