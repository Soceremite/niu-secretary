#!/usr/bin/env python3
"""根据图片抓取/审核结果更新 section HTML。

- OK：插入或更新 detail-visual 图片。
- 其他已知状态：移除 detail-visual，避免错图上线。
"""
from __future__ import annotations

import json
import re
from pathlib import Path


DIST = Path(__file__).resolve().parents[1] / "dist"
REVIEWED_JSON = DIST / "image_review.json"
REVIEWED_FILE = Path("/tmp/img_reviewed_results.txt")
CRAWL_FILE = Path("/tmp/img_crawl_results.txt")
KNOWN_STATUSES = {
    "OK",
    "NO_IMAGE",
    "FETCH_FAILED",
    "REJECTED_LOGO",
    "REJECTED_QRCODE",
    "REJECTED_SMALL",
    "REJECTED_FORMAT",
    "REJECTED_AD",
    "REJECTED_PLACEHOLDER",
    "FAIL",
}


def choose_results_file() -> Path | None:
    candidates = [REVIEWED_JSON, REVIEWED_FILE, CRAWL_FILE]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def normalize_id(value: str) -> str:
    return (value or "").strip().replace("detail-", "", 1)


def load_results_json(path: Path) -> dict[str, str | None]:
    """从 dist/image_review.json 读取审核结果。

    JSON 格式: {"results": [{"image": "domestic-1.jpg", "verdict": "pass"}, ...]}
    image 字段是文件名，去掉扩展名后作为 ID（domestic-1.jpg → domestic-1）。
    verdict "pass" → 使用 CRAWL_FILE 中对应的已爬取路径；其他 → 无图。
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # 先从 CRAWL_FILE 建立文件名→路径映射
    crawl_paths: dict[str, str] = {}
    if CRAWL_FILE.exists():
        for line in CRAWL_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) >= 3 and parts[1] == "OK" and parts[2]:
                crawl_paths[parts[0]] = parts[2]

    results: dict[str, str | None] = {}
    for item in data.get("results", []):
        image_name = item.get("image", "")
        verdict = item.get("verdict", "")
        # domestic-1.jpg → domestic-1
        ident = normalize_id(Path(image_name).stem)
        if verdict == "pass":
            results[ident] = crawl_paths.get(ident, "")
        else:
            results[ident] = None
    return results


def load_results_txt(path: Path) -> dict[str, str | None]:
    results: dict[str, str | None] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        ident = normalize_id(parts[0])
        status = parts[1] if len(parts) > 1 else ""
        img_path = parts[2] if len(parts) > 2 else ""
        if status not in KNOWN_STATUSES:
            print(f"⚠️ 未知状态，按无图处理: {ident} {status}")
        results[ident] = img_path if status == "OK" and img_path else None
    return results


def update_template(full: str, results: dict[str, str | None]) -> str:
    id_match = re.search(r'(?:data-id|id)=["\']([^"\']+)["\']', full)
    if not id_match:
        return full

    ident = normalize_id(id_match.group(1))
    img_path = results.get(ident)
    cleaned = re.sub(
        r'\s*<div class="detail-visual"[^>]*>.*?</div>\s*',
        "\n",
        full,
        flags=re.DOTALL,
    )

    if not img_path:
        return cleaned

    img_html = (
        f'  <div class="detail-visual"><img src="{img_path}" alt="" '
        "onerror=\"this.parentElement.style.display='none'\"></div>"
    )
    updated = re.sub(
        r'(<div class="detail-meta">.*?</div>)',
        lambda match: match.group(1) + "\n" + img_html,
        cleaned,
        count=1,
        flags=re.DOTALL,
    )
    if updated != cleaned:
        return updated
    return re.sub(r"(\n\s*<p>)", "\n" + img_html + r"\1", cleaned, count=1)


def main() -> int:
    results_file = choose_results_file()
    if results_file is None:
        print(f"❌ 找不到图片结果文件: {REVIEWED_JSON} 或 {REVIEWED_FILE} 或 {CRAWL_FILE}")
        return 1

    print(f"📄 使用结果文件: {results_file}")
    if results_file == REVIEWED_JSON:
        results = load_results_json(results_file)
    else:
        results = load_results_txt(results_file)
    print(f"✅ 加载 {len(results)} 条结果 (通过: {sum(1 for v in results.values() if v)})")

    for section_file in sorted((DIST / "sections").glob("*.html")):
        content = section_file.read_text(encoding="utf-8")
        original = content
        content = re.sub(
            r"<template\b[^>]*(?:data-id|id)=['\"][^'\"]+['\"][^>]*>.*?</template>",
            lambda match: update_template(match.group(0), results),
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if content != original:
            section_file.write_text(content, encoding="utf-8")
            print(f"✅ 更新: {section_file.name}")
        else:
            print(f"⏭️ 无变化: {section_file.name}")

    print("\n=== 完成 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
