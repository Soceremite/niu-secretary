"""Simple assistant intent parser for the first Niu Secretary 2.0 slice."""

from __future__ import annotations

import re
from datetime import date, timedelta

from server import store


MEAL_KEYWORDS = ("吃了", "早餐", "午餐", "晚餐", "夜宵", "加餐", "喝了")
EVENT_KEYWORDS = ("提醒", "日程", "开会", "会议", "约", "预约")
TODO_KEYWORDS = ("待办", "记得", "帮我记", "要做")

CALORIE_HINTS = {
    "牛肉面": (650, 32, 85, 18),
    "米饭": (280, 6, 62, 1),
    "鸡胸": (220, 42, 0, 5),
    "沙拉": (180, 8, 18, 8),
    "咖啡": (60, 2, 8, 2),
    "奶茶": (420, 7, 65, 14),
    "汉堡": (520, 24, 46, 26),
    "鸡蛋": (80, 7, 1, 5),
}

CHINESE_HOURS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
}


def handle_message(text: str, context: dict | None = None) -> dict:
    context = context or {}
    cleaned = normalize_text(text)
    if not cleaned:
        return {
            "reply": "我在。你可以直接说“我今天吃了牛肉面”或“明天下午三点提醒我开会”。",
            "intent": "empty",
            "proposedActions": [],
        }

    if contains_any(cleaned, MEAL_KEYWORDS):
        response = build_meal_response(cleaned, context)
    elif contains_any(cleaned, EVENT_KEYWORDS):
        response = build_event_response(cleaned, context)
    elif contains_any(cleaned, TODO_KEYWORDS):
        response = build_todo_response(cleaned, context)
    else:
        response = {
            "reply": "这句话我先记为普通咨询。v2.0 第一阶段已支持记录餐食、创建日程和创建待办。",
            "intent": "chat",
            "proposedActions": [],
        }

    store.insert_assistant_message(cleaned, response["reply"], response["proposedActions"])
    return response


def build_meal_response(text: str, context: dict) -> dict:
    food = extract_food(text)
    calories, protein, carbs, fat = estimate_meal(food)
    target_date = parse_relative_date(text)
    action = {
        "action": "fitness.nutrition.create",
        "input": {
            "food": food,
            "date": target_date,
            "calories": calories,
            "proteinG": protein,
            "carbsG": carbs,
            "fatG": fat,
            "source": context.get("client") or "assistant-estimate",
        },
        "requiresConfirmation": True,
    }
    return {
        "reply": f"我估算“{food}”约 {calories} 千卡。确认后会写入塑形馆营养日志。",
        "intent": "record_meal",
        "proposedActions": [action],
    }


def build_event_response(text: str, context: dict) -> dict:
    title = extract_event_title(text)
    target_date = parse_relative_date(text)
    target_time = parse_time(text)
    action = {
        "action": "schedule.event.create",
        "input": {
            "title": title,
            "date": target_date,
            "time": target_time,
            "note": text,
            "source": context.get("client") or "assistant",
        },
        "requiresConfirmation": True,
    }
    time_label = f" {target_time}" if target_time else ""
    return {
        "reply": f"我准备把“{title}”加入时务局日程：{target_date}{time_label}。",
        "intent": "create_schedule_event",
        "proposedActions": [action],
    }


def build_todo_response(text: str, context: dict) -> dict:
    title = extract_todo_title(text)
    target_date = parse_relative_date(text) if has_date_word(text) else ""
    action = {
        "action": "schedule.todo.create",
        "input": {
            "title": title,
            "date": target_date,
            "priority": "normal",
            "source": context.get("client") or "assistant",
        },
        "requiresConfirmation": True,
    }
    return {
        "reply": f"我准备把“{title}”加入时务局待办。",
        "intent": "create_todo",
        "proposedActions": [action],
    }


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def extract_food(text: str) -> str:
    patterns = [
        r"(?:吃了|喝了)(.+)$",
        r"(?:早餐|午餐|晚餐|夜宵|加餐)(?:吃|喝|是|:|：)?(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return trim_phrase(match.group(1)) or "一餐"
    return trim_phrase(text) or "一餐"


def extract_event_title(text: str) -> str:
    patterns = [
        r"提醒我(.+)$",
        r"日程(?:是|:|：)?(.+)$",
        r"(?:明天|今天|后天)?.*(开会|会议|预约.+|见.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return trim_phrase(match.group(1)) or "日程"
    return trim_phrase(remove_time_words(text)) or "日程"


def extract_todo_title(text: str) -> str:
    patterns = [r"待办(?:是|:|：)?(.+)$", r"记得(.+)$", r"帮我记(.+)$"]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return trim_phrase(match.group(1)) or "待办"
    return trim_phrase(text) or "待办"


def trim_phrase(value: str) -> str:
    text = remove_time_words(value)
    text = re.sub(r"[。！!，,；;]+$", "", text.strip())
    text = re.sub(r"^(我|今天|明天|后天|早上|上午|中午|下午|晚上|今晚|到时候)+", "", text)
    return text.strip()[:160]


def remove_time_words(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"(今天|明天|后天|今晚)", "", text)
    text = re.sub(r"(早上|上午|中午|下午|晚上)?[零一二两三四五六七八九十]{1,2}点(半|一刻|三刻)?", "", text)
    text = re.sub(r"(早上|上午|中午|下午|晚上)?\d{1,2}[:：点]\d{0,2}", "", text)
    return text


def parse_relative_date(text: str) -> str:
    today = date.today()
    if "后天" in text:
        return (today + timedelta(days=2)).isoformat()
    if "明天" in text:
        return (today + timedelta(days=1)).isoformat()
    return today.isoformat()


def has_date_word(text: str) -> bool:
    return any(word in text for word in ("今天", "明天", "后天", "今晚"))


def parse_time(text: str) -> str:
    numeric = re.search(r"(早上|上午|中午|下午|晚上)?\s*(\d{1,2})[:：点](\d{1,2})?", text)
    if numeric:
        period, hour_raw, minute_raw = numeric.groups()
        return normalize_hour(int(hour_raw), period, int(minute_raw or 0))

    chinese = re.search(r"(早上|上午|中午|下午|晚上)?\s*([零一二两三四五六七八九十]{1,2})点(半)?", text)
    if chinese:
        period, hour_raw, half = chinese.groups()
        hour = CHINESE_HOURS.get(hour_raw, 0)
        return normalize_hour(hour, period, 30 if half else 0)
    return ""


def normalize_hour(hour: int, period: str | None, minute: int) -> str:
    if period in {"下午", "晚上"} and hour < 12:
        hour += 12
    if period == "中午" and hour < 11:
        hour += 12
    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    return f"{hour:02d}:{minute:02d}"


def estimate_meal(food: str) -> tuple[int, int, int, int]:
    for keyword, estimate in CALORIE_HINTS.items():
        if keyword in food:
            return estimate
    return (450, 20, 50, 15)
