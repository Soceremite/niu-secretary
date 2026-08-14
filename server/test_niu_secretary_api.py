"""v4 测试 — 适配新字段 module + 本地 fallback 大餐估算"""
import os
import tempfile
import unittest
from unittest import mock

from server.actions import ActionError, execute_action
from server.assistant import handle_message
from server.capabilities import capabilities_response


class NiuSecretaryApiV4Test(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["NIU_SECRETARY_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")
        self.model_patcher = mock.patch("server.assistant._try_models", return_value=None)
        self.model_patcher.start()

    def tearDown(self):
        self.model_patcher.stop()
        os.environ.pop("NIU_SECRETARY_DB_PATH", None)
        self.tempdir.cleanup()

    def test_capabilities_include_nutrition_create(self):
        names = {item["name"] for item in capabilities_response()["capabilities"]}
        self.assertIn("fitness.nutrition.create", names)
        self.assertIn("schedule.event.create", names)

    def test_missing_food_returns_validation_error(self):
        with self.assertRaises(ActionError) as raised:
            execute_action("fitness.nutrition.create", {"date": "2026-05-29"})
        self.assertEqual(raised.exception.error, "validation_failed")
        self.assertEqual(raised.exception.details["field"], "food")

    def test_create_nutrition_and_read_summary(self):
        result = execute_action(
            "fitness.nutrition.create",
            {
                "food": "牛肉面",
                "date": "2026-05-29",
                "calories": 650,
                "proteinG": 28,
                "carbsG": 82,
                "fatG": 20,
                "source": "test",
            },
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["record"]["food"], "牛肉面")

        summary = execute_action("fitness.nutrition.today_summary", {"date": "2026-05-29"})
        self.assertEqual(summary["summary"]["count"], 1)
        self.assertEqual(summary["summary"]["calories"], 650)

    def test_assistant_meal_message_proposes_nutrition_action(self):
        """v4: 返回 module 而非 intent"""
        response = handle_message("我今天吃了牛肉面", {"client": "test"})
        self.assertEqual(response["module"], "fitness")
        self.assertIn("proposedActions", response)
        self.assertGreater(len(response["proposedActions"]), 0)
        self.assertEqual(response["proposedActions"][0]["action"], "fitness.nutrition.create")
        self.assertEqual(response["proposedActions"][0]["input"]["food"], "牛肉面")

    def test_assistant_large_meat_meal_uses_high_calorie_estimate(self):
        """v4: 本地 fallback 对「七八个菜大部分肉类」估算高温量"""
        response = handle_message("我今天晚上吃了东北菜，有七八个菜，大部分是肉类", {"client": "test"})
        action_input = response["proposedActions"][0]["input"]
        self.assertEqual(response["module"], "fitness")
        self.assertGreaterEqual(action_input["calories"], 1000)
        self.assertGreaterEqual(action_input["proteinG"], 70)

    def test_assistant_reminder_message_proposes_event_action(self):
        """v4: module=schedule, action=schedule.event.create"""
        response = handle_message("明天下午三点提醒我开会", {"client": "test"})
        self.assertEqual(response["module"], "schedule")
        action = response["proposedActions"][0]
        self.assertEqual(action["action"], "schedule.event.create")
        self.assertEqual(action["input"]["title"], "开会")
        self.assertEqual(action["input"]["time"], "15:00")

    def test_news_module_returns_fallback_no_actions(self):
        """news/leisure/chat 走本地规则，无 proposedActions"""
        response = handle_message("今天有什么新闻", {"client": "test"})
        self.assertEqual(response["module"], "news")
        self.assertEqual(response["source"], "fallback")
        self.assertEqual(response["proposedActions"], [])

    def test_chat_module_returns_fallback(self):
        response = handle_message("你好啊", {"client": "test"})
        self.assertEqual(response["module"], "chat")
        self.assertEqual(response["source"], "fallback")
        self.assertEqual(response["proposedActions"], [])

    def test_nutrition_list_returns_inserted_rows(self):
        execute_action("fitness.nutrition.create", {"food": "鸡胸肉", "date": "2026-05-29", "calories": 200})
        execute_action("fitness.nutrition.create", {"food": "米饭", "date": "2026-05-30", "calories": 200})
        result = execute_action("fitness.nutrition.list", {})
        self.assertEqual(result["count"], 2)
        ranged = execute_action("fitness.nutrition.list", {"from": "2026-05-30", "to": "2026-05-30"})
        self.assertEqual(ranged["count"], 1)
        self.assertEqual(ranged["items"][0]["food"], "米饭")

    def test_nutrition_delete_removes_row(self):
        created = execute_action("fitness.nutrition.create", {"food": "面包", "date": "2026-05-29"})
        rid = created["record"]["id"]
        execute_action("fitness.nutrition.delete", {"id": rid})
        self.assertEqual(execute_action("fitness.nutrition.list", {})["count"], 0)
        with self.assertRaises(ActionError) as raised:
            execute_action("fitness.nutrition.delete", {"id": rid})
        self.assertEqual(raised.exception.status, 404)

    def test_event_list_and_delete(self):
        created = execute_action("schedule.event.create", {"title": "开会", "date": "2026-06-01", "time": "15:00"})
        rid = created["record"]["id"]
        listed = execute_action("schedule.event.list", {"from": "2026-06-01", "to": "2026-06-01"})
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["items"][0]["title"], "开会")
        execute_action("schedule.event.delete", {"id": rid})
        self.assertEqual(execute_action("schedule.event.list", {})["count"], 0)

    def test_todo_list_toggle_and_filter_done(self):
        created = execute_action("schedule.todo.create", {"title": "买菜", "priority": "high"})
        rid = created["record"]["id"]
        toggled = execute_action("schedule.todo.toggle", {"id": rid, "done": True})
        self.assertTrue(toggled["record"]["done"])
        all_todos = execute_action("schedule.todo.list", {})
        self.assertEqual(all_todos["count"], 1)
        pending = execute_action("schedule.todo.list", {"includeDone": False})
        self.assertEqual(pending["count"], 0)
        # toggle without explicit done flips back to undone
        flipped = execute_action("schedule.todo.toggle", {"id": rid})
        self.assertFalse(flipped["record"]["done"])

    def test_undated_todo_included_in_ranged_list(self):
        execute_action("schedule.todo.create", {"title": "无日期待办"})
        ranged = execute_action("schedule.todo.list", {"from": "2026-06-01", "to": "2026-06-02"})
        self.assertEqual(ranged["count"], 1)

    def test_new_capabilities_registered(self):
        names = {item["name"] for item in capabilities_response()["capabilities"]}
        for name in (
            "fitness.nutrition.list",
            "fitness.nutrition.delete",
            "schedule.event.list",
            "schedule.event.delete",
            "schedule.todo.list",
            "schedule.todo.toggle",
            "schedule.todo.delete",
            "schedule.important_date.create",
            "schedule.important_date.list",
            "schedule.goal.create",
            "schedule.goal.list",
        ):
            self.assertIn(name, names)

    def test_schedule_important_dates_and_goals_persist(self):
        birthday = execute_action(
            "schedule.important_date.create",
            {"title": "生日", "date": "XXXX-06-20", "note": "提前准备", "source": "test"},
        )
        self.assertTrue(birthday["ok"])
        self.assertEqual(birthday["record"]["date"], "XXXX-06-20")

        goal = execute_action(
            "schedule.goal.create",
            {"title": "每周复盘", "cadence": "weekly", "streak": 3, "source": "test"},
        )
        self.assertTrue(goal["ok"])
        self.assertEqual(goal["record"]["streak"], 3)

        dates = execute_action("schedule.important_date.list", {"limit": 10})
        goals = execute_action("schedule.goal.list", {"limit": 10})
        self.assertEqual(dates["count"], 1)
        self.assertEqual(goals["count"], 1)
        self.assertEqual(dates["items"][0]["title"], "生日")
        self.assertEqual(goals["items"][0]["title"], "每周复盘")

    def test_schedule_important_date_rejects_invalid_recurring_date(self):
        with self.assertRaises(ActionError) as raised:
            execute_action("schedule.important_date.create", {"title": "坏日期", "date": "XXXX-02-31"})
        self.assertEqual(raised.exception.error, "validation_failed")

    # ---- 用户画像 ----
    def test_profile_capabilities_registered(self):
        names = {item["name"] for item in capabilities_response()["capabilities"]}
        for name in (
            "profile.get",
            "profile.update",
            "profile.reset",
            "profile.changes",
            "fitness.recommend",
            "schedule.recommend",
        ):
            self.assertIn(name, names)

    def test_profile_get_returns_default(self):
        result = execute_action("profile.get", {"module": "fitness"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["profile"]["goal"], "maintain")
        self.assertEqual(result["updatedAt"], "")

    def test_profile_get_all_when_module_omitted(self):
        result = execute_action("profile.get", {})
        self.assertTrue(result["ok"])
        self.assertEqual(set(result["profiles"].keys()), {"fitness", "schedule", "news", "leisure", "airesearch"})

    def test_profile_update_merges_and_records_change(self):
        result = execute_action("profile.update", {
            "module": "fitness",
            "patch": {"goal": "fat_loss", "targetCalories": 1700},
            "summary": "调为减脂",
            "source": "test",
        })
        self.assertTrue(result["ok"])
        self.assertEqual(result["profile"]["goal"], "fat_loss")
        self.assertEqual(result["profile"]["targetCalories"], 1700)
        self.assertEqual(set(result["changedFields"]), {"goal", "targetCalories"})
        # 再读取应持久化
        again = execute_action("profile.get", {"module": "fitness"})
        self.assertEqual(again["profile"]["goal"], "fat_loss")
        # 变更历史
        changes = execute_action("profile.changes", {"module": "fitness"})
        self.assertEqual(changes["count"], 2)

    def test_profile_update_no_change_when_same_value(self):
        execute_action("profile.update", {"module": "news", "patch": {"depth": "deep"}})
        result = execute_action("profile.update", {"module": "news", "patch": {"depth": "deep"}})
        self.assertEqual(result["changedFields"], [])

    def test_profile_update_rejects_unknown_module(self):
        with self.assertRaises(ActionError) as raised:
            execute_action("profile.update", {"module": "bogus", "patch": {"x": 1}})
        self.assertEqual(raised.exception.error, "validation_failed")

    def test_profile_update_rejects_empty_patch(self):
        with self.assertRaises(ActionError) as raised:
            execute_action("profile.update", {"module": "fitness", "patch": {}})
        self.assertEqual(raised.exception.details.get("field"), "patch")

    def test_profile_reset_restores_default(self):
        execute_action("profile.update", {"module": "leisure", "patch": {"moods": ["解压"]}})
        execute_action("profile.reset", {"module": "leisure"})
        result = execute_action("profile.get", {"module": "leisure"})
        self.assertEqual(result["profile"]["moods"], [])

    def test_fitness_recommend_uses_profile(self):
        execute_action("profile.update", {"module": "fitness", "patch": {
            "goal": "fat_loss", "targetCalories": 1700, "proteinTarget": 140,
            "restrictions": ["乳糖不耐"],
        }})
        result = execute_action("fitness.recommend", {"date": "2026-05-30"})
        self.assertTrue(result["ok"])
        self.assertTrue(len(result["recommendations"]) >= 1)
        joined = " ".join(result["recommendations"])
        self.assertIn("乳糖不耐", joined)

    def test_schedule_recommend_uses_profile(self):
        execute_action("profile.update", {"module": "schedule", "patch": {
            "workHours": "09:00-18:00", "priorities": ["科研 rebuttal"],
        }})
        result = execute_action("schedule.recommend", {"date": "2026-05-30"})
        self.assertTrue(result["ok"])
        joined = " ".join(result["recommendations"])
        self.assertIn("09:00-18:00", joined)

    # ---- 阶段B：AI 聊天调整画像（本地降级逻辑，不依赖模型）----
    def test_local_intent_detects_preference(self):
        from server.assistant import local_intent
        self.assertEqual(local_intent("我想减脂"), "preference")
        self.assertEqual(local_intent("我爱看悬疑剧"), "preference")
        self.assertEqual(local_intent("今天吃什么好"), "query")
        self.assertEqual(local_intent("我今天吃了牛肉面"), "record")

    def test_local_extract_preference_fitness(self):
        from server.assistant import local_extract_preference
        patch = local_extract_preference("我想减脂，我乳糖不耐，口味偏川渝", "fitness")
        self.assertEqual(patch["goal"], "fat_loss")
        self.assertIn("乳糖不耐", patch["restrictions"])
        self.assertEqual(patch["dietStyle"], "川渝")

    def test_local_extract_preference_leisure(self):
        from server.assistant import local_extract_preference
        patch = local_extract_preference("我爱看悬疑和科幻电影", "leisure")
        self.assertIn("悬疑", patch["genres"]["movie"])
        self.assertIn("科幻", patch["genres"]["movie"])

    def test_preference_fallback_produces_profile_update(self):
        from server.assistant import preference_fallback
        result = preference_fallback("我想减脂", "fitness")
        self.assertEqual(len(result["proposedActions"]), 1)
        action = result["proposedActions"][0]
        self.assertEqual(action["action"], "profile.update")
        self.assertEqual(action["input"]["module"], "fitness")
        self.assertEqual(action["input"]["patch"]["goal"], "fat_loss")
        # 该动作可被实际执行
        exec_result = execute_action(action["action"], action["input"])
        self.assertEqual(exec_result["profile"]["goal"], "fat_loss")

    def test_preference_fallback_empty_when_no_signal(self):
        from server.assistant import preference_fallback
        result = preference_fallback("嗯嗯啊啊", "fitness")
        self.assertEqual(result["proposedActions"], [])

    def test_profile_update_in_allowed_actions(self):
        from server.assistant import ALLOWED_ACTIONS
        self.assertIn("profile.update", ALLOWED_ACTIONS)

    # ---- v1.1: 新闻社 / 闲趣集 recommend ----
    def test_v11_recommend_capabilities_registered(self):
        names = {item["name"] for item in capabilities_response()["capabilities"]}
        self.assertIn("news.recommend", names)
        self.assertIn("leisure.recommend", names)

    def test_news_recommend_returns_today_cards(self):
        """空画像时返回今日要闻（读真实 sections/*.html）。"""
        result = execute_action("news.recommend", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["module"], "news")
        self.assertFalse(result["personalized"])
        self.assertGreater(result["count"], 0)
        first = result["items"][0]
        self.assertIn("title", first)
        self.assertIn("section", first)
        self.assertTrue(first["title"])

    def test_news_recommend_respects_topics_and_exclude(self):
        """设定关注 AI/科技、排除财经，结果应偏重匹配且不含排除项。"""
        execute_action("profile.update", {"module": "news", "patch": {
            "topics": ["AI", "科技"], "excludeTopics": ["财经"],
        }})
        result = execute_action("news.recommend", {"limit": 10})
        self.assertTrue(result["ok"])
        self.assertTrue(result["personalized"])
        self.assertGreater(result["items"][0]["matchScore"], 0)
        for item in result["items"]:
            blob = (item["tag"] + item["title"] + item["summary"] + item["sectionLabel"]).lower()
            self.assertNotIn("财经", blob)

    def test_leisure_recommend_returns_groups(self):
        """空画像时返回各类目推荐（读真实 data/*.json）。"""
        result = execute_action("leisure.recommend", {})
        self.assertTrue(result["ok"])
        self.assertEqual(result["module"], "leisure")
        self.assertGreater(result["count"], 0)
        self.assertTrue(any(g["category"] == "movie" for g in result["groups"]))

    def test_leisure_recommend_respects_genres_and_avoid(self):
        """设定爱看科幻、避开恐怖，结果偏重科幻且不含恐怖。"""
        execute_action("profile.update", {"module": "leisure", "patch": {
            "genres": {"movie": ["科幻"], "music": [], "podcast": [], "novel": []},
            "avoid": ["恐怖"],
        }})
        result = execute_action("leisure.recommend", {})
        self.assertTrue(result["ok"])
        self.assertTrue(result["personalized"])
        movie_group = next((g for g in result["groups"] if g["category"] == "movie"), None)
        self.assertIsNotNone(movie_group)
        for item in movie_group["items"]:
            self.assertNotIn("恐怖", [g.lower() for g in item["genres"]])


if __name__ == "__main__":
    unittest.main()
