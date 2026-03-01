#!/usr/bin/env python3
"""Mistrusic Cascade — Mistral-directed musical journey generator.

Mistral picks progressions from an indexed library, assigns timbres,
and the vocoder chains them into one continuous audio piece.

Usage::

    export MISTRAL_API_KEY=sk-...
    python cascade.py --journey "start melancholic and sparse, build to triumphant brass"
    python cascade.py --journey "dreamy flute intro, warm jazz middle, cinematic strings outro"
"""
from __future__ import annotations

import argparse, json, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import soundfile as sf
import mlx.core as mx

from src.model import load_checkpoint, compute_mel, mel_to_audio, N_MELS
from src.style_profiles import load_profiles
from openai import OpenAI

MIDI_DIR = Path("/Users/rachpradhan/Downloads/Free-Chord-Progressions-main/EDM Progressions")
RAW_DIR  = Path("audio/edm_raw")
IDX_FILE = Path("audio/edm_index.json")

# ── Feature extraction ───────────────────────────────────────────────────────

def extract_features(wav_path: Path) -> dict:
    """Extract musical features from a rendered progression."""
    audio, sr = sf.read(str(wav_path), dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if len(audio) < 1024:
        return None

    mel = compute_mel(audio, sr=sr)          # (80, T)
    energy   = float(np.mean(mel ** 2))
    brightness = float(np.mean(mel[40:]))    # upper half = brightness
    darkness   = float(np.mean(mel[:20]))    # lower = warmth/bass
    spread     = float(np.std(mel))          # spectral spread / complexity
    duration   = round(len(audio) / sr, 2)

    return {
        "energy":     round(energy, 4),
        "brightness": round(brightness, 4),
        "darkness":   round(darkness, 4),
        "spread":     round(spread, 4),
        "duration":   duration,
    }


def build_index(force: bool = False) -> list[dict]:
    if IDX_FILE.exists() and not force:
        return json.loads(IDX_FILE.read_text())

    print("Building MIDI index...")
    index = []
    def _proc(n):
        wav = RAW_DIR / f"prog_{n:03d}.wav"
        if not wav.exists():
            return None
        feats = extract_features(wav)
        if feats is None:
            return None
        return {"id": n, "wav": str(wav), **feats}

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(_proc, range(1, 101)))

    index = [r for r in results if r]
    IDX_FILE.parent.mkdir(parents=True, exist_ok=True)
    IDX_FILE.write_text(json.dumps(index, indent=2))
    print(f"Indexed {len(index)} progressions → {IDX_FILE}")
    return index


# ── Mistral cascade planning ─────────────────────────────────────────────────

_SYSTEM = """\
You are a music director planning a seamless musical journey.

You have a library of chord progressions with audio features and a set of
instrument timbres. Given a journey description, select 4-6 progressions
that together form a compelling arc, and assign a timbre to each.

Available timbres: flute, clarinet, violin, cello, trumpet, sax_alto, sax_tenor, oboe.
You may blend 2-3 instruments per segment using weights summing to 1.0.

Output a JSON array of segment objects, each with:
  - "id": progression number (integer)
  - "timbre": {instrument: weight, ...}  (weights sum to 1.0)
  - "reason": one short sentence why this fits here

Example:
[
  {"id": 7,  "timbre": {"cello": 0.7, "violin": 0.3},   "reason": "Opens with melancholic strings"},
  {"id": 23, "timbre": {"clarinet": 0.6, "flute": 0.4}, "reason": "Brightens into woodwind warmth"},
  {"id": 41, "timbre": {"trumpet": 0.8, "oboe": 0.2},   "reason": "Climaxes with triumphant brass"}
]

Respond with valid JSON array ONLY.
"""


