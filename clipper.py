import os
import re
import shutil
import subprocess
import psutil
from pathlib import Path
from storage import OUTPUT_DIR, TEMP_DIR, sanitize_filename

def find_ffmpeg() -> str | None:
    """Locate ffmpeg even if this process inherited a stale PATH."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe

    candidates = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        winget = Path(local) / "Microsoft" / "WinGet" / "Packages"
        candidates.extend(sorted(winget.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe")))
    candidates.extend([
        Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"),
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
    ])
    for candidate in candidates:
        if Path(candidate).is_file():
            return str(candidate)
    return None

FFMPEG = find_ffmpeg()

def find_ffprobe() -> str | None:
    if FFMPEG:
        candidate = Path(FFMPEG).with_name("ffprobe.exe")
        if candidate.is_file():
            return str(candidate)
    return shutil.which("ffprobe")

FFPROBE = find_ffprobe()

def has_audio(path: Path) -> bool | None:
    """Return True/False if the file has an audio stream, None if it can't be checked."""
    try:
        result = subprocess.run(
            [FFPROBE or "ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return bool(result.stdout.strip())

def check_ffmpeg():
    try:
        result = subprocess.run([FFMPEG or "ffmpeg", "-version"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False

def parse_time(t_str: str) -> int:
    t_str = t_str.strip()
    if not re.match(r'^(\d+:)?(\d+:)?\d+$', t_str):
        raise ValueError(f"Invalid timestamp format: '{t_str}'")
    
    parts = t_str.split(':')
    if len(parts) == 1:
        return int(parts[0])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    raise ValueError("Invalid timestamp structure.")

def format_time_file(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}-{m:02d}-{s:02d}"

def validate_clips(clips_data: list, max_duration: int) -> list:
    valid = []
    for c in clips_data:
        start_sec = parse_time(c['start'])
        end_sec = parse_time(c['end'])
        
        if start_sec < 0 or end_sec < 0:
            raise ValueError("Timestamps cannot be negative.")
        if start_sec >= end_sec:
            raise ValueError(f"Start time ({start_sec}s) must be before end time ({end_sec}s).")
        if max_duration and end_sec > max_duration:
            raise ValueError(f"End time ({end_sec}s) exceeds video duration ({max_duration}s).")
            
        valid.append({
            'original': c,
            'start_sec': start_sec,
            'end_sec': end_sec,
            'duration_sec': end_sec - start_sec
        })
    return valid

def process_clip(input_path: Path, clip_info: dict, index: int, mode: str, preset: str, crf: int, max_res: int,
                 cancel_event=None) -> Path:
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Processing was cancelled by the user.")

    start = clip_info['start_sec']
    duration = clip_info['duration_sec']

    is_reel = str(clip_info['original'].get('format', 'video')).lower() == 'reel'
    tag = "_reel" if is_reel else ""

    custom_name = clip_info['original'].get('name', '').strip()
    if custom_name:
        filename = f"{sanitize_filename(custom_name)}{tag}.mp4"
    else:
        ts_start = format_time_file(start)
        ts_end = format_time_file(clip_info['end_sec'])
        filename = f"clip_{index:03d}_{ts_start}_to_{ts_end}{tag}.mp4"
        
    output_path = OUTPUT_DIR / filename
    
    counter = 1
    while output_path.exists():
        output_path = OUTPUT_DIR / f"{Path(filename).stem}_{counter}.mp4"
        counter += 1

    cmd = [FFMPEG or "ffmpeg", "-y", "-v", "error", "-ss", str(start), "-i", str(input_path), "-t", str(duration)]

    if is_reel:
        # 1080x1920 vertical: full frame centred over a blurred, zoomed copy of itself.
        # Reels always need a re-encode, even when "Fast Cut" is selected.
        cmd.extend([
            "-filter_complex",
            "[0:v]split=2[bg][fg];"
            "[bg]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,"
            "gblur=sigma=14,scale=1080:1920,setsar=1[bgv];"
            "[fg]scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,"
            "setsar=1[fgo];"
            "[bgv][fgo]overlay=(W-w)/2:(H-h)/2[vout]",
            "-map", "[vout]", "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", str(crf),
            "-c:a", "aac",
            "-b:a", "192k",
        ])
    else:
        cmd.extend(["-map", "0:v:0", "-map", "0:a:0?"])
        if mode == "Fast Cut":
            cmd.extend(["-c", "copy"])
        else:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", str(crf),
                "-vf", f"scale=-2:'min({max_res},ih)'",
                "-c:a", "aac",
                "-b:a", "192k"
            ])
        
    cmd.append(str(output_path))
    
    pid_file = TEMP_DIR / "current_pid.txt"
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    with open(pid_file, "w") as f:
        f.write(str(process.pid))

    if cancel_event is not None and cancel_event.is_set():
        process.terminate()

    _, stderr = process.communicate()
    
    if pid_file.exists():
        pid_file.unlink()
        
    if process.returncode != 0:
        output_path.unlink(missing_ok=True)
        if (cancel_event is not None and cancel_event.is_set()) or process.returncode in (-15, 15, -9):
            raise InterruptedError("Processing was cancelled by the user.")
        raise RuntimeError(f"FFmpeg Error: {stderr.strip()}")
        
    return output_path

def cancel_active_process():
    pid_file = TEMP_DIR / "current_pid.txt"
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            psutil.Process(pid).terminate()
        except Exception:
            pass
        finally:
            pid_file.unlink(missing_ok=True)
