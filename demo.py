#!/usr/bin/env python3
"""Mistrusic Demo — Mistral-powered instrument timbre transfer.

Set MISTRAL_API_KEY to use Mistral cloud, or start LM Studio for local.
Without either, --offline uses hardcoded style blends for demonstration.

Usage (with Mistral cloud)::

    export MISTRAL_API_KEY=sk-...
    python demo.py --input audio/gb_altered_piano.wav

Usage (offline showcase)::

    python demo.py --input audio/gb_altered_piano.wav --offline
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import mlx.core as mx

from src.model import load_checkpoint, compute_mel, mel_to_audio, mel_to_audio_with_phase, add_reverb
from src.style_profiles import load_profiles

# ── Creative prompts + their Mistral-resolved blends ────────────────────────
# (offline fallback: manually curated blends that mirror what Mistral would pick)
DEMO_PROMPTS = [
    {
        "slug":    "warm_jazz_sax",
        "prompt":  "warm smoky jazz saxophone, late-night club vibes",
        "offline": {"sax_tenor": 0.65, "clarinet": 0.35},
    },
    {
        "slug":    "melancholic_strings",
        "prompt":  "melancholic cello with a hint of violin, cinematic sadness",
        "offline": {"cello": 0.70, "violin": 0.30},
    },
    {
        "slug":    "bright_woodwind",
        "prompt":  "bright airy flute and oboe, sunlit morning forest",
        "offline": {"flute": 0.60, "oboe": 0.40},
    },
    {
        "slug":    "brass_fanfare",
        "prompt":  "triumphant brass fanfare — bold trumpet with an oboe undertone",
        "offline": {"trumpet": 0.75, "oboe": 0.25},
    },
    {
        "slug":    "chamber_ensemble",
        "prompt":  "intimate chamber ensemble: violin, cello and clarinet",
        "offline": {"violin": 0.40, "cello": 0.35, "clarinet": 0.25},
    },
]


def blend_profiles(weights: dict[str, float], profiles: dict[str, np.ndarray]) -> np.ndarray:
    dim = next(iter(profiles.values())).shape[0]
    emb = np.zeros(dim, dtype=np.float32)
    for name, w in weights.items():
        emb += w * profiles[name]
    return emb


def run_one(
    model,
    profiles: dict,
    audio: np.ndarray,
    src_sr: int,
    weights: dict[str, float],
    out_path: Path,
) -> None:
    emb     = blend_profiles(weights, profiles)
    style_t = mx.array(emb[None])
    mel     = compute_mel(audio, sr=src_sr)
    carrier = mx.array(mel.T[None])
    pred    = model(carrier, style_t)
    pred_np = np.array(pred[0]).T

    audio_out = mel_to_audio(pred_np, sr=src_sr, n_iter=128)
    peak = np.abs(audio_out).max()
    if peak > 1e-8:
        audio_out /= peak / 0.95

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), audio_out, src_sr)


def main() -> None:
    ap = argparse.ArgumentParser(description="Mistrusic demo")
    ap.add_argument("--input",      required=True)
    ap.add_argument("--checkpoint", default="checkpoints/best")
    ap.add_argument("--profiles",   default="profiles.npz")
    ap.add_argument("--out-dir",    default="audio/demo")
    ap.add_argument("--lm-url",     default="http://localhost:1234/v1")
    ap.add_argument("--offline",    action="store_true",
                    help="Skip Mistral API; use curated blends for demo")
    ap.add_argument("--prompt",     default=None,
                    help="Single custom prompt (requires Mistral API)")
    args = ap.parse_args()

    use_mistral = not args.offline and (
        os.environ.get("MISTRAL_API_KEY") or args.lm_url
    )

    print(f"\n=== Mistrusic: Mistral-powered Timbre Transfer ===")
    if args.offline:
        print("   Mode    : offline (curated blends)")
    elif os.environ.get("MISTRAL_API_KEY"):
        print("   Mode    : Mistral La Plateforme (cloud)")
    else:
        print(f"   Mode    : LM Studio @ {args.lm_url}")
    print(f"   Input   : {args.input}\n")

    model, _ = load_checkpoint(args.checkpoint)
    model.eval()
    profiles = load_profiles(args.profiles)
    audio, src_sr = sf.read(args.input, dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if args.prompt:
        # Single custom prompt — needs Mistral
        from src.style_agent import StyleAgent
        agent = StyleAgent(base_url=args.lm_url)
        t0 = time.time()
        emb, weights = agent.resolve_style(args.prompt, profiles)
        ms = int((time.time() - t0) * 1000)
        out = Path(args.out_dir) / "custom.wav"
        run_one(model, profiles, audio, src_sr, weights, out)
        blend_str = ", ".join(f"{k}={v:.2f}" for k, v in weights.items())
        print(f'  Prompt : "{args.prompt}"')
        print(f"  Mistral: {blend_str}  ({ms}ms)")
        print(f"  Output : {out}")
        return

    agent = None
    if use_mistral and not args.offline:
        try:
            from src.style_agent import StyleAgent
            agent = StyleAgent(base_url=args.lm_url)
        except Exception:
            print("  [!] Could not connect to Mistral — falling back to offline mode\n")

    for item in DEMO_PROMPTS:
        prompt = item["prompt"]
        print(f'  Prompt : "{prompt}"')

        if agent:
            t0 = time.time()
            _, weights = agent.resolve_style(prompt, profiles)
            ms = int((time.time() - t0) * 1000)
            source = f"Mistral ({ms}ms)"
        else:
            weights = item["offline"]
            source  = "curated blend"

        blend_str = ", ".join(f"{k}={v:.2f}" for k, v in weights.items())
        print(f"  Blend  : {blend_str}  [{source}]")

        out = Path(args.out_dir) / f"{item['slug']}.wav"
        run_one(model, profiles, audio, src_sr, weights, out)
        print(f"  Output : {out}\n")

    print("Done! Play the files in", args.out_dir)


if __name__ == "__main__":
    main()
