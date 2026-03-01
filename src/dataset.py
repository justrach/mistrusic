"""Dataset loader for (carrier, target) mel pairs with style embeddings.

Returns plain numpy arrays — no framework dependency.

Expected layout under ``data_dir``::

    metadata.json   [{"carrier": "sound_files/.../x.wav",
                      "output":  "sound_files/.../y.wav",
                      "style":   "flute"}, ...]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from .model import SR, compute_mel


class VocoderDataset:
    """Loads (carrier, target) audio pairs with pre-computed style embeddings.

    Args:
        data_dir:        Root directory containing ``metadata.json``.
        profiles:        Dict mapping style name → numpy embedding (N_MELS,).
        sr:              Working sample rate.
        segment_samples: Fixed window length in samples.
    """

    def __init__(
        self,
        data_dir: str | Path,
        profiles: dict[str, np.ndarray],
        sr: int = SR,
        segment_samples: int = 32768,
    ) -> None:
        self.root = Path(data_dir)
        self.profiles = profiles
        self.sr = sr
        self.seg = segment_samples

        meta_path = self.root / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"metadata.json not found in {self.root}")
        with open(meta_path) as f:
            self.meta: list[dict[str, Any]] = json.load(f)

        known = set(profiles.keys())
        bad = {item.get("style", "") for item in self.meta} - known
        if bad:
            raise ValueError(f"Styles in metadata not in profiles: {bad}")

    def __len__(self) -> int:
        return len(self.meta)

    def _load(self, rel: str) -> np.ndarray:
        audio, file_sr = sf.read(str(self.root / rel), dtype="float32", always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if file_sr != self.sr:
            import librosa
            audio = librosa.resample(audio, orig_sr=file_sr, target_sr=self.sr)
        return audio

    def _segment(self, a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        n = min(len(a), len(b))
        if n < self.seg:
            return np.pad(a[:n], (0, self.seg - n)), np.pad(b[:n], (0, self.seg - n))
        start = int(np.random.randint(0, n - self.seg + 1))
        return a[start:start + self.seg], b[start:start + self.seg]

    def __getitem__(self, idx: int) -> dict[str, np.ndarray]:
        item = self.meta[idx]
        carrier = self._load(item["carrier"])
        target  = self._load(item["output"])
        carrier, target = self._segment(carrier, target)
        return {
            "carrier_mel": compute_mel(carrier, self.sr),   # (N_MELS, T)
            "target_mel":  compute_mel(target,  self.sr),   # (N_MELS, T)
            "style_emb":   self.profiles[item["style"]],    # (N_MELS,)
        }
