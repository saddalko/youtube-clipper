import streamlit as st
from datetime import datetime
from pathlib import Path
from storage import init_dirs, get_free_space_mb, DOWNLOADS_DIR, OUTPUT_DIR, cleanup_temp_files, create_zip, cleanup_directory, delete_file
from downloader import get_video_info
from clipper import check_ffmpeg, validate_clips, has_audio
from processor import get_job, start_job, cancel_job

st.set_page_config(page_title="Local YouTube Clipper", layout="wide")
init_dirs()

if 'clips_config' not in st.session_state:
    st.session_state.clips_config = [{'id': 1, 'start': '00:00', 'end': '00:10', 'name': '', 'format': 'video'}]
if 'video_info' not in st.session_state:
    st.session_state.video_info = None
if 'source_path' not in st.session_state:
    st.session_state.source_path = None
if 'pending_delete' not in st.session_state:
    st.session_state.pending_delete = set()
if 'zip_path' not in st.session_state:
    st.session_state.zip_path = None
if 'zip_sig' not in st.session_state:
    st.session_state.zip_sig = None

def add_clip():
    next_id = max([c['id'] for c in st.session_state.clips_config] + [0]) + 1
    st.session_state.clips_config.append({'id': next_id, 'start': '', 'end': '', 'name': '', 'format': 'video'})

def remove_clip(clip_id):
    st.session_state.clips_config = [c for c in st.session_state.clips_config if c['id'] != clip_id]

with st.sidebar:
    st.header("System & Storage")
    if not check_ffmpeg(): st.error("⚠️ FFmpeg not found in PATH!")
    else: st.success("✅ FFmpeg available.")
    st.write(f"**Free Disk Space:** {get_free_space_mb():,.0f} MB")
    
    st.markdown("---")
    st.subheader("Cleanup Tools")
    if st.button("Clear Temporary Files"):
        failed = cleanup_temp_files()
        if failed:
            st.warning(f"Still in use: {', '.join(failed)}")
        else:
            st.success("Temp files cleared.")
    if st.button("Clear Downloaded Sources"):
        failed = cleanup_directory(DOWNLOADS_DIR)
        if failed:
            st.warning(f"Still in use: {', '.join(failed)}")
        else:
            st.success("Downloads cleared.")
        st.session_state.video_info = None
        st.session_state.source_path = None
    if st.button("Clear Output Clips"):
        failed = cleanup_directory(OUTPUT_DIR)
        st.session_state.pending_delete.clear()
        st.session_state.zip_path = None
        st.session_state.zip_sig = None
        if failed:
            st.warning(f"Still in use: {', '.join(failed)}")
        else:
            st.success("Outputs cleared.")

st.title("✂️ Local Video Clipper (CPU Only)")

st.header("Section A: Source Video")
source_type = st.radio("Select Source Type", ["YouTube URL", "Local Video File"])

if source_type == "YouTube URL":
    url_input = st.text_input("Enter YouTube URL:")
    if st.button("Fetch / Inspect Video"):
        if url_input:
            with st.spinner("Fetching video info..."):
                try:
                    info = get_video_info(url_input)
                    st.session_state.video_info = {'title': info.get('title', 'Unknown Title'), 'duration': info.get('duration', 0), 'url': url_input}
                    st.success(f"Loaded: {st.session_state.video_info['title']}")
                except Exception as e:
                    st.error(f"Failed: {str(e)}")
else:
    uploaded_file = st.file_uploader("Upload local video file", type=["mp4", "mkv", "avi", "mov"])
    if uploaded_file:
        file_path = DOWNLOADS_DIR / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.source_path = file_path
        st.session_state.video_info = {'title': uploaded_file.name, 'duration': None, 'url': None}
        st.success("Loaded local file.")

st.header("Section B: Clip Configuration")
for i, clip in enumerate(st.session_state.clips_config):
    clip.setdefault('format', 'video')
    cols = st.columns([2, 2, 3, 2, 1])
    clip['start'] = cols[0].text_input("Start", value=clip['start'], key=f"start_{clip['id']}", label_visibility="collapsed", placeholder="00:00")
    clip['end'] = cols[1].text_input("End", value=clip['end'], key=f"end_{clip['id']}", label_visibility="collapsed", placeholder="00:10")
    clip['name'] = cols[2].text_input("Name", value=clip['name'], key=f"name_{clip['id']}", label_visibility="collapsed", placeholder="Custom Name")
    clip['format'] = cols[3].selectbox(
        "Type", ["Video", "Reel"],
        index=0 if clip['format'] == 'video' else 1,
        key=f"fmt_{clip['id']}",
        label_visibility="collapsed",
        help="Video = original ratio. Reel = 1080x1920 vertical with a blurred background (always re-encoded).",
    ).lower()
    if cols[4].button("Remove", key=f"del_{clip['id']}"):
        remove_clip(clip['id'])
        st.rerun()

