import shutil
import subprocess
from pathlib import Path
import pytest
from clipper import parse_time, validate_clips, process_clip, has_audio, FFPROBE
from storage import init_dirs, TEMP_DIR, sanitize_filename, delete_file

DUMMY_VIDEO = TEMP_DIR / "dummy_test.mp4"
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

def setup_module(module):
    init_dirs()
    if FFMPEG_AVAILABLE and not DUMMY_VIDEO.exists():
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=640x360:rate=30", "-c:v", "libx264", str(DUMMY_VIDEO)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def test_parse_time():
    assert parse_time("10") == 10
    assert parse_time("01:20") == 80
    with pytest.raises(ValueError):
        parse_time("invalid")

def test_validate_clips():
    clips = [{'start': '00:01', 'end': '00:03', 'name': ''}]
    valid = validate_clips(clips, max_duration=5)
    assert len(valid) == 1
    assert valid[0]['duration_sec'] == 2

def test_sanitize_filename():
    assert sanitize_filename("") == "clip"
    assert sanitize_filename("My Clip: Part 1!") == "My_Clip__Part_1"
    assert sanitize_filename("__already_safe__") == "already_safe"

def test_delete_file_retries_when_locked(monkeypatch, tmp_path):
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"x")
    real_unlink = Path.unlink
    calls = {"n": 0}

    def flaky_unlink(self, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise PermissionError(32, "in use", str(self))
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    assert delete_file(target, attempts=5, delay=0.01) is True
    assert not target.exists()

def test_delete_file_reports_still_locked(monkeypatch, tmp_path):
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"x")

    def locked_unlink(self, *args, **kwargs):
        raise PermissionError(32, "in use", str(self))

    monkeypatch.setattr(Path, "unlink", locked_unlink)
    assert delete_file(target, attempts=2, delay=0.01) is False

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg is not installed")
def test_ffmpeg_precise_cut():
    clip_info = {'original': {'name': 'test'}, 'start_sec': 1, 'end_sec': 3, 'duration_sec': 2}
    out = process_clip(DUMMY_VIDEO, clip_info, 1, "Precise Cut", "veryfast", 18, 1080)
    assert out.exists()
    out.unlink()

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg is not installed")
def test_process_clip_keeps_audio(tmp_path):
    source = tmp_path / "av_source.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-c:v", "libx264", "-c:a", "aac", "-shortest", str(source)], check=True)

    clip = {'original': {'name': 'audio_test'}, 'start_sec': 0, 'end_sec': 2, 'duration_sec': 2}
    out = process_clip(source, clip, 1, "Precise Cut", "veryfast", 18, 480)
    try:
        assert has_audio(out) is True
    finally:
        out.unlink(missing_ok=True)

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg is not installed")
def test_has_audio_detects_video_only():
    assert has_audio(DUMMY_VIDEO) is False

@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg is not installed")
def test_reel_output_is_vertical_with_audio(tmp_path):
    source = tmp_path / "source_16x9.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", "testsrc2=duration=3:size=1280x720:rate=30",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(source)], check=True)

    clip = {'original': {'name': 'reel_test', 'format': 'reel'},
            'start_sec': 0, 'end_sec': 2, 'duration_sec': 2}
    # "Fast Cut" is ignored for reels: they must be re-encoded.
    out = process_clip(source, clip, 1, "Fast Cut", "veryfast", 23, 720)
    try:
        assert out.name == "reel_test_reel.mp4"
        probe = subprocess.run(
            [FFPROBE or "ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(out)],
            capture_output=True, text=True, check=True)
        assert probe.stdout.strip() == "1080,1920"
        assert has_audio(out) is True
    finally:
        out.unlink(missing_ok=True)
