# ✂️ Local YouTube Timestamp-to-Clip Generator

Cut precise clips from **YouTube videos** or **local files** — completely locally, CPU-only, with optional vertical **Reels** (1080×1920).

Works on **Windows 10/11** and **macOS** (Intel or Apple Silicon).

---

## Features

- **YouTube URL or local upload** (`mp4`, `mkv`, `avi`, `mov`)
- **Multiple clips per video** with start/end timestamps and optional custom names
- **Per-clip output type**
  - **Video** — original aspect ratio, respects *Max Resolution*
  - **Reel** — 1080×1920 vertical, full frame centered over a **blurred background**
- **Precise Cut** (re-encode, frame-accurate) or **Fast Cut** (stream copy, instant)
- **CPU presets** (`veryfast`, `fast`, `medium`) and adjustable **CRF** quality
- **Background processing** with a working **Cancel** button
- **Preview, download, delete** clips; build a **ZIP on demand**
- **Cleanup tools** and free-disk-space indicator
- 100% local: no accounts, no cloud, no API keys

---

## Requirements

| Component | Why it's needed | Windows | macOS |
|---|---|---|---|
| **Python 3.11+** (tested on 3.15) | Runs the app | `winget install --id Python.Python.3.13 -e` | `brew install python@3.13` |
| **FFmpeg 6+** (tested 9.0.2) | Cutting, encoding, merging | `winget install --id Gyan.FFmpeg -e` | `brew install ffmpeg` |
| **Deno 2.3+** (recommended) | yt-dlp solves YouTube JS challenges | `winget install --id DenoLand.Deno -e` | `brew install deno` |
| **Node.js 22+** (optional alternative) | Same as above | `winget install --id OpenJS.NodeJS.LTS -e` | `brew install node` |

- **Deno or Node is required** for reliable YouTube downloads. The app enables both automatically; Deno is used first.
- Homebrew (macOS), if not installed yet:
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
- After installing FFmpeg/Deno, **close and reopen your terminal** (or VS Code) so the new PATH is picked up.
- Allow a few GB of free disk space for downloads and clips.

---

## Windows Setup

### 1. Install the tools

Open **PowerShell** and run:

```powershell
winget install --id Gyan.FFmpeg -e
winget install --id DenoLand.Deno -e
```

Alternative if you use Chocolatey (run in an **Administrator** shell):

```powershell
choco install ffmpeg deno -y
```

Then **close and reopen** PowerShell.

### 2. Create the environment

```powershell
cd C:\path\to\youtube-clipper
py -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activation script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

> If the folder already contains `env\` with dependencies installed (as shipped), you can skip creating the environment and just run `pip install -r requirements.txt` to make sure everything is present.

### 3. Run

```powershell
.\run.bat
```

or directly:

```powershell
.\env\Scripts\python.exe -m streamlit run app.py
```

Open **http://127.0.0.1:8501**.

---

## macOS Setup

### 1. Install the tools

```bash
brew install ffmpeg deno
```

### 2. Create the environment

```bash
cd ~/path/to/youtube-clipper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> The bundled `env/` folder is a **Windows** virtual environment and will not work on macOS. Always create `.venv` as shown above. You can delete `env/` on macOS.

### 3. Run

```bash
chmod +x run.sh
./run.sh
```

or directly:

```bash
.venv/bin/python -m streamlit run app.py
```

Open **http://127.0.0.1:8501**.

---

## Verify the Installation

Run these and make sure each prints a version:

```powershell
# Windows
ffmpeg -version
ffprobe -version
deno --version
.\env\Scripts\python.exe -c "import streamlit, yt_dlp, psutil, yt_dlp_ejs; print('deps ok')"
```

```bash
# macOS
ffmpeg -version
ffprobe -version
deno --version
.venv/bin/python -c "import streamlit, yt_dlp, psutil, yt_dlp_ejs; print('deps ok')"
```

If any command is "not recognized" / "command not found", reopen the terminal.

---

## How to Use

### Section A — Source
- **YouTube URL**: paste a link and click **Fetch / Inspect Video**. The video downloads when you start processing.
- **Local Video File**: upload `mp4`, `mkv`, `avi`, or `mov`. Uploads are stored in `downloads/`.

### Section B — Clip Configuration
Each row has `Start`, `End`, `Name`, `Type`:

- Timestamps accept `SS`, `MM:SS`, or `HH:MM:SS` (e.g. `90`, `01:30`, `00:01:30`).
- **Type = Video** → keeps the original aspect ratio.
- **Type = Reel** → 1080×1920 vertical, full frame centered with a blurred background.
- Leave **Name** empty to get an automatic name like `clip_001_00-00-10_to_00-00-40.mp4`; Reels get a `_reel` suffix.
- Use **➕ Add Clip** / **Remove** for multiple clips.

