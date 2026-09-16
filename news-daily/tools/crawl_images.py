#!/usr/bin/env python3
"""从每条新闻的真实原文页面提取配图。

只使用 external-btn/sourceUrl 指向的原文页，不使用通用图片搜索。
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests

from extract_news_json import build_news_json
from image_rules import extract_image_candidates


DIST = Path(__file__).resolve().parents[1] / "dist"
IMG_DIR = DIST / "assets" / "images"
RESULT_FILE = Path("/tmp/img_crawl_results.txt")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def output_id(item: dict) -> str:
    open_id = item.get("openId") or item.get("id") or ""
    return open_id.replace("detail-", "")


def extension_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def fetch_html(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    if response.encoding is None:
        response.encoding = response.apparent_encoding
    return response.text


def file_is_image(path: Path) -> bool:
    result = subprocess.run(["file", str(path)], capture_output=True, text=True, check=False)
    return "image" in result.stdout.lower()


def download_image(url: str, target: Path, min_size: int = 5000) -> str:
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        response.raise_for_status()
    except Exception:
        return "FETCH_FAILED"

    content_type = response.headers.get("content-type", "").lower()
    if "image" not in content_type and not any(
        url.lower().split("?")[0].endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")
    ):
        return "REJECTED_FORMAT"
    if len(response.content) < min_size:
        return "REJECTED_SMALL"

    target.write_bytes(response.content)
    if not file_is_image(target):
        target.unlink(missing_ok=True)
        return "REJECTED_FORMAT"
    return "OK"


def main() -> int:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    for old in IMG_DIR.glob("*.*"):
        old.unlink()

    payload = build_news_json(DIST)
    results: list[tuple[str, str, str, str, int]] = []
    print(f"=== 共 {len(payload['items'])} 条新闻需要从原文抓取配图 ===")

    for item in payload["items"]:
        ident = output_id(item)
        source_url = item.get("sourceUrl", "")
        title = item.get("title", "")
        print(f"\n[{ident}] {title[:60]}")

        if not source_url:
            print("  缺少原文 URL")
            results.append((ident, "FETCH_FAILED", "", "", 0))
            continue

        try:
            html = fetch_html(source_url)
        except Exception as exc:
            print(f"  原文抓取失败: {exc}")
            results.append((ident, "FETCH_FAILED", "", "", 0))
            continue

        candidates = extract_image_candidates(html, source_url, title)
        ok_candidates = [candidate for candidate in candidates if candidate["status"] == "OK"]
        if not ok_candidates:
            status = candidates[0]["status"] if candidates else "NO_IMAGE"
            print(f"  无可靠配图: {status}")
            candidate_url = candidates[0]["url"] if candidates else ""
            candidate_score = int(candidates[0]["score"]) if candidates else 0
            results.append((ident, status, "", candidate_url, candidate_score))
            continue

        final_status = "NO_IMAGE"
        final_path = ""
        final_url = ""
        final_score = 0
        for candidate in ok_candidates[:5]:
            ext = extension_from_url(candidate["url"])
            local_file = IMG_DIR / f"{ident}{ext}"
            status = download_image(candidate["url"], local_file)
            if status == "OK":
                final_status = "OK"
                final_path = f"assets/images/{local_file.name}"
                final_url = candidate["url"]
                final_score = int(candidate["score"])
                print(f"  OK: {candidate['url'][:100]}")
                break
            print(f"  候选图拒绝: {status} {candidate['url'][:100]}")

        results.append((ident, final_status, final_path, final_url, final_score))

    ok_count = sum(1 for _, status, _, _, _ in results if status == "OK")
    print(f"\n=== 配图结果: OK {ok_count} / {len(results)} ===")
    with RESULT_FILE.open("w", encoding="utf-8") as handle:
        for ident, status, path, url, score in results:
            handle.write(f"{ident}|{status}|{path}|{url}|{score}\n")
    print(f"结果已写入 {RESULT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
