"""Offline single-file inference with optional Mistral style prompting.

Examples::

    # Named style, carrier-phase reconstruction (default — smoother)
    python -m src.infer \\
        --checkpoint checkpoints/best \\
        --profiles profiles.npz \\
        --input guitar.wav \\
        --style flute \\
        --output out.wav

    # Add reverb for spaciousness
    python -m src.infer ... --reverb

    # Natural-language prompt via local Mistral (LM Studio)
    python -m src.infer ... --prompt \"warm smoky jazz saxophone\" --reverb
"""
from __future__ import annotations

import argparse

import numpy as np
import soundfile as sf
import mlx.core as mx

from .model import (
    load_checkpoint, compute_mel,
    mel_to_audio_with_phase, mel_to_audio,
    add_reverb, SR,
)
from .style_profiles import load_profiles, encode_reference


def infer(args: argparse.Namespace) -> None:
    model, _ = load_checkpoint(args.checkpoint)
    model.eval()

    profiles = load_profiles(args.profiles)

    # ── Resolve style embedding ───────────────────────────────────────────────
    if args.prompt:
        from .style_agent import StyleAgent
        agent = StyleAgent(base_url=args.lm_url, model=args.lm_model)
        style_emb, weights = agent.resolve_style(args.prompt, profiles)
        print(f"Style blend: { {k: round(v, 3) for k, v in weights.items()} }")
    elif args.style:
        if args.style not in profiles:
            raise ValueError(
                f"Style '{args.style}' not in profiles. Available: {sorted(profiles)}"
            )
        style_emb = profiles[args.style]
    else:
        ref, ref_sr = sf.read(args.reference, dtype="float32", always_2d=False)
        if ref.ndim > 1:
            ref = ref.mean(axis=1)
        style_emb = encode_reference(ref, ref_sr)

    # ── Load carrier ──────────────────────────────────────────────────────────
    audio, src_sr = sf.read(args.input, dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    mel     = compute_mel(audio, sr=src_sr)          # (N_MELS, T)
    carrier = mx.array(mel.T[None])                  # (1, T, N_MELS)
    style_t = mx.array(style_emb[None])              # (1, N_MELS)

    # ── Model forward ──────────────────────────────────────────────────────────
    pred    = model(carrier, style_t)                # (1, T, N_MELS)
    pred_np = np.array(pred[0]).T                    # (N_MELS, T)

    # Carrier-phase reconstruction (smooth) vs Griffin-Lim (fallback)
    if args.griffin_lim:
        audio_out = mel_to_audio(pred_np, sr=src_sr, n_iter=128)
    else:
        audio_out = mel_to_audio_with_phase(pred_np, audio, sr=src_sr)

    # Optional reverb
    if args.reverb:
        audio_out = add_reverb(
            audio_out, sr=src_sr,
            room_size=args.reverb_size,
            decay=args.reverb_decay,
            wet=args.reverb_wet,
        )

    peak = np.abs(audio_out).max()
    if peak > 1e-8:
        audio_out /= peak / 0.95

    out_sr = src_sr if src_sr <= 48000 else SR
    sf.write(args.output, audio_out, out_sr)
    print(f"Written: {args.output}  ({len(audio_out)/out_sr:.2f}s @ {out_sr} Hz)")


def main() -> None:
    ap = argparse.ArgumentParser(description="StyleVocoder inference")
    ap.add_argument("--checkpoint",    required=True)
    ap.add_argument("--profiles",      required=True)
    ap.add_argument("--input",         required=True)
    ap.add_argument("--output",        required=True)

    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--style",        help="Named profile")
    grp.add_argument("--reference",    help="Reference .wav for ad-hoc style")
    grp.add_argument("--prompt",       help="Natural-language style (uses Mistral)")

    ap.add_argument("--griffin-lim",   action="store_true",
                    help="Use Griffin-Lim instead of carrier-phase reconstruction")
    ap.add_argument("--reverb",        action="store_true",
                    help="Add convolution reverb for spaciousness")
    ap.add_argument("--reverb-size",   type=float, default=0.6,
                    help="Reverb room size in seconds (default 0.6)")
    ap.add_argument("--reverb-decay",  type=float, default=0.65,
                    help="Reverb decay 0-1 (default 0.65)")
    ap.add_argument("--reverb-wet",    type=float, default=0.45,
                    help="Wet/dry mix 0-1 (default 0.45)")
    ap.add_argument("--lm-url",        default="http://localhost:1234/v1")
    ap.add_argument("--lm-model",      default=None)
    infer(ap.parse_args())


if __name__ == "__main__":
    main()