### Section C — Processing
- **Max Resolution** (1080 / 720 / 480) applies to YouTube downloads and **Video** clips. Reels are always 1080×1920.
- **Cut Mode**
  - **Precise Cut** — re-encodes; exact start/end.
  - **Fast Cut** — stream copy; near-instant, but cuts at keyframes (start/end can be off by a second or two). **Reels always re-encode**, even in Fast Cut.
- **CPU Preset**
  - `veryfast` — recommended: fastest, quality at CRF 18 is effectively identical.
  - `fast` / `medium` — slower; only marginal size gains on some footage.
- **CRF Quality** — `18` = high quality. Use `20–22` for smaller files, `23–28` for much smaller.
- **Cancel Processing** stops the current download or FFmpeg encode.
- Processing runs in the background, so the page and Cancel button stay responsive.

### Section D — Results
- Preview each clip in the browser, download it, or delete it.
- **Prepare ZIP of all clips** builds one archive on demand (large clips take a moment).
- Files are written to `output/`.

---

## Running the Tests

```powershell
# Windows
.\env\Scripts\python.exe -m pytest tests -v
```

```bash
# macOS
.venv/bin/python -m pytest tests -v
```

Tests that need FFmpeg are skipped automatically when it is not installed.

---

## Project Structure

```
youtube-clipper/
├── app.py                  # Streamlit UI and page layout
├── downloader.py           # yt-dlp metadata + download (with cancel support)
├── clipper.py              # timestamps, validation, FFmpeg commands, Reels, audio check
├── processor.py            # background job runner (progress + cancel)
├── storage.py              # folders, disk space, ZIP creation, safe deletion
├── requirements.txt
├── run.bat                 # Windows launcher (refreshes PATH)
├── run.sh                  # macOS/Linux launcher
├── .streamlit/config.toml  # binds to 127.0.0.1:8501
├── tests/test_clipper.py
├── downloads/              # downloaded/uploaded sources
├── output/                 # finished clips
├── temp/                   # scratch files
└── logs/                   # Streamlit logs when launched by run.bat/run.sh
```

---

## Troubleshooting

### "⚠️ FFmpeg not found in PATH"
- Install FFmpeg (see above), then **fully close and reopen** the terminal / VS Code.
- Verify with `ffmpeg -version` in a fresh terminal.
- The app also searches common install locations (WinGet, Chocolatey, `C:\ffmpeg`, Homebrew), so a stale PATH is usually tolerated.
- On Windows, `run.bat` re-reads PATH from the registry before launching.

### No audio when playing a clip
- The audio track is normally present — verify a downloaded clip in **VLC (Windows)** or **QuickTime (macOS)**.
- If the player is the browser: right-click the tab → **Unmute site**; check the player's speaker icon; check the OS volume mixer.
- Reels keep the original audio track.

### `PermissionError: [WinError 32] ... being used by another process` when deleting
- Another program still has the file open (video player, Explorer preview pane, antivirus).
- Close the player / preview pane and click **Delete** again.
- The app retries automatically and will delete the file on the next interaction.

### YouTube download fails or says "Sign in to confirm you're not a bot"
- Update yt-dlp: `pip install -U yt-dlp yt-dlp-ejs`
- Make sure Deno or Node is installed and `deno --version` works.
- This app does not support browser cookies yet; as a workaround, download the video separately and use **Local Video File**.

### Download is very slow or stalls
- Update yt-dlp (YouTube changes frequently): `pip install -U yt-dlp`
- Check your network/VPN.
- `Cancel Processing` stops a download cleanly.

### Port 8501 is already in use
Run on another port:

```powershell
.\env\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

```bash
.venv/bin/python -m streamlit run app.py --server.port 8502
```

### `python`/`py` not recognized (Windows)
Reinstall Python and tick **"Add python.exe to PATH"**, or use the full path to `python.exe`. Reopen the terminal afterwards.

### macOS: "operation not permitted" when reading/writing
- Move the project into your home folder (e.g. `~/youtube-clipper`).
- Or grant **Terminal** / **VS Code** Full Disk Access in *System Settings → Privacy & Security*.

### Reel looks cropped / off-center
Reels use a **blurred background**: the full frame is centered and sharp, with a blurred copy filling the top and bottom. Nothing is cut off by default. If you prefer a center crop, that is a one-line filter change in `clipper.py`.

---

## Notes & Limitations

- **CPU-only** (libx264). GPU encoding is not used.
- Designed for **local, single-user** use; it binds to `127.0.0.1` only.
- **Fast Cut** is keyframe-based and cannot be frame-accurate; use **Precise Cut** for exact edits.
- **Reels** are always 1080×1920 and always re-encoded, because vertical framing requires a filter.
- Dependencies in `requirements.txt` are unpinned; if a future yt-dlp or Streamlit release breaks something, install a known-good version with `pip install "yt-dlp==<version>"`.
- `downloads/`, `output/`, `temp/`, and `logs/` are created automatically on first launch.
