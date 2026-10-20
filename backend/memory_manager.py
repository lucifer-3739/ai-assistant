import os
import json
import numpy as np
from google import genai
from google.genai.errors import APIError

class MemoryManager:
    def __init__(self, gemini_client: genai.Client = None, filepath: str = "backend/memory.json"):
        self.filepath = filepath
        self.gemini_client = gemini_client
        self.memories = []
        self._load_memories()

    def _load_memories(self):
        """Loads memories from the local JSON file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.memories = json.load(f)
                print(f"[Memory Manager] Loaded {len(self.memories)} memories.")
            except Exception as e:
                print(f"[Memory Manager Error] Failed to load memory file: {e}")
                self.memories = []
        else:
            self.memories = []

    def _save_memories(self):
        """Saves current memories to the local JSON file."""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Memory Manager Error] Failed to save memory file: {e}")

    def _get_embedding(self, text: str) -> list[float]:
        """Generates embedding for the text using Gemini API."""
        if not self.gemini_client:
            print("[Memory Manager] Gemini client not configured. Cannot generate embeddings.")
            return []
            
        try:
            # We use text-embedding-004 which is the standard Gemini embedding model
            response = self.gemini_client.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            # Check response format
            if response.embedding and response.embedding.values:
                return [float(x) for x in response.embedding.values]
            elif isinstance(response.embeddings, list) and len(response.embeddings) > 0:
                return [float(x) for x in response.embeddings[0].values]
        except APIError as ae:
            print(f"[Memory Manager Error] Gemini Embedding API error: {ae}")
        except Exception as e:
            print(f"[Memory Manager Error] Embedding unexpected exception: {e}")
        return []

    def add_memory(self, text: str) -> bool:
        """Adds a fact to long-term memory."""
        text = text.strip()
        if not text:
            return False

        # Check if already exists to avoid exact duplicates
        for m in self.memories:
            if m["text"].lower() == text.lower():
                return True

        print(f"[Memory Manager] Storing new memory: '{text}'")
        embedding = self._get_embedding(text)
        if not embedding:
            # Fallback: store text anyway, though similarity search won't work perfectly on it,
            # but it is better than discarding it. We can search by keyword.
            embedding = []

        self.memories.append({
            "text": text,
            "embedding": embedding
        })
        self._save_memories()
        return True

    def retrieve_memories(self, query: str, top_k: int = 3) -> list[str]:
        """Retrieves top_k relevant memories for a query based on cosine similarity."""
        query = query.strip()
        if not query or not self.memories:
            return []

        query_vector = self._get_embedding(query)
        if not query_vector:
            # Fallback: simple keyword containment match if embeddings fail or aren't configured
            print("[Memory Manager] Falling back to keyword memory matching.")
            query_lower = query.lower()
            matched = []
            for m in self.memories:
                m_words = set(m["text"].lower().split())
                q_words = set(query_lower.split())
                intersection = m_words.intersection(q_words)
                if intersection:
                    matched.append((len(intersection), m["text"]))
            matched.sort(reverse=True)
            return [text for count, text in matched[:top_k]]

        scored_memories = []
        q_vec = np.array(query_vector, dtype=np.float32)
        norm_q = np.linalg.norm(q_vec)

        for m in self.memories:
            if not m.get("embedding"):
                continue
                
            m_vec = np.array(m["embedding"], dtype=np.float32)
            norm_m = np.linalg.norm(m_vec)
            
            if norm_q == 0 or norm_m == 0:
                score = 0.0
            else:
                score = float(np.dot(q_vec, m_vec) / (norm_q * norm_m))
                
            scored_memories.append((score, m["text"]))

        # Sort by score descending
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        # Return top-k memories that pass a reasonable similarity threshold (e.g. 0.3)
        threshold = 0.3
        results = [text for score, text in scored_memories[:top_k] if score >= threshold]
        print(f"[Memory Manager] Retrieved memories: {results}")
        return results
