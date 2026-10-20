from typing import List, Dict, Any, Optional
from memory.base import Memory
from database.connection import get_connection

class SQLiteMemory(Memory):
    def store_memory(self, memory_type: str, key_name: str, value: str, session_id: Optional[str] = None):
        """Stores a key-value memory in SQLite."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                # Check if it already exists to avoid exact duplicates
                cursor.execute("""
                SELECT id FROM memory 
                WHERE memory_type = ? AND key_name = ? AND (session_id = ? OR (session_id IS NULL AND ? IS NULL))
                """, (memory_type.upper(), key_name, session_id, session_id))
                row = cursor.fetchone()
                
                if row:
                    # Update
                    cursor.execute("""
                    UPDATE memory SET value = ?, created_at = CURRENT_TIMESTAMP WHERE id = ?
                    """, (value, row["id"]))
                else:
                    # Insert
                    cursor.execute("""
                    INSERT INTO memory (memory_type, session_id, key_name, value)
                    VALUES (?, ?, ?, ?)
                    """, (memory_type.upper(), session_id, key_name, value))
            print(f"[Memory] Stored {memory_type} memory: '{key_name}' = '{value}'")
        except Exception as e:
            print(f"[Memory Error] Failed to store memory: {e}")

    def retrieve_memories(self, memory_type: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all memories of a given type from SQLite."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                if session_id:
                    cursor.execute("""
                    SELECT key_name, value FROM memory 
                    WHERE memory_type = ? AND session_id = ?
                    ORDER BY created_at DESC
                    """, (memory_type.upper(), session_id))
                else:
                    cursor.execute("""
                    SELECT key_name, value FROM memory 
                    WHERE memory_type = ?
                    ORDER BY created_at DESC
                    """, (memory_type.upper(),))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Memory Error] Failed to retrieve memories: {e}")
            return []

    def search_memories(self, query: str, memory_type: str, session_id: Optional[str] = None) -> List[str]:
        """Performs simple keyword search on stored memory values."""
        try:
            query_str = f"%{query}%"
            with get_connection() as conn:
                cursor = conn.cursor()
                if session_id:
                    cursor.execute("""
                    SELECT value FROM memory 
                    WHERE memory_type = ? AND session_id = ? AND (key_name LIKE ? OR value LIKE ?)
                    """, (memory_type.upper(), session_id, query_str, query_str))
                else:
                    cursor.execute("""
                    SELECT value FROM memory 
                    WHERE memory_type = ? AND (key_name LIKE ? OR value LIKE ?)
                    """, (memory_type.upper(), query_str, query_str))
                return [row["value"] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Memory Error] Failed to search memories: {e}")
            return []
