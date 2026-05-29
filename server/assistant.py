"""Model-routed assistant for the Niu Secretary Action Protocol."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, timedelta

from server import store


MEAL_KEYWORDS = ("吃了", "早餐", "午餐", "晚餐", "夜宵", "加餐", "喝了")
EVENT_KEYWORDS = ("提醒", "日程", "开会", "会议", "约", "预约")
TODO_KEYWORDS = ("待办", "记得", "帮我记", "要做")

ALLOWED_ACTIONS = {
    "fitness.nutrition.create",
    "fitness.nutrition.today_summary",
    "schedule.event.create",
    "schedule.todo.create",
    "schedule.today_summary",
}

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

CUISINE_HINTS = {
    "东北菜": (760, 38, 56, 42),
    "川菜": (720, 34, 52, 40),
    "湘菜": (720, 34, 52, 40),
    "烧烤": (850, 50, 35, 55),
    "火锅": (900, 48, 45, 58),
}

MEAT_WORDS = ("肉", "牛肉", "羊肉", "猪肉", "排骨", "锅包肉", "鸡肉", "烤肉", "鱼")
MANY_DISH_WORDS = ("七八个菜", "七八道菜", "很多菜", "一桌菜", "聚餐", "大餐")

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


class AssistantModelError(Exception):
    pass


def handle_message(text: str, context: dict | None = None) -> dict:
    context = context or {}
    cleaned = normalize_text(text)
    if not cleaned:
        return {
            "reply": "我在。你可以直接说“我今天吃了牛肉面”或“明天下午三点提醒我开会”。",
            "intent": "empty",
            "module": "chat",
            "proposedActions": [],
        }

    response = None
    if assistant_model_configured():
        try:
            response = handle_with_model(cleaned, context)
        except AssistantModelError as exc:
            response = fallback_response(cleaned, context)
            response["reply"] = f"AI 意图识别暂时失败，已使用本地降级：{response['reply']}"
            response["warnings"] = [str(exc)[:180]]
    else:
        response = fallback_response(cleaned, context)
        response["warnings"] = ["assistant_model_unconfigured"]

    store.insert_assistant_message(cleaned, response["reply"], response["proposedActions"])
    return response


def assistant_model_configured() -> bool:
    return all(os.environ.get(name) for name in ("NIU_ASSISTANT_API_BASE", "NIU_ASSISTANT_API_KEY", "NIU_ASSISTANT_MODEL"))


def handle_with_model(text: str, context: dict) -> dict:
    module = classify_intent(text, context)
    raw = call_assistant_model(build_module_prompt(module, text), max_tokens=700)
    data = parse_json_object(raw)
    response = normalize_model_response(data, text, context, module)
    response["source"] = "assistant-model"
    return response


def classify_intent(text: str, context: dict) -> str:
    prompt = "\n".join([
        "你是牛秘书 2.0 的总调度器，只判断用户这句话应该交给哪个板块。",
        "只能返回 JSON：{\"module\":\"fitness|schedule|news|leisure|chat|unknown\"}",
        "fitness=塑形馆：饮食、营养、训练、恢复、身体评估、图片卡路里。",
        "schedule=时务局：日程、提醒、待办、会议、时间安排。",
        "news=新闻页：新闻查询、摘要、生成新闻页面。",
        "leisure=逍遥游：娱乐、旅行、休闲计划。",
        "chat=纯聊天或不需要写入任何板块。",
        f"今天日期：{date.today().isoformat()}。",
        f"用户：{text}",
    ])
    try:
        data = parse_json_object(call_assistant_model(prompt, max_tokens=80))
    except AssistantModelError:
        raise
    except Exception as exc:
        raise AssistantModelError(f"意图 JSON 解析失败：{exc}") from exc
    module = str(data.get("module") or "unknown").strip().lower()
    return module if module in {"fitness", "schedule", "news", "leisure", "chat", "unknown"} else "unknown"


def build_module_prompt(module: str, text: str) -> str:
    common = [
        "你是牛秘书 2.0 的动作生成器。不要输出 Markdown，不要解释推理，只输出 JSON 对象。",
        "返回格式：",
        "{",
        '  "module": "fitness|schedule|news|leisure|chat|unknown",',
        '  "intent": "简短英文意图",',
        '  "reply": "给用户看的中文回复",',
        '  "proposedActions": [',
        '    {"action": "动作名", "input": {}, "requiresConfirmation": true}',
        "  ]",
        "}",
        "如果只是聊天或当前板块没有可执行动作，proposedActions 返回空数组。",
        "所有写入动作都必须 requiresConfirmation=true。",
        f"今天日期：{date.today().isoformat()}。",
        f"用户原文：{text}",
    ]
    if module == "fitness":
        module_lines = [
            "板块：塑形馆。",
            "当前允许动作：fitness.nutrition.create。",
            "当用户描述吃了什么、喝了什么、某顿饭、聚餐、营养摄入时，生成 fitness.nutrition.create。",
            "input 字段必须包含：food, date, calories, proteinG, carbsG, fatG, source。",
            "date 用 YYYY-MM-DD。今天/今晚用今天日期，明天/后天按日期换算。",
            "calories/proteinG/carbsG/fatG 必须是整数；没有重量时按常见一人实际摄入粗估，不能默认 450。",
            "如果是七八个菜、大部分肉类、火锅、烧烤、聚餐，应按高热量餐估算，并在 reply 中说明是文字粗估、可确认前修改。",
            "source 固定为 home-assistant-ai。",
        ]
    elif module == "schedule":
        module_lines = [
            "板块：时务局。",
            "当前允许动作：schedule.event.create 或 schedule.todo.create。",
            "有明确时间点、会议、提醒、预约时用 schedule.event.create，input 包含 title,date,time,note,source。",
            "没有明确时间点但要记住/待办/要做时用 schedule.todo.create，input 包含 title,date,priority,source。",
            "time 用 HH:MM，下午三点写 15:00；没有时间写空字符串。",
            "source 固定为 home-assistant-ai。",
        ]
    elif module in {"news", "leisure"}:
        module_lines = [
            f"板块：{module}。",
            "这个板块的统一写入动作还没有开放。请只给中文回复，proposedActions 返回空数组。",
            "回复里说明已识别到对应板块，但目前需要下一阶段接入具体技能。",
        ]
    else:
        module_lines = [
            "板块：聊天。",
            "如果用户只是普通对话，给简短中文回复，proposedActions 返回空数组。",
        ]
    return "\n".join(common + module_lines)


def call_assistant_model(prompt: str, max_tokens: int = 500) -> str:
    url = resolve_model_url(os.environ["NIU_ASSISTANT_API_BASE"])
    request = urllib.request.Request(
        url,
        data=json.dumps(build_model_payload(url, prompt, max_tokens), ensure_ascii=False).encode("utf-8"),
        headers=build_model_headers(url),
        method="POST",
    )
    timeout = int(os.environ.get("NIU_ASSISTANT_TIMEOUT_MS", "60000")) / 1000
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise AssistantModelError(f"模型 HTTP {exc.code}: {detail}") from exc
    except TimeoutError as exc:
        raise AssistantModelError("模型请求超时") from exc
    except Exception as exc:
        raise AssistantModelError(str(exc)) from exc
    text = extract_text_content(payload)
    if not isinstance(text, str) or not text.strip():
        raise AssistantModelError("模型没有返回文本")
    return text


def build_model_headers(url: str) -> dict:
    if url.endswith("/messages"):
        return {
            "x-api-key": os.environ["NIU_ASSISTANT_API_KEY"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 NiuSecretaryApi/2.0",
        }
    return {
        "Authorization": f"Bearer {os.environ['NIU_ASSISTANT_API_KEY']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def build_model_payload(url: str, prompt: str, max_tokens: int) -> dict:
    if url.endswith("/messages"):
        return {
            "model": os.environ["NIU_ASSISTANT_MODEL"],
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    return {
        "model": os.environ["NIU_ASSISTANT_MODEL"],
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }


def resolve_model_url(base: str) -> str:
    trimmed = str(base or "").rstrip("/")
    if trimmed.endswith("/messages") or trimmed.endswith("/chat/completions"):
        return trimmed
    return f"{trimmed}/chat/completions"


def extract_text_content(data):
    choices = data.get("choices") if isinstance(data, dict) else None
    if choices:
        return choices[0].get("message", {}).get("content")
    if isinstance(data, dict) and data.get("output_text") is not None:
        return data.get("output_text")
    if isinstance(data, dict) and isinstance(data.get("content"), list):
        for item in data["content"]:
            if item.get("type") == "text":
                return item.get("text")
        if data["content"]:
            return data["content"][0].get("text")
    if isinstance(data, dict) and isinstance(data.get("message"), dict):
        return data["message"].get("content")
    return ""


def parse_json_object(value: str) -> dict:
    text = strip_json_fence(value)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("模型返回不是 JSON 对象")
    return data


def strip_json_fence(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def normalize_model_response(data: dict, text: str, context: dict, module: str) -> dict:
    proposed = data.get("proposedActions") or []
    if not isinstance(proposed, list):
        proposed = []
    normalized_actions = []
    for item in proposed[:3]:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "")
        if action not in ALLOWED_ACTIONS:
            continue
        action_input = normalize_action_input(action, item.get("input") or {}, text, context)
        normalized_actions.append({
            "action": action,
            "input": action_input,
            "requiresConfirmation": True,
        })
    reply = clean_text(data.get("reply"), 300) or ("我已理解，但没有需要执行的动作。" if not normalized_actions else "我准备好了一个动作，请确认。")
    return {
        "reply": reply,
        "intent": clean_text(data.get("intent"), 80) or ("record_meal" if normalized_actions else "chat"),
        "module": clean_text(data.get("module"), 40) or module,
        "proposedActions": normalized_actions,
    }


def normalize_action_input(action: str, payload: dict, text: str, context: dict) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    if action == "fitness.nutrition.create":
        fallback_food = extract_food(text)
        calories, protein, carbs, fat = estimate_meal(fallback_food)
        return {
            "food": clean_text(payload.get("food"), 160) or fallback_food,
            "date": clean_date(payload.get("date") or parse_relative_date(text)),
            "calories": clamp_number(payload.get("calories"), 0, 5000, calories),
            "proteinG": clamp_number(payload.get("proteinG"), 0, 300, protein),
            "carbsG": clamp_number(payload.get("carbsG"), 0, 600, carbs),
            "fatG": clamp_number(payload.get("fatG"), 0, 300, fat),
            "source": "home-assistant-ai",
        }
    if action == "schedule.event.create":
        return {
            "title": clean_text(payload.get("title"), 160) or extract_event_title(text),
            "date": clean_date(payload.get("date") or parse_relative_date(text)),
            "time": clean_time(payload.get("time") or parse_time(text)),
            "note": clean_text(payload.get("note"), 300, allow_empty=True) or text,
            "source": "home-assistant-ai",
        }
    if action == "schedule.todo.create":
        return {
            "title": clean_text(payload.get("title"), 160) or extract_todo_title(text),
            "date": clean_optional_date(payload.get("date") or (parse_relative_date(text) if has_date_word(text) else "")),
            "priority": clean_priority(payload.get("priority")),
            "source": "home-assistant-ai",
        }
    if action in {"fitness.nutrition.today_summary", "schedule.today_summary"}:
        return {"date": clean_date(payload.get("date") or parse_relative_date(text))}
    return payload


def fallback_response(text: str, context: dict) -> dict:
    if contains_any(text, MEAL_KEYWORDS):
        return build_meal_response(text, context)
    if contains_any(text, EVENT_KEYWORDS):
        return build_event_response(text, context)
    if contains_any(text, TODO_KEYWORDS):
        return build_todo_response(text, context)
    return {
        "reply": "这句话我先记为普通咨询。v2.0 已支持记录餐食、创建日程和创建待办。",
        "intent": "chat",
        "module": "chat",
        "proposedActions": [],
    }


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
        "reply": f"我按文字粗估“{food}”约 {calories} 千卡。确认前可以改数值，确认后会写入塑形馆营养日志。",
        "intent": "record_meal",
        "module": "fitness",
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
        "module": "schedule",
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
        "module": "schedule",
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

    calories, protein, carbs, fat = estimate_by_meal_description(food)
    return (
        clamp_int(calories, 180, 1800),
        clamp_int(protein, 5, 120),
        clamp_int(carbs, 0, 220),
        clamp_int(fat, 0, 120),
    )


def estimate_by_meal_description(food: str) -> tuple[int, int, int, int]:
    estimate = next((value for keyword, value in CUISINE_HINTS.items() if keyword in food), (450, 20, 50, 15))
    calories, protein, carbs, fat = estimate

    dish_count = parse_dish_count(food)
    if dish_count >= 6:
        calories += 380
        protein += 24
        carbs += 18
        fat += 26
    elif dish_count >= 3:
        calories += 180
        protein += 12
        carbs += 10
        fat += 12
    elif contains_any(food, MANY_DISH_WORDS):
        calories += 260
        protein += 16
        carbs += 12
        fat += 18

    if "大部分是肉" in food or "多数是肉" in food or "肉类偏多" in food:
        calories += 260
        protein += 28
        carbs -= 10
        fat += 22
    elif contains_any(food, MEAT_WORDS):
        calories += 160
        protein += 18
        carbs -= 6
        fat += 12

    if "少量" in food or "一点" in food:
        calories -= 160
        protein -= 8
        carbs -= 12
        fat -= 8

    return calories, protein, carbs, fat


def parse_dish_count(text: str) -> int:
    numeric = re.search(r"(\d{1,2})\s*(?:个|道)?菜", text)
    if numeric:
        return int(numeric.group(1))
    if re.search(r"七八(?:个|道)?菜", text):
        return 8
    if re.search(r"五六(?:个|道)?菜", text):
        return 6
    if re.search(r"三四(?:个|道)?菜", text):
        return 4
    return 0


def clean_text(value, limit: int, allow_empty: bool = False) -> str:
    text = normalize_text(value)
    if not text and not allow_empty:
        return ""
    return text[:limit]


def clean_date(value) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    return date.today().isoformat()


def clean_optional_date(value) -> str:
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else ""


def clean_time(value) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"\d{1,2}:\d{2}", text):
        hour, minute = text.split(":")
        return normalize_hour(int(hour), None, int(minute))
    return ""


def clean_priority(value) -> str:
    text = str(value or "normal").strip().lower()
    return text if text in {"low", "normal", "high"} else "normal"


def clamp_number(value, low: int, high: int, fallback: int = 0) -> int:
    try:
        number = round(float(value))
    except (TypeError, ValueError):
        number = fallback
    return max(low, min(high, number))


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))
