import os
import tempfile
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import sosfilt, butter, sosfiltfilt

TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp_audio")
os.makedirs(TEMP_DIR, exist_ok=True)

DEFAULT_SR = 44100


def temp_path(suffix=".wav") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix, dir=TEMP_DIR)
    os.close(fd)
    return path


def load_audio(file_path: str, sr: int = DEFAULT_SR, mono: bool = True) -> tuple[np.ndarray, int]:
    y, loaded_sr = librosa.load(file_path, sr=sr, mono=mono)
    return y, loaded_sr


def save_audio(y: np.ndarray, path: str, sr: int = DEFAULT_SR) -> str:
    y = post_process(y, sr)
    sf.write(path, y, sr)
    return path


def peak_normalize(y: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(y))
    if peak > 0:
        y = y / peak * 0.95
    return y


def post_process(y: np.ndarray, sr: int) -> np.ndarray:
    """Mastering chain applied to all output audio."""
    # 1. DC offset removal
    y = y - np.mean(y)

    # 2. High-pass filter at 30 Hz — removes sub-bass rumble
    sos_hp = butter(4, 30, btype='high', fs=sr, output='sos')
    y = sosfiltfilt(sos_hp, y).astype(np.float32)

    # 3. Gentle RMS compression — 3:1 ratio above -12 dBFS
    y = _rms_compress(y, sr, threshold_db=-12, ratio=3.0, window_ms=50)

    # 4. 3-band EQ: high-shelf +2dB above 4kHz, low-shelf -1dB below 200Hz
    y = _apply_eq(y, sr)

    # 5. Soft limiter — tanh instead of hard clipping
    y = np.tanh(y * 1.5) / 1.5

    # 6. RMS normalization to -18 dBFS
    y = _rms_normalize(y, target_db=-18)

    return y


def _rms_compress(y: np.ndarray, sr: int, threshold_db: float, ratio: float, window_ms: float) -> np.ndarray:
    """Simple RMS-based compressor."""
    window_samples = int(sr * window_ms / 1000)
    if window_samples < 1:
        window_samples = 1

    # Compute RMS envelope
    y_sq = y ** 2
    # Pad for windowed mean
    rms_env = np.sqrt(np.convolve(y_sq, np.ones(window_samples) / window_samples, mode='same') + 1e-10)

    # Convert threshold to linear
    threshold_lin = 10 ** (threshold_db / 20)

    # Compute gain reduction
    gain = np.ones_like(y)
    mask = rms_env > threshold_lin
    if np.any(mask):
        # dB over threshold
        over_db = 20 * np.log10(rms_env[mask] / threshold_lin + 1e-10)
        # Reduce by (1 - 1/ratio) of the overshoot
        reduction_db = over_db * (1 - 1 / ratio)
        gain[mask] = 10 ** (-reduction_db / 20)

    return y * gain


def _apply_eq(y: np.ndarray, sr: int) -> np.ndarray:
    """3-band EQ: high-shelf boost, low-shelf cut."""
    # High-shelf +2dB above 4kHz (approximated with a high-shelf via HP filter blend)
    if sr > 8000:  # Only apply if sample rate supports it
        sos_high = butter(2, 4000, btype='high', fs=sr, output='sos')
        high_band = sosfiltfilt(sos_high, y).astype(np.float32)
        high_gain = 10 ** (2 / 20)  # +2 dB
        y = y + high_band * (high_gain - 1)

    # Low-shelf -1dB below 200Hz (approximated via LP filter blend)
    sos_low = butter(2, 200, btype='low', fs=sr, output='sos')
    low_band = sosfiltfilt(sos_low, y).astype(np.float32)
    low_gain = 10 ** (-1 / 20)  # -1 dB
    y = y + low_band * (low_gain - 1)

    return y


def _rms_normalize(y: np.ndarray, target_db: float) -> np.ndarray:
    """Normalize to target RMS level in dBFS."""
    rms = np.sqrt(np.mean(y ** 2) + 1e-10)
    target_rms = 10 ** (target_db / 20)
    if rms > 0:
        y = y * (target_rms / rms)
    # Final safety clip
    y = np.clip(y, -1.0, 1.0)
    return y


def match_length(y_a: np.ndarray, y_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    max_len = max(len(y_a), len(y_b))
    if len(y_a) < max_len:
        y_a = np.pad(y_a, (0, max_len - len(y_a)))
    if len(y_b) < max_len:
        y_b = np.pad(y_b, (0, max_len - len(y_b)))
    return y_a, y_b
