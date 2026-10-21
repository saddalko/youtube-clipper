import yt_dlp
from pathlib import Path
from storage import DOWNLOADS_DIR, sanitize_filename

def get_video_info(url: str) -> dict:
    """Fetches video metadata without downloading."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        # YouTube needs a JS runtime to solve signature/n-sig challenges.
        'js_runtimes': {'deno': {}, 'node': {}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def download_video(url: str, max_res: int, progress_hook=None, cancel_event=None) -> Path:
    """Downloads the best available video strictly up to max_res, prioritizing MP4."""
    format_str = f"bestvideo[height<={max_res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_res}][ext=mp4]/best[height<={max_res}]/best"
    
    def internal_hook(d):
        if cancel_event is not None and cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("Cancelled by user.")
        if progress_hook and d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0%').strip('\x1b[0;39m').strip('%')
            try:
                progress_hook(float(percent_str) / 100.0)
            except ValueError:
                pass

    ydl_opts = {
        'format': format_str,
        'merge_output_format': 'mp4',
        'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [internal_hook],
        # YouTube needs a JS runtime to solve signature/n-sig challenges.
        'js_runtimes': {'deno': {}, 'node': {}},
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return Path(ydl.prepare_filename(info)).with_suffix('.mp4')
    except yt_dlp.utils.DownloadCancelled:
        raise InterruptedError("Download was cancelled by the user.")
