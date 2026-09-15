#!/usr/bin/env python3
"""Turn fetched candidates (dist/candidates.json) into section HTML.

Reads candidates.json, asks the unified LLM (logic model "content") for a
one-sentence Chinese summary + content tag per item, then renders section
HTML files with the exact card/detail template used by the live site.

This replaces the Hermes-agent browsing session for the summarization step:
fetching is done by fetch_news_candidates.py (static RSS), and this script only
does cheap LLM text work. Reuses the same HTML shapes as tools/generate_current.py.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from niu_core.llm_client import NiuLLM  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
CANDIDATES = HERE / "dist" / "candidates.json"
OUT_DIR = HERE / "dist" / "sections"

META = {
    "domestic": ("国内", "国内要闻", "tag-green", "中华网/中新网"),
    "international": ("国际", "国际焦点", "tag-red", "BBC中文/联合早报"),
    "finance": ("财经", "财经快讯", "tag-purple", "东方财富网/财联社"),
    "tech": ("科技", "科技动态", "tag-blue", "IT之家/中新网"),
    "ai": ("AI", "人工智能", "tag-orange", "IT之家/中新网"),
}

MAX_PER_SECTION = int(os.environ.get("NEWS_MAX_PER_SECTION", "5"))

REDACTED = ""  # placeholder kept for grep-safety; no secrets ever printed

SYSTEM = (
    "你是牛秘书新闻社的编辑。给每条新闻写：tag(2-6字分类标签), summary(55-80字中文摘要,"
    "基于标题和已有摘要改写,不编造事实,不添加原文没有的数据)。"
    "严格输出 JSON 数组,每项 {\"i\": 序号, \"tag\": \"..\", \"summary\": \"..\"}。只输出 JSON。"
)


def llm_summarize(llm: NiuLLM, items: list[dict]) -> list[dict]:
    """Batch-summarize up to ~10 items in one call; returns parsed list."""
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it['title']}\n   已有摘要: {it.get('summary','')[:120]}\n   来源: {it.get('source','')}")
    prompt = "给下面每条新闻写分类标签和55-80字中文摘要:\n" + "\n".join(lines)
    rsp = llm.chat("content", [
        {"role": "system", "content": "只输出 JSON 数组,不输出其他任何文字。"},
        {"role": "user", "content": prompt},
    ], temperature=0.1)
    text = rsp.text.strip()
    # strip code fences
    import re as _re
    text = _re.sub(r"^```(?:json)?\s*", "", text)
    text = _re.sub(r"\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = parsed.get("items") or parsed.get("data") or []
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def render_section(cat: str, rows: list[dict], date_str: str) -> str:
    sec, name, color, source = META[cat]
    chunks = []
    for n, it in enumerate(rows, 1):
        oid = f"{cat}-{n}"
        te = escape(it["title"])
        se = escape(it.get("summary", ""))
        tag = escape(it.get("tag", sec))
        ue = escape(it["url"], quote=True)
        chunks.append(
            f'<a class="card-link" onclick="openDetail(\'{oid}\'); return false;" href="#">'
            f'<div class="news-card"><span class="tag {color}">{tag}</span>'
            f'<div class="emoji-icon">📰</div><h3>{te}</h3>'
            f'<p class="card-summary">{se}</p><div class="expand-hint">点击查看详情 →</div></div></a>\n'
            f'<template id="detail-{oid}"><div class="detail-meta"><span>📅 {date_str}</span>'
            f'<span>📰 {source}</span><span class="tag {color}">{tag}</span></div>'
            f'<div class="detail-visual"></div><h2>{te}</h2>'
            f'<div class="detail-keypoints"><div class="keypoint-card"><span>事件</span><strong>{se}</strong></div>'
            f'<div class="keypoint-card"><span>影响</span><strong>{escape(tag)}领域出现新的值得关注变化</strong></div>'
            f'<div class="keypoint-card"><span>数据</span><strong>原文标题与摘要披露了相关进展</strong></div>'
            f'<div class="keypoint-card"><span>后续</span><strong>后续影响取决于实际推进和公开信息</strong></div></div>'
            f"<p>{se}</p>"
            f"<p>这条消息反映出当前{sec}领域的最新动向，后续进展仍值得持续关注。</p>"
            f'<a class="external-btn" href="{ue}" target="_blank" rel="noopener">阅读原文</a></template>'
        )
    return "\n".join(chunks)


def main() -> int:
    data = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    date_str = datetime.now().strftime("%Y-%m-%d")
    llm = NiuLLM.load()

    sections_out = {}
    total_llm_failed = 0
    for cat, items in data["sections"].items():
        if cat not in META:
            continue
        if not items:
            print(f"  {cat}: no candidates, keeping existing section untouched")
            continue
        picked = items[:MAX_PER_SECTION]
        summaries = llm_summarize(llm, picked)
        if not summaries:
            print(f"  {cat}: LLM summary failed, using fallback summaries", file=sys.stderr)
            summaries = [{"i": i + 1, "tag": META[cat][0], "summary": it.get("summary") or it["title"]}
                         for i, it in enumerate(picked)]
        by_i = {s.get("i"): s for s in summaries if isinstance(s, dict) and s.get("i")}
        rows = []
        for i, it in enumerate(picked, 1):
            s = by_i.get(i, {})
            rows.append({
                "title": it["title"],
                "url": it["url"],
                "tag": s.get("tag") or META[cat][0],
                "summary": s.get("summary") or it.get("summary") or it["title"],
                "source": it.get("source", ""),
            })
        html = render_section(cat, rows, date_str)
        out_file = OUT_DIR / f"{cat}.html"
        out_file.write_text(html, encoding="utf-8")
        sections_used = len(rows)
        print(f"  {cat}: wrote {len(rows)} items -> {out_file.name}")
        sections_out = None  # placeholder lint

    print("sections updated:", sorted(p.name for p in OUT_DIR.glob("*.html") if p.exists()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
