import json
from typing import Dict, Any, Optional
from database.connection import get_connection

def log_action(
    task_id: Optional[str],
    tool_name: str,
    arguments: Dict[str, Any],
    result: Optional[Dict[str, Any]],
    risk_level: str,
    permission_status: str
):
    """Securely logs a tool action to the database audit_log table.
    Ensures passwords or secrets are not written.
    """
    # Sanitize arguments and results to filter out potentially sensitive keywords (e.g., API keys, passwords)
    sanitized_args = _sanitize(arguments)
    sanitized_result = _sanitize(result) if result else None
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audit_log (task_id, tool_name, arguments, result, risk_level, permission_status)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                tool_name,
                json.dumps(sanitized_args),
                json.dumps(sanitized_result) if sanitized_result else None,
                risk_level,
                permission_status
            ))
            print(f"[Audit Log] Recorded action for tool: {tool_name} (Risk: {risk_level}, Status: {permission_status})")
    except Exception as e:
        print(f"[Audit Log Error] Failed to write audit entry: {e}")

def _sanitize(data: Any) -> Any:
    """Recursively redacts values for keys resembling passwords or tokens."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = k.lower()
            if any(secret in k_lower for secret in ("key", "password", "token", "secret", "auth")):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = _sanitize(v)
        return sanitized
    elif isinstance(data, list):
        return [_sanitize(item) for item in data]
    return data
