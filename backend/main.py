# Friday Voice Assistant Backend
import os
import base64
import re
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

from tts_service import TTSService
from memory_manager import MemoryManager
import tools

# Map tool functions for dynamic execution
tool_mapping = {
    "open_website": tools.open_website,
    "search_google": tools.search_google,
    "open_application": tools.open_application,
    "close_application": tools.close_application,
    "list_directory": tools.list_directory,
    "read_file": tools.read_file,
    "write_file": tools.write_file,
    "organize_folder": tools.organize_folder,
    "capture_screen": tools.capture_screen,
    "capture_camera": tools.capture_camera
}
tools_list = list(tool_mapping.values())

# Load configuration
load_dotenv()

app = FastAPI(title="Friday Voice Assistant Backend")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize TTS
tts_service = TTSService()

# Initialize Gemini Client
gemini_key = os.getenv("GEMINI_API_KEY")
gemini_client = None
memory_manager = None

if gemini_key and gemini_key != "your_gemini_api_key_here":
    try:
        gemini_client = genai.Client(api_key=gemini_key)
        print("Gemini client successfully initialized.")
        # Initialize memory manager with the gemini client
        memory_manager = MemoryManager(gemini_client=gemini_client)
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
else:
    print("WARNING: GEMINI_API_KEY is not set. Using mock/fallback responses.")
    # Initialize memory manager with no gemini client (will fall back to keyword search)
    memory_manager = MemoryManager(gemini_client=None)

# In-memory session store for chat history
# Format: { session_id: [{"role": "user"|"model", "text": "..."}] }
session_histories = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    system_instruction: str = (
        "You are Friday, a helpful, Jarvis-style voice assistant. "
        "Keep your answers brief, conversational, and direct, as they will be spoken aloud. "
        "Avoid long paragraphs, markdown lists, or symbols like asterisks that sound awkward when read.\n\n"
        "Memory Directive:\n"
        "If the user shares personal details (e.g. name, preferences, favorite things) or explicitly asks you to remember something, "
        "append the tag '[MEMORIZE: fact]' in your response. For example: "
        "'I will remember that your favorite editor is VS Code. [MEMORIZE: User\'s favorite editor is VS Code]'. "
        "Ensure the fact in the tag is written in third person (e.g. 'User\'s favorite editor is VS Code' instead of 'My favorite editor is VS Code')."
    )

class ChatResponse(BaseModel):
    text: str
    audio_base64: str = ""

@app.get("/")
def read_root():
    return {
        "status": "online",
        "assistant_name": "Friday",
        "tts_provider": tts_service.provider,
        "gemini_configured": gemini_client is not None,
        "memories_count": len(memory_manager.memories) if memory_manager else 0
    }

