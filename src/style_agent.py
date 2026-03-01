"""Natural-language style control via Mistral (La Plateforme or LM Studio).

Set MISTRAL_API_KEY env var for Mistral's real API, or use --lm-url for
a local LM Studio server.

Example::

    # Mistral cloud (recommended for demo)
    export MISTRAL_API_KEY=your_key_here
    python -m src.infer --checkpoint checkpoints/best --profiles profiles.npz \
        --input audio/gb_altered_piano.wav \
        --prompt "warm smoky jazz saxophone with a hint of muted trumpet" \
        --output audio/jazz_sax.wav --reverb

    # Local LM Studio
    python -m src.infer ... --lm-url http://localhost:1234/v1
"""
from __future__ import annotations

import json
import os

import numpy as np
from openai import OpenAI

_SYSTEM = """\
You are an expert music producer specialising in instrument timbre and tone.
You map natural-language style descriptions to blends of instrument profiles.

Given a list of available instrument profiles and a user request, output a
JSON object whose keys are instrument names (from the available list only) and
whose values are non-negative weights that sum to exactly 1.0.

Rules:
- Only use instruments from the provided list.
- Weights must sum to 1.0 (normalise if unsure).
- Include at most 3 instruments; omit any with weight < 0.05.
- Respond with valid JSON ONLY — no prose, no markdown fences.

Example response: {"sax_tenor": 0.6, "clarinet": 0.4}
"""

# Mistral model to use when hitting the real API
_MISTRAL_MODEL = "mistral-small-latest"


class StyleAgent:
    """Maps a text prompt to a blended style embedding.

    Automatically selects backend:
    - MISTRAL_API_KEY set → Mistral La Plateforme (cloud)
    - Otherwise → local LM Studio at base_url

    Args:
        base_url: LM Studio endpoint (ignored if MISTRAL_API_KEY is set).
        model:    Override model ID. None = auto-detect.
        timeout:  Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if api_key:
            self.client = OpenAI(
                base_url="https://api.mistral.ai/v1",
                api_key=api_key,
                timeout=timeout,
            )
            self._model = model or _MISTRAL_MODEL
            self._cloud = True
        else:
            self.client = OpenAI(
                base_url=base_url,
                api_key=os.environ.get("LM_STUDIO_API_KEY", "lm-studio"),
                timeout=timeout,
            )
            self._model = model
            self._cloud = False
        self._cached_model: str | None = None

    @property
    def model(self) -> str:
        if self._model:
            return self._model
        if not self._cached_model:
            models = self.client.models.list().data
            if not models:
                raise RuntimeError("No models found on the local server")
            self._cached_model = models[0].id
            print(f"[StyleAgent] Using model: {self._cached_model}")
        return self._cached_model

    def resolve_style(
        self,
        prompt: str,
        profiles: dict[str, np.ndarray],
    ) -> tuple[np.ndarray, dict[str, float]]:
        """Map a natural-language prompt to a blended profile embedding.

        Args:
            prompt:   Free-text style description.
            profiles: Dict of available instrument embeddings.

        Returns:
            (embedding, weights) tuple.
        """
        available = sorted(profiles.keys())
        user_msg = (
            f"Available instruments: {available}\n"
            f'Style request: "{prompt}"'
        )

        kwargs: dict = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=128,
        )
        # json_object response_format works on both Mistral cloud and LM Studio
        if self._cloud:
            kwargs["response_format"] = {"type": "json_object"}

        resp = self.client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content.strip()

        # Strip any accidental markdown fences
        if content.startswith("```"):
            content = content.split("```")[1].lstrip("json").strip()

        raw = json.loads(content)

        weights = {k: float(v) for k, v in raw.items() if k in profiles and float(v) > 0}
        if not weights:
            weights = {available[0]: 1.0}
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        dim = next(iter(profiles.values())).shape[0]
        blended = np.zeros(dim, dtype=np.float32)
        for name, w in weights.items():
            blended += w * profiles[name]

        return blended, weights
