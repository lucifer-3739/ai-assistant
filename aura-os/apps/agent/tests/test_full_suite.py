import os
import sys
import shutil
import tempfile
import unittest
import asyncio
from dotenv import load_dotenv

# Ensure agent directory is in Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from database.schema import init_db
from database.connection import get_connection
from core.memory_manager import MemoryManager
from core.ai_provider import GeminiProvider
from core.planner import Planner
from core.executor import Executor
from core.verifier import Verifier
from tools.base import registry
from tools.system_control import get_battery_status, get_network_status, list_top_processes, set_system_volume
from tools.organizer import organize_directory, find_duplicate_files, get_directory_analytics
from tools.vision import take_screenshot, get_active_window_info, analyze_screen
from tools.gui import type_text, press_keyboard_shortcut
from tools.browser import open_url, search_web, play_media
from security.permissions import requires_approval, resolve_permission, pending_approvals
from security.auditor import log_action
from voice.text_to_speech import gTTSProvider
from voice.wake_word import LocalWakeWordProvider

class FullSystemTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="friday_full_test_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # 1. Database & Memory Layer
    def test_01_database_and_memory(self):
        print("\n[TEST 01] Verifying SQLite DB and Context Memory Engine...")
        MemoryManager.set("user_name", "Tony Stark", "identity")
        MemoryManager.set("default_browser", "Chrome", "preference")
        
        val = MemoryManager.get("user_name")
        self.assertEqual(val, "Tony Stark")
        
        all_mems = MemoryManager.list_all()
        self.assertTrue(len(all_mems) >= 2)
        
        prompt_ctx = MemoryManager.get_prompt_context()
        self.assertIn("user_name: Tony Stark", prompt_ctx)
        print("  -> Context Memory successfully verified.")

    # 2. System Control & Hardware Tools
    def test_02_system_control_tools(self):
        print("\n[TEST 02] Verifying System Control & Diagnostics Tools...")
        battery = get_battery_status()
        self.assertTrue(len(battery) > 0)
        
        network = get_network_status()
        self.assertIn("Network Uplink Status", network)
        
        procs = list_top_processes(count=3)
        self.assertIn("Active Processes", procs)
        
        vol = set_system_volume(action="up")
        self.assertIn("master system volume", vol)
        print("  -> System diagnostics and volume tools verified.")

    # 3. Smart Organizer & Duplicate File Finder
    def test_03_file_organizer_and_analytics(self):
        print("\n[TEST 03] Verifying Smart File Organizer & Hashing...")
        f1 = os.path.join(self.test_dir, "doc1.txt")
        f2 = os.path.join(self.test_dir, "doc2_dup.txt")
        f3 = os.path.join(self.test_dir, "image.png")
        
        with open(f1, "w") as f: f.write("IDENTICAL CONTENT 12345")
        with open(f2, "w") as f: f.write("IDENTICAL CONTENT 12345")
        with open(f3, "wb") as f: f.write(b"IMAGE_PNG_BYTES")
        
        dups = find_duplicate_files(directory_path=self.test_dir)
        self.assertIn("Found 1 sets of identical duplicate files", dups)
        
        analytics = get_directory_analytics(directory_path=self.test_dir)
        self.assertIn("Total Files: 3", analytics)
        
        org = organize_directory(directory_path=self.test_dir)
        self.assertIn("Automated Organization Complete", org)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documents", "doc1.txt")))
        print("  -> Smart file organizer and SHA-256 duplicate scanner verified.")

    # 4. Multi-Modal Vision & Screen Capture
    def test_04_multimodal_vision(self):
        print("\n[TEST 04] Verifying Screen Capture & Vision Analysis...")
        shot_path = os.path.join(self.test_dir, "screenshot.png")
        shot_res = take_screenshot(filename=shot_path)
        self.assertIn("Screenshot successfully saved", shot_res)
        self.assertTrue(os.path.exists(shot_path))
        
        win_info = get_active_window_info()
        self.assertTrue(len(win_info) > 0)
        
        vision_res = analyze_screen(query="Provide a 1-sentence description of the screen.")
        self.assertIn("Screen Vision Analysis", vision_res)
        print("  -> Screen capture and Gemini multimodal vision verified.")

    # 5. GUI Input Automation
    def test_05_gui_automation(self):
        print("\n[TEST 05] Verifying GUI Hotkey & SendKeys Automation...")
        hotkey_res = press_keyboard_shortcut(shortcut="win+d")
        self.assertIn("Toggled Show Desktop", hotkey_res)
        print("  -> GUI automation verified.")

    # 6. Security Gate & Risk Interception
    def test_06_security_auditor_and_gating(self):
        print("\n[TEST 06] Verifying Security Auditor & Risk Approval...")
        self.assertTrue(requires_approval("DANGEROUS"))
        self.assertTrue(requires_approval("CRITICAL"))
        self.assertFalse(requires_approval("SAFE"))
        self.assertFalse(requires_approval("MODERATE"))
        
        log_action("test-task-uuid", "delete_file", {"filepath": "dummy.txt"}, None, "DANGEROUS", "PENDING_APPROVAL")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tool_name, risk_level, permission_status FROM audit_log WHERE task_id = 'test-task-uuid'")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["tool_name"], "delete_file")
            self.assertEqual(row["permission_status"], "PENDING_APPROVAL")
        print("  -> Security gate risk rules and audit persistence verified.")

    # 7. AI Planner & Tool Registry
    def test_07_ai_planner_and_execution(self):
        print("\n[TEST 07] Verifying AI Planner Formulation...")
        provider = GeminiProvider()
        planner = Planner(provider)
        tools = registry.list_tools()
        
        plan = asyncio.run(planner.create_plan("Open Notepad and check battery", tools))
        self.assertIsInstance(plan, list)
        self.assertTrue(len(plan) >= 1)
        self.assertIn("step_number", plan[0])
        print(f"  -> Planner generated {len(plan)} structured steps successfully.")

    # 8. Continuous Voice Wake Word & Task Separation Provider
    def test_08_voice_wake_word_keywords(self):
        print("\n[TEST 08] Verifying FRIDAY Continuous Wake Word & Task Separation...")
        from voice.wake_word import extract_command_after_wake_word
        ww = LocalWakeWordProvider(keyword="friday")
        self.assertEqual(ww.keyword, "friday")
        
        trig, cmd = extract_command_after_wake_word("friday open notepad and write test")
        self.assertTrue(trig)
        self.assertEqual(cmd, "open notepad and write test")
        print("  -> FRIDAY continuous wake word and task separation verified.")

if __name__ == "__main__":
    unittest.main()
