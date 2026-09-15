#!/usr/bin/env python3
# fitness/server/nutrition_api.py
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROUTES = {
    "/niu-secretary/fitness/api/agent/nutrition-recognize",
    "/api/agent/nutrition-recognize",
}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_BODY_BYTES = MAX_IMAGE_BYTES + 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


class FitnessApiHandler(BaseHTTPRequestHandler):
    server_version = "NiuFitnessApi/1.0"

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.end_headers()

    def do_POST(self):
        if self.path.split("?", 1)[0] not in ROUTES:
            return self.send_json(404, {"error": "not_found", "message": "未知接口。"})
        return self.handle_nutrition_recognize()

    def handle_nutrition_recognize(self):
        content_type = self.headers.get("content-type", "")
        if "multipart/form-data" not in content_type:
            return self.send_json(400, {"error": "invalid_request", "message": "请使用 multipart/form-data 上传图片。"})

        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            length = 0
        if length > MAX_BODY_BYTES:
            return self.send_json(413, {"error": "photo_too_large", "message": "图片超过 8MB，请压缩后再上传。"})

        body = self.rfile.read(length)
        form = parse_multipart(body, content_type)
        photo = form["files"].get("photo")
        description = form["fields"].get("description", "")

        if not photo or not photo["data"]:
            return self.send_json(400, {"error": "missing_photo", "message": "缺少 photo 图片字段。"})
        if len(photo["data"]) > MAX_IMAGE_BYTES:
            return self.send_json(413, {"error": "photo_too_large", "message": "图片超过 8MB，请压缩后再上传。"})
        if photo["content_type"] not in ALLOWED_IMAGE_TYPES:
            return self.send_json(400, {"error": "unsupported_photo_type", "message": "仅支持 JPG、PNG、WebP、HEIC 图片。"})

        if not all(os.environ.get(name) for name in ("FITNESS_VISION_API_BASE", "FITNESS_VISION_API_KEY", "FITNESS_VISION_MODEL")):
            return self.send_json(503, {
                "error": "agent_unconfigured",
                "message": "识别服务未配置，请设置 FITNESS_VISION_API_BASE、FITNESS_VISION_API_KEY、FITNESS_VISION_MODEL。"
            })

        started = time.monotonic()
        try:
            result = call_vision_model(photo, description)
            elapsed = time.monotonic() - started
            print(f"[fitness-api] vision call ok elapsed={elapsed:.1f}s bytes={len(photo["data"])}", flush=True)
            return self.send_json(200, normalize_meal(result, "agent"))
        except TimeoutError:
            elapsed = time.monotonic() - started
            print(f"[fitness-api] vision call timeout elapsed={elapsed:.1f}s bytes={len(photo["data"])}", file=sys.stderr, flush=True)
            return self.send_json(502, {"error": "agent_timeout", "message": "Agent 识别超时，请稍后重试或使用本地估算。"})
        except Exception as exc:
            message = str(exc)
            print(f"[fitness-api] vision call failed {message}", file=sys.stderr, flush=True)
            no_vision = re.search(r"Unexpected item type in content|messages input is invalid|image", message, re.I)
            return self.send_json(502, {
                "error": "model_no_vision" if no_vision else "agent_failed",
                "message": f"当前模型 {os.environ.get('FITNESS_VISION_MODEL', '')} 不支持图片输入，请换成支持视觉/多模态的模型。"
                if no_vision else "Agent/模型调用失败，请稍后重试或使用本地估算。"
            })

    def send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def log_message(self, fmt, *args):
        print(f"[fitness-api] {self.address_string()} {fmt % args}", flush=True)


def call_vision_model(photo, description):
    """Vision meal recognition via the unified gateway (niu_core.llm_client,
    logic model "vision" — sub2api gpt-5.6-luna primary, opencode vision-exp
    fallback). Falls back to the legacy direct-endpoint path when the unified
    config cannot be loaded (no models.yaml / missing key)."""
    prompt = "\n".join([
        "你是营养识别助手。识别餐食图片并估算整餐营养。不要解释推理，不要 Markdown 表格。",
        "请严格输出以下 7 行，数值只写整数，未知就写 0：",
        "餐食: <一句话餐食名称>",
        "热量: <整数> kcal",
        "蛋白: <整数> g",
        "碳水: <整数> g",
        "脂肪: <整数> g",
        "置信度: <0-100整数>%",
        "明细: <食物1 份量 热量kcal; 食物2 份量 热量kcal>",
        "提醒: <一句话提醒，没有就写 无>",
        f"用户补充描述：{description}" if description else "用户没有补充描述。",
    ])
    image_base64 = base64.b64encode(photo["data"]).decode("ascii")
    image_url = f"data:{photo['content_type']};base64,{image_base64}"
    try:
        _repo = str(Path(__file__).resolve().parents[2])
        if _repo not in sys.path:
            sys.path.insert(0, _repo)
        from niu_core.llm_client import NiuLLM as _NiuLLM, ConfigError as _CfgErr
        _llm = _NiuLLM.load()
    except (_CfgErr, Exception) as _load_exc:
        if isinstance(_load_exc, (KeyboardInterrupt, SystemExit)):
            raise
        return _legacy_call_vision_model(photo, prompt)
    rsp = _llm.vision(
        os.environ.get("FITNESS_VISION_LOGIC_MODEL", "vision"),
        image_url, prompt)
    content = rsp.text
    text = strip_json_fence(content)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return parse_meal_text(text)


