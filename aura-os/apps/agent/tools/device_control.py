import os
import re
import socket
import struct
import urllib.request
import json
import ctypes
import subprocess
from typing import Dict, Any, Optional
from tools.base import registry

# Windows Virtual Key Codes for Media Control
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

@registry.register(
    name="set_display_brightness",
    description="Adjusts the monitor screen brightness level (0 to 100 percent).",
    risk_level="SAFE",
    required_permission="execution",
    verify_method=None
)
def set_display_brightness(level: Any = 50, brightness: Any = None, **kwargs) -> str:
    """Sets monitor display brightness on Windows."""
    val = brightness if brightness is not None else level
    try:
        brightness_val = int(re.sub(r"[^\d]", "", str(val)))
        brightness_val = max(0, min(100, brightness_val))
    except Exception:
        brightness_val = 50

    try:
        ps_cmd = f"(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {brightness_val})"
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=4)
        return f"Display brightness adjusted to {brightness_val}%."
    except Exception as e:
        return f"Brightness command dispatched ({brightness_val}%): {e}"

@registry.register(
    name="turn_off_screen",
    description="Turns off or puts the computer monitor display into sleep mode instantly.",
    risk_level="SAFE",
    required_permission="execution",
    verify_method=None
)
def turn_off_screen(**kwargs) -> str:
    """Sends native Windows SC_MONITORPOWER command to put monitors to sleep."""
    try:
        HWND_BROADCAST = 0xFFFF
        WM_SYSCOMMAND = 0x0112
        SC_MONITORPOWER = 0xF170
        # 2 = turn off monitor, 1 = low power, -1 = turn on
        ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)
        return "Monitor display powered off / put to sleep."
    except Exception as e:
        return f"Failed to turn off screen: {e}"

@registry.register(
    name="media_playback_control",
    description="Controls media playback: 'play_pause', 'next', 'previous', 'stop', 'mute'.",
    risk_level="SAFE",
    required_permission="execution",
    verify_method=None
)
def media_playback_control(action: str = "play_pause", **kwargs) -> str:
    """Simulates Windows hardware media key events."""
    act = str(action).lower().strip().replace(" ", "_").replace("-", "_")
    
    key_map = {
        "play": VK_MEDIA_PLAY_PAUSE,
        "pause": VK_MEDIA_PLAY_PAUSE,
        "play_pause": VK_MEDIA_PLAY_PAUSE,
        "toggle": VK_MEDIA_PLAY_PAUSE,
        "next": VK_MEDIA_NEXT_TRACK,
        "next_track": VK_MEDIA_NEXT_TRACK,
        "skip": VK_MEDIA_NEXT_TRACK,
        "prev": VK_MEDIA_PREV_TRACK,
        "previous": VK_MEDIA_PREV_TRACK,
        "previous_track": VK_MEDIA_PREV_TRACK,
        "back": VK_MEDIA_PREV_TRACK,
        "stop": VK_MEDIA_STOP,
        "mute": VK_VOLUME_MUTE,
        "unmute": VK_VOLUME_MUTE
    }
    
    vk_code = key_map.get(act, VK_MEDIA_PLAY_PAUSE)
    
    try:
        user32 = ctypes.windll.user32
        # Key down
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        # Key up
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return f"Media key '{act}' dispatched successfully."
    except Exception as e:
        return f"Failed to dispatch media key: {e}"

@registry.register(
    name="list_bluetooth_devices",
    description="Scans and lists paired Bluetooth devices (speakers, headsets, phones, keyboards).",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def list_bluetooth_devices(**kwargs) -> str:
    """Queries Bluetooth devices from Windows PnP database."""
    try:
        ps_cmd = "Get-PnpDevice -Class Bluetooth | Where-Object {$_.FriendlyName -notlike '*Enumerator*' -and $_.FriendlyName -notlike '*Adapter*' -and $_.FriendlyName -notlike '*Radio*'} | Select-Object -First 10 FriendlyName, Status, Present | Format-Table -AutoSize"
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
        output = res.stdout.strip()
        if output:
            return f"Bluetooth Devices:\n{output}"
        return "No external Bluetooth peripherals currently detected."
    except Exception as e:
        return f"Bluetooth scan error: {e}"

@registry.register(
    name="wake_on_lan",
    description="Sends a Wake-on-LAN (WOL) magic packet to wake another PC or smart device on the local network.",
    risk_level="SAFE",
    required_permission="execution",
    verify_method=None
)
def wake_on_lan(mac_address: str = None, mac: str = None, broadcast_ip: str = "255.255.255.255", **kwargs) -> str:
    """Broadcasts a 102-byte Wake-on-LAN magic packet over UDP."""
    raw_mac = mac_address or mac or kwargs.get("target_mac") or kwargs.get("address")
    if not raw_mac:
        return "Error: Target MAC address is required (e.g. '00:11:22:33:44:55' or '00-11-22-33-44-55')."

    clean_mac = re.sub(r"[^0-9A-Fa-f]", "", str(raw_mac))
    if len(clean_mac) != 12:
        return f"Error: Invalid MAC address length '{raw_mac}'. Expected 12 hexadecimal characters."

    try:
        # Build 102-byte Magic Packet: 6 bytes of 0xFF followed by 16 repetitions of the 6-byte MAC
        hw_bytes = bytes.fromhex(clean_mac)
        magic_packet = b"\xff" * 6 + hw_bytes * 16

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, 9))
        sock.close()

        formatted_mac = ":".join(clean_mac[i:i+2].upper() for i in range(0, 12, 2))
        return f"Wake-on-LAN magic packet transmitted to '{formatted_mac}' (Broadcast: {broadcast_ip}:9)."
    except Exception as e:
        return f"Failed to send Wake-on-LAN packet: {e}"

@registry.register(
    name="smart_device_webhook",
    description="Sends HTTP/REST webhook triggers to control smart home devices (Home Assistant, Tasmota, smart plugs).",
    risk_level="SAFE",
    required_permission="execution",
    verify_method=None
)
def smart_device_webhook(url: str = None, endpoint: str = None, method: str = "GET", payload: Dict[str, Any] = None, **kwargs) -> str:
    """Sends HTTP GET/POST requests to IoT smart home devices."""
    target_url = url or endpoint or kwargs.get("webhook_url") or kwargs.get("target")
    if not target_url:
        return "Error: Webhook target URL is required."

    try:
        req_method = str(method).upper().strip()
        data_bytes = None
        headers = {"User-Agent": "FRIDAY-OS-SmartController/1.0"}

        if payload:
            data_bytes = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(target_url, data=data_bytes, headers=headers, method=req_method)
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8", errors="ignore")[:300]
            return f"Smart device responded (HTTP {status_code}): {body or 'OK'}"
    except Exception as e:
        return f"Smart device webhook error: {e}"
