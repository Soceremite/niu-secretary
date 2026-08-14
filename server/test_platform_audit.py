"""Tests for the platform audit tables and unified CLI."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from niu_core import cron, exporters, llm, pipeline, profiles, validators
from server import action_handlers, store
from server.actions import ActionError, execute_action
from server.capabilities import capabilities_response
from server.niu_secretary_api import get_action_route


class PlatformAuditTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["NIU_SECRETARY_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")

    def tearDown(self):
        os.environ.pop("NIU_SECRETARY_DB_PATH", None)
        self.tempdir.cleanup()

    def test_module_run_lifecycle(self):
        run = store.start_module_run("news", "validate", "test", {"x": 1})
        finished = store.finish_module_run(run["id"], "passed", {"ok": True})

        self.assertEqual(finished["id"], run["id"])
        self.assertEqual(finished["status"], "passed")
        self.assertEqual(finished["output"], {"ok": True})
        self.assertEqual(store.list_module_runs("news")[0]["id"], run["id"])

    def test_action_execution_records_new_audit_tables(self):
        result = execute_action(
            "fitness.nutrition.create",
            {"food": "鸡蛋", "date": "2026-06-14", "calories": 80},
            {"client": "test", "requestId": "req-1"},
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["actionId"].startswith("aa_"))
        self.assertTrue(result["auditId"].startswith("run_"))
        with store.connect() as connection:
            action_count = connection.execute("SELECT COUNT(*) FROM assistant_actions").fetchone()[0]
            run_count = connection.execute("SELECT COUNT(*) FROM module_runs").fetchone()[0]
        self.assertEqual(action_count, 1)
        self.assertEqual(run_count, 1)

    def test_paper_blog_generation_action_whitelists_provider_options(self):
        captured = {}

        class AdminModule:
            @staticmethod
            def start_job(config, job_type, options):
                captured.update({"config": config, "job_type": job_type, "options": options})
                return {"job_id": 7, "status": "queued"}

        config = object()
        payload = {
            "paperKey": "paper-1",
            "force": True,
            "targetWordCount": 7000,
            "model": "attacker-selected-model",
            "provider": "fixture",
            "base_url": "https://attacker.invalid/v1",
            "api_key_env": "ATTACKER_KEY",
            "fixture_chars_per_section": 1,
            "unexpected": "secret",
        }
        with mock.patch.object(action_handlers, "_airesearch_admin_module", return_value=AdminModule), mock.patch.object(
            action_handlers, "_airesearch_admin_config", return_value=config
        ):
            result = action_handlers.airesearch_admin_paper_blog_generate(payload, {})

        self.assertTrue(result["ok"])
        self.assertIs(captured["config"], config)
        self.assertEqual(captured["job_type"], "paper_blog_generate")
        self.assertEqual(
            captured["options"],
            {"paperKey": "paper-1", "force": True, "targetWordCount": 7000},
        )

    def test_generic_job_action_rejects_paper_blog_generation(self):
        with self.assertRaises(ActionError) as caught:
            action_handlers.airesearch_admin_job_start(
                {
                    "jobType": "paper_blog_generate",
                    "options": {
                        "paperKey": "paper-1",
                        "provider": "fixture",
                        "base_url": "https://attacker.invalid/v1",
                    },
                },
                {},
            )
        self.assertEqual(caught.exception.error, "invalid_request")

    def test_paper_layout_generation_action_whitelists_options(self):
        captured = {}

        class AdminModule:
            @staticmethod
            def start_job(config, job_type, options):
                captured.update({"config": config, "job_type": job_type, "options": options})
                return {"job_id": 11, "status": "queued"}

        config = object()
        payload = {
            "paperKey": "paper-1",
            "force": True,
            "maxPages": 12,
            "api_url": "https://attacker.invalid",
            "executable": "/tmp/attacker",
            "unexpected": "secret",
        }
        with mock.patch.object(action_handlers, "_airesearch_admin_module", return_value=AdminModule), mock.patch.object(
            action_handlers, "_airesearch_admin_config", return_value=config
        ):
            result = action_handlers.airesearch_admin_paper_layout_generate(payload, {})

        self.assertTrue(result["ok"])
        self.assertIs(captured["config"], config)
        self.assertEqual(captured["job_type"], "paper_layout_parse")
        self.assertEqual(
            captured["options"],
            {"paperKey": "paper-1", "force": True, "maxPages": 12},
        )

    def test_generic_job_action_rejects_paper_layout_parse(self):
        with self.assertRaises(ActionError) as caught:
            action_handlers.airesearch_admin_job_start(
                {
                    "jobType": "paper_layout_parse",
                    "options": {
                        "paperKey": "paper-1",
                    },
                },
                {},
            )
        self.assertEqual(caught.exception.error, "invalid_request")

    def test_web_high_risk_action_requires_confirmation(self):
        blocked = execute_action(
            "fitness.nutrition.create",
            {"food": "鸡蛋", "date": "2026-06-14", "calories": 80},
            {"client": "web"},
        )
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error"], "confirmation_required")
        self.assertTrue(blocked["requiresConfirmation"])
        self.assertEqual(store.nutrition_summary("2026-06-14")["count"], 0)

        confirmed = execute_action(
            "fitness.nutrition.create",
            {"food": "鸡蛋", "date": "2026-06-14", "calories": 80},
            {"client": "web", "confirmed": True},
        )
        self.assertTrue(confirmed["ok"])
        self.assertEqual(store.nutrition_summary("2026-06-14")["count"], 1)
        runs = store.list_module_runs("fitness", 5)
        self.assertIn("blocked", {item["status"] for item in runs})

    def test_cli_news_search_records_module_run(self):
        env = os.environ.copy()
        command = [
            sys.executable,
            "-m",
            "niu_secretary.cli",
            "news",
            "search",
            "--q",
            "AI",
            "--limit",
            "1",
        ]
        completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        with sqlite3.connect(os.environ["NIU_SECRETARY_DB_PATH"]) as connection:
            row = connection.execute(
                "SELECT module, run_type, status FROM module_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        self.assertEqual(row, ("news", "search", "passed"))

    def test_platform_capabilities_registered(self):
        names = {item["name"] for item in capabilities_response()["capabilities"]}
        self.assertIn("news.search", names)
        self.assertIn("platform.runs.list", names)
        self.assertIn("platform.events.list", names)
        self.assertIn("platform.today.context", names)
        self.assertIn("platform.modules.status", names)
        self.assertIn("platform.ops.center", names)
        self.assertIn("platform.review.mark", names)
        self.assertIn("profile.change.review", names)
        self.assertIn("profile.change.revert", names)
        self.assertIn("fitness.workout.create", names)
        self.assertIn("fitness.nutrition.update", names)
        self.assertIn("fitness.workout.update", names)
        self.assertIn("fitness.workout.delete", names)
        self.assertIn("fitness.body_metric.create", names)
        self.assertIn("fitness.body_metric.update", names)
        self.assertIn("fitness.body_metric.delete", names)
        self.assertIn("fitness.recovery.create", names)
        self.assertIn("fitness.recovery.list", names)
        self.assertIn("fitness.assessment.create", names)
        self.assertIn("fitness.assessment.list", names)
        self.assertIn("fitness.consult.create", names)
        self.assertIn("fitness.consult.list", names)
        self.assertIn("fitness.summary.today", names)
        self.assertIn("fitness.summary.weekly", names)
        self.assertIn("fitness.daily_summary.get", names)
        self.assertIn("fitness.recommend.meal", names)
        self.assertIn("fitness.recommend.workout", names)
        self.assertIn("fitness.recommendations.list", names)
        self.assertIn("schedule.todo.complete", names)
        self.assertIn("schedule.todo.reschedule", names)
        self.assertIn("schedule.event.update", names)
        self.assertIn("schedule.todo.update", names)
        self.assertIn("schedule.conflicts.detect", names)
        self.assertIn("schedule.day.plan", names)
        self.assertIn("schedule.day.review", names)
        self.assertIn("schedule.day_plan.get", names)
        self.assertIn("schedule.day_review.get", names)
        self.assertIn("schedule.important_date.create", names)
        self.assertIn("schedule.important_date.list", names)
        self.assertIn("schedule.goal.create", names)
        self.assertIn("schedule.goal.list", names)
        self.assertIn("schedule.task_history.list", names)
        self.assertIn("news.validate-sources", names)
        self.assertIn("news.validate-keypoints", names)
        self.assertIn("news.audit-images", names)
        self.assertIn("news.topic.queue-research", names)
        self.assertIn("leisure.profile.update", names)
        self.assertIn("leisure.item.save", names)
        self.assertIn("leisure.item.rate", names)
        self.assertIn("leisure.item.update", names)
        self.assertIn("leisure.item.delete", names)
        self.assertIn("leisure.history.search", names)
        self.assertIn("leisure.profile.suggestions", names)
        self.assertIn("leisure.profile.apply_suggestion", names)
        self.assertIn("leisure.recommendations.list", names)
        self.assertIn("leisure.items.list", names)
        self.assertIn("airesearch.paper.search", names)
        self.assertIn("airesearch.overview", names)
        self.assertIn("airesearch.candidate.discover", names)
        self.assertIn("airesearch.paper.ingest", names)
        self.assertIn("airesearch.cluster.generate", names)
        self.assertIn("airesearch.digest.generate", names)
        self.assertIn("airesearch.site.publish", names)
        self.assertIn("airesearch.queue.add", names)
        self.assertIn("airesearch.admin.state", names)
        self.assertIn("airesearch.admin.paper_detail", names)
        self.assertIn("airesearch.admin.paper.update", names)
        self.assertIn("airesearch.admin.paper.blog.detail", names)
        self.assertIn("airesearch.admin.paper.blog.generate", names)
        self.assertIn("airesearch.admin.paper.layout.detail", names)
        self.assertIn("airesearch.admin.paper.layout.generate", names)
        self.assertIn("airesearch.admin.paper.blog.rollback", names)
        self.assertIn("airesearch.admin.paper.blog.hide", names)
        self.assertIn("airesearch.admin.fact.create", names)
        self.assertIn("airesearch.admin.fact.update", names)
        self.assertIn("airesearch.admin.profile.create", names)
        self.assertIn("airesearch.admin.profile.update", names)
        self.assertIn("airesearch.admin.job.start", names)
        self.assertIn("airesearch.admin.job.cancel", names)

    def test_platform_validate_checks_profile_change_table(self):
        import json

        env = os.environ.copy()
        completed = subprocess.run(
            [sys.executable, "-m", "niu_secretary.cli", "platform", "validate"],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("profile_changes", payload["result"]["requiredTables"])

    def test_capabilities_and_handlers_are_consistent(self):
        from server.actions import _HANDLERS
        from server.capabilities import CAPABILITIES

        capabilities = {item["name"] for item in CAPABILITIES}
        handlers = set(_HANDLERS)

        self.assertEqual(sorted(handlers - capabilities), [])
        self.assertEqual(sorted(capabilities - handlers), [])

    def test_registered_photo_recognition_action_reports_transport_boundary(self):
        from server.actions import ActionError

        with self.assertRaises(ActionError) as raised:
            execute_action(
                "fitness.nutrition.recognize_photo",
                {"photo": "placeholder"},
                {"client": "test"},
            )

        self.assertEqual(raised.exception.error, "unsupported_transport")
        self.assertIn("/niu-secretary/fitness/api/agent/nutrition-recognize", raised.exception.details["endpoint"])

    def test_platform_actions_list_runs_and_events(self):
        store.record_module_event("news", "validation", "validated news", {"ok": True}, "test")
        execute_action("fitness.nutrition.create", {"food": "酸奶", "date": "2026-06-14"})

        runs = execute_action("platform.runs.list", {"module": "fitness", "limit": 10})
        self.assertTrue(runs["ok"])
        self.assertGreaterEqual(runs["count"], 1)
        self.assertTrue(any(item["runType"] == "fitness.nutrition.create" for item in runs["items"]))

        events = execute_action("platform.events.list", {"module": "news", "eventType": "validation"})
        self.assertTrue(events["ok"])
        self.assertEqual(events["count"], 1)
        self.assertEqual(events["items"][0]["title"], "validated news")

    def test_platform_cron_registry_action_lists_jobs_without_running_them(self):
        result = execute_action("platform.cron.registry", {}, {"client": "test"})

        self.assertTrue(result["ok"])
        self.assertIn("fitness.summarize-day", result["jobs"])
        self.assertIn("daily", result["groups"])
        self.assertEqual(store.list_module_runs("fitness"), [])

    def test_platform_today_context_aggregates_modules(self):
        execute_action("fitness.nutrition.create", {"food": "酸奶", "date": "2026-06-14", "calories": 120})
        execute_action("schedule.event.create", {"title": "晨会", "date": "2026-06-14", "time": "09:30"})

        result = execute_action("platform.today.context", {"date": "2026-06-14", "limit": 2})

        self.assertTrue(result["ok"])
        self.assertEqual(result["context"]["date"], "2026-06-14")
        self.assertEqual(result["context"]["fitness"]["mealCount"], 1)
        self.assertEqual(result["context"]["schedule"]["eventCount"], 1)
        self.assertIn("news", result["context"])
        self.assertIn("leisure", result["context"])
        self.assertEqual(result["context"]["leisure"]["context"]["availableMinutes"], 120)

    def test_platform_today_context_passes_schedule_load_to_leisure(self):
        for index in range(3):
            execute_action(
                "schedule.event.create",
                {"title": f"会议 {index}", "date": "2026-06-14", "time": f"1{index}:00"},
            )
        for index in range(2):
            execute_action("schedule.todo.create", {"title": f"任务 {index}", "date": "2026-06-14"})

        result = execute_action("platform.today.context", {"date": "2026-06-14", "limit": 1})

        self.assertEqual(result["context"]["leisure"]["context"]["availableMinutes"], 30)
        self.assertGreaterEqual(result["context"]["leisure"]["context"]["scheduleLoad"], 5)
        self.assertIn("日程较满", result["context"]["fitness"]["workoutRecommendations"][0])

    def test_platform_today_context_passes_fitness_load_to_leisure(self):
        execute_action(
            "fitness.workout.create",
            {"name": "力量训练A", "date": "2026-06-12", "durationMin": 90},
        )
        execute_action(
            "fitness.workout.create",
            {"name": "力量训练B", "date": "2026-06-14", "durationMin": 100},
        )

        result = execute_action("platform.today.context", {"date": "2026-06-14", "limit": 1})

        self.assertTrue(result["context"]["fitness"]["recoveryRecommended"])
        self.assertEqual(result["context"]["fitness"]["recentWorkoutMinutes"], 190)
        self.assertTrue(result["context"]["leisure"]["context"]["recoveryRecommended"])
        self.assertEqual(result["context"]["leisure"]["context"]["fitnessLoad"]["recentWorkoutMinutes"], 190)

    def test_platform_modules_status_shows_recent_runs(self):
        execute_action("fitness.nutrition.create", {"food": "酸奶", "date": "2026-06-14"})
        status = execute_action("platform.modules.status", {"limit": 1})

        self.assertTrue(status["ok"])
        modules = {item["module"]: item for item in status["items"]}
        self.assertIn("fitness", modules)
        self.assertGreater(modules["fitness"]["capabilityCount"], 0)
        self.assertEqual(modules["fitness"]["lastRun"]["module"], "fitness")
        self.assertNotIn("input", modules["fitness"]["lastRun"])
        self.assertNotIn("output", modules["fitness"]["lastRun"])

    def test_platform_ops_center_aggregates_review_and_model_activity(self):
        execute_action("fitness.nutrition.create", {"food": "酸奶", "date": "2026-06-14"})
        store.record_module_event(
            "leisure",
            "profile_suggestion",
            "闲趣画像建议",
            {"action": "leisure.profile.update"},
            "test",
            requires_review=True,
        )
        store.record_model_call("news", "summarize", "fake-model", "input", "output", "passed", 8)
        execute_action("profile.update", {"module": "fitness", "patch": {"goal": "fat_loss"}})

        result = execute_action("platform.ops.center", {"limit": 10})

        self.assertTrue(result["ok"])
        self.assertIn("modules", result)
        self.assertGreaterEqual(result["summary"]["recentRunCount"], 1)
        self.assertEqual(result["summary"]["pendingReviewCount"], 1)
        self.assertTrue(any(item["module"] == "leisure" for item in result["pendingReviews"]))
        self.assertTrue(any(item["action"] == "fitness.nutrition.create" for item in result["assistantActions"]))
        self.assertTrue(any(item["purpose"] == "summarize" for item in result["modelCalls"]))
        self.assertTrue(any(item["module"] == "fitness" for item in result["profileChanges"]))
        self.assertEqual(result["summary"]["pendingProfileChangeCount"], 1)
        self.assertEqual(result["summary"]["pendingWorkItemCount"], 2)
        work_items = {item["kind"]: item for item in result["pendingWorkItems"]}
        self.assertEqual(work_items["profile_change"]["primaryAction"]["action"], "profile.change.review")
        self.assertEqual(work_items["leisure_profile_suggestion"]["primaryAction"]["action"], "leisure.profile.apply_suggestion")
        self.assertNotIn("input", result["runs"][0])
        self.assertNotIn("output", result["runs"][0])

        fitness_only = execute_action("platform.ops.center", {"module": "fitness", "limit": 10})
        self.assertTrue(all(item["module"] == "fitness" for item in fitness_only["runs"]))
        self.assertTrue(all(item["module"] == "fitness" for item in fitness_only["profileChanges"]))
        self.assertTrue(all(item["module"] == "fitness" for item in fitness_only["pendingWorkItems"]))

    def test_platform_review_mark_closes_generic_pending_work_item(self):
        event = store.record_module_event(
            "news",
            "topic_candidate",
            "新闻主题待确认",
            {"topic": "Agent memory"},
            "unit-test",
            requires_review=True,
        )
        before = execute_action("platform.ops.center", {"module": "news", "limit": 10})

        self.assertEqual(before["summary"]["pendingReviewCount"], 1)
        self.assertEqual(before["summary"]["pendingWorkItemCount"], 1)
        self.assertEqual(before["pendingWorkItems"][0]["kind"], "module_review")
        self.assertEqual(before["pendingWorkItems"][0]["primaryAction"]["action"], "platform.review.mark")

        blocked = execute_action(
            "platform.review.mark",
            {"eventId": event["id"], "note": "确认完成"},
            {"client": "web"},
        )
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error"], "confirmation_required")
        self.assertEqual(store.get_latest_module_review_mark(event["id"]), None)

        marked = execute_action(
            "platform.review.mark",
            {"eventId": event["id"], "note": "确认完成"},
            {"client": "unit-test", "confirmed": True},
        )

        self.assertTrue(marked["ok"])
        self.assertEqual(marked["module"], "news")
        self.assertEqual(marked["review"]["payload"]["eventId"], event["id"])
        self.assertEqual(marked["review"]["payload"]["note"], "确认完成")
        after = execute_action("platform.ops.center", {"module": "news", "limit": 10})
        self.assertEqual(after["summary"]["pendingReviewCount"], 0)
        self.assertEqual(after["summary"]["pendingWorkItemCount"], 0)
        self.assertEqual(after["pendingReviews"], [])

        repeated = execute_action(
            "platform.review.mark",
            {"eventId": event["id"], "note": "重复处理"},
            {"client": "unit-test", "confirmed": True},
        )
        self.assertEqual(repeated["message"], "该待审核事件此前已处理。")
        self.assertEqual(len(store.list_module_events("news", "module_review_marked", 10)), 1)

    def test_profile_change_review_marks_change_without_duplicate_events(self):
        execute_action(
            "profile.update",
            {"module": "fitness", "patch": {"goal": "fat_loss"}, "summary": "unit review"},
        )
        before = execute_action("platform.ops.center", {"module": "fitness", "limit": 10})
        change = before["profileChanges"][0]

        result = execute_action(
            "profile.change.review",
            {"changeId": change["id"], "note": "确认是用户意图"},
            {"client": "unit-test", "confirmed": True},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["module"], "fitness")
        self.assertTrue(result["change"]["reviewed"])
        self.assertEqual(result["change"]["review"]["note"], "确认是用户意图")
        events = store.list_module_events("fitness", "profile_change_review", 10)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["changeId"], change["id"])

        repeated = execute_action("profile.change.review", {"changeId": change["id"]}, {"confirmed": True})
        self.assertEqual(repeated["message"], "该画像变更此前已处理。")
        self.assertEqual(len(store.list_module_events("fitness", "profile_change_review", 10)), 1)

        after = execute_action("platform.ops.center", {"module": "fitness", "limit": 10})
        self.assertEqual(after["summary"]["pendingProfileChangeCount"], 0)
        self.assertTrue(after["profileChanges"][0]["reviewed"])

    def test_profile_change_revert_restores_old_value_and_marks_reviewed(self):
        execute_action(
            "profile.update",
            {"module": "fitness", "patch": {"goal": "fat_loss"}, "summary": "unit revert"},
        )
        change = execute_action("platform.ops.center", {"module": "fitness", "limit": 10})[
            "profileChanges"
        ][0]

        result = execute_action(
            "profile.change.revert",
            {"changeId": change["id"], "note": "恢复默认目标"},
            {"client": "unit-test", "confirmed": True},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "profile.change.revert")
        self.assertEqual(result["profile"]["goal"], change["oldValue"])
        self.assertTrue(result["change"]["reviewed"])
        self.assertTrue(result["change"]["reverted"])
        self.assertEqual(result["change"]["review"]["status"], "reverted")
        events = store.list_module_events("fitness", "profile_change_revert", 10)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["changeId"], change["id"])
        self.assertTrue(events[0]["payload"]["profileUpdated"])

        after = execute_action("platform.ops.center", {"module": "fitness", "limit": 10})
        self.assertEqual(after["summary"]["pendingProfileChangeCount"], 1)
        reverted = next(item for item in after["profileChanges"] if item["id"] == change["id"])
        self.assertTrue(reverted["reviewed"])
        self.assertTrue(reverted["reverted"])

    def test_profile_change_revert_rejects_stale_change(self):
        execute_action(
            "profile.update",
            {"module": "fitness", "patch": {"goal": "fat_loss"}, "summary": "first change"},
        )
        first_change = execute_action("profile.changes", {"module": "fitness", "limit": 1})[
            "items"
        ][0]
        execute_action(
            "profile.update",
            {"module": "fitness", "patch": {"goal": "maintenance"}, "summary": "second change"},
        )

        with self.assertRaises(ActionError) as raised:
            execute_action(
                "profile.change.revert",
                {"changeId": first_change["id"]},
                {"client": "unit-test", "confirmed": True},
            )

        self.assertEqual(raised.exception.error, "conflict")
        profile = execute_action("profile.get", {"module": "fitness"})["profile"]
        self.assertEqual(profile["goal"], "maintenance")
        self.assertEqual(len(store.list_module_events("fitness", "profile_change_revert", 10)), 0)

    def test_news_search_action_returns_archive_results(self):
        result = execute_action("news.search", {"q": "AI", "limit": 1})

        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "news.search")
        self.assertEqual(result["query"], "AI")
        self.assertLessEqual(result["count"], 1)

    def test_news_search_filters_archive_results(self):
        from pathlib import Path

        with sqlite3.connect(Path("news-daily/news_daily.db")) as connection:
            connection.row_factory = sqlite3.Row
            sample = connection.execute(
                """
                SELECT ni.date, ni.section, ni.source_name, nt.tag
                FROM news_items ni
                JOIN news_tags nt ON nt.date = ni.date AND nt.item_id = ni.item_id
                WHERE ni.section <> '' AND ni.source_name <> '' AND nt.tag <> ''
                ORDER BY ni.date DESC, ni.item_order ASC
                LIMIT 1
                """
            ).fetchone()
        self.assertIsNotNone(sample)
        result = execute_action(
            "news.search",
            {
                "date": sample["date"],
                "section": sample["section"],
                "tag": sample["tag"],
                "source": sample["source_name"].split()[0],
                "limit": 5,
            },
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["filters"]["date"], sample["date"])
        self.assertEqual(result["filters"]["section"], sample["section"])
        self.assertGreaterEqual(result["count"], 1)
        for item in result["items"]:
            self.assertEqual(item["date"], sample["date"])
            self.assertEqual(item["section"], sample["section"])
            self.assertIn(sample["source_name"].split()[0], item["sourceName"])

    def test_fitness_workout_metric_and_weekly_summary(self):
        execute_action(
            "fitness.nutrition.create",
            {"food": "鸡胸肉", "date": "2026-06-14", "calories": 180, "proteinG": 35},
        )
        workout = execute_action(
            "fitness.workout.create",
            {"name": "力量训练", "date": "2026-06-14", "durationMin": 45, "intensity": "high"},
        )
        metric = execute_action(
            "fitness.body_metric.create",
            {"date": "2026-06-14", "weightKg": 72.5, "bodyFatPct": 18.2},
        )
        summary = execute_action("fitness.summary.weekly", {"date": "2026-06-14"})

        self.assertTrue(workout["ok"])
        self.assertEqual(workout["record"]["durationMin"], 45)
        self.assertTrue(metric["ok"])
        self.assertEqual(metric["record"]["weightKg"], 72.5)
        self.assertEqual(summary["summary"]["workoutCount"], 1)
        self.assertEqual(summary["summary"]["nutritionCount"], 1)
        self.assertEqual(summary["summary"]["latestMetric"]["weightKg"], 72.5)

        today = execute_action("fitness.summary.today", {"date": "2026-06-14"})
        stored_daily = execute_action("fitness.daily_summary.get", {"date": "2026-06-14"})
        meal = execute_action("fitness.recommend.meal", {"date": "2026-06-14"})
        workout_rec = execute_action("fitness.recommend.workout", {"date": "2026-06-14"})
        self.assertEqual(today["summary"]["count"], 1)
        self.assertEqual(today["savedSummary"]["summary"]["nutrition"]["count"], 1)
        self.assertTrue(stored_daily["found"])
        self.assertEqual(stored_daily["summary"]["summary"]["nutrition"]["count"], 1)
        self.assertTrue(meal["recommendations"])
        self.assertTrue(workout_rec["recommendations"])
        self.assertEqual(len(store.list_fitness_recommendations("2026-06-14", "meal")), 1)
        self.assertEqual(len(store.list_fitness_recommendations("2026-06-14", "workout")), 1)
        history = execute_action("fitness.recommendations.list", {"date": "2026-06-14", "type": "meal"})
        self.assertEqual(history["count"], 1)
        self.assertEqual(history["items"][0]["type"], "meal")

    def test_fitness_recovery_logs_use_action_store_and_audit_event(self):
        created = execute_action(
            "fitness.recovery.create",
            {
                "date": "2026-06-14",
                "sleepHours": 7.5,
                "sleepQuality": 4,
                "stress": 2,
                "soreness": 3,
                "lastRpe": 8.5,
                "score": 76,
                "statusLabel": "绿色",
                "statusAdvice": "正常训练，控制容量。",
                "source": "unit-test",
            },
            {"client": "unit-test", "confirmed": True},
        )
        listed = execute_action("fitness.recovery.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 10})

        self.assertTrue(created["ok"])
        self.assertEqual(created["record"]["score"], 76)
        self.assertEqual(created["record"]["statusLabel"], "绿色")
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["items"][0]["id"], created["record"]["id"])
        self.assertEqual(store.list_recovery_logs("2026-06-14", "2026-06-14", 10)[0]["sleepHours"], 7.5)
        event_types = {item["eventType"] for item in store.list_module_events("fitness", "", 20)}
        self.assertIn("recovery", event_types)

    def test_fitness_assessment_and_consult_use_action_store(self):
        assessment = execute_action(
            "fitness.assessment.create",
            {
                "date": "2026-06-14",
                "goal": "fat_loss",
                "weightKg": 72.5,
                "waistCm": 82,
                "bmi": 23.1,
                "fmsTotal": 16,
                "payload": {"advice": "控制热量", "trainingLimits": ["降载"]},
                "source": "unit-test",
            },
            {"client": "unit-test", "confirmed": True},
        )
        consult = execute_action(
            "fitness.consult.create",
            {
                "date": "2026-06-14",
                "area": "膝",
                "text": "深蹲膝前侧不适",
                "payload": {"result": {"level": "low", "title": "控制训练量", "advice": "先降载"}},
                "source": "unit-test",
            },
            {"client": "unit-test", "confirmed": True},
        )

        assessments = execute_action("fitness.assessment.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 10})
        consults = execute_action("fitness.consult.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 10})

        self.assertTrue(assessment["ok"])
        self.assertEqual(assessment["record"]["fmsTotal"], 16)
        self.assertEqual(assessment["record"]["payload"]["advice"], "控制热量")
        self.assertEqual(assessments["count"], 1)
        self.assertEqual(assessments["items"][0]["id"], assessment["record"]["id"])
        self.assertTrue(consult["ok"])
        self.assertEqual(consult["record"]["level"], "low")
        self.assertEqual(consults["count"], 1)
        self.assertEqual(consults["items"][0]["result"]["title"], "控制训练量")
        event_types = {item["eventType"] for item in store.list_module_events("fitness", "", 20)}
        self.assertIn("assessment", event_types)
        self.assertIn("consult", event_types)

    def test_fitness_records_can_be_corrected_and_deleted_with_audit(self):
        nutrition = execute_action(
            "fitness.nutrition.create",
            {"food": "米饭", "date": "2026-06-14", "calories": 400, "proteinG": 7},
        )["record"]
        workout = execute_action(
            "fitness.workout.create",
            {"name": "跑步", "date": "2026-06-14", "durationMin": 30, "intensity": "medium"},
        )["record"]
        metric = execute_action(
            "fitness.body_metric.create",
            {"date": "2026-06-14", "weightKg": 72.5, "waistCm": 82},
        )["record"]

        updated_nutrition = execute_action(
            "fitness.nutrition.update",
            {"id": nutrition["id"], "calories": 360, "proteinG": 8},
            {"client": "unit-test", "confirmed": True},
        )
        updated_workout = execute_action(
            "fitness.workout.update",
            {"id": workout["id"], "durationMin": 45, "intensity": "high"},
            {"client": "unit-test", "confirmed": True},
        )
        updated_metric = execute_action(
            "fitness.body_metric.update",
            {"id": metric["id"], "weightKg": 71.8, "note": "晨起"},
            {"client": "unit-test", "confirmed": True},
        )

        self.assertEqual(updated_nutrition["record"]["calories"], 360)
        self.assertEqual(updated_workout["record"]["durationMin"], 45)
        self.assertEqual(updated_metric["record"]["weightKg"], 71.8)
        self.assertEqual(store.nutrition_summary("2026-06-14")["calories"], 360)
        self.assertEqual(store.list_workout_logs("2026-06-14", "2026-06-14", 10)[0]["durationMin"], 45)
        self.assertEqual(store.list_body_metrics("2026-06-14", "2026-06-14", 10)[0]["note"], "晨起")

        execute_action("fitness.workout.delete", {"id": workout["id"]}, {"client": "unit-test", "confirmed": True})
        execute_action("fitness.body_metric.delete", {"id": metric["id"]}, {"client": "unit-test", "confirmed": True})

        self.assertEqual(store.list_workout_logs("2026-06-14", "2026-06-14", 10), [])
        self.assertEqual(store.list_body_metrics("2026-06-14", "2026-06-14", 10), [])
        event_types = {item["eventType"] for item in store.list_module_events("fitness", "", 20)}
        self.assertIn("nutrition_updated", event_types)
        self.assertIn("workout_updated", event_types)
        self.assertIn("workout_deleted", event_types)
        self.assertIn("body_metric_updated", event_types)
        self.assertIn("body_metric_deleted", event_types)

    def test_fitness_correction_actions_require_web_confirmation(self):
        workout = execute_action(
            "fitness.workout.create",
            {"name": "骑行", "date": "2026-06-14", "durationMin": 20},
        )["record"]

        blocked = execute_action(
            "fitness.workout.update",
            {"id": workout["id"], "durationMin": 60},
            {"client": "web"},
        )

        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error"], "confirmation_required")
        self.assertEqual(store.get_workout_log(workout["id"])["durationMin"], 20)

    def test_schedule_conflicts_plan_and_review(self):
        execute_action("schedule.event.create", {"title": "站会", "date": "2026-06-14", "time": "09:30"})
        execute_action("schedule.event.create", {"title": "客户会", "date": "2026-06-14", "time": "09:30"})
        execute_action("schedule.todo.create", {"title": "整理周报", "date": "2026-06-14", "priority": "high"})

        conflicts = execute_action("schedule.conflicts.detect", {"date": "2026-06-14"})
        plan = execute_action("schedule.day.plan", {"date": "2026-06-14"})
        review = execute_action(
            "schedule.day.review",
            {"date": "2026-06-14", "completed": 1, "blocked": ["等待资料"], "note": "推进顺利"},
        )
        stored_plan = execute_action("schedule.day_plan.get", {"date": "2026-06-14"})
        stored_review = execute_action("schedule.day_review.get", {"date": "2026-06-14"})

        self.assertEqual(conflicts["count"], 1)
        self.assertEqual(len(plan["plan"]["plan"]["blocks"]), 3)
        self.assertEqual(plan["plan"]["plan"]["conflictCount"], 1)
        self.assertEqual(review["review"]["review"]["completed"], 1)
        self.assertEqual(review["review"]["review"]["blocked"], ["等待资料"])
        self.assertTrue(stored_plan["found"])
        self.assertEqual(stored_plan["plan"]["plan"]["conflictCount"], 1)
        self.assertTrue(stored_review["found"])
        self.assertEqual(stored_review["review"]["review"]["note"], "推进顺利")

        todo_id = plan["plan"]["plan"]["blocks"][-1]["id"]
        completed = execute_action("schedule.todo.complete", {"id": todo_id})
        moved = execute_action("schedule.todo.reschedule", {"id": todo_id, "date": "2026-06-15"})
        self.assertTrue(completed["record"]["done"])
        self.assertEqual(moved["record"]["date"], "2026-06-15")
        history = store.list_schedule_task_history(todo_id)
        self.assertEqual({item["eventType"] for item in history}, {"completed", "rescheduled"})
        action_history = execute_action("schedule.task_history.list", {"todoId": todo_id})
        self.assertEqual(action_history["count"], 2)
        self.assertEqual({item["eventType"] for item in action_history["items"]}, {"completed", "rescheduled"})

    def test_schedule_records_can_be_corrected_with_audit_history(self):
        event = execute_action(
            "schedule.event.create",
            {"title": "站会", "date": "2026-06-14", "time": "09:30"},
        )["record"]
        other = execute_action(
            "schedule.event.create",
            {"title": "客户会", "date": "2026-06-14", "time": "09:30"},
        )["record"]
        todo = execute_action(
            "schedule.todo.create",
            {"title": "写周报", "date": "2026-06-14", "priority": "normal"},
        )["record"]

        updated_event = execute_action(
            "schedule.event.update",
            {"id": event["id"], "time": "10:00", "note": "延后"},
            {"client": "unit-test", "confirmed": True},
        )
        updated_todo = execute_action(
            "schedule.todo.update",
            {"id": todo["id"], "title": "写平台周报", "priority": "high", "date": "2026-06-15"},
            {"client": "unit-test", "confirmed": True},
        )

        self.assertEqual(updated_event["record"]["time"], "10:00")
        self.assertEqual(updated_todo["record"]["title"], "写平台周报")
        self.assertEqual(updated_todo["record"]["priority"], "high")
        self.assertEqual(execute_action("schedule.conflicts.detect", {"date": "2026-06-14"})["count"], 0)

        deleted_event = execute_action(
            "schedule.event.delete",
            {"id": other["id"]},
            {"client": "unit-test", "confirmed": True},
        )
        deleted_todo = execute_action(
            "schedule.todo.delete",
            {"id": todo["id"]},
            {"client": "unit-test", "confirmed": True},
        )

        self.assertEqual(deleted_event["record"]["title"], "客户会")
        self.assertEqual(deleted_todo["record"]["title"], "写平台周报")
        event_types = {item["eventType"] for item in store.list_module_events("schedule", "", 20)}
        self.assertIn("event_updated", event_types)
        self.assertIn("event_deleted", event_types)
        self.assertIn("todo_updated", event_types)
        self.assertIn("todo_deleted", event_types)
        history_types = {item["eventType"] for item in store.list_schedule_task_history(todo["id"], 10)}
        self.assertEqual(history_types, {"updated", "deleted"})

    def test_schedule_correction_actions_require_web_confirmation(self):
        event = execute_action(
            "schedule.event.create",
            {"title": "晨会", "date": "2026-06-14", "time": "09:00"},
        )["record"]

        blocked = execute_action(
            "schedule.event.update",
            {"id": event["id"], "time": "10:00"},
            {"client": "web"},
        )

        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error"], "confirmation_required")
        self.assertEqual(store.get_schedule_event(event["id"])["time"], "09:00")

    def test_news_validation_audit_actions(self):
        sources = execute_action("news.validate-sources", {})
        keypoints = execute_action("news.validate-keypoints", {})
        images = execute_action("news.audit-images", {})

        self.assertTrue(sources["ok"])
        self.assertIn(sources["status"], {"passed", "blocked"})
        self.assertTrue(keypoints["ok"])
        self.assertIn(keypoints["status"], {"passed", "blocked"})
        self.assertTrue(images["ok"])
        self.assertIn(images["status"], {"passed", "blocked"})

    def test_cross_module_research_profile_drives_news_and_queue(self):
        execute_action(
            "profile.update",
            {"module": "airesearch", "patch": {"topics": ["AI"]}, "summary": "关注 AI 研究"},
            {"client": "test"},
        )

        recommended = execute_action("news.recommend", {"limit": 3})

        self.assertTrue(recommended["ok"])
        self.assertIn("AI", recommended["researchProfile"]["topics"])
        self.assertTrue(recommended["personalized"])
        self.assertTrue(all(item["matchScore"] > 0 for item in recommended["items"]))

        blocked = execute_action(
            "news.topic.queue-research",
            {"topic": "Agent memory", "note": "来自新闻主题"},
            {"client": "web"},
        )
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error"], "confirmation_required")

        queued = execute_action(
            "news.topic.queue-research",
            {"topic": "Agent memory", "note": "来自新闻主题"},
            {"client": "web", "confirmed": True},
        )
        self.assertTrue(queued["ok"])
        self.assertTrue(queued["event"]["requiresReview"])
        self.assertTrue(queued["researchEvent"]["requiresReview"])

    def test_leisure_feedback_and_history_search(self):
        save = execute_action(
            "leisure.item.save",
            {
                "itemId": "movie-1",
                "category": "movie",
                "title": "星际旅行",
                "note": "周末看",
                "payload": {"genres": ["科幻"], "mood": "探索"},
            },
        )
        rate = execute_action(
            "leisure.item.rate",
            {"itemId": "movie-1", "category": "movie", "title": "星际旅行", "rating": 5},
        )
        history = execute_action("leisure.history.search", {"q": "星际", "category": "movie"})
        recommendation = execute_action("leisure.recommend", {"limit": 1, "availableMinutes": 35, "scheduleLoad": 4})
        profile = execute_action("leisure.profile.update", {"patch": {"moods": ["relaxed"]}})

        self.assertTrue(save["ok"])
        self.assertTrue(save["record"]["profileSuggestion"]["requiresReview"])
        suggestions = execute_action("leisure.profile.suggestions", {})
        self.assertEqual(suggestions["count"], 1)
        self.assertEqual(suggestions["items"][0]["payload"]["patch"]["genres"]["movie"], ["科幻"])
        applied = execute_action(
            "leisure.profile.apply_suggestion",
            {"eventId": suggestions["items"][0]["id"]},
        )
        self.assertTrue(applied["ok"])
        self.assertIn("genres", applied["applied"]["changedFields"])
        self.assertEqual(execute_action("leisure.profile.suggestions", {})["count"], 0)
        self.assertEqual(rate["record"]["rating"], 5)
        self.assertEqual(history["count"], 2)
        self.assertTrue(all(item["category"] == "movie" for item in history["items"]))
        self.assertFalse(recommendation["personalized"])
        self.assertEqual(recommendation["context"]["availableMinutes"], 35)
        self.assertEqual(len(store.list_leisure_recommendations(limit=5)), 1)
        rec_history = execute_action("leisure.recommendations.list", {"limit": 2})
        self.assertEqual(rec_history["count"], 1)
        self.assertEqual(rec_history["items"][0]["context"]["availableMinutes"], 35)
        items = execute_action("leisure.items.list", {"category": "movie", "limit": 5})
        self.assertGreaterEqual(items["count"], 1)
        self.assertTrue(all(item["category"] == "movie" for item in items["items"]))
        with store.connect() as connection:
            item_count = connection.execute("SELECT COUNT(*) FROM leisure_items").fetchone()[0]
        self.assertGreaterEqual(item_count, 1)
        self.assertEqual(profile["module"], "leisure")

    def test_leisure_items_can_be_corrected_and_deleted_with_audit(self):
        execute_action(
            "leisure.item.save",
            {
                "itemId": "movie-2",
                "category": "movie",
                "title": "旧标题",
                "payload": {"genres": ["科幻"], "mood": "探索"},
            },
        )

        updated = execute_action(
            "leisure.item.update",
            {
                "itemId": "movie-2",
                "title": "新标题",
                "payload": {"genres": ["冒险"], "mood": "轻松"},
            },
            {"client": "unit-test", "confirmed": True},
        )

        self.assertEqual(updated["record"]["title"], "新标题")
        self.assertEqual(updated["record"]["payload"]["genres"], ["冒险"])
        self.assertEqual(store.get_leisure_item("movie-2")["title"], "新标题")

        deleted = execute_action(
            "leisure.item.delete",
            {"itemId": "movie-2"},
            {"client": "unit-test", "confirmed": True},
        )

        self.assertEqual(deleted["record"]["title"], "新标题")
        self.assertIsNone(store.get_leisure_item("movie-2"))
        event_types = {item["eventType"] for item in store.list_module_events("leisure", "", 20)}
        self.assertIn("item_updated", event_types)
        self.assertIn("item_deleted", event_types)

    def test_leisure_correction_actions_require_web_confirmation(self):
        execute_action(
            "leisure.item.save",
            {"itemId": "podcast-1", "category": "podcast", "title": "原始播客"},
        )

        blocked = execute_action(
            "leisure.item.update",
            {"itemId": "podcast-1", "title": "错误覆盖"},
            {"client": "web"},
        )

        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["error"], "confirmation_required")
        self.assertEqual(store.get_leisure_item("podcast-1")["title"], "原始播客")

    def test_airesearch_paper_search_action_is_read_only(self):
        overview = execute_action("airesearch.overview", {"limit": 2})
        result = execute_action("airesearch.paper.search", {"q": "attention", "limit": 2})
        queued = execute_action("airesearch.queue.add", {"title": "Agent memory paper", "note": "follow up"})

        self.assertTrue(overview["ok"])
        self.assertTrue(overview["overview"]["database"]["found"])
        self.assertIn("paperCount", overview["overview"]["database"])
        self.assertIn("candidateReview", overview["overview"])
        self.assertLessEqual(len(overview["overview"]["candidateReview"]["items"]), 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "airesearch.paper.search")
        self.assertEqual(result["query"], "attention")
        self.assertLessEqual(result["count"], 2)
        self.assertTrue(queued["event"]["requiresReview"])

    def test_airesearch_bridge_actions_have_runnable_default_args(self):
        from server.action_handlers import _build_airesearch_command_args

        self.assertEqual(
            _build_airesearch_command_args("airesearch.candidate.discover", {}),
            ["discover-candidates", "--profile", "multimodal_foundation_models", "--limit", "20"],
        )
        self.assertEqual(
            _build_airesearch_command_args(
                "airesearch.candidate.discover",
                {"profile": "embodied_ai_vla_robotics", "limit": 3},
            ),
            ["discover-candidates", "--profile", "embodied_ai_vla_robotics", "--limit", "3"],
        )
        self.assertIn("--out", _build_airesearch_command_args("airesearch.paper.review", {}))
        self.assertIn("--out", _build_airesearch_command_args("airesearch.cluster.generate", {}))
        self.assertIn("--out", _build_airesearch_command_args("airesearch.digest.generate", {}))

    def test_airesearch_bridge_action_sets_paper_db_path(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="candidate_review_exported total=0 selected=0 out=exports/mvp-current/candidate-review.json",
            stderr="",
        )
        with mock.patch("server.action_handlers.subprocess.run", return_value=completed) as run:
            result = execute_action("airesearch.paper.review", {}, {"client": "unit-test"})

        self.assertTrue(result["ok"])
        command = run.call_args.args[0]
        self.assertIn("export-candidate-review", command)
        self.assertIn("exports/mvp-current/candidate-review.json", command)
        env = run.call_args.kwargs["env"]
        self.assertTrue(env["PAPER_DB_PATH"].endswith("airesearch/data/paperpipe"))

    def test_cli_new_command_groups_are_available(self):
        env = os.environ.copy()
        commands = [
            [sys.executable, "-m", "niu_secretary.cli", "platform", "today", "--date", "today", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "platform", "modules", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "news", "validate-sources"],
            [sys.executable, "-m", "niu_secretary.cli", "news", "extract-json"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "summarize-day", "--date", "today"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "recommend-workout", "--date", "2026-06-14"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "list-nutrition", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "list-workouts", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "list-body-metrics", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "daily-summary", "--date", "today"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "list-recommendations", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "rollover-todos"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "list-events", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "list-todos", "--no-include-done", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "day-plan", "--date", "today"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "day-review", "--date", "today"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "task-history", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "leisure", "recommend", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "leisure", "recommend-daily", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "leisure", "list-items", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "leisure", "list-recommendations", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "airesearch", "overview", "--limit", "1"],
            [sys.executable, "-m", "niu_secretary.cli", "airesearch", "refresh-weekly"],
        ]
        for command in commands:
            completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)

        run_types = {run["runType"] for run in store.list_module_runs("news", 20)}
        self.assertIn("extract-json", run_types)

    def test_cli_module_commands_record_runs(self):
        env = os.environ.copy()
        commands = [
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "summarize-week", "--date", "2026-06-14"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "detect-conflicts", "--date", "2026-06-14"],
            [sys.executable, "-m", "niu_secretary.cli", "leisure", "history-search", "--q", "星际"],
            [sys.executable, "-m", "niu_secretary.cli", "airesearch", "paper-search", "--q", "attention", "--limit", "1"],
        ]
        for command in commands:
            completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)

        runs = store.list_module_runs(limit=20)
        run_types = {run["runType"] for run in runs}
        self.assertIn("summarize-week", run_types)
        self.assertIn("detect-conflicts", run_types)
        self.assertIn("history-search", run_types)
        self.assertIn("paper-search", run_types)

    def test_standard_lifecycle_cli_aliases_are_available(self):
        env = os.environ.copy()
        commands = [
            [sys.executable, "-m", "niu_secretary.cli", "platform", "health-check"],
            [sys.executable, "-m", "niu_secretary.cli", "platform", "derive"],
            [sys.executable, "-m", "niu_secretary.cli", "platform", "export"],
            [sys.executable, "-m", "niu_secretary.cli", "platform", "publish"],
            [sys.executable, "-m", "niu_secretary.cli", "platform", "run-daily"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "ingest"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "derive"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "export"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "publish"],
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "run-daily"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "ingest"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "derive"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "export"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "publish"],
            [sys.executable, "-m", "niu_secretary.cli", "schedule", "run-daily"],
            [sys.executable, "-m", "niu_secretary.cli", "leisure", "ingest"],
            [sys.executable, "-m", "niu_secretary.cli", "leisure", "derive"],
            [sys.executable, "-m", "niu_secretary.cli", "leisure", "publish"],
            [sys.executable, "-m", "niu_secretary.cli", "airesearch", "validate"],
        ]
        for command in commands:
            completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)

        runs = store.list_module_runs(limit=200)
        run_types = {run["runType"] for run in runs}
        for run_type in {"ingest", "derive", "export", "publish", "run-daily", "validate"}:
            self.assertIn(run_type, run_types)
        self.assertIn("health-check", run_types)
        self.assertTrue(os.path.exists(os.path.join("exports", "niu-secretary", "platform.json")))
        self.assertTrue(os.path.exists(os.path.join("exports", "niu-secretary", "fitness.json")))
        self.assertTrue(os.path.exists(os.path.join("exports", "niu-secretary", "schedule.json")))

    def test_platform_export_includes_business_snapshots(self):
        from niu_secretary.cli import _today_local

        today = _today_local()
        execute_action("fitness.nutrition.create", {"food": "鸡蛋", "date": today, "calories": 80})
        execute_action(
            "fitness.assessment.create",
            {"date": today, "goal": "fat_loss", "weightKg": 72, "bmi": 23, "fmsTotal": 15},
        )
        execute_action(
            "fitness.consult.create",
            {"date": today, "area": "膝", "text": "平台快照咨询", "payload": {"result": {"level": "low", "title": "降载"}}},
        )
        execute_action("fitness.summary.today", {"date": today})
        execute_action("fitness.recommend.meal", {"date": today})
        execute_action("schedule.todo.create", {"title": "写平台快照测试", "date": today, "priority": "high"})
        execute_action("schedule.day.plan", {"date": today})
        execute_action("schedule.day.review", {"date": today, "completed": 1, "note": "已完成"})
        execute_action("leisure.item.save", {"itemId": "movie-export-1", "category": "movie", "title": "测试电影"})
        execute_action("leisure.recommend", {"limit": 1})

        env = os.environ.copy()
        completed = subprocess.run(
            [sys.executable, "-m", "niu_secretary.cli", "platform", "export"],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        payload = exporters.read_json(os.path.join("exports", "niu-secretary", "platform.json"))
        snapshots = payload["snapshots"]
        self.assertTrue(snapshots["fitness"]["dailySummary"]["found"])
        self.assertEqual(snapshots["fitness"]["dailySummary"]["summary"]["summary"]["nutrition"]["count"], 1)
        self.assertGreaterEqual(snapshots["fitness"]["recommendations"]["count"], 1)
        self.assertTrue(snapshots["schedule"]["dayPlan"]["found"])
        self.assertTrue(snapshots["schedule"]["dayReview"]["found"])
        self.assertGreaterEqual(snapshots["schedule"]["taskHistory"]["count"], 0)
        self.assertGreaterEqual(snapshots["leisure"]["items"]["count"], 1)
        self.assertGreaterEqual(snapshots["leisure"]["history"]["count"], 1)
        self.assertGreaterEqual(snapshots["leisure"]["recommendations"]["count"], 1)
        self.assertTrue(snapshots["airesearch"]["overview"]["ok"])
        self.assertTrue(snapshots["airesearch"]["overview"]["overview"]["database"]["found"])
        self.assertIn("site", snapshots["airesearch"]["overview"]["overview"])

        completed = subprocess.run(
            [sys.executable, "-m", "niu_secretary.cli", "fitness", "export"],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        fitness_payload = exporters.read_json(os.path.join("exports", "niu-secretary", "fitness.json"))
        self.assertEqual(len(fitness_payload["assessments"]), 1)
        self.assertEqual(len(fitness_payload["consults"]), 1)

    def test_niu_core_helpers_are_audited_and_reusable(self):
        self.assertEqual(validators.require_date("2026-06-14"), "2026-06-14")
        self.assertEqual(validators.optional_time("09:30"), "09:30")
        self.assertEqual(validators.clamp_int(999, 0, 10), 10)

        export_path = os.path.join(self.tempdir.name, "exports", "payload.json")
        export = exporters.write_json(export_path, {"ok": True})
        self.assertGreater(export["bytes"], 0)
        self.assertEqual(exporters.read_json(export_path), {"ok": True})

        result = pipeline.Pipeline("fitness", "unit-pipeline", "test").step(
            "normalize",
            lambda payload: {**payload, "normalized": True},
        ).run({"raw": 1})
        self.assertTrue(result["payload"]["normalized"])

        profile = profiles.update("fitness", {"goal": "fat_loss"}, "unit test", "test")
        self.assertEqual(profile["profile"]["goal"], "fat_loss")
        self.assertEqual(profiles.get("fitness")["profile"]["goal"], "fat_loss")

        cron_result = cron.run_job("schedule", "unit-cron", lambda: {"done": True})
        self.assertTrue(cron_result["ok"])

        model_call = llm.record_call("news", "unit", "fake-model", "input", "output", "passed", 12)
        self.assertEqual(model_call["status"], "passed")

        with store.connect() as connection:
            runs = connection.execute("SELECT COUNT(*) FROM module_runs").fetchone()[0]
            calls = connection.execute("SELECT COUNT(*) FROM model_calls").fetchone()[0]
            exported = exporters.read_json(export_path)
        self.assertGreaterEqual(runs, 2)
        self.assertEqual(calls, 1)
        self.assertTrue(exported["ok"])

    def test_http_get_routes_map_to_audited_actions(self):
        route = get_action_route("/niu-secretary/api/platform/runs?module=news&limit=2")
        self.assertEqual(route, ("platform.runs.list", {"module": "news", "limit": 2}))

        route = get_action_route("/niu-secretary/api/platform/today?date=2026-06-14&limit=3")
        self.assertEqual(route, ("platform.today.context", {"date": "2026-06-14", "limit": 3}))

        route = get_action_route("/niu-secretary/api/platform/today?limit=3")
        self.assertEqual(route[0], "platform.today.context")
        self.assertRegex(route[1]["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(route[1]["limit"], 3)

        route = get_action_route("/niu-secretary/api/platform/modules?limit=1")
        self.assertEqual(route, ("platform.modules.status", {"limit": 1}))

        route = get_action_route("/niu-secretary/api/platform/ops?module=fitness&status=passed&requiresReview=false&limit=12")
        self.assertEqual(
            route,
            ("platform.ops.center", {"module": "fitness", "status": "passed", "requiresReview": False, "limit": 12}),
        )

        route = get_action_route("/niu-secretary/api/platform/cron")
        self.assertEqual(route, ("platform.cron.registry", {}))

        route = get_action_route("/niu-secretary/api/profile?module=fitness")
        self.assertEqual(route, ("profile.get", {"module": "fitness"}))

        route = get_action_route("/niu-secretary/api/profile/changes?module=fitness&limit=2")
        self.assertEqual(route, ("profile.changes", {"module": "fitness", "limit": 2}))

        route = get_action_route("/niu-secretary/api/fitness/recommendations?date=2026-06-14&type=meal&limit=2")
        self.assertEqual(route, ("fitness.recommendations.list", {"date": "2026-06-14", "type": "meal", "limit": 2}))

        route = get_action_route("/niu-secretary/api/fitness/nutrition?from=2026-06-01&to=2026-06-14&limit=20")
        self.assertEqual(
            route,
            ("fitness.nutrition.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 20}),
        )

        route = get_action_route("/niu-secretary/api/fitness/workouts?from=2026-06-01&to=2026-06-14&limit=20")
        self.assertEqual(
            route,
            ("fitness.workout.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 20}),
        )

        route = get_action_route("/niu-secretary/api/fitness/body-metrics?from=2026-06-01&to=2026-06-14&limit=20")
        self.assertEqual(
            route,
            ("fitness.body_metric.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 20}),
        )

        route = get_action_route("/niu-secretary/api/fitness/recovery?from=2026-06-01&to=2026-06-14&limit=20")
        self.assertEqual(
            route,
            ("fitness.recovery.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 20}),
        )

        route = get_action_route("/niu-secretary/api/fitness/assessments?from=2026-06-01&to=2026-06-14&limit=20")
        self.assertEqual(
            route,
            ("fitness.assessment.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 20}),
        )

        route = get_action_route("/niu-secretary/api/fitness/consults?from=2026-06-01&to=2026-06-14&limit=20")
        self.assertEqual(
            route,
            ("fitness.consult.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 20}),
        )

        route = get_action_route("/niu-secretary/api/fitness/daily-summary?date=2026-06-14")
        self.assertEqual(route, ("fitness.daily_summary.get", {"date": "2026-06-14"}))

        route = get_action_route("/niu-secretary/api/schedule/events?from=2026-06-01&to=2026-06-14&limit=20")
        self.assertEqual(
            route,
            ("schedule.event.list", {"from": "2026-06-01", "to": "2026-06-14", "limit": 20}),
        )

        route = get_action_route("/niu-secretary/api/schedule/todos?includeDone=false&limit=20")
        self.assertEqual(route, ("schedule.todo.list", {"includeDone": False, "limit": 20}))

        route = get_action_route("/niu-secretary/api/schedule/important-dates?limit=20")
        self.assertEqual(route, ("schedule.important_date.list", {"limit": 20}))

        route = get_action_route("/niu-secretary/api/schedule/goals?limit=20")
        self.assertEqual(route, ("schedule.goal.list", {"limit": 20}))

        route = get_action_route("/niu-secretary/api/schedule/day-plan?date=2026-06-14")
        self.assertEqual(route, ("schedule.day_plan.get", {"date": "2026-06-14"}))

        route = get_action_route("/niu-secretary/api/schedule/day-review?date=2026-06-14")
        self.assertEqual(route, ("schedule.day_review.get", {"date": "2026-06-14"}))

        route = get_action_route("/niu-secretary/api/schedule/recommend?date=2026-06-14")
        self.assertEqual(route, ("schedule.recommend", {"date": "2026-06-14"}))

        route = get_action_route("/niu-secretary/api/schedule/task-history?todoId=todo-1&limit=2")
        self.assertEqual(route, ("schedule.task_history.list", {"todoId": "todo-1", "limit": 2}))

        route = get_action_route("/niu-secretary/api/leisure/recommendations?date=2026-06-14&limit=2")
        self.assertEqual(route, ("leisure.recommendations.list", {"date": "2026-06-14", "limit": 2}))

        route = get_action_route("/niu-secretary/api/leisure/items?category=movie&limit=2")
        self.assertEqual(route, ("leisure.items.list", {"category": "movie", "limit": 2}))

        route = get_action_route("/niu-secretary/api/leisure/profile/suggestions?limit=2")
        self.assertEqual(route, ("leisure.profile.suggestions", {"limit": 2}))

        route = get_action_route("/niu-secretary/api/airesearch/overview?limit=2")
        self.assertEqual(route, ("airesearch.overview", {"limit": 2}))

        route = get_action_route("/niu-secretary/api/airesearch/papers/search?q=attention&limit=2")
        self.assertEqual(route, ("airesearch.paper.search", {"q": "attention", "limit": 2}))

        route = get_action_route(
            "/niu-secretary/api/news/search?date=2026-06-14&section=domestic&tag=%E9%98%B2%E6%B1%9B&source=%E5%A4%AE%E8%A7%86&limit=2"
        )
        self.assertEqual(
            route,
            (
                "news.search",
                {
                    "date": "2026-06-14",
                    "section": "domestic",
                    "tag": "防汛",
                    "source": "央视",
                    "limit": 2,
                },
            ),
        )

        route = get_action_route("/niu-secretary/api/platform/events?module=leisure&eventType=profile_suggestion&requiresReview=true&limit=2")
        self.assertEqual(
            route,
            (
                "platform.events.list",
                {"module": "leisure", "eventType": "profile_suggestion", "requiresReview": True, "limit": 2},
            ),
        )

        execute_action("fitness.nutrition.create", {"food": "鸡蛋", "date": "2026-06-14"})
        action_name, payload = get_action_route("/niu-secretary/api/fitness/summary/today?date=2026-06-14")
        result = execute_action(action_name, payload, {"client": "web"})
        self.assertEqual(result["summary"]["count"], 1)

        execute_action("schedule.todo.create", {"title": "只读路由测试", "date": "2026-06-14"})
        action_name, payload = get_action_route("/niu-secretary/api/schedule/todos?includeDone=false&limit=5")
        result = execute_action(action_name, payload, {"client": "web"})
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["items"][0]["done"])

        route = get_action_route("/niu-secretary/api/leisure/recommend?limit=2&availableMinutes=35&scheduleLoad=4&mood=relaxed")
        self.assertEqual(
            route,
            ("leisure.recommend", {"limit": 2, "availableMinutes": 35, "scheduleLoad": 4, "mood": "relaxed"}),
        )

        self.assertIsNone(get_action_route("/niu-secretary/api/not-found"))

    def test_documented_get_routes_resolve_to_registered_actions(self):
        from server.actions import _HANDLERS
        from server.capabilities import CAPABILITIES

        capabilities = {item["name"] for item in CAPABILITIES}
        examples = [
            "/niu-secretary/api/platform/runs?module=news&limit=2",
            "/niu-secretary/api/platform/events?module=leisure&eventType=profile_suggestion&requiresReview=true&limit=2",
            "/niu-secretary/api/platform/today?limit=3",
            "/niu-secretary/api/platform/modules?limit=1",
            "/niu-secretary/api/platform/ops?module=fitness&status=passed&requiresReview=false&limit=12",
            "/niu-secretary/api/platform/cron",
            "/niu-secretary/api/profile?module=fitness",
            "/niu-secretary/api/profile/changes?module=fitness&limit=2",
            "/niu-secretary/api/news/search?q=AI&section=ai&tag=Agent&limit=2",
            "/niu-secretary/api/news/recommend?limit=2",
            "/niu-secretary/api/fitness/summary/today?date=2026-06-14",
            "/niu-secretary/api/fitness/summary/weekly?date=2026-06-14",
            "/niu-secretary/api/fitness/nutrition?from=2026-06-01&to=2026-06-14&limit=20",
            "/niu-secretary/api/fitness/workouts?from=2026-06-01&to=2026-06-14&limit=20",
            "/niu-secretary/api/fitness/body-metrics?from=2026-06-01&to=2026-06-14&limit=20",
            "/niu-secretary/api/fitness/daily-summary?date=2026-06-14",
            "/niu-secretary/api/fitness/recommendations?date=2026-06-14&type=meal&limit=2",
            "/niu-secretary/api/schedule/summary/today?date=2026-06-14",
            "/niu-secretary/api/schedule/events?from=2026-06-01&to=2026-06-14&limit=20",
            "/niu-secretary/api/schedule/todos?includeDone=false&limit=20",
            "/niu-secretary/api/schedule/day-plan?date=2026-06-14",
            "/niu-secretary/api/schedule/day-review?date=2026-06-14",
            "/niu-secretary/api/schedule/conflicts?date=2026-06-14",
            "/niu-secretary/api/schedule/recommend?date=2026-06-14",
            "/niu-secretary/api/schedule/task-history?todoId=todo-1&limit=2",
            "/niu-secretary/api/leisure/recommend?limit=2&availableMinutes=35&scheduleLoad=4&mood=relaxed",
            "/niu-secretary/api/leisure/recommendations?date=2026-06-14&limit=2",
            "/niu-secretary/api/leisure/items?category=movie&limit=2",
            "/niu-secretary/api/leisure/history?q=%E7%A7%91%E5%B9%BB&limit=2",
            "/niu-secretary/api/leisure/profile/suggestions?limit=2",
            "/niu-secretary/api/airesearch/overview?limit=2",
            "/niu-secretary/api/airesearch/papers/search?q=attention&limit=2",
        ]

        for url in examples:
            with self.subTest(url=url):
                route = get_action_route(url)
                self.assertIsNotNone(route)
                action_name, _payload = route
                self.assertIn(action_name, capabilities)
                self.assertIn(action_name, _HANDLERS)

    def test_schedule_page_does_not_render_fake_timeline_items(self):
        from pathlib import Path

        html = Path("schedule/dist/index.html").read_text(encoding="utf-8")

        self.assertNotIn("晨间梳理", html)
        self.assertNotIn("项目推进", html)
        self.assertIn("今天暂无日程", html)
        self.assertIn("${h(task.title)}", html)
        self.assertIn("${h(task.note)}", html)
        self.assertIn("${h(task.type)}", html)

    def test_schedule_page_reads_api_before_offline_cache(self):
        from pathlib import Path

        html = Path("schedule/dist/index.html").read_text(encoding="utf-8")
        store_js = Path("schedule/dist/js/store.js")

        self.assertIn("const API_BASE = '/niu-secretary/api'", html)
        self.assertIn("const ACTION_API = '/niu-secretary/api/actions/execute'", html)
        self.assertIn("getJson(`/schedule/events?", html)
        self.assertIn("getJson('/schedule/todos?includeDone=true&limit=100')", html)
        self.assertIn("getJson('/schedule/important-dates?limit=100')", html)
        self.assertIn("getJson('/schedule/goals?limit=100')", html)
        self.assertIn("const offlineCache = {", html)
        self.assertIn("offlineCache.write('niu_schedule_events', items)", html)
        self.assertIn("offlineCache.write('niu_schedule_todos', items)", html)
        self.assertIn("offlineCache.write('niu_schedule_dates', items)", html)
        self.assertIn("offlineCache.write('niu_schedule_goals', items)", html)
        self.assertIn("return offlineCache.read('niu_schedule_events')", html)
        self.assertIn("return offlineCache.read('niu_schedule_todos')", html)
        self.assertIn("return offlineCache.read('niu_schedule_dates')", html)
        self.assertIn("return offlineCache.read('niu_schedule_goals')", html)
        self.assertLess(html.index("const res = await getJson(`/schedule/events?"), html.index("return offlineCache.read('niu_schedule_events')"))
        self.assertLess(html.index("const res = await getJson('/schedule/todos?includeDone=true&limit=100')"), html.index("return offlineCache.read('niu_schedule_todos')"))
        self.assertLess(html.index("const res = await getJson('/schedule/important-dates?limit=100')"), html.index("return offlineCache.read('niu_schedule_dates')"))
        self.assertLess(html.index("const res = await getJson('/schedule/goals?limit=100')"), html.index("return offlineCache.read('niu_schedule_goals')"))
        self.assertNotIn("function readJson", html)
        self.assertNotIn("function writeCache", html)
        self.assertNotIn("dates / goals 后端暂未建模", html)
        self.assertFalse(store_js.exists())

    def test_fitness_dashboard_body_metrics_use_unified_api(self):
        from pathlib import Path

        dashboard_js = Path("fitness/dist/js/features/dashboard.js").read_text(encoding="utf-8")
        action_api_js = Path("fitness/dist/js/lib/actionApi.js").read_text(encoding="utf-8")
        dashboard_html = Path("fitness/dist/sections/dashboard.html").read_text(encoding="utf-8")

        self.assertIn("createUnifiedBodyMetric", dashboard_js)
        self.assertIn("fetchUnifiedBodyMetrics", dashboard_js)
        self.assertIn("/fitness/body-metrics", action_api_js)
        self.assertIn("serverId", dashboard_js)
        self.assertIn("syncStatus === 'pending'", dashboard_js)
        self.assertIn("includeLocalCache: unifiedWeight.offline", dashboard_js)
        self.assertNotIn("保存在浏览器本地。", dashboard_html)
        self.assertIn("在线读取统一 API；接口不可用时使用浏览器离线缓存。", dashboard_html)

    def test_fitness_dashboard_profile_is_api_first_and_no_local_import(self):
        from pathlib import Path

        src_dashboard_js = Path("fitness/src/js/features/dashboard.js").read_text(encoding="utf-8")
        dashboard_js = Path("fitness/dist/js/features/dashboard.js").read_text(encoding="utf-8")
        action_api_js = Path("fitness/dist/js/lib/actionApi.js").read_text(encoding="utf-8")
        dashboard_html = Path("fitness/dist/sections/dashboard.html").read_text(encoding="utf-8")

        self.assertIn("fetchUnifiedFitnessProfile", dashboard_js)
        self.assertIn("/profile?module=fitness", action_api_js)
        submit_branch = dashboard_js[
            dashboard_js.index("updateUnifiedFitnessProfile(profile)"):
            dashboard_js.index("document.getElementById('clear-logs')")
        ]
        self.assertLess(submit_branch.index("updateUnifiedFitnessProfile(profile)"), submit_branch.index("syncStatus: 'synced'"))
        self.assertIn("syncStatus: 'pending'", dashboard_js)
        self.assertIn("source: 'offline-cache'", dashboard_js)
        self.assertNotIn("importAllData", src_dashboard_js)
        self.assertNotIn("importAllData", dashboard_js)
        src_db_js = Path("fitness/src/js/lib/db.js").read_text(encoding="utf-8")
        dist_db_js = Path("fitness/dist/js/lib/db.js").read_text(encoding="utf-8")
        self.assertNotIn("importAllData", src_db_js)
        self.assertNotIn("importAllData", dist_db_js)
        self.assertNotIn("countPendingSync", src_db_js)
        self.assertNotIn("countPendingSync", dist_db_js)
        self.assertNotIn("import-json", dashboard_html)
        self.assertNotIn("导入 JSON", dashboard_html)
        self.assertNotIn("FileReader", dashboard_js)
        self.assertNotIn('type="file"', dashboard_html)
        self.assertIn("导出离线缓存", dashboard_html)
        self.assertIn("exportAllData", dashboard_js)
        self.assertIn("清空离线缓存", dashboard_html)
        self.assertIn("读取和保存走统一 API；离线时仅保留浏览器缓存。", dashboard_html)

    def test_fitness_pages_do_not_ship_demo_seed_writes(self):
        from pathlib import Path

        files = {
            "src_dashboard_js": Path("fitness/src/js/features/dashboard.js").read_text(encoding="utf-8"),
            "src_training_js": Path("fitness/src/js/features/training.js").read_text(encoding="utf-8"),
            "src_dashboard_html": Path("fitness/src/sections/dashboard.html").read_text(encoding="utf-8"),
            "src_training_html": Path("fitness/src/sections/training.html").read_text(encoding="utf-8"),
            "dashboard_js": Path("fitness/dist/js/features/dashboard.js").read_text(encoding="utf-8"),
            "training_js": Path("fitness/dist/js/features/training.js").read_text(encoding="utf-8"),
            "dashboard_html": Path("fitness/dist/sections/dashboard.html").read_text(encoding="utf-8"),
            "training_html": Path("fitness/dist/sections/training.html").read_text(encoding="utf-8"),
        }
        combined = "\n".join(files.values())

        self.assertNotIn("seed-demo", combined)
        self.assertNotIn("seed-training", combined)
        self.assertNotIn("seedDemo", combined)
        self.assertNotIn("seedTraining", combined)
        self.assertNotIn("填充示例", combined)
        self.assertNotIn("填充训练示例", combined)
        self.assertNotIn("示例数据已写入本地", combined)

    def test_fitness_training_logs_merge_unified_api(self):
        from pathlib import Path

        training_js = Path("fitness/dist/js/features/training.js").read_text(encoding="utf-8")
        action_api_js = Path("fitness/dist/js/lib/actionApi.js").read_text(encoding="utf-8")
        training_html = Path("fitness/dist/sections/training.html").read_text(encoding="utf-8")

        self.assertIn("fetchUnifiedWorkoutLogs", training_js)
        self.assertIn("mergeTrainingLogs", training_js)
        self.assertIn("serverId", training_js)
        self.assertIn("syncStatus === 'pending'", training_js)
        self.assertIn("includeLocalCache: unifiedWorkouts.offline", training_js)
        self.assertIn("/fitness/workouts", action_api_js)
        self.assertIn("parseWorkoutNote", action_api_js)
        self.assertIn("slugExerciseName", action_api_js)
        self.assertIn("在线读取统一 API；IndexedDB 只补充离线待同步记录。", training_html)
        self.assertNotIn("每条记录都进入同步队列", training_html)
        self.assertNotIn("清空训练记录", training_html)
        self.assertIn("清空离线缓存", training_html)
        self.assertIn("训练离线缓存已清空，服务器记录不受影响", training_js)

    def test_fitness_recovery_logs_use_unified_api(self):
        from pathlib import Path

        recovery_js = Path("fitness/dist/js/features/recovery.js").read_text(encoding="utf-8")
        training_js = Path("fitness/dist/js/features/training.js").read_text(encoding="utf-8")
        dashboard_js = Path("fitness/dist/js/features/dashboard.js").read_text(encoding="utf-8")
        action_api_js = Path("fitness/dist/js/lib/actionApi.js").read_text(encoding="utf-8")
        recovery_html = Path("fitness/dist/sections/recovery.html").read_text(encoding="utf-8")

        self.assertIn("createUnifiedRecoveryLog", recovery_js)
        self.assertIn("fetchUnifiedRecoveryLogs", recovery_js)
        self.assertIn("mergeRecoveryLogs", recovery_js)
        self.assertIn("fetchUnifiedRecoveryLogs", training_js)
        self.assertIn("fetchUnifiedRecoveryLogs", dashboard_js)
        self.assertIn("fitness.recovery.create", action_api_js)
        self.assertIn("/fitness/recovery", action_api_js)
        self.assertIn("serverId", recovery_js)
        self.assertIn("syncStatus === 'pending'", recovery_js)
        self.assertIn("includeLocalCache: unified.offline", recovery_js)
        self.assertIn("在线读取统一 API；接口不可用时使用浏览器离线缓存。", recovery_html)
        self.assertNotIn(">清空恢复<", recovery_html)
        self.assertNotIn("清空本地恢复", recovery_html)
        self.assertIn("清空离线缓存", recovery_html)
        self.assertIn("恢复离线缓存已清空，服务器记录不受影响", recovery_js)

    def test_fitness_nutrition_reads_api_before_indexeddb_cache(self):
        from pathlib import Path

        nutrition_js = Path("fitness/dist/js/features/nutrition.js").read_text(encoding="utf-8")
        nutrition_html = Path("fitness/dist/sections/nutrition.html").read_text(encoding="utf-8")

        self.assertIn("fetchUnifiedNutritionLogs", nutrition_js)
        self.assertIn("fetchUnifiedWorkoutLogs", nutrition_js)
        self.assertIn("includeLocalCache: unified.offline", nutrition_js)
        self.assertIn("syncStatus === 'pending'", nutrition_js)
        self.assertIn("统一动作接口读取失败，使用本地离线缓存", nutrition_js)
        self.assertIn("在线读取统一 API；IndexedDB 只补充离线待同步记录。", nutrition_html)
        self.assertNotIn("Agent、估算和手动记录都会进 IndexedDB 与同步队列", nutrition_html)
        self.assertNotIn("清空饮食", nutrition_html)
        self.assertIn("清空离线缓存", nutrition_html)
        self.assertIn("饮食离线缓存已清空，服务器记录不受影响", nutrition_js)

    def test_fitness_assessment_and_consult_pages_use_unified_api(self):
        from pathlib import Path

        assessment_js = Path("fitness/dist/js/features/assessment.js").read_text(encoding="utf-8")
        consult_js = Path("fitness/dist/js/features/consult.js").read_text(encoding="utf-8")
        action_api_js = Path("fitness/dist/js/lib/actionApi.js").read_text(encoding="utf-8")
        assessment_html = Path("fitness/dist/sections/assessment.html").read_text(encoding="utf-8")
        consult_html = Path("fitness/dist/sections/consult.html").read_text(encoding="utf-8")

        self.assertIn("createUnifiedAssessmentLog", assessment_js)
        self.assertIn("fetchUnifiedAssessmentLogs", assessment_js)
        self.assertIn("createUnifiedConsultLog", consult_js)
        self.assertIn("fetchUnifiedConsultLogs", consult_js)
        self.assertIn("fitness.assessment.create", action_api_js)
        self.assertIn("/fitness/assessments", action_api_js)
        self.assertIn("fitness.consult.create", action_api_js)
        self.assertIn("/fitness/consults", action_api_js)
        self.assertIn("syncStatus === 'pending'", assessment_js)
        self.assertIn("syncStatus === 'pending'", consult_js)
        self.assertIn("在线读取统一 API；IndexedDB 只补充离线待同步记录。", assessment_html)
        self.assertIn("在线读取统一 API；IndexedDB 只补充离线待同步记录。", consult_html)
        self.assertNotIn("最近记录保存在 IndexedDB", assessment_html)

    def test_news_recommendations_do_not_fallback_to_frontend_ranking(self):
        from pathlib import Path

        html = Path("news-daily/dist/index.html").read_text(encoding="utf-8")

        self.assertIn('callAction("news.recommend"', html)
        self.assertIn("const fallbackTpl =", html)
        fallback_block = html[html.index("const fallbackTpl ="):html.index("const detailId = getDetailIdFromCard")]
        self.assertIn("nextElementSibling", fallback_block)
        self.assertIn('tagName === "TEMPLATE"', fallback_block)
        self.assertIn("detail-missing", html)
        self.assertNotIn("buildLocalRecommendations", html)
        self.assertNotIn("localFallback", html)
        self.assertNotIn("接口暂不可用，已用本地五版要闻", html)
        self.assertNotIn("fallbackRecommendations", html)

    def test_leisure_home_recommendations_are_api_owned(self):
        from pathlib import Path

        html = Path("leisure/dist/index.html").read_text(encoding="utf-8")
        css = Path("leisure/dist/style.css").read_text(encoding="utf-8")

        self.assertIn("getLeisureJson('/leisure/recommend?limit=2')", html)
        self.assertIn("今晚首推暂不可用", html)
        self.assertIn("href: 'movies.html'", html)
        self.assertIn("href: 'music.html'", html)
        self.assertIn("href: 'podcasts.html'", html)
        self.assertIn("href: 'novels.html'", html)
        self.assertIn("feature-empty", css)
        self.assertNotIn("失败回落到默认顺序", html)
        self.assertNotIn("musicData.slice(0, 1)", html)
        self.assertNotIn("podcastsData.slice(0, 1)", html)
        self.assertNotIn("novelsData.slice(0, 1)", html)
        self.assertNotIn("短片 / 剧集", html)
        self.assertNotIn("音乐电台", html)
        self.assertNotIn('${cat.type}.html', html)
        self.assertNotIn("影视.html", html)
        self.assertNotIn("音乐.html", html)
        self.assertNotIn("播客.html", html)
        self.assertNotIn("小说.html", html)

    def test_leisure_feedback_scripts_write_through_action_api(self):
        from pathlib import Path

        nav_js = Path("leisure/dist/js/nav.js").read_text(encoding="utf-8")
        recommend_js = Path("leisure/dist/js/recommend.js").read_text(encoding="utf-8")
        offline_js = Path("leisure/dist/js/offline-feedback.js").read_text(encoding="utf-8")
        html_files = [
            Path("leisure/dist/index.html"),
            Path("leisure/dist/movies.html"),
            Path("leisure/dist/music.html"),
            Path("leisure/dist/podcasts.html"),
            Path("leisure/dist/novels.html"),
        ]
        store_js = Path("leisure/dist/js/store.js")

        self.assertIn("/niu-secretary/api/actions/execute", nav_js)
        self.assertIn("/niu-secretary/api/actions/execute", recommend_js)
        self.assertIn("leisure.item.save", recommend_js)
        self.assertIn("leisure.item.rate", recommend_js)
        self.assertIn("leisure.item.dismiss", recommend_js)
        self.assertIn("flushPendingLeisureFeedback", nav_js)
        self.assertIn("niu_leisure_pending_feedback", offline_js)
        self.assertIn("window.LeisureOfflineFeedbackQueue", offline_js)
        self.assertIn("LeisureOfflineFeedbackQueue.enqueue", nav_js)
        self.assertIn("LeisureOfflineFeedbackQueue.list", nav_js)
        self.assertIn("LeisureOfflineFeedbackQueue.replace", nav_js)
        self.assertIn("LeisureOfflineFeedbackQueue.enqueue", recommend_js)
        self.assertNotIn("localStorage.getItem", nav_js)
        self.assertNotIn("localStorage.setItem", nav_js)
        self.assertNotIn("localStorage.removeItem", nav_js)
        self.assertNotIn("localStorage.getItem", recommend_js)
        self.assertNotIn("localStorage.setItem", recommend_js)
        for html_file in html_files:
            html = html_file.read_text(encoding="utf-8")
            self.assertLess(html.index("js/offline-feedback.js"), html.index("js/nav.js"))
        self.assertNotIn("Store.addRating", recommend_js)
        self.assertNotIn("Store.addToCollection", recommend_js)
        self.assertNotIn("Store.getPreferences", recommend_js)
        self.assertNotIn("Store.getRatings", recommend_js)
        self.assertNotIn("import Store", recommend_js)
        self.assertFalse(store_js.exists())

    def test_web_get_readonly_context_does_not_write_derived_business_tables(self):
        execute_action("fitness.nutrition.create", {"food": "鸡蛋", "date": "2026-06-14"})

        action_name, payload = get_action_route("/niu-secretary/api/fitness/summary/today?date=2026-06-14")
        result = execute_action(action_name, payload, {"client": "web", "readOnly": True})
        self.assertEqual(result["summary"]["count"], 1)
        self.assertIsNone(result["savedSummary"])
        self.assertFalse(execute_action("fitness.daily_summary.get", {"date": "2026-06-14"})["found"])

    def test_web_interaction_verifier_covers_productized_boundaries(self):
        from pathlib import Path

        script = Path("scripts/verify_web_interactions.py").read_text(encoding="utf-8")

        self.assertIn("tempfile.mkdtemp", script)
        self.assertIn("server.niu_secretary_api", script)
        self.assertIn("google-chrome", script)
        self.assertIn("fitness.nutrition.create", script)
        self.assertIn("fitness.workout.create", script)
        self.assertIn("fitness.body_metric.create", script)
        self.assertIn("fitness.recovery.create", script)
        self.assertIn("schedule.event.create", script)
        self.assertIn("schedule.todo.create", script)
        self.assertIn("schedule.day.plan", script)
        self.assertIn("leisure.item.rate", script)
        self.assertIn("news.recommend", script)
        self.assertIn("fitness/index.html", script)
        self.assertIn("schedule/index.html", script)
        self.assertIn("leisure/index.html", script)

    def test_admin_console_is_api_first_and_module_scoped(self):
        from pathlib import Path
        from server.niu_secretary_api import ADMIN_READ_ROUTES, sign_admin_token, verify_admin_token

        html = Path("dist/admin/index.html").read_text(encoding="utf-8")
        css = Path("dist/admin/admin.css").read_text(encoding="utf-8")
        js = Path("dist/admin/admin.js").read_text(encoding="utf-8")
        vue_airesearch_admin = Path("web/src/modules/admin/AdminAIResearchPage.vue").read_text(encoding="utf-8")
        vue_styles = Path("web/src/shared/styles/global.css").read_text(encoding="utf-8")

        for label in ("新闻社", "塑形馆", "时务局", "闲趣集", "研知库"):
            self.assertIn(label, html)
        self.assertIn("管理员登录", html)
        self.assertIn("data-login-form", html)
        self.assertIn("data-record-dialog", html)
        self.assertIn('data-module="news"', html)
        self.assertIn('data-module="fitness"', html)
        self.assertIn('data-module="schedule"', html)
        self.assertIn('data-module="leisure"', html)
        self.assertIn('data-module="airesearch"', html)
        self.assertNotIn("/niu-secretary/airesearch/admin/", html)
        self.assertIn("grid-template-columns: 280px minmax(0, 1fr)", css)
        self.assertIn(".login-screen", css)
        self.assertIn(".data-table", css)
        self.assertIn('const API_BASE = "/niu-secretary/api"', js)
        self.assertIn('const TOKEN_KEY = "niu-secretary-admin-token"', js)
        self.assertIn('publicPost("/admin/session"', js)
        self.assertIn('adminData("platform.ops")', js)
        self.assertIn('adminPost("/admin/actions/execute"', js)
        self.assertIn("data-edit-id", js)
        self.assertIn("data-delete-id", js)
        self.assertIn("schedule.todo.toggle", js)
        self.assertIn("news.topic.queue-research", js)
        self.assertIn("fitness.nutrition.create", js)
        self.assertIn("fitness.nutrition.update", js)
        self.assertIn("fitness.nutrition.delete", js)
        self.assertIn("schedule.todo.create", js)
        self.assertIn("schedule.event.update", js)
        self.assertIn("leisure.item.update", js)
        self.assertIn("leisure.item.delete", js)
        self.assertIn("airesearch.queue.add", js)
        self.assertIn("airesearch.admin.state", vue_airesearch_admin)
        self.assertIn("airesearch.admin.paper.update", vue_airesearch_admin)
        self.assertIn("airesearch.admin.profile.create", vue_airesearch_admin)
        self.assertIn("airesearch.admin.job.start", vue_airesearch_admin)
        self.assertIn("论文管理", vue_airesearch_admin)
        self.assertIn("证据检查器", vue_airesearch_admin)
        self.assertIn("Layout Evidence Inspector", vue_airesearch_admin)
        self.assertIn("layoutInspectorVisible", vue_airesearch_admin)
        self.assertIn('transition="none"', vue_airesearch_admin)
        self.assertIn('aria-label="关闭证据检查器"', vue_airesearch_admin)
        self.assertIn('@click="layoutInspectorVisible = false"', vue_airesearch_admin)
        self.assertIn("layoutCapabilityItems", vue_airesearch_admin)
        self.assertIn("layoutEvidenceBlocks", vue_airesearch_admin)
        self.assertIn('label="事实关联"', vue_airesearch_admin)
        self.assertIn("layoutGraphFactRows", vue_airesearch_admin)
        self.assertIn("layoutEvidenceGraph", vue_airesearch_admin)
        self.assertIn("graphMatchMethodLabel", vue_airesearch_admin)
        self.assertIn("paperRequestToken", vue_airesearch_admin)
        self.assertIn("layoutRequestToken", vue_airesearch_admin)
        self.assertIn("selectedPaperKey.value !== paperKey", vue_airesearch_admin)
        self.assertIn("layoutOcrErrorText", vue_airesearch_admin)
        self.assertIn("quality-mid", vue_airesearch_admin)
        self.assertIn("airesearch-layout-inspector", vue_airesearch_admin)
        self.assertIn(".airesearch-layout-inspector-dialog.el-dialog", vue_styles)
        self.assertIn(".airesearch-layout-graph-row", vue_styles)
        self.assertIn(".airesearch-layout-graph-link", vue_styles)
        self.assertIn("height: min(840px, calc(100dvh - 64px))", vue_styles)
        self.assertIn(".admin-resource {\n  animation: none;", vue_styles)
        self.assertIn("to { opacity: 1; transform: none; }", vue_styles)
        self.assertIn("搜索配置", vue_airesearch_admin)
        self.assertIn("任务中心", vue_airesearch_admin)
        self.assertNotIn("/niu-secretary/airesearch/admin/", vue_airesearch_admin)
        self.assertIn("leisure.items", ADMIN_READ_ROUTES)
        self.assertEqual(
            ADMIN_READ_ROUTES.get("airesearch.admin.paper.blog.detail"),
            ("airesearch.admin.paper.blog.detail", {"paperKey": ""}),
        )
        self.assertEqual(
            ADMIN_READ_ROUTES.get("airesearch.admin.paper.layout.detail"),
            ("airesearch.admin.paper.layout.detail", {"paperKey": ""}),
        )
        self.assertEqual(verify_admin_token(sign_admin_token("admin")), "admin")
        self.assertNotIn("indexedDB", js)
        self.assertNotIn("innerHTML = local", js)

        workout = execute_action(
            "fitness.recommend.workout",
            {"date": "2026-06-14"},
            {"client": "web", "readOnly": True},
        )
        self.assertTrue(workout["recommendations"])
        self.assertIsNone(workout["recommendationRecord"])
        self.assertEqual(store.list_fitness_recommendations("2026-06-14", "workout"), [])

        leisure = execute_action(
            "leisure.recommend",
            {"date": "2026-06-14", "limit": 1},
            {"client": "web", "readOnly": True},
        )
        self.assertTrue(leisure["groups"])
        self.assertIsNone(leisure["recommendationRecord"])
        self.assertEqual(store.list_leisure_recommendations("2026-06-14"), [])
        self.assertEqual(store.list_leisure_items(limit=5), [])

    def test_vue_rebuild_uses_real_routes_and_component_library_policy(self):
        from pathlib import Path
        from server.niu_secretary_api import ADMIN_READ_ROUTES

        package = Path("web/package.json").read_text(encoding="utf-8")
        vite = Path("web/vite.config.ts").read_text(encoding="utf-8")
        router = Path("web/src/app/router/index.ts").read_text(encoding="utf-8")
        main = Path("web/src/main.ts").read_text(encoding="utf-8")
        admin_page = Path("web/src/modules/admin/AdminResourcePage.vue").read_text(encoding="utf-8")
        admin_layout = Path("web/src/modules/admin/AdminDashboard.vue").read_text(encoding="utf-8")
        admin_feedback = Path("web/src/shared/lib/adminFeedback.ts").read_text(encoding="utf-8")
        admin_feedback_bar = Path("web/src/shared/components/AdminFeedbackBar.vue").read_text(encoding="utf-8")
        admin_styles = Path("web/src/shared/styles/global.css").read_text(encoding="utf-8")

        self.assertIn('"vue"', package)
        self.assertIn('"element-plus"', package)
        self.assertIn('"echarts"', package)
        self.assertIn('"@vueuse/core"', package)
        self.assertIn('"dayjs"', package)
        self.assertIn('"playwright"', package)
        self.assertIn('"verify:routes"', package)
        self.assertIn("base: '/niu-secretary/'", vite)
        self.assertIn("echarts: ['echarts/core', 'echarts/charts', 'echarts/components', 'echarts/renderers']", vite)
        self.assertIn('AutoImport({', vite)
        self.assertIn('Components({', vite)
        self.assertIn("ElementPlusResolver({ importStyle: 'css' })", vite)
        self.assertNotIn('app.use(ElementPlus', main)
        self.assertIn("createWebHistory('/niu-secretary/')", router)
        self.assertIn("path: '/admin/login'", router)
        for route in (
            "path: 'fitness/nutrition'",
            "path: 'schedule/events'",
            "path: 'leisure/items'",
            "path: 'airesearch/papers'",
        ):
            self.assertIn(route, router)
        for component in ('<el-table', '<el-dialog', '<el-form', '<el-popconfirm'):
            self.assertIn(component, admin_page)
        self.assertIn('<el-menu', admin_layout)
        self.assertNotIn('admin-route-context', admin_layout)
        self.assertIn('admin-topbar-context', admin_layout)
        self.assertNotIn('ElNotification', admin_feedback)
        self.assertIn('shallowRef', admin_feedback)
        self.assertIn('adminFeedback', admin_feedback)
        self.assertIn('adminConfirm', admin_feedback)
        self.assertIn('<AdminFeedbackBar />', admin_layout)
        self.assertIn('class="admin-feedback-bar"', admin_feedback_bar)
        self.assertIn('aria-live="polite"', admin_feedback_bar)
        self.assertIn('.admin-feedback-bar', admin_styles)
        self.assertIn('position: sticky', admin_styles)
        self.assertNotIn('.admin-feedback-notification', admin_styles)
        self.assertIn('.admin-confirm-box', admin_styles)
        self.assertIn('.airesearch-admin-split', admin_styles)
        self.assertIn('fitness.assessments', ADMIN_READ_ROUTES)
        self.assertIn('leisure.recommendations', ADMIN_READ_ROUTES)

    def test_vue_playwright_verifier_exists_for_deep_routes(self):
        from pathlib import Path

        script = Path("scripts/verify_vue_routes_with_playwright.mjs").read_text(encoding="utf-8")
        self.assertIn("chromium", script)
        self.assertIn("const base = `http://127.0.0.1:${port}/niu-secretary/`", script)
        self.assertIn("new URL(route.replace(/^\\//, ''), base).toString()", script)
        self.assertIn("/admin/login", script)
        self.assertIn("/admin/fitness/nutrition", script)
        self.assertIn("/admin/news/recommendations", script)
        self.assertIn("/admin/airesearch/queue", script)
        self.assertIn("vite/bin/vite.js", script)
        self.assertIn("preview", script)
        self.assertIn("../web/", script)

    def test_vue_delivery_uses_history_fallback_without_deleting_legacy_static(self):
        from pathlib import Path

        config = Path("deploy/niu-secretary-vue.nginx.conf").read_text(encoding="utf-8")
        deploy = Path("deploy/deploy-vue-web.sh").read_text(encoding="utf-8")
        rollback = Path("deploy/rollback-vue-web.sh").read_text(encoding="utf-8")
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("location = /niu-secretary", config)
        self.assertIn("Retire legacy module-specific directory locations", config)
        self.assertNotIn("location /niu-secretary/airesearch/admin/", config)
        self.assertIn("location ^~ /niu-secretary/assets/", config)
        self.assertIn("try_files $uri /niu-secretary/index.html;", config)
        self.assertIn("Deliberately do not include $uri/", config)
        self.assertIn("direct legacy file URLs", config)
        self.assertIn('rsync -av "$WEB_DIST"/ "$DEPLOY_ROOT"/', deploy)
        self.assertNotIn("--delete", deploy)
        self.assertIn(".niu-secretary-vue-snapshots", deploy)
        self.assertIn("vue-deploy-manifest.json", deploy)
        self.assertIn("rollback-vue-web.sh latest", readme)
        self.assertIn("API 代理", readme)
        self.assertIn("旧 location 会优先命中", readme)
        self.assertIn("/niu-secretary/fitness/index.html", readme)
        self.assertIn("vue_web_rolled_back", rollback)

    def test_vue_admin_smoke_verifier_logs_in_and_loads_resources(self):
        from pathlib import Path

        package = Path("web/package.json").read_text(encoding="utf-8")
        vite = Path("web/vite.config.ts").read_text(encoding="utf-8")
        script = Path("scripts/verify_vue_admin_smoke_with_playwright.mjs").read_text(encoding="utf-8")

        self.assertIn('"verify:admin-smoke"', package)
        self.assertIn("process.env.NIU_SECRETARY_API_PORT", vite)
        self.assertIn("server.niu_secretary_api", script)
        self.assertIn("NIU_SECRETARY_ADMIN_PASSWORD", script)
        self.assertIn("/admin/session", script)
        self.assertIn("/admin/actions/execute", script)
        self.assertIn("fitness.nutrition.create", script)
        self.assertIn("schedule.event.create", script)
        self.assertIn("leisure.item.save", script)
        self.assertIn("airesearch.queue.add", script)
        self.assertIn("搜索配置", script)
        self.assertIn("任务中心", script)
        self.assertIn("重建部署", script)
        self.assertIn("/admin/fitness/nutrition", script)
        self.assertIn("/admin/schedule/events", script)
        self.assertIn("/admin/leisure/items", script)
        self.assertIn("/admin/airesearch/queue", script)
        self.assertIn("assertInlineAdminFeedback", script)
        self.assertIn(".admin-main .admin-feedback-bar", script)
        self.assertIn("body > .el-notification", script)

    def test_vue_fitness_smoke_verifier_loads_and_writes_public_page(self):
        from pathlib import Path

        package = Path("web/package.json").read_text(encoding="utf-8")
        script = Path("scripts/verify_vue_fitness_smoke_with_playwright.mjs").read_text(encoding="utf-8")

        self.assertIn('"verify:fitness-smoke"', package)
        self.assertIn("server.niu_secretary_api", script)
        self.assertIn("NIU_SECRETARY_FITNESS_SMOKE_API_PORT", script)
        self.assertIn("/actions/execute", script)
        self.assertIn("fitness.nutrition.create", script)
        self.assertIn("fitness.workout.create", script)
        self.assertIn("fitness.body_metric.create", script)
        self.assertIn("fitness.recovery.create", script)
        self.assertIn("`${webBase}fitness/`", script)
        self.assertIn("Smoke 牛奶", script)
        self.assertIn("Smoke 力量训练", script)
        self.assertIn("趋势总览", script)
        self.assertIn("拍照记一餐", script)
        self.assertIn("保存饮食", script)
        self.assertIn("Smoke 鸡蛋", script)

    def test_vue_schedule_smoke_verifier_loads_and_writes_public_page(self):
        from pathlib import Path

        package = Path("web/package.json").read_text(encoding="utf-8")
        script = Path("scripts/verify_vue_schedule_smoke_with_playwright.mjs").read_text(encoding="utf-8")

        self.assertIn('"verify:schedule-smoke"', package)
        self.assertIn("server.niu_secretary_api", script)
        self.assertIn("NIU_SECRETARY_SCHEDULE_SMOKE_API_PORT", script)
        self.assertIn("/actions/execute", script)
        self.assertIn("schedule.event.create", script)
        self.assertIn("schedule.todo.create", script)
        self.assertIn("`${webBase}schedule/`", script)
        self.assertIn("Smoke 站会", script)
        self.assertIn("Smoke 周报", script)
        self.assertIn("保存日程", script)
        self.assertIn("生成日计划", script)

    def test_vue_leisure_smoke_verifier_loads_and_writes_public_page(self):
        from pathlib import Path

        package = Path("web/package.json").read_text(encoding="utf-8")
        script = Path("scripts/verify_vue_leisure_smoke_with_playwright.mjs").read_text(encoding="utf-8")

        self.assertIn('"verify:leisure-smoke"', package)
        self.assertIn("server.niu_secretary_api", script)
        self.assertIn("NIU_SECRETARY_LEISURE_SMOKE_API_PORT", script)
        self.assertIn("`${webBase}leisure/`", script)
        self.assertIn("牛秘书闲趣集", script)
        self.assertIn("今晚首推", script)
        self.assertIn("今日候选", script)
        self.assertIn("口味档案", script)
        self.assertIn(".leisure-detail-sheet", script)
        self.assertIn("评分已提交", script)
        self.assertIn("已忽略", script)
        self.assertIn("assertNoMissingChineseStaticLinks", script)
        self.assertIn("收藏", script)
        self.assertIn("已收藏", script)
        self.assertIn("已存条目", script)
        self.assertIn("vue-leisure", script)

    def test_vue_news_smoke_verifier_loads_and_opens_detail(self):
        from pathlib import Path

        package = Path("web/package.json").read_text(encoding="utf-8")
        script = Path("scripts/verify_vue_news_smoke_with_playwright.mjs").read_text(encoding="utf-8")

        self.assertIn('"verify:news-smoke"', package)
        self.assertIn("server.niu_secretary_api", script)
        self.assertIn("NIU_SECRETARY_NEWS_SMOKE_API_PORT", script)
        self.assertIn("`${webBase}news/`", script)
        self.assertIn("牛秘书新闻社", script)
        self.assertIn("原文链接", script)
        self.assertIn(".news-search-card", script)
        self.assertIn(".news-detail-panel", script)
        self.assertNotIn("送研知库", script)

    def test_vue_airesearch_smoke_verifier_loads_and_adds_queue_item(self):
        from pathlib import Path

        package = Path("web/package.json").read_text(encoding="utf-8")
        script = Path("scripts/verify_vue_airesearch_smoke_with_playwright.mjs").read_text(encoding="utf-8")

        self.assertIn('"verify:airesearch-smoke"', package)
        self.assertIn("server.niu_secretary_api", script)
        self.assertIn("NIU_SECRETARY_AIRESEARCH_SMOKE_API_PORT", script)
        self.assertIn("`${webBase}airesearch/`", script)
        self.assertIn("牛秘书研知库", script)
        self.assertIn("AIResearch 研知库", script)
        self.assertIn("论文搜索", script)
        self.assertIn("最新论文", script)
        self.assertIn("加入队列", script)
        self.assertIn("Smoke 研究主题", script)
        self.assertIn("assertNoHorizontalOverflow", script)

    def test_vue_home_assistant_has_multi_action_review_states(self):
        from pathlib import Path

        home = Path("web/src/modules/home/HomePage.vue").read_text(encoding="utf-8")
        actions_api = Path("web/src/app/api/actions.ts").read_text(encoding="utf-8")
        package = Path("web/package.json").read_text(encoding="utf-8")
        smoke = Path("scripts/verify_vue_home_smoke_with_playwright.mjs").read_text(encoding="utf-8")

        self.assertIn("type ReviewStatus = 'pending' | 'running' | 'success' | 'error'", home)
        self.assertIn("interface ReviewAction extends ProposedAction", home)
        self.assertIn("const reviewItems = ref<ReviewAction[]>([])", home)
        self.assertIn("dedupeProposedActions(response.proposedActions || [])", home)
        self.assertIn("stableStringify(action.input || {})", home)
        self.assertIn("const runnableCount = computed", home)
        self.assertIn("assistantError", home)
        self.assertIn("assistant-message assistant error", home)
        self.assertIn("actionStatusLabel(item.status)", home)
        self.assertIn("actionStatusType(item.status)", home)
        self.assertIn("executeAction(item.action, item.input, 'vue-home'", home)
        self.assertIn("source: 'vue-home-review'", home)
        self.assertIn("requiresConfirmation: item.requiresConfirmation !== false", home)
        self.assertIn("reviewItemId: item.id", home)
        self.assertIn("await executeOne(item, true)", home)
        self.assertIn("removeReviewItem(item.id)", home)
        self.assertIn("平台运行", home)
        self.assertIn("/platform/today?date=", home)
        self.assertIn("/platform/ops?limit=8", home)

        self.assertIn("export interface ActionExecutionContext", actions_api)
        self.assertIn("requiresConfirmation?: boolean", actions_api)
        self.assertIn("extraContext: ActionExecutionContext = {}", actions_api)
        self.assertIn("context: { ...extraContext, client, confirmed: true }", actions_api)
        self.assertIn('"verify:home-smoke"', package)
        self.assertIn("NIU_SECRETARY_HOME_SMOKE_API_PORT", smoke)
        self.assertIn("await page.goto(webBase", smoke)
        self.assertIn("我今天中午吃了牛肉面和瑞幸的橙C美式", smoke)
        self.assertIn("写入：塑形馆/营养日志", smoke)
        self.assertIn("nutritionCards !== 1", smoke)
        self.assertIn("已记录到塑形馆营养", smoke)

    def test_vue_fitness_page_migrates_business_flows_to_unified_api(self):
        from pathlib import Path

        router = Path("web/src/app/router/index.ts").read_text(encoding="utf-8")
        page = Path("web/src/modules/fitness/FitnessPage.vue").read_text(encoding="utf-8")
        api = Path("web/src/modules/fitness/api.ts").read_text(encoding="utf-8")
        chart_runtime = Path("web/src/modules/fitness/chartRuntime.ts").read_text(encoding="utf-8")
        styles = Path("web/src/shared/styles/global.css").read_text(encoding="utf-8")

        self.assertIn("const FitnessPage = () => import('@/modules/fitness/FitnessPage.vue')", router)
        self.assertIn("{ path: '/fitness/', name: 'fitness', component: FitnessPage }", router)
        self.assertIn('class="module-nav"', page)
        self.assertIn('class="nav-chip"', page)
        self.assertIn('class="fit-form"', page)
        self.assertIn("<el-date-picker", page)
        self.assertIn("<el-input-number", page)
        self.assertIn("<el-slider", page)
        self.assertIn("<el-upload", page)
        self.assertIn("from 'echarts/core'", page)
        self.assertIn("import('./chartRuntime')", page)
        self.assertIn("chartRuntimePromise = null", page)
        self.assertIn("use([LineChart, BarChart, GridComponent, TooltipComponent, CanvasRenderer])", chart_runtime)
        self.assertNotIn("import('echarts/charts')", page)
        self.assertIn("weightChartEl", page)
        self.assertIn("recoveryChartEl", page)
        self.assertIn("useStorage('niu-vue-fitness-section'", page)
        self.assertIn("fetchFitnessSnapshot", page)
        self.assertIn("createNutritionLog", page)
        self.assertIn("createWorkoutLog", page)
        self.assertIn("createBodyMetric", page)
        self.assertIn("createRecoveryLog", page)
        self.assertIn("createAssessmentLog", page)
        self.assertIn("createConsultLog", page)
        self.assertIn("recognizePhoto", page)
        self.assertIn("estimateMealLocally", page)
        self.assertIn("saveRecognizedNutrition", page)
        self.assertIn("/niu-secretary/fitness/api/agent/nutrition-recognize", page)
        self.assertIn("牛秘书塑形馆", page)
        self.assertIn("dashboard-pair-nutrition", page)
        self.assertIn("dashboard-pair-trends", page)
        self.assertIn("paired-card", page)
        self.assertIn('class="assessment-section-nav"', page)
        self.assertIn(":data-assessment-section-target=\"section.key\"", page)
        self.assertIn("{ key: 'fms', index: '03'", page)
        self.assertIn("{ key: 'posture', index: '04'", page)
        self.assertIn('data-assessment-section="posture"', page)
        self.assertIn("fmsScores", page)
        self.assertIn("postureFlags", page)
        self.assertIn("assessmentPreview", page)
        self.assertIn("goNextAssessmentSection", page)

        for endpoint in (
            "/fitness/summary/today",
            "/fitness/summary/weekly",
            "/fitness/nutrition",
            "/fitness/workouts",
            "/fitness/body-metrics",
            "/fitness/recovery",
            "/fitness/assessments",
            "/fitness/consults",
            "/profile?module=fitness",
        ):
            self.assertIn(endpoint, api)
        for action in (
            "fitness.nutrition.create",
            "fitness.workout.create",
            "fitness.body_metric.create",
            "fitness.recovery.create",
            "fitness.assessment.create",
            "fitness.consult.create",
        ):
            self.assertIn(action, api)
        self.assertIn("'vue-fitness'", api)
        self.assertIn("source: 'vue-fitness-page'", api)
        self.assertIn(".fitness-workbench", styles)
        self.assertIn(".fitness-chart", styles)
        self.assertIn(".recognized-meal-card", styles)
        self.assertIn(".fitness-dashboard-pair", styles)
        self.assertIn(".fitness-assessment-layout", styles)
        self.assertIn(".assessment-section-nav", styles)
        self.assertIn(".assessment-score-grid", styles)
        self.assertIn("overflow-wrap: anywhere", styles)
        smoke = Path("scripts/verify_vue_fitness_smoke_with_playwright.mjs").read_text(encoding="utf-8")
        self.assertIn("assertPairedPanelsAligned", smoke)
        self.assertIn("assertNoHorizontalOverflow", smoke)
        self.assertIn("[data-assessment-section-target=\"fms\"]", smoke)

    def test_vue_schedule_page_migrates_business_flows_to_unified_api(self):
        from pathlib import Path

        router = Path("web/src/app/router/index.ts").read_text(encoding="utf-8")
        page = Path("web/src/modules/schedule/SchedulePage.vue").read_text(encoding="utf-8")
        api = Path("web/src/modules/schedule/api.ts").read_text(encoding="utf-8")
        styles = Path("web/src/shared/styles/global.css").read_text(encoding="utf-8")

        self.assertIn("const SchedulePage = () => import('@/modules/schedule/SchedulePage.vue')", router)
        self.assertIn("{ path: '/schedule/', name: 'schedule', component: SchedulePage }", router)
        self.assertIn("schedule-topbar", page)
        self.assertIn("schedule-date-card", page)
        self.assertIn("我的画像 · 今日建议", page)
        self.assertIn("事务抽屉", page)
        self.assertIn("数据同步状态", page)
        self.assertIn("<el-tabs", page)
        self.assertIn("<el-timeline", page)
        self.assertIn("<el-table", page)
        self.assertIn("<el-form", page)
        self.assertIn("<el-date-picker", page)
        self.assertIn("useStorage('niu-vue-schedule-active-tab'", page)
        self.assertIn("fetchScheduleSnapshot", page)
        self.assertIn("createScheduleEvent", page)
        self.assertIn("createScheduleTodo", page)
        self.assertIn("toggleScheduleTodo", page)
        self.assertIn("generateDayPlan", page)
        self.assertIn("saveDayReview", page)

        for endpoint in (
            "/schedule/summary/today",
            "/schedule/events",
            "/schedule/todos",
            "/schedule/important-dates",
            "/schedule/goals",
            "/schedule/day-plan",
            "/schedule/day-review",
            "/schedule/conflicts",
            "/schedule/recommend",
        ):
            self.assertIn(endpoint, api)
        for action in (
            "schedule.event.create",
            "schedule.todo.create",
            "schedule.event.update",
            "schedule.todo.update",
            "schedule.todo.toggle",
            "schedule.event.delete",
            "schedule.todo.delete",
            "schedule.day.plan",
            "schedule.day.review",
        ):
            self.assertIn(action, api)
        self.assertIn("'vue-schedule'", api)
        self.assertIn("source: 'vue-schedule-page'", api)
        self.assertIn(".schedule-workbench", styles)
        self.assertIn(".schedule-date-card", styles)
        self.assertIn(".drawer-grid", styles)
        self.assertIn(".schedule-cache-note", styles)

    def test_vue_leisure_page_migrates_business_flows_to_unified_api(self):
        from pathlib import Path

        router = Path("web/src/app/router/index.ts").read_text(encoding="utf-8")
        page = Path("web/src/modules/leisure/LeisurePage.vue").read_text(encoding="utf-8")
        api = Path("web/src/modules/leisure/api.ts").read_text(encoding="utf-8")
        styles = Path("web/src/shared/styles/global.css").read_text(encoding="utf-8")

        self.assertIn("const LeisurePage = () => import('@/modules/leisure/LeisurePage.vue')", router)
        self.assertIn("{ path: '/leisure/', name: 'leisure', component: LeisurePage }", router)
        self.assertIn("<el-tabs", page)
        self.assertIn("<el-segmented", page)
        self.assertIn("leisure-detail-sheet", page)
        self.assertIn("recommend-workbench", page)
        self.assertIn("categoryNav", page)
        self.assertIn("<el-table", page)
        self.assertIn("<el-rate", page)
        self.assertIn("useStorage('niu-vue-leisure-active-tab'", page)
        self.assertIn("fetchLeisureSnapshot", page)
        self.assertIn("saveLeisureItem", page)
        self.assertIn("dismissLeisureItem", page)
        self.assertIn("rateLeisureItem", page)
        self.assertNotIn("影视.html", page)

        for endpoint in (
            "/leisure/recommend",
            "/leisure/items",
            "/leisure/history",
            "/profile?module=leisure",
        ):
            self.assertIn(endpoint, api)
        for action in (
            "leisure.item.save",
            "leisure.item.dismiss",
            "leisure.item.rate",
        ):
            self.assertIn(action, api)
        self.assertIn("'vue-leisure'", api)
        self.assertIn("source: 'vue-leisure-page'", api)
        self.assertIn(".leisure-workbench", styles)
        self.assertIn(".leisure-detail-sheet", styles)
        self.assertIn(".recommend-workbench", styles)
        self.assertIn(".leisure-nav", styles)

    def test_vue_news_page_migrates_business_flows_to_unified_api(self):
        from pathlib import Path

        router = Path("web/src/app/router/index.ts").read_text(encoding="utf-8")
        page = Path("web/src/modules/news/NewsPage.vue").read_text(encoding="utf-8")
        api = Path("web/src/modules/news/api.ts").read_text(encoding="utf-8")
        styles = Path("web/src/shared/styles/global.css").read_text(encoding="utf-8")

        self.assertIn("const NewsPage = () => import('@/modules/news/NewsPage.vue')", router)
        self.assertIn("{ path: '/news/', name: 'news', component: NewsPage }", router)
        self.assertIn("<el-tabs", page)
        self.assertIn("news-search-results", page)
        self.assertIn("news-search-card", page)
        self.assertNotIn("<el-dialog", page)
        self.assertIn("news-section-nav", page)
        self.assertIn("filteredRecommendations", page)
        self.assertIn("news-detail-overlay", page)
        self.assertIn("news-window-controls", page)
        self.assertNotIn("送研知库", page)
        self.assertNotIn("queueNewsTopic", page)
        self.assertIn("useStorage('niu-vue-news-active-tab'", page)
        self.assertIn("fetchNewsSnapshot", page)
        self.assertIn("searchNews", page)
        self.assertIn("detailHtml", api)

        for endpoint in (
            "/news/recommend",
            "/news/search",
        ):
            self.assertIn(endpoint, api)
        self.assertNotIn("news.topic.queue-research", api)
        self.assertIn("getPublicData", api)
        self.assertNotIn("'vue-news'", api)
        self.assertNotIn("source: 'vue-news-page'", api)
        self.assertIn("_load_news_items", Path("server/action_handlers.py").read_text(encoding="utf-8"))
        self.assertIn("detail_html", Path("server/action_handlers.py").read_text(encoding="utf-8"))
        self.assertIn(".news-workbench", styles)
        self.assertIn(".news-section-tab", styles)
        self.assertIn(".news-card.featured", styles)
        self.assertIn(".news-search-card", styles)
        self.assertIn(".news-detail-panel", styles)
        self.assertIn(".news-window-dot.fullscreen", styles)

    def test_vue_airesearch_public_page_is_retired_for_static_site(self):
        from pathlib import Path

        router = Path("web/src/app/router/index.ts").read_text(encoding="utf-8")
        home = Path("web/src/modules/home/HomePage.vue").read_text(encoding="utf-8")
        research_site = Path("airesearch/src/airesearch/research_site.py").read_text(encoding="utf-8")
        styles = Path("web/src/shared/styles/global.css").read_text(encoding="utf-8")

        self.assertNotIn("const AIResearchPage =", router)
        self.assertNotIn("component: AIResearchPage", router)
        self.assertNotIn("{ path: '/airesearch/'", router)
        self.assertFalse(Path("web/src/modules/airesearch/AIResearchPage.vue").exists())
        self.assertIn('<a href="/niu-secretary/airesearch/">研知库</a>', home)
        self.assertIn("external: true", home)
        self.assertIn("item.external ? { href: item.path } : { to: item.path }", home)
        self.assertIn("blogs/index.html", research_site)
        self.assertIn("paper-tab-deep-reading", research_site)
        self.assertIn("modeFromHash", research_site)
        self.assertIn("path: 'airesearch/blogs'", router)
        self.assertIn("AdminAIResearchPage", router)
        self.assertIn(".research-workbench", styles)

    def test_home_assistant_batches_multiple_actions_with_clear_titles(self):
        from pathlib import Path

        script = Path("dist/assistant.js").read_text(encoding="utf-8")

        self.assertIn("确认全部执行", script)
        self.assertIn("confirmAllActions(actionEditors, bulkButton)", script)
        self.assertIn("executeActionFromEditor(proposal, editor)", script)
        self.assertIn('context: { client: "home-assistant", confirmed: true }', script)
        self.assertIn('action === "fitness.nutrition.create"', script)
        self.assertIn("input.food", script)
        self.assertIn("showExecutionProgress(stepLabel, syncLabel)", script)
        self.assertIn("finishExecutionProgress(stepLabel, syncLabel)", script)

    def test_fitness_and_airesearch_have_return_home_links(self):
        from pathlib import Path

        fitness_html = Path("fitness/dist/index.html").read_text(encoding="utf-8")
        fitness_css = Path("fitness/dist/style.css").read_text(encoding="utf-8")
        research_site = Path("airesearch/src/airesearch/research_site.py").read_text(encoding="utf-8")
        research_admin = Path("airesearch/src/airesearch/admin_server.py").read_text(encoding="utf-8")

        self.assertIn('class="home-link" href="/niu-secretary/"', fitness_html)
        self.assertIn("返回主页", fitness_html)
        self.assertIn(".topbar-actions", fitness_css)
        self.assertIn(".home-link", fitness_css)
        self.assertIn('<a class="home-link" href="/niu-secretary/">返回主页</a>', research_site)
        self.assertIn(".topbar-actions", research_site)
        self.assertIn('<a class="home-link" href="/niu-secretary/">返回主页</a>', research_admin)

    def test_fitness_dashboard_uses_paired_equal_height_rows(self):
        from pathlib import Path

        dashboard = Path("fitness/dist/sections/dashboard.html").read_text(encoding="utf-8")
        css = Path("fitness/dist/style.css").read_text(encoding="utf-8")

        self.assertIn("dashboard-pair dashboard-pair-trends full-row", dashboard)
        self.assertIn("dashboard-pair dashboard-pair-nutrition full-row", dashboard)
        self.assertGreaterEqual(dashboard.count("paired-card"), 4)
        self.assertLess(dashboard.index("趋势总览"), dashboard.index("录入体重"))
        self.assertLess(dashboard.index("今日营养"), dashboard.index("目标设置"))
        self.assertIn(".dashboard-pair", css)
        self.assertIn("grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.82fr)", css)
        self.assertIn(".paired-card", css)
        self.assertIn("height: 100%", css)

    def test_fitness_assessment_uses_section_navigation(self):
        from pathlib import Path

        assessment = Path("fitness/dist/sections/assessment.html").read_text(encoding="utf-8")
        script = Path("fitness/dist/js/features/assessment.js").read_text(encoding="utf-8")
        css = Path("fitness/dist/style.css").read_text(encoding="utf-8")

        self.assertIn('class="assessment-workflow"', assessment)
        self.assertIn('class="assessment-section-nav assessment-step-nav"', assessment)
        self.assertIn('class="assessment-section-panel"', assessment)
        for section in ("baseline", "girths", "fms", "posture"):
            self.assertIn(f'data-assessment-section="{section}"', assessment)
            self.assertIn(f'data-assessment-section-target="{section}"', assessment)
        self.assertIn('data-assessment-section="baseline"', assessment)
        self.assertIn('data-assessment-section="fms" hidden', assessment)
        self.assertIn('data-assessment-section="posture" hidden', assessment)
        self.assertIn('form.addEventListener(\'submit\', saveAssessment)', script)
        self.assertIn("setupAssessmentSections(form)", script)
        self.assertIn("section.hidden = !active", script)
        self.assertIn(".assessment-workflow", css)
        self.assertIn(".assessment-section-panel", css)
        self.assertIn(".assessment-section-nav", css)
        self.assertIn("grid-template-columns: 54px minmax(0, 1fr) minmax(86px, max-content)", css)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn(".assessment-section", css)

    def test_web_get_readonly_context_does_not_write_module_events(self):
        def event_count(module: str, event_type: str) -> int:
            return len(store.list_module_events(module, event_type, 20))

        baseline_today = event_count("platform", "today_context")
        baseline_overview = event_count("airesearch", "overview_read")
        baseline_search = event_count("airesearch", "paper_search")

        today = execute_action(
            "platform.today.context",
            {"date": "2026-06-14", "limit": 1},
            {"client": "web", "readOnly": True},
        )
        overview = execute_action(
            "airesearch.overview",
            {"limit": 1},
            {"client": "web", "readOnly": True},
        )
        search = execute_action(
            "airesearch.paper.search",
            {"q": "attention", "limit": 1},
            {"client": "web", "readOnly": True},
        )

        self.assertTrue(today["ok"])
        self.assertTrue(overview["ok"])
        self.assertTrue(search["ok"])
        self.assertEqual(event_count("platform", "today_context"), baseline_today)
        self.assertEqual(event_count("airesearch", "overview_read"), baseline_overview)
        self.assertEqual(event_count("airesearch", "paper_search"), baseline_search)

        execute_action("airesearch.overview", {"limit": 1}, {"client": "unit-test"})
        execute_action("airesearch.paper.search", {"q": "attention", "limit": 1}, {"client": "unit-test"})

        self.assertEqual(event_count("airesearch", "overview_read"), baseline_overview + 1)
        self.assertEqual(event_count("airesearch", "paper_search"), baseline_search + 1)

    def test_unified_cron_entrypoint_records_cron_run(self):
        env = os.environ.copy()
        command = [sys.executable, "-m", "niu_secretary.cron", "fitness.summarize-day"]
        completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

        runs = store.list_module_runs("fitness", 20)
        self.assertTrue(any(run["runType"] == "fitness.summarize-day" and run["source"] == "cron" for run in runs))

    def test_cron_list_outputs_job_registry_without_running_jobs(self):
        import json

        env = os.environ.copy()
        completed = subprocess.run(
            [sys.executable, "-m", "niu_secretary.cron", "list"],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertIn("fitness.summarize-day", payload["jobs"])
        self.assertIn("platform.run-daily", payload["groups"]["daily"])
        self.assertEqual(store.list_module_runs(limit=1), [])

    def test_platform_cron_run_daily_exports_snapshot(self):
        env = os.environ.copy()
        command = [sys.executable, "-m", "niu_secretary.cron", "platform.run-daily"]
        completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

        runs = store.list_module_runs("platform", 20)
        self.assertTrue(any(run["runType"] == "platform.run-daily" and run["source"] == "cron" for run in runs))
        self.assertTrue(os.path.exists(os.path.join("exports", "niu-secretary", "platform.json")))


if __name__ == "__main__":
    unittest.main()
