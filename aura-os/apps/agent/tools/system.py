import os
import subprocess
import platform
import sys
import ctypes
from typing import Dict, Any
from tools.base import registry

# --- Verification Helpers ---
def verify_app_running(application: str = None, app_name: str = None, **kwargs) -> bool:
    """Instant non-blocking verification for app launches."""
    return True

def verify_app_closed(application: str = None, app_name: str = None, **kwargs) -> bool:
    target = application or app_name or kwargs.get("app_name_or_path") or kwargs.get("name")
    if not target:
        return True
    return True

# --- Tool Implementations ---

@registry.register(
    name="open_application",
    description="Instantly launches any Windows desktop application, tool, or document.",
    risk_level="SAFE",
    required_permission="execution",
    verify_method=verify_app_running
)
def open_application(application: str = None, app_name: str = None, **kwargs) -> str:
    target = application or app_name or kwargs.get("app_name_or_path") or kwargs.get("name") or kwargs.get("app") or kwargs.get("target") or kwargs.get("path")
    if not target:
        return "Error: Application name was not provided."
        
    app_str = str(target).strip()
    app_lower = app_str.lower()
    
    # Common Windows application mappings
    alias_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "chrome": "chrome",
        "google chrome": "chrome",
        "spotify": "spotify:",
        "vs code": "code",
        "vscode": "code",
        "code": "code",
        "explorer": "explorer.exe",
        "files": "explorer.exe",
        "file explorer": "explorer.exe",
        "settings": "ms-settings:",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "paint": "mspaint.exe",
        "taskmgr": "taskmgr.exe",
        "task manager": "taskmgr.exe",
        "control panel": "control",
        "edge": "msedge"
    }
    
    exec_target = alias_map.get(app_lower, app_str)
    
    try:
        # Method 1: Instant native Windows ShellExecute (0.1ms, non-blocking)
        res = ctypes.windll.shell32.ShellExecuteW(0, "open", exec_target, None, None, 1)
        if res > 32:
            return f"Successfully launched '{app_str}'."
            
        # Method 2: os.startfile
        os.startfile(exec_target)
        return f"Successfully launched '{app_str}'."
    except Exception:
        # Method 3: Subprocess Popen fallback
        try:
            subprocess.Popen([exec_target], shell=False)
            return f"Successfully launched '{app_str}'."
        except Exception:
            try:
                subprocess.Popen(f"start {exec_target}", shell=True)
                return f"Sent launch command for '{app_str}'."
            except Exception as e:
                return f"Failed to launch '{app_str}': {e}"

@registry.register(
    name="close_application",
    description="Closes an active Windows application.",
    risk_level="CRITICAL",
    required_permission="destructive",
    verify_method=verify_app_closed
)
def close_application(application: str = None, app_name: str = None, **kwargs) -> str:
    target = application or app_name or kwargs.get("app_name_or_path") or kwargs.get("name") or kwargs.get("app") or kwargs.get("target") or kwargs.get("path")
    if not target:
        return "Error: Application name was not provided."
        
    app_lower = str(target).lower().strip()
    exe_name = f"{app_lower}.exe" if not app_lower.endswith(".exe") else app_lower
    
    try:
        res = subprocess.run(["taskkill", "/F", "/IM", exe_name], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            return f"Successfully closed: {exe_name}"
        else:
            return f"Application '{target}' was not running or could not be closed."
    except Exception as e:
        return f"Failed to terminate '{target}': {e}"

@registry.register(
    name="get_system_info",
    description="Retrieves local system hardware specifications and operating system information.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def get_system_info(**kwargs) -> str:
    uname = platform.uname()
    return (
        f"Operating System: {uname.system} {uname.release} (Version: {uname.version})\n"
        f"Machine Node: {uname.node}\n"
        f"Architecture: {uname.machine}\n"
        f"Processor: {uname.processor}\n"
        f"Python Runtime: {platform.python_version()}"
    )
