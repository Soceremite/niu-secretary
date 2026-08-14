from __future__ import annotations

import html as html_lib
import json
import re
from urllib.parse import urljoin


LOGO_WORDS = (
    "logo",
    "favicon",
    "icon",
    "sprite",
    "avatar",
    "badge",
    "site-logo",
    "newslog",
    "footer032",
    "keywordbanner",
    "key_word_banner",
    "tech_5g",
    "spcx.png",
)
QR_WORDS = ("qrcode", "qr", "wechat", "weixin", "wx", "二维码", "扫码")
AD_WORDS = ("advert", "ad-", "banner-ad", "tracking", "pixel", "doubleclick")
PLACEHOLDER_WORDS = ("default", "placeholder", "blank", "loading", "images/v2/t.png")
NON_ARTICLE_CONTEXT_WORDS = (
    "footer",
    "header",
    "nav",
    "toolbar",
    "side",
    "sidebar",
    "copyright",
    "author",
    "follow",
)
ARTICLE_HINTS = (
    "articleDetailContent",
    "kr-rich-text-wrapper",
    "article-content",
    "rich_media_content",
    "news-content",
    "post-content",
    "post_content",
    "main-content",
    "article",
    "content",
)


def reject_reason(url: str, alt: str = "") -> str:
    value = f"{url} {alt}".lower()
    if any(word in value for word in QR_WORDS):
        return "REJECTED_QRCODE"
    if any(word in value for word in LOGO_WORDS):
        return "REJECTED_LOGO"
    if any(word in value for word in AD_WORDS):
        return "REJECTED_AD"
    if any(word in value for word in PLACEHOLDER_WORDS):
        return "REJECTED_PLACEHOLDER"
    return ""


def _attr(tag: str, name: str) -> str:
    match = re.search(rf'{name}=["\']([^"\']+)["\']', tag, flags=re.IGNORECASE)
    return html_lib.unescape(match.group(1)).strip() if match else ""


def _dimension_score(tag: str) -> int:
    score = 0
    width = re.search(r'width[=:]\s*["\']?(\d+)', tag, flags=re.IGNORECASE)
    height = re.search(r'height[=:]\s*["\']?(\d+)', tag, flags=re.IGNORECASE)
    if width:
        w = int(width.group(1))
        score += 25 if w >= 300 else -80 if w < 120 else 0
    if height:
        h = int(height.group(1))
        score += 25 if h >= 180 else -80 if h < 120 else 0
    return score


def _data_size_score(tag: str) -> int:
    match = re.search(
        r'data-img-size-val=["\'](\d+)\s*,\s*(\d+)["\']',
        tag,
        flags=re.IGNORECASE,
    )
    if not match:
        return 0

    width = int(match.group(1))
    height = int(match.group(2))
    if width < 240 or height < 140:
        return -80

    ratio = width / height if height else 0
    score = 45
    if 1.35 <= ratio <= 2.8:
        score += 20
    elif ratio > 4.5 or ratio < 0.45:
        score -= 35
    return score


def _near_context(page_html: str, position: int, window: int = 420) -> str:
    start = max(0, position - window)
    return page_html[start:position].lower()


def _context_reject_reason(page_html: str, position: int) -> str:
    context = _near_context(page_html, position, window=1200)
    bad_container = max(
        context.rfind("<footer"),
        context.rfind("<header"),
        context.rfind("<nav"),
        context.rfind("<aside"),
    )
    article_container = max(
        context.rfind("<article"),
        context.rfind("<main"),
        context.rfind("article-content"),
        context.rfind("articledetailcontent"),
        context.rfind("kr-rich-text-wrapper"),
        context.rfind("rich_media_content"),
        context.rfind("news-content"),
        context.rfind("post-content"),
        context.rfind("post_content"),
        context.rfind("main-content"),
    )
    if bad_container > article_container:
        return "REJECTED_LOGO"
    non_article = max(context.rfind(word) for word in NON_ARTICLE_CONTEXT_WORDS)
    if non_article > article_container and article_container < 0:
        return "REJECTED_PLACEHOLDER"
    return ""