def plan_cascade(journey: str, index: list[dict], client: OpenAI) -> list[dict]:
    # Summarise index for Mistral (keep token count manageable)
    summary = []
    for item in index:
        summary.append(
            f"#{item['id']:03d}: energy={item['energy']:.3f} "
            f"brightness={item['brightness']:.3f} "
            f"darkness={item['darkness']:.3f} "
            f"spread={item['spread']:.3f} "
            f"dur={item['duration']}s"
        )

    user_msg = (
        f"Journey: \"{journey}\"\n\n"
        f"Library ({len(index)} progressions):\n" +
        "\n".join(summary)
    )

    resp = client.chat.completions.create(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.4,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content.strip()
    # Mistral might wrap the array in an object
    parsed = json.loads(content)
    if isinstance(parsed, list):
        return parsed
    # Unwrap if it's {"segments": [...]} or similar
    for v in parsed.values():
        if isinstance(v, list):
            return v
    return list(parsed.values())


# ── Audio synthesis ──────────────────────────────────────────────────────────

def crossfade(a: np.ndarray, b: np.ndarray, fade_samples: int = 4410) -> np.ndarray:
    """Crossfade two mono arrays."""
    f = min(fade_samples, len(a), len(b))
    ramp_out = np.linspace(1, 0, f)
    ramp_in  = np.linspace(0, 1, f)
    a_fade = a.copy(); a_fade[-f:] *= ramp_out
    b_fade = b.copy(); b_fade[:f]  *= ramp_in
    overlap = a_fade[-f:] + b_fade[:f]
    return np.concatenate([a_fade[:-f], overlap, b_fade[f:]])


def render_segment(
    wav_path: str,
    timbre: dict[str, float],
    model,
    profiles: dict,
) -> np.ndarray:
    audio, sr = sf.read(wav_path, dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Blend style embedding
    dim = next(iter(profiles.values())).shape[0]
    emb = np.zeros(dim, dtype=np.float32)
    for name, w in timbre.items():
        if name in profiles:
            emb += w * profiles[name]

    mel     = compute_mel(audio, sr=sr)
    carrier = mx.array(mel.T[None])
    style_t = mx.array(emb[None])
    pred    = model(carrier, style_t)
    pred_np = np.array(pred[0]).T

    audio_out = mel_to_audio(pred_np, sr=sr, n_iter=128)
    peak = np.abs(audio_out).max()
    if peak > 1e-8:
        audio_out /= peak / 0.95
    return audio_out, sr


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Mistrusic Cascade")
    ap.add_argument("--journey",    required=True,
                    help="Describe the musical journey you want")
    ap.add_argument("--checkpoint", default="checkpoints/best")
    ap.add_argument("--profiles",   default="profiles.npz")
    ap.add_argument("--output",     default="audio/cascade_output.wav")
    ap.add_argument("--reindex",    action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("Error: set MISTRAL_API_KEY"); return

    print(f'\n=== Mistrusic Cascade ===')
    print(f'Journey : "{args.journey}"\n')

    # 1. Index
    index = build_index(force=args.reindex)
    print(f"Library : {len(index)} progressions indexed")

    # 2. Mistral plans the cascade
    client = OpenAI(base_url="https://api.mistral.ai/v1", api_key=api_key)
    print("Mistral : planning cascade...")
    plan = plan_cascade(args.journey, index, client)

    print(f"\nPlan ({len(plan)} segments):")
    for seg in plan:
        blend = ", ".join(f"{k}={v:.2f}" for k, v in seg["timbre"].items())
        print(f"  #{seg['id']:03d}  [{blend}]  — {seg.get('reason','')}")

    # 3. Load model + profiles
    model, _ = load_checkpoint(args.checkpoint)
    model.eval()
    profiles = load_profiles(args.profiles)

    # Build lookup
    id_to_wav = {item["id"]: item["wav"] for item in index}

    # 4. Render each segment
    print("\nRendering segments...")
    segments = []
    out_sr = 22050
    for seg in plan:
        pid = int(seg["id"])
        wav = id_to_wav.get(pid)
        if not wav:
            print(f"  #{pid:03d} not found, skipping"); continue
        audio_out, out_sr = render_segment(wav, seg["timbre"], model, profiles)
        segments.append(audio_out)
        blend = ", ".join(f"{k}={v:.2f}" for k, v in seg["timbre"].items())
        print(f"  #{pid:03d} → {len(audio_out)/out_sr:.1f}s  [{blend}]")

    if not segments:
        print("No segments rendered."); return

    # 5. Crossfade and concatenate
    result = segments[0]
    for seg in segments[1:]:
        result = crossfade(result, seg)

    # Normalize
    peak = np.abs(result).max()
    if peak > 1e-8:
        result /= peak / 0.95

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, result, out_sr)
    print(f"\nOutput  : {args.output}  ({len(result)/out_sr:.1f}s total)")
    print("Done!")


if __name__ == "__main__":
    main()
