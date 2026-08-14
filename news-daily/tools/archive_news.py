#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from extract_news_json import build_news_json
from news_daily_validate import validate_items
from news_db import archive_payload


ROOT = Path("/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily")
DIST = ROOT / "dist"
ARCHIVE = ROOT / "archive"
KEEP_DAYS = 15


def prune_archives() -> None:
    if not ARCHIVE.exists():
        return
    dated = [
        path
        for path in ARCHIVE.iterdir()
        if path.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.name)
    ]
    for path in sorted(dated, key=lambda p: p.name, reverse=True)[KEEP_DAYS:]:
        shutil.rmtree(path)
        print(f"Pruned {path}")


def copytree_replace(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    if source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)


def main() -> int:
    payload = build_news_json(DIST)
    errors = validate_items(payload["items"])
    if errors:
        print("Archive blocked because validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    target = ARCHIVE / today
    target.mkdir(parents=True, exist_ok=True)

    (target / "news.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copytree_replace(DIST / "sections", target / "sections")
    copytree_replace(DIST / "assets" / "images", target / "assets" / "images")

    manifest = {
        "date": today,
        "generatedAt": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "itemCount": len(payload["items"]),
        "validation": "passed",
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    db_path = archive_payload(payload, manifest)
    prune_archives()
    print(f"Archived {len(payload['items'])} items to {target}")
    print(f"Archived SQLite copy to {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
