"""
separator.py
Core audio separation logic powered by Demucs.
Supports CUDA (NVIDIA GPU) and CPU automatically.
"""

import os
import shutil
import tempfile
import torch
import torchaudio
from pathlib import Path
from demucs.pretrained import get_model
from demucs.apply import apply_model
from demucs.audio import AudioFile, save_audio


# ─────────────────────────────────────────
# Available models
# ─────────────────────────────────────────
MODELS = {
    "htdemucs_6s — 6 stems (recommended)": "htdemucs_6s",
    "htdemucs_ft — 4 stems (highest quality)": "htdemucs_ft",
}

STEM_LABELS = {
    "vocals":  {"label": "Vocals",  "color": "#E8A838"},
    "drums":   {"label": "Drums",   "color": "#4ADE80"},
    "bass":    {"label": "Bass",    "color": "#38BDF8"},
    "other":   {"label": "Other",   "color": "#A78BFA"},
    "guitar":  {"label": "Guitar",  "color": "#F472B6"},
    "piano":   {"label": "Piano",   "color": "#FB923C"},
}


def detect_device() -> tuple[str, str]:
    """Returns (device_string, human_readable_name)."""
    if torch.cuda.is_available():
        return "cuda", torch.cuda.get_device_name(0)
    return "cpu", "CPU"


def separate_audio(
    input_path: str,
    model_name: str = "htdemucs_6s",
    output_dir: str = None,
    progress_callback=None,
) -> dict:
    """
    Separate an audio file into individual stems.

    Args:
        input_path:        Path to the audio file (MP3, WAV, FLAC, OGG).
        model_name:        Demucs model identifier.
        output_dir:        Output directory. If None, a temp dir is created.
        progress_callback: Optional callable(float, str) for progress updates.

    Returns:
        dict mapping stem name -> WAV file path.
    """
    device, device_name = detect_device()

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="tracksplitter_")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback(0.05, f"Loading model {model_name} on {device_name}...")

    model = get_model(model_name)
    model.to(device)
    model.eval()

    if progress_callback:
        progress_callback(0.15, "Reading audio file...")

    wav = AudioFile(input_path).read(
        streams=0,
        samplerate=model.samplerate,
        channels=model.audio_channels,
    )
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    wav = wav.unsqueeze(0).to(device)

    if progress_callback:
        progress_callback(0.25, "Separating stems — this may take a few minutes...")

    with torch.no_grad():
        sources = apply_model(
            model, wav,
            device=device,
            shifts=1,
            split=True,
            overlap=0.25,
            progress=False,
        )[0]

    sources = sources * ref.std() + ref.mean()

    if progress_callback:
        progress_callback(0.85, "Writing stem files...")

    stem_paths = {}
    for idx, stem in enumerate(model.sources):
        out_path = output_dir / f"{stem}.wav"
        save_audio(sources[idx].cpu(), str(out_path), samplerate=model.samplerate)
        stem_paths[stem] = str(out_path)

    if progress_callback:
        progress_callback(1.0, "Done.")

    return stem_paths


def get_stem_info(stem_name: str) -> dict:
    """Return display label and color for a stem."""
    return STEM_LABELS.get(
        stem_name,
        {"label": stem_name.capitalize(), "color": "#737373"}
    )


def mix_stems(stem_paths: dict, volumes: dict, mute_flags: dict) -> tuple:
    """
    Mix multiple stems into a single audio array with per-stem gain and mute.

    Args:
        stem_paths: dict of stem_name -> WAV file path.
        volumes:    dict of stem_name -> float gain (0.0 – 1.0).
        mute_flags: dict of stem_name -> bool (True = muted).

    Returns:
        (numpy array, sample_rate) or (None, None) if all muted.
    """
    import numpy as np
    import soundfile as sf

    mixed = None
    target_sr = None

    for stem_name, wav_path in stem_paths.items():
        if mute_flags.get(stem_name, False):
            continue

        data, sr = sf.read(wav_path)

        if target_sr is None:
            target_sr = sr
            mixed = np.zeros_like(data, dtype=np.float64)
        else:
            if sr != target_sr:
                import librosa
                data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
            if len(data) < len(mixed):
                padded = np.zeros_like(mixed)
                padded[:len(data)] = data
                data = padded
            elif len(data) > len(mixed):
                data = data[:len(mixed)]

        gain = volumes.get(stem_name, 1.0)
        mixed += data * gain

    if mixed is None:
        return None, None

    peak = np.max(np.abs(mixed))
    if peak > 0.95:
        mixed = mixed * (0.95 / peak)

    return mixed.astype(np.float32), target_sr


def cleanup(path: str):
    """Remove a temporary directory."""
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
