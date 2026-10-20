import os
import shutil
import subprocess
import webbrowser
import urllib.parse

def open_website(url: str) -> str:
    """Opens a website URL in the user's default web browser.

    Args:
        url: The website URL to open (e.g., 'https://youtube.com', 'https://github.com').
    """
    # Ensure URL has protocol prefix
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    
    try:
        webbrowser.open(url)
        return f"Opened website: {url}"
    except Exception as e:
        return f"Failed to open website: {e}"

def search_google(query: str) -> str:
    """Searches Google for the given query in the user's default web browser.

    Args:
        query: The query string to search for.
    """
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        webbrowser.open(url)
        return f"Searched Google for: '{query}'"
    except Exception as e:
        return f"Failed to perform search: {e}"

def open_application(app_name: str) -> str:
    """Launches a Windows application on the user's computer.

    Args:
        app_name: The name of the application to open (e.g., 'notepad', 'chrome', 'spotify', 'calculator', 'explorer').
    """
    app_lower = app_name.lower().strip()
    
    # Common Windows application mappings
    app_map = {
        "notepad": ["notepad.exe"],
        "chrome": ["cmd.exe", "/c", "start chrome"],
        "google chrome": ["cmd.exe", "/c", "start chrome"],
        "spotify": ["cmd.exe", "/c", "start spotify"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "explorer": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
        "cmd": ["cmd.exe"],
        "command prompt": ["cmd.exe"],
        "paint": ["mspaint.exe"],
        "mspaint": ["mspaint.exe"]
    }
    
    try:
        if app_lower in app_map:
            args = app_map[app_lower]
            subprocess.Popen(args)
            return f"Launching {app_name}..."
        else:
            # Fallback: try running it directly as a command in the shell
            subprocess.Popen(["cmd.exe", "/c", f"start {app_lower}"], shell=True)
            return f"Attempting to launch '{app_name}' via start command..."
    except Exception as e:
        return f"Failed to launch application '{app_name}': {e}"

def close_application(app_name: str) -> str:
    """Closes a running application on the user's computer.

    Args:
        app_name: The name of the application to close (e.g., 'notepad', 'chrome', 'spotify', 'calculator').
    """
    app_lower = app_name.lower().strip()
    
    # Common taskkill executable mappings
    exe_map = {
        "notepad": "notepad.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "spotify": "Spotify.exe",
        "calculator": "CalculatorApp.exe",
        "calc": "CalculatorApp.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe"
    }
    
    exe_name = exe_map.get(app_lower, f"{app_lower}.exe")
    
    try:
        # Run taskkill to terminate the application process
        # /F forces termination, /IM specifies image name
        result = subprocess.run(
            ["taskkill", "/F", "/IM", exe_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return f"Closed {app_name} successfully."
        else:
            # Try close by window title or standard command if process name didn't match
            return f"Could not close {app_name}. (Process '{exe_name}' might not be running)."
    except Exception as e:
        return f"Failed to close application '{app_name}': {e}"

def list_directory(path: str = ".") -> str:
    """Lists files and folders in the specified directory path.

    Args:
        path: The folder path to inspect (defaults to current folder).
    """
    try:
        # Resolve path
        resolved_path = os.path.abspath(path)
        if not os.path.exists(resolved_path):
            return f"Path does not exist: {path}"
            
        items = os.listdir(resolved_path)
        if not items:
            return f"The directory '{resolved_path}' is empty."
            
        files_list = []
        for item in items:
            full_item_path = os.path.join(resolved_path, item)
            is_dir = "[DIR]" if os.path.isdir(full_item_path) else "[FILE]"
            files_list.append(f"{is_dir} {item}")
            
        return f"Contents of '{resolved_path}':\n" + "\n".join(files_list)
    except Exception as e:
        return f"Error listing directory: {e}"

def read_file(filepath: str) -> str:
    """Reads and returns the contents of a text file.

    Args:
        filepath: The path of the file to read.
    """
    try:
        resolved_path = os.path.abspath(filepath)
        if not os.path.exists(resolved_path):
            return f"File not found: {filepath}"
            
        if os.path.isdir(resolved_path):
            return f"'{filepath}' is a directory, not a file."
            
        with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(8000) # limit to first 8000 characters to avoid API token blowup
            if len(content) >= 8000:
                content += "\n...[Content truncated due to size limit]"
            return f"Content of '{resolved_path}':\n\n{content}"
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(filepath: str, content: str) -> str:
    """Creates a new text file or overwrites an existing one with content.

    Args:
        filepath: The path of the file to write to.
        content: The text content to write.
    """
    try:
        resolved_path = os.path.abspath(filepath)
        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
        
        with open(resolved_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Successfully wrote to file: '{resolved_path}'"
    except Exception as e:
        return f"Error writing file: {e}"

def organize_folder(folder_path: str) -> str:
    """Organizes files in a folder into subdirectories based on their file type extensions.

    Args:
        folder_path: The directory path containing files to organize.
    """
    try:
        resolved_path = os.path.abspath(folder_path)
        if not os.path.exists(resolved_path) or not os.path.isdir(resolved_path):
            return f"Directory does not exist or is not a folder: {folder_path}"

        # Category maps for extensions
        category_map = {
            "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico"],
            "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".csv", ".json"],
            "Audio": [".mp3", ".wav", ".m4a", ".flac", ".wma"],
            "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"]
        }

        items = os.listdir(resolved_path)
        moved_counts = {}

        for item in items:
            item_path = os.path.join(resolved_path, item)
            
            # Skip directories
            if os.path.isdir(item_path):
                continue
                
            file_name, file_ext = os.path.splitext(item).lower()
            
            # Find category
            target_category = None
            for category, extensions in category_map.items():
                if file_ext in extensions:
                    target_category = category
                    break
                    
            if not target_category:
                target_category = "Others"

            # Create destination folder
            dest_folder = os.path.join(resolved_path, target_category)
            os.makedirs(dest_folder, exist_ok=True)
            
            # Move file
            dest_file_path = os.path.join(dest_folder, item)
            shutil.move(item_path, dest_file_path)
            
            # Update counts
            moved_counts[target_category] = moved_counts.get(target_category, 0) + 1

        if not moved_counts:
            return f"No files were found in '{resolved_path}' to organize."
            
        summary = ", ".join([f"{count} files to {cat}" for cat, count in moved_counts.items()])
        return f"Successfully organized folder '{resolved_path}': Moved {summary}."
    except Exception as e:
        return f"Error organizing folder: {e}"

def capture_screen() -> str:
    """Captures the user's primary desktop monitor screen. Use this when the user asks you to look at their screen, inspect what is open, read code or see an error message on screen."""
    try:
        from PIL import ImageGrab
        # Grab screen
        screenshot = ImageGrab.grab()
        # Save as screenshot.png in the project directory
        screenshot.save("screenshot.png")
        return "Primary monitor screen captured successfully. The image is now available."
    except Exception as e:
        return f"Failed to capture screen: {e}"

def capture_camera(camera_index: int = 0) -> str:
    """Captures a single frame from the user's webcam or local camera. Use this when the user asks you to see them, look at their surroundings, or identify an object in front of the camera.
    
    Args:
        camera_index: The hardware index of the camera (default: 0).
    """
    try:
        import cv2
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return f"Error: Could not open camera at index {camera_index}."
            
        # Read a few frames to allow the camera's auto-exposure to adjust
        for _ in range(5):
            ret, frame = cap.read()
            
        if not ret:
            cap.release()
            return "Error: Could not read frame from camera."
            
        # Save the captured frame
        cv2.imwrite("camera.jpg", frame)
        cap.release()
        return "Webcam frame captured successfully. The image is now available."
    except Exception as e:
        return f"Failed to capture camera frame: {e}"
