import os
import asyncio
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

class AIResponse(BaseModel):
    text: str
    tool_calls: Optional[List[Dict[str, Any]]] = None

class AIProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/png"
    ) -> AIResponse:
        """Sends a request to the LLM provider and returns the structured AIResponse."""
        pass

class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None):
        # Read key from argument, or fallback to environment
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("[GeminiProvider] WARNING: GEMINI_API_KEY is not set. Provider running in dry-run/mock mode.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)
            print(f"[GeminiProvider] Initialized using model: {self.model_name}")

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/png"
    ) -> AIResponse:
        if not self.client:
            # Running in mock mode
            return self._mock_response(prompt)
            
        try:
            config_args = {}
            if system_instruction:
                config_args["system_instruction"] = system_instruction
            if tools:
                config_args["tools"] = tools

            # Map chat history format to Gemini API Content types
            contents = []
            if history:
                for msg in history:
                    role = "model" if msg["role"] == "model" else "user"
                    contents.append(
                        types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=msg["text"])]
                        )
                    )
            
            # Attach image part if multimodal analysis is requested
            if image_bytes:
                contents.append(
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type
                    )
                )

            # Append the current prompt
            contents.append(prompt)

            # Run blocking generate_content in asyncio thread executor to keep the server non-blocking
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(**config_args) if config_args else None
                )
            )

            # Check for function calls
            tool_calls = []
            if response.function_calls:
                for call in response.function_calls:
                    tool_calls.append({
                        "name": call.name,
                        "args": {k: v for k, v in call.args.items()} if call.args else {}
                    })

            return AIResponse(
                text=response.text or "",
                tool_calls=tool_calls if tool_calls else None
            )
            
        except APIError as ae:
            print(f"[GeminiProvider Error] API Error: {ae}")
            raise RuntimeError(f"Gemini API Error: {ae.message}")
        except Exception as e:
            print(f"[GeminiProvider Error] Unexpected error: {e}")
            raise RuntimeError(f"Unexpected LLM failure: {str(e)}")

    def _mock_response(self, prompt: str) -> AIResponse:
        """Fallback mock responses for testing without API keys."""
        p_lower = prompt.lower()
        if "plan" in p_lower:
            return AIResponse(text="""[
                {"step_number": 1, "description": "Mock plan execution step", "tool_name": "list_directory", "tool_args": {"path": "."}}
            ]""")
        return AIResponse(text="AURA OS Mock response: Operational.")
