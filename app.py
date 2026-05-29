"""
app.py
TrackSplitter — AI-powered audio stem separator.
Industrial pro-audio aesthetic. Powered by Demucs (Meta AI Research).
"""

import os
import math
import time
import tempfile
import zipfile
import io as _io
import streamlit as st
from pathlib import Path
from separator import MODELS, detect_device, separate_audio, get_stem_info, cleanup, mix_stems
from mixer_component import render_mixer

# ─────────────────────────────────────────
# Page config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="TrackSplitter",
    page_icon="assets/icon.png" if Path("assets/icon.png").exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────
# CSS — industrial pro-audio aesthetic
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Barlow+Condensed:wght@300;400;600;700;900&display=swap');

:root {
  --bg:       #0A0A0A;
  --surface:  #0F0F0F;
  --card:     #141414;
  --border:   #222222;
  --border2:  #2A2A2A;
  --amber:    #E8A838;
  --green:    #4ADE80;
  --blue:     #38BDF8;
  --text:     #D4D4D4;
  --muted:    #525252;
  --faint:    #2A2A2A;
}

/* ── Reset & base ── */
html, body, [class*="css"] {
  font-family: 'IBM Plex Mono', monospace !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header, .stDeployButton { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── Header ── */
.ts-header {
  padding: 2.5rem 0 2rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2.5rem;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}
.ts-wordmark {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 3.2rem;
  font-weight: 900;
  letter-spacing: -1px;
  color: var(--text);
  line-height: 1;
  text-transform: uppercase;
}
.ts-wordmark span { color: var(--amber); }
.ts-sub {
  font-size: 9px;
  letter-spacing: 4px;
  color: var(--muted);
  text-transform: uppercase;
  margin-top: 6px;
}
.ts-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--muted);
  text-transform: uppercase;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 2px;
}
.ts-badge-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--green);
  animation: signal 2s infinite;
}
.ts-badge-dot.cpu { background: var(--muted); animation: none; }
@keyframes signal { 0%,100%{opacity:1} 50%{opacity:0.2} }

/* ── Section labels ── */
.ts-label {
  font-size: 9px;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

/* ── Panels ── */
.ts-panel {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 1.4rem;
  margin-bottom: 1rem;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
  background: var(--card) !important;
  border-color: var(--border2) !important;
  border-radius: 2px !important;
  color: var(--text) !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 12px !important;
}
.stSelectbox label {
  font-size: 9px !important;
  letter-spacing: 3px !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
  font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Model description box ── */
.model-desc {
  margin-top: 10px;
  padding: 10px 14px;
  border-left: 2px solid var(--amber);
  background: var(--surface);
  font-size: 11px;
  color: var(--muted);
  line-height: 1.7;
}
.model-desc strong { color: var(--text); }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--card) !important;
  border: 1px dashed var(--border2) !important;
  border-radius: 2px !important;
}
[data-testid="stFileUploader"] label {
  font-size: 9px !important;
  letter-spacing: 3px !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
  font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Primary button ── */
.stButton > button {
  background: var(--amber) !important;
  color: #0A0A0A !important;
  border: none !important;
  border-radius: 2px !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 3px !important;
  text-transform: uppercase !important;
  padding: 0.65rem 2rem !important;
  transition: opacity 0.15s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
  background: transparent !important;
  color: var(--muted) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 2px !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 10px !important;
  letter-spacing: 3px !important;
  text-transform: uppercase !important;
  padding: 0.6rem 1.5rem !important;
  transition: all 0.15s !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--amber) !important;
  color: var(--amber) !important;
}

/* ── Progress bar ── */
.stProgress > div > div > div {
  background: var(--amber) !important;
}
[data-testid="stProgressBar"] > div {
  background: var(--border) !important;
  border-radius: 1px !important;
}

/* ── Alerts ── */
.stAlert {
  background: var(--card) !important;
  border-color: var(--border2) !important;
  border-radius: 2px !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 11px !important;
}

/* ── Spec table ── */
.spec-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  margin-top: 12px;
}
.spec-cell {
  background: var(--card);
  padding: 8px 12px;
}
.spec-key {
  font-size: 9px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 3px;
}
.spec-val {
  font-size: 12px;
  color: var(--text);
}
.spec-val.amber { color: var(--amber); }
.spec-val.green { color: var(--green); }

