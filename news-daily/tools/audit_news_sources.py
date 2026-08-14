#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import socket
import subprocess
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from news_parser import parse_sections_dir


DIST = Path("/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist")


GENERIC_PATH_PATTERNS = (
    "/list",
    "/lists",
    "/index.",
    "/index/",
    "/category",
    "/channels/",
)

HIGH_RISK_TERMS = (
    "首相",
    "总统",
    "遇难",
    "死亡",
    "强震",
    "地震",
    "交火",
    "战争",
    "GPT-",
    "GPT",
    "OpenAI",
    "Claude",
    "Anthropic",
)

EVENT_GROUP_RULES = (
    ("rocket-recovery", ("火箭", "回收")),
    ("hormuz-us-iran", ("美伊", "海峡")),
    ("hormuz-us-iran", ("霍尔木兹",)),
)


class PageTitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.parts.append(data)

    @property
    def title(self) -> str:
        return html.unescape(re.sub(r"\s+", " ", " ".join(self.parts))).strip()


def is_generic_source_url(url: str) -> bool:
    parsed = urlparse((url or "").strip().lower())
    path = parsed.path or "/"
    if path in {"", "/"}:
        return True
    return any(pattern in path for pattern in GENERIC_PATH_PATTERNS)


def _title_terms(value: str) -> set[str]:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", value.lower())
    terms = {part for part in normalized.split() if len(part) >= 2}
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", value)
    for chunk in chinese:
        terms.update(chunk[index : index + 2] for index in range(max(0, len(chunk) - 1)))
    return terms


def source_title_matches(item_title: str, source_title: str) -> bool:
    item_terms = _title_terms(item_title)
    source_terms = _title_terms(source_title)
    if not item_terms or not source_terms:
        return True
    overlap = item_terms & source_terms
    return len(overlap) >= 2 or len(overlap) >= max(1, min(len(item_terms), len(source_terms)) // 4)


def is_high_risk_item(item: dict) -> bool:
    text = " ".join(str(item.get(key) or "") for key in ("title", "summary", "section", "sectionName"))
    return any(term.lower() in text.lower() for term in HIGH_RISK_TERMS)


def event_group_key(item: dict) -> str | None:
    text = " ".join(str(item.get(key) or "") for key in ("title", "summary"))
    for key, required_terms in EVENT_GROUP_RULES:
        if all(term in text for term in required_terms):
            return key
    return None


def fetch_page_title(url: str, timeout: int = 12) -> tuple[int | str, str]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 NiuSecretaryAudit/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(180_000)
            parser = PageTitleParser()
            parser.feed(raw.decode("utf-8", "ignore"))
            return response.status, parser.title
    except HTTPError as error:
        return _fetch_page_title_with_curl(url, timeout) or (error.code, "")
    except (OSError, URLError, socket.timeout, TimeoutError) as error:
        return _fetch_page_title_with_curl(url, timeout) or ("ERR", f"{type(error).__name__}: {error}")


def _fetch_page_title_with_curl(url: str, timeout: int) -> tuple[int | str, str] | None:
    try:
        result = subprocess.run(
            [
                "curl",
                "-L",
                "--max-time",
                str(timeout),
                "-A",
                "Mozilla/5.0 NiuSecretaryAudit/1.0",
                "-s",
                "-w",
                "\n%{http_code}",
                url,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout + 2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0 or "\n" not in result.stdout:
        return None
    body, status_text = result.stdout.rsplit("\n", 1)
    try:
        status: int | str = int(status_text.strip())
    except ValueError:
        status = "ERR"
    parser = PageTitleParser()
    parser.feed(body[:180_000])
    return status, parser.title


def collect_source_issues(
    items: list[dict],
    *,
    source_titles: dict[str, str] | None = None,
    status_by_url: dict[str, int | str] | None = None,
    max_reuse: int = 1,
    require_verified_high_risk: bool = True,
    max_event_reuse: int = 2,
) -> list[str]:
    issues: list[str] = []
    source_titles = source_titles or {}
    status_by_url = status_by_url or {}
    counts = Counter(item.get("sourceUrl", "") for item in items if item.get("sourceUrl"))
    event_counts = Counter(key for item in items if (key := event_group_key(item)))

    for item in items:
        ident = item.get("id") or "<missing-id>"
        title = item.get("title") or ""
        url = item.get("sourceUrl") or ""
        if not url:
            continue

        if is_generic_source_url(url):
            issues.append(f"{ident}: sourceUrl looks like a list/index page: {url}")

        if counts[url] > max_reuse:
            issues.append(f"{ident}: sourceUrl reused by {counts[url]} items: {url}")

        status = status_by_url.get(url)
        if status and (not isinstance(status, int) or status >= 400):
            issues.append(f"{ident}: sourceUrl fetch failed with {status}: {url}")

        source_title = source_titles.get(url, "")
        if source_title and not source_title.startswith("ERR") and not source_title_matches(title, source_title):
            issues.append(
                f"{ident}: item title does not match source page title: {title} <> {source_title}"
            )

        if require_verified_high_risk and is_high_risk_item(item) and not source_title:
            issues.append(f"{ident}: high-risk item requires live source title verification: {title}")

        group_key = event_group_key(item)
        if group_key and event_counts[group_key] > max_event_reuse:
            issues.append(
                f"{ident}: event group {group_key} appears {event_counts[group_key]} times; reduce cross-section repetition"
            )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit generated news source URLs before publishing.")
    parser.add_argument("--dist", type=Path, default=DIST)
    parser.add_argument("--no-network", action="store_true", help="Skip live HTTP title/status checks.")
    args = parser.parse_args()

    items = parse_sections_dir(args.dist / "sections")
    source_titles: dict[str, str] = {}
    status_by_url: dict[str, int | str] = {}

    if not args.no_network:
        for url in sorted({item.get("sourceUrl", "") for item in items if item.get("sourceUrl")}):
            status, title = fetch_page_title(url)
            status_by_url[url] = status
            source_titles[url] = title

    issues = collect_source_issues(items, source_titles=source_titles, status_by_url=status_by_url)

    if issues:
        print("News source audit failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print(f"News source audit passed: {len(items)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
