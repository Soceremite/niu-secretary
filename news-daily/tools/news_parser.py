#!/usr/bin/env python3
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any


SECTION_NAMES = {
    "domestic": "国内要闻",
    "international": "国际焦点",
    "finance": "财经快讯",
    "tech": "科技动态",
    "ai": "人工智能",
}


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def normalize_detail_id(value: str) -> str:
    normalized = re.sub(r"^detail-", "", (value or "").strip())
    return re.sub(r"-detail$", "", normalized)


def ensure_detail_heading(detail_html: str, title: str) -> str:
    """Older generated fragments sometimes omit the detail h2."""
    if not detail_html or re.search(r"<h2\b", detail_html, flags=re.IGNORECASE):
        return detail_html
    heading = f"<h2>{html.escape(title)}</h2>"
    meta = re.search(
        r'(<div[^>]*class=["\'][^"\']*\bdetail-meta\b[^"\']*["\'][^>]*>.*?</div>)',
        detail_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if meta:
        return detail_html[: meta.end()] + "\n  " + heading + detail_html[meta.end() :]
    return heading + "\n" + detail_html


def parse_source_name(meta_text: str) -> str:
    meta_text = meta_text.replace("\xa0", " ")
    if "📎" in meta_text:
        return meta_text.split("📎")[-1].strip()
    if "📰" in meta_text:
        return meta_text.split("📰")[-1].strip()
    match = re.search(r"(?:📡|来源[:：]?)\s*([^|]+)$", meta_text)
    return match.group(1).strip() if match else ""


def _extract_templates(content: str) -> dict[str, str]:
    templates: dict[str, str] = {}
    for match in re.finditer(
        r"<template\b([^>]*)>(.*?)</template>",
        content,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        attrs = match.group(1)
        body = match.group(2)
        id_match = re.search(r'(?:data-id|id)=["\']([^"\']+)["\']', attrs)
        if not id_match:
            continue
        raw_id = id_match.group(1).strip()
        templates[raw_id] = body
        templates[normalize_detail_id(raw_id)] = body
    return templates


def _extract_card_blocks(content: str) -> list[tuple[str, str]]:
    cards: list[tuple[str, str]] = []
    pattern = re.compile(
        r'<a\b(?=[^>]*class=["\'][^"\']*\bcard-link\b[^"\']*["\'])[^>]*'
        r"openDetail\((['\"])([^'\"]+)\1\)[^>]*>(.*?)</a>",
        flags=re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(content):
        cards.append((match.group(2), match.group(3)))
    return cards


def parse_section_html(content: str, section: str) -> list[dict[str, Any]]:
    templates = _extract_templates(content)
    items: list[dict[str, Any]] = []

    for raw_detail_id, card_html in _extract_card_blocks(content):
        normalized_id = normalize_detail_id(raw_detail_id)
        template_id = f"detail-{normalized_id}"
        detail_html = templates.get(raw_detail_id) or templates.get(normalized_id) or ""

        title_match = re.search(
            r"<h3[^>]*>(.*?)</h3>", card_html, flags=re.DOTALL | re.IGNORECASE
        )
        summary_match = re.search(
            r'<p[^>]*class=["\'][^"\']*\bcard-summary\b[^"\']*["\'][^>]*>(.*?)</p>',
            card_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        meta_match = re.search(
            r'<div[^>]*class=["\'][^"\']*\bdetail-meta\b[^"\']*["\'][^>]*>(.*?)</div>',
            detail_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        source_match = re.search(
            r'<a[^>]*class=["\'][^"\']*\bexternal-btn\b[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
            detail_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        tag_values = re.findall(
            r'<span[^>]*class=["\'][^"\']*\btag\b[^"\']*["\'][^>]*>(.*?)</span>',
            card_html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        meta_text = strip_tags(meta_match.group(1)) if meta_match else ""
        image_match = re.search(
            r'<div[^>]*class=["\'][^"\']*\bdetail-visual\b[^"\']*["\'][^>]*>.*?<img[^>]*src=["\']([^"\']*)["\']',
            detail_html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        title = strip_tags(title_match.group(1)) if title_match else ""
        detail_html = ensure_detail_heading(detail_html.strip(), title)

        items.append(
            {
                "id": template_id,
                "openId": raw_detail_id,
                "section": section,
                "sectionName": SECTION_NAMES.get(section, section),
                "title": title,
                "summary": strip_tags(summary_match.group(1)) if summary_match else "",
                "dateText": meta_text,
                "sourceName": parse_source_name(meta_text),
                "sourceUrl": html.unescape(source_match.group(1)).strip()
                if source_match
                else "",
                "tags": [strip_tags(tag) for tag in tag_values],
                "detailHtml": detail_html,
                "imagePath": image_match.group(1).strip() if image_match else "",
            }
        )

    return items


def parse_sections_dir(sections_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for section in SECTION_NAMES:
        path = sections_dir / f"{section}.html"
        if path.exists():
            items.extend(parse_section_html(path.read_text(encoding="utf-8"), section))
    return items
