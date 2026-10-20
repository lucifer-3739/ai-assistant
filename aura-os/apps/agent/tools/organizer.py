import os
import shutil
import hashlib
from typing import Dict, List, Any
from tools.base import registry

CATEGORY_MAP = {
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".md", ".rtf", ".odt"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff", ".psd"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg", ".wma"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".bz2"],
    "Code": [".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".cpp", ".c", ".h", ".java", ".rs", ".go", ".sql", ".sh"],
    "Executables": [".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs"]
}

@registry.register(
    name="organize_directory",
    description="Automatically categorizes and sorts unorganized files into organized subfolders (Documents, Images, Code, etc.).",
    risk_level="MODERATE",
    required_permission="filesystem-write",
    verify_method=None
)
def organize_directory(directory_path: str = ".", **kwargs) -> str:
    target = directory_path or kwargs.get("path") or kwargs.get("folder") or kwargs.get("dir") or "."
    resolved = os.path.abspath(target)
    
    if not os.path.exists(resolved) or not os.path.isdir(resolved):
        return f"Error: Directory '{target}' does not exist."
        
    stats: Dict[str, int] = {cat: 0 for cat in CATEGORY_MAP}
    stats["Other"] = 0
    moved_count = 0

    try:
        entries = os.listdir(resolved)
        for item in entries:
            item_path = os.path.join(resolved, item)
            
            # Skip directories (only organize top-level loose files)
            if os.path.isdir(item_path):
                continue
                
            ext = os.path.splitext(item)[1].lower()
            if not ext:
                continue

            # Determine category
            destination_cat = "Other"
            for cat, extensions in CATEGORY_MAP.items():
                if ext in extensions:
                    destination_cat = cat
                    break
                    
            cat_dir = os.path.join(resolved, destination_cat)
            os.makedirs(cat_dir, exist_ok=True)
            
            dest_file_path = os.path.join(cat_dir, item)
            # Avoid overwriting
            if not os.path.exists(dest_file_path):
                shutil.move(item_path, dest_file_path)
                stats[destination_cat] += 1
                moved_count += 1

        summary_lines = [f"Automated Organization Complete for '{resolved}':"]
        summary_lines.append(f"Total files categorized: {moved_count}\nBreakdown:")
        for cat, count in stats.items():
            if count > 0:
                summary_lines.append(f" - {cat}: {count} files")
                
        if moved_count == 0:
            return f"Directory '{resolved}' is already organized or contains no loose files."
            
        return "\n".join(summary_lines)
    except Exception as e:
        return f"File organization failed: {e}"

@registry.register(
    name="find_duplicate_files",
    description="Calculates SHA-256 hashes of files in a directory to identify identical duplicate files wasting disk space.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def find_duplicate_files(directory_path: str = ".", **kwargs) -> str:
    target = directory_path or kwargs.get("path") or kwargs.get("folder") or kwargs.get("dir") or "."
    resolved = os.path.abspath(target)
    
    if not os.path.exists(resolved) or not os.path.isdir(resolved):
        return f"Error: Directory '{target}' not found."
        
    hashes: Dict[str, List[str]] = {}
    
    def hash_file(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    try:
        for root, _, files in os.walk(resolved):
            for file in files:
                full_path = os.path.join(root, file)
                try:
                    if os.path.getsize(full_path) > 0:
                        file_hash = hash_file(full_path)
                        if file_hash in hashes:
                            hashes[file_hash].append(full_path)
                        else:
                            hashes[file_hash] = [full_path]
                except Exception:
                    continue

        duplicates = {k: v for k, v in hashes.items() if len(v) > 1}
        
        if not duplicates:
            return f"Duplicate Check Complete: No duplicate files found in '{resolved}'."
            
        result = [f"Found {len(duplicates)} sets of identical duplicate files in '{resolved}':\n"]
        for idx, (h, paths) in enumerate(duplicates.items(), 1):
            size_mb = round(os.path.getsize(paths[0]) / (1024 * 1024), 2)
            result.append(f"Set #{idx} (Size per file: {size_mb} MB):")
            for p in paths:
                result.append(f"  - {p}")
            result.append("")
            
        return "\n".join(result)
    except Exception as e:
        return f"Duplicate file check error: {e}"

@registry.register(
    name="get_directory_analytics",
    description="Provides deep analytics on a directory, including total size, item counts, and top 5 largest files.",
    risk_level="SAFE",
    required_permission="read-only",
    verify_method=None
)
def get_directory_analytics(directory_path: str = ".", **kwargs) -> str:
    target = directory_path or kwargs.get("path") or kwargs.get("folder") or kwargs.get("dir") or "."
    resolved = os.path.abspath(target)
    
    if not os.path.exists(resolved) or not os.path.isdir(resolved):
        return f"Error: Directory '{target}' not found."
        
    total_size = 0
    file_count = 0
    dir_count = 0
    all_files: List[tuple[str, int]] = []
    
    try:
        for root, dirs, files in os.walk(resolved):
            dir_count += len(dirs)
            for f in files:
                p = os.path.join(root, f)
                try:
                    s = os.path.getsize(p)
                    total_size += s
                    file_count += 1
                    all_files.append((p, s))
                except Exception:
                    continue

        all_files.sort(key=lambda x: x[1], reverse=True)
        size_mb = round(total_size / (1024 * 1024), 2)
        
        output = [
            f"Directory Storage Analytics for '{resolved}':",
            f" - Total Size: {size_mb} MB ({total_size:,} bytes)",
            f" - Total Files: {file_count:,}",
            f" - Total Subdirectories: {dir_count:,}",
            "\nTop 5 Largest Files:"
        ]
        
        for p, s in all_files[:5]:
            mb = round(s / (1024 * 1024), 2)
            output.append(f"  - {p} ({mb} MB)")
            
        return "\n".join(output)
    except Exception as e:
        return f"Directory analytics error: {e}"
