import os
import subprocess
import platform
import re
from typing import Dict, Any
from tools.base import registry

@registry.register(
    name="get_battery_status",
    description="Checks the current battery percentage and charging status on portable devices or power connection on desktops.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def get_battery_status(**kwargs) -> str:
    try:
        cmd = "Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=8)
        
        output = res.stdout.strip()
        if not output or "EstimatedChargeRemaining" not in output:
            return "Power Status: Running on AC power connection (Desktop Workstation / No battery installed)."
            
        # Parse percentage numbers
        numbers = re.findall(r"\d+", output)
        if numbers:
            pct = numbers[0]
            status_code = int(numbers[1]) if len(numbers) > 1 else 1
            status_desc = {
                1: "Discharging",
                2: "On AC Power (Charging)",
                3: "Fully Charged",
                4: "Low Battery",
                5: "Critical Battery",
                6: "Charging",
                7: "Charging and High",
                8: "Charging and Low",
                9: "Charging and Critical"
            }.get(status_code, "Connected")
            
            return f"Battery Status: {pct}% remaining ({status_desc})."
            
        return f"Battery Diagnostics: {output}"
    except Exception as e:
        return f"Power Diagnostics: AC power connected ({e})."

@registry.register(
    name="get_network_status",
    description="Tests network connectivity, returns current IPv4 address, and measures ping latency.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def get_network_status(**kwargs) -> str:
    import socket
    import time
    try:
        hostname = socket.gethostname()
        local_ip = "127.0.0.1"
        try:
            # Connect to an external IP to determine default egress interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = socket.gethostbyname(hostname)
        
        # Fast DNS latency test
        latency_str = "Offline / Local Only"
        try:
            t0 = time.time()
            test_sock = socket.create_connection(("8.8.8.8", 53), timeout=3)
            elapsed_ms = int((time.time() - t0) * 1000)
            test_sock.close()
            latency_str = f"{elapsed_ms} ms (Active Internet Connection)"
        except Exception:
            pass
            
        result = "Network Uplink Status:\n"
        result += f" - Hostname: {hostname}\n"
        result += f" - IPv4 Address: {local_ip}\n"
        result += f" - Internet Latency (Google DNS): {latency_str}"
        return result
    except Exception as e:
        return f"Network check error: {e}"

@registry.register(
    name="list_top_processes",
    description="Inspects active Windows processes and lists the top memory and CPU consuming applications.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def list_top_processes(count: int = 10, **kwargs) -> str:
    limit = count or kwargs.get("top_n") or kwargs.get("limit") or 10
    try:
        cmd = f"Get-Process | Sort-Object -Property WorkingSet64 -Descending | Select-Object -First {limit} -Property ProcessName, Id, @{{Name='Memory_MB';Expression={{[math]::Round($_.WorkingSet64/1MB,1)}}}} | Format-Table -AutoSize"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=10)
        return f"Top {limit} Active Processes by Memory Usage:\n\n{res.stdout.strip()}"
    except Exception as e:
        return f"Process inspection error: {e}"

@registry.register(
    name="set_system_volume",
    description="Adjusts master system audio volume (up, down, mute, or unmute).",
    risk_level="SAFE",
    required_permission="system-control",
    verify_method=None
)
def set_system_volume(action: str = "up", level: int = None, **kwargs) -> str:
    act = action or kwargs.get("direction") or kwargs.get("mode") or "up"
    act_lower = str(act).lower()
    
    try:
        if "mute" in act_lower:
            # Mute toggle key (0xAD = 173)
            cmd = "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            return "System audio mute state toggled."
        elif "down" in act_lower or "decrease" in act_lower:
            # Volume down key (0xAE = 174) pressed multiple times
            cmd = "1..5 | ForEach-Object { (New-Object -ComObject WScript.Shell).SendKeys([char]174) }"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            return "Decreased master system volume."
        else:
            # Volume up key (0xAF = 175) pressed multiple times
            cmd = "1..5 | ForEach-Object { (New-Object -ComObject WScript.Shell).SendKeys([char]175) }"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            return "Increased master system volume."
    except Exception as e:
        return f"Failed to adjust system volume: {e}"

@registry.register(
    name="manage_power",
    description="Manages system power states (lock workstation, sleep, restart, or shutdown computer).",
    risk_level="CRITICAL",
    required_permission="system-power",
    verify_method=None
)
def manage_power(action: str = "lock", **kwargs) -> str:
    act = action or kwargs.get("state") or kwargs.get("mode") or kwargs.get("operation") or "lock"
    act_lower = str(act).lower().strip()
    
    try:
        if "lock" in act_lower:
            # Safe lock screen
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Workstation screen locked successfully."
        elif "sleep" in act_lower or "suspend" in act_lower:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return "System entering sleep mode."
        elif "restart" in act_lower or "reboot" in act_lower:
            subprocess.run(["shutdown", "/r", "/t", "10", "/c", "AURA OS requested system restart"])
            return "System restart initiated (10 second timer). Run 'shutdown /a' to abort."
        elif "shutdown" in act_lower or "turn off" in act_lower or "power off" in act_lower:
            subprocess.run(["shutdown", "/s", "/t", "10", "/c", "AURA OS requested system shutdown"])
            return "System shutdown initiated (10 second timer). Run 'shutdown /a' to abort."
        else:
            return f"Unknown power action '{action}'. Supported: lock, sleep, restart, shutdown."
    except Exception as e:
        return f"Power management error: {e}"
