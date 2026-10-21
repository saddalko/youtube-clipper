# Local YouTube Timestamp-to-Clip Generator

A completely local, CPU-only web application that extracts video clips from YouTube URLs or local files based on precise timestamps.

## Prerequisites
1. **Windows 10/11 64-bit**.
2. **Python 3.11+** installed (this project was set up with Python 3.15).
3. **FFmpeg** installed and added to your System PATH.
   - *Verification:* Open PowerShell and type `ffmpeg -version`. If it returns a version number, you are ready.
   - *Install (Windows):* `winget install --id Gyan.FFmpeg -e`, then open a **new** terminal.
4. **A JavaScript runtime for yt-dlp** (used to solve YouTube signature challenges).
   - *Recommended:* Deno 2.3+ → `winget install --id DenoLand.Deno -e`
   - Node.js 22+ also works; the app enables both automatically via `js_runtimes`.
   - The `yt-dlp-ejs` solver package is installed by `pip install -r requirements.txt`.

## Setup Instructions
1. **Open Visual Studio Code** and load this project folder.
2. **Open a new Terminal** (PowerShell) in VS Code.
3. **Use the bundled environment** in `env/` (dependencies are already installed):
   `.\.env\Scripts\Activate.ps1`
4. **Install/update dependencies** (only needed if the environment is missing or broken):
   `pip install -r requirements.txt`

> If you prefer a fresh environment, create it with `python -m venv .venv`,
> activate it, and run `pip install -r requirements.txt`. Do not mix the two.

## Running the Application
Easiest: double-click **`run.bat`** (it refreshes PATH so newly installed tools like FFmpeg/Deno are always found).

Or launch manually with the bundled environment (no activation needed):
`.\.env\Scripts\python.exe -m streamlit run app.py`

Then open http://127.0.0.1:8501 in your browser.

> If a terminal was opened before FFmpeg/Deno was installed, it has a stale PATH.
> Restart VS Code entirely, or just use `run.bat`.

## How It Works
- **Section A** loads a YouTube URL (downloaded with yt-dlp) or a local upload.
- **Section B** defines one or more clips (`start`, `end`, optional name) and a per-clip type:
  **Video** (original aspect ratio, respects Max Resolution) or **Reel** (1080×1920 vertical,
  full frame over a blurred background — always re-encoded, even in Fast Cut mode).
- **Section C** runs the job in a background thread, so the **Cancel** button can stop a download or an FFmpeg encode mid-flight.
- **Section D** previews and downloads the finished `.mp4` files from `output/`.

## Running Automated Tests
To verify everything works correctly locally without hitting YouTube:
`.\env\Scripts\python.exe -m pytest tests/test_clipper.py -v`

Tests that need FFmpeg are skipped automatically when it is not installed.