st.caption("Video = original aspect ratio · Reel = 1080×1920 vertical, full frame over a blurred background.")

st.button("➕ Add Clip", on_click=add_clip)

p_cols = st.columns(4)
max_res = p_cols[0].selectbox("Max Resolution", [1080, 720, 480], index=0)
cut_mode = p_cols[1].radio("Cut Mode", ["Precise Cut", "Fast Cut"], index=0)
preset_opts = p_cols[2].selectbox("CPU Preset", ["veryfast", "fast", "medium"], index=0)
crf_val = p_cols[3].number_input("CRF Quality", min_value=0, max_value=51, value=18)

st.header("Section C: Processing")

@st.fragment(run_every="1s")
def render_job_progress():
    current = get_job()
    st.progress(max(0.0, min(current.progress, 1.0)), text=current.message or "Working...")
    if current.running:
        if st.button("⏹️ Cancel Processing", key="cancel_job"):
            cancel_job()
            st.warning("Cancelling...")
        return
    if current.source_path:
        st.session_state.source_path = current.source_path
    st.rerun(scope="app")

job = get_job()

if job.running:
    render_job_progress()
else:
    if job.status == "done":
        st.success(f"Finished in {job.elapsed:.1f}s. {job.message}")
    elif job.status == "cancelled":
        st.warning(job.message)
    elif job.status == "error":
        st.error(job.message)

    if st.button("▶️ Start Processing", type="primary"):
        if not st.session_state.video_info:
            st.error("Please provide a video source.")
        else:
            try:
                valid_clips = validate_clips(st.session_state.clips_config, st.session_state.video_info.get('duration'))
            except Exception as e:
                st.error(f"Error: {str(e)}")
            else:
                if start_job(st.session_state.video_info, st.session_state.source_path,
                             valid_clips, max_res, cut_mode, preset_opts, crf_val):
                    st.rerun()
                else:
                    st.warning("A job is already running.")

st.header("Section D: Results")

# Deletions queued on the previous run are retried now that the preview is gone.
if st.session_state.pending_delete:
    for name in list(st.session_state.pending_delete):
        if delete_file(OUTPUT_DIR / name):
            st.session_state.pending_delete.discard(name)
    if st.session_state.pending_delete:
        st.warning(
            "Windows is still using "
            + ", ".join(sorted(st.session_state.pending_delete))
            + ". Close any video player or Explorer preview, then click Delete again."
        )

output_files = [
    f for f in OUTPUT_DIR.iterdir()
    if f.is_file() and f.suffix == '.mp4' and f.name not in st.session_state.pending_delete
]
if output_files:
    if len(output_files) > 1:
        sig = tuple(sorted((f.name, f.stat().st_size) for f in output_files))
        if st.session_state.zip_sig != sig:
            # Clips changed: the cached ZIP is stale.
            if st.session_state.zip_path:
                delete_file(Path(st.session_state.zip_path))
            st.session_state.zip_path = None
            st.session_state.zip_sig = sig
        if st.button("📦 Prepare ZIP of all clips", key="make_zip"):
            with st.spinner("Building ZIP..."):
                zip_path = create_zip(output_files, f"clips_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.zip")
            st.session_state.zip_path = str(zip_path)
        if st.session_state.zip_path and Path(st.session_state.zip_path).exists():
            zip_path = Path(st.session_state.zip_path)
            st.download_button(
                "⬇️ Download ZIP",
                data=lambda: zip_path.read_bytes(),
                file_name=zip_path.name,
                mime="application/zip",
                key="download_zip",
            )
    st.markdown("---")
    for file in output_files:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.video(str(file))
            st.caption(f"**{file.name}** | Size: {file.stat().st_size / (1024 * 1024):.2f} MB")
            if has_audio(file) is False:
                st.warning("🔇 This clip has no audio track — the source video itself has no audio.")
        with col2:
            with open(file, "rb") as f:
                st.download_button("⬇️ Download", data=f, file_name=file.name, mime="video/mp4", key=f"dl_{file.name}")
            if st.button("🗑️ Delete", key=f"rm_{file.name}"):
                st.session_state.pending_delete.add(file.name)
                st.rerun()
else:
    st.info("No clips available.")