def _legacy_call_vision_model(photo, description, prompt=None):
    """Pre-unification direct-endpoint path (kept as documented fallback)."""
    prompt = prompt or "\n".join([
        "你是营养识别助手。识别餐食图片并估算整餐营养。不要解释推理，不要 Markdown 表格。",
        "请严格输出以下 7 行，数值只写整数，未知就写 0：",
        "餐食: <一句话餐食名称>",
        "热量: <整数> kcal",
        "蛋白: <整数> g",
        "碳水: <整数> g",
        "脂肪: <整数> g",
        "置信度: <0-100整数>%",
        "明细: <食物1 份量 热量kcal; 食物2 份量 热量kcal>",
        "提醒: <一句话提醒，没有就写 无>",
        f"用户补充描述：{description}" if description else "用户没有补充描述。",
    ])
    url = resolve_vision_url(os.environ["FITNESS_VISION_API_BASE"])
    request = urllib.request.Request(
        url,
        data=json.dumps(build_vision_payload(url, prompt, photo), ensure_ascii=False).encode("utf-8"),
        headers=build_vision_headers(url),
        method="POST",
    )
    timeout = int(os.environ.get("FITNESS_VISION_TIMEOUT_MS", "25000")) / 1000
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"vision-http-{exc.code}: {detail}") from exc
    except TimeoutError:
        raise
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc
    return parse_vision_response(data)


def build_vision_headers(url):
    if url.endswith("/messages"):
        return {
            "x-api-key": os.environ["FITNESS_VISION_API_KEY"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 NiuFitnessApi/1.0",
        }
    return {
        "Authorization": f"Bearer {os.environ['FITNESS_VISION_API_KEY']}",
        "Content-Type": "application/json",
    }


def build_vision_payload(url, prompt, photo):
    image_base64 = base64.b64encode(photo["data"]).decode("ascii")
    if url.endswith("/messages"):
        return {
            "model": os.environ["FITNESS_VISION_MODEL"],
            "max_tokens": 500,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "source": {"type": "base64", "media_type": photo["content_type"], "data": image_base64}},
                ],
            }],
        }
    return {
        "model": os.environ["FITNESS_VISION_MODEL"],
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{photo['content_type']};base64,{image_base64}"}},
            ],
        }],
    }


def parse_vision_response(data):
    content = extract_text_content(data)
    if isinstance(content, str):
        text = strip_json_fence(content)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return parse_meal_text(text)
    return content


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
    return data


def parse_meal_text(text):
    food = find_text_field(text, ["餐食", "食物", "名称", "food"]) or first_nonempty_line(text) or "图片餐食"
    calories = find_number_field(text, ["热量", "卡路里", "calories", "calorie", "kcal"])
    protein = find_number_field(text, ["蛋白质", "蛋白", "protein"])
    carbs = find_number_field(text, ["碳水化合物", "碳水", "carbs", "carbohydrate"])
    fat = find_number_field(text, ["脂肪", "fat"])
    confidence_raw = find_number_field(text, ["置信度", "confidence"])
    detail_text = find_text_field(text, ["明细", "拆分", "items", "details"]) or ""
    warning_text = find_text_field(text, ["提醒", "警告", "备注", "warnings"]) or ""
    return {
        "food": food,
        "items": parse_detail_items(detail_text),
        "calories": calories,
        "proteinG": protein,
        "carbsG": carbs,
        "fatG": fat,
        "confidence": confidence_raw / 100 if confidence_raw > 1 else confidence_raw,
        "warnings": [] if warning_text in ("", "无", "none", "None") else [warning_text],
        "rawText": text[:1000],
    }


