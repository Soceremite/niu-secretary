"""Unified CLI entrypoint for Niu Secretary modules."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEWS_TOOLS = PROJECT_ROOT / "news-daily" / "tools"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(NEWS_TOOLS) not in sys.path:
    sys.path.insert(0, str(NEWS_TOOLS))

from niu_core import audit, exporters  # noqa: E402
from niu_core.cli import run_command  # noqa: E402
from server import store  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="niu_secretary")
    parser.add_argument("--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="module", required=True)

    platform = subparsers.add_parser("platform")
    platform_sub = platform.add_subparsers(dest="command", required=True)
    _add_simple_command(platform_sub, "health-check", platform_health_check)
    _add_simple_command(platform_sub, "validate", platform_health_check)
    _add_simple_command(platform_sub, "derive", platform_derive)
    _add_simple_command(platform_sub, "export", platform_export)
    _add_simple_command(platform_sub, "publish", platform_publish)
    _add_simple_command(platform_sub, "run-daily", platform_run_daily)
    platform_today = platform_sub.add_parser("today")
    platform_today.add_argument("--date", required=True)
    platform_today.add_argument("--limit", type=int, default=5)
    platform_today.set_defaults(handler=platform_today_context)
    platform_modules = platform_sub.add_parser("modules")
    platform_modules.add_argument("--limit", type=int, default=1)
    platform_modules.set_defaults(handler=platform_modules_status)

    news = subparsers.add_parser("news")
    news_sub = news.add_subparsers(dest="command", required=True)
    _add_simple_command(news_sub, "validate", news_validate)
    _add_simple_command(news_sub, "health-check", news_validate)
    _add_simple_command(news_sub, "ingest", news_archive)
    _add_simple_command(news_sub, "derive", news_validate_keypoints)
    _add_simple_command(news_sub, "export", news_archive)
    _add_simple_command(news_sub, "generate-daily", news_run_daily)
    _add_simple_command(news_sub, "validate-sources", news_validate_sources)
    _add_simple_command(news_sub, "validate-keypoints", news_validate_keypoints)
    _add_simple_command(news_sub, "audit-images", news_audit_images)
    _add_simple_command(news_sub, "extract-json", news_extract_json)
    _add_simple_command(news_sub, "crawl-images", news_crawl_images)
    _add_simple_command(news_sub, "review-images", news_review_images)
    _add_simple_command(news_sub, "update-sections", news_update_sections)
    _add_simple_command(news_sub, "archive", news_archive)
    _add_simple_command(news_sub, "publish", news_publish)
    _add_simple_command(news_sub, "run-daily", news_run_daily)
    search = news_sub.add_parser("search")
    search.add_argument("--q", default="")
    search.add_argument("--date", default="")
    search.add_argument("--from", dest="from_date", default="")
    search.add_argument("--to", dest="to_date", default="")
    search.add_argument("--section", default="")
    search.add_argument("--tag", default="")
    search.add_argument("--source", default="")
    search.add_argument("--limit", type=int, default=20)
    search.set_defaults(handler=news_search)

    fitness = subparsers.add_parser("fitness")
    fitness_sub = fitness.add_subparsers(dest="command", required=True)
    _add_simple_command(fitness_sub, "validate", fitness_validate)
    _add_simple_command(fitness_sub, "health-check", fitness_validate)
    _add_simple_command(fitness_sub, "ingest", fitness_ingest_nutrition)
    _add_simple_command(fitness_sub, "ingest-nutrition", fitness_ingest_nutrition)
    _add_simple_command(fitness_sub, "derive", fitness_derive)
    _add_simple_command(fitness_sub, "export", fitness_export)
    _add_simple_command(fitness_sub, "publish", fitness_publish)
    _add_simple_command(fitness_sub, "run-daily", fitness_run_daily)
    fitness_day = fitness_sub.add_parser("summarize-day")
    fitness_day.add_argument("--date", required=True)
    fitness_day.set_defaults(handler=fitness_summarize_day)
    fitness_week = fitness_sub.add_parser("summarize-week")
    fitness_week.add_argument("--date", required=True)
    fitness_week.set_defaults(handler=fitness_summarize_week)
    fitness_meal = fitness_sub.add_parser("recommend-meal")
    fitness_meal.add_argument("--date", default="")
    fitness_meal.set_defaults(handler=fitness_recommend_meal)
    fitness_workout = fitness_sub.add_parser("recommend-workout")
    fitness_workout.add_argument("--date", default="")
    fitness_workout.set_defaults(handler=fitness_recommend_workout)
    fitness_nutrition_list = fitness_sub.add_parser("list-nutrition")
    fitness_nutrition_list.add_argument("--from", dest="from_date", default="")
    fitness_nutrition_list.add_argument("--to", dest="to_date", default="")
    fitness_nutrition_list.add_argument("--limit", type=int, default=100)
    fitness_nutrition_list.set_defaults(handler=fitness_list_nutrition)
    fitness_workout_list = fitness_sub.add_parser("list-workouts")
    fitness_workout_list.add_argument("--from", dest="from_date", default="")
    fitness_workout_list.add_argument("--to", dest="to_date", default="")
    fitness_workout_list.add_argument("--limit", type=int, default=100)
    fitness_workout_list.set_defaults(handler=fitness_list_workouts)
    fitness_metric_list = fitness_sub.add_parser("list-body-metrics")
    fitness_metric_list.add_argument("--from", dest="from_date", default="")
    fitness_metric_list.add_argument("--to", dest="to_date", default="")
    fitness_metric_list.add_argument("--limit", type=int, default=100)
    fitness_metric_list.set_defaults(handler=fitness_list_body_metrics)
    fitness_daily_summary = fitness_sub.add_parser("daily-summary")
    fitness_daily_summary.add_argument("--date", default="today")
    fitness_daily_summary.set_defaults(handler=fitness_daily_summary_get)
    fitness_recommendation_list = fitness_sub.add_parser("list-recommendations")
    fitness_recommendation_list.add_argument("--date", default="")
    fitness_recommendation_list.add_argument("--type", default="")
    fitness_recommendation_list.add_argument("--limit", type=int, default=100)
    fitness_recommendation_list.set_defaults(handler=fitness_list_recommendations)

    schedule = subparsers.add_parser("schedule")
    schedule_sub = schedule.add_subparsers(dest="command", required=True)
    _add_simple_command(schedule_sub, "validate", schedule_validate)
    _add_simple_command(schedule_sub, "health-check", schedule_validate)
    _add_simple_command(schedule_sub, "ingest", schedule_validate)
    _add_simple_command(schedule_sub, "derive", schedule_derive)
    _add_simple_command(schedule_sub, "export", schedule_export)
    _add_simple_command(schedule_sub, "publish", schedule_publish)
    _add_simple_command(schedule_sub, "run-daily", schedule_run_daily)
    schedule_conflicts = schedule_sub.add_parser("detect-conflicts")
    schedule_conflicts.add_argument("--date", required=True)
    schedule_conflicts.set_defaults(handler=schedule_detect_conflicts)
    schedule_plan = schedule_sub.add_parser("plan-day")
    schedule_plan.add_argument("--date", required=True)
    schedule_plan.set_defaults(handler=schedule_plan_day)
    schedule_review = schedule_sub.add_parser("review-day")
    schedule_review.add_argument("--date", required=True)
    schedule_review.add_argument("--completed", type=int, default=0)
    schedule_review.add_argument("--note", default="")
    schedule_review.set_defaults(handler=schedule_review_day)
    schedule_events = schedule_sub.add_parser("list-events")
    schedule_events.add_argument("--from", dest="from_date", default="")
    schedule_events.add_argument("--to", dest="to_date", default="")
    schedule_events.add_argument("--limit", type=int, default=100)
    schedule_events.set_defaults(handler=schedule_list_events)
    schedule_todos = schedule_sub.add_parser("list-todos")
    schedule_todos.add_argument("--from", dest="from_date", default="")
    schedule_todos.add_argument("--to", dest="to_date", default="")
    schedule_todos.add_argument("--include-done", action=argparse.BooleanOptionalAction, default=True)
    schedule_todos.add_argument("--limit", type=int, default=100)
    schedule_todos.set_defaults(handler=schedule_list_todos)
    schedule_plan_get = schedule_sub.add_parser("day-plan")
    schedule_plan_get.add_argument("--date", default="today")
    schedule_plan_get.set_defaults(handler=schedule_day_plan_get)
    schedule_review_get = schedule_sub.add_parser("day-review")
    schedule_review_get.add_argument("--date", default="today")
    schedule_review_get.set_defaults(handler=schedule_day_review_get)
    schedule_history = schedule_sub.add_parser("task-history")
    schedule_history.add_argument("--todo-id", default="")
    schedule_history.add_argument("--limit", type=int, default=100)
    schedule_history.set_defaults(handler=schedule_task_history)
    _add_simple_command(schedule_sub, "rollover-todos", schedule_rollover_todos)

    leisure = subparsers.add_parser("leisure")
    leisure_sub = leisure.add_subparsers(dest="command", required=True)
    leisure_validate_cmd = leisure_sub.add_parser("validate")
    leisure_validate_cmd.add_argument("--strict-content", action="store_true")
    leisure_validate_cmd.set_defaults(handler=leisure_validate)
    _add_simple_command(leisure_sub, "health-check", leisure_validate)
    _add_simple_command(leisure_sub, "ingest", leisure_refresh_candidates)
    _add_simple_command(leisure_sub, "derive", leisure_derive)
    leisure_history = leisure_sub.add_parser("history-search")
    leisure_history.add_argument("--q", default="")
    leisure_history.add_argument("--category", default="")
    leisure_history.add_argument("--limit", type=int, default=20)
    leisure_history.set_defaults(handler=leisure_history_search)
    leisure_recommend_cmd = leisure_sub.add_parser("recommend")
    leisure_recommend_cmd.add_argument("--limit", type=int, default=3)
    leisure_recommend_cmd.add_argument("--mood", default="")
    leisure_recommend_cmd.add_argument("--minutes", type=int, default=0)
    leisure_recommend_cmd.set_defaults(handler=leisure_recommend)
    leisure_daily = leisure_sub.add_parser("recommend-daily")
    leisure_daily.add_argument("--limit", type=int, default=3)
    leisure_daily.add_argument("--mood", default="")
    leisure_daily.add_argument("--minutes", type=int, default=0)
    leisure_daily.set_defaults(handler=leisure_recommend_daily)
    leisure_items = leisure_sub.add_parser("list-items")
    leisure_items.add_argument("--category", default="")
    leisure_items.add_argument("--limit", type=int, default=100)
    leisure_items.set_defaults(handler=leisure_list_items)
    leisure_recommendations = leisure_sub.add_parser("list-recommendations")
    leisure_recommendations.add_argument("--date", default="")
    leisure_recommendations.add_argument("--limit", type=int, default=100)
    leisure_recommendations.set_defaults(handler=leisure_list_recommendations)
    _add_simple_command(leisure_sub, "refresh-candidates", leisure_refresh_candidates)
    _add_simple_command(leisure_sub, "run-daily", leisure_derive)
    _add_simple_command(leisure_sub, "summarize-history", leisure_summarize_history)
    _add_simple_command(leisure_sub, "export", leisure_export)
    _add_simple_command(leisure_sub, "publish", leisure_export)

    airesearch = subparsers.add_parser("airesearch")
    airesearch_sub = airesearch.add_subparsers(dest="command", required=True)
    _add_simple_command(airesearch_sub, "health-check", airesearch_health_check)
    _add_simple_command(airesearch_sub, "validate", airesearch_health_check)
    _add_simple_command(airesearch_sub, "discover", airesearch_discover)
    _add_simple_command(airesearch_sub, "ingest-candidates", airesearch_discover)
    _add_simple_command(airesearch_sub, "ingest", airesearch_ingest)
    _add_simple_command(airesearch_sub, "derive", airesearch_derive)
    _add_simple_command(airesearch_sub, "export", airesearch_digest)
    _add_simple_command(airesearch_sub, "cluster", airesearch_cluster)
    _add_simple_command(airesearch_sub, "digest", airesearch_digest)
    _add_simple_command(airesearch_sub, "publish", airesearch_publish)
    _add_simple_command(airesearch_sub, "run-daily", airesearch_health_check)
    _add_simple_command(airesearch_sub, "refresh-weekly", airesearch_refresh_weekly)
    overview = airesearch_sub.add_parser("overview")
    overview.add_argument("--limit", type=int, default=5)
    overview.set_defaults(handler=airesearch_overview)
    paper_search = airesearch_sub.add_parser("paper-search")
    paper_search.add_argument("--q", required=True)
    paper_search.add_argument("--limit", type=int, default=20)
    paper_search.set_defaults(handler=airesearch_paper_search)

    return parser


def _add_simple_command(subparsers, name: str, handler) -> None:
    command = subparsers.add_parser(name)
    command.set_defaults(handler=handler)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_command(args.module, args.command, args, args.handler)


def platform_today_context(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action(
        "platform.today.context",
        {"date": _resolve_date_arg(args.date), "limit": args.limit},
        {"client": "cli"},
    )


def platform_modules_status(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("platform.modules.status", {"limit": args.limit}, {"client": "cli"})


def platform_health_check(args: argparse.Namespace) -> dict:
    """Validate the public platform tables and module registry."""
    with store.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    required = {
        "module_runs",
        "module_events",
        "assistant_actions",
        "model_calls",
        "user_profiles",
        "profile_changes",
    }
    missing = sorted(required - tables)
    if missing:
        raise RuntimeError("platform tables missing: " + ", ".join(missing))
    status = _execute_action("platform.modules.status", {"limit": 1})
    profile = _execute_action("profile.get", {})
    result = {
        "status": "passed",
        "requiredTables": sorted(required),
        "moduleCount": status.get("count", 0),
        "profileModules": sorted((profile.get("profiles") or {}).keys()),
    }
    audit.record_module_event("platform", "health_check", "platform health-check completed", result, "cli")
    return result


def platform_derive(args: argparse.Namespace) -> dict:
    """Derive the platform operational snapshot for today."""
    today = _today_local()
    modules = _execute_action("platform.modules.status", {"limit": 1})
    context = _execute_action("platform.today.context", {"date": today, "limit": 5})
    return {
        "status": "passed",
        "date": today,
        "modules": [_compact_module_status(item) for item in modules.get("items", [])],
        "today": _compact_today_context(context.get("context", {})),
    }


def platform_export(args: argparse.Namespace) -> dict:
    """Export the public platform operational snapshot."""
    today = _today_local()
    snapshots = _platform_business_snapshots(today)
    payload = {
        "date": today,
        "modules": [
            _compact_module_status(item)
            for item in _execute_action("platform.modules.status", {"limit": 2}).get("items", [])
        ],
        "today": _compact_today_context(
            _execute_action("platform.today.context", {"date": today, "limit": 5}).get("context", {})
        ),
        "runs": [_compact_run(item) for item in _execute_action("platform.runs.list", {"limit": 100}).get("items", [])],
        "events": [
            _compact_event(item) for item in _execute_action("platform.events.list", {"limit": 100}).get("items", [])
        ],
        "profiles": _execute_action("profile.get", {}).get("profiles", {}),
        "snapshots": snapshots,
    }
    export = exporters.write_json(PROJECT_ROOT / "exports" / "niu-secretary" / "platform.json", payload)
    audit.record_module_event("platform", "export", "platform export completed", export, "cli")
    return {
        "status": "passed",
        "export": export,
        "counts": {
            "modules": len(payload["modules"]),
            "runs": len(payload["runs"]),
            "events": len(payload["events"]),
            "profiles": len(payload["profiles"]),
            "snapshots": len(payload["snapshots"]),
        },
    }


def platform_publish(args: argparse.Namespace) -> dict:
    export = platform_export(args)
    return {"status": "passed", "export": export, "message": "platform export is ready for static serving"}


def platform_run_daily(args: argparse.Namespace) -> dict:
    health = platform_health_check(args)
    derived = platform_derive(args)
    export = platform_export(args)
    return {"status": "passed", "health": health, "derived": derived, "export": export}


def _compact_module_status(item: dict) -> dict:
    return {
        "module": item.get("module", ""),
        "capabilityCount": item.get("capabilityCount", 0),
        "status": item.get("status", ""),
        "lastRun": _compact_run(item.get("lastRun") or {}),
        "lastCronRun": _compact_run(item.get("lastCronRun") or {}),
        "lastEvent": _compact_event(item.get("lastEvent") or {}),
    }


def _compact_today_context(context: dict) -> dict:
    if not context:
        return {}
    copied = dict(context)
    copied["recentRuns"] = [_compact_run(item) for item in context.get("recentRuns", [])]
    return copied


def _compact_run(item: dict) -> dict:
    if not item:
        return {}
    return {
        "id": item.get("id", ""),
        "module": item.get("module", ""),
        "runType": item.get("runType", ""),
        "source": item.get("source", ""),
        "status": item.get("status", ""),
        "startedAt": item.get("startedAt", ""),
        "finishedAt": item.get("finishedAt", ""),
        "error": item.get("error", ""),
    }


def _compact_event(item: dict) -> dict:
    if not item:
        return {}
    return {
        "id": item.get("id", ""),
        "module": item.get("module", ""),
        "eventType": item.get("eventType", ""),
        "title": item.get("title", ""),
        "occurredAt": item.get("occurredAt", ""),
        "source": item.get("source", ""),
        "confidence": item.get("confidence", 1.0),
        "requiresReview": bool(item.get("requiresReview")),
    }


def _platform_business_snapshots(today: str) -> dict:
    """Collect small module snapshots for static clients and external tools."""
    return {
        "fitness": {
            "dailySummary": _execute_action("fitness.daily_summary.get", {"date": today}),
            "recommendations": _execute_action("fitness.recommendations.list", {"date": today, "limit": 20}),
        },
        "schedule": {
            "dayPlan": _execute_action("schedule.day_plan.get", {"date": today}),
            "dayReview": _execute_action("schedule.day_review.get", {"date": today}),
            "taskHistory": _execute_action("schedule.task_history.list", {"limit": 50}),
        },
        "leisure": {
            "items": _execute_action("leisure.items.list", {"limit": 50}),
            "history": _execute_action("leisure.history.search", {"limit": 50}),
            "recommendations": _execute_action("leisure.recommendations.list", {"limit": 20}),
        },
        "airesearch": {
            "overview": _execute_action("airesearch.overview", {"limit": 10}),
        },
    }


def news_validate(args: argparse.Namespace) -> dict:
    from extract_news_json import build_news_json
    from news_daily_validate import validate_items

    payload = build_news_json(PROJECT_ROOT / "news-daily" / "dist")
    errors = validate_items(payload["items"])
    status = "passed" if not errors else "blocked"
    audit.record_module_event(
        "news",
        "validation",
        f"news validate {status}",
        {"itemCount": len(payload["items"]), "errors": errors},
        "cli",
        1.0,
        bool(errors),
    )
    if errors:
        raise ValueError("news validation failed: " + "; ".join(errors[:5]))
    return {"status": status, "itemCount": len(payload["items"]), "errors": errors}


def news_archive(args: argparse.Namespace) -> dict:
    from archive_news import main as archive_main

    code = archive_main()
    if code != 0:
        raise RuntimeError(f"news archive exited with {code}")
    audit.record_module_event("news", "archive", "news archive completed", {"exitCode": code}, "cli")
    return {"status": "passed", "exitCode": code}


def news_run_daily(args: argparse.Namespace) -> dict:
    validation = news_validate(args)
    archive = news_archive(args)
    return {"status": "passed", "validate": validation, "archive": archive}


def news_validate_sources(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("news.validate-sources", {}, {"client": "cli"})


def news_validate_keypoints(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("news.validate-keypoints", {}, {"client": "cli"})


def news_audit_images(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("news.audit-images", {}, {"client": "cli"})


def news_extract_json(args: argparse.Namespace) -> dict:
    from extract_news_json import main as extract_main

    code = extract_main()
    if code != 0:
        raise RuntimeError(f"news extract-json exited with {code}")
    audit.record_module_event("news", "extract_json", "news extract-json completed", {"exitCode": code}, "cli")
    return {"status": "passed", "exitCode": code}


def news_crawl_images(args: argparse.Namespace) -> dict:
    from crawl_images import main as crawl_main

    code = crawl_main()
    if code != 0:
        raise RuntimeError(f"news crawl-images exited with {code}")
    audit.record_module_event("news", "crawl_images", "news crawl-images completed", {"exitCode": code}, "cli")
    return {"status": "passed", "exitCode": code}


def news_review_images(args: argparse.Namespace) -> dict:
    return _run_news_tool_script("review_images.py", "review_images", "review-images")


def news_update_sections(args: argparse.Namespace) -> dict:
    from update_sections import main as update_sections_main

    code = update_sections_main()
    if code != 0:
        raise RuntimeError(f"news update-sections exited with {code}")
    audit.record_module_event("news", "update_sections", "news update-sections completed", {"exitCode": code}, "cli")
    return {"status": "passed", "exitCode": code}


def _run_news_tool_script(script_name: str, event_type: str, command_name: str) -> dict:
    script = NEWS_TOOLS / script_name
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=PROJECT_ROOT,
        env=dict(os.environ),
        text=True,
        capture_output=True,
        check=False,
    )
    result = {
        "status": "passed" if completed.returncode == 0 else "failed",
        "exitCode": completed.returncode,
        "stdout": (completed.stdout or "").strip()[-4000:],
        "stderr": (completed.stderr or "").strip()[-2000:],
    }
    audit.record_module_event("news", event_type, f"news {command_name} completed", result, "cli", 1.0, completed.returncode != 0)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or f"news {command_name} exited with {completed.returncode}")
    return result


def news_publish(args: argparse.Namespace) -> dict:
    validation = news_validate(args)
    audit.record_module_event("news", "publish", "news publish completed", {"validation": validation}, "cli")
    return {"status": "passed", "validation": validation, "message": "news dist is ready for static serving"}


def news_search(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    payload = {
        "q": args.q,
        "date": args.date,
        "from": args.from_date,
        "to": args.to_date,
        "section": args.section,
        "tag": args.tag,
        "source": args.source,
        "limit": args.limit,
    }
    return execute_action("news.search", payload, {"client": "cli"})


def fitness_validate(args: argparse.Namespace) -> dict:
    errors = []
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT id, food, date, calories, protein_g, carbs_g, fat_g
            FROM fitness_nutrition_logs
            """
        ).fetchall()
        workouts = connection.execute(
            """
            SELECT id, name, date, duration_min, intensity, calories
            FROM fitness_workout_logs
            """
        ).fetchall()
        metrics = connection.execute(
            """
            SELECT id, date, weight_kg, body_fat_pct, waist_cm
            FROM fitness_body_metrics
            """
        ).fetchall()
        recovery = connection.execute(
            """
            SELECT id, date, sleep_hours, sleep_quality, stress, soreness, last_rpe, score
            FROM fitness_recovery_logs
            """
        ).fetchall()
        assessments = connection.execute(
            """
            SELECT id, date, goal, weight_kg, waist_cm, bmi, fms_total
            FROM fitness_assessment_logs
            """
        ).fetchall()
        consults = connection.execute(
            """
            SELECT id, date, area, text, level, title
            FROM fitness_consult_logs
            """
        ).fetchall()
    for row in rows:
        if not row["food"]:
            errors.append(f"{row['id']}: missing food")
        if not _valid_date(row["date"]):
            errors.append(f"{row['id']}: invalid date {row['date']}")
        for field in ("calories", "protein_g", "carbs_g", "fat_g"):
            if row[field] < 0:
                errors.append(f"{row['id']}: negative {field}")
    for row in workouts:
        if not row["name"]:
            errors.append(f"{row['id']}: missing workout name")
        if not _valid_date(row["date"]):
            errors.append(f"{row['id']}: invalid date {row['date']}")
        if row["duration_min"] < 0 or row["calories"] < 0:
            errors.append(f"{row['id']}: negative workout value")
        if row["intensity"] not in ("low", "medium", "high"):
            errors.append(f"{row['id']}: invalid intensity {row['intensity']}")
    for row in metrics:
        if not _valid_date(row["date"]):
            errors.append(f"{row['id']}: invalid date {row['date']}")
        for field in ("weight_kg", "body_fat_pct", "waist_cm"):
            if row[field] is not None and row[field] < 0:
                errors.append(f"{row['id']}: negative {field}")
    for row in recovery:
        if not _valid_date(row["date"]):
            errors.append(f"{row['id']}: invalid date {row['date']}")
        for field in ("sleep_hours", "sleep_quality", "stress", "soreness", "last_rpe", "score"):
            if row[field] < 0:
                errors.append(f"{row['id']}: negative {field}")
        if row["score"] > 100:
            errors.append(f"{row['id']}: invalid recovery score {row['score']}")
    for row in assessments:
        if not _valid_date(row["date"]):
            errors.append(f"{row['id']}: invalid date {row['date']}")
        for field in ("weight_kg", "waist_cm", "bmi"):
            if row[field] is not None and row[field] < 0:
                errors.append(f"{row['id']}: negative {field}")
        if row["fms_total"] < 0 or row["fms_total"] > 21:
            errors.append(f"{row['id']}: invalid fms_total {row['fms_total']}")
    for row in consults:
        if not _valid_date(row["date"]):
            errors.append(f"{row['id']}: invalid date {row['date']}")
        if not row["text"]:
            errors.append(f"{row['id']}: missing consult text")
    if errors:
        raise ValueError("fitness validation failed: " + "; ".join(errors[:5]))
    return {
        "status": "passed",
        "nutrition": len(rows),
        "workouts": len(workouts),
        "metrics": len(metrics),
        "recovery": len(recovery),
        "assessments": len(assessments),
        "consults": len(consults),
        "errors": [],
    }


