import os
import sys
import time
import base64
import tempfile
import requests
import sounddevice as sd
import numpy as np
import speech_recognition as sr
from dotenv import load_dotenv
import ctypes

# Load settings
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Wake word config
WAKE_WORD = "friday"

# Global threshold for speech detection (will be calibrated at startup)
ENERGY_THRESHOLD = 0.02
SAMPLE_RATE = 16000

def play_audio(audio_bytes: bytes):
    """Plays audio bytes (MP3) using Windows MCI (Media Control Interface)."""
    if not audio_bytes:
        return
        
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
            
        winmm = ctypes.windll.winmm
        unique_alias = f"friday_audio_{int(time.time() * 1000)}"
        
        # Open
        open_cmd = f'open "{temp_path}" type mpegvideo alias {unique_alias}'
        r = winmm.mciSendStringW(open_cmd, None, 0, 0)
        if r != 0:
            print(f"\nMCI Open Error code: {r}")
            return
            
        # Play
        play_cmd = f'play {unique_alias}'
        r = winmm.mciSendStringW(play_cmd, None, 0, 0)
        if r != 0:
            print(f"\nMCI Play Error code: {r}")
            winmm.mciSendStringW(f'close {unique_alias}', None, 0, 0)
            return

        # Block until audio finishes playing
        status_buf = ctypes.create_unicode_buffer(256)
        while True:
            winmm.mciSendStringW(f'status {unique_alias} mode', status_buf, 255, 0)
            if status_buf.value != "playing":
                break
            time.sleep(0.1)
            
        # Close
        winmm.mciSendStringW(f'close {unique_alias}', None, 0, 0)
    except Exception as e:
        print(f"\n[Error playing audio]: {e}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

def send_to_backend(message: str) -> tuple[str, bytes]:
    """Sends text to FastAPI backend and returns (response_text, audio_bytes)."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": message},
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            text = data.get("text", "")
            audio_b64 = data.get("audio_base64", "")
            audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""
            return text, audio_bytes
        else:
            return f"Error: Server returned status code {response.status_code}", b""
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to Friday's backend server. Is it running?", b""
    except Exception as e:
        return f"Error: {e}", b""

def select_input_device():
    """Scans for input devices and automatically sets the best physical microphone."""
    try:
        devices = sd.query_devices()
        best_device_idx = None
        
        # Pass 1: Look for physical microphone device (Realtek, etc.) and exclude virtual/steam/generic ones
        for idx, dev in enumerate(devices):
            name = dev['name'].lower()
            if dev['max_input_channels'] > 0:
                # Ensure "mic" is not matching the "mic" in "microsoft"
                is_mic = "microphone" in name or "headset" in name or ("mic" in name and "microsoft" not in name)
                if is_mic:
                    if "steam" not in name and "virtual" not in name and "aux" not in name:
                        best_device_idx = idx
                        break
                        
        # Pass 2: Look for any microphone (even if it contains steam/aux/virtual)
        if best_device_idx is None:
            for idx, dev in enumerate(devices):
                name = dev['name'].lower()
                if dev['max_input_channels'] > 0:
                    is_mic = "microphone" in name or "headset" in name or ("mic" in name and "microsoft" not in name)
                    if is_mic:
                        best_device_idx = idx
                        break
                        
        # Pass 3: Take Microsoft Sound Mapper - Input or default input device
        if best_device_idx is None:
            for idx, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    best_device_idx = idx
                    break
                    
        if best_device_idx is not None:
            sd.default.device = (best_device_idx, None)
            print(f"[Audio Device] Selected physical microphone: #{best_device_idx} ({devices[best_device_idx]['name']})")
        else:
            print("[Audio Device] WARNING: No input audio device found!")
    except Exception as e:
        print(f"[Audio Device Error] Error selecting input device: {e}")

def calibrate_mic(duration=2.0):
    """Calibrates energy threshold based on ambient background noise."""
    global ENERGY_THRESHOLD
    print("\nCalibrating microphone for ambient noise... Please remain quiet.")
    chunk_size = 1024
    num_chunks = int(duration * SAMPLE_RATE / chunk_size)
    energies = []
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', blocksize=chunk_size) as stream:
        for _ in range(num_chunks):
            chunk, _ = stream.read(chunk_size)
            rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0
            energies.append(rms)
            
    mean_energy = np.mean(energies)
    # Set threshold to 2.5x the mean ambient noise energy, minimum of 0.015
    ENERGY_THRESHOLD = max(mean_energy * 2.5, 0.015)
    print(f"Calibration done! Ambient energy mean: {mean_energy:.4f}, Set threshold: {ENERGY_THRESHOLD:.4f}\n")

def record_speech_until_silence(silence_duration=0.8, timeout=5.0) -> tuple[bytes, int]:
    """
    Listens to the microphone stream. 
    Returns raw 16-bit PCM bytes when speech ends, or empty bytes on timeout.
    """
    chunk_size = 1024
    sample_width = 2  # 16-bit is 2 bytes
    
    audio_data = []
    recording = False
    silent_chunks = 0
    max_silent_chunks = int(silence_duration * SAMPLE_RATE / chunk_size)
    
    # Store a small amount of pre-speech audio to avoid clipping
    pre_speech_chunks = []
    max_pre_speech = int(0.5 * SAMPLE_RATE / chunk_size) # 0.5s pre-speech buffer
    
    start_time = time.time()
    
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', blocksize=chunk_size) as stream:
            while True:
                chunk, overflowed = stream.read(chunk_size)
                rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0
                
                if not recording:
                    pre_speech_chunks.append(chunk)
                    if len(pre_speech_chunks) > max_pre_speech:
                        pre_speech_chunks.pop(0)
                        
                    if rms > ENERGY_THRESHOLD:
                        print("\n[Listening...]")
                        recording = True
                        audio_data.extend(pre_speech_chunks)
                        silent_chunks = 0
                    elif time.time() - start_time > timeout:
                        # Timeout waiting for speech
                        return b"", sample_width
                else:
                    audio_data.append(chunk)
                    if rms < ENERGY_THRESHOLD:
                        silent_chunks += 1
                        if silent_chunks > max_silent_chunks:
                            print("[Processing...]")
                            break
                    else:
                        silent_chunks = 0
                        
                    # Max recording limit of 15 seconds to prevent memory overflow
                    if len(audio_data) * chunk_size / SAMPLE_RATE > 15.0:
                        print("[Reached max recording length]")
                        break
    except Exception as e:
        print(f"\n[Microphone Error]: {e}")
        return b"", sample_width
        
    if audio_data:
        pcm_data = np.concatenate(audio_data, axis=0)
        return pcm_data.tobytes(), sample_width
        
    return b"", sample_width

def run_assistant():
    recognizer = sr.Recognizer()
    
    print("====================================================")
    print("     FRIDAY VOICE ASSISTANT - CLIENT INITIALIZED    ")
    print("====================================================")
    print(f"Wake word: '{WAKE_WORD.upper()}'")
    print("Connecting to backend at:", BACKEND_URL)
    
    # Test backend connection and cache wake prompt
    wake_prompt_audio = b""
    try:
        r = requests.get(BACKEND_URL, timeout=3)
        if r.status_code == 200:
            print("Status: Connected to Backend successfully!")
            # Cache wake prompt
            print("Caching wake prompt response...")
            wr = requests.post(f"{BACKEND_URL}/wake-prompt", timeout=5)
            if wr.status_code == 200:
                data = wr.json()
                audio_b64 = data.get("audio_base64", "")
                if audio_b64:
                    wake_prompt_audio = base64.b64decode(audio_b64)
                    print("Status: Wake prompt audio cached successfully.")
        else:
            print("Status: Connected, but backend returned status:", r.status_code)
    except Exception as e:
        print(f"WARNING: Could not connect to backend or cache wake prompt: {e}")
        
    select_input_device()
    calibrate_mic()
    print("Friday is online and listening...")
    
    while True:
        try:
            print(".", end="", flush=True)
            # Listen for any audio above threshold
            pcm_bytes, sample_width = record_speech_until_silence(silence_duration=0.8, timeout=5.0)
            
            if not pcm_bytes:
                continue
                
            # Create AudioData object for SpeechRecognition
            audio_data = sr.AudioData(pcm_bytes, SAMPLE_RATE, sample_width)
            
            # Transcribe
            try:
                transcription = recognizer.recognize_google(audio_data)
                transcription = transcription.strip()
            except sr.UnknownValueError:
                # Speech was unintelligible
                continue
            except sr.RequestError as e:
                print(f"\n[STT Request Error]: {e}")
                continue
                
            if not transcription:
                continue
                
            print(f"\nHeard: '{transcription}'")
            transcription_lower = transcription.lower()
            
            # Check for wake word
            if WAKE_WORD in transcription_lower:
                wake_index = transcription_lower.find(WAKE_WORD)
                command = transcription[wake_index + len(WAKE_WORD):].strip()
                
                # Clean up leading punctuation
                if command and command[0] in [",", ".", "!", "?", "-"]:
                    command = command[1:].strip()
                    
                if not command:
                    # Trigger active response
                    print("Friday: Yes?")
                    if wake_prompt_audio:
                        play_audio(wake_prompt_audio)
                    else:
                        reply_text, reply_audio = send_to_backend("Hello Friday")
                        if reply_audio:
                            play_audio(reply_audio)
                        
                    # Immediately listen for command
                    print("Friday is listening for your command...")
                    # We set a shorter timeout (5s) for the follow-up command
                    pcm_bytes, sample_width = record_speech_until_silence(silence_duration=0.8, timeout=5.0)
                    if not pcm_bytes:
                        print("Friday: (No command heard, going back to standby)")
                        continue
                        
                    audio_data = sr.AudioData(pcm_bytes, SAMPLE_RATE, sample_width)
                    try:
                        command = recognizer.recognize_google(audio_data).strip()
                    except Exception:
                        print("Friday: (Could not understand, going back to standby)")
                        continue
                        
                    if not command:
                        print("Friday: (No command heard, going back to standby)")
                        continue
                        
                    print(f"Command: '{command}'")
                
                # Process command
                print(f"Processing command: '{command}'...")
                response_text, response_audio = send_to_backend(command)
                print(f"Friday: {response_text}")
                
                if response_audio:
                    play_audio(response_audio)
                    
        except KeyboardInterrupt:
            print("\nShutting down Friday Client. Goodbye!")
            break
        except Exception as e:
            print(f"\nError in client loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_assistant()
