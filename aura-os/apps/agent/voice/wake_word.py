import time
import re
import sounddevice as sd
import numpy as np
import speech_recognition as sr
from typing import Any, Optional, Tuple
from voice.base import WakeWordProvider

SAMPLE_RATE = 16000

# Regex patterns to detect and cleanly strip wake words from spoken speech
WAKE_PATTERNS = [
    r"^(?:hey\s+|ok\s+|okay\s+|hello\s+|hi\s+)?(?:n\.?o\.?v\.?a|nova|no\s+va|friday|aura)\b[\s,:\-]*(?:please\s+)?",
    r"\b(?:n\.?o\.?v\.?a|nova|no\s+va|friday|aura)\b[\s,:\-]*(?:please\s+)?"
]

def extract_command_after_wake_word(text: str) -> Tuple[bool, str]:
    """
    Detects if a wake word is present in the transcribed text, separates it,
    and returns (is_wake_word_detected, separated_task_command).
    
    Examples:
      - "Nova open notepad" -> (True, "open notepad")
      - "Hey Nova, can you check my battery" -> (True, "check my battery")
      - "Nova" -> (True, "")
      - "Hello world" -> (False, "")
    """
    if not text:
        return False, ""
        
    cleaned = text.strip().lower()
    
    for pattern in WAKE_PATTERNS:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            start_idx = match.start()
            end_idx = match.end()
            
            # If the wake word was at or near the beginning (first few words)
            if start_idx <= 12:
                remainder = cleaned[end_idx:].strip()
            else:
                # If wake word was placed in the middle or end
                remainder = (cleaned[:start_idx] + " " + cleaned[end_idx:]).strip()
                
            # Clean up polite prefixes / conversational fillers
            remainder = re.sub(
                r"^(?:please\s+|can\s+you\s+|could\s+you\s+|would\s+you\s+|tell\s+me\s+)",
                "",
                remainder,
                flags=re.IGNORECASE
            ).strip()
            
            # Remove trailing/leading punctuation
            remainder = remainder.strip(" ,.-:;!?")
            return True, remainder
            
    return False, ""

def auto_select_input_device() -> Optional[int]:
    """Scans system audio input devices and binds the best physical microphone."""
    try:
        devices = sd.query_devices()
        best_device_idx = None
        
        # Pass 1: Look for physical microphone (Realtek, Microphone Array, etc.) and exclude Steam/virtual
        for idx, dev in enumerate(devices):
            name = dev['name'].lower()
            if dev['max_input_channels'] > 0:
                if any(k in name for k in ['realtek', 'microphone array', 'built-in', 'mic']):
                    if 'steam' not in name and 'mapper' not in name:
                        best_device_idx = idx
                        break
                        
        # Pass 2: Any non-steam input device
        if best_device_idx is None:
            for idx, dev in enumerate(devices):
                if dev['max_input_channels'] > 0 and 'steam' not in dev['name'].lower() and 'mapper' not in dev['name'].lower():
                    best_device_idx = idx
                    break

        if best_device_idx is not None:
            sd.default.device = (best_device_idx, None)
            print(f"[Audio Device] Bound physical microphone: #{best_device_idx} ({devices[best_device_idx]['name']})")
            return best_device_idx
        else:
            print("[Audio Device Warning] Using default system input device.")
    except Exception as e:
        print(f"[Audio Device Error] Failed to select device: {e}")
    return None

class LocalWakeWordProvider(WakeWordProvider):
    def __init__(self, keyword: str = "nova"):
        self.keyword = keyword.lower().strip()
        self.recognizer = sr.Recognizer()
        self.energy_threshold = 0.015
        self.calibrated = False

    def calibrate(self, duration=1.0):
        """Calibrates energy threshold based on ambient background noise."""
        auto_select_input_device()
        print("\n[WakeWord] Calibrating microphone for ambient noise... Please remain quiet.")
        chunk_size = 1024
        num_chunks = int(duration * SAMPLE_RATE / chunk_size)
        energies = []
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', blocksize=chunk_size) as stream:
                for _ in range(num_chunks):
                    chunk, _ = stream.read(chunk_size)
                    rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0
                    energies.append(rms)
            mean_energy = np.mean(energies) if energies else 0.005
            self.energy_threshold = max(mean_energy * 2.2, 0.012)
            self.calibrated = True
            print(f"[WakeWord] Ambient calibration complete! Threshold set to: {self.energy_threshold:.4f}")
        except Exception as e:
            print(f"[WakeWord Calibration Warning] Failed: {e}. Using default threshold.")
            self.energy_threshold = 0.015

    def listen_and_detect_command(self, stop_event: Any) -> Tuple[bool, str]:
        """
        Listens continuously on the microphone. When speech is heard, transcribes it,
        detects the wake word, separates the command, and returns (triggered, command).
        """
        if not self.calibrated:
            self.calibrate()

        chunk_size = 1024
        sample_width = 2
        
        while not stop_event.is_set():
            audio_data = []
            recording = False
            silent_chunks = 0
            max_silent_chunks = int(0.75 * SAMPLE_RATE / chunk_size)
            pre_speech_chunks = []
            max_pre_speech = int(0.5 * SAMPLE_RATE / chunk_size)
            start_time = time.time()
            
            try:
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', blocksize=chunk_size) as stream:
                    while not stop_event.is_set():
                        chunk, _ = stream.read(chunk_size)
                        rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0
                        
                        if not recording:
                            pre_speech_chunks.append(chunk)
                            if len(pre_speech_chunks) > max_pre_speech:
                                pre_speech_chunks.pop(0)
                            if rms > self.energy_threshold:
                                recording = True
                                audio_data.extend(pre_speech_chunks)
                                silent_chunks = 0
                            elif time.time() - start_time > 3.0:
                                break
                        else:
                            audio_data.append(chunk)
                            if rms < self.energy_threshold:
                                silent_chunks += 1
                                if silent_chunks > max_silent_chunks:
                                    break
                            else:
                                silent_chunks = 0
                            # Allow natural sentence length (up to 7 seconds of continuous speech)
                            if len(audio_data) * chunk_size / SAMPLE_RATE > 7.0:
                                break
            except Exception as e:
                print(f"[WakeWord Stream Error] {e}")
                time.sleep(1)
                continue

            if audio_data:
                pcm_data = np.concatenate(audio_data, axis=0)
                sr_audio = sr.AudioData(pcm_data.tobytes(), SAMPLE_RATE, sample_width)
                try:
                    text = self.recognizer.recognize_google(sr_audio).lower()
                    print(f"[WakeWord Detected Audio] Spoken: \"{text}\"")
                    triggered, extracted_command = extract_command_after_wake_word(text)
                    if triggered:
                        print(f"[WakeWord Triggered] Command separated: \"{extracted_command}\"")
                        return True, extracted_command
                except Exception:
                    pass

        return False, ""

    def listen_and_detect(self, stop_event: Any) -> bool:
        """Backwards-compatible boolean detector."""
        triggered, _ = self.listen_and_detect_command(stop_event)
        return triggered