@app.post("/wake-prompt", response_model=ChatResponse)
async def wake_prompt_endpoint():
    response_text = "Yes?"
    audio_bytes = b""
    try:
        audio_bytes = tts_service.synthesize(response_text)
    except Exception as e:
        print(f"Failed to generate wake prompt TTS: {e}")
        
    audio_base64 = ""
    if audio_bytes:
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
    return ChatResponse(
        text=response_text,
        audio_base64=audio_base64
    )

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    session_id = request.session_id
    if not user_message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    # 1. Retrieve relevant memories for context
    relevant_memories = []
    if memory_manager:
        try:
            relevant_memories = memory_manager.retrieve_memories(user_message, top_k=3)
        except Exception as e:
            print(f"Error retrieving memories: {e}")

    # Build system instruction injecting memories
    system_instruction = request.system_instruction
    if relevant_memories:
        memory_context = "\n\nYou remember the following facts about the user:\n" + "\n".join([f"- {m}" for m in relevant_memories])
        system_instruction += memory_context

    response_text = ""

    if gemini_client:
        try:
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            
            # Retrieve or initialize session history
            if session_id not in session_histories:
                session_histories[session_id] = []
            
            history = session_histories[session_id]
            
            # Map history to Gemini API types
            gemini_history = []
            for msg in history:
                # Map role 'model' to 'model' and 'user' to 'user'
                role = "model" if msg["role"] == "model" else "user"
                gemini_history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["text"])]
                    )
                )
            
            # Create a chat session with the history and registered tools
            chat = gemini_client.chats.create(
                model=gemini_model,
                history=gemini_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools_list
                )
            )
            
            # Send the new message to get a response
            response = chat.send_message(user_message)
            
            # Handle tool execution loop if the model wants to call functions
            while response.function_calls:
                for call in response.function_calls:
                    func_name = call.name
                    func_args = call.args
                    
                    print(f"[Tool Call] Model requested: {func_name} with args: {func_args}")
                    
                    # Convert arguments
                    kwargs = {}
                    if func_args:
                        for k, v in func_args.items():
                            kwargs[k] = v
                            
                    # Execute tool
                    if func_name in tool_mapping:
                        try:
                            result = tool_mapping[func_name](**kwargs)
                        except Exception as e:
                            result = f"Error executing tool {func_name}: {e}"
                    else:
                        result = f"Error: Tool '{func_name}' is not registered locally."
                        
                    print(f"[Tool Output] Result: {result}")
                    
                    # Send the tool output back to the model to continue conversation
                    parts = [
                        types.Part.from_function_response(
                            name=func_name,
                            response={"result": result}
                        )
                    ]
                    
                    # If this was a successful vision capture tool call, inject the image as a Part
                    temp_image_file = None
                    mime_type = None
                    if "successfully" in result.lower():
                        if func_name == "capture_screen" and os.path.exists("screenshot.png"):
                            temp_image_file = "screenshot.png"
                            mime_type = "image/png"
                        elif func_name == "capture_camera" and os.path.exists("camera.jpg"):
                            temp_image_file = "camera.jpg"
                            mime_type = "image/jpeg"
                            
                    if temp_image_file and mime_type:
                        try:
                            with open(temp_image_file, "rb") as img_file:
                                img_bytes = img_file.read()
                            parts.append(
                                types.Part.from_bytes(
                                    data=img_bytes,
                                    mime_type=mime_type
                                )
                            )
                            print(f"[Vision Integration] Injected image '{temp_image_file}' as Part.")
                        except Exception as e:
                            print(f"[Vision Error] Failed to read image bytes: {e}")
                            
                    # Send parts to Gemini
                    response = chat.send_message(parts)
                    
                    # Clean up the temporary image file from disk to protect privacy and save space
                    if temp_image_file and os.path.exists(temp_image_file):
                        try:
                            os.remove(temp_image_file)
                            print(f"[Vision Integration] Temporary file '{temp_image_file}' deleted.")
                        except Exception as e:
                            print(f"[Vision Warning] Failed to delete temporary file: {e}")
            
            response_text = response.text
            
            # Update our session history with the new turn
            session_histories[session_id].append({"role": "user", "text": user_message})
            session_histories[session_id].append({"role": "model", "text": response_text})
            
            # Cap history length to last 20 messages to prevent context bloat
            if len(session_histories[session_id]) > 20:
                session_histories[session_id] = session_histories[session_id][-20:]
                
        except APIError as ae:
            print(f"Gemini API Error: {ae}")
            response_text = f"Sorry, I encountered a Gemini API error. Details: {ae.message}"
        except Exception as e:
            print(f"Gemini unexpected exception: {e}")
            response_text = "Sorry, I had trouble processing your request with the AI brain."
    else:
        # Mock responses for testing without API keys
        user_lower = user_message.lower()
        if "hello" in user_lower or "hi" in user_lower:
            response_text = "Hello! I am Friday, your personal voice assistant. Please configure my API key to unlock my full potential."
        elif "your name" in user_lower:
            response_text = "My name is Friday."
        else:
            response_text = f"You said: '{user_message}'. Please configure my Gemini API key to allow me to respond intelligently."

    # 2. Parse and save memory tags if found
    if memory_manager and response_text:
        try:
            # Check for [MEMORIZE: fact]
            memorize_matches = re.findall(r'\[MEMORIZE:\s*(.*?)\]', response_text)
            for fact in memorize_matches:
                memory_manager.add_memory(fact)
            
            # Strip tags from the response text so the user never hears or sees them
            response_text = re.sub(r'\[MEMORIZE:\s*(.*?)\]', '', response_text).strip()
        except Exception as e:
            print(f"Error parsing memory tags: {e}")

    # Synthesize response text to audio bytes
    audio_bytes = b""
    if response_text:
        try:
            audio_bytes = tts_service.synthesize(response_text)
        except Exception as e:
            print(f"Failed to generate TTS: {e}")

    # Encode audio in base64 to send in JSON response
    audio_base64 = ""
    if audio_bytes:
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    return ChatResponse(
        text=response_text,
        audio_base64=audio_base64
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=True)
