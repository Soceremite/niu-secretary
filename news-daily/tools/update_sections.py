#!/usr/bin/env python3
"""根据 AI 审核结果更新 section HTML：
- 有图（审核通过）：确保 detail-visual 存在且 img src 正确
- 无图（审核不通过/未爬取）：移除 detail-visual 整行

优先使用审核结果 /tmp/img_reviewed_results.txt
fallback 使用爬取结果 /tmp/img_crawl_results.txt
"""
import re
from pathlib import Path

DIST = Path("/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist")
REVIEWED_FILE = Path("/tmp/img_reviewed_results.txt")
CRAWL_FILE = Path("/tmp/img_crawl_results.txt")

# 优先使用审核结果，fallback 爬取结果
results_file = REVIEWED_FILE if REVIEWED_FILE.exists() else CRAWL_FILE
print(f"📄 使用结果文件: {results_file}")

results = {}
for line in results_file.read_text().strip().split("\n"):
    if not line.strip():
        continue
    parts = line.split("|")
    detail_id = parts[0]
    status = parts[1]
    path = parts[2] if len(parts) > 2 else ""
    results[detail_id] = path if status == "OK" else None

print(f"✅ 加载 {len(results)} 条结果 (通过: {sum(1 for v in results.values() if v)})")

for section_file in sorted((DIST / "sections").glob("*.html")):
    content = section_file.read_text(encoding="utf-8")
    original = content

    # 处理每个 template
    def process_template(m):
        full = m.group(0)
        id_m = re.search(r'data-id="([^"]+)"', full)
        if not id_m:
            return full
        detail_id = id_m.group(1)
        img_path = results.get(detail_id)

        # 先移除已有的 detail-visual
        cleaned = re.sub(
            r'\s*<div class="detail-visual"[^>]*>.*?</div>\s*',
            '\n',
            full,
            flags=re.DOTALL
        )

        if img_path:
            # 有图：在 detail-meta 后面插入 detail-visual
            img_html = f'  <div class="detail-visual"><img src="{img_path}" alt="" onerror="this.parentElement.style.display=\'none\'"></div>'

            # 尝试在 detail-meta 后面插入
            new_cleaned = re.sub(
                r'(</div>\s*<!-- detail-meta end -->|<div class="detail-meta">[^<]*</div>)',
                lambda x: x.group(0) + '\n' + img_html,
                cleaned,
                count=1
            )
            if new_cleaned != cleaned:
                cleaned = new_cleaned
            elif img_path not in cleaned:
                # 在第一个 <p> 前面插入
                cleaned = re.sub(
                    r'(\n\s*<p>)',
                    '\n' + img_html + r'\1',
                    cleaned,
                    count=1
                )

        return cleaned

    content = re.sub(
        r'<template class="detail-tpl"[^>]*>.*?</template>',
        process_template,
        content,
        flags=re.DOTALL
    )

    if content != original:
        section_file.write_text(content, encoding="utf-8")
        print(f"✅ 更新: {section_file.name}")
    else:
        print(f"⏭️ 无变化: {section_file.name}")

print("\n=== 完成 ===")
