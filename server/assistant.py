"""牛秘书 AI v6 — 统一 OpenAI-compatible provider + 本地规则引擎

v6 改进（2026-07-17）：
  - 全部迁移到统一 OpenAI 兼容端点
  - 统一 OpenAI 兼容端点: http://124.222.22.171:8080/v1
  - 默认模型: gpt-5.6-luna
"""

from __future__ import annotations

import json, os, re, sys, time, urllib.error, urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from server import store

# ====== 常量 ======
MEAL_KEYWORDS = ("吃了","早餐","午餐","晚餐","夜宵","加餐","喝了","买了","叫了","点","买","摄入")
EVENT_KEYWORDS = ("提醒","日程","开会","会议","约","预约","见面","讨论")
TODO_KEYWORDS   = ("待办","记得","帮我记","要做","别忘了")
ALLOWED_ACTIONS = {"fitness.nutrition.create","schedule.event.create","schedule.todo.create","profile.update"}

# 偏好（画像调整）信号词—本地粗判断
PREFERENCE_KEYWORDS = (
    "我喜欢","我爱","我偏好","我的目标","我想减","我要减","我想增","我要增",
    "减脂","增肌","塑形目标","忌口","过敏","不吃","不喜欢","讨厌","不看","不听",
    "我关注","我感兴趣","我爱看","我喜欢看","我爱听","我喜欢听","口味",
    "平时喜欢","一般喜欢","我通常","记住我","我的偏好","我习惯","我总是",
    "设定我","设置我","以后都","从今以后","我期望","偏好是",
)

# OpenCode Go 端点
API_KEY = os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("NIU_ASSISTANT_API_KEY", "")
BASE = (
    os.environ.get("OPENCODE_GO_BASE_URL")
    or os.environ.get("NIU_ASSISTANT_API_BASE")
    or "http://124.222.22.171:8080/v1"
).rstrip("/")
for _endpoint_suffix in ("/chat/completions", "/responses"):
    if BASE.casefold().endswith(_endpoint_suffix):
        BASE = BASE[: -len(_endpoint_suffix)].rstrip("/")
        break


# ================================================================
# 模型调用基础设施
# ================================================================
class ModelError(Exception):
    """模型调用不可恢复"""


