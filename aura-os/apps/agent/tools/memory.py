from typing import Dict, Any
from tools.base import registry
from core.memory_manager import MemoryManager

@registry.register(
    name="remember_user_preference",
    description="Saves a user preference, habit, or contextual fact into persistent long-term memory.",
    risk_level="SAFE",
    required_permission="memory-write",
    verify_method=None
)
def remember_user_preference(key: str = None, value: str = None, category: str = "preference", **kwargs) -> str:
    k = key or kwargs.get("name") or kwargs.get("preference") or kwargs.get("item")
    v = value or kwargs.get("val") or kwargs.get("content") or kwargs.get("setting") or kwargs.get("detail")
    c = category or kwargs.get("type") or "preference"
    
    if not k or not v:
        return "Error: Both key and value must be provided to remember a preference."
        
    try:
        MemoryManager.set(k, v, c)
        return f"Successfully committed to memory: [{c.upper()}] '{k}' = '{v}'"
    except Exception as e:
        return f"Failed to record memory: {e}"

@registry.register(
    name="recall_user_preference",
    description="Queries persistent memory for a previously stored user preference or fact.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def recall_user_preference(key: str = None, **kwargs) -> str:
    k = key or kwargs.get("name") or kwargs.get("preference") or kwargs.get("item") or kwargs.get("query")
    if not k:
        return "Error: Specify the memory key to recall."
        
    try:
        val = MemoryManager.get(k)
        if val is not None:
            return f"Memory Retrieved: '{k}' = '{val}'"
        else:
            return f"No memory found for '{k}'."
    except Exception as e:
        return f"Memory query error: {e}"

@registry.register(
    name="list_stored_memories",
    description="Lists all remembered user preferences, settings, and facts.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def list_stored_memories(**kwargs) -> str:
    try:
        memories = MemoryManager.list_all()
        if not memories:
            return "Persistent Context Memory is currently empty."
            
        output = [f"Stored User Memories ({len(memories)} items):"]
        for m in memories:
            output.append(f" - [{m['category'].upper()}] {m['key']}: {m['value']} (Updated: {m['updated_at']})")
        return "\n".join(output)
    except Exception as e:
        return f"Failed to list memories: {e}"

@registry.register(
    name="forget_memory",
    description="Deletes a specific remembered user preference from persistent memory.",
    risk_level="SAFE",
    required_permission="memory-write",
    verify_method=None
)
def forget_memory(key: str = None, **kwargs) -> str:
    k = key or kwargs.get("name") or kwargs.get("preference") or kwargs.get("item")
    if not k:
        return "Error: Specify the memory key to forget."
    try:
        deleted = MemoryManager.delete(k)
        if deleted:
            return f"Successfully deleted '{k}' from memory."
        else:
            return f"Memory key '{k}' was not found."
    except Exception as e:
        return f"Failed to delete memory: {e}"
