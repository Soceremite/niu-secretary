"""Action handlers for Niu Secretary 2.0."""

from __future__ import annotations

import html as html_lib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from server.actions import register_handler, ActionError
from server import store
from server.capabilities import CAPABILITIES

_AIRESEARCH_ADMIN_RUNTIME_INITIALIZED: set[str] = set()


def _is_read_only(context: dict) -> bool:
    return bool(
        context.get("readOnly")
        or context.get("read_only")
        or context.get("readonly")
    )


# ============================================================================
# Fitness Actions
# ============================================================================

@register_handler("fitness.nutrition.create")
def create_nutrition_log(payload: dict, context: dict) -> dict:
    """Create a nutrition log entry."""
    normalized = {
        "food": clean_text(payload.get("food"), 160),
        "date": clean_date(payload.get("date")),
        "calories": clamp(payload.get("calories"), 0, 5000),
        "proteinG": clamp(payload.get("proteinG"), 0, 300),
        "carbsG": clamp(payload.get("carbsG"), 0, 600),
        "fatG": clamp(payload.get("fatG"), 0, 300),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    record = store.insert_nutrition_log(normalized)
    return {
        "ok": True,
        "action": "fitness.nutrition.create",
        "record": record,
        "message": f"已记录到塑形馆营养：{record['food']}。",
    }


@register_handler("fitness.nutrition.today_summary")
def get_nutrition_summary(payload: dict, context: dict) -> dict:
    """Get nutrition summary for a specific date."""
    target_date = clean_date(payload.get("date"))
    summary = store.nutrition_summary(target_date)
    saved = None
    if not _is_read_only(context):
        saved = store.save_fitness_daily_summary(
            target_date,
            {"nutrition": summary},
            clean_source(payload.get("source") or context.get("client")),
        )
    return {
        "ok": True,
        "action": "fitness.nutrition.today_summary",
        "summary": summary,
        "savedSummary": saved,
        "message": f"{summary['date']} 已记录 {summary['count']} 餐，共 {summary['calories']} 千卡。",
    }


@register_handler("fitness.nutrition.list")
def list_nutrition(payload: dict, context: dict) -> dict:
    """List nutrition logs within an optional date range."""
    items = store.list_nutrition_logs(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "fitness.nutrition.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条营养记录。",
    }


@register_handler("fitness.nutrition.delete")
def delete_nutrition(payload: dict, context: dict) -> dict:
    """Delete a nutrition log by id."""
    record_id = clean_text(payload.get("id"), 80)
    record = store.delete_nutrition_log(record_id)
    if not record:
        raise ActionError("not_found", "未找到该营养记录。", 404, {"id": record_id})
    store.record_module_event(
        "fitness",
        "nutrition_deleted",
        f"nutrition deleted: {record['food']}",
        {"id": record_id, "record": record},
        clean_source(payload.get("source") or context.get("client")),
    )
    return {
        "ok": True,
        "action": "fitness.nutrition.delete",
        "id": record_id,
        "record": record,
        "message": "已从塑形馆删除该营养记录。",
    }


@register_handler("fitness.nutrition.update")
def update_nutrition(payload: dict, context: dict) -> dict:
    """Update a nutrition log by id."""
    record_id = clean_text(payload.get("id"), 80)
    patch = {}
    if "food" in payload:
        patch["food"] = clean_text(payload.get("food"), 160)
    if "date" in payload:
        patch["date"] = clean_date(payload.get("date"))
    if "calories" in payload:
        patch["calories"] = clamp(payload.get("calories"), 0, 5000)
    if "proteinG" in payload:
        patch["proteinG"] = clamp(payload.get("proteinG"), 0, 300)
    if "carbsG" in payload:
        patch["carbsG"] = clamp(payload.get("carbsG"), 0, 600)
    if "fatG" in payload:
        patch["fatG"] = clamp(payload.get("fatG"), 0, 300)
    if not patch:
        raise ActionError("validation_failed", "至少需要提供一个可更新字段。", 400, {"id": record_id})
    source = clean_source(payload.get("source") or context.get("client"))
    patch["source"] = source
    before = store.get_nutrition_log(record_id)
    record = store.update_nutrition_log(record_id, patch)
    if not record:
        raise ActionError("not_found", "未找到该营养记录。", 404, {"id": record_id})
    store.record_module_event(
        "fitness",
        "nutrition_updated",
        f"nutrition updated: {record['food']}",
        {"id": record_id, "before": before, "after": record, "changedFields": sorted(patch.keys() - {"source"})},
        source,
    )
    return {
        "ok": True,
        "action": "fitness.nutrition.update",
        "record": record,
        "message": f"已更新营养记录：{record['food']}。",
    }


@register_handler("fitness.nutrition.recognize_photo")
def recognize_nutrition_photo(payload: dict, context: dict) -> dict:
    """Action Protocol bridge for the existing multipart nutrition photo service."""
    raise ActionError(
        "unsupported_transport",
        "餐食图片识别需要 multipart 图片上传，请使用塑形馆图片识别服务；识别结果再通过 fitness.nutrition.create 写入。",
        400,
        {"endpoint": "/niu-secretary/fitness/api/agent/nutrition-recognize"},
    )


@register_handler("fitness.workout.create")
def create_workout_log(payload: dict, context: dict) -> dict:
    """Create a workout log entry."""
    normalized = {
        "name": clean_text(payload.get("name"), 160),
        "date": clean_date(payload.get("date")),
        "durationMin": clamp(payload.get("durationMin"), 0, 1440),
        "intensity": clean_choice(payload.get("intensity"), {"low", "medium", "high"}, "medium"),
        "calories": clamp(payload.get("calories"), 0, 3000),
        "note": clean_text(payload.get("note"), 300, allow_empty=True),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    record = store.insert_workout_log(normalized)
    store.record_module_event(
        "fitness",
        "workout",
        f"workout logged: {record['name']}",
        {"id": record["id"], "date": record["date"], "durationMin": record["durationMin"]},
        "api",
    )
    return {
        "ok": True,
        "action": "fitness.workout.create",
        "record": record,
        "message": f"已记录训练：{record['name']}。",
    }


@register_handler("fitness.workout.list")
def list_workouts(payload: dict, context: dict) -> dict:
    """List workout logs within an optional date range."""
    items = store.list_workout_logs(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "fitness.workout.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条训练记录。",
    }


@register_handler("fitness.workout.update")
def update_workout(payload: dict, context: dict) -> dict:
    """Update a workout log by id."""
    record_id = clean_text(payload.get("id"), 80)
    patch = {}
    if "name" in payload:
        patch["name"] = clean_text(payload.get("name"), 160)
    if "date" in payload:
        patch["date"] = clean_date(payload.get("date"))
    if "durationMin" in payload:
        patch["durationMin"] = clamp(payload.get("durationMin"), 0, 1440)
    if "intensity" in payload:
        patch["intensity"] = clean_choice(payload.get("intensity"), {"low", "medium", "high"}, "medium")
    if "calories" in payload:
        patch["calories"] = clamp(payload.get("calories"), 0, 3000)
    if "note" in payload:
        patch["note"] = clean_text(payload.get("note"), 300, allow_empty=True)
    if not patch:
        raise ActionError("validation_failed", "至少需要提供一个可更新字段。", 400, {"id": record_id})
    source = clean_source(payload.get("source") or context.get("client"))
    patch["source"] = source
    before = store.get_workout_log(record_id)
    record = store.update_workout_log(record_id, patch)
    if not record:
        raise ActionError("not_found", "未找到该训练记录。", 404, {"id": record_id})
    store.record_module_event(
        "fitness",
        "workout_updated",
        f"workout updated: {record['name']}",
        {"id": record_id, "before": before, "after": record, "changedFields": sorted(patch.keys() - {"source"})},
        source,
    )
    return {
        "ok": True,
        "action": "fitness.workout.update",
        "record": record,
        "message": f"已更新训练记录：{record['name']}。",
    }


@register_handler("fitness.workout.delete")
def delete_workout(payload: dict, context: dict) -> dict:
    """Delete a workout log by id."""
    record_id = clean_text(payload.get("id"), 80)
    record = store.delete_workout_log(record_id)
    if not record:
        raise ActionError("not_found", "未找到该训练记录。", 404, {"id": record_id})
    store.record_module_event(
        "fitness",
        "workout_deleted",
        f"workout deleted: {record['name']}",
        {"id": record_id, "record": record},
        clean_source(payload.get("source") or context.get("client")),
    )
    return {
        "ok": True,
        "action": "fitness.workout.delete",
        "id": record_id,
        "record": record,
        "message": "已从塑形馆删除该训练记录。",
    }


@register_handler("fitness.body_metric.create")
def create_body_metric(payload: dict, context: dict) -> dict:
    """Create a body metric entry."""
    normalized = {
        "date": clean_date(payload.get("date")),
        "weightKg": clean_optional_float(payload.get("weightKg"), 0, 500),
        "bodyFatPct": clean_optional_float(payload.get("bodyFatPct"), 0, 80),
        "waistCm": clean_optional_float(payload.get("waistCm"), 0, 300),
        "note": clean_text(payload.get("note"), 300, allow_empty=True),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    if all(normalized[field] is None for field in ("weightKg", "bodyFatPct", "waistCm")):
        raise ActionError("validation_failed", "至少需要提供一个身体指标。", 400)
    record = store.insert_body_metric(normalized)
    store.record_module_event(
        "fitness",
        "body_metric",
        "body metric logged",
        {"id": record["id"], "date": record["date"]},
        "api",
    )
    return {
        "ok": True,
        "action": "fitness.body_metric.create",
        "record": record,
        "message": "已记录身体指标。",
    }


@register_handler("fitness.body_metric.list")
def list_body_metrics(payload: dict, context: dict) -> dict:
    """List body metrics within an optional date range."""
    items = store.list_body_metrics(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "fitness.body_metric.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条身体指标。",
    }


@register_handler("fitness.body_metric.update")
def update_body_metric(payload: dict, context: dict) -> dict:
    """Update a body metric by id."""
    record_id = clean_text(payload.get("id"), 80)
    patch = {}
    if "date" in payload:
        patch["date"] = clean_date(payload.get("date"))
    if "weightKg" in payload:
        patch["weightKg"] = clean_optional_float(payload.get("weightKg"), 0, 500)
    if "bodyFatPct" in payload:
        patch["bodyFatPct"] = clean_optional_float(payload.get("bodyFatPct"), 0, 80)
    if "waistCm" in payload:
        patch["waistCm"] = clean_optional_float(payload.get("waistCm"), 0, 300)
    if "note" in payload:
        patch["note"] = clean_text(payload.get("note"), 300, allow_empty=True)
    if not patch:
        raise ActionError("validation_failed", "至少需要提供一个可更新字段。", 400, {"id": record_id})
    source = clean_source(payload.get("source") or context.get("client"))
    patch["source"] = source
    before = store.get_body_metric(record_id)
    if not before:
        raise ActionError("not_found", "未找到该身体指标。", 404, {"id": record_id})
    candidate = {field: patch.get(field, before[field]) for field in ("weightKg", "bodyFatPct", "waistCm")}
    if all(candidate[field] is None for field in ("weightKg", "bodyFatPct", "waistCm")):
        raise ActionError("validation_failed", "至少需要保留一个身体指标。", 400, {"id": record_id})
    record = store.update_body_metric(record_id, patch)
    store.record_module_event(
        "fitness",
        "body_metric_updated",
        "body metric updated",
        {"id": record_id, "before": before, "after": record, "changedFields": sorted(patch.keys() - {"source"})},
        source,
    )
    return {
        "ok": True,
        "action": "fitness.body_metric.update",
        "record": record,
        "message": "已更新身体指标。",
    }


@register_handler("fitness.body_metric.delete")
def delete_body_metric(payload: dict, context: dict) -> dict:
    """Delete a body metric by id."""
    record_id = clean_text(payload.get("id"), 80)
    record = store.delete_body_metric(record_id)
    if not record:
        raise ActionError("not_found", "未找到该身体指标。", 404, {"id": record_id})
    store.record_module_event(
        "fitness",
        "body_metric_deleted",
        "body metric deleted",
        {"id": record_id, "record": record},
        clean_source(payload.get("source") or context.get("client")),
    )
    return {
        "ok": True,
        "action": "fitness.body_metric.delete",
        "id": record_id,
        "record": record,
        "message": "已从塑形馆删除该身体指标。",
    }


@register_handler("fitness.recovery.create")
def create_recovery_log(payload: dict, context: dict) -> dict:
    """Create a recovery log entry."""
    normalized = {
        "date": clean_date(payload.get("date")),
        "sleepHours": clean_optional_float(payload.get("sleepHours"), 0, 24) or 0,
        "sleepQuality": clamp(payload.get("sleepQuality"), 0, 5),
        "stress": clamp(payload.get("stress"), 0, 5),
        "soreness": clamp(payload.get("soreness"), 0, 5),
        "lastRpe": clean_optional_float(payload.get("lastRpe"), 0, 10) or 0,
        "score": clamp(payload.get("score"), 0, 100),
        "statusLabel": clean_text(payload.get("statusLabel"), 40, allow_empty=True),
        "statusAdvice": clean_text(payload.get("statusAdvice"), 300, allow_empty=True),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    record = store.insert_recovery_log(normalized)
    store.record_module_event(
        "fitness",
        "recovery",
        f"recovery logged: {record['score']}",
        {"id": record["id"], "date": record["date"], "score": record["score"]},
        "api",
    )
    return {
        "ok": True,
        "action": "fitness.recovery.create",
        "record": record,
        "message": f"已记录恢复状态：{record['score']} 分。",
    }


@register_handler("fitness.recovery.list")
def list_recovery(payload: dict, context: dict) -> dict:
    """List recovery logs within an optional date range."""
    items = store.list_recovery_logs(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "fitness.recovery.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条恢复记录。",
    }


@register_handler("fitness.assessment.create")
def create_assessment(payload: dict, context: dict) -> dict:
    """Create a fitness assessment entry."""
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    normalized = {
        "date": clean_date(payload.get("date")),
        "goal": clean_text(payload.get("goal") or body.get("goal"), 80, allow_empty=True),
        "weightKg": clean_optional_float(payload.get("weightKg") if "weightKg" in payload else body.get("weightKg"), 0, 500),
        "waistCm": clean_optional_float(payload.get("waistCm") if "waistCm" in payload else body.get("waistCm"), 0, 300),
        "bmi": clean_optional_float(payload.get("bmi") if "bmi" in payload else body.get("bmi"), 0, 100),
        "fmsTotal": clamp(payload.get("fmsTotal") if "fmsTotal" in payload else body.get("fmsTotal"), 0, 21),
        "payload": body,
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    normalized["payload"] = normalized["payload"] | {
        "date": normalized["date"],
        "goal": normalized["goal"],
        "weightKg": normalized["weightKg"],
        "waistCm": normalized["waistCm"],
        "bmi": normalized["bmi"],
        "fmsTotal": normalized["fmsTotal"],
    }
    record = store.insert_assessment_log(normalized)
    store.record_module_event(
        "fitness",
        "assessment",
        "fitness assessment logged",
        {"id": record["id"], "date": record["date"], "fmsTotal": record["fmsTotal"]},
        "api",
    )
    return {
        "ok": True,
        "action": "fitness.assessment.create",
        "record": record,
        "message": "已记录身体评估。",
    }


@register_handler("fitness.assessment.list")
def list_assessments(payload: dict, context: dict) -> dict:
    items = store.list_assessment_logs(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "fitness.assessment.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条身体评估。",
    }


@register_handler("fitness.consult.create")
def create_consult(payload: dict, context: dict) -> dict:
    """Create a fitness consult entry."""
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    result = body.get("result") if isinstance(body.get("result"), dict) else {}
    normalized = {
        "date": clean_date(payload.get("date")),
        "area": clean_text(payload.get("area"), 80, allow_empty=True),
        "text": clean_text(payload.get("text"), 500),
        "level": clean_text(payload.get("level") or result.get("level"), 40, allow_empty=True),
        "title": clean_text(payload.get("title") or result.get("title"), 160, allow_empty=True),
        "payload": body,
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    normalized["payload"] = normalized["payload"] | {
        "date": normalized["date"],
        "area": normalized["area"],
        "text": normalized["text"],
        "level": normalized["level"],
        "title": normalized["title"],
    }
    record = store.insert_consult_log(normalized)
    store.record_module_event(
        "fitness",
        "consult",
        "fitness consult logged",
        {"id": record["id"], "date": record["date"], "level": record["level"]},
        "api",
    )
    return {
        "ok": True,
        "action": "fitness.consult.create",
        "record": record,
        "message": "已记录身体咨询。",
    }


@register_handler("fitness.consult.list")
def list_consults(payload: dict, context: dict) -> dict:
    items = store.list_consult_logs(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "fitness.consult.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条身体咨询。",
    }


@register_handler("fitness.summary.weekly")
def fitness_weekly_summary(payload: dict, context: dict) -> dict:
    """Summarize nutrition, workouts, and body metrics for a 7-day window."""
    end = date.fromisoformat(clean_date(payload.get("date")))
    start = end - timedelta(days=6)
    date_from = start.isoformat()
    date_to = end.isoformat()
    nutrition = store.list_nutrition_logs(date_from, date_to, 5000)
    workouts = store.list_workout_logs(date_from, date_to, 5000)
    metrics = store.list_body_metrics(date_from, date_to, 5000)
    summary = {
        "from": date_from,
        "to": date_to,
        "nutritionCount": len(nutrition),
        "calories": sum(item["calories"] for item in nutrition),
        "proteinG": sum(item["proteinG"] for item in nutrition),
        "workoutCount": len(workouts),
        "workoutMinutes": sum(item["durationMin"] for item in workouts),
        "workoutCalories": sum(item["calories"] for item in workouts),
        "latestMetric": metrics[0] if metrics else None,
        "metricsCount": len(metrics),
    }
    saved = None
    if not _is_read_only(context):
        saved = store.save_fitness_daily_summary(
            date_to,
            {"weekly": summary},
            clean_source(payload.get("source") or context.get("client")),
        )
    return {
        "ok": True,
        "action": "fitness.summary.weekly",
        "summary": summary,
        "savedSummary": saved,
        "message": f"{date_from} 至 {date_to} 汇总：{len(workouts)} 次训练，{len(nutrition)} 条饮食记录。",
    }


@register_handler("fitness.summary.today")
def fitness_today_summary(payload: dict, context: dict) -> dict:
    """Compatibility action for the platform plan's summary.today name."""
    return get_nutrition_summary(payload, context) | {
        "action": "fitness.summary.today",
        "message": "已返回指定日期的塑形馆营养汇总。",
    }


@register_handler("fitness.recommend.meal")
def fitness_recommend_meal(payload: dict, context: dict) -> dict:
    """Compatibility action for meal recommendations."""
    result = fitness_recommend_handler(payload, context)
    return result | {
        "action": "fitness.recommend.meal",
        "message": "已生成餐食建议。",
    }


@register_handler("fitness.recommend.workout")
def fitness_recommend_workout(payload: dict, context: dict) -> dict:
    """Generate a simple workout recommendation from recent logs."""
    target_date = clean_optional_date(payload.get("date")) or date.today().isoformat()
    available_minutes = clamp(payload.get("availableMinutes") or payload.get("available_minutes") or 0, 0, 720)
    schedule_load = clamp(payload.get("scheduleLoad") or payload.get("schedule_load") or 0, 0, 100)
    end = date.fromisoformat(target_date)
    start = (end - timedelta(days=6)).isoformat()
    workouts = store.list_workout_logs(start, target_date, 100)
    minutes = sum(item["durationMin"] for item in workouts)
    profile = store.get_profile("fitness")["profile"]
    if schedule_load >= 5 or (available_minutes and available_minutes <= 30):
        tip = "今日日程较满，训练建议压缩为 15-25 分钟拉伸、核心激活或低强度散步。"
    elif minutes >= 180:
        tip = "本周训练量已经较高，今天优先安排拉伸、散步或低强度恢复。"
    elif profile.get("goal") == "muscle_gain":
        tip = "今天建议安排 45-60 分钟力量训练，优先复合动作并记录组数。"
    else:
        tip = "今天建议安排 30-45 分钟中等强度训练，保持可持续的训练负荷。"
    recommendation = None
    if not _is_read_only(context):
        recommendation = store.record_fitness_recommendation(
            target_date,
            "workout",
            [tip],
            {
                "recentWorkoutCount": len(workouts),
                "recentWorkoutMinutes": minutes,
                "availableMinutes": available_minutes,
                "scheduleLoad": schedule_load,
                "profile": profile,
            },
            clean_source(payload.get("source") or context.get("client")),
        )
    return {
        "ok": True,
        "action": "fitness.recommend.workout",
        "module": "fitness",
        "date": target_date,
        "recentWorkoutCount": len(workouts),
        "recentWorkoutMinutes": minutes,
        "availableMinutes": available_minutes,
        "scheduleLoad": schedule_load,
        "recommendations": [tip],
        "recommendationRecord": recommendation,
        "message": "已生成训练建议。",
    }


@register_handler("fitness.recommendations.list")
def list_fitness_recommendations_handler(payload: dict, context: dict) -> dict:
    """Read persisted fitness recommendation history."""
    target_date = clean_optional_date(payload.get("date"))
    recommendation_type = clean_choice(
        payload.get("type") or payload.get("recommendationType"),
        {"", "meal", "workout", "general"},
        "",
    )
    items = store.list_fitness_recommendations(
        target_date,
        recommendation_type,
        clamp(payload.get("limit") or 50, 1, 500),
    )
    return {
        "ok": True,
        "action": "fitness.recommendations.list",
        "module": "fitness",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条塑形馆推荐历史。",
    }


@register_handler("fitness.daily_summary.get")
def get_fitness_daily_summary_handler(payload: dict, context: dict) -> dict:
    """Read a stored fitness daily summary without recomputing it."""
    target_date = clean_date(payload.get("date"))
    summary = store.get_fitness_daily_summary(target_date)
    return {
        "ok": True,
        "action": "fitness.daily_summary.get",
        "module": "fitness",
        "date": target_date,
        "summary": summary,
        "found": bool(summary.get("summary")),
        "message": f"返回 {target_date} 塑形馆已保存汇总。",
    }


# ============================================================================
# Schedule Actions
# ============================================================================

@register_handler("schedule.event.create")
def create_schedule_event(payload: dict, context: dict) -> dict:
    """Create a schedule event."""
    normalized = {
        "title": clean_text(payload.get("title"), 160),
        "date": clean_date(payload.get("date")),
        "time": clean_time(payload.get("time")),
        "note": clean_text(payload.get("note"), 300, allow_empty=True),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    record = store.insert_schedule_event(normalized)
    time_label = f" {record['time']}" if record["time"] else ""
    return {
        "ok": True,
        "action": "schedule.event.create",
        "record": record,
        "message": f"已加入时务局日程：{record['date']}{time_label} {record['title']}。",
    }


@register_handler("schedule.todo.create")
def create_schedule_todo(payload: dict, context: dict) -> dict:
    """Create a schedule todo."""
    normalized = {
        "title": clean_text(payload.get("title"), 160),
        "date": clean_optional_date(payload.get("date")),
        "priority": clean_priority(payload.get("priority")),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    record = store.insert_schedule_todo(normalized)
    return {
        "ok": True,
        "action": "schedule.todo.create",
        "record": record,
        "message": f"已加入时务局待办：{record['title']}。",
    }


@register_handler("schedule.important_date.create")
def create_schedule_important_date(payload: dict, context: dict) -> dict:
    """Create an important date for schedule reminders."""
    normalized = {
        "title": clean_text(payload.get("title"), 160),
        "date": clean_schedule_anchor_date(payload.get("date")),
        "note": clean_text(payload.get("note"), 300, allow_empty=True),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    record = store.insert_schedule_important_date(normalized)
    store.record_module_event(
        "schedule",
        "important_date_created",
        f"important date created: {record['title']}",
        {"id": record["id"], "date": record["date"]},
        record["source"],
    )
    return {
        "ok": True,
        "action": "schedule.important_date.create",
        "record": record,
        "message": f"已加入重要日期：{record['title']}。",
    }


@register_handler("schedule.important_date.list")
def list_schedule_important_dates_handler(payload: dict, context: dict) -> dict:
    """List important dates for schedule reminders."""
    items = store.list_schedule_important_dates(clamp(payload.get("limit") or 500, 1, 2000))
    return {
        "ok": True,
        "action": "schedule.important_date.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 个重要日期。",
    }


@register_handler("schedule.goal.create")
def create_schedule_goal(payload: dict, context: dict) -> dict:
    """Create a schedule goal tracking row."""
    normalized = {
        "title": clean_text(payload.get("title"), 160),
        "cadence": clean_schedule_cadence(payload.get("cadence")),
        "streak": clamp(payload.get("streak") or 0, 0, 10000),
        "note": clean_text(payload.get("note"), 500, allow_empty=True),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    record = store.insert_schedule_goal(normalized)
    store.record_module_event(
        "schedule",
        "goal_created",
        f"goal created: {record['title']}",
        {"id": record["id"], "streak": record["streak"]},
        record["source"],
    )
    return {
        "ok": True,
        "action": "schedule.goal.create",
        "record": record,
        "message": f"已加入目标：{record['title']}。",
    }


@register_handler("schedule.goal.list")
def list_schedule_goals_handler(payload: dict, context: dict) -> dict:
    """List schedule goals."""
    items = store.list_schedule_goals(clamp(payload.get("limit") or 500, 1, 2000))
    return {
        "ok": True,
        "action": "schedule.goal.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 个目标。",
    }


@register_handler("schedule.today_summary")
def get_schedule_summary(payload: dict, context: dict) -> dict:
    """Get schedule summary for a specific date."""
    summary = store.schedule_summary(clean_date(payload.get("date")))
    return {
        "ok": True,
        "action": "schedule.today_summary",
        "summary": summary,
        "message": f"{summary['date']} 有 {len(summary['events'])} 个日程、{len(summary['todos'])} 个待办。",
    }


@register_handler("schedule.conflicts.detect")
def detect_schedule_conflicts(payload: dict, context: dict) -> dict:
    """Detect same-date events that share an exact start time."""
    target_date = clean_date(payload.get("date"))
    events = [item for item in store.list_schedule_events(target_date, target_date, 2000) if item.get("time")]
    by_time: dict[str, list[dict]] = {}
    for event in events:
        by_time.setdefault(event["time"], []).append(event)
    conflicts = [
        {"date": target_date, "time": time, "events": items}
        for time, items in sorted(by_time.items())
        if len(items) > 1
    ]
    return {
        "ok": True,
        "action": "schedule.conflicts.detect",
        "date": target_date,
        "conflicts": conflicts,
        "count": len(conflicts),
        "message": f"发现 {len(conflicts)} 组日程冲突。",
    }


@register_handler("schedule.day.plan")
def plan_schedule_day(payload: dict, context: dict) -> dict:
    """Create and store a deterministic day plan from events and todos."""
    target_date = clean_date(payload.get("date"))
    source = clean_source(payload.get("source") or context.get("client"))
    summary = store.schedule_summary(target_date)
    events = sorted(summary["events"], key=lambda item: (item.get("time") or "99:99", item.get("created_at") or ""))
    todos = [todo for todo in summary["todos"] if not bool(todo.get("done"))]
    blocks = []
    for event in events:
        blocks.append({
            "type": "event",
            "time": event.get("time") or "",
            "title": event.get("title") or "",
            "id": event.get("id") or "",
        })
    for todo in todos[:8]:
        blocks.append({
            "type": "todo",
            "time": "",
            "title": todo.get("title") or "",
            "id": todo.get("id") or "",
            "priority": todo.get("priority") or "normal",
        })
    plan = {
        "date": target_date,
        "blocks": blocks,
        "eventCount": len(events),
        "todoCount": len(todos),
        "conflictCount": len(detect_schedule_conflicts({"date": target_date}, context)["conflicts"]),
    }
    saved = store.save_day_plan(target_date, plan, source)
    store.record_module_event("schedule", "day_plan", "schedule day plan saved", saved, "api")
    return {
        "ok": True,
        "action": "schedule.day.plan",
        "plan": saved,
        "message": f"已生成 {target_date} 日计划。",
    }


@register_handler("schedule.day.review")
def review_schedule_day(payload: dict, context: dict) -> dict:
    """Store a day review."""
    target_date = clean_date(payload.get("date"))
    source = clean_source(payload.get("source") or context.get("client"))
    blocked = payload.get("blocked") if isinstance(payload.get("blocked"), list) else []
    review = {
        "date": target_date,
        "completed": clamp(payload.get("completed") or 0, 0, 500),
        "blocked": [clean_text(item, 120) for item in blocked[:20]],
        "note": clean_text(payload.get("note"), 1000, allow_empty=True),
    }
    saved = store.save_day_review(target_date, review, source)
    store.record_module_event("schedule", "day_review", "schedule day review saved", saved, "api")
    return {
        "ok": True,
        "action": "schedule.day.review",
        "review": saved,
        "message": f"已保存 {target_date} 日复盘。",
    }


@register_handler("schedule.day_plan.get")
def get_schedule_day_plan(payload: dict, context: dict) -> dict:
    """Read a stored deterministic day plan."""
    target_date = clean_date(payload.get("date"))
    plan = store.get_day_plan(target_date)
    return {
        "ok": True,
        "action": "schedule.day_plan.get",
        "module": "schedule",
        "date": target_date,
        "plan": plan,
        "found": bool(plan.get("plan")),
        "message": f"返回 {target_date} 日计划。",
    }


@register_handler("schedule.day_review.get")
def get_schedule_day_review(payload: dict, context: dict) -> dict:
    """Read a stored day review."""
    target_date = clean_date(payload.get("date"))
    review = store.get_day_review(target_date)
    return {
        "ok": True,
        "action": "schedule.day_review.get",
        "module": "schedule",
        "date": target_date,
        "review": review,
        "found": bool(review.get("review")),
        "message": f"返回 {target_date} 日复盘。",
    }


@register_handler("schedule.event.list")
def list_schedule_events_handler(payload: dict, context: dict) -> dict:
    """List schedule events within an optional date range."""
    items = store.list_schedule_events(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "schedule.event.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 个日程。",
    }


@register_handler("schedule.event.delete")
def delete_schedule_event_handler(payload: dict, context: dict) -> dict:
    """Delete a schedule event by id."""
    record_id = clean_text(payload.get("id"), 80)
    record = store.delete_schedule_event(record_id)
    if not record:
        raise ActionError("not_found", "未找到该日程。", 404, {"id": record_id})
    store.record_module_event(
        "schedule",
        "event_deleted",
        f"schedule event deleted: {record['title']}",
        {"id": record_id, "record": record},
        clean_source(payload.get("source") or context.get("client")),
    )
    return {
        "ok": True,
        "action": "schedule.event.delete",
        "id": record_id,
        "record": record,
        "message": "已从时务局删除该日程。",
    }


@register_handler("schedule.event.update")
def update_schedule_event_handler(payload: dict, context: dict) -> dict:
    """Update a schedule event by id."""
    record_id = clean_text(payload.get("id"), 80)
    patch = {}
    if "title" in payload:
        patch["title"] = clean_text(payload.get("title"), 160)
    if "date" in payload:
        patch["date"] = clean_date(payload.get("date"))
    if "time" in payload:
        patch["time"] = clean_time(payload.get("time"))
    if "note" in payload:
        patch["note"] = clean_text(payload.get("note"), 300, allow_empty=True)
    if not patch:
        raise ActionError("validation_failed", "至少需要提供一个可更新字段。", 400, {"id": record_id})
    source = clean_source(payload.get("source") or context.get("client"))
    patch["source"] = source
    before = store.get_schedule_event(record_id)
    record = store.update_schedule_event(record_id, patch)
    if not record:
        raise ActionError("not_found", "未找到该日程。", 404, {"id": record_id})
    store.record_module_event(
        "schedule",
        "event_updated",
        f"schedule event updated: {record['title']}",
        {"id": record_id, "before": before, "after": record, "changedFields": sorted(patch.keys() - {"source"})},
        source,
    )
    return {
        "ok": True,
        "action": "schedule.event.update",
        "record": record,
        "message": f"已更新日程：{record['title']}。",
    }


@register_handler("schedule.todo.list")
def list_schedule_todos_handler(payload: dict, context: dict) -> dict:
    """List todos within an optional date range."""
    include_done = payload.get("includeDone")
    items = store.list_schedule_todos(
        clean_optional_date(payload.get("from")),
        clean_optional_date(payload.get("to")),
        True if include_done is None else bool(include_done),
        clamp(payload.get("limit") or 500, 1, 2000),
    )
    return {
        "ok": True,
        "action": "schedule.todo.list",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 个待办。",
    }


@register_handler("schedule.todo.toggle")
def toggle_schedule_todo_handler(payload: dict, context: dict) -> dict:
    """Toggle or set a todo's done state."""
    record_id = clean_text(payload.get("id"), 80)
    done = payload.get("done")
    if done is None:
        # No explicit state: flip current value.
        current = next(
            (t for t in store.list_schedule_todos() if t["id"] == record_id), None
        )
        if current is None:
            raise ActionError("not_found", "未找到该待办。", 404, {"id": record_id})
        done = not current["done"]
    record = store.set_schedule_todo_done(record_id, bool(done))
    if record is None:
        raise ActionError("not_found", "未找到该待办。", 404, {"id": record_id})
    history = store.record_schedule_task_history(
        record_id,
        "completed" if record["done"] else "reopened",
        record["title"],
        {"done": record["done"], "date": record["date"]},
        clean_source(payload.get("source") or context.get("client")),
    )
    return {
        "ok": True,
        "action": "schedule.todo.toggle",
        "record": record,
        "history": history,
        "message": f"待办「{record['title']}」已标记为{'完成' if record['done'] else '未完成'}。",
    }


@register_handler("schedule.todo.complete")
def complete_schedule_todo_handler(payload: dict, context: dict) -> dict:
    """Compatibility action for marking a todo as complete."""
    return toggle_schedule_todo_handler({**payload, "done": True}, context) | {
        "action": "schedule.todo.complete",
    }


@register_handler("schedule.todo.reschedule")
def reschedule_schedule_todo_handler(payload: dict, context: dict) -> dict:
    """Move a todo to a new date."""
    record_id = clean_text(payload.get("id"), 80)
    target_date = clean_date(payload.get("date"))
    record = store.reschedule_todo(record_id, target_date)
    if record is None:
        raise ActionError("not_found", "未找到该待办。", 404, {"id": record_id})
    store.record_module_event(
        "schedule",
        "todo_rescheduled",
        f"todo rescheduled: {record['title']}",
        {"id": record_id, "date": target_date},
        "api",
    )
    history = store.record_schedule_task_history(
        record_id,
        "rescheduled",
        record["title"],
        {"date": target_date},
        clean_source(payload.get("source") or context.get("client")),
    )
    return {
        "ok": True,
        "action": "schedule.todo.reschedule",
        "record": record,
        "history": history,
        "message": f"已将待办「{record['title']}」调整到 {target_date}。",
    }


@register_handler("schedule.todo.update")
def update_schedule_todo_handler(payload: dict, context: dict) -> dict:
    """Update a todo's title, date or priority."""
    record_id = clean_text(payload.get("id"), 80)
    patch = {}
    if "title" in payload:
        patch["title"] = clean_text(payload.get("title"), 160)
    if "date" in payload:
        patch["date"] = clean_optional_date(payload.get("date"))
    if "priority" in payload:
        patch["priority"] = clean_priority(payload.get("priority"))
    if not patch:
        raise ActionError("validation_failed", "至少需要提供一个可更新字段。", 400, {"id": record_id})
    source = clean_source(payload.get("source") or context.get("client"))
    patch["source"] = source
    before = store.get_schedule_todo(record_id)
    record = store.update_schedule_todo(record_id, patch)
    if not record:
        raise ActionError("not_found", "未找到该待办。", 404, {"id": record_id})
    changed_fields = sorted(patch.keys() - {"source"})
    store.record_module_event(
        "schedule",
        "todo_updated",
        f"todo updated: {record['title']}",
        {"id": record_id, "before": before, "after": record, "changedFields": changed_fields},
        source,
    )
    history = store.record_schedule_task_history(
        record_id,
        "updated",
        record["title"],
        {"before": before, "after": record, "changedFields": changed_fields},
        source,
    )
    return {
        "ok": True,
        "action": "schedule.todo.update",
        "record": record,
        "history": history,
        "message": f"已更新待办：{record['title']}。",
    }


@register_handler("schedule.todo.delete")
def delete_schedule_todo_handler(payload: dict, context: dict) -> dict:
    """Delete a todo by id."""
    record_id = clean_text(payload.get("id"), 80)
    record = store.delete_schedule_todo(record_id)
    if not record:
        raise ActionError("not_found", "未找到该待办。", 404, {"id": record_id})
    source = clean_source(payload.get("source") or context.get("client"))
    store.record_module_event(
        "schedule",
        "todo_deleted",
        f"todo deleted: {record['title']}",
        {"id": record_id, "record": record},
        source,
    )
    history = store.record_schedule_task_history(
        record_id,
        "deleted",
        record["title"],
        {"record": record},
        source,
    )
    return {
        "ok": True,
        "action": "schedule.todo.delete",
        "id": record_id,
        "record": record,
        "history": history,
        "message": "已从时务局删除该待办。",
    }


# ============================================================================
# User Profile Actions (用户画像)
# ============================================================================

def _validate_module(value) -> str:
    module = clean_text(value, 40).lower()
    if module not in store.PROFILE_MODULES:
        raise ActionError(
            "validation_failed",
            f"未知板块：{module}。可选：{', '.join(store.PROFILE_MODULES)}。",
            400,
            {"field": "module"},
        )
    return module


@register_handler("profile.get")
def get_profile_handler(payload: dict, context: dict) -> dict:
    """Read one module profile, or all when module is omitted."""
    raw_module = str(payload.get("module") or "").strip()
    if not raw_module:
        return {
            "ok": True,
            "action": "profile.get",
            "profiles": store.get_all_profiles(),
            "message": "返回全部板块画像。",
        }
    module = _validate_module(raw_module)
    result = store.get_profile(module)
    return {
        "ok": True,
        "action": "profile.get",
        "module": module,
        "profile": result["profile"],
        "updatedAt": result["updatedAt"],
        "message": f"返回{module}板块画像。",
    }


@register_handler("profile.update")
def update_profile_handler(payload: dict, context: dict) -> dict:
    """Merge a patch into a module profile."""
    module = _validate_module(payload.get("module"))
    patch = payload.get("patch")
    if not isinstance(patch, dict) or not patch:
        raise ActionError("validation_failed", "patch 必须是非空对象。", 400, {"field": "patch"})
    summary = clean_text(payload.get("summary"), 200, allow_empty=True)
    source = clean_source(payload.get("source") or context.get("client"))
    result = store.update_profile(module, patch, summary, source)
    changed = result["changedFields"]
    if changed:
        msg = f"已更新{module}画像：{ '、'.join(changed) }。"
    else:
        msg = f"{module}画像无变化（值与现状相同）。"
    return {
        "ok": True,
        "action": "profile.update",
        "module": module,
        "profile": result["profile"],
        "changedFields": changed,
        "message": msg,
    }


@register_handler("profile.reset")
def reset_profile_handler(payload: dict, context: dict) -> dict:
    """Reset a module profile to default."""
    module = _validate_module(payload.get("module"))
    source = clean_source(payload.get("source") or context.get("client"))
    result = store.reset_profile(module, source)
    return {
        "ok": True,
        "action": "profile.reset",
        "module": module,
        "profile": result["profile"],
        "message": f"已将{module}画像重置为默认值。",
    }


@register_handler("profile.changes")
def profile_changes_handler(payload: dict, context: dict) -> dict:
    """Read profile change history."""
    raw_module = str(payload.get("module") or "").strip()
    module = _validate_module(raw_module) if raw_module else ""
    items = store.list_profile_changes(module, clamp(payload.get("limit") or 50, 1, 500))
    return {
        "ok": True,
        "action": "profile.changes",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条画像变更记录。",
    }


@register_handler("profile.change.review")
def profile_change_review_handler(payload: dict, context: dict) -> dict:
    """Mark one profile change as reviewed by recording an audit event."""
    change_id = clean_text(payload.get("changeId") or payload.get("id"), 120)
    change = store.get_profile_change(change_id)
    if not change:
        raise ActionError("not_found", "未找到该画像变更。", 404, {"changeId": change_id})
    if change.get("reviewed"):
        return {
            "ok": True,
            "action": "profile.change.review",
            "module": change["module"],
            "change": change,
            "event": change.get("review"),
            "message": "该画像变更此前已处理。",
        }
    note = clean_text(payload.get("note"), 300, allow_empty=True)
    source = clean_source(payload.get("source") or context.get("client"))
    event = store.record_module_event(
        change["module"],
        "profile_change_review",
        f"profile change reviewed: {change['field']}",
        {
            "changeId": change["id"],
            "field": change["field"],
            "oldValue": change["oldValue"],
            "newValue": change["newValue"],
            "note": note,
        },
        source,
    )
    reviewed_change = store.get_profile_change(change_id) or change
    return {
        "ok": True,
        "action": "profile.change.review",
        "module": change["module"],
        "change": reviewed_change,
        "event": event,
        "message": "已标记该画像变更为已处理。",
    }


@register_handler("profile.change.revert")
def profile_change_revert_handler(payload: dict, context: dict) -> dict:
    """Revert one profile field back to the value before a specific change."""
    change_id = clean_text(payload.get("changeId") or payload.get("id"), 120)
    change = store.get_profile_change(change_id)
    if not change:
        raise ActionError("not_found", "未找到该画像变更。", 404, {"changeId": change_id})
    if change.get("reviewed"):
        return {
            "ok": True,
            "action": "profile.change.revert",
            "module": change["module"],
            "change": change,
            "event": change.get("review"),
            "message": "该画像变更此前已处理。",
        }
    if change["field"] == "*":
        raise ActionError(
            "validation_failed",
            "重置类画像变更不能按单字段回滚。",
            400,
            {"changeId": change_id, "field": change["field"]},
        )

    current_profile = store.get_profile(change["module"])["profile"]
    current_value = current_profile.get(change["field"])
    if current_value != change["newValue"] and current_value != change["oldValue"]:
        raise ActionError(
            "conflict",
            "该画像字段已被后续变更修改，不能直接回滚旧变更。",
            409,
            {
                "changeId": change_id,
                "field": change["field"],
                "currentValue": current_value,
                "expectedValue": change["newValue"],
            },
        )

    note = clean_text(payload.get("note"), 300, allow_empty=True)
    source = clean_source(payload.get("source") or context.get("client"))
    profile_update = None
    if current_value != change["oldValue"]:
        profile_update = store.update_profile(
            change["module"],
            {change["field"]: change["oldValue"]},
            f"回滚画像变更 {change['id']}: {change['field']}",
            source,
        )
    event = store.record_module_event(
        change["module"],
        "profile_change_revert",
        f"profile change reverted: {change['field']}",
        {
            "changeId": change["id"],
            "field": change["field"],
            "oldValue": change["oldValue"],
            "newValue": change["newValue"],
            "revertedTo": change["oldValue"],
            "note": note,
            "profileUpdated": bool(profile_update),
        },
        source,
    )
    reverted_change = store.get_profile_change(change_id) or change
    return {
        "ok": True,
        "action": "profile.change.revert",
        "module": change["module"],
        "change": reverted_change,
        "event": event,
        "profile": (profile_update or store.get_profile(change["module"]))["profile"],
        "message": "已回滚该画像字段并写入审计。" if profile_update else "画像字段已是旧值，已补充回滚审计。",
    }


# ============================================================================
# Platform audit actions
# ============================================================================

def _validate_optional_module(value) -> str:
    module = clean_text(value, 40, allow_empty=True).lower()
    if not module:
        return ""
    allowed = set(store.PROFILE_MODULES) | {"profile", "platform", "airesearch"}
    if module not in allowed:
        raise ActionError(
            "validation_failed",
            f"未知板块：{module}。可选：{', '.join(sorted(allowed))}。",
            400,
            {"field": "module"},
        )
    return module


@register_handler("platform.runs.list")
def platform_runs_list_handler(payload: dict, context: dict) -> dict:
    """Read module run audit history."""
    module = _validate_optional_module(payload.get("module"))
    items = store.list_module_runs(module, clamp(payload.get("limit") or 50, 1, 500))
    return {
        "ok": True,
        "action": "platform.runs.list",
        "module": module,
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条模块运行记录。",
    }


@register_handler("platform.events.list")
def platform_events_list_handler(payload: dict, context: dict) -> dict:
    """Read module event audit history."""
    module = _validate_optional_module(payload.get("module"))
    event_type = clean_text(payload.get("eventType"), 80, allow_empty=True)
    requires_review = None
    if payload.get("requiresReview") is not None:
        requires_review = bool(payload.get("requiresReview"))
    items = store.list_module_events(
        module,
        event_type,
        clamp(payload.get("limit") or 50, 1, 500),
        requires_review,
    )
    return {
        "ok": True,
        "action": "platform.events.list",
        "module": module,
        "eventType": event_type,
        "requiresReview": requires_review,
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条模块事件记录。",
    }


@register_handler("platform.review.mark")
def platform_review_mark_handler(payload: dict, context: dict) -> dict:
    """Mark a reviewable module event as handled or ignored via append-only audit."""
    event_id = clean_text(payload.get("eventId"), 120)
    status = clean_choice(payload.get("status"), {"handled", "ignored"}, "handled")
    note = clean_text(payload.get("note"), 500, allow_empty=True)
    event = store.get_module_event(event_id)
    if not event:
        raise ActionError("not_found", "未找到该待审核事件。", 404, {"eventId": event_id})
    if not event.get("requiresReview"):
        raise ActionError("validation_failed", "该事件不需要审核处理。", 400, {"eventId": event_id})

    existing = store.get_latest_module_review_mark(event_id)
    if existing:
        return {
            "ok": True,
            "action": "platform.review.mark",
            "module": event["module"],
            "event": event,
            "review": existing,
            "message": "该待审核事件此前已处理。",
        }

    source = clean_source(payload.get("source") or context.get("client"))
    review = store.record_module_event(
        event["module"],
        "module_review_marked",
        f"module review {status}: {event.get('title') or event_id}",
        {
            "eventId": event_id,
            "status": status,
            "note": note,
            "originalEvent": event,
        },
        source,
    )
    return {
        "ok": True,
        "action": "platform.review.mark",
        "module": event["module"],
        "event": event,
        "review": review,
        "message": "已标记待审核事件。",
    }


@register_handler("platform.today.context")
def platform_today_context_handler(payload: dict, context: dict) -> dict:
    """Read-only cross-module context for the home page and assistant."""
    target_date = clean_date(payload.get("date"))
    limit = clamp(payload.get("limit") or 5, 1, 20)
    schedule = store.schedule_summary(target_date)
    conflicts = detect_schedule_conflicts({"date": target_date}, context)["conflicts"]
    fitness = store.nutrition_summary(target_date)
    news = news_recommend_handler({"limit": limit}, context)
    leisure_window = _leisure_availability_from_schedule(schedule, conflicts)
    fitness_load = _fitness_load_context(target_date)
    workout = fitness_recommend_workout({"date": target_date, **leisure_window}, context)
    leisure = leisure_recommend_handler(
        {"limit": min(limit, 3), **leisure_window, "fitnessLoad": fitness_load},
        context,
    )
    recent_runs = store.list_module_runs("", limit)
    context_payload = {
        "date": target_date,
        "schedule": {
            "eventCount": len(schedule["events"]),
            "todoCount": len(schedule["todos"]),
            "conflictCount": len(conflicts),
            "events": schedule["events"][:limit],
            "todos": schedule["todos"][:limit],
        },
        "fitness": {
            "mealCount": fitness["count"],
            "calories": fitness["calories"],
            "proteinG": fitness["proteinG"],
            "recentWorkoutCount": fitness_load["recentWorkoutCount"],
            "recentWorkoutMinutes": fitness_load["recentWorkoutMinutes"],
            "recoveryRecommended": fitness_load["recoveryRecommended"],
            "workoutRecommendations": workout["recommendations"],
        },
        "news": {
            "count": news["count"],
            "items": news["items"][:limit],
            "personalized": news["personalized"],
        },
        "leisure": {
            "count": leisure["count"],
            "groups": leisure["groups"],
            "personalized": leisure["personalized"],
            "context": leisure["context"],
        },
        "recentRuns": recent_runs,
    }
    if not _is_read_only(context):
        store.record_module_event(
            "platform",
            "today_context",
            "platform today context read",
            {"date": target_date, "limit": limit},
            context.get("client") or context.get("source") or "api",
        )
    return {
        "ok": True,
        "action": "platform.today.context",
        "module": "platform",
        "context": context_payload,
        "message": f"返回 {target_date} 的跨模块上下文。",
    }


@register_handler("platform.modules.status")
def platform_modules_status_handler(payload: dict, context: dict) -> dict:
    """Return an operational status summary for all Niu Secretary modules."""
    limit = clamp(payload.get("limit") or 1, 1, 5)
    modules = ["news", "fitness", "schedule", "leisure", "airesearch", "platform", "profile"]
    capability_counts = {module: 0 for module in modules}
    for capability in CAPABILITIES:
        module = capability.get("module") or ""
        capability_counts[module] = capability_counts.get(module, 0) + 1

    items = []
    for module in modules:
        runs = store.list_module_run_summaries(module, limit)
        events = store.list_module_events(module, "", limit)
        cron_runs = store.list_module_run_summaries(module, limit, source="cron")
        status = "unknown"
        if runs:
            status = runs[0]["status"]
        items.append(
            {
                "module": module,
                "capabilityCount": capability_counts.get(module, 0),
                "lastRun": runs[0] if runs else None,
                "lastCronRun": cron_runs[0] if cron_runs else None,
                "lastEvent": events[0] if events else None,
            }
            | {"status": status}
        )
    return {
        "ok": True,
        "action": "platform.modules.status",
        "module": "platform",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 个模块状态。",
    }


_OPS_CENTER_INTERNAL_ACTIONS = {
    "platform.ops.center",
    "platform.review.mark",
    "platform.today.context",
    "platform.modules.status",
    "platform.runs.list",
    "platform.events.list",
}


def _pending_work_item_sort_key(item: dict) -> tuple[str, str]:
    return (item.get("createdAt") or "", item.get("id") or "")


def _resolved_pending_review_ids() -> set[str]:
    resolved = {
        (item.get("payload") or {}).get("eventId")
        for item in store.list_module_events("", "module_review_marked", 500)
    }
    resolved.update(
        {
            (item.get("payload") or {}).get("suggestionEventId")
            for item in store.list_module_events("leisure", "profile_suggestion_applied", 500)
        }
    )
    return {item for item in resolved if item}


def _filter_open_pending_reviews(pending_reviews: list[dict]) -> list[dict]:
    resolved_ids = _resolved_pending_review_ids()
    return [event for event in pending_reviews if event["id"] not in resolved_ids]


def _build_pending_work_items(module: str, pending_reviews: list[dict], pending_profile_changes: list[dict], limit: int) -> list[dict]:
    """Build a cross-module review queue from existing audited pending sources."""
    items: list[dict] = []
    for change in pending_profile_changes:
        items.append(
            {
                "id": f"profile:{change['id']}",
                "kind": "profile_change",
                "module": change["module"],
                "title": change.get("summary") or f"{change['field']} 画像变更",
                "detail": f"{change.get('field') or 'field'}: {change.get('oldValue')} -> {change.get('newValue')}",
                "sourceId": change["id"],
                "source": change.get("source") or "action",
                "createdAt": change.get("createdAt") or "",
                "requiresReview": True,
                "primaryAction": {
                    "action": "profile.change.review",
                    "label": "标记处理",
                    "input": {"changeId": change["id"]},
                    "confirm": False,
                },
                "secondaryAction": None
                if change.get("field") == "*"
                else {
                    "action": "profile.change.revert",
                    "label": "回滚字段",
                    "input": {"changeId": change["id"]},
                    "confirm": True,
                    "danger": True,
                },
            }
        )
    for event in pending_reviews:
        payload = event.get("payload") or {}
        if event["module"] == "leisure" and event["eventType"] == "profile_suggestion":
            items.append(
                {
                    "id": f"review:{event['id']}",
                    "kind": "leisure_profile_suggestion",
                    "module": event["module"],
                    "title": event.get("title") or "闲趣画像建议",
                    "detail": payload.get("summary") or payload.get("reason") or event.get("eventType") or "",
                    "sourceId": event["id"],
                    "source": event.get("source") or "system",
                    "createdAt": event.get("occurredAt") or "",
                    "requiresReview": True,
                    "primaryAction": {
                        "action": "leisure.profile.apply_suggestion",
                        "label": "应用建议",
                        "input": {"eventId": event["id"]},
                        "confirm": True,
                    },
                    "secondaryAction": None,
                }
            )
            continue
        items.append(
            {
                "id": f"review:{event['id']}",
                "kind": "module_review",
                "module": event["module"],
                "title": event.get("title") or event.get("eventType") or "待审核事件",
                "detail": event.get("eventType") or "",
                "sourceId": event["id"],
                "source": event.get("source") or "system",
                "createdAt": event.get("occurredAt") or "",
                "requiresReview": bool(event.get("requiresReview")),
                "primaryAction": {
                    "action": "platform.review.mark",
                    "label": "标记处理",
                    "input": {"eventId": event["id"], "status": "handled"},
                    "confirm": False,
                },
                "secondaryAction": None,
            }
        )
    if module:
        items = [item for item in items if item.get("module") == module]
    items.sort(key=_pending_work_item_sort_key, reverse=True)
    return items[:limit]


@register_handler("platform.ops.center")
def platform_ops_center_handler(payload: dict, context: dict) -> dict:
    """Return a compact operations center payload for the Web platform console."""
    module = _validate_optional_module(payload.get("module"))
    status = clean_text(payload.get("status"), 40, allow_empty=True).lower()
    limit = clamp(payload.get("limit") or 20, 1, 100)
    requires_review = None
    if payload.get("requiresReview") is not None:
        requires_review = bool(payload.get("requiresReview"))

    modules = platform_modules_status_handler({"limit": 1}, context)["items"]
    runs = store.list_module_run_summaries(
        module,
        limit,
        status=status,
        exclude_run_types=tuple(_OPS_CENTER_INTERNAL_ACTIONS),
    )
    events = store.list_module_events(module, "", limit, requires_review)
    pending_reviews = _filter_open_pending_reviews(store.list_module_events(module, "", limit, True))
    assistant_actions = store.list_assistant_action_summaries(
        module,
        status,
        limit,
        exclude_actions=tuple(_OPS_CENTER_INTERNAL_ACTIONS),
    )
    model_calls = store.list_model_call_summaries(module, status, limit)
    profile_module = module if module in store.PROFILE_MODULES else ""
    profile_changes = store.list_profile_changes(profile_module, min(limit, 50))
    pending_profile_changes = [item for item in profile_changes if not item.get("reviewed")]
    pending_work_items = _build_pending_work_items(module, pending_reviews, pending_profile_changes, limit)
    run_status_counts = store.count_module_runs_by_status(module)

    return {
        "ok": True,
        "action": "platform.ops.center",
        "module": module or "platform",
        "filters": {
            "module": module,
            "status": status,
            "requiresReview": requires_review,
            "limit": limit,
        },
        "summary": {
            "moduleCount": len(modules),
            "runStatusCounts": run_status_counts,
            "pendingReviewCount": len(pending_reviews),
            "recentRunCount": len(runs),
            "recentEventCount": len(events),
            "assistantActionCount": len(assistant_actions),
            "modelCallCount": len(model_calls),
            "profileChangeCount": len(profile_changes),
            "pendingProfileChangeCount": len(pending_profile_changes),
            "pendingWorkItemCount": len(pending_work_items),
        },
        "modules": modules,
        "runs": runs,
        "events": events,
        "pendingWorkItems": pending_work_items,
        "pendingReviews": pending_reviews,
        "assistantActions": assistant_actions,
        "modelCalls": model_calls,
        "profileChanges": profile_changes,
        "pendingProfileChanges": pending_profile_changes,
        "message": "返回平台运行中心摘要。",
    }


@register_handler("platform.cron.registry")
def platform_cron_registry_handler(payload: dict, context: dict) -> dict:
    """Return the cron job/group registry without executing any jobs."""
    from niu_secretary.cron import cron_registry

    registry = cron_registry()
    return {
        "ok": True,
        "action": "platform.cron.registry",
        "module": "platform",
        "jobs": registry["jobs"],
        "groups": registry["groups"],
        "message": "返回统一 Cron 任务注册表。",
    }


# ============================================================================
# Recommendation Actions (画像驱动推送)
# ============================================================================

@register_handler("fitness.recommend")
def fitness_recommend_handler(payload: dict, context: dict) -> dict:
    """Generate today's fitness suggestions from the profile."""
    target_date = clean_optional_date(payload.get("date")) or date.today().isoformat()
    profile = store.get_profile("fitness")["profile"]
    summary = store.nutrition_summary(target_date)
    tips = _build_fitness_tips(profile, summary)
    recommendation = None
    if not _is_read_only(context):
        recommendation = store.record_fitness_recommendation(
            target_date,
            "meal",
            tips,
            {"summary": summary, "profile": profile},
            clean_source(payload.get("source") or context.get("client")),
        )
    return {
        "ok": True,
        "action": "fitness.recommend",
        "module": "fitness",
        "date": target_date,
        "profile": profile,
        "summary": summary,
        "recommendations": tips,
        "recommendationRecord": recommendation,
        "message": f"为你生成了 {len(tips)} 条今日塑形建议。",
    }


def _build_fitness_tips(profile: dict, summary: dict) -> list[str]:
    tips: list[str] = []
    goal = profile.get("goal") or "maintain"
    goal_label = {
        "fat_loss": "减脂",
        "muscle_gain": "增肌",
        "recomp": "身体重组",
        "maintain": "维持",
    }.get(goal, goal)
    target_cal = int(profile.get("targetCalories") or 0)
    eaten = int(summary.get("calories") or 0)
    if target_cal > 0:
        remaining = target_cal - eaten
        if goal == "fat_loss" and remaining < 0:
            tips.append(f"今日热量已超出目标 {abs(remaining)} 千卡，晚餐建议以蛋白质+蔬菜为主。")
        else:
            tips.append(f"目标{goal_label}：今日还有 {max(remaining, 0)} 千卡预算。")
    else:
        tips.append(f"目标{goal_label}。设定一个每日热量目标后，我能给你更精准的饮食建议。")
    protein_target = int(profile.get("proteinTarget") or 0)
    if protein_target > 0:
        tips.append(f"蛋白质目标 {protein_target}g，优先选鸡胸/鱼类/豆制品/低脂乳制品。")
    diet_style = profile.get("dietStyle")
    if diet_style:
        tips.append(f"口味偏好：{diet_style}，可在此基础上控油控糖。")
    restrictions = profile.get("restrictions") or []
    if restrictions:
        tips.append(f"避开：{ '、'.join(restrictions) }。")
    return tips


@register_handler("schedule.recommend")
def schedule_recommend_handler(payload: dict, context: dict) -> dict:
    """Generate today's schedule suggestions from the profile."""
    target_date = clean_optional_date(payload.get("date")) or date.today().isoformat()
    profile = store.get_profile("schedule")["profile"]
    summary = store.schedule_summary(target_date)
    tips = _build_schedule_tips(profile, summary)
    return {
        "ok": True,
        "action": "schedule.recommend",
        "module": "schedule",
        "date": target_date,
        "profile": profile,
        "summary": summary,
        "recommendations": tips,
        "message": f"为你生成了 {len(tips)} 条今日日程建议。",
    }


def _build_schedule_tips(profile: dict, summary: dict) -> list[str]:
    tips: list[str] = []
    events = summary.get("events") or []
    todos = [t for t in (summary.get("todos") or []) if not t.get("done")]
    work_hours = profile.get("workHours")
    if work_hours:
        tips.append(f"工作时段 {work_hours}，今日共 {len(events)} 个日程、{len(todos)} 个待办。")
    else:
        tips.append(f"今日共 {len(events)} 个日程、{len(todos)} 个待办。")
    focus_blocks = profile.get("focusBlocks") or []
    for block in focus_blocks[:3]:
        tips.append(f"专注安排：{block}。")
    priorities = profile.get("priorities") or []
    if priorities:
        tips.append(f"优先事项：{ '、'.join(priorities[:3]) }，建议今日推进。")
    reminder_style = profile.get("reminderStyle")
    if reminder_style and events:
        tips.append(f"提醒偏好：{reminder_style}。")
    return tips


@register_handler("schedule.task_history.list")
def list_schedule_task_history_handler(payload: dict, context: dict) -> dict:
    """Read todo completion/reschedule history."""
    todo_id = clean_text(payload.get("todoId") or payload.get("id"), 120, allow_empty=True)
    items = store.list_schedule_task_history(todo_id, clamp(payload.get("limit") or 50, 1, 500))
    return {
        "ok": True,
        "action": "schedule.task_history.list",
        "module": "schedule",
        "todoId": todo_id,
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条时务局任务历史。",
    }


# ============================================================================
# News recommendation (画像驱动新闻精选)
# ============================================================================

# section id -> 中文板块名（与 news-daily 栏目对应）
_NEWS_SECTIONS = {
    "domestic": "国内要闻",
    "international": "国际焦点",
    "finance": "财经快讯",
    "tech": "科技动态",
    "ai": "人工智能",
}

_NEWS_CARD_BLOCK_RE = re.compile(r'<div class="news-card">(?P<body>.*?)</div>\s*</a>', re.DOTALL)
_NEWS_TAG_RE = re.compile(r'<span class="tag[^"]*">(?P<tag>.*?)</span>', re.DOTALL)
_NEWS_TITLE_RE = re.compile(r"<h3>(?P<title>.*?)</h3>", re.DOTALL)
_NEWS_SUMMARY_RE = re.compile(r'<p class="card-summary">(?P<summary>.*?)</p>', re.DOTALL)


def _strip_html(raw: str) -> str:
    """Remove tags/emoji-safe text and collapse whitespace."""
    text = re.sub(r"<[^>]+>", "", raw or "")
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _load_news_cards() -> list[dict]:
    """Parse today's news cards from news-daily section HTML. Read-only, best-effort."""
    cards: list[dict] = []
    sections_dir = store.PROJECT_ROOT / "news-daily" / "dist" / "sections"
    for section_id, section_label in _NEWS_SECTIONS.items():
        path = sections_dir / f"{section_id}.html"
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for block in _NEWS_CARD_BLOCK_RE.finditer(content):
            body = block.group("body")
            tag = _NEWS_TAG_RE.search(body)
            title = _NEWS_TITLE_RE.search(body)
            summary = _NEWS_SUMMARY_RE.search(body)
            if not (tag and title and summary):
                continue
            cards.append(
                {
                    "section": section_id,
                    "sectionLabel": section_label,
                    "tag": _strip_html(tag.group("tag")),
                    "title": _strip_html(title.group("title")),
                    "summary": _strip_html(summary.group("summary")),
                }
            )
    return cards


def _load_news_items() -> list[dict]:
    """Read today's full news export, including detail HTML, images and source links."""
    try:
        payload = _load_news_payload()
        items = payload.get("items") or []
        if items:
            normalized = []
            for item in items:
                tags = item.get("tags") or []
                normalized.append(
                    {
                        **item,
                        "tag": item.get("tag") or (tags[0] if tags else ""),
                        "sectionLabel": item.get("sectionLabel") or item.get("sectionName") or "",
                    }
                )
            return normalized
    except Exception:
        # Keep the public recommendation endpoint available even if the export
        # helper is temporarily broken; the fallback returns summary cards only.
        pass
    return _load_news_cards()


def _score_news_card(card: dict, topics: list[str], exclude: list[str],
                     regions: list[str]) -> int:
    """Score a news card against the news profile. Negative => filtered out."""
    tags_text = " ".join(str(tag) for tag in (card.get("tags") or []))
    haystack = " ".join(
        [
            str(card.get("tag", "")),
            tags_text,
            str(card.get("title", "")),
            str(card.get("summary", "")),
            str(card.get("sectionLabel") or card.get("sectionName") or ""),
        ]
    ).lower()
    for term in exclude:
        term = str(term).strip().lower()
        if term and term in haystack:
            return -1
    score = 0
    for term in topics:
        term = str(term).strip().lower()
        if not term:
            continue
        if term in f"{card.get('tag', '')} {tags_text}".lower():
            score += 3
        if term in card.get("title", "").lower():
            score += 2
        if term in card.get("summary", "").lower():
            score += 1
    for term in regions:
        term = str(term).strip().lower()
        if term and term in haystack:
            score += 1
    return score


@register_handler("news.recommend")
def news_recommend_handler(payload: dict, context: dict) -> dict:
    """Pick today's news matching the news profile (topics/excludeTopics)."""
    limit = clamp(payload.get("limit") or 8, 1, 30)
    profile = store.get_profile("news")["profile"]
    research_profile = store.get_profile("airesearch")["profile"]
    research_terms = [
        t
        for t in (research_profile.get("topics") or []) + (research_profile.get("keywords") or [])
        if str(t).strip()
    ]
    topics = [t for t in (profile.get("topics") or []) if str(t).strip()]
    topics = list(dict.fromkeys([*topics, *research_terms]))
    exclude = [t for t in (profile.get("excludeTopics") or []) if str(t).strip()]
    regions = [r for r in (profile.get("regions") or []) if str(r).strip()]
    cards = _load_news_items()

    scored = []
    for card in cards:
        score = _score_news_card(card, topics, exclude, regions)
        if score < 0:
            continue
        scored.append((score, card))

    if topics:
        # Profile has interests: prefer matches, keep only scored>0 when any matched.
        matched = [item for item in scored if item[0] > 0]
        chosen = matched if matched else scored
        personalized = bool(matched)
    else:
        chosen = scored
        personalized = False

    chosen.sort(key=lambda item: item[0], reverse=True)
    items = [
        {**card, "matchScore": score}
        for score, card in chosen[:limit]
    ]
    if topics and personalized:
        msg = f"按你关注的「{ '、'.join(topics) }」精选了 {len(items)} 条今日新闻。"
    elif topics:
        msg = f"今日新闻里暂无完全匹配你关注话题的内容，先返回 {len(items)} 条要闻。"
    else:
        msg = f"返回今日要闻 {len(items)} 条。和牛秘书 AI 聊聊你关注的话题，就能个性化精选。"
    return {
        "ok": True,
        "action": "news.recommend",
        "module": "news",
        "profile": profile,
        "researchProfile": research_profile,
        "personalized": personalized,
        "items": items,
        "count": len(items),
        "message": msg,
    }


@register_handler("news.topic.queue-research")
def queue_news_topic_for_research(payload: dict, context: dict) -> dict:
    """Add a news topic into the AIResearch review queue."""
    topic = clean_text(payload.get("topic") or payload.get("title"), 240)
    source_url = clean_text(payload.get("url"), 500, allow_empty=True)
    note = clean_text(payload.get("note"), 1000, allow_empty=True)
    source = clean_source(payload.get("source") or context.get("client"))
    queued = airesearch_queue_add(
        {
            "title": topic,
            "url": source_url,
            "note": note or "from news topic",
            "source": source,
        },
        context,
    )
    event = store.record_module_event(
        "news",
        "research_queue",
        f"news topic queued for research: {topic}",
        {"topic": topic, "url": source_url, "researchEventId": queued["event"]["id"]},
        source,
        1.0,
        True,
    )
    return {
        "ok": True,
        "action": "news.topic.queue-research",
        "module": "news",
        "event": event,
        "researchEvent": queued["event"],
        "message": "已将新闻主题加入研知库候选队列。",
    }


@register_handler("news.search")
def news_search_handler(payload: dict, context: dict) -> dict:
    """Search archived news items from the news SQLite database."""
    query_text = clean_text(payload.get("q"), 120, allow_empty=True)
    target_date = clean_optional_date(payload.get("date"))
    date_from = clean_optional_date(payload.get("from"))
    date_to = clean_optional_date(payload.get("to"))
    section = clean_text(payload.get("section"), 80, allow_empty=True)
    tag = clean_text(payload.get("tag"), 80, allow_empty=True)
    source = clean_text(payload.get("source"), 120, allow_empty=True)
    limit = clamp(payload.get("limit") or 20, 1, 100)
    db_path = store.PROJECT_ROOT / "news-daily" / "news_daily.db"
    if not db_path.exists():
        raise ActionError(
            "not_found",
            "新闻社归档数据库不存在，请先运行 news archive。",
            404,
            {"path": str(db_path)},
        )

    conditions: list[str] = []
    params: list = []
    if query_text:
        query = f"%{query_text}%"
        conditions.append(
            """(
                ni.title LIKE ? OR ni.summary LIKE ? OR ni.section_name LIKE ? OR ni.source_name LIKE ?
                OR EXISTS (
                    SELECT 1 FROM news_tags nt
                    WHERE nt.date = ni.date AND nt.item_id = ni.item_id AND nt.tag LIKE ?
                )
            )"""
        )
        params.extend([query, query, query, query, query])
    if target_date:
        conditions.append("ni.date = ?")
        params.append(target_date)
    if date_from:
        conditions.append("ni.date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("ni.date <= ?")
        params.append(date_to)
    if section:
        conditions.append("(ni.section = ? OR ni.section_name LIKE ?)")
        params.extend([section, f"%{section}%"])
    if tag:
        conditions.append(
            """EXISTS (
                SELECT 1 FROM news_tags nt
                WHERE nt.date = ni.date AND nt.item_id = ni.item_id AND nt.tag LIKE ?
            )"""
        )
        params.append(f"%{tag}%")
    if source:
        conditions.append("(ni.source_name LIKE ? OR ni.source_url LIKE ?)")
        params.extend([f"%{source}%", f"%{source}%"])
    where_sql = " AND ".join(conditions) if conditions else "1 = 1"
    params.append(limit)
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT ni.date, ni.item_id, ni.open_id, ni.section, ni.section_name, ni.title, ni.summary,
                   ni.source_name, ni.source_url, ni.date_text, ni.image_path, ni.detail_html
            FROM news_items ni
            WHERE {where_sql}
            ORDER BY ni.date DESC, ni.item_order ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
        items = []
        for row in rows:
            tag_rows = connection.execute(
                "SELECT tag FROM news_tags WHERE date = ? AND item_id = ? ORDER BY tag",
                (row["date"], row["item_id"]),
            ).fetchall()
            items.append(
                {
                    "date": row["date"],
                    "id": row["item_id"],
                    "openId": row["open_id"],
                    "section": row["section"],
                    "sectionName": row["section_name"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "sourceName": row["source_name"],
                    "sourceUrl": row["source_url"],
                    "dateText": row["date_text"],
                    "imagePath": row["image_path"],
                    "detailHtml": row["detail_html"],
                    "tags": [tag_row["tag"] for tag_row in tag_rows],
                }
            )
    store.record_module_event(
        "news",
        "search",
        "news action search completed",
        {
            "query": query_text,
            "filters": {
                "date": target_date,
                "from": date_from,
                "to": date_to,
                "section": section,
                "tag": tag,
                "source": source,
            },
            "count": len(items),
            "source": context.get("client") or context.get("source") or "api",
        },
        "api",
    )
    return {
        "ok": True,
        "action": "news.search",
        "module": "news",
        "query": query_text,
        "filters": {
            "date": target_date,
            "from": date_from,
            "to": date_to,
            "section": section,
            "tag": tag,
            "source": source,
        },
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条新闻搜索结果。",
    }


def _news_tools_path() -> str:
    tools = str(store.PROJECT_ROOT / "news-daily" / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    return tools


def _load_news_payload() -> dict:
    _news_tools_path()
    from extract_news_json import build_news_json

    return build_news_json(store.PROJECT_ROOT / "news-daily" / "dist")


@register_handler("news.validate-sources")
def news_validate_sources(payload: dict, context: dict) -> dict:
    """Validate source URLs in the current news export."""
    _news_tools_path()
    from news_daily_validate import is_rejected_source_url

    news = _load_news_payload()
    errors = []
    for item in news.get("items", []):
        ident = item.get("id") or "<missing-id>"
        source_url = item.get("sourceUrl") or ""
        if not source_url:
            errors.append(f"{ident}: missing sourceUrl")
        elif is_rejected_source_url(source_url):
            errors.append(f"{ident}: rejected sourceUrl {source_url}")
    status = "passed" if not errors else "blocked"
    store.record_module_event(
        "news",
        "validate_sources",
        f"news validate-sources {status}",
        {"count": len(news.get("items", [])), "errors": errors},
        "api",
        1.0,
        bool(errors),
    )
    return {
        "ok": True,
        "action": "news.validate-sources",
        "status": status,
        "count": len(news.get("items", [])),
        "errors": errors,
        "message": f"新闻来源校验{status}，发现 {len(errors)} 个问题。",
    }


@register_handler("news.validate-keypoints")
def news_validate_keypoints(payload: dict, context: dict) -> dict:
    """Validate that detail pages contain structured summary material."""
    news = _load_news_payload()
    errors = []
    for item in news.get("items", []):
        ident = item.get("id") or "<missing-id>"
        detail = item.get("detailHtml") or ""
        paragraphs = re.findall(r"<p\b", detail)
        if not item.get("tags"):
            errors.append(f"{ident}: missing tags")
        if "<h2" not in detail:
            errors.append(f"{ident}: missing detail h2")
        if len(paragraphs) < 2:
            errors.append(f"{ident}: detail has fewer than 2 paragraphs")
    status = "passed" if not errors else "blocked"
    store.record_module_event(
        "news",
        "validate_keypoints",
        f"news validate-keypoints {status}",
        {"count": len(news.get("items", [])), "errors": errors},
        "api",
        1.0,
        bool(errors),
    )
    return {
        "ok": True,
        "action": "news.validate-keypoints",
        "status": status,
        "count": len(news.get("items", [])),
        "errors": errors,
        "message": f"新闻详情要点校验{status}，发现 {len(errors)} 个问题。",
    }


@register_handler("news.audit-images")
def news_audit_images(payload: dict, context: dict) -> dict:
    """Audit current news image paths and archived image candidate coverage."""
    news = _load_news_payload()
    missing = []
    invalid_paths = []
    dist = store.PROJECT_ROOT / "news-daily" / "dist"
    for item in news.get("items", []):
        image_path = item.get("imagePath") or ""
        if not image_path:
            missing.append(item.get("id") or "<missing-id>")
            continue
        if not (dist / image_path).exists():
            invalid_paths.append({"id": item.get("id") or "", "imagePath": image_path})

    candidate_rows = 0
    db_path = store.PROJECT_ROOT / "news-daily" / "news_daily.db"
    if db_path.exists():
        with sqlite3.connect(db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='image_candidates'"
            ).fetchone()
            if row and row[0]:
                candidate_rows = connection.execute("SELECT COUNT(*) FROM image_candidates").fetchone()[0]
    status = "passed" if not invalid_paths else "blocked"
    store.record_module_event(
        "news",
        "audit_images",
        f"news audit-images {status}",
        {
            "count": len(news.get("items", [])),
            "missing": missing,
            "invalidPaths": invalid_paths,
            "candidateRows": candidate_rows,
        },
        "api",
        1.0,
        bool(invalid_paths),
    )
    return {
        "ok": True,
        "action": "news.audit-images",
        "status": status,
        "count": len(news.get("items", [])),
        "missingCount": len(missing),
        "invalidPaths": invalid_paths,
        "candidateRows": candidate_rows,
        "message": f"新闻配图审计{status}，缺图 {len(missing)} 条，路径错误 {len(invalid_paths)} 条。",
    }


# ============================================================================
# Leisure recommendation (画像驱动闲趣精选)
# ============================================================================

# leisure profile genres key -> (data file, content type label)
_LEISURE_CATEGORIES = (
    ("movie", "movies.json", "影视"),
    ("music", "music.json", "音乐"),
    ("podcast", "podcasts.json", "播客"),
    ("novel", "novels.json", "小说"),
)


def _load_leisure_items(filename: str) -> list[dict]:
    """Load a leisure data file. Handles both list and {items:[...]} shapes."""
    path = store.PROJECT_ROOT / "leisure" / "dist" / "data" / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("items") or []
    return data if isinstance(data, list) else []


def _item_genres(item: dict) -> list[str]:
    """Normalize an item's genres to a list (handles 'genres' list or 'genre' str)."""
    genres = item.get("genres")
    if isinstance(genres, list):
        return [str(g) for g in genres]
    single = item.get("genre")
    return [str(single)] if single else []


def _score_leisure_item(item: dict, want_genres: list[str], moods: list[str],
                        avoid: list[str]) -> int:
    """Score a leisure item against the leisure profile. Negative => filtered out."""
    item_genres = [g.lower() for g in _item_genres(item)]
    item_mood = str(item.get("mood") or "").lower()
    for term in avoid:
        term = str(term).strip().lower()
        if term and (term in item_genres or term == item_mood):
            return -1
    score = 0
    for term in want_genres:
        term = str(term).strip().lower()
        if term and term in item_genres:
            score += 3
    for term in moods:
        term = str(term).strip().lower()
        if term and term == item_mood:
            score += 2
    # Use baked-in matchScore as a gentle tiebreaker (0-100 -> 0-1 bucket).
    score += int(item.get("matchScore") or 0) // 50
    return score


def _estimate_leisure_minutes(item: dict) -> int:
    """Best-effort duration estimate for schedule-aware leisure ranking."""
    raw = str(item.get("duration") or item.get("runtime") or "").strip()
    if not raw:
        return 0
    numbers = [int(value) for value in re.findall(r"\d+", raw)]
    if not numbers:
        return 0
    if "集" in raw and "分钟" not in raw:
        return 45
    if "小时" in raw:
        return max(numbers) * 60
    return max(numbers)


def _leisure_availability_from_schedule(schedule: dict, conflicts: list[dict]) -> dict:
    """Derive a conservative leisure window from today's schedule load."""
    load = len(schedule.get("events") or []) + len(schedule.get("todos") or []) + len(conflicts)
    if load >= 5:
        minutes = 30
        label = "compact"
    elif load >= 3:
        minutes = 60
        label = "moderate"
    else:
        minutes = 120
        label = "open"
    return {"availableMinutes": minutes, "scheduleLoad": load, "label": label}


def _fitness_load_context(target_date: str) -> dict:
    """Summarize recent training load for cross-module recommendation context."""
    end = date.fromisoformat(target_date)
    start = (end - timedelta(days=6)).isoformat()
    workouts = store.list_workout_logs(start, target_date, 100)
    minutes = sum(item["durationMin"] for item in workouts)
    return {
        "recentWorkoutCount": len(workouts),
        "recentWorkoutMinutes": minutes,
        "recoveryRecommended": minutes >= 180,
    }


@register_handler("leisure.recommend")
def leisure_recommend_handler(payload: dict, context: dict) -> dict:
    """Pick leisure items matching the leisure profile (genres/moods/avoid)."""
    per_category = clamp(payload.get("limit") or 3, 1, 10)
    available_minutes = clamp(payload.get("availableMinutes") or payload.get("available_minutes") or 0, 0, 720)
    schedule_load = clamp(payload.get("scheduleLoad") or payload.get("schedule_load") or 0, 0, 100)
    fitness_load = payload.get("fitnessLoad") if isinstance(payload.get("fitnessLoad"), dict) else {}
    recovery_recommended = bool(payload.get("recoveryRecommended") or fitness_load.get("recoveryRecommended"))
    profile = store.get_profile("leisure")["profile"]
    genres_pref = profile.get("genres") or {}
    moods = [m for m in (profile.get("moods") or []) if str(m).strip()]
    mood_override = clean_text(payload.get("mood"), 80, allow_empty=True)
    if mood_override:
        moods = [mood_override, *[m for m in moods if m != mood_override]]
    avoid = [a for a in (profile.get("avoid") or []) if str(a).strip()]

    groups = []
    any_personalized = False
    for key, filename, label in _LEISURE_CATEGORIES:
        items = _load_leisure_items(filename)
        if not items:
            continue
        want = genres_pref.get(key) or [] if isinstance(genres_pref, dict) else []
        want = [g for g in want if str(g).strip()]
        scored = []
        for item in items:
            score = _score_leisure_item(item, want, moods, avoid)
            if score < 0:
                continue
            duration_minutes = _estimate_leisure_minutes(item)
            if available_minutes and duration_minutes:
                if duration_minutes <= available_minutes + 15:
                    score += 1
                elif duration_minutes > available_minutes * 2:
                    score -= 2
            if recovery_recommended:
                light_haystack = " ".join(
                    [
                        str(item.get("mood") or ""),
                        str(item.get("reason") or ""),
                        " ".join(_item_genres(item)),
                    ]
                )
                if duration_minutes and duration_minutes <= 60:
                    score += 1
                if any(term in light_haystack for term in ("放松", "轻", "舒缓", "专注", "沉思", "疗愈")):
                    score += 1
            scored.append((score, item))
        matched = [s for s in scored if s[0] > 0]
        chosen = matched if matched else scored
        if (want or moods) and matched:
            any_personalized = True
        chosen.sort(key=lambda s: s[0], reverse=True)
        picked = [
            {
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "genres": _item_genres(item),
                "mood": item.get("mood", ""),
                "reason": item.get("reason", ""),
                "duration": item.get("duration", ""),
                "durationMinutes": _estimate_leisure_minutes(item),
                "matchScore": item.get("matchScore", score),
                "url": item.get("doubanUrl") or item.get("platformUrl") or "",
            }
            for score, item in chosen[:per_category]
        ]
        if picked:
            if not _is_read_only(context):
                for item in picked:
                    store.upsert_leisure_item(
                        item["id"] or f"{key}:{item['title']}",
                        key,
                        item["title"],
                        item,
                        clean_source(payload.get("source") or context.get("client")),
                    )
            groups.append({"category": key, "label": label, "items": picked})

    total = sum(len(g["items"]) for g in groups)
    context_payload = {
        "availableMinutes": available_minutes,
        "scheduleLoad": schedule_load,
        "mood": mood_override,
        "fitnessLoad": fitness_load,
        "recoveryRecommended": recovery_recommended,
    }
    recommendation = None
    if not _is_read_only(context):
        recommendation = store.record_leisure_recommendation(
            clean_optional_date(payload.get("date")) or date.today().isoformat(),
            groups,
            context_payload | {"personalized": any_personalized},
            clean_source(payload.get("source") or context.get("client")),
        )
    if any_personalized:
        msg = f"按你的口味档案精选了 {total} 条闲趣推荐。"
    elif total:
        msg = f"返回 {total} 条闲趣推荐。和牛秘书 AI 聊聊你爱看/爱听的，就能个性化精选。"
    else:
        msg = "暂无可推荐的闲趣内容。"
    return {
        "ok": True,
        "action": "leisure.recommend",
        "module": "leisure",
        "profile": profile,
        "personalized": any_personalized,
        "context": context_payload,
        "groups": groups,
        "count": total,
        "recommendationRecord": recommendation,
        "message": msg,
    }


@register_handler("leisure.recommendations.list")
def list_leisure_recommendations_handler(payload: dict, context: dict) -> dict:
    """Read persisted leisure recommendation history."""
    target_date = clean_optional_date(payload.get("date"))
    items = store.list_leisure_recommendations(
        target_date,
        clamp(payload.get("limit") or 50, 1, 500),
    )
    return {
        "ok": True,
        "action": "leisure.recommendations.list",
        "module": "leisure",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条闲趣推荐历史。",
    }


@register_handler("leisure.items.list")
def list_leisure_items_handler(payload: dict, context: dict) -> dict:
    """Read persisted leisure items saved from recommendations or feedback."""
    category = clean_text(payload.get("category"), 80, allow_empty=True)
    items = store.list_leisure_items(category, clamp(payload.get("limit") or 100, 1, 500))
    return {
        "ok": True,
        "action": "leisure.items.list",
        "module": "leisure",
        "category": category,
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条闲趣集条目。",
    }


@register_handler("leisure.item.update")
def update_leisure_item_handler(payload: dict, context: dict) -> dict:
    """Update a persisted leisure item by id."""
    item_id = clean_text(payload.get("itemId") or payload.get("id"), 120)
    patch = {}
    if "category" in payload:
        patch["category"] = clean_choice(payload.get("category"), {"movie", "music", "podcast", "novel"}, "movie")
    if "title" in payload:
        patch["title"] = clean_text(payload.get("title"), 200)
    if "payload" in payload:
        if not isinstance(payload.get("payload"), dict):
            raise ActionError("validation_failed", "payload 必须是对象。", 400, {"field": "payload"})
        patch["payload"] = payload.get("payload") or {}
    if not patch:
        raise ActionError("validation_failed", "至少需要提供一个可更新字段。", 400, {"itemId": item_id})
    source = clean_source(payload.get("source") or context.get("client"))
    patch["source"] = source
    before = store.get_leisure_item(item_id)
    record = store.update_leisure_item(item_id, patch)
    if not record:
        raise ActionError("not_found", "未找到该闲趣条目。", 404, {"itemId": item_id})
    changed_fields = sorted(patch.keys() - {"source"})
    event = store.record_module_event(
        "leisure",
        "item_updated",
        f"leisure item updated: {record['title']}",
        {"itemId": item_id, "before": before, "after": record, "changedFields": changed_fields},
        source,
    )
    return {
        "ok": True,
        "action": "leisure.item.update",
        "module": "leisure",
        "record": record,
        "event": event,
        "message": f"已更新闲趣条目：{record['title']}。",
    }


@register_handler("leisure.item.delete")
def delete_leisure_item_handler(payload: dict, context: dict) -> dict:
    """Delete a persisted leisure item by id."""
    item_id = clean_text(payload.get("itemId") or payload.get("id"), 120)
    record = store.delete_leisure_item(item_id)
    if not record:
        raise ActionError("not_found", "未找到该闲趣条目。", 404, {"itemId": item_id})
    source = clean_source(payload.get("source") or context.get("client"))
    event = store.record_module_event(
        "leisure",
        "item_deleted",
        f"leisure item deleted: {record['title']}",
        {"itemId": item_id, "record": record},
        source,
    )
    return {
        "ok": True,
        "action": "leisure.item.delete",
        "module": "leisure",
        "itemId": item_id,
        "record": record,
        "event": event,
        "message": "已删除该闲趣条目。",
    }


@register_handler("leisure.profile.update")
def leisure_profile_update_handler(payload: dict, context: dict) -> dict:
    """Compatibility action for updating the leisure profile."""
    return update_profile_handler(
        {
            "module": "leisure",
            "patch": payload.get("patch"),
            "summary": payload.get("summary") or "leisure profile update",
            "source": payload.get("source") or context.get("client"),
        },
        context,
    ) | {"action": "leisure.profile.update"}


def _unique_preserve_order(values: list) -> list:
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _leisure_profile_patch_from_feedback(record: dict) -> dict:
    payload = record.get("payload") or {}
    interaction = record["interaction"]
    rating = int(record.get("rating") or 0)
    category = record["category"]
    profile = store.get_profile("leisure")["profile"]
    patch: dict = {}

    if interaction == "dismiss" or (interaction == "rate" and rating <= 2):
        avoid = _unique_preserve_order([*(profile.get("avoid") or []), record["title"]])
        patch["avoid"] = avoid[:30]
        return patch

    if interaction == "save" or rating >= 4:
        genres = profile.get("genres") or {}
        if not isinstance(genres, dict):
            genres = {}
        item_genres = payload.get("genres")
        if not isinstance(item_genres, list) or not item_genres:
            item_genres = payload.get("tags") if isinstance(payload.get("tags"), list) else []
        if item_genres:
            patch["genres"] = {
                **genres,
                category: _unique_preserve_order([*(genres.get(category) or []), *item_genres])[:20],
            }
        mood = clean_text(payload.get("mood"), 80, allow_empty=True)
        if mood:
            patch["moods"] = _unique_preserve_order([*(profile.get("moods") or []), mood])[:20]
    return patch


def _record_leisure_profile_suggestion(record: dict, source: str) -> dict | None:
    patch = _leisure_profile_patch_from_feedback(record)
    if not patch:
        return None
    event = store.record_module_event(
        "leisure",
        "profile_suggestion",
        f"leisure profile suggestion: {record['title']}",
        {
            "action": "leisure.profile.update",
            "module": "leisure",
            "patch": patch,
            "summary": f"根据「{record['title']}」的{record['interaction']}反馈调整闲趣画像",
            "sourceInteractionId": record["id"],
            "item": {
                "itemId": record["itemId"],
                "category": record["category"],
                "title": record["title"],
                "interaction": record["interaction"],
                "rating": record["rating"],
            },
            "status": "pending",
        },
        source,
        confidence=0.7,
        requires_review=True,
    )
    return event


def _record_leisure_feedback(payload: dict, context: dict, interaction: str) -> dict:
    category = clean_choice(payload.get("category"), {"movie", "music", "podcast", "novel"}, "movie")
    item_id = clean_text(payload.get("itemId"), 120)
    title = clean_text(payload.get("title"), 200)
    source = clean_source(payload.get("source") or context.get("client"))
    store.upsert_leisure_item(
        item_id,
        category,
        title,
        {"feedback": interaction},
        source,
    )
    record = store.record_leisure_interaction(
        {
            "itemId": item_id,
            "category": category,
            "title": title,
            "interaction": interaction,
            "rating": clamp(payload.get("rating") or 0, 0, 5),
            "note": clean_text(payload.get("note"), 500, allow_empty=True),
            "payload": payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
            "source": source,
        }
    )
    suggestion = _record_leisure_profile_suggestion(record, source)
    store.record_module_event(
        "leisure",
        interaction,
        f"leisure item {interaction}: {record['title']}",
        {
            "id": record["id"],
            "itemId": record["itemId"],
            "category": record["category"],
            "profileSuggestionId": suggestion["id"] if suggestion else "",
        },
        source,
    )
    if suggestion:
        record["profileSuggestion"] = suggestion
    return record


@register_handler("leisure.item.save")
def save_leisure_item(payload: dict, context: dict) -> dict:
    record = _record_leisure_feedback(payload, context, "save")
    return {"ok": True, "action": "leisure.item.save", "record": record, "message": "已收藏该闲趣条目。"}


@register_handler("leisure.item.dismiss")
def dismiss_leisure_item(payload: dict, context: dict) -> dict:
    record = _record_leisure_feedback(payload, context, "dismiss")
    return {"ok": True, "action": "leisure.item.dismiss", "record": record, "message": "已记录忽略反馈。"}


@register_handler("leisure.item.rate")
def rate_leisure_item(payload: dict, context: dict) -> dict:
    if payload.get("rating") is None:
        raise ActionError("validation_failed", "rating 不能为空。", 400, {"field": "rating"})
    record = _record_leisure_feedback(payload, context, "rate")
    return {"ok": True, "action": "leisure.item.rate", "record": record, "message": "已记录评分反馈。"}


@register_handler("leisure.history.search")
def search_leisure_history(payload: dict, context: dict) -> dict:
    items = store.list_leisure_interactions(
        clean_text(payload.get("category"), 40, allow_empty=True),
        clean_text(payload.get("itemId"), 120, allow_empty=True),
        clean_text(payload.get("q"), 120, allow_empty=True),
        clamp(payload.get("limit") or 50, 1, 500),
    )
    return {
        "ok": True,
        "action": "leisure.history.search",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条闲趣互动历史。",
    }


@register_handler("leisure.profile.suggestions")
def leisure_profile_suggestions_handler(payload: dict, context: dict) -> dict:
    """List pending reviewable profile suggestions generated from leisure feedback."""
    suggestions = store.list_module_events(
        "leisure",
        "profile_suggestion",
        clamp(payload.get("limit") or 50, 1, 500),
        True,
    )
    applied_ids = {
        (item.get("payload") or {}).get("suggestionEventId")
        for item in store.list_module_events("leisure", "profile_suggestion_applied", 500)
    }
    items = [item for item in suggestions if item["id"] not in applied_ids]
    return {
        "ok": True,
        "action": "leisure.profile.suggestions",
        "module": "leisure",
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 条待审核闲趣画像建议。",
    }


@register_handler("leisure.profile.apply_suggestion")
def leisure_profile_apply_suggestion_handler(payload: dict, context: dict) -> dict:
    """Apply a previously generated leisure profile suggestion."""
    event_id = clean_text(payload.get("eventId"), 120)
    event = store.get_module_event(event_id)
    if not event or event["module"] != "leisure" or event["eventType"] != "profile_suggestion":
        raise ActionError("not_found", "未找到该闲趣画像建议。", 404, {"eventId": event_id})
    event_payload = event.get("payload") or {}
    patch = event_payload.get("patch")
    if not isinstance(patch, dict) or not patch:
        raise ActionError("validation_failed", "画像建议缺少可应用的 patch。", 400, {"eventId": event_id})
    source = clean_source(payload.get("source") or context.get("client"))
    applied = update_profile_handler(
        {
            "module": "leisure",
            "patch": patch,
            "summary": event_payload.get("summary") or "apply leisure profile suggestion",
            "source": source,
        },
        context,
    )
    applied_event = store.record_module_event(
        "leisure",
        "profile_suggestion_applied",
        f"leisure profile suggestion applied: {event_id}",
        {
            "suggestionEventId": event_id,
            "changedFields": applied.get("changedFields", []),
            "patch": patch,
        },
        source,
    )
    return {
        "ok": True,
        "action": "leisure.profile.apply_suggestion",
        "module": "leisure",
        "suggestion": event,
        "applied": applied,
        "event": applied_event,
        "message": "已应用闲趣画像建议。",
    }


def _airesearch_db_path():
    return store.PROJECT_ROOT / "airesearch" / "data" / "airesearch.sqlite3"


def _airesearch_paper_db_path():
    return store.PROJECT_ROOT / "airesearch" / "data" / "paperpipe"


def _airesearch_admin_module():
    src = store.PROJECT_ROOT / "airesearch" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from airesearch import admin_server
    except Exception as exc:  # pragma: no cover - surfaced as API error
        raise ActionError(
            "airesearch_admin_unavailable",
            "研知库管理模块不可用。",
            500,
            {"detail": str(exc)},
        ) from exc
    return admin_server


def _build_airesearch_admin_config(admin_server=None):
    admin_server = admin_server or _airesearch_admin_module()
    return admin_server.AdminConfig(
        base_path="/niu-secretary/airesearch/admin/",
        db_path=_airesearch_db_path(),
        paper_db_path=_airesearch_paper_db_path(),
        project_dir=store.PROJECT_ROOT / "airesearch",
        deploy_script=store.PROJECT_ROOT / "airesearch" / "deploy" / "deploy-airesearch.sh",
        papi_executable=os.environ.get("PAPI_EXECUTABLE") or str(store.PROJECT_ROOT / "airesearch" / ".venv" / "bin" / "papi"),
        username="",
        password="",
        layout_output_dir=Path(os.environ.get("AIRESEARCH_LAYOUT_OUTPUT_DIR", store.PROJECT_ROOT / "airesearch" / "data" / "layout")),
        layout_max_pages=(
            int(os.environ["AIRESEARCH_LAYOUT_MAX_PAGES"])
            if os.environ.get("AIRESEARCH_LAYOUT_MAX_PAGES", "").isdigit()
            else None
        ),
        layout_ocr_mode=os.environ.get("AIRESEARCH_LAYOUT_OCR_MODE", "auto"),
        layout_ocr_languages=os.environ.get("AIRESEARCH_LAYOUT_OCR_LANGUAGES", "eng+chi_sim"),
        layout_ocr_dpi=(
            int(os.environ["AIRESEARCH_LAYOUT_OCR_DPI"])
            if os.environ.get("AIRESEARCH_LAYOUT_OCR_DPI", "").isdigit()
            else 220
        ),
        layout_ocr_executable=os.environ.get("AIRESEARCH_LAYOUT_OCR_EXECUTABLE", "tesseract"),
        layout_formula_ocr_mode=os.environ.get("AIRESEARCH_FORMULA_OCR_MODE", "off"),
        layout_formula_ocr_dpi=(
            int(os.environ["AIRESEARCH_FORMULA_OCR_DPI"])
            if os.environ.get("AIRESEARCH_FORMULA_OCR_DPI", "").isdigit()
            else 260
        ),
        layout_formula_ocr_min_confidence=float(os.environ.get("AIRESEARCH_FORMULA_OCR_MIN_CONFIDENCE", "0.7")),
    )


def _ensure_airesearch_admin_runtime():
    admin_server = _airesearch_admin_module()
    config = _build_airesearch_admin_config(admin_server)
    runtime_key = str(config.db_path.resolve())
    if runtime_key not in _AIRESEARCH_ADMIN_RUNTIME_INITIALIZED:
        admin_server._mark_interrupted_jobs(config.db_path)
        admin_server._ensure_worker(config)
        _AIRESEARCH_ADMIN_RUNTIME_INITIALIZED.add(runtime_key)
    return admin_server, config


def _airesearch_admin_config():
    return _ensure_airesearch_admin_runtime()[1]


def _airesearch_admin_call(operation: str, callback, success_message: str) -> dict:
    try:
        result = callback()
    except KeyError as exc:
        raise ActionError("not_found", f"研知库记录不存在：{exc.args[0]}", 404) from exc
    except ValueError as exc:
        raise ActionError("invalid_request", str(exc), 400) from exc
    except RuntimeError as exc:
        raise ActionError("operation_failed", str(exc), 500) from exc
    return {
        "ok": True,
        "action": operation,
        "module": "airesearch",
        "result": result,
        "message": success_message,
    }


def _paper_key_from_payload(payload: dict) -> str:
    paper_key = clean_text(payload.get("paperKey") or payload.get("paper_key"), 300)
    return paper_key


def _relative_project_path(path) -> str:
    try:
        return str(path.relative_to(store.PROJECT_ROOT))
    except ValueError:
        return str(path)


def _file_snapshot(path) -> dict:
    if not path.exists():
        return {"found": False, "path": _relative_project_path(path)}
    stat = path.stat()
    return {
        "found": True,
        "path": _relative_project_path(path),
        "bytes": stat.st_size,
        "updatedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def _read_json_file(path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _airesearch_count_table(connection, tables: set[str], table: str) -> int:
    if table not in tables:
        return 0
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _airesearch_max_column(connection, tables: set[str], table: str, column: str) -> str:
    if table not in tables:
        return ""
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        return ""
    value = connection.execute(f"SELECT MAX({column}) FROM {table}").fetchone()[0]
    return str(value or "")


def _airesearch_database_summary(db_path) -> dict:
    summary = {"found": db_path.exists(), "path": _relative_project_path(db_path)}
    if not db_path.exists():
        return summary | {
            "paperCount": 0,
            "factCount": 0,
            "candidateCount": 0,
            "profileCount": 0,
            "kgNodeCount": 0,
            "kgEdgeCount": 0,
        }
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        summary.update(
            {
                "paperCount": _airesearch_count_table(connection, tables, "papers"),
                "factCount": _airesearch_count_table(connection, tables, "research_facts"),
                "candidateCount": _airesearch_count_table(connection, tables, "candidate_papers"),
                "profileCount": _airesearch_count_table(connection, tables, "research_profiles"),
                "kgNodeCount": _airesearch_count_table(connection, tables, "kg_nodes"),
                "kgEdgeCount": _airesearch_count_table(connection, tables, "kg_edges"),
                "latestPaperUpdatedAt": _airesearch_max_column(connection, tables, "papers", "updated_at"),
                "latestSyncFinishedAt": _airesearch_max_column(connection, tables, "sync_events", "finished_at"),
            }
        )
    return summary


def _candidate_review_summary(path, limit: int) -> dict:
    data = _read_json_file(path)
    items = data.get("items") if isinstance(data.get("items"), list) else []
    status_counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    top_items = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        top_items.append(
            {
                "rank": item.get("rank"),
                "title": item.get("title") or "",
                "status": item.get("status") or "",
                "score": item.get("best_score"),
                "identifier": item.get("identifier") or "",
                "year": item.get("year"),
            }
        )
    return _file_snapshot(path) | {
        "generatedAt": data.get("generated_at") or "",
        "count": len(items),
        "statusCounts": status_counts,
        "items": top_items,
    }


def _research_clusters_summary(path, limit: int) -> dict:
    data = _read_json_file(path)
    clusters = data.get("clusters") if isinstance(data.get("clusters"), list) else []
    return _file_snapshot(path) | {
        "generatedAt": data.get("generated_at") or "",
        "clusterCount": int(data.get("cluster_count") or len(clusters)),
        "clusteredFactCount": int(data.get("clustered_fact_count") or 0),
        "items": [
            {
                "clusterId": item.get("cluster_id") or "",
                "label": item.get("label") or "",
                "factType": item.get("fact_type") or "",
                "paperCount": item.get("paper_count") or 0,
                "factCount": item.get("fact_count") or 0,
            }
            for item in clusters[:limit]
            if isinstance(item, dict)
        ],
    }


def _research_digest_summary(path, limit: int) -> dict:
    data = _read_json_file(path)
    papers = data.get("papers") if isinstance(data.get("papers"), list) else []
    return _file_snapshot(path) | {
        "generatedAt": data.get("generated_at") or "",
        "paperCount": int(data.get("paper_count") or len(papers)),
        "factCount": int(data.get("fact_count") or 0),
        "items": [
            {
                "paperKey": item.get("paper_key") or item.get("key") or "",
                "title": item.get("title") or "",
                "year": item.get("year"),
                "venue": item.get("venue") or "",
                "artifactTypes": item.get("artifact_types") if isinstance(item.get("artifact_types"), list) else [],
            }
            for item in papers[:limit]
            if isinstance(item, dict)
        ],
    }


@register_handler("airesearch.overview")
def airesearch_overview(payload: dict, context: dict) -> dict:
    """Return a compact read-only AIResearch status payload for Web/API clients."""
    limit = clamp(payload.get("limit") or 5, 1, 20)
    root = store.PROJECT_ROOT / "airesearch"
    exports_root = root / "exports"
    mvp_current = exports_root / "mvp-current"
    site_current = exports_root / "site-current"
    site_stats_path = site_current / "api" / "stats.json"
    site_stats = _read_json_file(site_stats_path)
    overview = {
        "database": _airesearch_database_summary(_airesearch_db_path()),
        "candidateReview": _candidate_review_summary(mvp_current / "candidate-review.json", limit),
        "clusters": _research_clusters_summary(mvp_current / "research-clusters.json", limit),
        "digest": _research_digest_summary(mvp_current / "bundle" / "digest.json", limit),
        "site": {
            "root": _file_snapshot(site_current),
            "stats": _file_snapshot(site_stats_path) | {
                "generatedAt": site_stats.get("generated_at") or "",
                "paperCount": int(site_stats.get("paper_count") or 0),
                "factCount": int(site_stats.get("fact_count") or 0),
                "clusterCount": int(site_stats.get("cluster_count") or 0),
                "reportCount": int(site_stats.get("report_count") or 0),
                "latestYear": site_stats.get("latest_year"),
                "lowCoverageFactTypes": site_stats.get("low_coverage_fact_types")
                if isinstance(site_stats.get("low_coverage_fact_types"), list)
                else [],
            },
            "api": {
                "papers": _file_snapshot(site_current / "api" / "papers.json"),
                "clusters": _file_snapshot(site_current / "api" / "clusters.json"),
                "searchIndex": _file_snapshot(site_current / "api" / "search-index.json"),
            },
        },
    }
    if not _is_read_only(context):
        store.record_module_event(
            "airesearch",
            "overview_read",
            "airesearch overview read",
            {
                "limit": limit,
                "paperCount": overview["database"].get("paperCount", 0),
                "candidateCount": overview["candidateReview"].get("count", 0),
            },
            context.get("client") or context.get("source") or "api",
        )
    return {
        "ok": True,
        "action": "airesearch.overview",
        "module": "airesearch",
        "overview": overview,
        "message": "返回研知库概览。",
    }


@register_handler("airesearch.paper.search")
def airesearch_paper_search(payload: dict, context: dict) -> dict:
    query_text = clean_text(payload.get("q"), 120)
    limit = clamp(payload.get("limit") or 20, 1, 100)
    db_path = _airesearch_db_path()
    if not db_path.exists():
        raise ActionError("not_found", "AIResearch 数据库不存在。", 404, {"path": str(db_path)})
    query = f"%{query_text}%"
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT paper_key, title, authors_json, year, venue, ids_json, paper_dir, updated_at
            FROM papers
            WHERE title LIKE ? OR authors_json LIKE ? OR venue LIKE ? OR paper_key LIKE ?
            ORDER BY COALESCE(year, 0) DESC, updated_at DESC
            LIMIT ?
            """,
            (query, query, query, query, limit),
        ).fetchall()
    items = []
    for row in rows:
        items.append(
            {
                "paperKey": row["paper_key"],
                "title": row["title"] or "",
                "authors": safe_json_list(row["authors_json"]),
                "year": row["year"],
                "venue": row["venue"] or "",
                "ids": safe_json_object(row["ids_json"]),
                "paperDir": row["paper_dir"],
                "updatedAt": row["updated_at"],
            }
        )
    if not _is_read_only(context):
        store.record_module_event(
            "airesearch",
            "paper_search",
            "airesearch paper search completed",
            {"query": query_text, "count": len(items)},
            context.get("client") or context.get("source") or "api",
        )
    return {
        "ok": True,
        "action": "airesearch.paper.search",
        "module": "airesearch",
        "query": query_text,
        "items": items,
        "count": len(items),
        "message": f"返回 {len(items)} 篇论文。",
    }


@register_handler("airesearch.admin.state")
def airesearch_admin_state(payload: dict, context: dict) -> dict:
    admin_server, _config = _ensure_airesearch_admin_runtime()
    result = admin_server.list_state(_airesearch_db_path())
    return {
        "ok": True,
        "action": "airesearch.admin.state",
        "module": "airesearch",
        "state": result,
        "message": "返回研知库管理台状态。",
    }


@register_handler("airesearch.admin.paper_detail")
def airesearch_admin_paper_detail(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.paper_detail",
        lambda: admin_server.paper_detail(_airesearch_db_path(), paper_key),
        "返回研知库论文详情。",
    )


@register_handler("airesearch.admin.paper.update")
def airesearch_admin_paper_update(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.paper.update",
        lambda: admin_server.update_paper(_airesearch_db_path(), paper_key, payload),
        "论文管理信息已更新。",
    )


@register_handler("airesearch.admin.paper.delete")
def airesearch_admin_paper_delete(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.paper.delete",
        lambda: admin_server.delete_paper(_airesearch_db_path(), _airesearch_paper_db_path(), paper_key),
        "论文已删除并移入归档。",
    )


@register_handler("airesearch.admin.paper.draft.save")
def airesearch_admin_paper_draft_save(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.paper.draft.save",
        lambda: admin_server.save_paper_draft(_airesearch_db_path(), paper_key, payload),
        "论文草稿已保存。",
    )


@register_handler("airesearch.admin.paper.draft.delete")
def airesearch_admin_paper_draft_delete(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.paper.draft.delete",
        lambda: admin_server.delete_paper_draft(_airesearch_db_path(), paper_key),
        "论文草稿已丢弃。",
    )


@register_handler("airesearch.admin.paper.blog.detail")
def airesearch_admin_paper_blog_detail(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.paper.blog.detail",
        lambda: admin_server.blog_detail(_airesearch_db_path(), paper_key),
        "返回论文深度解读状态。",
    )


@register_handler("airesearch.admin.paper.blog.generate")
def airesearch_admin_paper_blog_generate(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    if not paper_key:
        raise ActionError("invalid_request", "paperKey is required.", 400)
    admin_server = _airesearch_admin_module()
    options = {
        "paperKey": paper_key,
        "force": payload.get("force") is True,
    }
    if payload.get("targetWordCount") is not None:
        options["targetWordCount"] = clamp(payload["targetWordCount"], 3000, 8000)
    return _airesearch_admin_call(
        "airesearch.admin.paper.blog.generate",
        lambda: admin_server.start_job(_airesearch_admin_config(), "paper_blog_generate", options),
        "论文深度解读生成任务已加入队列。",
    )


@register_handler("airesearch.admin.paper.layout.detail")
def airesearch_admin_paper_layout_detail(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.paper.layout.detail",
        lambda: admin_server.layout_detail(_airesearch_db_path(), paper_key),
        "返回论文版面解析状态。",
    )


@register_handler("airesearch.admin.paper.layout.generate")
def airesearch_admin_paper_layout_generate(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    if not paper_key:
        raise ActionError("invalid_request", "paperKey is required.", 400)
    admin_server = _airesearch_admin_module()
    options = {
        "paperKey": paper_key,
        "force": payload.get("force") is True,
    }
    if payload.get("maxPages") or payload.get("max_pages"):
        options["maxPages"] = clamp(payload.get("maxPages") or payload.get("max_pages"), 1, 10_000)
    return _airesearch_admin_call(
        "airesearch.admin.paper.layout.generate",
        lambda: admin_server.start_job(_airesearch_admin_config(), "paper_layout_parse", options),
        "论文版面解析任务已加入队列。",
    )


@register_handler("airesearch.admin.paper.blog.rollback")
def airesearch_admin_paper_blog_rollback(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    version_id = clamp(payload.get("versionId") or payload.get("version_id"), 1, 10_000_000)
    admin_server = _airesearch_admin_module()
    config = _airesearch_admin_config()
    return _airesearch_admin_call(
        "airesearch.admin.paper.blog.rollback",
        lambda: admin_server.rollback_blog(_airesearch_db_path(), paper_key, version_id, config=config),
        "论文深度解读已回退。",
    )


@register_handler("airesearch.admin.paper.blog.hide")
def airesearch_admin_paper_blog_hide(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    config = _airesearch_admin_config()
    return _airesearch_admin_call(
        "airesearch.admin.paper.blog.hide",
        lambda: admin_server.hide_blog(_airesearch_db_path(), paper_key, config=config),
        "论文深度解读已隐藏。",
    )


@register_handler("airesearch.admin.fact.create")
def airesearch_admin_fact_create(payload: dict, context: dict) -> dict:
    paper_key = _paper_key_from_payload(payload)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.fact.create",
        lambda: admin_server.create_fact(_airesearch_db_path(), paper_key, payload),
        "研究事实已新增。",
    )


@register_handler("airesearch.admin.fact.update")
def airesearch_admin_fact_update(payload: dict, context: dict) -> dict:
    fact_id = clamp(payload.get("id") or payload.get("factId"), 1, 10_000_000)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.fact.update",
        lambda: admin_server.update_fact(_airesearch_db_path(), fact_id, payload),
        "研究事实已更新。",
    )


@register_handler("airesearch.admin.fact.delete")
def airesearch_admin_fact_delete(payload: dict, context: dict) -> dict:
    fact_id = clamp(payload.get("id") or payload.get("factId"), 1, 10_000_000)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.fact.delete",
        lambda: admin_server.delete_fact(_airesearch_db_path(), fact_id),
        "研究事实已删除。",
    )


@register_handler("airesearch.admin.profile.create")
def airesearch_admin_profile_create(payload: dict, context: dict) -> dict:
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.profile.create",
        lambda: admin_server.create_profile(_airesearch_db_path(), payload),
        "搜索配置已新增。",
    )


@register_handler("airesearch.admin.profile.update")
def airesearch_admin_profile_update(payload: dict, context: dict) -> dict:
    name = clean_text(payload.get("name"), 120)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.profile.update",
        lambda: admin_server.update_profile(_airesearch_db_path(), name, payload),
        "搜索配置已更新。",
    )


@register_handler("airesearch.admin.profile.delete")
def airesearch_admin_profile_delete(payload: dict, context: dict) -> dict:
    name = clean_text(payload.get("name"), 120)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.profile.delete",
        lambda: admin_server.delete_profile(_airesearch_db_path(), name),
        "搜索配置已删除。",
    )


@register_handler("airesearch.admin.job.start")
def airesearch_admin_job_start(payload: dict, context: dict) -> dict:
    job_type = clean_text(payload.get("jobType") or payload.get("job_type"), 80)
    allowed = {"search_ingest", "rebuild_site", "deploy_site", "rebuild_deploy", "refresh", "rebuild"}
    if job_type not in allowed:
        raise ActionError("invalid_request", "不支持的研知库任务类型。", 400)
    admin_server = _airesearch_admin_module()
    options = payload.get("options") if isinstance(payload.get("options"), dict) else dict(payload)
    return _airesearch_admin_call(
        "airesearch.admin.job.start",
        lambda: admin_server.start_job(_airesearch_admin_config(), job_type, options),
        "研知库任务已加入队列。",
    )


@register_handler("airesearch.admin.job.cancel")
def airesearch_admin_job_cancel(payload: dict, context: dict) -> dict:
    job_id = clamp(payload.get("id") or payload.get("jobId"), 1, 10_000_000)
    admin_server = _airesearch_admin_module()
    return _airesearch_admin_call(
        "airesearch.admin.job.cancel",
        lambda: admin_server.cancel_job(_airesearch_db_path(), job_id),
        "研知库任务已取消。",
    )


_AIRESEARCH_ACTION_COMMANDS = {
    "airesearch.paper.ingest": ["sync-paperpipe"],
    "airesearch.paper.review": [
        "export-candidate-review",
        "--out",
        "exports/mvp-current/candidate-review.json",
        "--markdown-out",
        "exports/mvp-current/candidate-review.md",
    ],
    "airesearch.cluster.generate": [
        "generate-research-clusters",
        "--out",
        "exports/mvp-current/research-clusters.json",
        "--format",
        "json",
    ],
    "airesearch.digest.generate": [
        "generate-research-digest",
        "--out",
        "exports/mvp-current/bundle/digest.json",
        "--format",
        "json",
    ],
    "airesearch.site.publish": [
        "publish-static-site",
        "--source-dir",
        "exports/mvp-current/bundle",
        "--out-dir",
        "exports/site-current",
    ],
}


def _airesearch_python() -> str:
    candidate = store.PROJECT_ROOT / "airesearch" / ".venv" / "bin" / "python"
    return str(candidate if candidate.exists() else sys.executable)


def _build_airesearch_command_args(action_name: str, payload: dict | None = None) -> list[str]:
    payload = payload or {}
    if action_name == "airesearch.candidate.discover":
        profile = clean_text(
            payload.get("profile") or "multimodal_foundation_models",
            120,
        )
        limit = clamp(payload.get("limit") or 20, 1, 100)
        return ["discover-candidates", "--profile", profile, "--limit", str(limit)]
    return list(_AIRESEARCH_ACTION_COMMANDS[action_name])


def _run_airesearch_cli(action_name: str, payload: dict | None = None, extra_args: list[str] | None = None) -> dict:
    command_args = _build_airesearch_command_args(action_name, payload)
    if extra_args:
        command_args.extend(extra_args)
    command = [_airesearch_python(), "-m", "airesearch.cli", *command_args]
    env = dict(os.environ)
    env.setdefault("PAPER_DB_PATH", str(store.PROJECT_ROOT / "airesearch" / "data" / "paperpipe"))
    completed = subprocess.run(
        command,
        cwd=store.PROJECT_ROOT / "airesearch",
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    output = (completed.stdout or "").strip()
    error = (completed.stderr or "").strip()
    if completed.returncode != 0:
        raise ActionError(
            "airesearch_cli_failed",
            f"AIResearch 命令执行失败：{' '.join(command_args)}",
            500,
            {"exitCode": completed.returncode, "stderr": error[-2000:], "stdout": output[-2000:]},
        )
    store.record_module_event(
        "airesearch",
        action_name.split(".", 1)[1].replace(".", "_"),
        f"{action_name} completed",
        {"command": command_args, "stdout": output[-2000:]},
        "api",
    )
    return {
        "ok": True,
        "action": action_name,
        "module": "airesearch",
        "command": command_args,
        "exitCode": completed.returncode,
        "stdout": output[-4000:],
        "stderr": error[-2000:],
        "message": f"AIResearch 命令已完成：{' '.join(command_args)}。",
    }


@register_handler("airesearch.candidate.discover")
def airesearch_candidate_discover(payload: dict, context: dict) -> dict:
    return _run_airesearch_cli("airesearch.candidate.discover", payload)


@register_handler("airesearch.paper.ingest")
def airesearch_paper_ingest(payload: dict, context: dict) -> dict:
    return _run_airesearch_cli("airesearch.paper.ingest")


@register_handler("airesearch.paper.review")
def airesearch_paper_review(payload: dict, context: dict) -> dict:
    return _run_airesearch_cli("airesearch.paper.review")


@register_handler("airesearch.cluster.generate")
def airesearch_cluster_generate(payload: dict, context: dict) -> dict:
    return _run_airesearch_cli("airesearch.cluster.generate")


@register_handler("airesearch.digest.generate")
def airesearch_digest_generate(payload: dict, context: dict) -> dict:
    return _run_airesearch_cli("airesearch.digest.generate")


@register_handler("airesearch.site.publish")
def airesearch_site_publish(payload: dict, context: dict) -> dict:
    return _run_airesearch_cli("airesearch.site.publish")


@register_handler("airesearch.queue.add")
def airesearch_queue_add(payload: dict, context: dict) -> dict:
    title = clean_text(payload.get("title"), 240)
    record = {
        "title": title,
        "url": clean_text(payload.get("url"), 500, allow_empty=True),
        "note": clean_text(payload.get("note"), 1000, allow_empty=True),
        "source": clean_source(payload.get("source") or context.get("client")),
    }
    event = store.record_module_event(
        "airesearch",
        "queue_add",
        f"research queue: {title}",
        record,
        record["source"],
        1.0,
        True,
    )
    return {
        "ok": True,
        "action": "airesearch.queue.add",
        "module": "airesearch",
        "event": event,
        "message": "已加入研知库候选队列，等待后续 pipeline 审核。",
    }


@register_handler("airesearch.paper.search_arxiv")
def airesearch_paper_search_arxiv(payload: dict, context: dict) -> dict:
    query = clean_text(payload.get("query") or payload.get("q"), 500)
    if not query:
        raise ActionError("invalid_input", "请提供搜索关键词。", 400)
    limit = clamp(payload.get("limit") or 10, 1, 20)
    admin_server = _airesearch_admin_module()
    results = admin_server.search_arxiv_title(query, limit=limit)
    return {
        "ok": True,
        "action": "airesearch.paper.search_arxiv",
        "module": "airesearch",
        "results": results,
        "query": query,
    }


@register_handler("airesearch.paper.ingest_single")
def airesearch_paper_ingest_single(payload: dict, context: dict) -> dict:
    paper_input = clean_text(payload.get("input") or payload.get("title") or payload.get("url"), 1000)
    if not paper_input:
        raise ActionError("invalid_input", "请提供论文标题、arXiv ID 或 URL。", 400)
    admin_server = _airesearch_admin_module()
    config = _airesearch_admin_config()
    result = admin_server.ingest_single_paper(
        db_path=config.db_path,
        paper_db_path=config.paper_db_path,
        papi_executable=config.papi_executable,
        paper_input=paper_input,
        config=config,
    )
    layout_job_id = result.get("layout_job_id")
    if layout_job_id:
        message = f"论文已入库，版面解析任务已加入队列 #{layout_job_id}。"
    elif result.get("layout_job_status") == "existing":
        message = "论文已入库，已有版面解析任务正在排队或运行。"
    elif result.get("layout_job_reason") == "layout_exists":
        message = "论文已入库，已有 layout v2 解析结果。"
    else:
        message = result.get("stdout", "") or result.get("error", "")
    return {
        "ok": result["status"] == "success",
        "action": "airesearch.paper.ingest_single",
        "module": "airesearch",
        "paper_key": result.get("paper_key", ""),
        "status": result["status"],
        "layout_job_id": layout_job_id,
        "layout_job_status": result.get("layout_job_status", ""),
        "layout_job_reason": result.get("layout_job_reason", ""),
        "message": message,
    }


# ============================================================================
# Validation Helpers
# ============================================================================

def clean_text(value, limit: int, allow_empty: bool = False) -> str:
    """Clean and validate text input."""
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if not text and not allow_empty:
        raise ActionError("validation_failed", "文本字段不能为空。", 400)
    return text[:limit]


def clean_date(value) -> str:
    """Clean and validate date input (required)."""
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ActionError("validation_failed", "日期必须使用 YYYY-MM-DD 格式。", 400, {"field": "date"})
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ActionError("validation_failed", "日期不是有效日期。", 400, {"field": "date"}) from exc
    return text


def clean_optional_date(value) -> str:
    """Clean and validate date input (optional)."""
    text = str(value or "").strip()
    return clean_date(text) if text else ""


def clean_schedule_anchor_date(value) -> str:
    """Clean one-off dates or recurring month-day anchors such as XXXX-06-16."""
    text = str(value or "").strip()
    if re.fullmatch(r"XXXX-\d{2}-\d{2}", text):
        try:
            date.fromisoformat("2000-" + text[5:])
        except ValueError as exc:
            raise ActionError("validation_failed", "循环日期不是有效日期。", 400, {"field": "date"}) from exc
        return text
    return clean_date(text)


def clean_schedule_cadence(value) -> str:
    text = clean_text(value or "weekly", 40).lower()
    allowed = {"daily", "weekly", "monthly", "quarterly", "yearly", "custom"}
    return text if text in allowed else "custom"


def clean_time(value) -> str:
    """Clean and validate time input."""
    text = str(value or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"\d{2}:\d{2}", text):
        raise ActionError("validation_failed", "时间必须使用 HH:MM 格式。", 400, {"field": "time"})
    hour, minute = (int(part) for part in text.split(":"))
    if hour > 23 or minute > 59:
        raise ActionError("validation_failed", "时间不是有效时间。", 400, {"field": "time"})
    return text


def clean_priority(value) -> str:
    """Clean and validate priority input."""
    priority = str(value or "normal").strip().lower()
    return priority if priority in {"low", "normal", "high"} else "normal"


def clean_source(value) -> str:
    """Clean source identifier."""
    return clean_text(value or "action", 80)


def clean_choice(value, allowed: set[str], default: str) -> str:
    text = str(value or default).strip().lower()
    return text if text in allowed else default


def clean_optional_float(value, low: float, high: float) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ActionError("validation_failed", "数值字段格式不正确。", 400) from exc
    return max(low, min(high, number))


def safe_json_list(raw: str) -> list:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def safe_json_object(raw: str) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def clamp(value, low: int, high: int) -> int:
    """Clamp a numeric value within bounds."""
    try:
        number = round(float(value or 0))
    except (TypeError, ValueError):
        number = 0
    return max(low, min(high, number))
