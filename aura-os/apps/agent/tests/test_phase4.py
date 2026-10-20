import os
import sys
import shutil
import tempfile
import unittest
from dotenv import load_dotenv

# Ensure agent folder is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from database.schema import init_db
from tools.vision import take_screenshot, get_active_window_info, analyze_screen
from tools.gui import type_text, press_keyboard_shortcut

class TestPhase4System(unittest.TestCase):
    def setUp(self):
        init_db()
        self.test_dir = tempfile.mkdtemp(prefix="aura_test_vision_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_screen_capture_tool(self):
        print("\n--- Testing Native Screenshot Tool ---")
        out_png = os.path.join(self.test_dir, "test_shot.png")
        result = take_screenshot(filename=out_png)
        print(f"Screenshot Tool Result: {result}")
        self.assertIn("Screenshot successfully saved", result)
        self.assertTrue(os.path.exists(out_png))
        self.assertTrue(os.path.getsize(out_png) > 1000)

    def test_active_window_tool(self):
        print("\n--- Testing Active Window Inspection ---")
        res = get_active_window_info()
        print(f"Active Window Result:\n{res}")
        self.assertTrue(len(res) > 0)

    def test_gui_automation_tools(self):
        print("\n--- Testing GUI Input Automation ---")
        # Test hotkey toggle desktop
        res_hotkey = press_keyboard_shortcut(shortcut="win+d")
        print(f"Hotkey Result: {res_hotkey}")
        self.assertIn("Toggled Show Desktop", res_hotkey)

    def test_multimodal_vision_analysis(self):
        print("\n--- Testing Multimodal Vision Screen Analysis with Gemini ---")
        res = analyze_screen(query="Identify any text or visible desktop elements in this screenshot in 1-2 sentences.")
        print(f"Vision Analysis Result:\n{res}")
        self.assertIn("Screen Vision Analysis", res)

if __name__ == "__main__":
    unittest.main()
