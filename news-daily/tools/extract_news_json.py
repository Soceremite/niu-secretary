#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from news_parser import parse_sections_dir


DIST = Path("/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily/dist")


def build_news_json(dist: Path = DIST) -> dict:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    items = parse_sections_dir(dist / "sections")
    return {
        "date": now.date().isoformat(),
        "generatedAt": now.isoformat(timespec="seconds"),
        "version": 1,
        "items": items,
    }


def main() -> int:
    payload = build_news_json()
    out = DIST / "news.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} with {len(payload['items'])} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
