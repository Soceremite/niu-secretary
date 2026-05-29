#!/usr/bin/env python3
"""从新闻原文页面爬取配图
优先级：
1. 正文中的大图（<img> 标签，过滤 logo/icon/avatar 等小图）
2. og:image / twitter:image 作为 fallback
"""
import re, subprocess
from pathlib import Path
from urllib.parse import urljoin

DIST = Path("/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist")
IMG_DIR = DIST / "assets" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

# 清理旧图片
for f in IMG_DIR.glob("*.*"):
    f.unlink()

# 收集 detail-id 和原文 URL
id_url_map = {}
for section_file in sorted((DIST / "sections").glob("*.html")):
    content = section_file.read_text(encoding="utf-8")
    templates = re.finditer(r'<template[^>]*data-id="([^"]+)"[^>]*>(.*?)</template>', content, re.DOTALL)
    for m in templates:
        detail_id = m.group(1)
        tpl_content = m.group(2)
        link_m = re.search(r'external-btn[^>]*href="(https?://[^"]+)"', tpl_content)
        if link_m:
            id_url_map[detail_id] = link_m.group(1)

print(f"=== 共 {len(id_url_map)} 条新闻需要爬取配图 ===\n")

# 过滤关键词：这些出现在 src/class/id 中的图片跳过
SKIP_KEYWORDS = [
    'logo', 'icon', 'avatar', 'badge', 'emoji', 'sprite',
    'banner-ad', 'advertisement', 'tracking', 'pixel',
    'share', 'social', 'button', 'arrow', 'loading',
    'placeholder', 'default', 'blank', '1x1', 'spacer',
    'footer', 'header-logo', 'site-logo', 'favicon',
]

def is_likely_content_image(img_tag, src):
    """判断是否是正文配图（非 logo/icon/广告）"""
    lower_src = src.lower()
    lower_tag = img_tag.lower()

    for kw in SKIP_KEYWORDS:
        if kw in lower_src or kw in lower_tag:
            return False

    # 跳过 base64 data URI（通常是小图标）
    if src.startswith("data:"):
        return False

    # 跳过明显的小尺寸（如果 HTML 中指定了 width/height）
    w_m = re.search(r'width[=:]\s*["\']?(\d+)', img_tag)
    h_m = re.search(r'height[=:]\s*["\']?(\d+)', img_tag)
    if w_m and int(w_m.group(1)) < 100:
        return False
    if h_m and int(h_m.group(1)) < 100:
        return False

    return True

def find_content_images(html, base_url):
    """从正文中提取候选大图 URL 列表"""
    candidates = []

    # 找所有 <img> 标签
    img_tags = re.finditer(r'<img[^>]+>', html, re.IGNORECASE)
    for img_m in img_tags:
        img_tag = img_m.group(0)
        # 提取 src
        src_m = re.search(r'src=["\']([^"\']+)["\']', img_tag)
        if not src_m:
            continue
        src = src_m.group(1)

        if not is_likely_content_image(img_tag, src):
            continue

        # 处理相对 URL
        if src.startswith("//"):
            src = "https:" + src
        elif not src.startswith("http"):
            src = urljoin(base_url, src)

        candidates.append(src)

    return candidates

def find_og_image(html):
    """提取 og:image / twitter:image"""
    patterns = [
        r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
        r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            url = m.group(1)
            if url.startswith("//"):
                url = "https:" + url
            return url
    return None

def download_image(img_url, local_file, min_size=5000):
    """下载图片，返回是否成功"""
    try:
        dl = subprocess.run(
            ["curl", "-sL", "--max-time", "15", "-A",
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             "-o", str(local_file), img_url],
            capture_output=True, timeout=20
        )
        if not local_file.exists():
            return False
        size = local_file.stat().st_size
        if size < min_size:
            local_file.unlink(missing_ok=True)
            return False
        # 验证是图片文件
        r = subprocess.run(["file", str(local_file)], capture_output=True, text=True)
        if "image" not in r.stdout.lower():
            local_file.unlink(missing_ok=True)
            return False
        return True
    except Exception:
        local_file.unlink(missing_ok=True)
        return False

results = {}

for detail_id in sorted(id_url_map.keys()):
    url = id_url_map[detail_id]
    print(f"[{detail_id}] {url[:70]}")

    # 获取页面
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "10", "-A",
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             url],
            capture_output=True, text=True, timeout=15
        )
        html = r.stdout
    except Exception:
        html = ""

    if not html or len(html) < 200:
        print("  ❌ 页面获取失败\n")
        results[detail_id] = None
        continue

    local_file = IMG_DIR / f"{detail_id}.jpg"
    success = False

    # 策略1：正文大图
    content_imgs = find_content_images(html, url)
    if content_imgs:
        print(f"  📷 找到 {len(content_imgs)} 张候选正文图片")
        for i, img_url in enumerate(content_imgs[:5]):  # 最多试前5张
            print(f"    尝试 [{i+1}]: {img_url[:80]}... ", end="", flush=True)
            if download_image(img_url, local_file):
                size = local_file.stat().st_size
                print(f"✅ {size//1024}KB")
                results[detail_id] = f"assets/images/{detail_id}.jpg"
                success = True
                break
            else:
                print("❌")

    # 策略2：og:image fallback
    if not success:
        og_url = find_og_image(html)
        if og_url:
            print(f"  🏷️ 尝试 og:image: {og_url[:80]}... ", end="", flush=True)
            if download_image(og_url, local_file):
                size = local_file.stat().st_size
                print(f"✅ {size//1024}KB")
                results[detail_id] = f"assets/images/{detail_id}.jpg"
                success = True
            else:
                print("❌")

    if not success:
        print("  ❌ 无可用配图")
        results[detail_id] = None

    print()

# 汇总
ok = sum(1 for v in results.values() if v)
fail = sum(1 for v in results.values() if not v)
print(f"=== 结果: 成功 {ok} / 失败 {fail} ===")

# 写结果文件
with open("/tmp/img_crawl_results.txt", "w") as f:
    for detail_id, path in sorted(results.items()):
        f.write(f"{detail_id}|{'OK' if path else 'FAIL'}|{path or ''}\n")

print("结果已写入 /tmp/img_crawl_results.txt")
