import os
import io
import requests
from gtts import gTTS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TTSService:
    def __init__(self):
        self.provider = os.getenv("TTS_PROVIDER", "gtts").lower()
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Default Rachel voice

    def synthesize(self, text: str) -> bytes:
        """
        Synthesizes text to speech.
        Returns audio bytes (MP3 format).
        """
        if not text.strip():
            return b""

        if self.provider == "elevenlabs" and self.elevenlabs_key:
            return self._synthesize_elevenlabs(text)
        elif self.provider == "openai" and self.openai_key:
            return self._synthesize_openai(text)
        else:
            # Default fallback to gTTS
            return self._synthesize_gtts(text)

    def _synthesize_gtts(self, text: str) -> bytes:
        try:
            fp = io.BytesIO()
            tts = gTTS(text=text, lang='en')
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.read()
        except Exception as e:
            print(f"gTTS failed: {e}. Returning empty audio.")
            return b""

    def _synthesize_openai(self, text: str) -> bytes:
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "tts-1",
                "input": text,
                "voice": "alloy"
            }
            response = requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers=headers,
                json=payload
            )
            if response.status_code == 200:
                return response.content
            else:
                print(f"OpenAI TTS error: {response.text}. Falling back to gTTS.")
                return self._synthesize_gtts(text)
        except Exception as e:
            print(f"OpenAI TTS exception: {e}. Falling back to gTTS.")
            return self._synthesize_gtts(text)

    def _synthesize_elevenlabs(self, text: str) -> bytes:
        try:
            headers = {
                "xi-api-key": self.elevenlabs_key,
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.content
            else:
                print(f"ElevenLabs TTS error: {response.text}. Falling back to gTTS.")
                return self._synthesize_gtts(text)
        except Exception as e:
            print(f"ElevenLabs TTS exception: {e}. Falling back to gTTS.")
            return self._synthesize_gtts(text)