def fitness_ingest_nutrition(args: argparse.Namespace) -> dict:
    """Lifecycle alias: current ingest state is the validated nutrition database."""
    result = fitness_validate(args)
    audit.record_module_event("fitness", "ingest", "fitness ingest completed", result, "cli")
    return {"status": "passed", "validation": result, "message": "fitness nutrition store is available"}


def fitness_derive(args: argparse.Namespace) -> dict:
    today = _today_local()
    day = _execute_action("fitness.summary.today", {"date": today})
    week = _execute_action("fitness.summary.weekly", {"date": today})
    meal = _execute_action("fitness.recommend.meal", {"date": today})
    workout = _execute_action("fitness.recommend.workout", {"date": today})
    return {
        "status": "passed",
        "date": today,
        "summaryToday": day.get("summary", {}),
        "summaryWeekly": week.get("summary", {}),
        "mealRecommendations": meal.get("recommendations", []),
        "workoutRecommendations": workout.get("recommendations", []),
    }


def fitness_export(args: argparse.Namespace) -> dict:
    payload = {
        "nutrition": store.list_nutrition_logs(limit=5000),
        "workouts": store.list_workout_logs(limit=5000),
        "metrics": store.list_body_metrics(limit=5000),
        "recovery": store.list_recovery_logs(limit=5000),
        "assessments": store.list_assessment_logs(limit=5000),
        "consults": store.list_consult_logs(limit=5000),
        "recommendations": store.list_fitness_recommendations(limit=5000),
    }
    export = exporters.write_json(PROJECT_ROOT / "exports" / "niu-secretary" / "fitness.json", payload)
    audit.record_module_event("fitness", "export", "fitness export completed", export, "cli")
    return {"status": "passed", "export": export, "counts": {key: len(value) for key, value in payload.items()}}


