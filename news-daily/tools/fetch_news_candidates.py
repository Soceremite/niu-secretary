#!/usr/bin/env python3
"""Fetch today's news candidates from official media RSS/HTML endpoints.

No LLM, no browser: plain HTTP + stdlib parsing. Sources are the official
media list from news-daily/SKILL.md. Output: news-daily/dist/candidates.json
with sections: domestic / international / finance / tech / ai, each item
{title, url, source, fetched_at} — one row per verified article URL.

Used by run_pipeline.sh between fetch and LLM-summarize steps so the LLM only
writes summaries for pre-verified URLs, reducing hallucinated links.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parents[1] / "dist" / "candidates.json"

SITES = {
    "domestic": [
        ("央视新闻", "https://news.cctv.com/2026/09/index.xml"),
        ("中新网", "https://www.chinanews.com.cn/rss/scroll-news.xml"),
        ("澎湃新闻", "https://www.thepaper.cn/rss/newsDetail_wenan.jsp"),
    ],
    "international": [
        ("BBC中文", "https://feedx.net/rss/bbc.xml"),
        ("联合早报", "https://rss.zaobao.com/rss/zaobao-realtime-world"),
    ],
    "finance": [
        ("财联社", "https://www.cls.cn/rss/roll.xml"),
        ("中新经纬", "https://www.chinanews.com.cn/rss/finance.xml"),
    ],
    "tech": [
        ("科技滚轮", "https://www.chinanews.com.cn/rss/scroll-news.xml"),
    ],
    "ai": [
        ("科技滚轮", "https://www.chinanews.com.cn/rss/scroll-news.xml"),
    ],
}

TECH_KEYWORDS = re.compile(
    r"科技|芯片|半导体|火箭|航天|无人机|机器人|5G|6G|算法|数据|算力|人形|智能网|新能源|数字经济|服务器|存储", re.I
)
AI_KEYWORDS = re.compile(r"AI|人工智能|大模型|GPT|Claude|Gemini|LLM|智能体|OpenAI|DeepSeek|人形机器人", re.I)
FINANCE_KEYWORDS = re.compile(r"经济|金融|股市|A股|沪指|央行|美联储|GDP|投资|资本|IPO|在岸|外汇", re.I)


def fetch(url: str, timeout: float = 12.0) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) NiuNewsDaily/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_rss(xml_text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = re.sub(r"<[^>]+>", "", item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if title and link:
            out.append({"title": unescape(title), "url": link,
                        "summary": unescape(desc)[:300], "pubDate": pub})
    return out


def classify(title: str, summary: str) -> str | None:
    text = f"{title} {summary}"
    if AI_KEYWORDS.search(text):
        return "ai"
    if FINANCE_KEYWORDS.search(text):
        return "finance"
    if TECH_KEYWORDS.search(text):
        return "tech"
    return None


def main() -> int:
    cutoff = datetime.now() - timedelta(days=3)
    all_items: dict[str, list[dict[str, str]]] = {k: [] for k in SITES}
    seen_urls: set[str] = set()

    for category, sources in SITES.items():
        for source_name, url in sources:
            try:
                entries = parse_rss(fetch(url))
            except Exception as exc:
                print(f"  ! {source_name}: {exc}", file=sys.stderr)
                continue
            fresh = 0
            for e in entries:
                if e["url"] in seen_urls:
                    continue
                # date filter: keep entries whose pubDate parses within cutoff
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(e["pubDate"])
                    if dt and dt < cutoff:
                        continue
                    fresh += 1
                except (ValueError, TypeError):
                    pass  # undated RSS entries keep (conservative: include)
                seen_urls.add(e["url"])
                e["source"] = source_name
                e["category"] = category
                all_items[category].append(e)
            print(f"  {source_name}: {fresh} fresh (fetched {len(entries)})")

    # Re-classify fetched neutral items into tech/ai/finance buckets
    for e in list(all_items["domestic"]):
        cat = classify(e["title"], e["summary"])
        if cat and cat != "domestic":
            all_items[cat].append({**e, "category": cat})

    payload = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "sources_fetched": len(SITES),
        "sections": {k: v[:10] for k, v in all_items.items()},
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    counts = {k: len(v) for k, v in all_items.items()}
    print("counts:", counts)
    if sum(counts.values()) == 0:
        print("ERROR: zero candidates fetched from all sources", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
