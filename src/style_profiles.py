"""Build and load per-instrument style profile embeddings.

Usage (CLI)::

    python -m src.style_profiles \\
        --styles-dir raw_instruments \\
        --out profiles.npz

``raw_instruments/`` should contain one sub-directory per style, each holding
one or more ``.wav`` reference clips::

    raw_instruments/
      flute/   *.wav
      sax/     *.wav
      violin/  *.wav
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from .model import (
    SR, N_MELS, N_FFT, HOP_LENGTH, TOP_DB, FMIN, FMAX,
)


def _extract_embedding(audio: np.ndarray, sr: int) -> np.ndarray:
    """Mean normalised log-mel over time → shape (N_MELS,) in [-1, 0]."""
    import librosa
    if sr != SR:
        audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=SR)
    mel = librosa.feature.melspectrogram(
        y=audio, sr=SR, n_fft=N_FFT, hop_length=HOP_LENGTH,
        n_mels=N_MELS, fmin=FMIN, fmax=FMAX,
    )
    mel_db = librosa.power_to_db(mel, ref=np.max, top_db=TOP_DB)
    return (mel_db.mean(axis=1) / TOP_DB).astype(np.float32)


def build_profiles(
    styles_dir: str | Path,
    out_path: str | Path,
) -> dict[str, np.ndarray]:
    """Scan ``<styles_dir>/<name>/*.wav`` and save one embedding per sub-dir.

    Args:
        styles_dir: Root directory containing one sub-directory per style.
        out_path:   Destination ``.npz`` file path.

    Returns:
        Dict mapping style name → numpy embedding array.
    """
    styles_dir = Path(styles_dir)
    profiles: dict[str, np.ndarray] = {}

    for style_dir in sorted(styles_dir.iterdir()):
        if not style_dir.is_dir():
            continue
        wavs = sorted(style_dir.glob("*.wav"))
        if not wavs:
            print(f"  {style_dir.name}: no .wav files, skipping")
            continue

        embs = []
        for wav in wavs:
            audio, file_sr = sf.read(str(wav), dtype="float32", always_2d=False)
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            embs.append(_extract_embedding(audio, file_sr))

        profiles[style_dir.name] = np.stack(embs).mean(axis=0)
        print(f"  {style_dir.name}: {len(embs)} file(s)")

    np.savez(str(out_path), **profiles)
    print(f"Saved {len(profiles)} profile(s) → {out_path}")
    return profiles


def load_profiles(path: str | Path) -> dict[str, np.ndarray]:
    """Load profiles from an ``.npz`` file built by :func:`build_profiles`."""
    data = np.load(str(path))
    return {k: data[k].astype(np.float32) for k in data.files}


def encode_reference(audio: np.ndarray, sr: int) -> np.ndarray:
    """Compute a style embedding from a raw audio clip on the fly."""
    return _extract_embedding(audio, sr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build instrument style profiles")
    ap.add_argument("--styles-dir", required=True,
                    help="Root dir with one sub-dir per style")
    ap.add_argument("--out", required=True, help="Output .npz path")
    args = ap.parse_args()
    build_profiles(args.styles_dir, args.out)
