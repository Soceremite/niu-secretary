import os
import tempfile
import unittest

from server.actions import ActionError, execute_action
from server.assistant import handle_message
from server.capabilities import capabilities_response


class NiuSecretaryApiTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["NIU_SECRETARY_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")

    def tearDown(self):
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
        response = handle_message("我今天吃了牛肉面", {"client": "test"})
        self.assertEqual(response["intent"], "record_meal")
        self.assertEqual(response["proposedActions"][0]["action"], "fitness.nutrition.create")
        self.assertEqual(response["proposedActions"][0]["input"]["food"], "牛肉面")

    def test_assistant_reminder_message_proposes_event_action(self):
        response = handle_message("明天下午三点提醒我开会", {"client": "test"})
        action = response["proposedActions"][0]
        self.assertEqual(response["intent"], "create_schedule_event")
        self.assertEqual(action["action"], "schedule.event.create")
        self.assertEqual(action["input"]["title"], "开会")
        self.assertEqual(action["input"]["time"], "15:00")


if __name__ == "__main__":
    unittest.main()