def _structure_score(page_html: str, position: int, tag: str) -> int:
    context = _near_context(page_html, position, window=1000)
    score = 0
    if re.search(
        r'<p\b[^>]*class=["\'][^"\']*\bimage-wrapper\b[^"\']*["\'][^>]*>$',
        context.strip(),
        flags=re.IGNORECASE,
    ):
        score += 90
    elif "image-wrapper" in context[-220:]:
        score += 70

    if "data-img-size-val" in tag.lower():
        score += _data_size_score(tag)

    if re.search(r'<h1\b[^>]*>.*?</h1>\s*(?:<[^>]+>\s*){0,5}$', context, flags=re.DOTALL | re.IGNORECASE):
        score += 25
    return score


def _article_spans(page_html: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    hint_re = "|".join(re.escape(hint) for hint in ARTICLE_HINTS)
    for match in re.finditer(
        rf'<(?:article|main|div)\b[^>]*(?:class|id)=["\'][^"\']*(?:{hint_re})[^"\']*["\'][^>]*>',
        page_html,
        flags=re.IGNORECASE,
    ):
        spans.append((match.start(), min(len(page_html), match.start() + 30000)))
    for match in re.finditer(r"<article\b[^>]*>", page_html, flags=re.IGNORECASE):
        spans.append((match.start(), min(len(page_html), match.start() + 30000)))
    return spans


def _json_ld_images(page_html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for match in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page_html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        raw = html_lib.unescape(match.group(1)).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            image = node.get("image") if isinstance(node, dict) else None
            if isinstance(image, str):
                urls.append(urljoin(base_url, image))
            elif isinstance(image, list):
                urls.extend(urljoin(base_url, item) for item in image if isinstance(item, str))
            elif isinstance(image, dict) and isinstance(image.get("url"), str):
                urls.append(urljoin(base_url, image["url"]))
    return urls


def extract_image_candidates(page_html: str, base_url: str, title: str) -> list[dict]:
    candidates: list[dict] = []
    spans = _article_spans(page_html)

    for match in re.finditer(r"<img\b[^>]*>", page_html, flags=re.IGNORECASE):
        tag = match.group(0)
        src = (
            _attr(tag, "data-original")
            or _attr(tag, "data-src")
            or _attr(tag, "data-url")
            or _attr(tag, "src")
        )
        if not src or src.startswith("data:"):
            continue
        url = urljoin(base_url, src)
        alt = _attr(tag, "alt") or _attr(tag, "title")
        reason = reject_reason(url, alt) or _context_reject_reason(page_html, match.start())
        if reason:
            candidates.append({"url": url, "score": -1000, "status": reason})
            continue

        score = _dimension_score(tag) + _structure_score(page_html, match.start(), tag)
        if any(start <= match.start() <= end for start, end in spans):
            score += 60
        if match.start() < 16000:
            score += 10
        if alt and title and any(part and part in alt for part in re.split(r"\s+", title)):
            score += 15
        status = "OK" if score >= 25 else "REJECTED_SMALL"
        candidates.append({"url": url, "score": score, "status": status})

    meta_patterns = (
        r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
        r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']',
    )
    for pattern in meta_patterns:
        for match in re.finditer(pattern, page_html, flags=re.IGNORECASE):
            url = urljoin(base_url, html_lib.unescape(match.group(1)).strip())
            reason = reject_reason(url, "")
            candidates.append(
                {"url": url, "score": 20 if not reason else -1000, "status": reason or "OK"}
            )

    for url in _json_ld_images(page_html, base_url):
        reason = reject_reason(url, "")
        candidates.append(
            {"url": url, "score": 35 if not reason else -1000, "status": reason or "OK"}
        )

    deduped: dict[str, dict] = {}
    for candidate in candidates:
        existing = deduped.get(candidate["url"])
        if not existing or candidate["score"] > existing["score"]:
            deduped[candidate["url"]] = candidate
    return sorted(deduped.values(), key=lambda item: item["score"], reverse=True)
