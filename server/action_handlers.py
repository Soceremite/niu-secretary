"""Action handlers for Niu Secretary 2.0."""

from __future__ import annotations

import html as html_lib
import json
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


@register_handler("fitness.nutrition.list")
def list_nutrition(payload: dict, context: dict) -> dict:
    """List nutrition logs within an optional date range."""
    items = store.list_nutrition_logs(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "fitness.nutrition.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条营养记录。",
    }


@register_handler("fitness.nutrition.delete")
def delete_nutrition(payload: dict, context: dict) -> dict:
    """Delete a nutrition log by id."""
    record_id = clean_text(payload.get("id"), 80)
    removed = store.delete_nutrition_log(record_id)
    if not removed:
        raise ActionError("not_found", "未找到该营养记录。", 404, {"id": record_id})
    return {
        "ok": True,
        "action": "fitness.nutrition.delete",
        "id": record_id,
        "message": "已从塑形馆删除该营养记录。",
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


@register_handler("schedule.event.list")
def list_schedule_events_handler(payload: dict, context: dict) -> dict:
    """List schedule events within an optional date range."""
    items = store.list_schedule_events(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "schedule.event.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 个日程。",
    }


@register_handler("schedule.event.delete")
def delete_schedule_event_handler(payload: dict, context: dict) -> dict:
    """Delete a schedule event by id."""
    record_id = clean_text(payload.get("id"), 80)
    removed = store.delete_schedule_event(record_id)
    if not removed:
        raise ActionError("not_found", "未找到该日程。", 404, {"id": record_id})
    return {
        "ok": True,
        "action": "schedule.event.delete",
        "id": record_id,
        "message": "已从时务局删除该日程。",
    }


@register_handler("schedule.todo.list")
def list_schedule_todos_handler(payload: dict, context: dict) -> dict:
    """List todos within an optional date range."""
    include_done = payload.get("includeDone")
    items = store.list_schedule_todos(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        True if include_done is None else bool(include_done),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "schedule.todo.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 个待办。",
    }


@register_handler("schedule.todo.toggle")
def toggle_schedule_todo_handler(payload: dict, context: dict) -> dict:
    """Toggle or set a todo's done state."""
    record_id = clean_text(payload.get("id"), 80)
    done = payload.get("done")
    if done is None:
        # No explicit state: flip current value.
        current = next(
            (t for t in store.list_schedule_todos() if t["id"] == record_id), None
        )
        if current is None:
            raise ActionError("not_found", "未找到该待办。", 404, {"id": record_id})
        done = not current["done"]
    record = store.set_schedule_todo_done(record_id, bool(done))
    if record is None:
        raise ActionError("not_found", "未找到该待办。", 404, {"id": record_id})
    return {
        "ok": True,
        "action": "schedule.todo.toggle",
        "record": record,
        "message": f"待办「{record['title']}」已标记为{'完成' if record['done'] else '未完成'}。",
    }


@register_handler("schedule.todo.delete")
def delete_schedule_todo_handler(payload: dict, context: dict) -> dict:
    """Delete a todo by id."""
    record_id = clean_text(payload.get("id"), 80)
    removed = store.delete_schedule_todo(record_id)
    if not removed:
        raise ActionError("not_found", "未找到该待办。", 404, {"id": record_id})
    return {
        "ok": True,
        "action": "schedule.todo.delete",
        "id": record_id,
        "message": "已从时务局删除该待办。",
    }


# ============================================================================
# User Profile Actions (用户画像)
# ============================================================================

def _validate_module(value) -> str:
    module = clean_text(value, 40).lower()
    if module not in store.PROFILE_MODULES:
        raise ActionError(
            "validation_failed",
            f"未知板块：{module}。可选：{', '.join(store.PROFILE_MODULES)}。",
            400,
            {"field": "module"},
        )
    return module


@register_handler("profile.get")
def get_profile_handler(payload: dict, context: dict) -> dict:
    """Read one module profile, or all when module is omitted."""
    raw_module = str(payload.get("module") or "").strip()
    if not raw_module:
        return {
            "ok": True,
            "action": "profile.get",
            "profiles": store.get_all_profiles(),
            "message": "返回全部板块画像。",
        }
    module = _validate_module(raw_module)
    result = store.get_profile(module)
    return {
        "ok": True,
        "action": "profile.get",
        "module": module,
        "profile": result["profile"],
        "updatedAt": result["updatedAt"],
        "message": f"返回{module}板块画像。",
    }


@register_handler("profile.update")
def update_profile_handler(payload: dict, context: dict) -> dict:
    """Merge a patch into a module profile."""
    module = _validate_module(payload.get("module"))
    patch = payload.get("patch")
    if not isinstance(patch, dict) or not patch:
        raise ActionError("validation_failed", "patch 必须是非空对象。", 400, {"field": "patch"})
    summary = clean_text(payload.get("summary"), 200, allow_empty=True)
    source = clean_source(payload.get("source") or context.get("client"))
    result = store.update_profile(module, patch, summary, source)
    changed = result["changedFields"]
    if changed:
        msg = f"已更新{module}画像：{ '、'.join(changed) }。"
    else:
        msg = f"{module}画像无变化（值与现状相同）。"
    return {
        "ok": True,
        "action": "profile.update",
        "module": module,
        "profile": result["profile"],
        "changedFields": changed,
        "message": msg,
    }


@register_handler("profile.reset")
def reset_profile_handler(payload: dict, context: dict) -> dict:
    """Reset a module profile to default."""
    module = _validate_module(payload.get("module"))
    source = clean_source(payload.get("source") or context.get("client"))
    result = store.reset_profile(module, source)
    return {
        "ok": True,
        "action": "profile.reset",
        "module": module,
        "profile": result["profile"],
        "message": f"已将{module}画像重置为默认值。",
    }


@register_handler("profile.changes")
def profile_changes_handler(payload: dict, context: dict) -> dict:
    """Read profile change history."""
    raw_module = str(payload.get("module") or "").strip()
    module = _validate_module(raw_module) if raw_module else ""
    items = store.list_profile_changes(module, clamp(payload.get("limit") or 50, 1, 500))
    return {
        "ok": True,
        "action": "profile.changes",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条画像变更记录。",
    }


# ============================================================================
# Recommendation Actions (画像驱动推送)
# ============================================================================

@register_handler("fitness.recommend")
def fitness_recommend_handler(payload: dict, context: dict) -> dict:
    """Generate today's fitness suggestions from the profile."""
    target_date = clean_optional_date(payload.get("date")) or date.today().isoformat()
    profile = store.get_profile("fitness")["profile"]
    summary = store.nutrition_summary(target_date)
    tips = _build_fitness_tips(profile, summary)
    return {
        "ok": True,
        "action": "fitness.recommend",
        "module": "fitness",
        "date": target_date,
        "profile": profile,
        "summary": summary,
        "recommendations": tips,
        "message": f"为你生成了 {len(tips)} 条今日塑形建议。",
    }


def _build_fitness_tips(profile: dict, summary: dict) -> list[str]:
    tips: list[str] = []
    goal = profile.get("goal") or "maintain"
    goal_label = {
        "fat_loss": "减脂",
        "muscle_gain": "增肌",
        "recomp": "身体重组",
        "maintain": "维持",
    }.get(goal, goal)
    target_cal = int(profile.get("targetCalories") or 0)
    eaten = int(summary.get("calories") or 0)
    if target_cal > 0:
        remaining = target_cal - eaten
        if goal == "fat_loss" and remaining < 0:
            tips.append(f"今日热量已超出目标 {abs(remaining)} 千卡，晚餐建议以蛋白质+蕨菜为主。")
        else:
            tips.append(f"目标{goal_label}：今日还有 {max(remaining, 0)} 千卡预算。")
    else:
        tips.append(f"目标{goal_label}。设定一个每日热量目标后，我能给你更精准的饮食建议。")
    protein_target = int(profile.get("proteinTarget") or 0)
    if protein_target > 0:
        tips.append(f"蛋白质目标 {protein_target}g，优先选鸡胸/鱼虑/豆制品/低脂乳制品。")
    diet_style = profile.get("dietStyle")
    if diet_style:
        tips.append(f"口味偏好：{diet_style}，可在此基础上控油控糖。")
    restrictions = profile.get("restrictions") or []
    if restrictions:
        tips.append(f"避开：{ '、'.join(restrictions) }。")
    return tips


@register_handler("schedule.recommend")
def schedule_recommend_handler(payload: dict, context: dict) -> dict:
    """Generate today's schedule suggestions from the profile."""
    target_date = clean_optional_date(payload.get("date")) or date.today().isoformat()
    profile = store.get_profile("schedule")["profile"]
    summary = store.schedule_summary(target_date)
    tips = _build_schedule_tips(profile, summary)
    return {
        "ok": True,
        "action": "schedule.recommend",
        "module": "schedule",
        "date": target_date,
        "profile": profile,
        "summary": summary,
        "recommendations": tips,
        "message": f"为你生成了 {len(tips)} 条今日日程建议。",
    }


def _build_schedule_tips(profile: dict, summary: dict) -> list[str]:
    tips: list[str] = []
    events = summary.get("events") or []
    todos = [t for t in (summary.get("todos") or []) if not t.get("done")]
    work_hours = profile.get("workHours")
    if work_hours:
        tips.append(f"工作时段 {work_hours}，今日共 {len(events)} 个日程、{len(todos)} 个待办。")
    else:
        tips.append(f"今日共 {len(events)} 个日程、{len(todos)} 个待办。")
    focus_blocks = profile.get("focusBlocks") or []
    for block in focus_blocks[:3]:
        tips.append(f"专注安排：{block}。")
    priorities = profile.get("priorities") or []
    if priorities:
        tips.append(f"优先事项：{ '、'.join(priorities[:3]) }，建议今日推进。")
    reminder_style = profile.get("reminderStyle")
    if reminder_style and events:
        tips.append(f"提醒偏好：{reminder_style}。")
    return tips


# ============================================================================
# News recommendation (画像驱动新闻精选)
# ============================================================================

# section id -> 中文板块名（与 news-daily 栏目对应）
_NEWS_SECTIONS = {
    "domestic": "国内要闻",
    "international": "国际焦点",
    "finance": "财经快讯",
    "tech": "科技动态",
    "ai": "人工智能",
}

_NEWS_CARD_BLOCK_RE = re.compile(r'<div class="news-card">(?P<body>.*?)</div>\s*</a>', re.DOTALL)
_NEWS_TAG_RE = re.compile(r'<span class="tag[^"]*">(?P<tag>.*?)</span>', re.DOTALL)
_NEWS_TITLE_RE = re.compile(r"<h3>(?P<title>.*?)</h3>", re.DOTALL)
_NEWS_SUMMARY_RE = re.compile(r'<p class="card-summary">(?P<summary>.*?)</p>', re.DOTALL)


def _strip_html(raw: str) -> str:
    """Remove tags/emoji-safe text and collapse whitespace."""
    text = re.sub(r"<[^>]+>", "", raw or "")
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _load_news_cards() -> list[dict]:
    """Parse today's news cards from news-daily section HTML. Read-only, best-effort."""
    cards: list[dict] = []
    sections_dir = store.PROJECT_ROOT / "news-daily" / "dist" / "sections"
    for section_id, section_label in _NEWS_SECTIONS.items():
        path = sections_dir / f"{section_id}.html"
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for block in _NEWS_CARD_BLOCK_RE.finditer(content):
            body = block.group("body")
            tag = _NEWS_TAG_RE.search(body)
            title = _NEWS_TITLE_RE.search(body)
            summary = _NEWS_SUMMARY_RE.search(body)
            if not (tag and title and summary):
                continue
            cards.append(
                {
                    "section": section_id,
                    "sectionLabel": section_label,
                    "tag": _strip_html(tag.group("tag")),
                    "title": _strip_html(title.group("title")),
                    "summary": _strip_html(summary.group("summary")),
                }
            )
    return cards


def _score_news_card(card: dict, topics: list[str], exclude: list[str],
                     regions: list[str]) -> int:
    """Score a news card against the news profile. Negative => filtered out."""
    haystack = " ".join(
        [card.get("tag", ""), card.get("title", ""), card.get("summary", ""),
         card.get("sectionLabel", "")]
    ).lower()
    for term in exclude:
        term = str(term).strip().lower()
        if term and term in haystack:
            return -1
    score = 0
    for term in topics:
        term = str(term).strip().lower()
        if not term:
            continue
        if term in card.get("tag", "").lower():
            score += 3
        if term in card.get("title", "").lower():
            score += 2
        if term in card.get("summary", "").lower():
            score += 1
    for term in regions:
        term = str(term).strip().lower()
        if term and term in haystack:
            score += 1
    return score


@register_handler("news.recommend")
def news_recommend_handler(payload: dict, context: dict) -> dict:
    """Pick today's news matching the news profile (topics/excludeTopics)."""
    limit = clamp(payload.get("limit") or 8, 1, 30)
    profile = store.get_profile("news")["profile"]
    topics = [t for t in (profile.get("topics") or []) if str(t).strip()]
    exclude = [t for t in (profile.get("excludeTopics") or []) if str(t).strip()]
    regions = [r for r in (profile.get("regions") or []) if str(r).strip()]
    cards = _load_news_cards()

    scored = []
    for card in cards:
        score = _score_news_card(card, topics, exclude, regions)
        if score < 0:
            continue
        scored.append((score, card))

    if topics:
        # Profile has interests: prefer matches, keep only scored>0 when any matched.
        matched = [item for item in scored if item[0] > 0]
        chosen = matched if matched else scored
        personalized = bool(matched)
    else:
        chosen = scored
        personalized = False

    chosen.sort(key=lambda item: item[0], reverse=True)
    items = [
        {**card, "matchScore": score}
        for score, card in chosen[:limit]
    ]
    if topics and personalized:
        msg = f"按你关注的「{ '、'.join(topics) }」精选了 {len(items)} 条今日新闻。"
    elif topics:
        msg = f"今日新闻里暂无完全匹配你关注话题的内容，先返回 {len(items)} 条要闻。"
    else:
        msg = f"返回今日要闻 {len(items)} 条。和牛秘书 AI 聊聊你关注的话题，就能个性化精选。"
    return {
        "ok": True,
        "action": "news.recommend",
        "module": "news",
        "profile": profile,
        "personalized": personalized,
        "items": items,
        "count": len(items),
        "message": msg,
    }


# ============================================================================
# Leisure recommendation (画像驱动闲趣精选)
# ============================================================================

# leisure profile genres key -> (data file, content type label)
_LEISURE_CATEGORIES = (
    ("movie", "movies.json", "影视"),
    ("music", "music.json", "音乐"),
    ("podcast", "podcasts.json", "播客"),
    ("novel", "novels.json", "小说"),
)


def _load_leisure_items(filename: str) -> list[dict]:
    """Load a leisure data file. Handles both list and {items:[...]} shapes."""
    path = store.PROJECT_ROOT / "leisure" / "dist" / "data" / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("items") or []
    return data if isinstance(data, list) else []


def _item_genres(item: dict) -> list[str]:
    """Normalize an item's genres to a list (handles 'genres' list or 'genre' str)."""
    genres = item.get("genres")
    if isinstance(genres, list):
        return [str(g) for g in genres]
    single = item.get("genre")
    return [str(single)] if single else []


def _score_leisure_item(item: dict, want_genres: list[str], moods: list[str],
                        avoid: list[str]) -> int:
    """Score a leisure item against the leisure profile. Negative => filtered out."""
    item_genres = [g.lower() for g in _item_genres(item)]
    item_mood = str(item.get("mood") or "").lower()
    for term in avoid:
        term = str(term).strip().lower()
        if term and (term in item_genres or term == item_mood):
            return -1
    score = 0
    for term in want_genres:
        term = str(term).strip().lower()
        if term and term in item_genres:
            score += 3
    for term in moods:
        term = str(term).strip().lower()
        if term and term == item_mood:
            score += 2
    # Use baked-in matchScore as a gentle tiebreaker (0-100 -> 0-1 bucket).
    score += int(item.get("matchScore") or 0) // 50
    return score


@register_handler("leisure.recommend")
def leisure_recommend_handler(payload: dict, context: dict) -> dict:
    """Pick leisure items matching the leisure profile (genres/moods/avoid)."""
    per_category = clamp(payload.get("limit") or 3, 1, 10)
    profile = store.get_profile("leisure")["profile"]
    genres_pref = profile.get("genres") or {}
    moods = [m for m in (profile.get("moods") or []) if str(m).strip()]
    avoid = [a for a in (profile.get("avoid") or []) if str(a).strip()]

    groups = []
    any_personalized = False
    for key, filename, label in _LEISURE_CATEGORIES:
        items = _load_leisure_items(filename)
        if not items:
            continue
        want = genres_pref.get(key) or [] if isinstance(genres_pref, dict) else []
        want = [g for g in want if str(g).strip()]
        scored = []
        for item in items:
            score = _score_leisure_item(item, want, moods, avoid)
            if score < 0:
                continue
            scored.append((score, item))
        matched = [s for s in scored if s[0] > 0]
        chosen = matched if matched else scored
        if matched:
            any_personalized = True
        chosen.sort(key=lambda s: s[0], reverse=True)
        picked = [
            {
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "genres": _item_genres(item),
                "mood": item.get("mood", ""),
                "reason": item.get("reason", ""),
                "matchScore": item.get("matchScore", score),
                "url": item.get("doubanUrl") or item.get("platformUrl") or "",
            }
            for score, item in chosen[:per_category]
        ]
        if picked:
            groups.append({"category": key, "label": label, "items": picked})

    total = sum(len(g["items"]) for g in groups)
    if any_personalized:
        msg = f"按你的口味档案精选了 {total} 条闲趣推荐。"
    elif total:
        msg = f"返回 {total} 条闲趣推荐。和牛秘书 AI 聊聊你爱看/爱听的，就能个性化精选。"
    else:
        msg = "暂无可推荐的闲趣内容。"
    return {
        "ok": True,
        "action": "leisure.recommend",
        "module": "leisure",
        "profile": profile,
        "personalized": any_personalized,
        "groups": groups,
        "count": total,
        "message": msg,
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
