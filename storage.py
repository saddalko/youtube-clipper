import os
import shutil
import time
import psutil
from pathlib import Path
import zipfile

# Base directories
BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"
DOWNLOADS_DIR = BASE_DIR / "downloads"
LOGS_DIR = BASE_DIR / "logs"

def init_dirs():
    """Create necessary application directories."""
    for d in [TEMP_DIR, OUTPUT_DIR, DOWNLOADS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def get_free_space_mb() -> float:
    """Returns free disk space on the drive where the app resides in MB."""
    return psutil.disk_usage(str(BASE_DIR)).free / (1024 * 1024)

def sanitize_filename(name: str) -> str:
    """Removes invalid Windows characters from filenames."""
    if not name:
        return "clip"
    safe_chars = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return safe_chars.strip("_")

def create_zip(clip_paths: list[Path], zip_name: str) -> Path:
    """Creates a ZIP archive of the specified paths."""
    zip_path = OUTPUT_DIR / zip_name
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in clip_paths:
            zf.write(path, arcname=path.name)
    return zip_path

def delete_file(path: Path, attempts: int = 6, delay: float = 0.25) -> bool:
    """Delete a file, retrying while another process holds a Windows lock.

    Returns True when the file is gone, False when it is still locked.
    """
    for _ in range(max(attempts, 1)):
        try:
            path.unlink(missing_ok=True)
            return True
        except PermissionError:
            time.sleep(delay)
        except OSError:
            return False
    return not path.exists()

def cleanup_temp_files() -> list[str]:
    """Deletes everything in the temp directory. Returns names that were locked."""
    return _cleanup_dir(TEMP_DIR)

def cleanup_directory(directory: Path) -> list[str]:
    """Deletes all files inside a target directory. Returns names that were locked."""
    return _cleanup_dir(directory)

def _cleanup_dir(directory: Path) -> list[str]:
    failed = []
    for item in directory.iterdir():
        try:
            if item.is_file():
                item.unlink(missing_ok=True)
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
        except PermissionError:
            failed.append(item.name)
    return failed
