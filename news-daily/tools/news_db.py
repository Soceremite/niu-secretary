#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path("/home/ubuntu/.openclaw/workspace/niu-secretary/news-daily")
DB_PATH = ROOT / "news_daily.db"
CANDIDATE_RESULTS = Path("/tmp/img_crawl_results.txt")
KEEP_DAYS = 15


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS news_days (
  date TEXT PRIMARY KEY,
  generated_at TEXT NOT NULL,
  item_count INTEGER NOT NULL,
  validation TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_items (
  date TEXT NOT NULL,
  item_id TEXT NOT NULL,
  open_id TEXT NOT NULL,
  item_order INTEGER NOT NULL,
  section TEXT NOT NULL,
  section_name TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  date_text TEXT NOT NULL,
  detail_html TEXT NOT NULL,
  image_path TEXT NOT NULL,
  PRIMARY KEY (date, item_id),
  FOREIGN KEY (date) REFERENCES news_days(date) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_news_items_date_order
ON news_items(date, item_order);

CREATE INDEX IF NOT EXISTS idx_news_items_section_date
ON news_items(section, date);

CREATE INDEX IF NOT EXISTS idx_news_items_title
ON news_items(title);

CREATE TABLE IF NOT EXISTS news_tags (
  date TEXT NOT NULL,
  item_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  PRIMARY KEY (date, item_id, tag),
  FOREIGN KEY (date, item_id) REFERENCES news_items(date, item_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS image_candidates (
  date TEXT NOT NULL,
  item_id TEXT NOT NULL,
  candidate_url TEXT NOT NULL,
  score INTEGER NOT NULL,
  status TEXT NOT NULL,
  local_path TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (date, item_id, candidate_url),
  FOREIGN KEY (date, item_id) REFERENCES news_items(date, item_id) ON DELETE CASCADE
);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def prune_old_days(conn: sqlite3.Connection, keep_days: int = KEEP_DAYS) -> None:
    dates = [
        row["date"]
        for row in conn.execute(
            "SELECT date FROM news_days ORDER BY date DESC"
        ).fetchall()
    ]
    for old_date in dates[keep_days:]:
        conn.execute("DELETE FROM news_days WHERE date = ?", (old_date,))


def load_image_candidates(path: Path = CANDIDATE_RESULTS) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}

    candidates: dict[str, list[dict[str, Any]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        open_id = parts[0].strip().replace("detail-", "", 1) if parts else ""
        status = parts[1].strip() if len(parts) > 1 else ""
        local_path = parts[2].strip() if len(parts) > 2 else ""
        candidate_url = parts[3].strip() if len(parts) > 3 else ""
        try:
            score = int(parts[4]) if len(parts) > 4 and parts[4].strip() else 0
        except ValueError:
            score = 0
        if open_id:
            candidates.setdefault(open_id, []).append(
                {
                    "status": status,
                    "local_path": local_path,
                    "candidate_url": candidate_url,
                    "score": score,
                }
            )
    return candidates


def archive_payload(
    payload: dict[str, Any],
    manifest: dict[str, Any],
    db_path: Path = DB_PATH,
) -> Path:
    date = str(manifest["date"])
    items = payload.get("items") or []
    image_candidates = load_image_candidates()

    with connect(db_path) as conn:
        init_db(conn)
        conn.execute(
            """
            INSERT INTO news_days(date, generated_at, item_count, validation, payload_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
              generated_at = excluded.generated_at,
              item_count = excluded.item_count,
              validation = excluded.validation,
              payload_json = excluded.payload_json
            """,
            (
                date,
                str(manifest["generatedAt"]),
                int(manifest["itemCount"]),
                str(manifest["validation"]),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.execute("DELETE FROM news_items WHERE date = ?", (date,))

        for index, item in enumerate(items):
            item_id = str(item.get("id") or "")
            conn.execute(
                """
                INSERT INTO news_items(
                  date, item_id, open_id, item_order, section, section_name,
                  title, summary, source_name, source_url, date_text,
                  detail_html, image_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date,
                    item_id,
                    str(item.get("openId") or ""),
                    index,
                    str(item.get("section") or ""),
                    str(item.get("sectionName") or ""),
                    str(item.get("title") or ""),
                    str(item.get("summary") or ""),
                    str(item.get("sourceName") or ""),
                    str(item.get("sourceUrl") or ""),
                    str(item.get("dateText") or ""),
                    str(item.get("detailHtml") or ""),
                    str(item.get("imagePath") or ""),
                ),
            )
            for tag in item.get("tags") or []:
                conn.execute(
                    "INSERT OR IGNORE INTO news_tags(date, item_id, tag) VALUES (?, ?, ?)",
                    (date, item_id, str(tag)),
                )
            for candidate in image_candidates.get(str(item.get("openId") or ""), []):
                candidate_url = str(candidate.get("candidate_url") or "")
                if not candidate_url:
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO image_candidates(
                      date, item_id, candidate_url, score, status, local_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        date,
                        item_id,
                        candidate_url,
                        int(candidate.get("score") or 0),
                        str(candidate.get("status") or ""),
                        str(candidate.get("local_path") or ""),
                    ),
                )

        prune_old_days(conn)

    return db_path


def main() -> int:
    archive_dir = ROOT / "archive"
    dates = sorted(path.name for path in archive_dir.glob("????-??-??") if path.is_dir())
    if not dates:
        print(f"No archive dates found under {archive_dir}")
        return 1

    latest = archive_dir / dates[-1]
    payload = json.loads((latest / "news.json").read_text(encoding="utf-8"))
    manifest = json.loads((latest / "manifest.json").read_text(encoding="utf-8"))
    path = archive_payload(payload, manifest)
    print(f"Archived {manifest['itemCount']} items into {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
