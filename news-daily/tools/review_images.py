#!/usr/bin/env python3
"""AI 审核新闻配图相关性

爬图完成后运行此脚本，对每张下载的图片用视觉模型判断是否与对应新闻内容相关。
审核通过 → 保留图片 + 标记 OK
审核不通过 → 删除图片 + 标记 FAIL
"""
import re, json, subprocess, os, sys
from pathlib import Path

DIST = Path("/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist")
IMG_DIR = DIST / "assets" / "images"
RESULTS_FILE = Path("/tmp/img_crawl_results.txt")
REVIEWED_FILE = Path("/tmp/img_reviewed_results.txt")

# ====== 配置 ======
# 视觉模型 API（通过 OpenClaw 网关或直连）
API_BASE = os.environ.get("IMAGE_REVIEW_API_BASE", "http://localhost:9900")
API_KEY = os.environ.get("IMAGE_REVIEW_API_KEY", "no-key")
MODEL = os.environ.get("IMAGE_REVIEW_MODEL", "")

# 如果未设置 MODEL，自动检测可用模型
if not MODEL:
    # 尝试通过 OpenClaw 网关
    try:
        r = subprocess.run(
            ["curl", "-s", f"{API_BASE}/v1/models"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            models = [m.get("id", "") for m in data.get("data", [])]
            # 优先选视觉模型
            vision_keywords = ["vision", "gemini", "claude", "gpt-4o", "multimodal"]
            for kw in vision_keywords:
                for m in models:
                    if kw.lower() in m.lower():
                        MODEL = m
                        break
                if MODEL:
                    break
            if not MODEL and models:
                MODEL = models[0]
    except Exception as e:
        print(f"⚠️ 无法获取模型列表: {e}")

if not MODEL:
    print("❌ 未找到可用的视觉模型，请设置 IMAGE_REVIEW_MODEL 环境变量")
    sys.exit(1)

print(f"🤖 审核模型: {MODEL}")
print()

# ====== 读取爬取结果 ======
id_data = {}
for line in RESULTS_FILE.read_text().strip().split("\n"):
    if not line.strip():
        continue
    parts = line.split("|")
    detail_id = parts[0]
    status = parts[1]
    path = parts[2] if len(parts) > 2 else ""
    if status == "OK" and path:
        id_data[detail_id] = {
            "img_path": path,
            "full_path": DIST / path,
        }

print(f"=== 共 {len(id_data)} 张图片待审核 ===\n")

# ====== 从 section HTML 中提取新闻内容摘要 ======
def get_news_context(detail_id):
    """提取对应新闻的标题和正文内容作为审核上下文"""
    for section_file in sorted((DIST / "sections").glob("*.html")):
        content = section_file.read_text(encoding="utf-8")
        # 找到对应 template
        pattern = rf'<template[^>]*data-id="{re.escape(detail_id)}"[^>]*>(.*?)</template>'
        m = re.search(pattern, content, re.DOTALL)
        if m:
            tpl = m.group(1)
            # 提取标题 h2
            h2_m = re.search(r'<h2[^>]*>(.*?)</h2>', tpl, re.DOTALL)
            title = h2_m.group(1).strip() if h2_m else ""
            # 提取所有 <p> 正文
            paras = re.findall(r'<p[^>]*>(.*?)</p>', tpl, re.DOTALL)
            body = " ".join(re.sub(r'<[^>]+>', '', p).strip() for p in paras)
            # 提取 detail-tag
            tag_m = re.search(r'<span[^>]*detail-tag[^>]*>(.*?)</span>', tpl, re.DOTALL)
            tag = re.sub(r'<[^>]+>', '', tag_m.group(1)).strip() if tag_m else ""
            return {
                "title": title,
                "tag": tag,
                "body": body[:800],  # 截取前 800 字符
            }
    return None

# ====== AI 视觉审核 ======
def review_image(img_path, context):
    """调用视觉模型判断图片是否与新闻内容相关"""
    if not img_path.exists():
        return False, "文件不存在"

    # 将图片转为 base64
    import base64
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    # 判断 MIME 类型
    ext = img_path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    mime_type = mime_map.get(ext, "image/jpeg")

    prompt = f"""你是一个新闻图片审核员。请判断这张图片是否与以下新闻内容相关。

新闻标题：{context['title']}
新闻标签：{context['tag']}
新闻摘要：{context['body'][:500]}

判断标准：
- ✅ 通过（PASS）：图片内容与新闻主题高度相关（相关人物、场景、事件、数据图表等）
- ❌ 不通过（FAIL）：图片是通用图库照、网站 logo、广告图、完全无关的风景/人物、低质量图片、或图片内容与新闻无关

只回复 PASS 或 FAIL，一个词即可。"""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{img_b64}",
                            "detail": "low"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 10,
        "temperature": 0
    }

    try:
        r = subprocess.run(
            ["curl", "-s", f"{API_BASE}/v1/chat/completions",
             "-H", f"Authorization: Bearer {API_KEY}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            print(f"    ⚠️ API 调用失败: {r.stderr[:200]}")
            return False, "API 错误"

        result = json.loads(r.stdout)
        if "choices" not in result or not result["choices"]:
            print(f"    ⚠️ API 返回异常: {json.dumps(result, ensure_ascii=False)[:300]}")
            return False, "API 返回异常"

        answer = result["choices"][0]["message"]["content"].strip().upper()
        passed = "PASS" in answer
        return passed, answer
    except json.JSONDecodeError as e:
        print(f"    ⚠️ JSON 解析失败: {r.stdout[:300]}")
        return False, "JSON 解析错误"
    except Exception as e:
        print(f"    ⚠️ 审核失败: {e}")
        return False, str(e)

# ====== 执行审核 ======
reviewed = {}
i = 0
for detail_id, data in sorted(id_data.items()):
    i += 1
    context = get_news_context(detail_id)
    if not context:
        print(f"[{i}/{len(id_data)}] ⏭️ {detail_id} - 无新闻上下文，保留图片")
        reviewed[detail_id] = "OK"
        continue

    print(f"[{i}/{len(id_data)}] 🔍 审核: {detail_id}")
    print(f"    📰 {context['title'][:60]}...")
    print(f"    🖼️ {data['img_path']} ({data['full_path'].stat().st_size // 1024}KB)")

    passed, reason = review_image(data["full_path"], context)

    if passed:
        print(f"    ✅ 审核通过: {reason}")
        reviewed[detail_id] = "OK"
    else:
        print(f"    ❌ 审核不通过: {reason}")
        # 删除不合格图片
        data["full_path"].unlink(missing_ok=True)
        reviewed[detail_id] = "FAIL"
    print()

# ====== 写审核结果 ======
with open(REVIEWED_FILE, "w") as f:
    for detail_id, status in sorted(reviewed.items()):
        f.write(f"{detail_id}|{status}|{'assets/images/' + detail_id + '.jpg' if status == 'OK' else ''}\n")

ok_count = sum(1 for v in reviewed.values() if v == "OK")
fail_count = sum(1 for v in reviewed.values() if v == "FAIL")
print(f"=== 审核完成: 通过 {ok_count} / 不通过 {fail_count} ===")
print(f"结果已写入 {REVIEWED_FILE}")
