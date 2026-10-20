import os
import io
import time
import ctypes
import asyncio
from datetime import datetime
from ctypes import wintypes
from typing import Dict, Any, Optional
import PIL.Image
from tools.base import registry
from core.ai_provider import GeminiProvider

def capture_screen_image() -> PIL.Image.Image:
    """Captures the primary monitor using native Windows GDI for high-speed, zero-dependency capture."""
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    w = user32.GetSystemMetrics(0) # SM_CXSCREEN
    h = user32.GetSystemMetrics(1) # SM_CYSCREEN
    
    hwnd = user32.GetDesktopWindow()
    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    # BitBlt with SRCCOPY
    gdi32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020 | 0x40000000)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', wintypes.DWORD),
            ('biWidth', wintypes.LONG),
            ('biHeight', wintypes.LONG),
            ('biPlanes', wintypes.WORD),
            ('biBitCount', wintypes.WORD),
            ('biCompression', wintypes.DWORD),
            ('biSizeImage', wintypes.DWORD),
            ('biXPelsPerMeter', wintypes.LONG),
            ('biYPelsPerMeter', wintypes.LONG),
            ('biClrUsed', wintypes.DWORD),
            ('biClrImportant', wintypes.DWORD)
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)

    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)

    img = PIL.Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
    return img

@registry.register(
    name="take_screenshot",
    description="Captures the full desktop screen and saves it to a PNG image file.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def take_screenshot(filename: str = None, **kwargs) -> str:
    target_name = filename or kwargs.get("path") or kwargs.get("name") or kwargs.get("file")
    
    if not target_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_name = f"screenshot_{timestamp}.png"
        
    if not target_name.endswith(".png") and not target_name.endswith(".jpg"):
        target_name += ".png"
        
    resolved_path = os.path.abspath(target_name)
    try:
        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
        img = capture_screen_image()
        img.save(resolved_path, format="PNG")
        return f"Screenshot successfully saved to: '{resolved_path}' (Resolution: {img.width}x{img.height})"
    except Exception as e:
        return f"Failed to capture screenshot: {e}"

@registry.register(
    name="analyze_screen",
    description="Captures the user's screen and uses Gemini Multi-Modal Vision to read text, understand error messages, and analyze visual elements.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def analyze_screen(query: str = None, **kwargs) -> str:
    prompt_text = query or kwargs.get("prompt") or kwargs.get("question") or "Describe what is currently visible on the screen, including open applications, errors, or prominent text."
    
    try:
        # Capture screen
        img = capture_screen_image()
        
        # Resize to max 1280 width to optimize network bandwidth while keeping text sharp
        if img.width > 1280:
            scale = 1280.0 / img.width
            new_size = (1280, int(img.height * scale))
            img = img.resize(new_size, PIL.Image.Resampling.LANCZOS)
            
        byte_io = io.BytesIO()
        img.save(byte_io, format="PNG", optimize=True)
        img_bytes = byte_io.getvalue()
        
        # Call Gemini Vision
        provider = GeminiProvider()
        
        system_instruction = (
            "You are the Vision Engine of AURA OS. You analyze the user's desktop screenshot. "
            "Be precise, clear, and direct. If the user asked about an error, extract the exact error text "
            "and diagnose it. If they asked to summarize or read content, extract the relevant information."
        )
        
        # Run async provider call in event loop or asyncio.run
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = pool.submit(
                    asyncio.run,
                    provider.generate(
                        prompt=prompt_text,
                        system_instruction=system_instruction,
                        image_bytes=img_bytes,
                        mime_type="image/png"
                    )
                ).result()
        except RuntimeError:
            res = asyncio.run(
                provider.generate(
                    prompt=prompt_text,
                    system_instruction=system_instruction,
                    image_bytes=img_bytes,
                    mime_type="image/png"
                )
            )
            
        return f"Screen Vision Analysis:\n\n{res.text}"
    except Exception as e:
        return f"Failed to perform visual screen analysis: {e}"

@registry.register(
    name="get_active_window_info",
    description="Inspects the currently focused application window title and process information.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def get_active_window_info(**kwargs) -> str:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "No foreground window currently detected."
            
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        
        # Get process ID
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        return f"Active Focused Window:\n - Title: '{title or 'Untitled / System Window'}'\n - HWND: {hwnd}\n - Process ID: {pid.value}"
    except Exception as e:
        return f"Failed to retrieve active window info: {e}"