def _post_openai(model: str, prompt: str, max_tokens: int,
                 timeout_s: float = 15,
                 disable_thinking: bool = False) -> str:
    """统一走 niu_core.llm_client → config/models.yaml 的 assistant 路由。

    注意：本函数的 `model` 参数、以及模块级的 BASE / API_KEY / DEFAULT_ASSISTANT_MODEL
    都是历史遗留（现已不参与路由）：实际服务方由 models.yaml 决定，管理台改完即生效。
    保留仅为兼容旧调用签名。
    v4: disable_thinking=True → 传 thinking:{type:disabled}
    """
    try:
        import sys as _sys
        _repo = str(Path(__file__).resolve().parents[1])
        if _repo not in _sys.path:
            _sys.path.insert(0, _repo)
        from niu_core.llm_client import NiuLLM as _NiuLLM
        if os.environ.get("NIU_ASSISTANT_DEBUG"):
            print(f"[assistant-debug] NiuLLM assistant full_prompt={prompt!r}",
                  file=sys.stderr, flush=True)
        resp = _NiuLLM.load().chat(
            "assistant", [{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0,
        )
        if os.environ.get("NIU_ASSISTANT_DEBUG"):
            print(f"[assistant-debug] served_by endpoint={resp.endpoint} model={resp.model} "
                  f"text={resp.text[:80]!r}", file=sys.stderr, flush=True)
        if not resp.text.strip():
            raise ModelError(f"{resp.model} 空返回")
        return resp.text
    except ModelError:
        raise
    except Exception as exc:
        _niu_failed = getattr(exc, "args", [None])
        raise ModelError(
            f"unified gateway call failed: {_niu_failed}"
        ) from exc


# ====== 模型池 v6 — 统一 OpenAI 兼容端点 ======
DEFAULT_ASSISTANT_MODEL = os.environ.get("NIU_ASSISTANT_MODEL", "gpt-5.6-luna")


def classify_with_model(text: str) -> Optional[str]:
    """用最快模型做意图分类，失败返回 None"""
    prompt = (
        "对用户消息分类,只输出JSON不分析:{\"module\":\"fitness|schedule|news|leisure|chat\"}。"
        "fitness=饮食营养运动健身健康 schedule=日程提醒待办 news=新闻 leisure=影视音乐推荐 chat=其他。"
        "用户:我吃了鸡蛋→fitness 用户:提醒我开会→schedule 用户:推荐电影→leisure"
        f" 用户:{text}"
    )
    models = [(DEFAULT_ASSISTANT_MODEL, _openai_thinkoff, 150, 12)]
    return _try_models(models, prompt, "classify")


def generate_actions_with_model(text: str, module: str) -> Optional[dict]:
    """用模型生成动作，失败返回 None"""
    prompt = "\n".join([
        "只返回JSON不分析不解释。",
        "格式:{\"reply\":\"给用户的中文回复\",\"proposedActions\":[{\"action\":\"...\",\"input\":{...}}]}",
        "",
        "动作:",
        "- fitness.nutrition.create: {food,date(YYYY-MM-DD),calories(整数),proteinG,carbsG,fatG,source:\"home-assistant-ai\"}",
        "- schedule.event.create: {title,date,time(HH:MM),note,source:\"home-assistant-ai\"}",
        "- schedule.todo.create: {title,date,priority(low|normal|high),source:\"home-assistant-ai\"}",
        "",
        f"今天:{date.today().isoformat()} 板块:{module} 用户:{text}",
    ])
    models = [(DEFAULT_ASSISTANT_MODEL, _openai_thinkoff, 300, 20)]
    result = _try_models(models, prompt, "gen_actions")
    if result and isinstance(result, dict):
        result["module"] = module
    return result


def classify_intent_with_model(text: str) -> Optional[dict]:
    """同时判断板块与意图类型。返回 {module, intent} 或 None。

    intent: record(记录一次性数据) | preference(调整长期偏好) | query(询问/要推荐)
    """
    prompt = "\n".join([
        "对用户消息做分类,只输出JSON: {\"module\":\"fitness|schedule|news|leisure|chat\",\"intent\":\"record|preference|query\"}",
        "module判断(饮食/吃饭/喝/运动/体重/卡路里/健身/健康都算fitness): fitness=吃了喝了什么、营养热量、运动健身、体重健康、饮食偏好",
        "schedule=日程安排、提醒、开会、待办、约定"
        " news=新闻话题 leisure=电影音乐播客小说推荐 chat=寒暄或其他。",
        "intent: record=报告一件已发生/要做的事(吃了X/几点开会/帮我记X) preference=长期偏好或目标(我想减脂/我爱看悬疑) query=求推荐求建议(今天吃什么/推荐部片子)。",
        "示例:",
        "用户:我早上吃了个鸡蛋 → {\"module\":\"fitness\",\"intent\":\"record\"}",
        "用户:提醒我明天3点开会 → {\"module\":\"schedule\",\"intent\":\"record\"}",
        "用户:推荐一部电影 → {\"module\":\"leisure\",\"intent\":\"query\"}",
        "用户:今天跑步半小时 → {\"module\":\"fitness\",\"intent\":\"record\"}",
        "用户:帮我把写周报加到待办 → {\"module\":\"schedule\",\"intent\":\"record\"}",
        f"用户:{text}",
    ])
    models = [(DEFAULT_ASSISTANT_MODEL, _openai_thinkoff, 200, 12)]
    return _try_models(models, prompt, "classify_intent")


def generate_profile_update_with_model(text: str, module: str) -> Optional[dict]:
    """从聊天中抽取偏好，生成 profile.update 动作。"""
    schema_hint = PROFILE_FIELD_HINTS.get(module, "")
    prompt = "\n".join([
        "只返回JSON不分析不解释。",
        "从用户话里抽取长期偏好，生成画像更新。",
        "格式:{\"reply\":\"给用户的中文回复\",\"proposedActions\":[{\"action\":\"profile.update\",\"input\":{\"module\":\"" + module + "\",\"patch\":{...},\"summary\":\"一句话说明\"}}]}",
        f"{module}画像可用字段: {schema_hint}",
        "只填用户明确表达的字段，不确定的不要编。数组字段返回数组。",
        f"用户:{text}",
    ])
    models = [(DEFAULT_ASSISTANT_MODEL, _openai_thinkoff, 300, 20)]
    result = _try_models(models, prompt, "gen_actions")
    if result and isinstance(result, dict):
        result["module"] = module
    return result


# 各板块画像字段提示（给模型用）
PROFILE_FIELD_HINTS = {
    "fitness": "goal(fat_loss|muscle_gain|recomp|maintain), dietStyle(口味风格文本), "
               "restrictions(禁忌数组), trainingLevel(beginner|intermediate|advanced), "
               "targetCalories(整数), proteinTarget(整数), notes",
    "schedule": "workHours(如\"09:00-18:00\"), focusBlocks(专注时段数组), "
                "reminderStyle(提醒偏好文本), priorities(优先事项数组), notes",
    "news": "topics(关注话题数组), excludeTopics(排除话题数组), "
            "depth(headline|brief|deep), regions(地区数组), notes",
    "leisure": "genres(对象:{movie:[],music:[],podcast:[],novel:[]}), "
               "moods(心情/场景数组), avoid(避开数组), notes",
}


# ====== 模型调用器（统一签名: (model_id, prompt, max_tokens, timeout) -> str） ======

def _openai_thinkoff(model_id: str, prompt: str, max_tokens: int, timeout: float) -> str:
    """OpenAI 端点 + thinking:disabled"""
    return _post_openai(model_id, prompt, max_tokens, timeout, disable_thinking=True)


# ====== 模型尝试框架 ======

def _served_model_label(fallback: str) -> str:
    """日志标签：真实服务方由 config/models.yaml 的 assistant 路由决定（管理台可改）。

    `model_id`（来自 DEFAULT_ASSISTANT_MODEL）只是历史遗留的调用签名参数、不参与路由，
    直接把它打进日志会误导排查（例如日志写 gpt-5.6-luna、实际是 opencode 的 glm-5.3-flash）。
    """
    try:
        from niu_core.llm_client import compat as _compat

        _base, _key, route_model = _compat.resolve("assistant")
        if route_model:
            return f"{route_model}(yaml)"
    except Exception:
        pass
    return fallback


def _try_models(models: list, prompt: str, task_name: str) -> Optional[any]:
    """按优先级尝试模型，成功返回结果，失败返回 None"""
    if os.environ.get("NIU_ASSISTANT_DEBUG"):
        print(f"[assistant-debug] task={task_name} model={models[0][0]} "
              f"prompt[0:120]={prompt[:120]!r}", file=sys.stderr, flush=True)
    for model_id, caller, max_tokens, timeout in models:
        t0 = time.time()
        try:
            raw = caller(model_id, prompt, max_tokens, timeout)
            if os.environ.get("NIU_ASSISTANT_DEBUG") and task_name == "classify_intent":
                print(f"[assistant-debug] raw_reply={raw!r}", file=sys.stderr, flush=True)
            data = parse_json_object(raw)
            result = _parse_result(data, task_name)
            elapsed_ms = int((time.time() - t0) * 1000)
            module = result.get("module", "assistant") if isinstance(result, dict) else str(result or "assistant")
            store.record_model_call(
                module if module in {"fitness", "schedule", "news", "leisure", "chat"} else "assistant",
                task_name,
                model_id,
                prompt[:300],
                json.dumps(data, ensure_ascii=False)[:300],
                "passed",
                elapsed_ms,
            )
            print(f"[assistant] {_served_model_label(model_id)} {task_name}={result} in {elapsed_ms/1000:.1f}s")
            return result
        except Exception as e:
            elapsed_ms = int((time.time() - t0) * 1000)
            try:
                store.record_model_call(
                    "assistant",
                    task_name,
                    model_id,
                    prompt[:300],
                    str(e)[:300],
                    "failed",
                    elapsed_ms,
                )
            except Exception:
                pass
            print(f"[assistant] {model_id} fail: {e}")
            continue
    return None

def _parse_result(data: dict, task_name: str) -> any:
    """根据任务类型解析模型返回"""
    if task_name == "classify":
        module = str(data.get("module") or "unknown").strip().lower()
        if module in {"fitness", "schedule", "news", "leisure", "chat"}:
            return module
        return None
    elif task_name == "classify_intent":
        module = str(data.get("module") or "").strip().lower()
        intent = str(data.get("intent") or "").strip().lower()
        if module not in {"fitness", "schedule", "news", "leisure", "chat"}:
            return None
        if intent not in {"record", "preference", "query"}:
            intent = "record"
        return {"module": module, "intent": intent}
    elif task_name == "gen_actions":
        return data  # 原样返回，由上层 normalize
    return None


def assistant_model_configured() -> bool:
    return True  # 始终可用（有本地降级）


# ====== 本地规则引擎 ======
def local_classify(text: str) -> str:
    """纯本地规则分类。检查顺序: schedule > fitness > news > leisure > chat"""
    for kw in EVENT_KEYWORDS:
        if kw in text: return "schedule"
    for kw in TODO_KEYWORDS:
        if kw in text: return "schedule"
    if re.search(r"(明天|后天|大后天|下周|周[一二三四五六日]|\d{1,2}[点:：])", text) and not any(kw in text for kw in MEAL_KEYWORDS):
        return "schedule"
    for kw in MEAL_KEYWORDS:
        if kw in text: return "fitness"
    for kw in ("热量","卡路里","脂肪","蛋白","碳水","训练","运动","健身"):
        if kw in text: return "fitness"
    for kw in ("新闻","头条","热搜","推送"):
        if kw in text: return "news"
    for kw in ("电影","电视剧","音乐","播客","小说","看什么","听什么"):
        if kw in text: return "leisure"
    return "chat"

def fallback_response(text: str, context: dict) -> dict:
    """纯本地规则 + 热量估算"""
    module = local_classify(text)
    today = date.today().isoformat()

    if module == "fitness":
        food = extract_food(text)
        actions = [{"action":"fitness.nutrition.create","input":{
            "food":food,"date":extract_date(text) or today,
            "calories":estimate_calories(food),
            "proteinG":estimate_macro(food,"protein"),
            "carbsG":estimate_macro(food,"carbs"),
            "fatG":estimate_macro(food,"fat"),
            "source":"home-assistant-ai"},"requiresConfirmation":True}]
        return {"module":module,"reply":f"已记录：{food}（约{actions[0]['input']['calories']}千卡），点击确认写入塑形馆。","source":"fallback","proposedActions":actions}

    if module == "schedule":
        title = _extract_event_title(text)
        edate = extract_date(text) or today
        etime = extract_time(text) or ""
        if any(kw in text for kw in TODO_KEYWORDS):
            actions = [{"action":"schedule.todo.create","input":{"title":title,"date":edate,"priority":"normal","source":"home-assistant-ai"},"requiresConfirmation":True}]
            return {"module":module,"reply":f"待办：{title}，点击确认写入时务局。","source":"fallback","proposedActions":actions}
        actions = [{"action":"schedule.event.create","input":{"title":title,"date":edate,"time":etime,"note":text,"source":"home-assistant-ai"},"requiresConfirmation":True}]
        ts = f" {etime}" if etime else ""
        return {"module":module,"reply":f"已安排：{edate}{ts} {title}，点击确认写入时务局。","source":"fallback","proposedActions":actions}

    replies = {"news":"新闻社模块：可以让我推送今日头条。","leisure":"闲趣集模块：对影视、音乐、播客还是小说感兴趣？","chat":"收到～有什么可以帮你的？"}
    return {"module":module,"reply":replies.get(module,"收到～"),"source":"fallback","proposedActions":[]}


# ====== 文本提取 ======
def parse_json_object(raw: str) -> dict:
    text = raw.strip()
    for fence in ("```json","```"):
        if fence in text:
            text = text[text.find(fence)+len(fence):]
            if "```" in text: text = text[:text.rfind("```")]
            break
    s = text.find("{"); e = text.rfind("}")
    if s==-1 or e<=s: raise ValueError(f"no JSON: {raw[:200]}")
    return json.loads(text[s:e+1])

def extract_food(text: str) -> str:
    for pat in [r"(?:吃了|喝了|买了|叫了|点了)(.+)$",r"(?:早餐|午餐|晚餐|夜宵|加餐)(?:吃|喝|买|叫|点|是|:|：)?(.+)$",r"(?:夜宵|加餐).*?(?:买了?|叫了?|点了?)?(.+)$"]:
        m = re.search(pat, text)
        if m:
            f = trim_phrase(m.group(1))
            if f: return f
    return trim_phrase(text) or "一餐"

def trim_phrase(raw: str) -> str:
    return re.sub(r"^\s*[了一二三四五六七八九十]*(个|份|块|碗|杯|盘|瓶|包|盒|只|条)?\s*","",raw).strip("!！.。,，～~ ")

def extract_date(text: str) -> Optional[str]:
    today = date.today()
    for kw,n in {"今天":0,"明天":1,"后天":2,"大后天":3}.items():
        if kw in text: return (today+timedelta(days=n)).isoformat()
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", text)
    if m: return f"{int(m.group(1))}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None

def extract_time(text: str) -> str:
    cn_num = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,"十一":11,"十二":12}
    periods = {"凌晨":(0,5),"早上":(6,8),"上午":(9,11),"中午":(12,13),"下午":(14,17),"傍晚":(18,19),"晚上":(20,23)}
    m = re.search(r"(\d{1,2})[点:：](\d{1,2})?", text)
    if m:
        h,m2 = int(m.group(1)), int(m.group(2)) if m.group(2) else 0
        p = re.search(r"(凌晨|早上|上午|中午|下午|傍晚|晚上)", text)
        if p:
            start,_ = periods.get(p.group(1),(0,23))
            if h<6 and start>=12: h+=12
            elif h==12 and start<12: h=0
        return f"{h:02d}:{m2:02d}"
    # 中文数字时间: "下午三点" / "上午十点半"
    m = re.search(r"(凌晨|早上|上午|中午|下午|傍晚|晚上)([\u4e00-\u9fa5]+)", text)
    if m:
        cn_time = m.group(2)
        # 提取"三点"→3, "十一点半"→11:30
        tm = re.match(r"([\u4e00-\u9fa5]+?)点(半)?", cn_time)
        if tm:
            h = cn_num.get(tm.group(1), 0)
            m2 = 30 if tm.group(2) else 0
            if h:
                start,_ = periods.get(m.group(1),(0,23))
                if h<6 and start>=12: h+=12
                elif h==12 and start<12: h=0
                return f"{h:02d}:{m2:02d}"
    return ""

def _extract_event_title(text: str) -> str:
    for pre in ("提醒我","帮我","记得","别忘了"):
        if pre in text: return text[text.find(pre)+len(pre):].strip(":：,， ")
    for pre in ("和","跟","与"):
        if f"{pre} " in text:
            suffix = text[text.find(f"{pre} "):]
            for kw in ("开会","会议","讨论","见面","聊"):
                if kw in suffix: return suffix[:suffix.find(kw)+len(kw)].strip(":：,， ")
    return trim_phrase(text) or "新日程"

def normalize_model_response(data: dict, text: str, context: dict, module: str) -> dict:
    reply = str(data.get("reply") or data.get("message") or "我已收到。")
    proposed = data.get("proposedActions") or []
    actions = []
    for a in proposed:
        aname = str(a.get("action") or "")
        if aname not in ALLOWED_ACTIONS: continue
        inp = dict(a.get("input") or {})
        if aname == "profile.update":
            # 画像更新：需 module + 非空 patch
            inp.setdefault("module", module)
            if not isinstance(inp.get("patch"), dict) or not inp.get("patch"):
                continue
            inp.setdefault("source", "home-assistant-ai")
        else:
            inp.setdefault("source", "home-assistant-ai")
        actions.append({"action":aname,"input":inp,"requiresConfirmation":True})
    return {"module":module,"reply":reply,"source":"assistant-model","proposedActions":actions}

# ====== 营养估算 ======
def estimate_calories(food: str) -> int:
    f = food.lower()
    # 大餐关键词 → 高热量
    if re.search(r"(几|七[八九十]|[八九]个菜|大餐|聚餐|宴|酒席|满汉|自助|放题|吃到饱|omakase)", f):
        return 1200
    if re.search(r"(大部分|多数|主要|全是|都是).*(肉|荤)", f):
        return 1200
    if re.search(r"(东北菜|湖南菜|川菜|粤菜|烤肉|火锅|海鲜大餐)", f):
        return 1100
    db = {"米饭":200,"面":350,"面条":350,"面包":250,"牛肉":250,"猪肉":300,"鸡肉":200,"鱼":150,"虾":100,"蛋":80,"鸡腿":280,"牛排":400,"火锅":500,"汉堡":450,"炸鸡":400,"热卤":350,"麻辣烫":400,"烧烤":450,"串":100,"奶茶":300,"可乐":150,"果汁":120,"啤酒":150,"咖啡":50,"蛋糕":350,"冰淇淋":200,"巧克力":250,"饼干":200,"沙拉":150,"水果":100,"蔬菜":50,"豆腐":80,"披萨":350,"三明治":300,"寿司":250,"拉面":400,"包子":150,"饺子":250,"炒饭":400,"炒面":400}
    for k,v in db.items():
        if k in f: return v
    m = re.search(r"(\d+)\s*(克|g|斤)", f)
    if m:
        g = int(m.group(1))
        if m.group(2)=="斤": g*=500
        return g//5
    return 350

def estimate_macro(food: str, macro: str) -> int:
    f = food.lower()
    # 大餐宏量估算
    if re.search(r"(大餐|聚餐|宴|酒席|满汉|自助|omakase|几[七八九十]个菜|大部分.*肉|多数.*肉)", f):
        return {"protein": 80, "carbs": 80, "fat": 60}.get(macro, 30)
    maps = {"protein":{"牛肉":20,"鸡肉":25,"鱼":18,"虾":18,"蛋":7,"豆腐":8,"猪肉":15,"热卤":18},"carbs":{"米饭":45,"面":50,"面条":50,"面包":40,"馒头":45,"蛋糕":40,"饼干":30,"土豆":20,"热卤":20},"fat":{"牛肉":10,"猪肉":20,"炸鸡":25,"火锅":25,"热卤":15,"烧烤":20,"奶茶":10}}
    for k,v in maps.get(macro,{}).items():
        if k in f: return v
    return {"protein":15,"carbs":30,"fat":10}[macro]

# ====== 主入口 ======
def handle_message(text: str, context: dict) -> dict:
    cleaned = text.strip()

    # 1) 意图分类（板块 + record/preference/query）
    intent_info = classify_intent_with_model(cleaned)
    if intent_info:
        module = intent_info["module"]
        intent = intent_info["intent"]
    else:
        module = local_classify(cleaned)
        intent = local_intent(cleaned)

    # 2) preference → 生成画像更新
    if intent == "preference" and module in ("fitness", "schedule", "news", "leisure"):
        prof = generate_profile_update_with_model(cleaned, module)
        if prof is not None:
            normalized = normalize_model_response(prof, cleaned, context, module)
            if normalized["proposedActions"]:
                return normalized
        return preference_fallback(cleaned, module)

    # 3) news/leisure/chat 的记录/询问：无写入动作，走本地回复
    if module in ("news", "leisure", "chat"):
        return fallback_response(cleaned, context)

    # 4) fitness/schedule 的 record：生成写入动作
    result = generate_actions_with_model(cleaned, module)
    if result is not None:
        return result

    return fallback_response(cleaned, context)


def local_intent(text: str) -> str:
    """本地规则判断意图。preference > query > record。"""
    for kw in PREFERENCE_KEYWORDS:
        if kw in text:
            return "preference"
    if re.search(r"(推荐|吃什么|看什么|听什么|玩什么|有什么建议|干点啥|怎么安排)", text):
        return "query"
    return "record"


def preference_fallback(text: str, module: str) -> dict:
    """模型不可用时，本地粗抽取偏好生成 profile.update。"""
    patch = local_extract_preference(text, module)
    if not patch:
        labels = {"fitness": "塑形馆", "schedule": "时务局", "news": "新闻社", "leisure": "闲趣集"}
        return {
            "module": module,
            "reply": f"我想更新你的{labels.get(module, module)}画像，但没听太明白具体偏好。能再说具体一点吗？",
            "source": "fallback",
            "proposedActions": [],
        }
    summary = f"根据你的描述更新{module}偏好"
    return {
        "module": module,
        "reply": f"我理解到你的偏好，点击确认就更新到{module}画像。",
        "source": "fallback",
        "proposedActions": [{
            "action": "profile.update",
            "input": {"module": module, "patch": patch, "summary": summary, "source": "home-assistant-ai"},
            "requiresConfirmation": True,
        }],
    }


def local_extract_preference(text: str, module: str) -> dict:
    """纯本地关键词抽取偏好（降级用）。"""
    patch: dict = {}
    if module == "fitness":
        if re.search(r"减脂|减肥|掍肉|减重", text): patch["goal"] = "fat_loss"
        elif re.search(r"增肌|增重|长肌肉|强壮", text): patch["goal"] = "muscle_gain"
        elif re.search(r"重组|recomp", text): patch["goal"] = "recomp"
        elif re.search(r"维持|保持", text): patch["goal"] = "maintain"
        restr = []
        for kw in ("乳糖不耐", "海鲜过敏", "花生过敏"):
            if kw in text: restr.append(kw)
        m = re.search(r"不吃([\u4e00-\u9fa5]{1,6})", text)
        if m: restr.append("不吃" + m.group(1))
        if restr: patch["restrictions"] = restr
        for style in ("川渝", "粤式", "湘菜", "清淡", "高蛋白", "低碳"):
            if style in text: patch["dietStyle"] = style; break
    elif module == "schedule":
        m = re.search(r"(\d{1,2}:\d{2})\s*[-~到]\s*(\d{1,2}:\d{2})", text)
        if m: patch["workHours"] = f"{m.group(1)}-{m.group(2)}"
    elif module == "news":
        topics = [t for t in ("AI", "科技", "财经", "国内", "国际", "体育", "游戏") if t in text]
        if topics: patch["topics"] = topics
    elif module == "leisure":
        genres = {}
        movie = [g for g in ("悬疑", "科幻", "动作", "喜剧", "爱情", "恐怖", "纪录片") if g in text]
        if movie: genres["movie"] = movie
        if genres: patch["genres"] = genres
    return patch
