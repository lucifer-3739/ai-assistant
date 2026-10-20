import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Initialize system path for imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import AURA core modules
from config.settings import settings
from database.schema import init_db
from database.connection import get_connection
from core.ai_provider import GeminiProvider
from core.orchestrator import Orchestrator
from security.permissions import resolve_permission, get_pending_request
import tools.filesystem
import tools.system
import tools.terminal
import tools.browser
import tools.system_control
import tools.organizer
import tools.memory
import tools.vision
import tools.gui
import tools.device_control
import tools.window_manager
from core.memory_manager import MemoryManager

# Initialize Database on startup
init_db()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] Client connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WebSocket] Client disconnected. Total active connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

# Define async broadcast callback for the Orchestrator
async def websocket_broadcast_callback(task_id: str, details: Dict[str, Any]):
    payload = {
        "event": "task_update",
        "task_id": task_id,
        "data": details
    }
    await manager.broadcast(json.dumps(payload))

# Import Voice Pipeline
from voice.pipeline import VoicePipeline

# Initialize AI Brain and Orchestrator
ai_provider = GeminiProvider()
orchestrator = Orchestrator(
    ai_provider=ai_provider,
    broadcast_callback=websocket_broadcast_callback
)

# Initialize Voice Pipeline
voice_pipeline = VoicePipeline(orchestrator=orchestrator)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan manager to coordinate background processes."""
    await voice_pipeline.start()
    yield
    voice_pipeline.stop()

app = FastAPI(
    title="AURA OS Agent API Backend",
    version=settings.VERSION,
    description="The local execution and orchestration backend for AURA OS",
    lifespan=lifespan
)

# Enable CORS for Tauri/Electron desktop shell integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic API Models ---

class CommandRequest(BaseModel):
    command: str

class PermissionResponse(BaseModel):
    task_id: str
    approved: bool

# --- REST API Endpoints ---

@app.get("/")
def get_status():
    """Returns general AURA OS operational status."""
    return {
        "status": "AURA OS ONLINE",
        "version": settings.VERSION,
        "model": settings.GEMINI_MODEL,
        "database": settings.SQLITE_DB_PATH
    }

@app.post("/api/command")
async def receive_command(request: CommandRequest):
    """Submits a natural language instruction to AURA OS."""
    command = request.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Empty command.")
        
    try:
        # Create task in database
        task_id = orchestrator.create_task(command)
        
        # Launch orchestrator loop in background so API responds immediately
        asyncio.create_task(orchestrator.execute_task(task_id))
        
        return {
            "task_id": task_id,
            "status": "PLANNING"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voice/status")
def get_voice_status():
    """Returns the current state and running status of the voice pipeline."""
    return {
        "running": voice_pipeline.is_running,
        "state": voice_pipeline.current_state
    }

@app.post("/api/voice/toggle")
async def toggle_voice():
    """Toggles continuous wake-word voice listening."""
    if voice_pipeline.is_running:
        voice_pipeline.stop()
        return {"running": False, "state": "DISABLED"}
    else:
        await voice_pipeline.start()
        return {"running": True, "state": "IDLE"}

@app.post("/api/voice/trigger")
async def trigger_voice():
    """Manually triggers a single voice listening and execution cycle."""
    asyncio.create_task(voice_pipeline.trigger_once())
    return {"status": "triggered"}

@app.post("/api/voice/speak")
async def speak_text(payload: Dict[str, str] = Body(...)):
    """Synthesizes and speaks text out loud via TTS."""
    text = payload.get("text", "")
    if text:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, voice_pipeline.tts.speak, text)
    return {"status": "ok"}

# --- Context Memory Endpoints ---

@app.get("/api/memory")
def get_memories():
    """Returns all stored user preferences and context memories."""
    return MemoryManager.list_all()

@app.post("/api/memory")
def save_memory(payload: Dict[str, Any] = Body(...)):
    """Stores or updates a remembered preference."""
    key = payload.get("key")
    value = payload.get("value")
    category = payload.get("category", "preference")
    if not key or not value:
        raise HTTPException(status_code=400, detail="Key and value are required.")
    MemoryManager.set(key, value, category)
    return {"status": "saved", "key": key, "value": value}

@app.delete("/api/memory/{key}")
def remove_memory(key: str):
    """Deletes a remembered preference."""
    deleted = MemoryManager.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory key not found.")
    return {"status": "deleted", "key": key}

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    """Returns the current state and steps of a specific task."""
    details = orchestrator.get_task_details(task_id)
    if not details:
        raise HTTPException(status_code=404, detail="Task not found.")
    return details

@app.get("/api/tasks")
def list_tasks():
    """Lists recent tasks executed in this session."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_request, state, created_at FROM tasks ORDER BY created_at DESC LIMIT 50")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query tasks: {e}")

@app.post("/api/permissions/respond")
def respond_permission(request: PermissionResponse):
    """Submits the user's decision for a security checkpoint."""
    resolved = resolve_permission(request.task_id, request.approved)
    if not resolved:
        raise HTTPException(status_code=404, detail="No pending permission request found for this task ID.")
    return {"status": "success", "message": "Permission resolved."}

@app.get("/api/permissions/pending/{task_id}")
def check_pending_permission(task_id: str):
    """Returns details of a pending permission check for the task, if any."""
    req = get_pending_request(task_id)
    if not req:
        return {"pending": False}
    return {"pending": True, "details": req}

@app.get("/api/tools")
def list_tools():
    """Lists all registered tools and their schemas."""
    from tools.base import registry
    return [
        {
            "name": t.name,
            "description": t.description,
            "risk_level": t.risk_level,
            "required_permission": t.required_permission,
            "parameters": t.parameters
        } for t in registry.list_tools()
    ]

@app.get("/api/audit")
def get_audit_log():
    """Returns the security audit log from the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query audit logs: {e}")

# --- WebSockets Gateway ---

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket route for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from client for now, just keep connection open
            data = await websocket.receive_text()
            # Echo or ignore
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket Error] Exception: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
