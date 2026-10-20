from abc import ABC, abstractmethod
from typing import Any

class SpeechToTextProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_data: Any) -> str:
        """Transcribes speech recognition AudioData into text."""
        pass

class TextToSpeechProvider(ABC):
    @abstractmethod
    def speak(self, text: str):
        """Converts text into speech and plays it out natively."""
        pass

class WakeWordProvider(ABC):
    @abstractmethod
    def listen_and_detect(self, stop_event: Any) -> bool:
        """Listens continuously on the microphone using sounddevice and triggers on keyword."""
        pass
