"""Common validation helpers for Niu Secretary module code."""

from __future__ import annotations

from datetime import date, time


class ValidationError(ValueError):
    """Raised when module input fails deterministic validation."""

    def __init__(self, message: str, field: str = ""):
        super().__init__(message)
        self.field = field


def require_text(value, field: str, limit: int = 500) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"{field} is required", field)
    return text[:limit]


def optional_text(value, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def require_date(value, field: str = "date") -> str:
    text = require_text(value, field, 20)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field} must be YYYY-MM-DD", field) from exc
    return text


def optional_date(value, field: str = "date") -> str:
    text = str(value or "").strip()
    return require_date(text, field) if text else ""


def optional_time(value, field: str = "time") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        time.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field} must be HH:MM", field) from exc
    if len(text) != 5:
        raise ValidationError(f"{field} must be HH:MM", field)
    return text


def clamp_int(value, low: int, high: int, default: int = 0) -> int:
    try:
        number = round(float(value))
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def require_choice(value, allowed: set[str], field: str, default: str = "") -> str:
    text = str(value or default).strip().lower()
    if text not in allowed:
        raise ValidationError(f"{field} must be one of: {', '.join(sorted(allowed))}", field)
    return text
