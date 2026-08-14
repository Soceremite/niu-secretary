from __future__ import annotations

from urllib.parse import urlparse


SEARCH_HOSTS = {
    "www.baidu.com",
    "baidu.com",
    "cn.bing.com",
    "www.bing.com",
    "bing.com",
    "www.google.com",
    "google.com",
    "www.sogou.com",
    "sogou.com",
}

KNOWN_IMAGE_STATUSES = {
    "",
    "OK",
    "NO_IMAGE",
    "FETCH_FAILED",
    "REJECTED_LOGO",
    "REJECTED_QRCODE",
    "REJECTED_SMALL",
    "REJECTED_FORMAT",
    "REJECTED_AD",
    "REJECTED_PLACEHOLDER",
}


def is_rejected_source_url(url: str) -> bool:
    value = (url or "").strip().lower()
    if not value or value == "#" or value.startswith("javascript:"):
        return True
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return True
    host = parsed.netloc.split("@")[-1]
    if host in SEARCH_HOSTS:
        return True
    if parsed.path in {"", "/"} and not parsed.query:
        return True
    if "search" in parsed.path and parsed.query:
        return True
    return False


def validate_items(items: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for item in items:
        ident = item.get("id") or "<missing-id>"
        if ident in seen:
            errors.append(f"{ident}: duplicate id")
        seen.add(ident)

        if not item.get("title"):
            errors.append(f"{ident}: missing title")
        if not item.get("summary"):
            errors.append(f"{ident}: missing summary")

        source_url = item.get("sourceUrl", "")
        if not source_url:
            errors.append(f"{ident}: missing sourceUrl")
        elif is_rejected_source_url(source_url):
            errors.append(f"{ident}: rejected sourceUrl {source_url}")

        detail = item.get("detailHtml", "")
        if "<h2" not in detail:
            errors.append(f"{ident}: missing detail h2")
        if "detail-meta" not in detail:
            errors.append(f"{ident}: missing detail-meta")
        if "<p" not in detail:
            errors.append(f"{ident}: missing body paragraph")
        if "external-btn" not in detail:
            errors.append(f"{ident}: missing external-btn")
        if "detail-keypoints" not in detail:
            errors.append(f"{ident}: missing detail-keypoints")
        keypoint_count = detail.count("keypoint-card")
        if keypoint_count < 2:
            errors.append(f"{ident}: expected at least 2 keypoint-card entries, got {keypoint_count}")

        image_status = item.get("imageStatus", "")
        if image_status not in KNOWN_IMAGE_STATUSES:
            errors.append(f"{ident}: unknown imageStatus {image_status}")

    return errors