def fitness_publish(args: argparse.Namespace) -> dict:
    export = fitness_export(args)
    return {"status": "passed", "export": export, "message": "fitness export is ready for static serving"}


def fitness_run_daily(args: argparse.Namespace) -> dict:
    validation = fitness_validate(args)
    derived = fitness_derive(args)
    return {"status": "passed", "validation": validation, "derived": derived}


def fitness_summarize_week(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("fitness.summary.weekly", {"date": _resolve_date_arg(args.date)}, {"client": "cli"})


def fitness_summarize_day(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("fitness.summary.today", {"date": _resolve_date_arg(args.date)}, {"client": "cli"})


def fitness_recommend_meal(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    payload = {"date": _resolve_date_arg(args.date)} if args.date else {}
    return execute_action("fitness.recommend.meal", payload, {"client": "cli"})


def fitness_recommend_workout(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    payload = {"date": _resolve_date_arg(args.date)} if args.date else {}
    return execute_action("fitness.recommend.workout", payload, {"client": "cli"})


def fitness_list_nutrition(args: argparse.Namespace) -> dict:
    payload = _date_range_payload(args)
    return _execute_action("fitness.nutrition.list", payload)


def fitness_list_workouts(args: argparse.Namespace) -> dict:
    payload = _date_range_payload(args)
    return _execute_action("fitness.workout.list", payload)


def fitness_list_body_metrics(args: argparse.Namespace) -> dict:
    payload = _date_range_payload(args)
    return _execute_action("fitness.body_metric.list", payload)


def fitness_daily_summary_get(args: argparse.Namespace) -> dict:
    return _execute_action("fitness.daily_summary.get", {"date": _resolve_date_arg(args.date)})


def fitness_list_recommendations(args: argparse.Namespace) -> dict:
    payload = {"limit": args.limit}
    if args.date:
        payload["date"] = _resolve_date_arg(args.date)
    if args.type:
        payload["type"] = args.type
    return _execute_action("fitness.recommendations.list", payload)


def schedule_validate(args: argparse.Namespace) -> dict:
    errors = []
    with store.connect() as connection:
        events = connection.execute("SELECT id, title, date, time FROM schedule_events").fetchall()
        todos = connection.execute("SELECT id, title, date, done FROM schedule_todos").fetchall()
    for row in events:
        if not row["title"]:
            errors.append(f"{row['id']}: missing title")
        if not _valid_date(row["date"]):
            errors.append(f"{row['id']}: invalid date {row['date']}")
        if row["time"] and not _valid_time(row["time"]):
            errors.append(f"{row['id']}: invalid time {row['time']}")
    for row in todos:
        if not row["title"]:
            errors.append(f"{row['id']}: missing title")
        if row["date"] and not _valid_date(row["date"]):
            errors.append(f"{row['id']}: invalid date {row['date']}")
        if row["done"] not in (0, 1):
            errors.append(f"{row['id']}: invalid done {row['done']}")
    if errors:
        raise ValueError("schedule validation failed: " + "; ".join(errors[:5]))
    return {"status": "passed", "events": len(events), "todos": len(todos), "errors": []}


def schedule_detect_conflicts(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("schedule.conflicts.detect", {"date": _resolve_date_arg(args.date)}, {"client": "cli"})


def schedule_plan_day(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("schedule.day.plan", {"date": _resolve_date_arg(args.date), "source": "cli"}, {"client": "cli"})


def schedule_review_day(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action(
        "schedule.day.review",
        {"date": _resolve_date_arg(args.date), "completed": args.completed, "note": args.note, "source": "cli"},
        {"client": "cli"},
    )


def schedule_list_events(args: argparse.Namespace) -> dict:
    payload = _date_range_payload(args)
    return _execute_action("schedule.event.list", payload)


def schedule_list_todos(args: argparse.Namespace) -> dict:
    payload = _date_range_payload(args)
    payload["includeDone"] = bool(args.include_done)
    return _execute_action("schedule.todo.list", payload)


def schedule_day_plan_get(args: argparse.Namespace) -> dict:
    return _execute_action("schedule.day_plan.get", {"date": _resolve_date_arg(args.date)})


def schedule_day_review_get(args: argparse.Namespace) -> dict:
    return _execute_action("schedule.day_review.get", {"date": _resolve_date_arg(args.date)})


def schedule_task_history(args: argparse.Namespace) -> dict:
    payload = {"limit": args.limit}
    if args.todo_id:
        payload["todoId"] = args.todo_id
    return _execute_action("schedule.task_history.list", payload)


def schedule_rollover_todos(args: argparse.Namespace) -> dict:
    today = _today_local()
    moved = []
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, date, priority, done, source, created_at
            FROM schedule_todos
            WHERE done = 0 AND date <> '' AND date < ?
            ORDER BY date, created_at
            """,
            (today,),
        ).fetchall()
    for row in rows:
        record = store.reschedule_todo(row["id"], today)
        if record:
            moved.append(record)
    audit.record_module_event(
        "schedule",
        "rollover_todos",
        "schedule rollover-todos completed",
        {"date": today, "count": len(moved)},
        "cli",
    )
    return {"status": "passed", "date": today, "count": len(moved), "items": moved}


def schedule_derive(args: argparse.Namespace) -> dict:
    today = _today_local()
    conflicts = _execute_action("schedule.conflicts.detect", {"date": today})
    plan = _execute_action("schedule.day.plan", {"date": today, "source": "cli"})
    recommendations = _execute_action("schedule.recommend", {"date": today})
    return {
        "status": "passed",
        "date": today,
        "conflicts": conflicts.get("conflicts", []),
        "plan": plan.get("plan", {}),
        "recommendations": recommendations.get("recommendations", []),
    }


def schedule_export(args: argparse.Namespace) -> dict:
    today = _today_local()
    payload = {
        "events": store.list_schedule_events(limit=5000),
        "todos": store.list_schedule_todos(limit=5000),
        "todayPlan": store.get_day_plan(today),
        "todayReview": store.get_day_review(today),
        "taskHistory": store.list_schedule_task_history(limit=5000),
    }
    export = exporters.write_json(PROJECT_ROOT / "exports" / "niu-secretary" / "schedule.json", payload)
    audit.record_module_event("schedule", "export", "schedule export completed", export, "cli")
    return {"status": "passed", "export": export, "counts": {"events": len(payload["events"]), "todos": len(payload["todos"])}}


def schedule_publish(args: argparse.Namespace) -> dict:
    export = schedule_export(args)
    return {"status": "passed", "export": export, "message": "schedule export is ready for static serving"}


def schedule_run_daily(args: argparse.Namespace) -> dict:
    validation = schedule_validate(args)
    rollover = schedule_rollover_todos(args)
    derived = schedule_derive(args)
    return {"status": "passed", "validation": validation, "rollover": rollover, "derived": derived}


def leisure_validate(args: argparse.Namespace) -> dict:
    from niu_secretary.leisure_validation import validate_leisure_data_dir

    data_dir = PROJECT_ROOT / "leisure" / "dist" / "data"
    result = validate_leisure_data_dir(
        data_dir,
        strict_content=bool(getattr(args, "strict_content", False)),
    )
    errors = result["errors"]
    if errors:
        raise ValueError("leisure validation failed: " + "; ".join(errors[:5]))
    return result


def leisure_history_search(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action(
        "leisure.history.search",
        {"q": args.q, "category": args.category, "limit": args.limit},
        {"client": "cli"},
    )


def leisure_recommend(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    payload = {"limit": args.limit}
    if args.mood:
        payload["mood"] = args.mood
    if args.minutes:
        payload["availableMinutes"] = args.minutes
    return execute_action("leisure.recommend", payload, {"client": "cli"})


def leisure_recommend_daily(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    payload = {"limit": args.limit}
    if args.mood:
        payload["mood"] = args.mood
    if args.minutes:
        payload["availableMinutes"] = args.minutes
    result = execute_action("leisure.recommend", payload, {"client": "cli"})
    audit.record_module_event(
        "leisure",
        "recommend_daily",
        "leisure recommend-daily completed",
        {"count": result.get("count", 0), "personalized": bool(result.get("personalized"))},
        "cli",
    )
    return result | {"command": "recommend-daily"}


def leisure_list_items(args: argparse.Namespace) -> dict:
    payload = {"limit": args.limit}
    if args.category:
        payload["category"] = args.category
    return _execute_action("leisure.items.list", payload)


def leisure_list_recommendations(args: argparse.Namespace) -> dict:
    payload = {"limit": args.limit}
    if args.date:
        payload["date"] = _resolve_date_arg(args.date)
    return _execute_action("leisure.recommendations.list", payload)


def leisure_derive(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    result = execute_action("leisure.recommend", {"limit": 3}, {"client": "cli"})
    audit.record_module_event(
        "leisure",
        "derive",
        "leisure derive completed",
        {"count": result.get("count", 0), "personalized": bool(result.get("personalized"))},
        "cli",
    )
    return result | {"command": "derive"}


def leisure_refresh_candidates(args: argparse.Namespace) -> dict:
    result = leisure_validate(args)
    audit.record_module_event("leisure", "refresh_candidates", "leisure refresh-candidates completed", result, "cli")
    return {"status": "passed", "validation": result, "message": "leisure static candidate files are current"}


def leisure_summarize_history(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("leisure.history.search", {"limit": 500}, {"client": "cli"})


def leisure_export(args: argparse.Namespace) -> dict:
    result = leisure_validate(args)
    audit.record_module_event("leisure", "export", "leisure export completed", result, "cli")
    return {"status": "passed", "validation": result, "message": "leisure dist data is ready for static serving"}


def airesearch_health_check(args: argparse.Namespace) -> dict:
    command = [
        str(PROJECT_ROOT / "airesearch" / ".venv" / "bin" / "python"),
        "-m",
        "airesearch.cli",
        "health-check",
        "--site-dir",
        "exports/site-current",
    ]
    python_path = PROJECT_ROOT / "airesearch" / ".venv" / "bin" / "python"
    if not python_path.exists():
        command[0] = sys.executable
    env = dict(os.environ)
    env.setdefault("PAPER_DB_PATH", str(PROJECT_ROOT / "airesearch" / "data" / "paperpipe"))
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT / "airesearch",
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or "airesearch health-check failed")
    return {
        "status": "passed",
        "exitCode": completed.returncode,
        "stdout": completed.stdout.strip()[-4000:],
    }


def airesearch_paper_search(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("airesearch.paper.search", {"q": args.q, "limit": args.limit}, {"client": "cli"})


def airesearch_overview(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("airesearch.overview", {"limit": args.limit}, {"client": "cli"})


def airesearch_discover(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("airesearch.candidate.discover", {}, {"client": "cli"})


def airesearch_ingest(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("airesearch.paper.ingest", {}, {"client": "cli"})


def airesearch_cluster(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("airesearch.cluster.generate", {}, {"client": "cli"})


def airesearch_digest(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("airesearch.digest.generate", {}, {"client": "cli"})


def airesearch_derive(args: argparse.Namespace) -> dict:
    cluster = airesearch_cluster(args)
    digest = airesearch_digest(args)
    return {"status": "passed", "cluster": cluster, "digest": digest}


def airesearch_publish(args: argparse.Namespace) -> dict:
    from server.actions import execute_action

    return execute_action("airesearch.site.publish", {}, {"client": "cli"})


def airesearch_refresh_weekly(args: argparse.Namespace) -> dict:
    health = airesearch_health_check(args)
    audit.record_module_event("airesearch", "refresh_weekly", "airesearch refresh-weekly completed", health, "cli")
    return {"status": "passed", "health": health}


def _today_local() -> str:
    import datetime as _dt
    from zoneinfo import ZoneInfo

    return _dt.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def _resolve_date_arg(value: str) -> str:
    text = str(value or "").strip().lower()
    if text == "today":
        return _today_local()
    return text


def _execute_action(action: str, payload: dict) -> dict:
    from server.actions import execute_action

    return execute_action(action, payload, {"client": "cli"})


def _date_range_payload(args: argparse.Namespace) -> dict:
    payload = {"limit": args.limit}
    if args.from_date:
        payload["from"] = _resolve_date_arg(args.from_date)
    if args.to_date:
        payload["to"] = _resolve_date_arg(args.to_date)
    return payload


def _valid_date(value: str) -> bool:
    import datetime as _dt

    try:
        _dt.date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def _valid_time(value: str) -> bool:
    import datetime as _dt

    try:
        _dt.time.fromisoformat(value)
        return len(value) == 5
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    raise SystemExit(main())
