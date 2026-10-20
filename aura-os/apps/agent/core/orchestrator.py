import uuid
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from core.ai_provider import AIProvider
from core.planner import Planner
from core.executor import Executor
from tools.base import registry
from database.connection import get_connection

class Orchestrator:
    def __init__(self, ai_provider: AIProvider, broadcast_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.ai_provider = ai_provider
        self.planner = Planner(ai_provider)
        self.executor = Executor()
        self.broadcast_callback = broadcast_callback

    async def broadcast(self, task_id: str):
        """Fetches current task details from DB and broadcasts them to WebSocket clients."""
        if not self.broadcast_callback:
            return
            
        try:
            details = self.get_task_details(task_id)
            if details:
                await self.broadcast_callback(task_id, details)
        except Exception as e:
            print(f"[Orchestrator Broadcast Warning] Failed to broadcast updates: {e}")

    def create_task(self, user_request: str) -> str:
        """Initializes a new task in the database and returns its UUID."""
        task_id = str(uuid.uuid4())
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO tasks (id, user_request, state) VALUES (?, ?, ?)",
                    (task_id, user_request, "UNDERSTANDING")
                )
            print(f"[Orchestrator] Created task: {task_id} for request: '{user_request}'")
            return task_id
        except Exception as e:
            print(f"[Orchestrator DB Error] Failed to create task: {e}")
            raise e

    async def execute_task(self, task_id: str):
        """Asynchronously executes the task lifecycle: Plan -> Execute -> Verify."""
        try:
            # 1. Update state to PLANNING
            self._update_task_state(task_id, "PLANNING")
            await self.broadcast(task_id)

            # Get request content
            task_info = self._get_task(task_id)
            if not task_info:
                print(f"[Orchestrator Error] Task '{task_id}' not found.")
                return

            user_request = task_info["user_request"]

            # Get available tools info to pass to the planner
            available_tools = registry.list_tools()

            # Generate plan
            plan_steps = await self.planner.create_plan(user_request, available_tools)
            
            # Save plan steps in DB
            self._save_plan_in_db(task_id, plan_steps)
            await self.broadcast(task_id)

            # 2. Iterate and execute steps
            db_steps = self._get_task_steps(task_id)
            
            for step in db_steps:
                step_id = step["id"]
                step_num = step["step_number"]
                tool_name = step["tool_name"]
                tool_args_str = step["tool_args"]
                
                # Check for cancelled state
                current_task = self._get_task(task_id)
                if current_task and current_task["state"] in ("CANCELLED", "FAILED"):
                    print(f"[Orchestrator] Stop executing task '{task_id}': State is {current_task['state']}")
                    break

                # If the step is just an informative step (no tool), complete it directly
                if not tool_name:
                    self._update_step_in_db(step_id, "COMPLETED", "Logical step completed.", "No verification needed.")
                    continue

                # Parse arguments
                tool_args = {}
                if tool_args_str:
                    try:
                        tool_args = json.loads(tool_args_str)
                    except Exception:
                        pass

                # Check if tool risk requires suspending task state to WAITING_FOR_PERMISSION
                tool_info = registry.get_tool(tool_name)
                if tool_info and tool_info[1].risk_level.upper() in ("DANGEROUS", "CRITICAL"):
                    self._update_task_state(task_id, "WAITING_FOR_PERMISSION")
                    await self.broadcast(task_id)

                # Set task state to EXECUTING
                self._update_task_state(task_id, "EXECUTING")
                await self.broadcast(task_id)

                # Execute
                result_text, success, verification = await self.executor.execute_step(
                    task_id, step_id, tool_name, tool_args
                )

                # Observe / Verify State transitions
                self._update_task_state(task_id, "OBSERVING")
                await self.broadcast(task_id)
                await asyncio.sleep(0.5) # Simulate observing time

                self._update_task_state(task_id, "VERIFYING")
                await self.broadcast(task_id)

                if not success:
                    # Recovery / Replanning Trigger
                    self._update_task_state(task_id, "RECOVERING")
                    await self.broadcast(task_id)
                    
                    # For Phase 1, we log the failure and set task to FAILED
                    print(f"[Orchestrator] Step {step_num} failed! Mark task '{task_id}' as FAILED.")
                    self._update_task_state(task_id, "FAILED")
                    await self.broadcast(task_id)
                    return

            # If loop finished successfully
            current_task = self._get_task(task_id)
            if current_task and current_task["state"] not in ("FAILED", "CANCELLED"):
                self._update_task_state(task_id, "COMPLETED")
                await self.broadcast(task_id)
                print(f"[Orchestrator] Task '{task_id}' completed successfully.")

        except Exception as e:
            print(f"[Orchestrator Error] Execution loop crashed for task '{task_id}': {e}")
            self._update_task_state(task_id, "FAILED")
            await self.broadcast(task_id)

    # --- Database Helpers ---
    def _update_task_state(self, task_id: str, state: str):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (state, task_id)
                )
        except Exception as e:
            print(f"[Orchestrator DB Error] Failed to update task state: {e}")

    def _get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[Orchestrator DB Error] Failed to fetch task: {e}")
            return None

    def _save_plan_in_db(self, task_id: str, plan_steps: List[Dict[str, Any]]):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Clean up existing steps if any
                cursor.execute("DELETE FROM plan_steps WHERE task_id = ?", (task_id,))
                for step in plan_steps:
                    cursor.execute("""
                    INSERT INTO plan_steps (task_id, step_number, description, tool_name, tool_args, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        task_id,
                        step["step_number"],
                        step["description"],
                        step.get("tool_name"),
                        json.dumps(step.get("tool_args")) if step.get("tool_args") else None,
                        "PENDING"
                    ))
        except Exception as e:
            print(f"[Orchestrator DB Error] Failed to save plan steps: {e}")

    def _get_task_steps(self, task_id: str) -> List[Dict[str, Any]]:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM plan_steps WHERE task_id = ? ORDER BY step_number ASC", (task_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Orchestrator DB Error] Failed to get task steps: {e}")
            return []

    def _update_step_in_db(self, step_id: int, status: str, result: str, verification: str):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                UPDATE plan_steps SET status = ?, result = ?, verification_result = ? WHERE id = ?
                """, (status, result, verification, step_id))
        except Exception as e:
            print(f"[Orchestrator DB Error] Failed to update logical step: {e}")

    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Fetches full task details, state, and plan progress for serialization."""
        task = self._get_task(task_id)
        if not task:
            return None
        steps = self._get_task_steps(task_id)
        return {
            "task_id": task["id"],
            "user_request": task["user_request"],
            "state": task["state"],
            "created_at": task["created_at"],
            "steps": [
                {
                    "step_number": s["step_number"],
                    "description": s["description"],
                    "tool_name": s["tool_name"],
                    "tool_args": json.loads(s["tool_args"]) if s["tool_args"] else None,
                    "status": s["status"],
                    "result": s["result"],
                    "verification_result": s["verification_result"]
                } for s in steps
            ]
        }
