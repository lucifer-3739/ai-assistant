import time
import ctypes
import subprocess
from typing import Dict, Any, Optional
from tools.base import registry

@registry.register(
    name="type_text",
    description="Types text characters into the currently active focused application window.",
    risk_level="MODERATE",
    required_permission="gui-automation",
    verify_method=None
)
def type_text(text: str = None, **kwargs) -> str:
    content = text or kwargs.get("keys") or kwargs.get("input") or kwargs.get("content") or kwargs.get("message")
    if not content:
        return "Error: No text provided to type."
        
    try:
        # Escape special SendKeys characters: +, ^, %, ~, (, ), [, ], {, }
        sanitized = ""
        for ch in str(content):
            if ch in "+^%~(){}[]":
                sanitized += f"{{{ch}}}"
            else:
                sanitized += ch
                
        # Send keys via WScript.Shell
        cmd = f"(New-Object -ComObject WScript.Shell).SendKeys('{sanitized}')"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=8)
        
        if res.returncode == 0:
            return f"Successfully typed {len(content)} characters into active window."
        else:
            return f"Typing error: {res.stderr}"
    except Exception as e:
        return f"Failed to type text: {e}"

@registry.register(
    name="press_keyboard_shortcut",
    description="Executes system keyboard shortcuts (e.g. 'ctrl+s', 'ctrl+c', 'ctrl+v', 'alt+f4', 'win+d', 'enter', 'esc').",
    risk_level="MODERATE",
    required_permission="gui-automation",
    verify_method=None
)
def press_keyboard_shortcut(shortcut: str = None, **kwargs) -> str:
    key = shortcut or kwargs.get("hotkey") or kwargs.get("keys") or kwargs.get("combo")
    if not key:
        return "Error: No shortcut specified."
        
    key_lower = str(key).lower().replace(" ", "")
    
    try:
        if "win+d" in key_lower or "showdesktop" in key_lower:
            cmd = "(New-Object -ComObject Shell.Application).ToggleDesktop()"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            return "Executed 'Win+D': Toggled Show Desktop."
            
        # Key mapping for SendKeys
        hotkey_map = {
            "ctrl+s": "^s",
            "ctrl+c": "^c",
            "ctrl+v": "^v",
            "ctrl+x": "^x",
            "ctrl+z": "^z",
            "ctrl+y": "^y",
            "ctrl+a": "^a",
            "ctrl+f": "^f",
            "ctrl+p": "^p",
            "ctrl+w": "^w",
            "ctrl+t": "^t",
            "alt+f4": "%{F4}",
            "alt+tab": "%{TAB}",
            "enter": "{ENTER}",
            "esc": "{ESC}",
            "escape": "{ESC}",
            "tab": "{TAB}",
            "space": " ",
            "backspace": "{BACKSPACE}",
            "delete": "{DELETE}"
        }
        
        send_key = hotkey_map.get(key_lower)
        if not send_key:
            # Fallback parsing for custom combos
            send_key = key_lower.replace("ctrl+", "^").replace("alt+", "%").replace("shift+", "+")
            
        cmd = f"(New-Object -ComObject WScript.Shell).SendKeys('{send_key}')"
        subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=5)
        return f"Successfully executed keyboard shortcut: '{key}'"
    except Exception as e:
        return f"Failed to press shortcut '{key}': {e}"

@registry.register(
    name="click_screen",
    description="Moves the mouse cursor and performs a mouse click on the screen.",
    risk_level="MODERATE",
    required_permission="gui-automation",
    verify_method=None
)
def click_screen(x: int = None, y: int = None, button: str = "left", **kwargs) -> str:
    target_x = x or kwargs.get("pos_x") or kwargs.get("coord_x")
    target_y = y or kwargs.get("pos_y") or kwargs.get("coord_y")
    btn = button or kwargs.get("mouse_button") or "left"
    
    user32 = ctypes.windll.user32
    
    try:
        # Move cursor if coordinates provided
        if target_x is not None and target_y is not None:
            user32.SetCursorPos(int(target_x), int(target_y))
            time.sleep(0.05)
            
        # Click flags
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010
        
        if "right" in str(btn).lower():
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            return f"Executed right mouse click at position ({target_x}, {target_y})."
        else:
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return f"Executed left mouse click at position ({target_x}, {target_y})."
    except Exception as e:
        return f"Mouse click execution failed: {e}"
