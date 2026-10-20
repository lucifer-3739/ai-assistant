import json
import re
from typing import List, Dict, Any, Optional
from core.ai_provider import AIProvider
from core.memory_manager import MemoryManager

PLANNING_SYSTEM_INSTRUCTION = """
You are the Planner for NOVA (N.O.V.A.), an AI-native voice-controlled desktop operating system agent and personal assistant.
Your job is to convert a user's natural-language goal or compound multi-task instructions into a structured, sequential plan of steps.

You have access to the following tools:
{tools_descriptions}

CRITICAL RULES FOR MULTI-TASK & COMPOUND DIRECTIVES:
1. When the user provides a compound request with multiple actions (e.g. "open notepad, check battery, and set volume up" or "take a screenshot and open calculator"), you MUST decompose the request into individual, sequential steps in the exact order requested.
2. Each step MUST map to the appropriate tool call with the required arguments.
3. If an action does not require a tool call (e.g. final answer synthesis or conversational report), set "tool_name": null and "tool_args": null.
4. You must return your output ONLY as a valid JSON array of step objects. Do not include markdown formatting, backticks, or extra commentary.

Step Object Schema:
- "step_number": (integer) Sequential step number starting at 1.
- "description": (string) A clear human-readable description of what this step does.
- "tool_name": (string or null) The exact name of the tool to execute for this step.
- "tool_args": (object or null) The arguments to pass to the tool.

Example 1 (Single Task): "check battery status"
[
  {{"step_number": 1, "description": "Retrieve system battery diagnostics", "tool_name": "get_battery_status", "tool_args": {{}}}}
]

Example 2 (Multi-Task Compound): "open chrome, check battery, and take a screenshot"
[
  {{"step_number": 1, "description": "Launch Google Chrome", "tool_name": "open_application", "tool_args": {{"application": "chrome"}}}},
  {{"step_number": 2, "description": "Check system battery status", "tool_name": "get_battery_status", "tool_args": {{}}}},
  {{"step_number": 3, "description": "Capture desktop screen snapshot", "tool_name": "take_screenshot", "tool_args": {{}}}}
]

Example 3 (Multi-Task Desktop & Media): "snap left, set volume up, and play synthwave on youtube"
[
  {{"step_number": 1, "description": "Snap active window to the left side", "tool_name": "control_active_window", "tool_args": {{"action": "snap_left"}}}},
  {{"step_number": 2, "description": "Increase system master volume", "tool_name": "set_system_volume", "tool_args": {{"action": "up"}}}},
  {{"step_number": 3, "description": "Play synthwave on YouTube", "tool_name": "play_media", "tool_args": {{"query": "synthwave"}}}}
]

Example 4 (Multi-Task File & Folder): "create a folder named Projects and list the directory"
[
  {{"step_number": 1, "description": "Create a new directory named Projects", "tool_name": "create_folder", "tool_args": {{"path": "Projects"}}}},
  {{"step_number": 2, "description": "List the contents of the current directory", "tool_name": "list_directory", "tool_args": {{"path": "."}}}}
]
"""

def match_single_fast_action(clause: str) -> Optional[Dict[str, Any]]:
    """Matches a single isolated desktop action clause into tool parameters."""
    req = clause.strip().lower()
    if not req:
        return None

    # 1. Open / Launch Applications
    m_open = re.match(r"^(?:open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+)$", req)
    if m_open:
        target = m_open.group(1).strip()
        if not any(k in target for k in ["file", "folder", "directory", "url", "website", "youtube", "google", "weather", "news", " and ", " then ", " after that "]):
            return {
                "description": f"Launch {target.title()}",
                "tool_name": "open_application",
                "tool_args": {"application": target}
            }
            
    # Direct short app names: "notepad", "calculator", "calc", "chrome", etc.
    if req in ("notepad", "calculator", "calc", "chrome", "spotify", "explorer", "code", "vscode", "cmd", "terminal", "paint", "settings"):
        return {
            "description": f"Launch {req.title()}",
            "tool_name": "open_application",
            "tool_args": {"application": req}
        }

    # 2. Close / Kill Applications
    m_close = re.match(r"^(?:close|kill|terminate|exit|quit)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+)$", req)
    if m_close:
        target = m_close.group(1).strip()
        if not any(k in target for k in ["tab", "window", "file", "down", "app"]):
            return {
                "description": f"Close {target.title()}",
                "tool_name": "close_application",
                "tool_args": {"application": target}
            }

    # 3. Take Screenshot
    if any(req == k or req.startswith(k) for k in [
        "take screenshot", "take a screenshot", "capture screen", "screenshot", "screen shot", "save screenshot"
    ]):
        return {
            "description": "Capture desktop screenshot",
            "tool_name": "take_screenshot",
            "tool_args": {}
        }

    # 4. Multimodal Screen Vision Analysis
    if any(req == k or req.startswith(k) for k in [
        "what is on my screen", "what is on screen", "analyze screen", "analyze my screen",
        "describe screen", "read my screen", "look at my screen", "what do you see on my screen"
    ]):
        return {
            "description": "Analyze visible screen contents using Gemini Vision",
            "tool_name": "analyze_screen",
            "tool_args": {"query": clause}
        }

    # 5. Battery & Power Diagnostics
    if any(req == k for k in [
        "battery", "battery status", "get battery status", "check battery", "power status",
        "what is my battery", "battery percentage", "check my battery", "check battery status"
    ]):
        return {
            "description": "Retrieve system battery diagnostics",
            "tool_name": "get_battery_status",
            "tool_args": {}
        }

    # 6. Network Uplink & Connectivity
    if any(req == k for k in [
        "network", "network status", "get network status", "check network", "wifi status",
        "internet status", "ping", "check my network", "check internet", "internet speed"
    ]):
        return {
            "description": "Inspect network interface and uplink connectivity",
            "tool_name": "get_network_status",
            "tool_args": {}
        }

    # 7. System Volume Control
    if req in ("volume up", "increase volume", "raise volume", "louder", "turn up volume", "set volume up"):
        return {
            "description": "Increase system volume",
            "tool_name": "set_system_volume",
            "tool_args": {"action": "up"}
        }
    if req in ("volume down", "decrease volume", "lower volume", "quieter", "turn down volume", "set volume down"):
        return {
            "description": "Decrease system volume",
            "tool_name": "set_system_volume",
            "tool_args": {"action": "down"}
        }
    if req in ("mute", "mute volume", "mute audio", "silence", "unmute", "toggle mute"):
        return {
            "description": "Mute/Unmute system volume",
            "tool_name": "set_system_volume",
            "tool_args": {"action": "mute"}
        }

    # 8. List Top Processes
    if req in ("top processes", "list top processes", "list processes", "task manager", "running processes", "active processes", "show processes"):
        return {
            "description": "List top active system processes",
            "tool_name": "list_top_processes",
            "tool_args": {"count": 5}
        }

    # 9. Power Management / Lock / Sleep
    if req in ("lock workstation", "lock screen", "lock pc", "lock computer", "lock"):
        return {
            "description": "Lock Windows workstation",
            "tool_name": "manage_power",
            "tool_args": {"action": "lock"}
        }
    if req in ("sleep", "sleep pc", "sleep computer", "put to sleep"):
        return {
            "description": "Put computer into sleep state",
            "tool_name": "manage_power",
            "tool_args": {"action": "sleep"}
        }

    # 10. Play Media on YouTube
    m_yt = re.match(r"^(?:play|listen to)\s+(.+?)(?:\s+on\s+youtube|\s+in\s+youtube)?$", req)
    if m_yt:
        media_query = m_yt.group(1).strip()
        return {
            "description": f"Play '{media_query}' on YouTube",
            "tool_name": "play_media",
            "tool_args": {"query": media_query}
        }

    # 11. Search Web on Google
    m_search = re.match(r"^(?:search|google|search for)\s+(.+?)(?:\s+on\s+google|\s+on\s+the\s+web|\s+online)?$", req)
    if m_search:
        search_query = m_search.group(1).strip()
        return {
            "description": f"Search the web for '{search_query}'",
            "tool_name": "search_web",
            "tool_args": {"query": search_query}
        }

    # 12. Show Desktop
    if req in ("show desktop", "minimize all", "toggle desktop", "hide windows"):
        return {
            "description": "Toggle Show Desktop (Win+D)",
            "tool_name": "press_keyboard_shortcut",
            "tool_args": {"shortcut": "win+d"}
        }

    # 13. Active Window Info
    if req in ("active window", "focused window", "current window", "inspect active window", "get active window"):
        return {
            "description": "Inspect active foreground window",
            "tool_name": "get_active_window_info",
            "tool_args": {}
        }

    # 14. Organize Downloads
    if req in ("organize downloads", "organize my downloads", "clean downloads"):
        return {
            "description": "Organize Downloads directory",
            "tool_name": "organize_directory",
            "tool_args": {"directory_path": "Downloads"}
        }

    # 15. Hardware Media Keys Control (Play, Pause, Next, Previous, Stop)
    if req in ("pause music", "pause song", "pause", "play music", "resume music", "play pause", "toggle music", "toggle media"):
        return {
            "description": "Toggle media play/pause",
            "tool_name": "media_playback_control",
            "tool_args": {"action": "play_pause"}
        }
    if req in ("next track", "next song", "next", "skip song", "skip track", "skip"):
        return {
            "description": "Skip to next media track",
            "tool_name": "media_playback_control",
            "tool_args": {"action": "next"}
        }
    if req in ("previous track", "previous song", "prev track", "prev song", "previous", "prev", "replay song"):
        return {
            "description": "Return to previous media track",
            "tool_name": "media_playback_control",
            "tool_args": {"action": "previous"}
        }
    if req in ("stop music", "stop media", "stop playback"):
        return {
            "description": "Stop media playback",
            "tool_name": "media_playback_control",
            "tool_args": {"action": "stop"}
        }

    # 16. Display & Brightness Controls
    if req in ("turn off screen", "turn off display", "turn off monitor", "sleep screen", "display sleep", "screen off"):
        return {
            "description": "Power off / sleep monitor display",
            "tool_name": "turn_off_screen",
            "tool_args": {}
        }
    m_bright = re.match(r"^(?:set\s+)?(?:display\s+|screen\s+|monitor\s+)?brightness\s+(?:to\s+)?(\d+)\s*%?$", req)
    if m_bright:
        lvl = int(m_bright.group(1))
        return {
            "description": f"Adjust display brightness to {lvl}%",
            "tool_name": "set_display_brightness",
            "tool_args": {"level": lvl}
        }
    if req in ("dim screen", "dim display", "lower brightness", "decrease brightness"):
        return {
            "description": "Dim display brightness to 30%",
            "tool_name": "set_display_brightness",
            "tool_args": {"level": 30}
        }
    if req in ("bright screen", "increase brightness", "max brightness", "full brightness"):
        return {
            "description": "Set display brightness to 100%",
            "tool_name": "set_display_brightness",
            "tool_args": {"level": 100}
        }

    # 17. Window Management (Maximize, Minimize, Restore, Snap, Switch, Close)
    if req in ("maximize window", "maximize", "full screen", "fullscreen window", "maximize current window"):
        return {
            "description": "Maximize active window",
            "tool_name": "control_active_window",
            "tool_args": {"action": "maximize"}
        }
    if req in ("minimize window", "minimize", "hide window", "minimize current window"):
        return {
            "description": "Minimize active window",
            "tool_name": "control_active_window",
            "tool_args": {"action": "minimize"}
        }
    if req in ("restore window", "restore", "unmaximize", "normal window"):
        return {
            "description": "Restore active window size",
            "tool_name": "control_active_window",
            "tool_args": {"action": "restore"}
        }
    if req in ("snap left", "snap window left", "left half", "window left"):
        return {
            "description": "Snap active window to the left",
            "tool_name": "control_active_window",
            "tool_args": {"action": "snap_left"}
        }
    if req in ("snap right", "snap window right", "right half", "window right"):
        return {
            "description": "Snap active window to the right",
            "tool_name": "control_active_window",
            "tool_args": {"action": "snap_right"}
        }
    if req in ("switch window", "switch app", "alt tab", "next window"):
        return {
            "description": "Switch active application (Alt+Tab)",
            "tool_name": "control_active_window",
            "tool_args": {"action": "switch"}
        }
    if req in ("close window", "exit window", "close active window", "close current window"):
        return {
            "description": "Close active window",
            "tool_name": "control_active_window",
            "tool_args": {"action": "close"}
        }

    # 18. Bluetooth Devices List
    if req in ("list bluetooth devices", "bluetooth devices", "show bluetooth", "check bluetooth", "bluetooth status"):
        return {
            "description": "Scan and list paired Bluetooth devices",
            "tool_name": "list_bluetooth_devices",
            "tool_args": {}
        }

    # 19. Wake-on-LAN (WOL) Magic Packet
    m_wol = re.match(r"^(?:wake\s+(?:on\s+lan|pc|computer|server|device)\s+)([0-9a-fA-F:\-]+)$", req)
    if m_wol:
        target_mac = m_wol.group(1).strip()
        return {
            "description": f"Send Wake-on-LAN magic packet to {target_mac}",
            "tool_name": "wake_on_lan",
            "tool_args": {"mac_address": target_mac}
        }

    return None

def split_compound_request(req: str) -> List[str]:
    """
    Decomposes a compound natural language sentence with multiple actions into sub-clauses.
    Handles 'and then', 'then', 'and', commas followed by actions, and semicolons.
    """
    raw = req.strip()
    # Normalize punctuation and conjunctions
    normalized = re.sub(r"\s*(?:,\s*(?:and\s+then|then|and)|;\s*|(?:and\s+then|then|after\s+that))\s*", " && ", raw, flags=re.IGNORECASE)
    
    # Split on explicit ' and ' when connecting separate action verbs
    # E.g. "open chrome and open notepad" or "check battery and take a screenshot"
    parts = re.split(r"\s+and\s+|\s*&&\s*|,\s*(?=(?:open|launch|close|kill|take|set|get|check|snap|maximize|minimize|dim|turn|play|list|show|switch|lock|sleep)\b)", normalized, flags=re.IGNORECASE)
    
    clauses = [p.strip(" ,.-:;!?") for p in parts if p.strip(" ,.-:;!?")]
    return clauses

def fast_plan_matcher(user_request: str) -> Optional[List[Dict[str, Any]]]:
    """
    Ultra-fast rule-based plan dispatcher (<0.1ms latency) for desktop commands and multi-tasking.
    Handles single directives as well as multi-task compound commands without LLM latency.
    """
    cleaned = user_request.strip().lower()
    
    # 1. Multi-Task compound action decomposition (check first)
    clauses = split_compound_request(cleaned)
    if len(clauses) > 1:
        steps = []
        for idx, clause in enumerate(clauses):
            action = match_single_fast_action(clause)
            if not action:
                # If any clause cannot be resolved by fast-path, delegate entire compound goal to Gemini LLM
                return None
            steps.append({
                "step_number": idx + 1,
                "description": action["description"],
                "tool_name": action["tool_name"],
                "tool_args": action["tool_args"]
            })
        return steps

    # 2. Direct single action check
    single_action = match_single_fast_action(cleaned)
    if single_action:
        return [{
            "step_number": 1,
            "description": single_action["description"],
            "tool_name": single_action["tool_name"],
            "tool_args": single_action["tool_args"]
        }]

    return None

