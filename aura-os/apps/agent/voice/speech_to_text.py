import speech_recognition as sr
from typing import Any
from voice.base import SpeechToTextProvider

class GoogleSTTProvider(SpeechToTextProvider):
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def transcribe(self, audio_data: Any) -> str:
        """Transcribes an AudioData object using Google's public speech recognition API."""
        if not audio_data:
            return ""
            
        try:
            text = self.recognizer.recognize_google(audio_data)
            print(f"[SpeechToText] Transcribed: '{text}'")
            return text.strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[SpeechToText Error] Google API request failure: {e}")
            return ""
        except Exception as e:
            print(f"[SpeechToText Error] Transcription exception: {e}")
            return ""
