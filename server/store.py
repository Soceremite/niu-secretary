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

        CREATE TABLE IF NOT EXISTS user_profiles (
            module TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profile_changes (
            id TEXT PRIMARY KEY,
            module TEXT NOT NULL,
            field TEXT NOT NULL,
            old_value TEXT NOT NULL DEFAULT '',
            new_value TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_profile_changes_module
        ON profile_changes(module);
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


def list_nutrition_logs(date_from: str = "", date_to: str = "", limit: int = 500) -> list[dict]:
    """List nutrition logs, optionally filtered by an inclusive date range."""
    clauses = []
    params: list = []
    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, food, date, calories, protein_g, carbs_g, fat_g, source, created_at
            FROM fitness_nutrition_logs
            {where}
            ORDER BY date DESC, created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
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


def delete_nutrition_log(record_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM fitness_nutrition_logs WHERE id = ?", (record_id,)
        )
        return cursor.rowcount > 0


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


def list_schedule_events(date_from: str = "", date_to: str = "", limit: int = 500) -> list[dict]:
    """List schedule events, optionally filtered by an inclusive date range."""
    clauses = []
    params: list = []
    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, title, date, time, note, source, created_at
            FROM schedule_events
            {where}
            ORDER BY date, time, created_at
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_event_to_dict(row) for row in rows]


def _event_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "date": row["date"],
        "time": row["time"],
        "note": row["note"],
        "source": row["source"],
        "createdAt": row["created_at"],
    }


def delete_schedule_event(record_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM schedule_events WHERE id = ?", (record_id,)
        )
        return cursor.rowcount > 0


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


def list_schedule_todos(date_from: str = "", date_to: str = "", include_done: bool = True, limit: int = 500) -> list[dict]:
    """List todos. Undated todos (date='') are always included."""
    clauses = []
    params: list = []
    if date_from or date_to:
        range_clauses = ["date = ''"]
        sub = []
        if date_from:
            sub.append("date >= ?")
            params.append(date_from)
        if date_to:
            sub.append("date <= ?")
            params.append(date_to)
        range_clauses.append("(" + " AND ".join(sub) + ")")
        clauses.append("(" + " OR ".join(range_clauses) + ")")
    if not include_done:
        clauses.append("done = 0")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, title, date, priority, done, source, created_at
            FROM schedule_todos
            {where}
            ORDER BY done, priority DESC, created_at
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_todo_to_dict(row) for row in rows]


def _todo_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "date": row["date"],
        "priority": row["priority"],
        "done": bool(row["done"]),
        "source": row["source"],
        "createdAt": row["created_at"],
    }


def set_schedule_todo_done(record_id: str, done: bool) -> dict | None:
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE schedule_todos SET done = ?, updated_at = ? WHERE id = ?",
            (1 if done else 0, now_iso(), record_id),
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT id, title, date, priority, done, source, created_at FROM schedule_todos WHERE id = ?",
            (record_id,),
        ).fetchone()
    return _todo_to_dict(row) if row else None


def delete_schedule_todo(record_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM schedule_todos WHERE id = ?", (record_id,)
        )
        return cursor.rowcount > 0


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


# ================================================================
# User profiles (用户画像)
# ================================================================

PROFILE_MODULES = ("fitness", "schedule", "news", "leisure")

DEFAULT_PROFILES: dict[str, dict] = {
    "fitness": {
        "goal": "maintain",
        "dietStyle": "",
        "restrictions": [],
        "trainingLevel": "beginner",
        "targetCalories": 0,
        "proteinTarget": 0,
        "notes": "",
    },
    "schedule": {
        "workHours": "",
        "focusBlocks": [],
        "reminderStyle": "",
        "priorities": [],
        "notes": "",
    },
    "news": {
        "topics": [],
        "excludeTopics": [],
        "depth": "brief",
        "regions": [],
        "notes": "",
    },
    "leisure": {
        "genres": {"movie": [], "music": [], "podcast": [], "novel": []},
        "moods": [],
        "avoid": [],
        "notes": "",
    },
}


def default_profile(module: str) -> dict:
    """Return a deep copy of the default profile for a module."""
    return json.loads(json.dumps(DEFAULT_PROFILES.get(module, {})))


def get_profile(module: str) -> dict:
    """Read a module profile, returning the default if none is stored yet."""
    with connect() as connection:
        row = connection.execute(
            "SELECT module, profile_json, updated_at FROM user_profiles WHERE module = ?",
            (module,),
        ).fetchone()
    if row is None:
        return {"module": module, "profile": default_profile(module), "updatedAt": ""}
    stored = json.loads(row["profile_json"])
    # Merge over defaults so newly added fields always appear.
    merged = default_profile(module)
    merged.update(stored)
    return {"module": module, "profile": merged, "updatedAt": row["updated_at"]}


def get_all_profiles() -> dict:
    """Return profiles for every known module."""
    return {module: get_profile(module)["profile"] for module in PROFILE_MODULES}


def _save_profile(connection, module: str, profile: dict, updated_at: str) -> None:
    connection.execute(
        """
        INSERT INTO user_profiles (module, profile_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(module) DO UPDATE SET
            profile_json = excluded.profile_json,
            updated_at = excluded.updated_at
        """,
        (module, json.dumps(profile, ensure_ascii=False), updated_at),
    )


def update_profile(module: str, patch: dict, summary: str = "", source: str = "action") -> dict:
    """Shallow-merge patch into the module profile and record field-level changes."""
    current = get_profile(module)["profile"]
    updated_at = now_iso()
    changed_fields = []
    with connect() as connection:
        for field, new_value in (patch or {}).items():
            old_value = current.get(field)
            if old_value == new_value:
                continue
            current[field] = new_value
            changed_fields.append(field)
            connection.execute(
                """
                INSERT INTO profile_changes
                (id, module, field, old_value, new_value, summary, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("pch"),
                    module,
                    field,
                    json.dumps(old_value, ensure_ascii=False),
                    json.dumps(new_value, ensure_ascii=False),
                    summary,
                    source,
                    updated_at,
                ),
            )
        _save_profile(connection, module, current, updated_at)
    return {
        "module": module,
        "profile": current,
        "changedFields": changed_fields,
        "updatedAt": updated_at,
    }


def reset_profile(module: str, source: str = "action") -> dict:
    """Reset a module profile back to its default."""
    updated_at = now_iso()
    profile = default_profile(module)
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO profile_changes
            (id, module, field, old_value, new_value, summary, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("pch"),
                module,
                "*",
                "",
                "reset",
                "重置为默认画像",
                source,
                updated_at,
            ),
        )
        _save_profile(connection, module, profile, updated_at)
    return {"module": module, "profile": profile, "updatedAt": updated_at}


def list_profile_changes(module: str = "", limit: int = 50) -> list[dict]:
    """Return profile change history, newest first."""
    clause = "WHERE module = ?" if module else ""
    params: list = [module] if module else []
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, module, field, old_value, new_value, summary, source, created_at
            FROM profile_changes
            {clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "module": row["module"],
                "field": row["field"],
                "oldValue": _safe_json_load(row["old_value"]),
                "newValue": _safe_json_load(row["new_value"]),
                "summary": row["summary"],
                "source": row["source"],
                "createdAt": row["created_at"],
            }
        )
    return result


def _safe_json_load(raw: str):
    if raw is None or raw == "":
        return ""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw
