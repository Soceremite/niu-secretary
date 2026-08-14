#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_news_sources import collect_source_issues, fetch_page_title
from extract_news_json import build_news_json
from news_daily_validate import validate_items


DIST = Path("/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist")


def validate_payload(
    payload: dict,
    *,
    strict_sources: bool = False,
    source_titles: dict[str, str] | None = None,
    status_by_url: dict[str, int | str] | None = None,
) -> list[str]:
    errors = validate_items(payload["items"])

    count = len(payload["items"])
    if count < 15:
        errors.append(f"expected at least 15 items, got {count}")
    if count > 32:
        errors.append(f"expected at most 32 items, got {count}")

    if strict_sources:
        errors.extend(
            collect_source_issues(
                payload["items"],
                source_titles=source_titles,
                status_by_url=status_by_url,
            )
        )

    return errors


def _fetch_source_titles(payload: dict) -> tuple[dict[str, str], dict[str, int | str]]:
    source_titles: dict[str, str] = {}
    status_by_url: dict[str, int | str] = {}
    urls = sorted({item.get("sourceUrl", "") for item in payload["items"] if item.get("sourceUrl")})
    for url in urls:
        status, title = fetch_page_title(url)
        status_by_url[url] = status
        source_titles[url] = title
    return source_titles, status_by_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated news JSON and section HTML.")
    parser.add_argument("--strict-sources", action="store_true", help="Reject reused or generic source URLs.")
    parser.add_argument(
        "--strict-sources-network",
        action="store_true",
        help="Also fetch source page titles and reject weak title matches.",
    )
    args = parser.parse_args()

    payload = build_news_json(DIST)
    source_titles: dict[str, str] | None = None
    status_by_url: dict[str, int | str] | None = None
    if args.strict_sources_network:
        args.strict_sources = True
        source_titles, status_by_url = _fetch_source_titles(payload)

    errors = validate_payload(
        payload,
        strict_sources=args.strict_sources,
        source_titles=source_titles,
        status_by_url=status_by_url,
    )

    out = DIST / "news.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if errors:
        print("News validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"News validation passed: {len(payload['items'])} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
