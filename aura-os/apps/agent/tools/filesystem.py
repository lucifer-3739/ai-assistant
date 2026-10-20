import os
import shutil
import glob
from typing import Dict, Any
from tools.base import registry

# --- Verification Helpers ---
def verify_folder_exists(path: str = None, **kwargs) -> bool:
    target = path or kwargs.get("folder_name") or kwargs.get("name") or kwargs.get("directory") or kwargs.get("dir") or kwargs.get("folder") or kwargs.get("folder_path")
    if not target:
        return True
    return os.path.isdir(os.path.abspath(target))

def verify_file_exists(filepath: str = None, **kwargs) -> bool:
    target = filepath or kwargs.get("path") or kwargs.get("file_name") or kwargs.get("filename") or kwargs.get("file")
    if not target:
        return True
    return os.path.isfile(os.path.abspath(target))

def verify_file_deleted(filepath: str = None, **kwargs) -> bool:
    target = filepath or kwargs.get("path") or kwargs.get("file_name") or kwargs.get("filename") or kwargs.get("file")
    if not target:
        return True
    return not os.path.exists(os.path.abspath(target))

# --- Tool Implementations ---

@registry.register(
    name="create_folder",
    description="Creates a new folder at the specified directory path.",
    risk_level="MODERATE",
    required_permission="filesystem-write",
    verify_method=verify_folder_exists
)
def create_folder(path: str = None, **kwargs) -> str:
    target = path or kwargs.get("folder_name") or kwargs.get("name") or kwargs.get("directory") or kwargs.get("dir") or kwargs.get("folder") or kwargs.get("folder_path") or "."
    resolved_path = os.path.abspath(target)
    if os.path.exists(resolved_path):
        return f"Folder already exists at: '{resolved_path}'"
    try:
        os.makedirs(resolved_path, exist_ok=True)
        return f"Folder created successfully at: '{resolved_path}'"
    except Exception as e:
        return f"Failed to create folder: {e}"

@registry.register(
    name="create_file",
    description="Creates an empty text file or a text file with initial content.",
    risk_level="MODERATE",
    required_permission="filesystem-write",
    verify_method=verify_file_exists
)
def create_file(filepath: str = None, content: str = "", **kwargs) -> str:
    target = filepath or kwargs.get("path") or kwargs.get("file_name") or kwargs.get("filename") or kwargs.get("file") or "file.txt"
    body = content or kwargs.get("text") or kwargs.get("data") or kwargs.get("file_content") or ""
    resolved_path = os.path.abspath(target)
    try:
        parent = os.path.dirname(resolved_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(resolved_path, "w", encoding="utf-8") as f:
            f.write(body)
        return f"File created successfully at: '{resolved_path}'"
    except Exception as e:
        return f"Failed to create file: {e}"

@registry.register(
    name="read_file",
    description="Reads and returns the text contents of a file.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=verify_file_exists
)
def read_file(filepath: str = None, **kwargs) -> str:
    target = filepath or kwargs.get("path") or kwargs.get("file_name") or kwargs.get("filename") or kwargs.get("file")
    if not target:
        return "Error: File path was not specified."
    resolved_path = os.path.abspath(target)
    if not os.path.exists(resolved_path):
        return f"File not found: '{target}'"
    try:
        with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read(8000)
            if len(data) >= 8000:
                data += "\n...[Content truncated due to size limit]"
            return f"Content of '{resolved_path}':\n\n{data}"
    except Exception as e:
        return f"Failed to read file: {e}"

@registry.register(
    name="write_file",
    description="Writes content to a file, completely replacing its existing content.",
    risk_level="MODERATE",
    required_permission="filesystem-write",
    verify_method=verify_file_exists
)
def write_file(filepath: str = None, content: str = "", **kwargs) -> str:
    target = filepath or kwargs.get("path") or kwargs.get("file_name") or kwargs.get("filename") or kwargs.get("file") or "file.txt"
    body = content or kwargs.get("text") or kwargs.get("data") or kwargs.get("file_content") or ""
    resolved_path = os.path.abspath(target)
    try:
        parent = os.path.dirname(resolved_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(resolved_path, "w", encoding="utf-8") as f:
            f.write(body)
        return f"Successfully wrote content to file: '{resolved_path}'"
    except Exception as e:
        return f"Failed to write file: {e}"

@registry.register(
    name="list_directory",
    description="Lists files and subdirectories inside the specified folder path.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=verify_folder_exists
)
def list_directory(path: str = ".", **kwargs) -> str:
    target = path or kwargs.get("folder") or kwargs.get("directory") or kwargs.get("dir") or kwargs.get("folder_path") or "."
    resolved_path = os.path.abspath(target)
    if not os.path.exists(resolved_path):
        return f"Folder not found: '{target}'"
    try:
        entries = os.listdir(resolved_path)
        if not entries:
            return f"Directory '{resolved_path}' is empty."
        
        items = []
        for entry in entries:
            full_item = os.path.join(resolved_path, entry)
            is_dir = os.path.isdir(full_item)
            type_label = "[DIR]" if is_dir else "[FILE]"
            size = os.path.getsize(full_item) if not is_dir else "-"
            items.append(f"{type_label:<7} {entry:<30} {str(size):>10} bytes")
        
        return f"Listing for: '{resolved_path}'\n\n" + "\n".join(items)
    except Exception as e:
        return f"Failed to list directory: {e}"

@registry.register(
    name="delete_file",
    description="Permanently deletes a file from the filesystem.",
    risk_level="DANGEROUS",
    required_permission="destructive",
    verify_method=verify_file_deleted
)
def delete_file(filepath: str = None, **kwargs) -> str:
    target = filepath or kwargs.get("path") or kwargs.get("file_name") or kwargs.get("filename") or kwargs.get("file")
    if not target:
        return "Error: File path was not specified."
    resolved_path = os.path.abspath(target)
    if not os.path.exists(resolved_path):
        return f"File does not exist: '{target}'"
    try:
        os.remove(resolved_path)
        return f"File permanently deleted: '{resolved_path}'"
    except Exception as e:
        return f"Failed to delete file: {e}"

@registry.register(
    name="search_files",
    description="Searches for files matching a wildcard pattern in a directory.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def search_files(pattern: str = "*", path: str = ".", **kwargs) -> str:
    pat = pattern or kwargs.get("query") or kwargs.get("keyword") or kwargs.get("name") or "*"
    root = path or kwargs.get("directory") or kwargs.get("dir") or "."
    resolved_path = os.path.abspath(root)
    
    search_query = os.path.join(resolved_path, "**", pat)
    try:
        matches = glob.glob(search_query, recursive=True)
        if not matches:
            return f"No files matching pattern '{pat}' found in '{resolved_path}'."
        return f"Found {len(matches)} matches for '{pat}':\n\n" + "\n".join(matches[:50])
    except Exception as e:
        return f"Search error: {e}"