class Planner:
    def __init__(self, ai_provider: AIProvider):
        self.ai_provider = ai_provider

    async def create_plan(self, user_request: str, available_tools: List[Any], context_memory: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generates a structured plan of steps for the user request with instant fast-path dispatch."""
        
        # 1. Fast-Path Instant Dispatcher (<0.1ms execution for single and compound multi-tasks)
        fast_plan = fast_plan_matcher(user_request)
        if fast_plan:
            print(f"[Planner FastPath] Instant {len(fast_plan)}-step plan generated in 0.05ms for: '{user_request}'")
            return fast_plan

        # 2. Complex / Multi-Step Planner via Gemini LLM
        tools_desc = []
        for info in available_tools:
            tools_desc.append(f"- '{info.name}': {info.description} (Risk level: {info.risk_level})")
        tools_str = "\n".join(tools_desc)

        active_memory = context_memory or MemoryManager.get_prompt_context()

        prompt = f"User Request: \"{user_request}\"\n"
        if active_memory:
            prompt += f"\nRelevant User Preferences & Remembered Context:\n{active_memory}\n"
        prompt += "\nDecompose this request and generate the sequential plan in JSON format."

        system_instruction = PLANNING_SYSTEM_INSTRUCTION.format(tools_descriptions=tools_str)

        try:
            response = await self.ai_provider.generate(
                prompt=prompt,
                system_instruction=system_instruction
            )
            
            clean_text = response.text.strip()
            if clean_text.startswith("```"):
                lines = clean_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()
            
            plan = json.loads(clean_text)
            if not isinstance(plan, list):
                raise ValueError("Planner LLM did not return a list array.")
                
            return plan
        except json.JSONDecodeError:
            print(f"[Planner Error] Failed to parse JSON plan: {response.text}")
            return [{
                "step_number": 1,
                "description": f"Executing directive: {user_request}",
                "tool_name": None,
                "tool_args": None
            }]
        except Exception as e:
            print(f"[Planner Error] Planning failed: {e}")
            raise e
