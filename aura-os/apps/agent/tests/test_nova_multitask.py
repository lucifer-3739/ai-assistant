import unittest
import sys
import os

# Add agent root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from voice.wake_word import extract_command_after_wake_word
from core.planner import fast_plan_matcher, split_compound_request

class TestNovaAndMultiTask(unittest.TestCase):
    def test_nova_wake_word_extraction(self):
        # Direct Nova wake words
        triggered, cmd = extract_command_after_wake_word("Nova open notepad")
        self.assertTrue(triggered)
        self.assertEqual(cmd, "open notepad")

        triggered, cmd = extract_command_after_wake_word("Hey Nova, can you check my battery?")
        self.assertTrue(triggered)
        self.assertEqual(cmd, "check my battery")

        triggered, cmd = extract_command_after_wake_word("OK Nova open chrome and check battery")
        self.assertTrue(triggered)
        self.assertEqual(cmd, "open chrome and check battery")

        triggered, cmd = extract_command_after_wake_word("Nova")
        self.assertTrue(triggered)
        self.assertEqual(cmd, "")

        # Non wake word
        triggered, cmd = extract_command_after_wake_word("Hello world how are you")
        self.assertFalse(triggered)

    def test_compound_splitting(self):
        splits1 = split_compound_request("open notepad and check battery")
        self.assertEqual(splits1, ["open notepad", "check battery"])

        splits2 = split_compound_request("open chrome, check battery, and take a screenshot")
        self.assertEqual(splits2, ["open chrome", "check battery", "take a screenshot"])

        splits3 = split_compound_request("snap left and open code, then play synthwave on youtube")
        self.assertEqual(splits3, ["snap left", "open code", "play synthwave on youtube"])

    def test_fast_plan_multi_task_execution(self):
        # 2-step compound
        plan = fast_plan_matcher("open notepad and check battery")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["step_number"], 1)
        self.assertEqual(plan[0]["tool_name"], "open_application")
        self.assertEqual(plan[0]["tool_args"]["application"], "notepad")
        self.assertEqual(plan[1]["step_number"], 2)
        self.assertEqual(plan[1]["tool_name"], "get_battery_status")

        # 3-step compound
        plan3 = fast_plan_matcher("open chrome, set volume up, and take a screenshot")
        self.assertIsNotNone(plan3)
        self.assertEqual(len(plan3), 3)
        self.assertEqual(plan3[0]["tool_name"], "open_application")
        self.assertEqual(plan3[1]["tool_name"], "set_system_volume")
        self.assertEqual(plan3[2]["tool_name"], "take_screenshot")

        # Device & Window multi-task
        plan_dev = fast_plan_matcher("dim screen and pause music")
        self.assertIsNotNone(plan_dev)
        self.assertEqual(len(plan_dev), 2)
        self.assertEqual(plan_dev[0]["tool_name"], "set_display_brightness")
        self.assertEqual(plan_dev[1]["tool_name"], "media_playback_control")

if __name__ == "__main__":
    unittest.main()
