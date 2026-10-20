import os
from typing import Dict, List, Any, Optional
from database.connection import get_connection

class MemoryManager:
    """Manages long-term user preferences and context memory stored in SQLite."""

    @staticmethod
    def set(key: str, value: str, category: str = "preference"):
        """Inserts or updates a memory key-value pair, ensuring uniqueness per key."""
        cleaned_key = str(key).strip().lower()
        cleaned_val = str(value).strip()
        cleaned_cat = str(category).strip().lower()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            # Remove any prior duplicate entries for this key to guarantee 1 entry per key
            cursor.execute("DELETE FROM memory WHERE key_name = ?", (cleaned_key,))
            cursor.execute(
                """
                INSERT INTO memory (key_name, value, memory_type) 
                VALUES (?, ?, ?)
                """,
                (cleaned_key, cleaned_val, cleaned_cat)
            )

    @staticmethod
    def get(key: str) -> Optional[str]:
        """Retrieves a remembered value for a specific key."""
        cleaned_key = str(key).strip().lower()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM memory WHERE key_name = ? ORDER BY id DESC LIMIT 1", (cleaned_key,))
            row = cursor.fetchone()
            return row["value"] if row else None

    @staticmethod
    def delete(key: str) -> bool:
        """Deletes all remembered records for a specific key."""
        cleaned_key = str(key).strip().lower()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory WHERE key_name = ?", (cleaned_key,))
            return cursor.rowcount > 0

    @staticmethod
    def list_all() -> List[Dict[str, Any]]:
        """Returns all remembered memories deduplicated by key."""
        with get_connection() as conn:
            cursor = conn.cursor()
            # Fetch the most recent entry for each unique key_name
            cursor.execute("""
                SELECT m.id, m.key_name, m.value, m.memory_type, m.created_at
                FROM memory m
                INNER JOIN (
                    SELECT key_name, MAX(id) as max_id
                    FROM memory
                    GROUP BY key_name
                ) latest ON m.id = latest.max_id
                ORDER BY m.id DESC
            """)
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "key": r["key_name"],
                    "value": r["value"],
                    "category": r["memory_type"],
                    "created_at": r["created_at"]
                }
                for r in rows
            ]

    @staticmethod
    def get_prompt_context() -> str:
        """Formats remembered preferences into a structured string for the LLM Planner."""
        memories = MemoryManager.list_all()
        if not memories:
            return ""
            
        lines = ["User Preferences & Remembered Facts:"]
        for m in memories:
            lines.append(f"- [{m['category'].upper()}] {m['key']}: {m['value']}")
        return "\n".join(lines)