/* ── Empty state ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  border: 1px solid var(--border);
  border-radius: 2px;
  background: var(--card);
}
.empty-waveform {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-bottom: 20px;
}
.empty-bar {
  width: 3px;
  border-radius: 1px;
  background: var(--border2);
}
.empty-label {
  font-size: 9px;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--faint);
}

/* ── Mix export controls ── */
.mix-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  margin-bottom: 4px;
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 2px solid var(--ch-color, var(--border));
  border-radius: 2px;
}
.mix-row-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  min-width: 70px;
  color: var(--ch-color);
}
.mix-row .stSlider { flex: 1; }
.mix-row .stSlider [data-testid="stThumbValue"] { display: none; }
.mix-row-mute {
  width: 28px; height: 28px;
  border-radius: 2px;
  border: 1px solid var(--border2);
  background: var(--card);
  color: var(--muted);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9px; font-weight: 600;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.mix-row-mute.active {
  background: var(--border2);
  color: var(--text);
}

/* ── Footer ── */
.ts-footer {
  border-top: 1px solid var(--border);
  padding: 1.2rem 0;
  margin-top: 2rem;
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #333333;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# Session state
# ─────────────────────────────────────────
for key, default in {
    "stem_paths": {},
    "output_dir": None,
    "processed_file": None,
    "session_ts": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────
# Header
# ─────────────────────────────────────────
device_type, device_name = detect_device()
dot_class = "ts-badge-dot" if device_type == "cuda" else "ts-badge-dot cpu"

st.markdown(f"""
<div class="ts-header">
  <div>
    <div class="ts-wordmark">Track<span>Splitter</span></div>
    <div class="ts-sub">AI-powered audio stem separator &nbsp;/&nbsp; Demucs v4</div>
  </div>
  <div class="ts-badge">
    <div class="{dot_class}"></div>
    {device_name}
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# Layout
# ─────────────────────────────────────────
col_ctrl, col_mixer = st.columns([1, 1.65], gap="large")


# ─── Left column: controls ───────────────
with col_ctrl:

    # Model selector
    st.markdown('<div class="ts-label">Model</div>', unsafe_allow_html=True)
    model_display = st.selectbox(
        "Model",
        list(MODELS.keys()),
        index=0,
        label_visibility="collapsed",
    )
    model_key = MODELS[model_display]

    model_desc = {
        "htdemucs_6s": "<strong>6 stems</strong> — Vocals · Drums · Bass · Guitar · Piano · Other<br>Best for full-spectrum analysis.",
        "htdemucs_ft": "<strong>4 stems</strong> — Vocals · Drums · Bass · Other<br>Fine-tuned per instrument. Highest quality separation.",
    }
    st.markdown(
        f'<div class="model-desc">{model_desc[model_key]}</div>',
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # File upload
    st.markdown('<div class="ts-label">Source file</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Drop audio file here",
        type=["mp3", "wav", "flac", "ogg", "m4a"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        size_mb = uploaded_file.size / 1_048_576
        st.markdown(f"""
        <div class="spec-grid">
          <div class="spec-cell">
            <div class="spec-key">Filename</div>
            <div class="spec-val" style="font-size:11px; word-break:break-all;">{uploaded_file.name}</div>
          </div>
          <div class="spec-cell">
            <div class="spec-key">Size</div>
            <div class="spec-val amber">{size_mb:.1f} MB</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Run separation", use_container_width=True)

        if run_btn:
            # Clean up previous run
            if st.session_state.output_dir:
                cleanup(st.session_state.output_dir)
            st.session_state.stem_paths = {}
            st.session_state.output_dir = None

            tmp = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=Path(uploaded_file.name).suffix
            )
            tmp.write(uploaded_file.read())
            tmp.flush()
            tmp.close()

            out_dir = tempfile.mkdtemp(prefix="tracksplitter_")

            bar = st.progress(0)
            status = st.empty()

            def on_progress(value: float, message: str = ""):
                bar.progress(value)
                if message:
                    status.markdown(
                        f'<p style="font-size:10px;color:#525252;letter-spacing:2px;'
                        f'text-transform:uppercase;margin-top:6px;">{message}</p>',
                        unsafe_allow_html=True
                    )

            try:
                stems = separate_audio(
                    input_path=tmp.name,
                    model_name=model_key,
                    output_dir=out_dir,
                    progress_callback=on_progress,
                )
                st.session_state.stem_paths    = stems
                st.session_state.output_dir    = out_dir
                st.session_state.processed_file = uploaded_file.name
                st.session_state.session_ts    = str(int(time.time()))
                bar.empty()
                status.empty()
                st.success("Separation complete.")

            except Exception as e:
                bar.empty()
                status.empty()
                st.error(f"Separation failed: {e}")

            finally:
                os.unlink(tmp.name)

    else:
        st.markdown("""
        <div style="
          border: 1px dashed #222;
          border-radius: 2px;
          padding: 20px 16px;
          text-align: center;
          margin-top: 8px;
        ">
          <div style="font-size:9px; letter-spacing:3px; text-transform:uppercase; color:#333;">
            Accepts MP3 · WAV · FLAC · OGG · M4A
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Specs panel
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="ts-label">System</div>', unsafe_allow_html=True)
    gpu_label = "CUDA" if device_type == "cuda" else "—"
    eta_gpu   = "30 – 90 sec" if device_type == "cuda" else "8 – 15 min"
    st.markdown(f"""
    <div class="spec-grid">
      <div class="spec-cell">
        <div class="spec-key">Device</div>
        <div class="spec-val" style="font-size:11px;">{device_name}</div>
      </div>
      <div class="spec-cell">
        <div class="spec-key">Acceleration</div>
        <div class="spec-val green">{gpu_label}</div>
      </div>
      <div class="spec-cell" style="grid-column:1/-1;">
        <div class="spec-key">Estimated time / 3-min track</div>
        <div class="spec-val amber">{eta_gpu}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Right column: mixer ─────────────────
with col_mixer:
    st.markdown('<div class="ts-label">Stem mixer</div>', unsafe_allow_html=True)

    if st.session_state.stem_paths:
        render_mixer(
            st.session_state.stem_paths,
            get_stem_info,
            st.session_state.session_ts,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Mix export ──────────────────────────
        st.markdown('<div class="ts-label">Mix export</div>', unsafe_allow_html=True)

        if "mix_volumes" not in st.session_state:
            st.session_state.mix_volumes = {}

        for stem_name in st.session_state.stem_paths:
            info = get_stem_info(stem_name)

            if stem_name not in st.session_state.mix_volumes:
                st.session_state.mix_volumes[stem_name] = 100

            c1, c2 = st.columns([4, 1.5])
            with c1:
                vol = st.slider(
                    f"{info['label']}",
                    0, 100,
                    value=st.session_state.mix_volumes[stem_name],
                    key=f"mx_vol_{stem_name}",
                    label_visibility="collapsed",
                )
                st.session_state.mix_volumes[stem_name] = vol
            with c2:
                db = "-∞" if vol == 0 else f"{20 * math.log10(vol / 100):.1f}"
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;"
                    f"height:38px;'>"
                    f"<span style='color:{info['color']};"
                    f"font-family:Barlow Condensed,sans-serif;"
                    f"font-size:13px;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:1px;'>"
                    f"{info['label']}</span>"
                    f"<span style='color:var(--muted);font-size:10px;'>"
                    f"{db} dB</span></div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Prepare mixed download", use_container_width=True):
            vols = {
                k: v / 100
                for k, v in st.session_state.mix_volumes.items()
            }

            mixed_audio, sr = mix_stems(
                st.session_state.stem_paths,
                vols,
                {},
            )

            if mixed_audio is not None:
                import soundfile as sf
                buf = _io.BytesIO()
                sf.write(buf, mixed_audio, sr, format="WAV")
                buf.seek(0)
                st.session_state["mixed_wav_data"] = buf.getvalue()
                st.session_state["mixed_wav_ready"] = True
            else:
                st.warning("All stems are at 0 — nothing to mix.")

        if st.session_state.get("mixed_wav_ready"):
            base = Path(st.session_state.processed_file or "track").stem
            st.download_button(
                label="Download mixed WAV",
                data=st.session_state["mixed_wav_data"],
                file_name=f"{base}_mixed.wav",
                mime="audio/wav",
                use_container_width=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="ts-label">Export</div>', unsafe_allow_html=True)

        # ZIP download
        zip_buf = _io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for stem_name, wav_path in st.session_state.stem_paths.items():
                zf.write(wav_path, arcname=f"{stem_name}.wav")
        zip_buf.seek(0)

        st.download_button(
            label="Download all stems  (.zip)",
            data=zip_buf,
            file_name="tracksplitter_stems.zip",
            mime="application/zip",
            use_container_width=True,
        )

    else:
        # Decorative empty state — static waveform bars
        bar_heights = [16, 28, 20, 40, 24, 36, 18, 44, 30, 22, 38, 26, 16, 32, 20, 42, 28, 18, 36, 24]
        bars_html = "".join(
            f'<div class="empty-bar" style="height:{h}px;"></div>'
            for h in bar_heights
        )
        st.markdown(f"""
        <div class="empty-state">
          <div class="empty-waveform">{bars_html}</div>
          <div class="empty-label">Awaiting source file</div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────
# Footer
# ─────────────────────────────────────────
st.markdown("""
<div class="ts-footer">
  <span>TrackSplitter &nbsp;/&nbsp; Open Source &nbsp;/&nbsp; MIT</span>
  <span>Powered by Demucs &mdash; Meta AI Research</span>
</div>
""", unsafe_allow_html=True)
