"""Plugin-style runtime with overlap-add block processing — MLX backend.

Example::

    from src.plugin_runtime import StyleVocoderPlugin

    plugin = StyleVocoderPlugin(
        checkpoint="checkpoints/best",
        profiles="profiles.npz",
    )

    # Named style
    wet = plugin.process(audio, style="flute", sample_rate=44100)

    # Natural-language style via Mistral
    wet = plugin.process(audio, prompt="warm smoky jazz sax", sample_rate=44100)
"""
from __future__ import annotations

import numpy as np
import mlx.core as mx
import librosa

from .model import load_checkpoint, compute_mel, mel_to_audio, SR
from .style_profiles import load_profiles, encode_reference


class StyleVocoderPlugin:
    """Drop-in runtime: load once, call ``process()`` per audio block.

    Args:
        checkpoint: Checkpoint stem (e.g. ``"checkpoints/best"``).
        profiles:   Path to ``profiles.npz``.
        lm_url:     LM Studio URL for Mistral-powered style prompting.
        lm_model:   Model ID override (auto-detected if ``None``).
    """

    def __init__(
        self,
        checkpoint: str,
        profiles: str,
        lm_url: str = "http://localhost:1234/v1",
        lm_model: str | None = None,
    ) -> None:
        self.model, _ = load_checkpoint(checkpoint)
        self.model.eval()
        self.profiles  = load_profiles(profiles)
        self._lm_url   = lm_url
        self._lm_model = lm_model
        self._agent    = None   # lazy-init when first needed

    # ── Style helpers ─────────────────────────────────────────────────────────

    def _get_agent(self):
        if self._agent is None:
            from .style_agent import StyleAgent
            self._agent = StyleAgent(base_url=self._lm_url, model=self._lm_model)
        return self._agent

    def _resolve(
        self,
        style: str | np.ndarray | None,
        prompt: str | None,
        reference: np.ndarray | None,
        reference_sr: int,
    ) -> mx.array:
        if prompt is not None:
            emb, weights = self._get_agent().resolve_style(prompt, self.profiles)
            print(f"[Plugin] style blend: { {k: round(v,3) for k,v in weights.items()} }")
        elif reference is not None:
            emb = encode_reference(reference, reference_sr)
        elif isinstance(style, str):
            if style not in self.profiles:
                raise KeyError(f"Style '{style}' not found. Have: {sorted(self.profiles)}")
            emb = self.profiles[style]
        else:
            emb = np.asarray(style, dtype=np.float32)
        return mx.array(emb[None])  # (1, N_MELS)

    # ── Core processing ─────────────────────────────────────────────────────────

    def _process_chunk(self, chunk: np.ndarray, style_t: mx.array) -> np.ndarray:
        mel   = compute_mel(chunk, sr=SR)               # (N_MELS, T)
        mel_t = mx.array(mel.T[None])                   # (1, T, N_MELS)
        pred  = self.model(mel_t, style_t)              # (1, T, N_MELS)
        return mel_to_audio(np.array(pred[0]).T, sr=SR) # (samples,)

    def process(
        self,
        audio: np.ndarray,
        *,
        style: str | np.ndarray = "flute",
        prompt: str | None = None,
        reference: np.ndarray | None = None,
        reference_sr: int = SR,
        block_size: int = 131072,
        sample_rate: int = SR,
        overlap: float = 0.5,
    ) -> np.ndarray:
        """Timbre-transfer ``audio`` using overlap-add synthesis.

        Pass exactly one of ``style``, ``prompt``, or ``reference``.

        Args:
            audio:        Float32 array in [-1, 1].
            style:        Named profile string or pre-computed embedding.
            prompt:       Natural-language description (calls Mistral).
            reference:    Raw reference clip for ad-hoc style.
            reference_sr: Sample rate of ``reference``.
            block_size:   Samples per block at ``sample_rate``.
            sample_rate:  Sample rate of ``audio``.
            overlap:      Overlap fraction (0.5 recommended).
        """
        audio   = audio.astype(np.float32)
        style_t = self._resolve(style, prompt, reference, reference_sr)

        if sample_rate != SR:
            audio_sr = librosa.resample(audio, orig_sr=sample_rate, target_sr=SR)
            block_sr = max(1, int(round(block_size * SR / sample_rate)))
        else:
            audio_sr, block_sr = audio, block_size

        hop  = max(1, int(block_sr * (1.0 - overlap)))
        win  = np.hanning(block_sr).astype(np.float32)
        out  = np.zeros(len(audio_sr) + block_sr, dtype=np.float32)
        wsum = np.zeros_like(out)

        for start in range(0, len(audio_sr), hop):
            block = audio_sr[start : start + block_sr]
            if len(block) < block_sr:
                block = np.pad(block, (0, block_sr - len(block)))
            y = self._process_chunk(block * win, style_t)
            y = y[:block_sr]
            if len(y) < block_sr:
                y = np.pad(y, (0, block_sr - len(y)))
            out[start : start + block_sr]  += y * win
            wsum[start : start + block_sr] += win * win

        mask = wsum > 1e-8
        out[mask] /= wsum[mask]
        out = out[: len(audio_sr)]

        peak = np.abs(out).max()
        if peak > 1e-8:
            out /= peak / 0.95

        if sample_rate != SR:
            out = librosa.resample(out, orig_sr=SR, target_sr=sample_rate)
            out = out[: len(audio)]

        return out
