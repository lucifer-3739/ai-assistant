import json
import asyncio
from typing import Dict, Any, Optional
from tools.base import registry
from security.permissions import request_permission
from security.auditor import log_action
from core.verifier import Verifier
from database.connection import get_connection

class Executor:
    def __init__(self):
        self.verifier = Verifier()

    async def execute_step(self, task_id: str, step_id: int, tool_name: str, tool_args: Optional[Dict[str, Any]]) -> tuple[str, bool, str]:
        """Executes a single step in a task's plan.
        Returns a tuple: (result_text: str, success: bool, verification_explanation: str).
        """
        # 1. Look up tool
        tool_entry = registry.get_tool(tool_name)
        if not tool_entry:
            err_msg = f"Error: Tool '{tool_name}' is not registered in AURA OS."
            self._update_step_in_db(step_id, "FAILED", err_msg, "Tool not found.")
            return err_msg, False, "Tool not found."
            
        func, info = tool_entry
        args = tool_args or {}

        # 2. Check Security & Permissions (Asynchronous check)
        print(f"[Executor] Checking permission for tool '{tool_name}' (Risk: {info.risk_level})")
        
        # Log entry in audit log that permission checking started
        log_action(task_id, tool_name, args, None, info.risk_level, "PENDING_APPROVAL")

        # Suspend task execution asynchronously if user approval is needed
        approved = await request_permission(task_id, tool_name, args, info.risk_level)
        
        if not approved:
            err_msg = f"Permission Denied: User rejected execution of tool '{tool_name}'."
            # Update step in DB
            self._update_step_in_db(step_id, "FAILED", err_msg, "Rejected by user.")
            # Record in audit log
            log_action(task_id, tool_name, args, {"error": err_msg}, info.risk_level, "DENIED")
            return err_msg, False, "User rejected execution."

        # 3. Execute Tool
        print(f"[Executor] Running tool '{tool_name}' with args: {args}")
        self._update_step_status_in_db(step_id, "EXECUTING")
        
        result_text = ""
        try:
            # Check if function expects a task_id
            # (framework context argument)
            import inspect
            sig = inspect.signature(func)
            if "task_id" in sig.parameters:
                # Run sync functions in threadpool if they are blocking, or call directly
                # (in Phase 1, tools are standard sync Python functions, so we run directly)
                result_text = func(task_id=task_id, **args)
            else:
                result_text = func(**args)
        except Exception as e:
            result_text = f"Error executing tool: {e}"

        # 4. Verify Outcome
        success, explanation = self.verifier.verify_step(tool_name, args, result_text, info.verify_method)
        
        status = "COMPLETED" if success else "FAILED"
        self._update_step_in_db(step_id, status, result_text, explanation)

        # 5. Write final entry in audit log
        log_action(task_id, tool_name, args, {"result": result_text}, info.risk_level, "ALLOWED")

        return result_text, success, explanation

    def _update_step_status_in_db(self, step_id: int, status: str):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE plan_steps SET status = ? WHERE id = ?",
                    (status, step_id)
                )
        except Exception as e:
            print(f"[Executor DB Error] Failed to update step status: {e}")

    def _update_step_in_db(self, step_id: int, status: str, result: str, verification_result: str):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE plan_steps SET status = ?, result = ?, verification_result = ? WHERE id = ?",
                    (status, result, verification_result, step_id)
                )
        except Exception as e:
            print(f"[Executor DB Error] Failed to update step details: {e}")
