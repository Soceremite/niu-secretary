"""SQLite storage for the Niu Secretary Action Protocol."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_INITIALIZED_DATABASES: set[str] = set()
_INITIALIZE_LOCK = threading.Lock()


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
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    path_key = str(path.resolve())
    if path_key not in _INITIALIZED_DATABASES:
        with _INITIALIZE_LOCK:
            if path_key not in _INITIALIZED_DATABASES:
                initialize(connection)
                _INITIALIZED_DATABASES.add(path_key)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
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

        CREATE TABLE IF NOT EXISTS module_runs (
            id TEXT PRIMARY KEY,
            module TEXT NOT NULL,
            run_type TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL DEFAULT '',
            input_json TEXT NOT NULL DEFAULT '{}',
            output_json TEXT NOT NULL DEFAULT '{}',
            error TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_module_runs_module_started
        ON module_runs(module, started_at);

        CREATE INDEX IF NOT EXISTS idx_module_runs_status
        ON module_runs(status);

        CREATE TABLE IF NOT EXISTS module_events (
            id TEXT PRIMARY KEY,
            module TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            occurred_at TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            requires_review INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_module_events_module_time
        ON module_events(module, occurred_at);

        CREATE INDEX IF NOT EXISTS idx_module_events_type_time
        ON module_events(event_type, occurred_at);

        CREATE INDEX IF NOT EXISTS idx_module_events_review_queue
        ON module_events(module, event_type, requires_review, occurred_at);

        CREATE TABLE IF NOT EXISTS assistant_actions (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            input_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL,
            requires_confirmation INTEGER NOT NULL DEFAULT 0,
            confirmed_at TEXT NOT NULL DEFAULT '',
            executed_at TEXT NOT NULL DEFAULT '',
            result_json TEXT NOT NULL DEFAULT '{}',
            error TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'api',
            request_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_assistant_actions_action_created
        ON assistant_actions(action, created_at);

        CREATE TABLE IF NOT EXISTS model_calls (
            id TEXT PRIMARY KEY,
            module TEXT NOT NULL,
            purpose TEXT NOT NULL,
            model TEXT NOT NULL,
            input_summary TEXT NOT NULL DEFAULT '',
            output_summary TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            latency_ms INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_model_calls_module_created
        ON model_calls(module, created_at);

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

        CREATE TABLE IF NOT EXISTS fitness_workout_logs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            duration_min INTEGER NOT NULL DEFAULT 0,
            intensity TEXT NOT NULL DEFAULT 'medium',
            calories INTEGER NOT NULL DEFAULT 0,
            note TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fitness_workout_date
        ON fitness_workout_logs(date);

        CREATE TABLE IF NOT EXISTS fitness_body_metrics (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            weight_kg REAL,
            body_fat_pct REAL,
            waist_cm REAL,
            note TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fitness_body_metrics_date
        ON fitness_body_metrics(date);

        CREATE TABLE IF NOT EXISTS fitness_recovery_logs (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            sleep_hours REAL NOT NULL DEFAULT 0,
            sleep_quality INTEGER NOT NULL DEFAULT 0,
            stress INTEGER NOT NULL DEFAULT 0,
            soreness INTEGER NOT NULL DEFAULT 0,
            last_rpe REAL NOT NULL DEFAULT 0,
            score INTEGER NOT NULL DEFAULT 0,
            status_label TEXT NOT NULL DEFAULT '',
            status_advice TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fitness_recovery_logs_date
        ON fitness_recovery_logs(date);

        CREATE TABLE IF NOT EXISTS fitness_assessment_logs (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            goal TEXT NOT NULL DEFAULT '',
            weight_kg REAL,
            waist_cm REAL,
            bmi REAL,
            fms_total INTEGER NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fitness_assessment_logs_date
        ON fitness_assessment_logs(date);

        CREATE TABLE IF NOT EXISTS fitness_consult_logs (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            area TEXT NOT NULL DEFAULT '',
            text TEXT NOT NULL DEFAULT '',
            level TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fitness_consult_logs_date
        ON fitness_consult_logs(date);

        CREATE TABLE IF NOT EXISTS fitness_daily_summaries (
            date TEXT PRIMARY KEY,
            summary_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fitness_food_candidates (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            meal TEXT NOT NULL DEFAULT '',
            calories INTEGER NOT NULL DEFAULT 0,
            protein_g INTEGER NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fitness_food_candidates_date
        ON fitness_food_candidates(date);

        CREATE TABLE IF NOT EXISTS fitness_recommendations (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            recommendation_type TEXT NOT NULL,
            recommendations_json TEXT NOT NULL DEFAULT '[]',
            context_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fitness_recommendations_date_type
        ON fitness_recommendations(date, recommendation_type, created_at);

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

        CREATE TABLE IF NOT EXISTS schedule_important_dates (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_schedule_important_dates_date
        ON schedule_important_dates(date);

        CREATE TABLE IF NOT EXISTS schedule_goals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            cadence TEXT NOT NULL DEFAULT 'weekly',
            streak INTEGER NOT NULL DEFAULT 0,
            note TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_schedule_goals_created
        ON schedule_goals(created_at);

        CREATE TABLE IF NOT EXISTS schedule_day_plans (
            date TEXT PRIMARY KEY,
            plan_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schedule_day_reviews (
            date TEXT PRIMARY KEY,
            review_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schedule_focus_blocks (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL DEFAULT '',
            end_time TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_schedule_focus_blocks_date
        ON schedule_focus_blocks(date);

        CREATE TABLE IF NOT EXISTS schedule_reminders (
            id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL DEFAULT '',
            target_type TEXT NOT NULL DEFAULT '',
            remind_at TEXT NOT NULL,
            title TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_schedule_reminders_time
        ON schedule_reminders(remind_at);

        CREATE TABLE IF NOT EXISTS schedule_task_history (
            id TEXT PRIMARY KEY,
            todo_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_schedule_task_history_todo
        ON schedule_task_history(todo_id, created_at);

        CREATE TABLE IF NOT EXISTS leisure_items (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_leisure_items_category
        ON leisure_items(category, updated_at);

        CREATE TABLE IF NOT EXISTS leisure_interactions (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            interaction TEXT NOT NULL,
            rating INTEGER NOT NULL DEFAULT 0,
            note TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_leisure_interactions_item
        ON leisure_interactions(item_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_leisure_interactions_category
        ON leisure_interactions(category, created_at);

        CREATE TABLE IF NOT EXISTS leisure_sessions (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            item_id TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            minutes INTEGER NOT NULL DEFAULT 0,
            note TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_leisure_sessions_date
        ON leisure_sessions(date);

        CREATE TABLE IF NOT EXISTS leisure_mood_logs (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            mood TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_leisure_mood_logs_date
        ON leisure_mood_logs(date);

        CREATE TABLE IF NOT EXISTS leisure_recommendations (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            recommendations_json TEXT NOT NULL DEFAULT '[]',
            context_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_leisure_recommendations_date
        ON leisure_recommendations(date, created_at);

        CREATE TABLE IF NOT EXISTS leisure_sources (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_path TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );

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
            updated_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'action'
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

        CREATE INDEX IF NOT EXISTS idx_profile_changes_module_created
        ON profile_changes(module, created_at);
        """
    )
    _ensure_column(connection, "user_profiles", "source", "TEXT NOT NULL DEFAULT 'action'")
    connection.commit()


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] if hasattr(row, "keys") else row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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