def find_text_field(text, labels):
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"^(?:\s*(?:{label_pattern})\s*[:：]\s*)(.+)$", text, re.I | re.M)
    if not match:
        return ""
    return match.group(1).strip().strip("-").strip()[:160]


def find_number_field(text, labels):
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{label_pattern})\s*[:：]?\s*约?\s*(\d+(?:\.\d+)?)", text, re.I)
    if match:
        return clamp(match.group(1), 0, 5000)
    return 0


def parse_detail_items(detail_text):
    items = []
    for part in re.split(r"[;；\n]+", detail_text):
        part = part.strip(" -，,")
        if not part:
            continue
        calories_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kcal|千卡|卡)", part, re.I)
        calories = clamp(calories_match.group(1), 0, 3000) if calories_match else 0
        name = re.sub(r"\d+(?:\.\d+)?\s*(?:kcal|千卡|卡|g|克)", "", part, flags=re.I).strip(" -，,")
        items.append({
            "name": name[:80] or "食物",
            "portion": "",
            "calories": calories,
            "proteinG": 0,
            "carbsG": 0,
            "fatG": 0,
        })
    return items[:8]


def first_nonempty_line(text):
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:160]
    return ""


def normalize_meal(data, source):
    if not isinstance(data, dict):
        data = {}
    items = []
    for item in data.get("items") or []:
        items.append({
            "name": str(item.get("name") or item.get("food") or "未命名食物")[:80],
            "portion": str(item.get("portion") or item.get("amount") or "")[:80],
            "calories": clamp(item.get("calories"), 0, 3000),
            "proteinG": clamp(item.get("proteinG", item.get("protein")), 0, 200),
            "carbsG": clamp(item.get("carbsG", item.get("carbs")), 0, 400),
            "fatG": clamp(item.get("fatG", item.get("fat")), 0, 200),
        })
    warnings = [str(item)[:120] for item in data.get("warnings", [])] if isinstance(data.get("warnings"), list) else []
    return {
        "food": str(data.get("food") or data.get("name") or "、".join(item["name"] for item in items) or "图片餐食")[:160],
        "items": items,
        "calories": clamp(data.get("calories"), 0, 5000),
        "proteinG": clamp(data.get("proteinG", data.get("protein")), 0, 300),
        "carbsG": clamp(data.get("carbsG", data.get("carbs")), 0, 600),
        "fatG": clamp(data.get("fatG", data.get("fat")), 0, 300),
        "confidence": max(0, min(1, float(data.get("confidence") or 0))),
        "warnings": warnings,
        "source": source,
    }


def parse_multipart(body, content_type):
    match = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type, re.I)
    if not match:
        return {"fields": {}, "files": {}}
    boundary = b"--" + (match.group(1) or match.group(2)).encode("utf-8")
    fields, files = {}, {}
    for raw in body.split(boundary):
        raw = raw.strip(b"\r\n")
        if not raw or raw == b"--":
            continue
        if raw.endswith(b"--"):
            raw = raw[:-2].rstrip(b"\r\n")
        header_blob, sep, value = raw.partition(b"\r\n\r\n")
        if not sep:
            continue
        if value.endswith(b"\r\n"):
            value = value[:-2]
        headers = header_blob.decode("latin1", errors="replace")
        disposition = re.search(r"content-disposition:\s*form-data;([^\r\n]+)", headers, re.I)
        if not disposition:
            continue
        name_match = re.search(r'name="([^"]+)"', disposition.group(1))
        if not name_match:
            continue
        name = name_match.group(1)
        filename = re.search(r'filename="([^"]*)"', disposition.group(1))
        type_match = re.search(r"content-type:\s*([^\r\n]+)", headers, re.I)
        if filename:
            files[name] = {
                "filename": filename.group(1),
                "content_type": (type_match.group(1) if type_match else "application/octet-stream").lower(),
                "data": value,
            }
        else:
            fields[name] = value.decode("utf-8", errors="replace")
    return {"fields": fields, "files": files}


def resolve_vision_url(base):
    trimmed = str(base or "").rstrip("/")
    if trimmed.endswith("/messages") or trimmed.endswith("/chat/completions"):
        return trimmed
    return f"{trimmed}/chat/completions"


def strip_json_fence(value):
    value = str(value).strip()
    value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*```$", "", value)
    return value


def clamp(value, low, high):
    try:
        number = round(float(value or 0))
    except (TypeError, ValueError):
        number = 0
    return max(low, min(high, number))


def main():
    port = int(os.environ.get("FITNESS_API_PORT", "5177"))
    server = ThreadingHTTPServer(("127.0.0.1", port), FitnessApiHandler)
    print(f"[fitness-api] python listening on http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
