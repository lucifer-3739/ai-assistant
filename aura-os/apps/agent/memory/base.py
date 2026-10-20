from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class Memory(ABC):
    @abstractmethod
    def store_memory(self, memory_type: str, key_name: str, value: str, session_id: Optional[str] = None):
        """Stores a key-value memory fact (SHORT_TERM or LONG_TERM)."""
        pass

    @abstractmethod
    def retrieve_memories(self, memory_type: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all memories of a given type."""
        pass

    @abstractmethod
    def search_memories(self, query: str, memory_type: str, session_id: Optional[str] = None) -> List[str]:
        """Simple keyword search across stored memories."""
        pass
