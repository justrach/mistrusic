"""StyleVocoder: log-mel U-Net with FiLM style conditioning — MLX backend.

MLX Conv layers use **NLC** format (batch, time, channels).
All conv inputs/outputs are in this format throughout the model.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import librosa
import mlx.core as mx
import mlx.nn as nn

# ── Shared audio constants ───────────────────────────────────────────────────────────
SR: int = 22050
N_MELS: int = 80
N_FFT: int = 1024
HOP_LENGTH: int = 256
TOP_DB: float = 80.0
FMIN: float = 0.0
FMAX: float = 8000.0


# ── Audio utilities ────────────────────────────────────────────────────────────────

def compute_mel(audio: np.ndarray, sr: int = SR) -> np.ndarray:
    """Return normalised log-mel in [-1, 0], shape (N_MELS, T)."""
    if sr != SR:
        audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=SR)
    mel = librosa.feature.melspectrogram(
        y=audio, sr=SR, n_fft=N_FFT, hop_length=HOP_LENGTH,
        n_mels=N_MELS, fmin=FMIN, fmax=FMAX,
    )
    mel_db = librosa.power_to_db(mel, ref=np.max, top_db=TOP_DB)
    return (mel_db / TOP_DB).astype(np.float32)


def mel_to_audio(mel_norm: np.ndarray, sr: int = SR, n_iter: int = 64) -> np.ndarray:
    """Reconstruct audio from normalised log-mel via Griffin-Lim."""
    mel_db = (mel_norm * TOP_DB).clip(-TOP_DB, 0.0)
    mel_power = librosa.db_to_power(mel_db)
    audio = librosa.feature.inverse.mel_to_audio(
        mel_power, sr=SR, n_fft=N_FFT, hop_length=HOP_LENGTH,
        fmin=FMIN, fmax=FMAX, n_iter=n_iter,
    )
    if sr != SR:
        audio = librosa.resample(audio, orig_sr=SR, target_sr=sr)
    return audio.astype(np.float32)


def mel_to_audio_with_phase(
    mel_norm: np.ndarray,
    carrier_audio: np.ndarray,
    sr: int = SR,
) -> np.ndarray:
    """Reconstruct audio using the carrier's STFT phase.

    Much smoother than Griffin-Lim: keeps the carrier's temporal dynamics,
    only recolours the spectral magnitude to match the predicted timbre.

    Args:
        mel_norm:     (N_MELS, T) predicted normalised log-mel from the model.
        carrier_audio: Original carrier audio at sample rate ``sr``.
        sr:           Sample rate of ``carrier_audio``.

    Returns:
        Float32 audio array.
    """
    # Resample carrier to model SR
    carrier_sr = carrier_audio.astype(np.float32)
    if sr != SR:
        carrier_sr = librosa.resample(carrier_sr, orig_sr=sr, target_sr=SR)

    # Carrier STFT → phase
    D_carrier = librosa.stft(carrier_sr, n_fft=N_FFT, hop_length=HOP_LENGTH)
    carrier_phase = np.angle(D_carrier)            # (n_fft//2+1, T_stft)

    # Predicted mel → linear magnitude
    mel_db    = (mel_norm * TOP_DB).clip(-TOP_DB, 0.0)
    mel_power = librosa.db_to_power(mel_db)        # (N_MELS, T_mel)
    target_mag = librosa.feature.inverse.mel_to_stft(
        mel_power, sr=SR, n_fft=N_FFT, fmin=FMIN, fmax=FMAX,
    )                                              # (n_fft//2+1, T_mel)

    # Align time axes
    T = min(target_mag.shape[1], carrier_phase.shape[1])
    target_mag   = target_mag[:, :T]
    carrier_phase = carrier_phase[:, :T]

    # Recombine: predicted magnitude + carrier phase
    D_out = target_mag * np.exp(1j * carrier_phase)
    audio = librosa.istft(D_out, hop_length=HOP_LENGTH, n_fft=N_FFT)

    if sr != SR:
        audio = librosa.resample(audio, orig_sr=SR, target_sr=sr)
    return audio.astype(np.float32)


def add_reverb(
    audio: np.ndarray,
    sr: int = SR,
    room_size: float = 0.6,
    decay: float = 0.65,
    wet: float = 0.45,
) -> np.ndarray:
    """Add synthetic convolution reverb using an exponential decay IR.

    Args:
        audio:     Input audio array.
        sr:        Sample rate.
        room_size: Reverb tail length in seconds.
        decay:     How slowly the tail decays (0 = dead, 1 = infinite).
        wet:       Wet/dry mix (0 = dry, 1 = fully wet).
    """
    import scipy.signal
    ir_len = int(room_size * sr)
    t  = np.linspace(0, room_size, ir_len)
    rng = np.random.default_rng(seed=42)
    ir  = rng.standard_normal(ir_len) * np.exp(-t * (1.0 - decay) * 8.0)
    ir[0] = 1.0
    ir /= np.abs(ir).max()
    reverbed = scipy.signal.fftconvolve(audio, ir)[: len(audio)]
    out = (1.0 - wet) * audio + wet * reverbed
    peak = np.abs(out).max()
    if peak > 1e-8:
        out /= peak / 0.95
    return out.astype(np.float32)
# ── Building blocks ─────────────────────────────────────────────────────────────────

def _gn(channels: int) -> nn.GroupNorm:
    for g in [8, 4, 2, 1]:
        if channels % g == 0:
            return nn.GroupNorm(g, channels)
    return nn.GroupNorm(1, channels)


class FiLM(nn.Module):
    """Feature-wise Linear Modulation for style conditioning."""

    def __init__(self, cond_dim: int, channels: int) -> None:
        super().__init__()
        self.gamma = nn.Linear(cond_dim, channels)
        self.beta  = nn.Linear(cond_dim, channels)

    def __call__(self, x: mx.array, cond: mx.array) -> mx.array:
        # x: (B, T, C)  cond: (B, cond_dim)
        g = self.gamma(cond)[:, None, :]   # (B, 1, C)
        b = self.beta(cond)[:, None, :]    # (B, 1, C)
        return g * x + b


class EncoderBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, downsample: bool = True) -> None:
        super().__init__()
        stride, ksize = (2, 4) if downsample else (1, 3)
        self.c1 = nn.Conv1d(in_ch,  out_ch, ksize, stride=stride, padding=1)
        self.n1 = _gn(out_ch)
        self.c2 = nn.Conv1d(out_ch, out_ch, 3, padding=1)
        self.n2 = _gn(out_ch)

    def __call__(self, x: mx.array) -> mx.array:
        x = nn.gelu(self.n1(self.c1(x)))
        x = nn.gelu(self.n2(self.c2(x)))
        return x


class DecoderBlock(nn.Module):
    def __init__(self, in_ch: int, skip_ch: int, out_ch: int, cond_dim: int) -> None:
        super().__init__()
        self.up   = nn.ConvTranspose1d(in_ch, out_ch, 4, stride=2, padding=1)
        self.film = FiLM(cond_dim, out_ch)
        self.conv = nn.Conv1d(out_ch + skip_ch, out_ch, 3, padding=1)
        self.norm = _gn(out_ch)

    def __call__(self, x: mx.array, skip: mx.array, cond: mx.array) -> mx.array:
        x = self.up(x)
        T = skip.shape[1]
        if x.shape[1] > T:
            x = x[:, :T, :]
        elif x.shape[1] < T:
            x = mx.pad(x, [(0, 0), (0, T - x.shape[1]), (0, 0)])
        x = self.film(x, cond)
        x = mx.concatenate([x, skip], axis=2)   # concat on channel axis
        return nn.gelu(self.norm(self.conv(x)))


class ResBlock(nn.Module):
    """Residual block with FiLM conditioning."""

    def __init__(self, ch: int, cond_dim: int) -> None:
        super().__init__()
        self.c1   = nn.Conv1d(ch, ch, 3, padding=1)
        self.c2   = nn.Conv1d(ch, ch, 3, padding=1)
        self.film = FiLM(cond_dim, ch)
        self.g1   = _gn(ch)
        self.g2   = _gn(ch)

    def __call__(self, x: mx.array, cond: mx.array) -> mx.array:
        h = nn.gelu(self.g1(self.c1(x)))
        h = self.film(h, cond)
        h = self.g2(self.c2(h))
        return nn.gelu(x + h)


# ── Model ────────────────────────────────────────────────────────────────────────

class StyleVocoderModel(nn.Module):
    """Mel-domain U-Net that morphs carrier timbre to a target style.

    Inputs/outputs use MLX NLC format: (batch, time, channels).
    """

    def __init__(
        self,
        n_mels:     int = N_MELS,
        style_dim:  int = N_MELS,
        hidden_dim: int = 256,
    ) -> None:
        super().__init__()
        H = hidden_dim
        self.n_mels    = n_mels
        self.style_dim = style_dim

        # Style projection: style_dim → H
        self.proj1 = nn.Linear(style_dim, H)
        self.proj2 = nn.Linear(H, H)

        # Encoder
        self.enc1 = EncoderBlock(n_mels, H // 2, downsample=False)  # (B, T,   H/2)
        self.enc2 = EncoderBlock(H // 2, H,      downsample=True)   # (B, T/2, H)
        self.enc3 = EncoderBlock(H,      H * 2,  downsample=True)   # (B, T/4, H*2)

        # Bottleneck
        self.bottleneck = ResBlock(H * 2, cond_dim=H)

        # Decoder
        self.dec3 = DecoderBlock(H * 2, skip_ch=H,     out_ch=H,     cond_dim=H)
        self.dec2 = DecoderBlock(H,     skip_ch=H // 2, out_ch=H // 2, cond_dim=H)

        # Output
        self.out = nn.Conv1d(H // 2, n_mels, 1)

    def __call__(self, carrier_mel: mx.array, style_emb: mx.array) -> mx.array:
        """Forward pass.

        Args:
            carrier_mel: (B, T, n_mels) normalised log-mel, NLC format.
            style_emb:   (B, style_dim) style embedding.
        Returns:
            pred_mel: (B, T, n_mels)
        """
        cond = self.proj2(nn.relu(self.proj1(style_emb)))  # (B, H)

        e1 = self.enc1(carrier_mel)       # (B, T,   H/2)
        e2 = self.enc2(e1)                # (B, T/2, H)
        e3 = self.enc3(e2)                # (B, T/4, H*2)

        h  = self.bottleneck(e3, cond)    # (B, T/4, H*2)

        d3 = self.dec3(h, e2, cond)       # (B, T/2, H)
        d2 = self.dec2(d3, e1, cond)      # (B, T,   H/2)

        return self.out(d2)               # (B, T,   n_mels)


# ── Checkpoint helpers ─────────────────────────────────────────────────────────────

def save_checkpoint(
    model:  StyleVocoderModel,
    stem:   str,
    config: dict,
    epoch:  int,
    loss:   float,
) -> None:
    """Save weights to ``{stem}.safetensors`` and config to ``{stem}.json``."""
    p = Path(stem)
    model.save_weights(str(p.with_suffix(".safetensors")))
    with open(p.with_suffix(".json"), "w") as f:
        json.dump({"config": config, "epoch": epoch, "loss": loss}, f, indent=2)


def load_checkpoint(stem: str) -> tuple[StyleVocoderModel, dict]:
    """Load model from ``{stem}.safetensors`` + ``{stem}.json``."""
    p = Path(stem)
    with open(p.with_suffix(".json")) as f:
        meta = json.load(f)
    model = StyleVocoderModel(**meta["config"])
    model.load_weights(str(p.with_suffix(".safetensors")))
    mx.eval(model.parameters())
    return model, meta
