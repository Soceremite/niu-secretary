#!/usr/bin/env python3
"""Generate the QQ-facing news briefing from the built sections.

Reads dist/sections/*.html (title + summary + url), calls the unified LLM
(logic model "content") to write a morning-briefing style digest with a
[重点关注] top-3, then prints ONLY the briefing text (stdout is what the
cron job delivers to QQ). No logs, no verification output.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from niu_core.llm_client import NiuLLM  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
SECTIONS = HERE / "dist" / "sections"

SECTION_LABELS = {
    "domestic": "国内",
    "international": "国际",
    "finance": "财经",
    "tech": "科技/AI",
    "ai": "AI",
}


def extract_items(cat: str) -> list[dict[str, str]]:
    text = (SECTIONS / f"{cat}.html").read_text(encoding="utf-8")
    items = []
    for m in re.finditer(
        r'<h3>(.*?)</h3><p class="card-summary">(.*?)</p>', text, re.DOTALL
    ):
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        summary = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if title:
            items.append({"title": title, "summary": summary})
    return items


def main() -> int:
    sections = {}
    for cat in ("domestic", "international", "finance", "tech", "ai"):
        items = extract_items(cat)
        if items:
            sections[cat] = items
    # merge tech + ai into a single 科技/AI block
    if "ai" in sections:
        sections["tech"] = (sections.get("tech") or []) + [
            it for it in sections["ai"] if it not in (sections.get("tech") or [])
        ]
        sections.pop("ai", None)

    overview_lines = []
    for cat, label in SECTION_LABELS.items():
        if cat not in sections:
            continue
        for it in sections[cat][:6]:
            overview_lines.append(f"{label}|{it['title']}|{it['summary']}")
    if not overview_lines:
        print("今日暂无可推送的新闻内容。")
        return 1

    llm = NiuLLM.load()
    feed = "\n".join(f"{i+1}. [{l}] {t} — {s}" for i, (l, t, s) in
                     enumerate(x.split("|", 2) for x in overview_lines))
    prompt = f"""根据以下今日新闻列表,写一份手机端 QQ 晨间简报,严格按此格式:

📰 牛秘书·今日新闻速递

今日简报：<2-3句概括五个板块整体趋势>

【重点关注】
1. <标题> — <1-2句核心事实和为什么值得关注>
2. <标题> — <1-2句>
3. <标题> — <1-2句>

【国内】
1. <标题> — <一句话>

【国际】
1. <标题> — <一句话>

【财经】
1. <标题> — <一句话>

【科技/AI】
1. <标题> — <一句话>

规则:只写新闻本身,不写"已生成/验证通过"等技术词;不带 Markdown 表格和代码块;每条一句话,精炼。

新闻列表:
{feed}"""

    rsp = llm.chat("content", [{"role": "user", "content": prompt}], temperature=0.3)
    text = rsp.text.strip()
    text = re.sub(r"^```[a-z]*\s*", "", text).strip()
    if "📰" not in text:
        print("LLM briefing 格式异常，回退到纯列表输出", file=sys.stderr)
        lines = [f"[{SECTION_LABELS.get(x.split('|')[0], x.split('|')[0])}] {x.split('|')[1]}" for x in overview_lines[:15]]
        text = "📰 牛秘书·今日新闻速递\n\n" + "\n".join(lines)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
