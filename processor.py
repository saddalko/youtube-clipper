"""Runs download + clipping in a background thread.

Streamlit executes the app script synchronously, so a long FFmpeg loop would
block the page and make the Cancel button unreachable. Running the work in a
daemon thread lets the UI keep polling and lets Cancel actually terminate the
current FFmpeg process.
"""

import threading
import time

from clipper import cancel_active_process, process_clip
from downloader import download_video
from storage import cleanup_temp_files


class ClipJob:
    def __init__(self):
        self.cancel_event = threading.Event()
        self.thread = None
        self.status = "idle"  # idle | downloading | processing | done | cancelled | error
        self.message = ""
        self.progress = 0.0
        self.error = None
        self.source_path = None
        self.elapsed = 0.0

    @property
    def running(self) -> bool:
        return self.status in ("downloading", "processing")


_job = ClipJob()


def get_job() -> ClipJob:
    return _job


def start_job(video_info, source_path, valid_clips, max_res, cut_mode, preset, crf) -> bool:
    """Start processing in the background. Returns False if a job is already running."""
    global _job
    if _job.running:
        return False

    job = ClipJob()
    job.source_path = source_path
    job.status = "downloading" if (not source_path and video_info.get("url")) else "processing"
    job.message = "Downloading source..." if job.status == "downloading" else "Starting..."
    _job = job

    def runner():
        started = time.time()
        try:
            src = source_path
            if not src and video_info.get("url"):
                def on_progress(pct):
                    job.progress = max(0.0, min(pct, 1.0)) * 0.4  # download = first 40%
                    job.message = f"Downloading source... {pct * 100:.0f}%"

                src = download_video(video_info["url"], max_res, on_progress, job.cancel_event)
                job.source_path = src
                job.progress = 0.4

            job.status = "processing"
            total = len(valid_clips)
            for i, clip in enumerate(valid_clips):
                if job.cancel_event.is_set():
                    raise InterruptedError("Processing was cancelled by the user.")
                job.message = f"Encoding clip {i + 1} of {total}..."
                process_clip(src, clip, i + 1, cut_mode, preset, crf, max_res, job.cancel_event)
                job.progress = 0.4 + 0.6 * ((i + 1) / max(total, 1))

            cleanup_temp_files()
            job.status = "done"
            job.message = f"Finished {total} clip(s)."
            job.progress = 1.0
        except InterruptedError:
            job.status = "cancelled"
            job.message = "Processing was cancelled."
        except Exception as e:
            job.status = "error"
            job.error = str(e)
            job.message = f"Error: {e}"
        finally:
            job.elapsed = time.time() - started

    job.thread = threading.Thread(target=runner, daemon=True)
    job.thread.start()
    return True


def cancel_job():
    """Signal cancellation and kill the FFmpeg process that is currently running."""
    _job.cancel_event.set()
    cancel_active_process()
