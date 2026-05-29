"""Action handlers for Niu Secretary 2.0."""

from __future__ import annotations

import re
from datetime import date

from server.actions import register_handler, ActionError
from server import store


# ============================================================================
# Fitness Actions
# ============================================================================

@register_handler("fitness.nutrition.create")
def create_nutrition_log(payload: dict, context: dict) -> dict:
    """Create a nutrition log entry."""
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
        "action": "fitness.nutrition.create",
        "record": record,
        "message": f"已记录到塑形馆营养：{record['food']}。",
    }


@register_handler("fitness.nutrition.today_summary")
def get_nutrition_summary(payload: dict, context: dict) -> dict:
    """Get nutrition summary for a specific date."""
    summary = store.nutrition_summary(clean_date(payload.get("date")))
    return {
        "ok": True,
        "action": "fitness.nutrition.today_summary",
        "summary": summary,
        "message": f"{summary['date']} 已记录 {summary['count']} 餐，共 {summary['calories']} 千卡。",
    }


# ============================================================================
# Schedule Actions
# ============================================================================

@register_handler("schedule.event.create")
def create_schedule_event(payload: dict, context: dict) -> dict:
    """Create a schedule event."""
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
        "action": "schedule.event.create",
        "record": record,
        "message": f"已加入时务局日程：{record['date']}{time_label} {record['title']}。",
    }


@register_handler("schedule.todo.create")
def create_schedule_todo(payload: dict, context: dict) -> dict:
    """Create a schedule todo."""
    normalized = {
        "title": clean_text(payload.get("title"), 160),
        "date": clean_optional_date(payload.get("date")),
        "priority": clean_priority(payload.get("priority")),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    record = store.insert_schedule_todo(normalized)
    return {
        "ok": True,
        "action": "schedule.todo.create",
        "record": record,
        "message": f"已加入时务局待办：{record['title']}。",
    }


@register_handler("schedule.today_summary")
def get_schedule_summary(payload: dict, context: dict) -> dict:
    """Get schedule summary for a specific date."""
    summary = store.schedule_summary(clean_date(payload.get("date")))
    return {
        "ok": True,
        "action": "schedule.today_summary",
        "summary": summary,
        "message": f"{summary['date']} 有 {len(summary['events'])} 个日程、{len(summary['todos'])} 个待办。",
    }


# ============================================================================
# Validation Helpers
# ============================================================================

def clean_text(value, limit: int, allow_empty: bool = False) -> str:
    """Clean and validate text input."""
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if not text and not allow_empty:
        raise ActionError("validation_failed", "文本字段不能为空。", 400)
    return text[:limit]


def clean_date(value) -> str:
    """Clean and validate date input (required)."""
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ActionError("validation_failed", "日期必须使用 YYYY-MM-DD 格式。", 400, {"field": "date"})
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ActionError("validation_failed", "日期不是有效日期。", 400, {"field": "date"}) from exc
    return text


def clean_optional_date(value) -> str:
    """Clean and validate date input (optional)."""
    text = str(value or "").strip()
    return clean_date(text) if text else ""


def clean_time(value) -> str:
    """Clean and validate time input."""
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
    """Clean and validate priority input."""
    priority = str(value or "normal").strip().lower()
    return priority if priority in {"low", "normal", "high"} else "normal"


def clean_source(value) -> str:
    """Clean source identifier."""
    return clean_text(value or "action", 80)


def clamp(value, low: int, high: int) -> int:
    """Clamp a numeric value within bounds."""
    try:
        number = round(float(value or 0))
    except (TypeError, ValueError):
        number = 0
    return max(low, min(high, number))
