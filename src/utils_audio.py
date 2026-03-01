"""Audio loading utilities shared by dataset/train/inference."""

from __future__ import annotations

from pathlib import Path
from math import gcd
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float32)


def resample_audio(audio: np.ndarray, src_sr: int, target_sr: int) -> np.ndarray:
    if src_sr == target_sr:
        return audio.astype(np.float32)
    g = gcd(int(target_sr), int(src_sr))
    return resample_poly(audio, target_sr // g, src_sr // g).astype(np.float32)


def normalize_wave(audio: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    peak = np.max(np.abs(audio))
    if peak < eps:
        return np.zeros_like(audio)
    return (audio / peak * 0.99).astype(np.float32)


def pad_or_trim(audio: np.ndarray, target_len: int) -> np.ndarray:
    if len(audio) == target_len:
        return audio
    if len(audio) > target_len:
        return audio[:target_len].astype(np.float32)
    return np.pad(audio, (0, target_len - len(audio))).astype(np.float32)


def load_waveform(
    path: Path | str,
    target_sr: int = 32_000,
    duration_sec: float = 4.0,
    normalize: bool = True,
) -> np.ndarray:
    path = Path(path)
    audio, sr = sf.read(path, always_2d=False)
    audio = to_mono(audio)
    audio = resample_audio(audio, sr, target_sr)
    n = int(duration_sec * target_sr)
    audio = pad_or_trim(audio, n)
    if normalize:
        audio = normalize_wave(audio)
    return audio.astype(np.float32)


def ensure_length_torch(x: np.ndarray, n: int) -> np.ndarray:
    return pad_or_trim(x, n)