def get_nutrition_log(record_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, food, date, calories, protein_g, carbs_g, fat_g, source, created_at, updated_at
            FROM fitness_nutrition_logs
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "food": row["food"],
        "date": row["date"],
        "calories": row["calories"],
        "proteinG": row["protein_g"],
        "carbsG": row["carbs_g"],
        "fatG": row["fat_g"],
        "source": row["source"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def update_nutrition_log(record_id: str, patch: dict) -> dict | None:
    before = get_nutrition_log(record_id)
    if not before:
        return None
    updated = {
        "food": patch.get("food", before["food"]),
        "date": patch.get("date", before["date"]),
        "calories": int(patch.get("calories", before["calories"]) or 0),
        "proteinG": int(patch.get("proteinG", before["proteinG"]) or 0),
        "carbsG": int(patch.get("carbsG", before["carbsG"]) or 0),
        "fatG": int(patch.get("fatG", before["fatG"]) or 0),
        "source": patch.get("source", before["source"]),
        "updatedAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            UPDATE fitness_nutrition_logs
            SET food = ?, date = ?, calories = ?, protein_g = ?, carbs_g = ?, fat_g = ?,
                source = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated["food"],
                updated["date"],
                updated["calories"],
                updated["proteinG"],
                updated["carbsG"],
                updated["fatG"],
                updated["source"],
                updated["updatedAt"],
                record_id,
            ),
        )
    return get_nutrition_log(record_id)


def delete_nutrition_log(record_id: str) -> dict | None:
    before = get_nutrition_log(record_id)
    if not before:
        return None
    with connect() as connection:
        connection.execute("DELETE FROM fitness_nutrition_logs WHERE id = ?", (record_id,))
    return before


def insert_workout_log(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("wrk"),
        "name": row["name"],
        "date": row["date"],
        "durationMin": int(row.get("durationMin") or 0),
        "intensity": row.get("intensity") or "medium",
        "calories": int(row.get("calories") or 0),
        "note": row.get("note") or "",
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO fitness_workout_logs
            (id, name, date, duration_min, intensity, calories, note, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["name"],
                record["date"],
                record["durationMin"],
                record["intensity"],
                record["calories"],
                record["note"],
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def list_workout_logs(date_from: str = "", date_to: str = "", limit: int = 500) -> list[dict]:
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
            SELECT id, name, date, duration_min, intensity, calories, note, source, created_at
            FROM fitness_workout_logs
            {where}
            ORDER BY date DESC, created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_workout_to_dict(row) for row in rows]


def _workout_to_dict(row) -> dict:
    item = {
        "id": row["id"],
        "name": row["name"],
        "date": row["date"],
        "durationMin": row["duration_min"],
        "intensity": row["intensity"],
        "calories": row["calories"],
        "note": row["note"],
        "source": row["source"],
        "createdAt": row["created_at"],
    }
    if "updated_at" in row.keys():
        item["updatedAt"] = row["updated_at"]
    return item


def get_workout_log(record_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, name, date, duration_min, intensity, calories, note, source, created_at, updated_at
            FROM fitness_workout_logs
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
    return _workout_to_dict(row) if row else None


def update_workout_log(record_id: str, patch: dict) -> dict | None:
    before = get_workout_log(record_id)
    if not before:
        return None
    updated = {
        "name": patch.get("name", before["name"]),
        "date": patch.get("date", before["date"]),
        "durationMin": int(patch.get("durationMin", before["durationMin"]) or 0),
        "intensity": patch.get("intensity", before["intensity"]),
        "calories": int(patch.get("calories", before["calories"]) or 0),
        "note": patch.get("note", before["note"]),
        "source": patch.get("source", before["source"]),
        "updatedAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            UPDATE fitness_workout_logs
            SET name = ?, date = ?, duration_min = ?, intensity = ?, calories = ?,
                note = ?, source = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated["name"],
                updated["date"],
                updated["durationMin"],
                updated["intensity"],
                updated["calories"],
                updated["note"],
                updated["source"],
                updated["updatedAt"],
                record_id,
            ),
        )
    return get_workout_log(record_id)


def delete_workout_log(record_id: str) -> dict | None:
    before = get_workout_log(record_id)
    if not before:
        return None
    with connect() as connection:
        connection.execute("DELETE FROM fitness_workout_logs WHERE id = ?", (record_id,))
    return before


def insert_body_metric(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("met"),
        "date": row["date"],
        "weightKg": row.get("weightKg"),
        "bodyFatPct": row.get("bodyFatPct"),
        "waistCm": row.get("waistCm"),
        "note": row.get("note") or "",
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO fitness_body_metrics
            (id, date, weight_kg, body_fat_pct, waist_cm, note, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["date"],
                record["weightKg"],
                record["bodyFatPct"],
                record["waistCm"],
                record["note"],
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def list_body_metrics(date_from: str = "", date_to: str = "", limit: int = 500) -> list[dict]:
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
            SELECT id, date, weight_kg, body_fat_pct, waist_cm, note, source, created_at
            FROM fitness_body_metrics
            {where}
            ORDER BY date DESC, created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_body_metric_to_dict(row) for row in rows]


def _body_metric_to_dict(row) -> dict:
    item = {
        "id": row["id"],
        "date": row["date"],
        "weightKg": row["weight_kg"],
        "bodyFatPct": row["body_fat_pct"],
        "waistCm": row["waist_cm"],
        "note": row["note"],
        "source": row["source"],
        "createdAt": row["created_at"],
    }
    if "updated_at" in row.keys():
        item["updatedAt"] = row["updated_at"]
    return item


def get_body_metric(record_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, date, weight_kg, body_fat_pct, waist_cm, note, source, created_at, updated_at
            FROM fitness_body_metrics
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
    return _body_metric_to_dict(row) if row else None


def update_body_metric(record_id: str, patch: dict) -> dict | None:
    before = get_body_metric(record_id)
    if not before:
        return None
    updated = {
        "date": patch.get("date", before["date"]),
        "weightKg": patch.get("weightKg", before["weightKg"]),
        "bodyFatPct": patch.get("bodyFatPct", before["bodyFatPct"]),
        "waistCm": patch.get("waistCm", before["waistCm"]),
        "note": patch.get("note", before["note"]),
        "source": patch.get("source", before["source"]),
        "updatedAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            UPDATE fitness_body_metrics
            SET date = ?, weight_kg = ?, body_fat_pct = ?, waist_cm = ?,
                note = ?, source = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated["date"],
                updated["weightKg"],
                updated["bodyFatPct"],
                updated["waistCm"],
                updated["note"],
                updated["source"],
                updated["updatedAt"],
                record_id,
            ),
        )
    return get_body_metric(record_id)


def delete_body_metric(record_id: str) -> dict | None:
    before = get_body_metric(record_id)
    if not before:
        return None
    with connect() as connection:
        connection.execute("DELETE FROM fitness_body_metrics WHERE id = ?", (record_id,))
    return before


def insert_recovery_log(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("rec"),
        "date": row["date"],
        "sleepHours": float(row.get("sleepHours") or 0),
        "sleepQuality": int(row.get("sleepQuality") or 0),
        "stress": int(row.get("stress") or 0),
        "soreness": int(row.get("soreness") or 0),
        "lastRpe": float(row.get("lastRpe") or 0),
        "score": int(row.get("score") or 0),
        "statusLabel": row.get("statusLabel") or "",
        "statusAdvice": row.get("statusAdvice") or "",
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO fitness_recovery_logs
            (id, date, sleep_hours, sleep_quality, stress, soreness, last_rpe, score,
             status_label, status_advice, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["date"],
                record["sleepHours"],
                record["sleepQuality"],
                record["stress"],
                record["soreness"],
                record["lastRpe"],
                record["score"],
                record["statusLabel"],
                record["statusAdvice"],
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def list_recovery_logs(date_from: str = "", date_to: str = "", limit: int = 500) -> list[dict]:
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
            SELECT id, date, sleep_hours, sleep_quality, stress, soreness, last_rpe, score,
                   status_label, status_advice, source, created_at, updated_at
            FROM fitness_recovery_logs
            {where}
            ORDER BY date DESC, created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_recovery_to_dict(row) for row in rows]


def _recovery_to_dict(row) -> dict:
    item = {
        "id": row["id"],
        "date": row["date"],
        "sleepHours": row["sleep_hours"],
        "sleepQuality": row["sleep_quality"],
        "stress": row["stress"],
        "soreness": row["soreness"],
        "lastRpe": row["last_rpe"],
        "score": row["score"],
        "statusLabel": row["status_label"],
        "statusAdvice": row["status_advice"],
        "source": row["source"],
        "createdAt": row["created_at"],
        "syncStatus": "synced",
    }
    if "updated_at" in row.keys():
        item["updatedAt"] = row["updated_at"]
    return item


def insert_assessment_log(row: dict) -> dict:
    created_at = now_iso()
    payload = row.get("payload") or {}
    record = {
        "id": new_id("asm"),
        "date": row["date"],
        "goal": row.get("goal") or "",
        "weightKg": row.get("weightKg"),
        "waistCm": row.get("waistCm"),
        "bmi": row.get("bmi"),
        "fmsTotal": int(row.get("fmsTotal") or 0),
        "payload": payload,
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO fitness_assessment_logs
            (id, date, goal, weight_kg, waist_cm, bmi, fms_total, payload_json, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["date"],
                record["goal"],
                record["weightKg"],
                record["waistCm"],
                record["bmi"],
                record["fmsTotal"],
                json.dumps(record["payload"], ensure_ascii=False),
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def list_assessment_logs(date_from: str = "", date_to: str = "", limit: int = 500) -> list[dict]:
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
            SELECT id, date, goal, weight_kg, waist_cm, bmi, fms_total, payload_json, source, created_at, updated_at
            FROM fitness_assessment_logs
            {where}
            ORDER BY date DESC, created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_assessment_to_dict(row) for row in rows]


def _assessment_to_dict(row) -> dict:
    payload = _safe_json_load(row["payload_json"]) or {}
    item = {
        **payload,
        "id": row["id"],
        "serverId": row["id"],
        "date": row["date"],
        "goal": row["goal"],
        "weightKg": row["weight_kg"],
        "waistCm": row["waist_cm"],
        "bmi": row["bmi"],
        "fmsTotal": row["fms_total"],
        "source": row["source"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "syncStatus": "synced",
    }
    return item


def insert_consult_log(row: dict) -> dict:
    created_at = now_iso()
    payload = row.get("payload") or {}
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    record = {
        "id": new_id("con"),
        "date": row["date"],
        "area": row.get("area") or "",
        "text": row.get("text") or "",
        "level": row.get("level") or result.get("level") or "",
        "title": row.get("title") or result.get("title") or "",
        "payload": payload,
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO fitness_consult_logs
            (id, date, area, text, level, title, payload_json, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["date"],
                record["area"],
                record["text"],
                record["level"],
                record["title"],
                json.dumps(record["payload"], ensure_ascii=False),
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def list_consult_logs(date_from: str = "", date_to: str = "", limit: int = 500) -> list[dict]:
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
            SELECT id, date, area, text, level, title, payload_json, source, created_at, updated_at
            FROM fitness_consult_logs
            {where}
            ORDER BY date DESC, created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_consult_to_dict(row) for row in rows]


def _consult_to_dict(row) -> dict:
    payload = _safe_json_load(row["payload_json"]) or {}
    item = {
        **payload,
        "id": row["id"],
        "serverId": row["id"],
        "date": row["date"],
        "area": row["area"],
        "text": row["text"],
        "level": row["level"],
        "title": row["title"],
        "source": row["source"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "syncStatus": "synced",
    }
    return item


def save_fitness_daily_summary(date: str, summary: dict, source: str = "action") -> dict:
    timestamp = now_iso()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO fitness_daily_summaries (date, summary_json, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                summary_json = excluded.summary_json,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (date, json.dumps(summary, ensure_ascii=False), source, timestamp, timestamp),
        )
    return {"date": date, "summary": summary, "source": source, "updatedAt": timestamp}


def get_fitness_daily_summary(date: str) -> dict:
    with connect() as connection:
        row = connection.execute(
            "SELECT date, summary_json, source, updated_at FROM fitness_daily_summaries WHERE date = ?",
            (date,),
        ).fetchone()
    if row is None:
        return {"date": date, "summary": {}, "source": "", "updatedAt": ""}
    return {
        "date": row["date"],
        "summary": _safe_json_load(row["summary_json"]) or {},
        "source": row["source"],
        "updatedAt": row["updated_at"],
    }


def record_fitness_recommendation(
    date: str,
    recommendation_type: str,
    recommendations: list,
    context: dict | None = None,
    source: str = "action",
) -> dict:
    record = {
        "id": new_id("fitrec"),
        "date": date,
        "type": recommendation_type,
        "recommendations": recommendations,
        "context": context or {},
        "source": source,
        "createdAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO fitness_recommendations
            (id, date, recommendation_type, recommendations_json, context_json, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                date,
                recommendation_type,
                json.dumps(recommendations, ensure_ascii=False),
                json.dumps(record["context"], ensure_ascii=False),
                source,
                record["createdAt"],
            ),
        )
    return record


def list_fitness_recommendations(date: str = "", recommendation_type: str = "", limit: int = 100) -> list[dict]:
    clauses = []
    params: list = []
    if date:
        clauses.append("date = ?")
        params.append(date)
    if recommendation_type:
        clauses.append("recommendation_type = ?")
        params.append(recommendation_type)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, date, recommendation_type, recommendations_json, context_json, source, created_at
            FROM fitness_recommendations
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "date": row["date"],
            "type": row["recommendation_type"],
            "recommendations": _safe_json_load(row["recommendations_json"]) or [],
            "context": _safe_json_load(row["context_json"]) or {},
            "source": row["source"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


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
    item = {
        "id": row["id"],
        "title": row["title"],
        "date": row["date"],
        "time": row["time"],
        "note": row["note"],
        "source": row["source"],
        "createdAt": row["created_at"],
    }
    if "updated_at" in row.keys():
        item["updatedAt"] = row["updated_at"]
    return item


def get_schedule_event(record_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, title, date, time, note, source, created_at, updated_at
            FROM schedule_events
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
    return _event_to_dict(row) if row else None


def update_schedule_event(record_id: str, patch: dict) -> dict | None:
    before = get_schedule_event(record_id)
    if not before:
        return None
    updated = {
        "title": patch.get("title", before["title"]),
        "date": patch.get("date", before["date"]),
        "time": patch.get("time", before["time"]),
        "note": patch.get("note", before["note"]),
        "source": patch.get("source", before["source"]),
        "updatedAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            UPDATE schedule_events
            SET title = ?, date = ?, time = ?, note = ?, source = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated["title"],
                updated["date"],
                updated["time"],
                updated["note"],
                updated["source"],
                updated["updatedAt"],
                record_id,
            ),
        )
    return get_schedule_event(record_id)


def delete_schedule_event(record_id: str) -> dict | None:
    before = get_schedule_event(record_id)
    if not before:
        return None
    with connect() as connection:
        connection.execute("DELETE FROM schedule_events WHERE id = ?", (record_id,))
    return before


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
    item = {
        "id": row["id"],
        "title": row["title"],
        "date": row["date"],
        "priority": row["priority"],
        "done": bool(row["done"]),
        "source": row["source"],
        "createdAt": row["created_at"],
    }
    if "updated_at" in row.keys():
        item["updatedAt"] = row["updated_at"]
    return item


def get_schedule_todo(record_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, title, date, priority, done, source, created_at, updated_at
            FROM schedule_todos
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()
    return _todo_to_dict(row) if row else None


def update_schedule_todo(record_id: str, patch: dict) -> dict | None:
    before = get_schedule_todo(record_id)
    if not before:
        return None
    updated = {
        "title": patch.get("title", before["title"]),
        "date": patch.get("date", before["date"]),
        "priority": patch.get("priority", before["priority"]),
        "source": patch.get("source", before["source"]),
        "updatedAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            UPDATE schedule_todos
            SET title = ?, date = ?, priority = ?, source = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated["title"],
                updated["date"],
                updated["priority"],
                updated["source"],
                updated["updatedAt"],
                record_id,
            ),
        )
    return get_schedule_todo(record_id)


def set_schedule_todo_done(record_id: str, done: bool) -> dict | None:
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE schedule_todos SET done = ?, updated_at = ? WHERE id = ?",
            (1 if done else 0, now_iso(), record_id),
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT id, title, date, priority, done, source, created_at, updated_at FROM schedule_todos WHERE id = ?",
            (record_id,),
        ).fetchone()
    return _todo_to_dict(row) if row else None


def reschedule_todo(record_id: str, target_date: str) -> dict | None:
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE schedule_todos SET date = ?, updated_at = ? WHERE id = ?",
            (target_date, now_iso(), record_id),
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT id, title, date, priority, done, source, created_at, updated_at FROM schedule_todos WHERE id = ?",
            (record_id,),
        ).fetchone()
    return _todo_to_dict(row) if row else None


def record_schedule_task_history(
    todo_id: str,
    event_type: str,
    title: str,
    payload: dict | None = None,
    source: str = "action",
) -> dict:
    record = {
        "id": new_id("taskhist"),
        "todoId": todo_id,
        "eventType": event_type,
        "title": title,
        "payload": payload or {},
        "source": source,
        "createdAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO schedule_task_history
            (id, todo_id, event_type, title, payload_json, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                todo_id,
                event_type,
                title,
                json.dumps(record["payload"], ensure_ascii=False),
                source,
                record["createdAt"],
            ),
        )
    return record


def list_schedule_task_history(todo_id: str = "", limit: int = 100) -> list[dict]:
    clause = "WHERE todo_id = ?" if todo_id else ""
    params: list = [todo_id] if todo_id else []
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, todo_id, event_type, title, payload_json, source, created_at
            FROM schedule_task_history
            {clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "todoId": row["todo_id"],
            "eventType": row["event_type"],
            "title": row["title"],
            "payload": _safe_json_load(row["payload_json"]) or {},
            "source": row["source"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def delete_schedule_todo(record_id: str) -> dict | None:
    before = get_schedule_todo(record_id)
    if not before:
        return None
    with connect() as connection:
        connection.execute("DELETE FROM schedule_todos WHERE id = ?", (record_id,))
    return before


def insert_schedule_important_date(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("sdate"),
        "title": row["title"],
        "date": row["date"],
        "note": row.get("note") or "",
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO schedule_important_dates
            (id, title, date, note, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["title"],
                record["date"],
                record["note"],
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def list_schedule_important_dates(limit: int = 500) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, date, note, source, created_at, updated_at
            FROM schedule_important_dates
            ORDER BY date, created_at
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "date": row["date"],
            "note": row["note"],
            "source": row["source"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "syncStatus": "synced",
        }
        for row in rows
    ]


def insert_schedule_goal(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("sgoal"),
        "title": row["title"],
        "cadence": row.get("cadence") or "weekly",
        "streak": int(row.get("streak") or 0),
        "note": row.get("note") or "",
        "source": row.get("source") or "action",
        "createdAt": created_at,
        "updatedAt": created_at,
        "syncStatus": "synced",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO schedule_goals
            (id, title, cadence, streak, note, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["title"],
                record["cadence"],
                record["streak"],
                record["note"],
                record["source"],
                record["createdAt"],
                record["updatedAt"],
            ),
        )
    return record


def list_schedule_goals(limit: int = 500) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, cadence, streak, note, source, created_at, updated_at
            FROM schedule_goals
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "cadence": row["cadence"],
            "streak": row["streak"],
            "note": row["note"],
            "source": row["source"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "syncStatus": "synced",
        }
        for row in rows
    ]


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


def save_day_plan(date: str, plan: dict, source: str = "action") -> dict:
    timestamp = now_iso()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO schedule_day_plans (date, plan_json, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                plan_json = excluded.plan_json,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (date, json.dumps(plan, ensure_ascii=False), source, timestamp, timestamp),
        )
    return {"date": date, "plan": plan, "source": source, "updatedAt": timestamp}


def get_day_plan(date: str) -> dict:
    with connect() as connection:
        row = connection.execute(
            "SELECT date, plan_json, source, updated_at FROM schedule_day_plans WHERE date = ?",
            (date,),
        ).fetchone()
    if row is None:
        return {"date": date, "plan": {}, "source": "", "updatedAt": ""}
    return {
        "date": row["date"],
        "plan": _safe_json_load(row["plan_json"]) or {},
        "source": row["source"],
        "updatedAt": row["updated_at"],
    }


def save_day_review(date: str, review: dict, source: str = "action") -> dict:
    timestamp = now_iso()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO schedule_day_reviews (date, review_json, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                review_json = excluded.review_json,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (date, json.dumps(review, ensure_ascii=False), source, timestamp, timestamp),
        )
    return {"date": date, "review": review, "source": source, "updatedAt": timestamp}


def get_day_review(date: str) -> dict:
    with connect() as connection:
        row = connection.execute(
            "SELECT date, review_json, source, updated_at FROM schedule_day_reviews WHERE date = ?",
            (date,),
        ).fetchone()
    if row is None:
        return {"date": date, "review": {}, "source": "", "updatedAt": ""}
    return {
        "date": row["date"],
        "review": _safe_json_load(row["review_json"]) or {},
        "source": row["source"],
        "updatedAt": row["updated_at"],
    }


def record_leisure_interaction(row: dict) -> dict:
    created_at = now_iso()
    record = {
        "id": new_id("lei"),
        "itemId": row["itemId"],
        "category": row["category"],
        "title": row["title"],
        "interaction": row["interaction"],
        "rating": int(row.get("rating") or 0),
        "note": row.get("note") or "",
        "payload": row.get("payload") or {},
        "source": row.get("source") or "action",
        "createdAt": created_at,
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO leisure_interactions
            (id, item_id, category, title, interaction, rating, note, payload_json, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["itemId"],
                record["category"],
                record["title"],
                record["interaction"],
                record["rating"],
                record["note"],
                json.dumps(record["payload"], ensure_ascii=False),
                record["source"],
                record["createdAt"],
            ),
        )
    return record


def list_leisure_interactions(
    category: str = "",
    item_id: str = "",
    query: str = "",
    limit: int = 500,
) -> list[dict]:
    clauses = []
    params: list = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if item_id:
        clauses.append("item_id = ?")
        params.append(item_id)
    if query:
        clauses.append("(title LIKE ? OR note LIKE ? OR payload_json LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, item_id, category, title, interaction, rating, note, payload_json, source, created_at
            FROM leisure_interactions
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "itemId": row["item_id"],
            "category": row["category"],
            "title": row["title"],
            "interaction": row["interaction"],
            "rating": row["rating"],
            "note": row["note"],
            "payload": _safe_json_load(row["payload_json"]) or {},
            "source": row["source"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def upsert_leisure_item(
    item_id: str,
    category: str,
    title: str,
    payload: dict | None = None,
    source: str = "action",
) -> dict:
    timestamp = now_iso()
    record = {
        "id": item_id,
        "category": category,
        "title": title,
        "payload": payload or {},
        "source": source,
        "updatedAt": timestamp,
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO leisure_items (id, category, title, payload_json, source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                category = excluded.category,
                title = excluded.title,
                payload_json = excluded.payload_json,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (
                item_id,
                category,
                title,
                json.dumps(record["payload"], ensure_ascii=False),
                source,
                timestamp,
            ),
        )
    return record


def list_leisure_items(category: str = "", limit: int = 100) -> list[dict]:
    clauses = []
    params: list = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    params.append(int(limit))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, category, title, payload_json, source, updated_at
            FROM leisure_items
            {where_sql}
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
        _leisure_item_to_dict(row)
        for row in rows
    ]


def _leisure_item_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "category": row["category"],
        "title": row["title"],
        "payload": _safe_json_load(row["payload_json"]) or {},
        "source": row["source"],
        "updatedAt": row["updated_at"],
    }


def get_leisure_item(item_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, category, title, payload_json, source, updated_at
            FROM leisure_items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
    return _leisure_item_to_dict(row) if row else None


def update_leisure_item(item_id: str, patch: dict) -> dict | None:
    before = get_leisure_item(item_id)
    if not before:
        return None
    updated = {
        "category": patch.get("category", before["category"]),
        "title": patch.get("title", before["title"]),
        "payload": patch.get("payload", before["payload"]),
        "source": patch.get("source", before["source"]),
        "updatedAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            UPDATE leisure_items
            SET category = ?, title = ?, payload_json = ?, source = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated["category"],
                updated["title"],
                json.dumps(updated["payload"], ensure_ascii=False),
                updated["source"],
                updated["updatedAt"],
                item_id,
            ),
        )
    return get_leisure_item(item_id)


def delete_leisure_item(item_id: str) -> dict | None:
    before = get_leisure_item(item_id)
    if not before:
        return None
    with connect() as connection:
        connection.execute("DELETE FROM leisure_items WHERE id = ?", (item_id,))
    return before


def record_leisure_recommendation(
    date: str,
    recommendations: list,
    context: dict | None = None,
    source: str = "action",
) -> dict:
    record = {
        "id": new_id("leirec"),
        "date": date,
        "recommendations": recommendations,
        "context": context or {},
        "source": source,
        "createdAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO leisure_recommendations
            (id, date, recommendations_json, context_json, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                date,
                json.dumps(recommendations, ensure_ascii=False),
                json.dumps(record["context"], ensure_ascii=False),
                source,
                record["createdAt"],
            ),
        )
    return record


def list_leisure_recommendations(date: str = "", limit: int = 100) -> list[dict]:
    clause = "WHERE date = ?" if date else ""
    params: list = [date] if date else []
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, date, recommendations_json, context_json, source, created_at
            FROM leisure_recommendations
            {clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "date": row["date"],
            "recommendations": _safe_json_load(row["recommendations_json"]) or [],
            "context": _safe_json_load(row["context_json"]) or {},
            "source": row["source"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def start_module_run(
    module: str,
    run_type: str,
    source: str,
    input_payload: dict | None = None,
    status: str = "running",
) -> dict:
    record = {
        "id": new_id("run"),
        "module": module,
        "runType": run_type,
        "source": source,
        "status": status,
        "startedAt": now_iso(),
        "finishedAt": "",
        "input": input_payload or {},
        "output": {},
        "error": "",
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO module_runs
            (id, module, run_type, source, status, started_at, input_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                module,
                run_type,
                source,
                status,
                record["startedAt"],
                json.dumps(record["input"], ensure_ascii=False),
            ),
        )
    return record


def finish_module_run(
    run_id: str,
    status: str,
    output_payload: dict | None = None,
    error: str = "",
) -> dict:
    finished_at = now_iso()
    with connect() as connection:
        connection.execute(
            """
            UPDATE module_runs
            SET status = ?, finished_at = ?, output_json = ?, error = ?
            WHERE id = ?
            """,
            (
                status,
                finished_at,
                json.dumps(output_payload or {}, ensure_ascii=False),
                error,
                run_id,
            ),
        )
        row = connection.execute(
            """
            SELECT id, module, run_type, source, status, started_at, finished_at,
                   input_json, output_json, error
            FROM module_runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
    return _module_run_to_dict(row) if row else {}


def _module_run_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "module": row["module"],
        "runType": row["run_type"],
        "source": row["source"],
        "status": row["status"],
        "startedAt": row["started_at"],
        "finishedAt": row["finished_at"],
        "input": _safe_json_load(row["input_json"]),
        "output": _safe_json_load(row["output_json"]),
        "error": row["error"],
    }


def list_module_runs(module: str = "", limit: int = 50) -> list[dict]:
    clause = "WHERE module = ?" if module else ""
    params: list = [module] if module else []
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, module, run_type, source, status, started_at, finished_at,
                   input_json, output_json, error
            FROM module_runs
            {clause}
            ORDER BY started_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_module_run_to_dict(row) for row in rows]


def list_module_run_summaries(
    module: str = "",
    limit: int = 50,
    source: str = "",
    status: str = "",
    exclude_run_types: tuple[str, ...] = (),
) -> list[dict]:
    clauses = []
    params: list = []
    if module:
        clauses.append("module = ?")
        params.append(module)
    if source:
        clauses.append("source = ?")
        params.append(source)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if exclude_run_types:
        placeholders = ", ".join("?" for _ in exclude_run_types)
        clauses.append(f"run_type NOT IN ({placeholders})")
        params.extend(exclude_run_types)
    clause = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, module, run_type, source, status, started_at, finished_at, error
            FROM module_runs
            {clause}
            ORDER BY started_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "module": row["module"],
            "runType": row["run_type"],
            "source": row["source"],
            "status": row["status"],
            "startedAt": row["started_at"],
            "finishedAt": row["finished_at"],
            "error": row["error"],
        }
        for row in rows
    ]


def count_module_runs_by_status(module: str = "") -> dict[str, int]:
    clause = "WHERE module = ?" if module else ""
    params: list = [module] if module else []
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT status, COUNT(*) AS count
            FROM module_runs
            {clause}
            GROUP BY status
            """,
            tuple(params),
        ).fetchall()
    return {row["status"]: int(row["count"]) for row in rows}


def record_module_event(
    module: str,
    event_type: str,
    title: str,
    payload: dict | None = None,
    source: str = "system",
    confidence: float = 1.0,
    requires_review: bool = False,
) -> dict:
    record = {
        "id": new_id("evtlog"),
        "module": module,
        "eventType": event_type,
        "title": title,
        "payload": payload or {},
        "occurredAt": now_iso(),
        "source": source,
        "confidence": float(confidence),
        "requiresReview": bool(requires_review),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO module_events
            (id, module, event_type, title, payload_json, occurred_at, source, confidence, requires_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                module,
                event_type,
                title,
                json.dumps(record["payload"], ensure_ascii=False),
                record["occurredAt"],
                source,
                record["confidence"],
                1 if requires_review else 0,
            ),
        )
    return record


def _module_event_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "module": row["module"],
        "eventType": row["event_type"],
        "title": row["title"],
        "payload": _safe_json_load(row["payload_json"]),
        "occurredAt": row["occurred_at"],
        "source": row["source"],
        "confidence": row["confidence"],
        "requiresReview": bool(row["requires_review"]),
    }


def get_module_event(event_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, module, event_type, title, payload_json, occurred_at,
                   source, confidence, requires_review
            FROM module_events
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()
    return _module_event_to_dict(row) if row else None


PROFILE_CHANGE_RESOLUTION_EVENTS = ("profile_change_review", "profile_change_revert")
MODULE_REVIEW_RESOLUTION_EVENTS = ("module_review_marked",)


def get_latest_profile_change_review(change_id: str) -> dict | None:
    """Return the newest review/revert event for a profile change, if one exists."""
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, module, event_type, title, payload_json, occurred_at,
                   source, confidence, requires_review
            FROM module_events
            WHERE event_type IN ('profile_change_review', 'profile_change_revert')
            ORDER BY occurred_at DESC, id DESC
            LIMIT 500
            """
        ).fetchall()
    for row in rows:
        event = _module_event_to_dict(row)
        if (event.get("payload") or {}).get("changeId") == change_id:
            return event
    return None


def get_latest_module_review_mark(event_id: str) -> dict | None:
    """Return the newest handling event for a reviewable module event, if one exists."""
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, module, event_type, title, payload_json, occurred_at,
                   source, confidence, requires_review
            FROM module_events
            WHERE event_type = 'module_review_marked'
            ORDER BY occurred_at DESC, id DESC
            LIMIT 500
            """
        ).fetchall()
    for row in rows:
        event = _module_event_to_dict(row)
        if (event.get("payload") or {}).get("eventId") == event_id:
            return event
    return None


def list_module_events(
    module: str = "",
    event_type: str = "",
    limit: int = 50,
    requires_review: bool | None = None,
) -> list[dict]:
    clauses = []
    params: list = []
    if module:
        clauses.append("module = ?")
        params.append(module)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    if requires_review is not None:
        clauses.append("requires_review = ?")
        params.append(1 if requires_review else 0)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, module, event_type, title, payload_json, occurred_at,
                   source, confidence, requires_review
            FROM module_events
            {where}
            ORDER BY occurred_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_module_event_to_dict(row) for row in rows]


def create_assistant_action(
    action: str,
    input_payload: dict | None = None,
    requires_confirmation: bool = False,
    source: str = "api",
    request_id: str = "",
    status: str = "running",
    confirmed: bool = False,
) -> dict:
    record = {
        "id": new_id("aa"),
        "action": action,
        "input": input_payload or {},
        "status": status,
        "requiresConfirmation": bool(requires_confirmation),
        "confirmedAt": now_iso() if (confirmed or not requires_confirmation) else "",
        "executedAt": "",
        "result": {},
        "error": "",
        "source": source,
        "requestId": request_id,
        "createdAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO assistant_actions
            (id, action, input_json, status, requires_confirmation, confirmed_at, source, request_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                action,
                json.dumps(record["input"], ensure_ascii=False),
                status,
                1 if requires_confirmation else 0,
                record["confirmedAt"],
                source,
                request_id,
                record["createdAt"],
            ),
        )
    return record


def finish_assistant_action(
    action_id: str,
    status: str,
    result: dict | None = None,
    error: str = "",
) -> dict:
    executed_at = now_iso()
    with connect() as connection:
        connection.execute(
            """
            UPDATE assistant_actions
            SET status = ?, executed_at = ?, result_json = ?, error = ?
            WHERE id = ?
            """,
            (
                status,
                executed_at,
                json.dumps(result or {}, ensure_ascii=False),
                error,
                action_id,
            ),
        )
        row = connection.execute(
            """
            SELECT id, action, input_json, status, requires_confirmation, confirmed_at,
                   executed_at, result_json, error, source, request_id, created_at
            FROM assistant_actions
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()
    return _assistant_action_to_dict(row) if row else {}


def _assistant_action_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "action": row["action"],
        "input": _safe_json_load(row["input_json"]),
        "status": row["status"],
        "requiresConfirmation": bool(row["requires_confirmation"]),
        "confirmedAt": row["confirmed_at"],
        "executedAt": row["executed_at"],
        "result": _safe_json_load(row["result_json"]),
        "error": row["error"],
        "source": row["source"],
        "requestId": row["request_id"],
        "createdAt": row["created_at"],
    }


def _action_module(action: str) -> str:
    return (action or "").split(".", 1)[0]


def list_assistant_action_summaries(
    module: str = "",
    status: str = "",
    limit: int = 50,
    exclude_actions: tuple[str, ...] = (),
) -> list[dict]:
    clauses = []
    params: list = []
    if module:
        clauses.append("action LIKE ?")
        params.append(f"{module}.%")
    if status:
        clauses.append("status = ?")
        params.append(status)
    if exclude_actions:
        placeholders = ", ".join("?" for _ in exclude_actions)
        clauses.append(f"action NOT IN ({placeholders})")
        params.extend(exclude_actions)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, action, status, requires_confirmation, confirmed_at,
                   executed_at, error, source, request_id, created_at
            FROM assistant_actions
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "action": row["action"],
            "module": _action_module(row["action"]),
            "status": row["status"],
            "requiresConfirmation": bool(row["requires_confirmation"]),
            "confirmedAt": row["confirmed_at"],
            "executedAt": row["executed_at"],
            "error": row["error"],
            "source": row["source"],
            "requestId": row["request_id"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def record_model_call(
    module: str,
    purpose: str,
    model: str,
    input_summary: str,
    output_summary: str,
    status: str,
    latency_ms: int = 0,
) -> dict:
    record = {
        "id": new_id("mdl"),
        "module": module,
        "purpose": purpose,
        "model": model,
        "inputSummary": input_summary,
        "outputSummary": output_summary,
        "status": status,
        "latencyMs": int(latency_ms),
        "createdAt": now_iso(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO model_calls
            (id, module, purpose, model, input_summary, output_summary, status, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                module,
                purpose,
                model,
                input_summary,
                output_summary,
                status,
                record["latencyMs"],
                record["createdAt"],
            ),
        )
    return record


def list_model_call_summaries(module: str = "", status: str = "", limit: int = 50) -> list[dict]:
    clauses = []
    params: list = []
    if module:
        clauses.append("module = ?")
        params.append(module)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, module, purpose, model, input_summary, output_summary,
                   status, latency_ms, created_at
            FROM model_calls
            {where}
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "module": row["module"],
            "purpose": row["purpose"],
            "model": row["model"],
            "inputSummary": row["input_summary"],
            "outputSummary": row["output_summary"],
            "status": row["status"],
            "latencyMs": int(row["latency_ms"]),
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


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

PROFILE_MODULES = ("fitness", "schedule", "news", "leisure", "airesearch")

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
    "airesearch": {
        "topics": [],
        "keywords": [],
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


def _save_profile(connection, module: str, profile: dict, updated_at: str, source: str = "action") -> None:
    connection.execute(
        """
        INSERT INTO user_profiles (module, profile_json, updated_at, source)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(module) DO UPDATE SET
            profile_json = excluded.profile_json,
            updated_at = excluded.updated_at,
            source = excluded.source
        """,
        (module, json.dumps(profile, ensure_ascii=False), updated_at, source),
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
        _save_profile(connection, module, current, updated_at, source)
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
        _save_profile(connection, module, profile, updated_at, source)
    return {"module": module, "profile": profile, "updatedAt": updated_at}


def get_profile_change(change_id: str) -> dict | None:
    """Return one profile change by id."""
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, module, field, old_value, new_value, summary, source, created_at
            FROM profile_changes
            WHERE id = ?
            """,
            (change_id,),
        ).fetchone()
    if not row:
        return None
    result = _profile_change_to_dict(row)
    review = get_latest_profile_change_review(result["id"])
    result["reviewed"] = bool(review)
    result["review"] = _profile_change_review_summary(review)
    result["reverted"] = bool(review and review["eventType"] == "profile_change_revert")
    return result


def _profile_change_review_summary(event: dict | None) -> dict | None:
    if not event:
        return None
    payload = event.get("payload") or {}
    reverted = event["eventType"] == "profile_change_revert"
    return {
        "eventId": event["id"],
        "eventType": event["eventType"],
        "reviewedAt": event["occurredAt"],
        "source": event["source"],
        "note": payload.get("note") or "",
        "reverted": reverted,
        "status": "reverted" if reverted else "reviewed",
    }


def _profile_change_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "module": row["module"],
        "field": row["field"],
        "oldValue": _safe_json_load(row["old_value"]),
        "newValue": _safe_json_load(row["new_value"]),
        "summary": row["summary"],
        "source": row["source"],
        "createdAt": row["created_at"],
    }


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
    result = [_profile_change_to_dict(row) for row in rows]
    reviews = {}
    resolution_limit = min(max(int(limit) * 3, 50), 500)
    for event_type in PROFILE_CHANGE_RESOLUTION_EVENTS:
        for event in list_module_events(module, event_type, resolution_limit):
            change_id = (event.get("payload") or {}).get("changeId")
            existing = reviews.get(change_id)
            if change_id and (
                not existing
                or (event.get("occurredAt") or "", event.get("id") or "")
                > (existing.get("occurredAt") or "", existing.get("id") or "")
            ):
                reviews[change_id] = event
    for item in result:
        review = reviews.get(item["id"])
        item["reviewed"] = bool(review)
        item["review"] = _profile_change_review_summary(review)
        item["reverted"] = bool(review and review["eventType"] == "profile_change_revert")
    return result


def _safe_json_load(raw: str):
    if raw is None or raw == "":
        return ""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw
