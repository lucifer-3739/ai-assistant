import os
import time
import json
import asyncio
import sounddevice as sd
import numpy as np
import speech_recognition as sr
from typing import Optional
from voice.speech_to_text import GoogleSTTProvider
from voice.text_to_speech import gTTSProvider
from voice.wake_word import LocalWakeWordProvider, SAMPLE_RATE, auto_select_input_device
from core.orchestrator import Orchestrator
from database.connection import get_connection

class VoicePipeline:
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.stt = GoogleSTTProvider()
        self.tts = gTTSProvider()
        self.wake_word = LocalWakeWordProvider(keyword="nova")
        self.stop_event = asyncio.Event()
        self.active_task_id: Optional[str] = None
        self.is_running = False
        self.current_state = "IDLE"

    async def _broadcast_voice_state(self, state: str, detail: str = ""):
        self.current_state = state
        payload = {
            "event": "voice_state",
            "state": state,
            "detail": detail
        }
        try:
            from main import manager
            await manager.broadcast(json.dumps(payload))
        except Exception:
            pass

    async def start(self):
        """Starts the voice pipeline in an asynchronous background loop."""
        if self.is_running:
            return
        self.is_running = True
        self.stop_event.clear()
        asyncio.create_task(self._loop())
        await self._broadcast_voice_state("IDLE", "Listening for 'NOVA' wake word")
        print("[Voice Pipeline] Continuous background listener active.")

    def stop(self):
        """Cancels background tasks."""
        self.is_running = False
        self.stop_event.set()
        asyncio.create_task(self._broadcast_voice_state("DISABLED", "Voice listener paused"))
        print("[Voice Pipeline] Stopping background listener...")

    async def trigger_once(self) -> dict:
        """Manually triggers one voice command turn (e.g. from UI Arc Reactor click)."""
        loop = asyncio.get_running_loop()
        return await self._record_and_execute_fallback(loop)

    async def _execute_direct_command(self, command: str, loop) -> dict:
        """Directly plans and executes a separated voice command without extra latency."""
        print(f"[Voice Pipeline] Executing continuous voice command: '{command}'")
        voice_task_id = self.orchestrator.create_task(command)
        self.active_task_id = voice_task_id

        # Update state to UNDERSTANDING -> EXECUTING
        await self._broadcast_voice_state("UNDERSTANDING", f"UNDERSTANDING: '{command.upper()}'")
        self.orchestrator._update_task_state(voice_task_id, "UNDERSTANDING")
        await self.orchestrator.broadcast(voice_task_id)

        # Check for immediate cancellation command
        cmd_lower = command.lower().strip()
        if cmd_lower in ("stop", "cancel", "abort", "stop execution"):
            self.orchestrator._update_task_state(voice_task_id, "CANCELLED")
            await self.orchestrator.broadcast(voice_task_id)
            await self._broadcast_voice_state("IDLE", "Task aborted")
            await loop.run_in_executor(None, self.tts.speak, "Aborted.")
            return {"status": "cancelled", "command": command}

        # Trigger Execution Plan
        await self._broadcast_voice_state("EXECUTING", f"EXECUTING: {command}")
        await self.orchestrator.execute_task(voice_task_id)

        # Fast crisp vocal summary
        task_details = self.orchestrator.get_task_details(voice_task_id)
        speech_text = "Done."
        if task_details:
            state = task_details["state"]
            if state == "COMPLETED":
                speech_text = f"Done. {command} completed."
            elif state == "FAILED":
                speech_text = "Task failed. Check logs."
            elif state == "CANCELLED":
                speech_text = "Cancelled."

        # Vocalize response
        await self._broadcast_voice_state("SPEAKING", speech_text)
        await loop.run_in_executor(None, self.tts.speak, speech_text)
        await self._broadcast_voice_state("IDLE", "SAY \"NOVA\" TO ENGAGE")
        return {"status": "success", "command": command, "task_id": voice_task_id}

    async def _record_and_execute_fallback(self, loop) -> dict:
        """Fallback when only wake word was spoken without immediate command."""
        print("[Voice Pipeline] Listening for instruction...")
        voice_task_id = self.orchestrator.create_task("Hearing speech input...")
        self.active_task_id = voice_task_id
        
        await self._broadcast_voice_state("LISTENING", "LISTENING... SPEAK NOW")
        self.orchestrator._update_task_state(voice_task_id, "LISTENING")
        await self.orchestrator.broadcast(voice_task_id)

        def record_speech_sounddevice():
            auto_select_input_device()
            chunk_size = 1024
            sample_width = 2
            audio_data = []
            recording = False
            silent_chunks = 0
            max_silent_chunks = int(0.75 * SAMPLE_RATE / chunk_size)
            pre_speech_chunks = []
            max_pre_speech = int(0.5 * SAMPLE_RATE / chunk_size)
            start_time = time.time()
            
            try:
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16', blocksize=chunk_size) as stream:
                    while True:
                        chunk, _ = stream.read(chunk_size)
                        rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0
                        
                        if not recording:
                            pre_speech_chunks.append(chunk)
                            if len(pre_speech_chunks) > max_pre_speech:
                                pre_speech_chunks.pop(0)
                            if rms > self.wake_word.energy_threshold:
                                recording = True
                                audio_data.extend(pre_speech_chunks)
                                silent_chunks = 0
                            elif time.time() - start_time > 4.0:
                                break
                        else:
                            audio_data.append(chunk)
                            if rms < self.wake_word.energy_threshold:
                                silent_chunks += 1
                                if silent_chunks > max_silent_chunks:
                                    break
                            else:
                                silent_chunks = 0
                            if len(audio_data) * chunk_size / SAMPLE_RATE > 8.0:
                                break
            except Exception as e:
                print(f"[Voice Pipeline Audio Error]: {e}")
                return None
                
            if audio_data:
                pcm = np.concatenate(audio_data, axis=0)
                return sr.AudioData(pcm.tobytes(), SAMPLE_RATE, sample_width)
            return None

        audio_data_obj = await loop.run_in_executor(None, record_speech_sounddevice)
        
        if not audio_data_obj:
            self.orchestrator._update_task_state(voice_task_id, "FAILED")
            await self.orchestrator.broadcast(voice_task_id)
            await self._broadcast_voice_state("IDLE", "SAY \"NOVA\" TO ENGAGE")
            return {"status": "error", "message": "No audio captured"}

        # Transcribe Audio
        await self._broadcast_voice_state("UNDERSTANDING", "TRANSCRIBING...")
        self.orchestrator._update_task_state(voice_task_id, "UNDERSTANDING")
        await self.orchestrator.broadcast(voice_task_id)

        command = await loop.run_in_executor(None, self.stt.transcribe, audio_data_obj)

        if not command.strip():
            self.orchestrator._update_task_state(voice_task_id, "FAILED")
            await self.orchestrator.broadcast(voice_task_id)
            await self._broadcast_voice_state("IDLE", "SAY \"NOVA\" TO ENGAGE")
            return {"status": "error", "message": "Unintelligible speech"}

        # Update task query in DB
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE tasks SET user_request = ? WHERE id = ?", (command, voice_task_id))
        except Exception as e:
            print(f"[Voice Pipeline DB Error] Failed to update query text: {e}")

        # Check for immediate cancellation
        cmd_lower = command.lower().strip()
        if cmd_lower in ("stop", "cancel", "abort", "stop execution"):
            self.orchestrator._update_task_state(voice_task_id, "CANCELLED")
            await self.orchestrator.broadcast(voice_task_id)
            await self._broadcast_voice_state("IDLE", "SAY \"NOVA\" TO ENGAGE")
            await loop.run_in_executor(None, self.tts.speak, "Aborted.")
            return {"status": "cancelled", "command": command}

        # Trigger Execution Plan
        await self._broadcast_voice_state("EXECUTING", f"EXECUTING: {command}")
        await self.orchestrator.execute_task(voice_task_id)
        
        # Vocal summary feedback
        task_details = self.orchestrator.get_task_details(voice_task_id)
        speech_text = "Done."
        if task_details:
            state = task_details["state"]
            if state == "COMPLETED":
                speech_text = f"Done. {command} completed."
            elif state == "FAILED":
                speech_text = "Task failed."
            elif state == "CANCELLED":
                speech_text = "Cancelled."
                
        # Vocalize response
        await self._broadcast_voice_state("SPEAKING", speech_text)
        await loop.run_in_executor(None, self.tts.speak, speech_text)
        await self._broadcast_voice_state("IDLE", "SAY \"NOVA\" TO ENGAGE")
        return {"status": "success", "command": command, "task_id": voice_task_id}

    async def _loop(self):
        loop = asyncio.get_running_loop()

        while self.is_running:
            # 1. Continuous Listen for Wake Word & Separated Command
            await self._broadcast_voice_state("IDLE", "SAY \"NOVA\" TO ENGAGE")
            print("[Voice Pipeline] Continuous listener active for 'NOVA' + commands...")
            
            class StopToken:
                def __init__(self, async_event):
                    self.async_event = async_event
                def is_set(self):
                    return self.async_event.is_set()

            stop_token = StopToken(self.stop_event)
            
            triggered, extracted_command = await loop.run_in_executor(
                None, 
                self.wake_word.listen_and_detect_command, 
                stop_token
            )
            
            if not triggered or not self.is_running:
                break
                
            print(f"[Voice Pipeline] Triggered! Separated task command: '{extracted_command}'")
            
            # If the user spoke the command in the same breath (e.g. "Nova open notepad")
            if extracted_command.strip():
                await self._execute_direct_command(extracted_command.strip(), loop)
            else:
                # If the user only said "Nova" and stopped, listen immediately for follow-up
                await self._record_and_execute_fallback(loop)
                
        print("[Voice Pipeline] Background voice loop exited.")
