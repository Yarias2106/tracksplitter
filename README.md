# TrackSplitter

**AI-powered audio stem separation in the browser.**  
Upload any song and get individual stems — vocals, drums, bass, guitar, piano — ready to play, mix, and download.

Built on [Demucs](https://github.com/facebookresearch/demucs) (Meta AI Research) with a Streamlit interface featuring a synchronized multi-track mixer powered by the Web Audio API.

---

## Features

- **6-stem separation** with `htdemucs_6s` — vocals, drums, bass, guitar, piano, other
- **4-stem fine-tuned** with `htdemucs_ft` — maximum quality per instrument
- **Synchronized mixer** — single transport controls all stems simultaneously; no drift, no desync
- **Per-stem controls** — individual volume faders and mute toggles
- **GPU accelerated** — automatic CUDA detection; falls back to CPU
- Accepts **MP3, WAV, FLAC, OGG, M4A**
- Export individual stems or download all as a ZIP

---

## Requirements

- Python 3.10
- NVIDIA GPU with CUDA *(optional but strongly recommended)*
- `ffmpeg` installed on the system

---

## Installation

### 1. Clone

```bash
git clone https://github.com/your-username/tracksplitter.git
cd tracksplitter
```

### 2. Create environment

```bash
conda create -n tracksplitter python=3.10
conda activate tracksplitter
```

### 3. Install PyTorch

**With NVIDIA GPU — replace `cu124` with your CUDA version (check with `nvidia-smi`):**

```bash
# CUDA 12.4 / 12.x
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# CUDA 11.8
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**CPU only:**

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Install ffmpeg

> **Windows** — do **not** use `conda install ffmpeg` (causes DLL conflicts). Use the standalone binary instead:

```bash
winget install Gyan.FFmpeg
```

Or download from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) and add `C:\ffmpeg\bin` to your PATH.

**Linux:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### 6. Pre-download models

On first run Demucs downloads the model weights (~800 MB). Do this before launching the app to avoid mid-session interruptions:

```bash
# 6-stem model
python -c "from demucs.pretrained import get_model; get_model('htdemucs_6s')"

# 4-stem fine-tuned (downloads 4 separate models)
python -c "from demucs.pretrained import get_model; get_model('htdemucs_ft')"
```

If the download is interrupted, re-run the same command — it resumes automatically.

---

## Usage

```bash
streamlit run app.py
```
---

## Performance

| Hardware | Time per 3-min track |
|---|---|
| NVIDIA RTX 3060 or better | ~30 – 60 sec |
| NVIDIA GTX 1060 | ~60 – 90 sec |
| CPU (8 cores) | ~8 – 15 min |

---


---

## Troubleshooting

### `[WinError 10054]` — Connection forcibly closed during model download

The download was interrupted. Re-run the pre-download command; it will resume where it left off:

```bash
python -c "from demucs.pretrained import get_model; get_model('htdemucs_6s')"
python -c "from demucs.pretrained import get_model; get_model('htdemucs_ft')"
```

---

### `[WinError 2]` — System cannot find the file specified

`ffmpeg` is not installed or not in PATH. See the ffmpeg installation step above.

**Do not use `conda install -c conda-forge ffmpeg` on Windows** — it installs GTK/Cairo DLLs that conflict with other packages.

---

### `gdk-pixbuf` / `cairo.dll` — Entry Point Not Found

Caused by the conda-forge ffmpeg. Fix:

```bash
conda remove ffmpeg
winget install Gyan.FFmpeg
```

Open a new terminal after installation and verify:

```bash
ffmpeg -version
```

---

### `MessageSizeError` — Data exceeds 200 MB limit

This was a known issue in earlier versions where audio was passed as base64 through Streamlit's message protocol. The current version serves stems as static files over HTTP, which has no size limit. Make sure `enableStaticServing = true` is present in `.streamlit/config.toml`.

---

## Models

| Model | Stems | Notes |
|---|---|---|
| `htdemucs_6s` | Vocals, Drums, Bass, Guitar, Piano, Other | Best for full analysis |
| `htdemucs_ft` | Vocals, Drums, Bass, Other | Fine-tuned per stem, highest quality |

---

## Tech stack

| Component | Technology |
|---|---|
| Separation model | [Demucs v4](https://github.com/facebookresearch/demucs) (Meta AI) |
| UI framework | [Streamlit](https://streamlit.io) |
| Audio playback | Web Audio API |
| Deep learning | PyTorch + torchaudio |

---

## License

MIT — free for personal and commercial use.

---

