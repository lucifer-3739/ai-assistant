import asyncio
from typing import Dict, Any

# Global store for pending permission responses
# Key: task_id (str), Value: {"event": asyncio.Event, "approved": bool}
pending_approvals: Dict[str, Dict[str, Any]] = {}

def requires_approval(risk_level: str) -> bool:
    """Determines whether a tool risk level requires explicit user confirmation."""
    risk_upper = risk_level.upper()
    # SAFE and MODERATE do not require prompts in default mode.
    # DANGEROUS and CRITICAL always require explicit user prompt.
    return risk_upper in ("DANGEROUS", "CRITICAL")

async def request_permission(task_id: str, tool_name: str, arguments: Dict[str, Any], risk_level: str) -> bool:
    """Registers a permission request, suspends execution asynchronously, 
    and returns True if approved, False if rejected.
    """
    if not requires_approval(risk_level):
        return True

    print(f"[Security Check] Suspending task '{task_id}' for tool '{tool_name}' (Risk: {risk_level})")
    
    # Create the wait event
    event = asyncio.Event()
    pending_approvals[task_id] = {
        "event": event,
        "tool_name": tool_name,
        "arguments": arguments,
        "risk_level": risk_level,
        "approved": False
    }

    # In main.py, we will broadcast this state change to the frontend UI
    # via WebSocket, indicating AURA OS is in WAITING_FOR_PERMISSION state
    
    try:
        # Wait asynchronously until the event is set (via API call)
        await event.wait()
        
        # Check user decision
        decision = pending_approvals[task_id]["approved"]
        print(f"[Security Check] Resuming task '{task_id}': User approved = {decision}")
        return decision
    finally:
        # Clean up global dict
        if task_id in pending_approvals:
            del pending_approvals[task_id]

def resolve_permission(task_id: str, approved: bool):
    """Sets the event for a pending permission request, resuming execution."""
    if task_id in pending_approvals:
        pending_approvals[task_id]["approved"] = approved
        pending_approvals[task_id]["event"].set()
        return True
    return False

def get_pending_request(task_id: str) -> Optional[Dict[str, Any]]:
    """Gets details of a pending permission check."""
    if task_id in pending_approvals:
        req = pending_approvals[task_id]
        return {
            "tool_name": req["tool_name"],
            "arguments": req["arguments"],
            "risk_level": req["risk_level"]
        }
    return None
