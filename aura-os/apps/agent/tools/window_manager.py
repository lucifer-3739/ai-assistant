import ctypes
import time
from typing import Dict, Any, Optional
from tools.base import registry

# Windows API Constants
SW_HIDE = 0
SW_NORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_MINIMIZE = 6
SW_RESTORE = 9

VK_LWIN = 0x5B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_MENU = 0x12  # Alt
VK_TAB = 0x09
VK_F4 = 0x73

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

@registry.register(
    name="control_active_window",
    description="Manages windows: 'maximize', 'minimize', 'restore', 'snap_left', 'snap_right', 'switch', 'close'.",
    risk_level="SAFE",
    required_permission="execution",
    verify_method=None
)
def control_active_window(action: str = "maximize", **kwargs) -> str:
    """Performs window control actions on the foreground active application window."""
    act = str(action).lower().strip().replace(" ", "_").replace("-", "_")
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()

    try:
        if act in ("maximize", "max", "full_screen", "fullscreen"):
            if hwnd:
                user32.ShowWindow(hwnd, SW_MAXIMIZE)
                return "Active window maximized."
            else:
                return "No active window to maximize."

        elif act in ("minimize", "min", "hide"):
            if hwnd:
                user32.ShowWindow(hwnd, SW_MINIMIZE)
                return "Active window minimized."
            else:
                return "No active window to minimize."

        elif act in ("restore", "unmaximize", "normal"):
            if hwnd:
                user32.ShowWindow(hwnd, SW_RESTORE)
                return "Active window restored to normal size."
            else:
                return "No active window to restore."

        elif act in ("snap_left", "left", "left_side"):
            # Win + Left Arrow
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_LEFT, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(VK_LEFT, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
            return "Active window snapped to the left half of the screen."

        elif act in ("snap_right", "right", "right_side"):
            # Win + Right Arrow
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
            return "Active window snapped to the right half of the screen."

        elif act in ("switch", "switch_app", "alt_tab", "next_window"):
            # Alt + Tab
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_TAB, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            return "Switched active application window."

        elif act in ("close", "close_window", "exit_window", "alt_f4"):
            # Alt + F4
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_F4, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_F4, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            return "Closed active window."

        else:
            return f"Unknown window action: '{action}'. Available: maximize, minimize, restore, snap_left, snap_right, switch, close."
    except Exception as e:
        return f"Window control error: {e}"
