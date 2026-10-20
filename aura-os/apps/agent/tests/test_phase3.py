import os
import sys
import shutil
import tempfile
import unittest

# Ensure agent folder is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db
from core.memory_manager import MemoryManager
from tools.system_control import get_battery_status, get_network_status, list_top_processes
from tools.organizer import organize_directory, find_duplicate_files, get_directory_analytics
from tools.memory import remember_user_preference, recall_user_preference, list_stored_memories

class TestPhase3System(unittest.TestCase):
    def setUp(self):
        init_db()
        self.test_dir = tempfile.mkdtemp(prefix="aura_test_organizer_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_system_control_tools(self):
        print("\n--- Testing System Control Tools ---")
        
        # Test battery
        bat = get_battery_status()
        print(f"Battery Tool Result: {bat}")
        self.assertTrue(len(bat) > 0)

        # Test network
        net = get_network_status()
        print(f"Network Tool Result:\n{net}")
        self.assertIn("Network Uplink Status", net)

        # Test processes
        procs = list_top_processes(count=5)
        print(f"Top Processes:\n{procs[:200]}...")
        self.assertIn("Active Processes", procs)

    def test_smart_organizer_and_duplicates(self):
        print("\n--- Testing Smart File Organizer ---")
        
        # Create unorganized sample files
        doc_file = os.path.join(self.test_dir, "report.pdf")
        img_file1 = os.path.join(self.test_dir, "photo.png")
        img_file2 = os.path.join(self.test_dir, "photo_copy.png")
        code_file = os.path.join(self.test_dir, "script.py")

        with open(doc_file, "w") as f:
            f.write("Sample PDF content")
        with open(img_file1, "wb") as f:
            f.write(b"IDENTICAL_IMAGE_BYTES_12345")
        with open(img_file2, "wb") as f:
            f.write(b"IDENTICAL_IMAGE_BYTES_12345")
        with open(code_file, "w") as f:
            f.write("print('hello world')")

        # Test duplicate finder
        dup_result = find_duplicate_files(directory_path=self.test_dir)
        print(f"Duplicate Finder Result:\n{dup_result}")
        self.assertIn("Found 1 sets of identical duplicate files", dup_result)

        # Test directory analytics
        analytics = get_directory_analytics(directory_path=self.test_dir)
        print(f"Directory Analytics:\n{analytics}")
        self.assertIn("Total Files: 4", analytics)

        # Test smart organize
        org_result = organize_directory(directory_path=self.test_dir)
        print(f"Organize Result:\n{org_result}")
        self.assertIn("Automated Organization Complete", org_result)
        
        # Verify categorized subdirectories exist
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documents", "report.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Images", "photo.png")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Code", "script.py")))

    def test_persistent_context_memory(self):
        print("\n--- Testing Persistent Context Memory ---")
        
        # Set memory via tool
        res = remember_user_preference(key="preferred_editor", value="VS Code", category="tooling")
        print(f"Remember Tool: {res}")
        self.assertIn("Successfully committed", res)

        # Recall memory via tool
        recall_res = recall_user_preference(key="preferred_editor")
        print(f"Recall Tool: {recall_res}")
        self.assertIn("VS Code", recall_res)

        # Check prompt context formatting
        prompt_ctx = MemoryManager.get_prompt_context()
        print(f"Prompt Context Injected:\n{prompt_ctx}")
        self.assertIn("preferred_editor: VS Code", prompt_ctx)

if __name__ == "__main__":
    unittest.main()
