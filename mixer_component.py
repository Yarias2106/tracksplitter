"""
mixer_component.py
Synchronized multi-stem mixer using the Web Audio API.
WAV files are served as static assets (no base64) to avoid Streamlit's
200 MB message size limit. Filenames include a timestamp to prevent
browser cache from serving stale audio after a new song is processed.
"""

import shutil
import json
import time
import os
from pathlib import Path
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).parent / "static" / "stems"


def _cleanup_old_sessions(keep: int = 2):
    """Remove all but the `keep` most recent session directories."""
    dirs = sorted(
        [d for d in BASE_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    for d in dirs[keep:]:
        shutil.rmtree(d, ignore_errors=True)


def prepare_static_stems(stem_paths: dict, session_ts: str) -> dict:
    """
    Copy WAV files to a session-scoped subdirectory (static/stems/<ts>/).
    Each session gets its own folder so old files are never locked.
    Also prunes old sessions on each call.
    Returns { stem_name: relative_url }.
    """
    static_dir = BASE_DIR / session_ts
    static_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_old_sessions()

    url_map = {}
    for stem_name, wav_path in stem_paths.items():
        fname = f"{stem_name}.wav"
        shutil.copy2(wav_path, static_dir / fname)
        url_map[stem_name] = f"app/static/stems/{session_ts}/{fname}"

    return url_map


def render_mixer(stem_paths: dict, stem_info_fn, session_ts: str) -> None:
    """
    Render the synchronized mixer.
    All stems share a single transport — perfect sync, no drift.
    Per-stem controls: volume slider and mute toggle.
    """
    url_map = prepare_static_stems(stem_paths, session_ts)

    stems_data = []
    for stem_name in stem_paths:
        info = stem_info_fn(stem_name)
        stems_data.append({
            "name":  stem_name,
            "label": info["label"],
            "color": info["color"],
            "url":   url_map[stem_name],
        })

    stems_json = json.dumps(stems_data)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Barlow+Condensed:wght@400;600;700&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: transparent;
    font-family: 'IBM Plex Mono', monospace;
    color: #D4D4D4;
    font-size: 13px;
  }}

  /* ── Transport ── */
  .transport {{
    background: #111111;
    border: 1px solid #2A2A2A;
    border-radius: 4px;
    padding: 14px 18px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: relative;
  }}
  .transport::before {{
    content: 'TRANSPORT';
    position: absolute;
    top: -9px; left: 14px;
    background: #111111;
    padding: 0 6px;
    font-size: 9px;
    letter-spacing: 3px;
    color: #404040;
  }}

  .play-btn {{
    width: 38px; height: 38px;
    border-radius: 2px;
    border: 1px solid #3A3A3A;
    background: #1A1A1A;
    color: #E8A838;
    font-size: 14px;
    cursor: pointer;
    flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.15s, border-color 0.15s;
    letter-spacing: 0;
  }}
  .play-btn:hover:not(:disabled) {{
    background: #222222;
    border-color: #E8A838;
  }}
  .play-btn:disabled {{ opacity: 0.3; cursor: not-allowed; }}
  .play-btn.playing {{ border-color: #E8A838; color: #E8A838; }}

  .progress-section {{ flex: 1; display: flex; flex-direction: column; gap: 8px; }}

  .timecode {{
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: #525252;
    letter-spacing: 1px;
  }}
  .timecode .current {{ color: #E8A838; }}

  .scrub-track {{
    width: 100%;
    height: 4px;
    background: #1E1E1E;
    border: 1px solid #2A2A2A;
    border-radius: 1px;
    cursor: pointer;
    position: relative;
  }}
  .scrub-fill {{
    height: 100%;
    background: #E8A838;
    border-radius: 1px;
    width: 0%;
    pointer-events: none;
    transition: width 0.08s linear;
  }}

  /* Loading indicator */
  .load-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 2px;
  }}
  .load-bar-wrap {{
    flex: 1;
    height: 2px;
    background: #1E1E1E;
    border-radius: 1px;
    overflow: hidden;
  }}
  .load-bar-fill {{
    height: 100%;
    background: #4ADE80;
    width: 0%;
    transition: width 0.3s ease;
  }}
  .load-label {{
    font-size: 9px;
    color: #404040;
    letter-spacing: 2px;
    white-space: nowrap;
  }}

  /* ── Channel strips ── */
  .channels {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}

  .channel {{
    background: #111111;
    border: 1px solid #222222;
    border-left: 2px solid var(--ch-color);
    border-radius: 2px;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 16px;
    transition: background 0.15s;
  }}
  .channel:hover {{ background: #151515; }}
  .channel.muted {{
    border-left-color: #2A2A2A;
    opacity: 0.45;
  }}

  .ch-name {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--ch-color);
    min-width: 80px;
    transition: color 0.15s;
  }}
  .channel.muted .ch-name {{ color: #3A3A3A; }}

  /* Signal indicator dots */
  .signal {{
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex-shrink: 0;
  }}
  .signal-dot {{
    width: 5px; height: 5px;
    border-radius: 50%;
    background: #1E1E1E;
    transition: background 0.3s;
  }}
  .signal-dot.active {{ background: var(--ch-color); }}
  .signal-dot.loading {{ background: #E8A838; animation: pulse 0.8s infinite; }}

  @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.2}} }}

  /* Mute */
  .mute-btn {{
    width: 26px; height: 26px;
    border-radius: 2px;
    border: 1px solid #2A2A2A;
    background: #161616;
    color: #525252;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    cursor: pointer;
    flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.12s;
  }}
  .mute-btn:hover {{ border-color: #E8A838; color: #D4D4D4; }}
  .mute-btn.muted {{ background: #1E1E1E; color: #2A2A2A; border-color: #1E1E1E; }}

  /* Volume fader */
  .fader-group {{ flex: 1; display: flex; align-items: center; gap: 10px; }}

  .fader-label {{ font-size: 9px; color: #404040; letter-spacing: 1px; flex-shrink: 0; }}

  .fader {{
    flex: 1;
    -webkit-appearance: none;
    height: 2px;
    background: #2A2A2A;
    border-radius: 1px;
    outline: none;
    cursor: pointer;
  }}
  .fader::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 12px; height: 20px;
    border-radius: 1px;
    background: #D4D4D4;
    border: 1px solid #404040;
    cursor: pointer;
    transition: background 0.12s;
  }}
  .fader::-webkit-slider-thumb:hover {{ background: #F5F5F5; }}

  .fader-val {{
    font-size: 10px;
    color: #525252;
    min-width: 34px;
    text-align: right;
  }}

  /* Download */
  .dl-btn {{
    background: transparent;
    border: 1px solid #2A2A2A;
    border-radius: 2px;
    color: #404040;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    letter-spacing: 1px;
    padding: 4px 10px;
    cursor: pointer;
    text-decoration: none;
    flex-shrink: 0;
    transition: all 0.12s;
    white-space: nowrap;
    text-transform: uppercase;
  }}
  .dl-btn:hover {{
    border-color: var(--ch-color);
    color: var(--ch-color);
  }}
</style>
</head>
<body>

<!-- Transport -->
<div class="transport">
  <button class="play-btn" id="playBtn" onclick="togglePlay()" disabled>
    <svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor">
      <polygon points="0,0 12,7 0,14" id="playIcon"/>
    </svg>
  </button>
  <div class="progress-section">
    <div class="timecode">
      <span class="current" id="timeCurrent">00:00.0</span>
      <span id="timeDuration">--:--.--</span>
    </div>
    <div class="scrub-track" id="scrubTrack" onclick="seek(event)">
      <div class="scrub-fill" id="scrubFill"></div>
    </div>
    <div class="load-row" id="loadRow">
      <span class="load-label" id="loadLabel">LOADING</span>
      <div class="load-bar-wrap">
        <div class="load-bar-fill" id="loadFill"></div>
      </div>
    </div>
  </div>
</div>

<!-- Channel strips -->
<div class="channels" id="channels"></div>

<script>
const STEMS = {stems_json};

const ctx    = new (window.AudioContext || window.webkitAudioContext)();
const master = ctx.createGain();
master.connect(ctx.destination);

const buffers  = {{}};
const gains    = {{}};
const muted    = {{}};
const volumes  = {{}};
let   sources  = {{}};
let   playing  = false;
let   startAt  = 0;
let   offset   = 0;
let   duration = 0;
let   loaded   = 0;
let   raf      = null;

// Build channel strips
const channelsEl = document.getElementById('channels');
STEMS.forEach(s => {{
  muted[s.name]   = false;
  volumes[s.name] = 1.0;

  const g = ctx.createGain();
  g.connect(master);
  gains[s.name] = g;

  const ch = document.createElement('div');
  ch.className = 'channel';
  ch.id = 'ch_' + s.name;
  ch.style.setProperty('--ch-color', s.color);
  ch.innerHTML = `
    <div class="signal" id="sig_${{s.name}}">
      <div class="signal-dot loading" id="dot0_${{s.name}}"></div>
      <div class="signal-dot loading" id="dot1_${{s.name}}"></div>
      <div class="signal-dot loading" id="dot2_${{s.name}}"></div>
    </div>
    <div class="ch-name">${{s.label}}</div>
    <button class="mute-btn" id="mute_${{s.name}}" onclick="toggleMute('${{s.name}}')">M</button>
    <div class="fader-group">
      <span class="fader-label">VOL</span>
      <input type="range" class="fader" id="fdr_${{s.name}}"
        min="0" max="100" value="100"
        oninput="setVol('${{s.name}}', this.value)">
      <span class="fader-val" id="fval_${{s.name}}">0 dB</span>
    </div>
    <a class="dl-btn" href="${{s.url}}" download="${{s.name}}.wav"
       style="--ch-color:${{s.color}}">Export</a>
  `;
  channelsEl.appendChild(ch);
}});

function setSignalReady(name) {{
  ['dot0','dot1','dot2'].forEach(d => {{
    const el = document.getElementById(d + '_' + name);
    el.className = 'signal-dot active';
  }});
}}
function setSignalError(name) {{
  ['dot0','dot1','dot2'].forEach(d => {{
    const el = document.getElementById(d + '_' + name);
    el.className = 'signal-dot';
    el.style.background = '#EF4444';
  }});
}}

// Fetch and decode all stems
async function loadAll() {{
  for (let i = 0; i < STEMS.length; i++) {{
    const s = STEMS[i];
    try {{
      const res = await fetch(s.url);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const buf = await res.arrayBuffer();
      buffers[s.name] = await ctx.decodeAudioData(buf);
      if (buffers[s.name].duration > duration) {{
        duration = buffers[s.name].duration;
        document.getElementById('timeDuration').textContent = fmt(duration);
      }}
      setSignalReady(s.name);
    }} catch(e) {{
      setSignalError(s.name);
      console.error('Error loading', s.name, e);
    }}
    loaded++;
    document.getElementById('loadFill').style.width =
      Math.round(loaded / STEMS.length * 100) + '%';
  }}
  document.getElementById('loadRow').style.display = 'none';
  document.getElementById('playBtn').disabled = false;
}}
loadAll();

// Transport
function togglePlay() {{
  if (ctx.state === 'suspended') ctx.resume();
  playing ? pause() : play(offset);
}}

function play(off) {{
  Object.values(sources).forEach(s => {{ try {{ s.stop(); }} catch(e) {{}} }});
  sources = {{}};

  STEMS.forEach(s => {{
    if (!buffers[s.name]) return;
    const src = ctx.createBufferSource();
    src.buffer = buffers[s.name];
    src.connect(gains[s.name]);
    src.start(0, off);
    sources[s.name] = src;
  }});

  const first = STEMS[0]?.name;
  if (first && sources[first]) {{
    sources[first].onended = () => {{
      if (ctx.currentTime - startAt >= duration - 0.3) {{
        playing = false; offset = 0;
        setPlayIcon(false);
        setProgress(0);
        cancelAnimationFrame(raf);
      }}
    }};
  }}

  startAt = ctx.currentTime - off;
  playing = true;
  setPlayIcon(true);
  tick();
}}

function pause() {{
  offset = ctx.currentTime - startAt;
  Object.values(sources).forEach(s => {{ try {{ s.stop(); }} catch(e) {{}} }});
  sources = {{}};
  playing = false;
  setPlayIcon(false);
  cancelAnimationFrame(raf);
}}

function seek(e) {{
  const r = e.clientX - e.currentTarget.getBoundingClientRect().left;
  const ratio = Math.max(0, Math.min(1, r / e.currentTarget.offsetWidth));
  offset = ratio * duration;
  setProgress(ratio);
  if (playing) play(offset);
}}

function setVol(name, val) {{
  volumes[name] = val / 100;
  if (!muted[name])
    gains[name].gain.setTargetAtTime(volumes[name], ctx.currentTime, 0.012);
  // Convert to dB-like display
  const db = val == 0 ? '-inf' : (20 * Math.log10(val / 100)).toFixed(1);
  document.getElementById('fval_' + name).textContent =
    val == 100 ? '0 dB' : db + ' dB';
}}

function toggleMute(name) {{
  muted[name] = !muted[name];
  const btn = document.getElementById('mute_' + name);
  const ch  = document.getElementById('ch_' + name);
  if (muted[name]) {{
    gains[name].gain.setTargetAtTime(0, ctx.currentTime, 0.012);
    btn.classList.add('muted');
    ch.classList.add('muted');
  }} else {{
    gains[name].gain.setTargetAtTime(volumes[name], ctx.currentTime, 0.012);
    btn.classList.remove('muted');
    ch.classList.remove('muted');
  }}
}}

function tick() {{
  raf = requestAnimationFrame(() => {{
    if (!playing) return;
    const elapsed = ctx.currentTime - startAt;
    setProgress(Math.min(elapsed / duration, 1));
    if (elapsed < duration) tick();
  }});
}}

function setProgress(ratio) {{
  document.getElementById('scrubFill').style.width = (ratio * 100) + '%';
  document.getElementById('timeCurrent').textContent = fmt(ratio * duration);
}}

function setPlayIcon(isPlaying) {{
  const btn = document.getElementById('playBtn');
  btn.innerHTML = isPlaying
    ? `<svg width="10" height="14" viewBox="0 0 10 14" fill="currentColor">
         <rect x="0" y="0" width="3" height="14"/><rect x="7" y="0" width="3" height="14"/>
       </svg>`
    : `<svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor">
         <polygon points="0,0 12,7 0,14"/>
       </svg>`;
  btn.classList.toggle('playing', isPlaying);
}}

function fmt(s) {{
  const m  = Math.floor(s / 60);
  const ss = Math.floor(s % 60);
  const ds = Math.floor((s % 1) * 10);
  return String(m).padStart(2,'0') + ':' + String(ss).padStart(2,'0') + '.' + ds;
}}
</script>
</body>
</html>"""

    components.html(html, height=148 + len(stems_data) * 64, scrolling=False)
