import os
import sys
import unittest
import asyncio
from typing import Dict, Any

# Ensure agent folder is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.base import registry, ToolInfo
from security.permissions import requires_approval, resolve_permission, pending_approvals
from core.verifier import Verifier
from core.ai_provider import AIProvider, AIResponse
from core.planner import Planner

# A mock tool for testing
def mock_verify_exists(path: str) -> bool:
    return True

class TestAgentCore(unittest.TestCase):

    def setUp(self):
        # Register a test tool to verify registry
        @registry.register(
            name="test_dummy_tool",
            description="A test tool that does nothing.",
            risk_level="SAFE",
            required_permission="read-only",
            verify_method=mock_verify_exists
        )
        def test_dummy_tool(path: str) -> str:
            return f"Processed {path}"

    def test_tool_registry(self):
        tool_entry = registry.get_tool("test_dummy_tool")
        self.assertIsNotNone(tool_entry)
        
        func, info = tool_entry
        self.assertEqual(info.name, "test_dummy_tool")
        self.assertEqual(info.risk_level, "SAFE")
        self.assertEqual(info.required_permission, "read-only")
        
        # Test generic signature reflection
        self.assertIn("path", info.parameters["properties"])

    def test_permission_model(self):
        # SAFE and MODERATE should return False for requires_approval (meaning they are safe to auto-run)
        self.assertFalse(requires_approval("SAFE"))
        self.assertFalse(requires_approval("MODERATE"))
        
        # DANGEROUS and CRITICAL must require approval
        self.assertTrue(requires_approval("DANGEROUS"))
        self.assertTrue(requires_approval("CRITICAL"))

    def test_verifier(self):
        verifier = Verifier()
        
        # Test general text checks
        success, explanation = verifier.verify_step("tool", {}, "Error executing command", None)
        self.assertFalse(success)
        self.assertIn("Error", explanation)
        
        # Test custom verify method
        success, explanation = verifier.verify_step("test_dummy_tool", {"path": "test.txt"}, "Completed successfully", mock_verify_exists)
        self.assertTrue(success)

class MockAIProvider(AIProvider):
    async def generate(self, prompt: str, system_instruction=None, tools=None, history=None) -> AIResponse:
        return AIResponse(
            text='[{"step_number": 1, "description": "Create folder", "tool_name": "create_folder", "tool_args": {"path": "test"}}]'
        )

class TestPlanner(unittest.IsolatedAsyncioTestCase):
    async def test_planner_json(self):
        mock_ai = MockAIProvider()
        planner = Planner(mock_ai)
        
        # Create a plan
        plan = await planner.create_plan("Create folder test", [])
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["step_number"], 1)
        self.assertEqual(plan[0]["tool_name"], "create_folder")
        self.assertEqual(plan[0]["tool_args"]["path"], "test")

if __name__ == "__main__":
    unittest.main()
