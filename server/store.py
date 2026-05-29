"""SQLite storage for the Niu Secretary Action Protocol."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}"


def database_path() -> Path:
    configured = os.environ.get("NIU_SECRETARY_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return PROJECT_ROOT / "data" / "niu-secretary.sqlite3"


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    initialize(connection)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS action_logs (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            input_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fitness_nutrition_logs (
            id TEXT PRIMARY KEY,
            food TEXT NOT NULL,
            date TEXT NOT NULL,
            calories INTEGER NOT NULL DEFAULT 0,
            protein_g INTEGER NOT NULL DEFAULT 0,
            carbs_g INTEGER NOT NULL DEFAULT 0,
            fat_g INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fitness_nutrition_date
        ON fitness_nutrition_logs(date);

        CREATE TABLE IF NOT EXISTS schedule_events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_schedule_events_date
        ON schedule_events(date);

        CREATE TABLE IF NOT EXISTS schedule_todos (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'normal',
            done INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_schedule_todos_date
        ON schedule_todos(date);

        CREATE TABLE IF NOT EXISTS assistant_messages (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            reply TEXT NOT NULL,
            proposed_actions_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    connection.commit()


def insert_nutrition_log(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("nut"),
        "food": row["food"],
        "date": row["date"],
        "calories": int(row.get("calories") or 0),
        "proteinG": int(row.get("proteinG") or 0),
        "carbsG": int(row.get("carbsG") or 0),
        "fatG": int(row.get("fatG") or 0),
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO fitness_nutrition_logs
            (id, food, date, calories, protein_g, carbs_g, fat_g, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["food"],
                record["date"],
                record["calories"],
                record["proteinG"],
                record["carbsG"],
                record["fatG"],
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def nutrition_summary(date: str) -> dict:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, food, date, calories, protein_g, carbs_g, fat_g, source, created_at
            FROM fitness_nutrition_logs
            WHERE date = ?
            ORDER BY created_at DESC
            """,
            (date,),
        ).fetchall()
    items = [
        {
            "id": row["id"],
            "food": row["food"],
            "date": row["date"],
            "calories": row["calories"],
            "proteinG": row["protein_g"],
            "carbsG": row["carbs_g"],
            "fatG": row["fat_g"],
            "source": row["source"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]
    return {
        "date": date,
        "count": len(items),
        "calories": sum(item["calories"] for item in items),
        "proteinG": sum(item["proteinG"] for item in items),
        "carbsG": sum(item["carbsG"] for item in items),
        "fatG": sum(item["fatG"] for item in items),
        "items": items,
    }


def insert_schedule_event(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("evt"),
        "title": row["title"],
        "date": row["date"],
        "time": row.get("time") or "",
        "note": row.get("note") or "",
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO schedule_events
            (id, title, date, time, note, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["title"],
                record["date"],
                record["time"],
                record["note"],
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def insert_schedule_todo(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("todo"),
        "title": row["title"],
        "date": row.get("date") or "",
        "priority": row.get("priority") or "normal",
        "done": False,
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO schedule_todos
            (id, title, date, priority, done, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["title"],
                record["date"],
                record["priority"],
                1 if record["done"] else 0,
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def schedule_summary(date: str) -> dict:
    with connect() as connection:
        events = connection.execute(
            """
            SELECT id, title, date, time, note, source, created_at
            FROM schedule_events
            WHERE date = ?
            ORDER BY time, created_at
            """,
            (date,),
        ).fetchall()
        todos = connection.execute(
            """
            SELECT id, title, date, priority, done, source, created_at
            FROM schedule_todos
            WHERE date = ? OR date = ''
            ORDER BY done, priority DESC, created_at
            """,
            (date,),
        ).fetchall()
    return {
        "date": date,
        "events": [dict(row) for row in events],
        "todos": [dict(row) for row in todos],
    }


def log_action(action: str, status: str, input_payload: dict, result: dict | None = None, error: str = "") -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO action_logs (id, action, status, input_json, result_json, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("act"),
                action,
                status,
                json.dumps(input_payload or {}, ensure_ascii=False),
                json.dumps(result or {}, ensure_ascii=False),
                error,
                now_iso(),
            ),
        )


def insert_assistant_message(text: str, reply: str, proposed_actions: list[dict]) -> dict:
    record = {
        "id": new_id("msg"),
        "text": text,
        "reply": reply,
        "proposedActions": proposed_actions,
        "createdAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO assistant_messages (id, text, reply, proposed_actions_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                text,
                reply,
                json.dumps(proposed_actions, ensure_ascii=False),
                record["createdAt"],
            ),
        )
    return record
