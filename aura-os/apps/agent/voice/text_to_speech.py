import os
import time
import ctypes
from gtts import gTTS
from voice.base import TextToSpeechProvider

class gTTSProvider(TextToSpeechProvider):
    def __init__(self, temp_folder: str = "temp_audio"):
        self.temp_folder = temp_folder
        os.makedirs(self.temp_folder, exist_ok=True)

    def speak(self, text: str):
        """Generates an MP3 using gTTS and plays it via Windows MCI."""
        if not text.strip():
            return
            
        print(f"[TextToSpeech] Speaking: \"{text}\"")
        
        # Save output path
        filename = f"tts_{int(time.time() * 1000)}.mp3"
        filepath = os.path.join(self.temp_folder, filename)
        abs_path = os.path.abspath(filepath)
        
        try:
            # Generate speech
            tts = gTTS(text=text, lang="en")
            tts.save(abs_path)
            
            # Play using Windows MCI (blocks until done playing using 'wait')
            alias = f"aura_audio_{int(time.time() * 1000)}"
            
            # 1. Open audio file
            ctypes.windll.winmm.mciSendStringW(
                f'open "{abs_path}" type mpegvideo alias {alias}', 
                None, 0, 0
            )
            
            # 2. Play (blocking)
            ctypes.windll.winmm.mciSendStringW(
                f'play {alias} wait', 
                None, 0, 0
            )
            
            # 3. Close
            ctypes.windll.winmm.mciSendStringW(
                f'close {alias}', 
                None, 0, 0
            )
            
        except Exception as e:
            print(f"[TextToSpeech Error] Playback failed: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass
