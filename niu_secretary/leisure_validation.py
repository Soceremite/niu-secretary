from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from .leisure_quality import collect_movie_quality_errors


RECOMMENDATION_FILES = {
    "movies.json",
    "music.json",
    "podcasts.json",
    "novels.json",
}


def _load_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{path.name}: {exc}"


def _items_from_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]
    return []


def _is_article_like_url(value: str) -> bool:
    parsed = urlparse((value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    lowered_path = parsed.path.lower()
    if "search" in lowered_path and parsed.query:
        return False
    if lowered_path in {"", "/"} and not parsed.query and not parsed.fragment:
        return False
    return True


def _parse_iso_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def validate_leisure_data_dir(
    data_dir: Path,
    *,
    strict_content: bool = False,
    today: date | None = None,
) -> dict:
    checked: list[str] = []
    errors: list[str] = []
    payloads: dict[str, object] = {}

    for path in sorted(data_dir.glob("*.json")):
        payload, error = _load_json(path)
        if error:
            errors.append(error)
            continue
        if payload in ({}, []):
            errors.append(f"{path.name}: empty payload")
        checked.append(path.name)
        payloads[path.name] = payload

    if strict_content:
        errors.extend(_strict_content_errors(payloads, today=today or date.today()))

    return {"status": "passed" if not errors else "failed", "checked": checked, "errors": errors}


def _strict_content_errors(payloads: dict[str, object], *, today: date) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    context = payloads.get("context.json")
    if not isinstance(context, dict):
        errors.append("context.json: expected object")
    else:
        generated = _parse_iso_date(str(context.get("generated", "")))
        if not generated:
            errors.append("context.json: missing or invalid generated timestamp")
        elif generated > today + timedelta(days=1):
            errors.append(f"context.json: generated date is in the future: {generated.isoformat()}")
        elif generated < today - timedelta(days=14):
            errors.append(f"context.json: generated date is older than 14 days: {generated.isoformat()}")
        for key in ("schedule", "fitness", "moodProfile", "dailyNote", "recommendationStrategy"):
            if key not in context:
                errors.append(f"context.json: missing {key}")

    for file_name in sorted(RECOMMENDATION_FILES & payloads.keys()):
        items = _items_from_payload(payloads[file_name])
        if not items:
            errors.append(f"{file_name}: expected non-empty recommendation items")
            continue
        if file_name == "movies.json":
            errors.extend(collect_movie_quality_errors(items, require_any_cover=True))
        for index, item in enumerate(items, start=1):
            ident = str(item.get("id") or "").strip()
            label = f"{file_name}#{index}" if not ident else f"{file_name}:{ident}"
            if not ident:
                errors.append(f"{label}: missing id")
            elif ident in seen_ids:
                errors.append(f"{label}: duplicate id")
            seen_ids.add(ident)

            if not str(item.get("title") or "").strip():
                errors.append(f"{label}: missing title")
            if not str(item.get("reason") or "").strip():
                errors.append(f"{label}: missing reason")

            score = item.get("matchScore")
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                errors.append(f"{label}: invalid matchScore {score!r}")

            url_field = "doubanUrl" if file_name == "movies.json" else "platformUrl"
            url = str(item.get(url_field) or "").strip()
            if not _is_article_like_url(url):
                errors.append(f"{label}: invalid {url_field} {url!r}")

    return errors
