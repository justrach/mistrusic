#!/usr/bin/env python3
"""Mistrusic Splicer — DJ-style compilation from all rendered WAVs.

Mistral picks the playback order, then we extract the most energetic
window from each track and splice them together with smooth crossfades.

Usage::

    export MISTRAL_API_KEY=...
    python splice.py                        # default 10s clips
    python splice.py --clip 15 --fade 2.5  # longer clips, 2.5s fade
    python splice.py --clip 6  --fade 1    # shorter, punchier
"""
from __future__ import annotations

import argparse, json, os, random, time
from pathlib import Path

import numpy as np
import soundfile as sf
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

IDX_FILE = Path("audio/edm_index.json")
SR       = 22050

# ── Audio helpers ─────────────────────────────────────────────────────────────

def load_mono(path: Path) -> np.ndarray:
    audio, _ = sf.read(str(path), dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio


def best_window(audio: np.ndarray, clip_samples: int) -> np.ndarray:
    """Return the most energetic window of length clip_samples."""
    if len(audio) <= clip_samples:
        return audio
    step   = clip_samples // 4
    best   = 0.0
    best_i = 0
    for i in range(0, len(audio) - clip_samples, step):
        e = float(np.mean(audio[i:i + clip_samples] ** 2))
        if e > best:
            best, best_i = e, i
    return audio[best_i: best_i + clip_samples]


def apply_fades(clip: np.ndarray, fade_samples: int) -> np.ndarray:
    f = min(fade_samples, len(clip) // 4)
    clip = clip.copy()
    clip[:f]  *= np.linspace(0, 1, f)
    clip[-f:] *= np.linspace(1, 0, f)
    return clip


def crossfade(a: np.ndarray, b: np.ndarray, fade_samples: int) -> np.ndarray:
    f = min(fade_samples, len(a), len(b))
    ramp_out = np.linspace(1, 0, f)
    ramp_in  = np.linspace(0, 1, f)
    a_fade = a.copy(); a_fade[-f:] *= ramp_out
    b_fade = b.copy(); b_fade[:f]  *= ramp_in
    overlap = a_fade[-f:] + b_fade[:f]
    return np.concatenate([a_fade[:-f], overlap, b_fade[f:]])


# ── Track discovery ───────────────────────────────────────────────────────────

def discover_tracks() -> list[dict]:
    """Return all renderable wav paths with a short label."""
    tracks = []

    edm_index = {}
    if IDX_FILE.exists():
        for e in json.loads(IDX_FILE.read_text()):
            edm_index[e["id"]] = e

    for n in range(1, 101):
        p = Path(f"audio/edm_raw/prog_{n:03d}.wav")
        if not p.exists(): continue
        feat = edm_index.get(n, {})
        tracks.append({
            "path":  p,
            "label": f"EDM#{n:03d}",
            "energy": feat.get("energy", 0.5),
            "brightness": feat.get("brightness", 0),
        })

    for p in sorted(Path("audio/altered").glob("*.wav")):
        key = p.stem.replace("_Altered_Dominant", "").replace("_","").strip()
        tracks.append({"path": p, "label": f"Altered-{key}", "energy": 0.35, "brightness": -0.5})

    for p in sorted(Path("audio/more_genres").glob("*.wav")):
        tracks.append({"path": p, "label": p.stem.replace("_"," "), "energy": 0.45, "brightness": -0.6})

    return tracks


# ── Mistral ordering ──────────────────────────────────────────────────────────

_SYS_ORDER = """\
You are a DJ curating a seamless, emotionally compelling mix.
Given a list of tracks with energy and brightness scores, select
30-40 of them and arrange them in a journey that:
  1. Opens gently (low energy)
  2. Builds through the middle
  3. Peaks with high-energy tracks
  4. Gradually winds down to a cool ending

Return a JSON object: {"sequence": [list of label strings in order]}.
Use labels exactly as given. No duplicates. Valid JSON only.
"""

def plan_order(tracks: list[dict], client: OpenAI) -> list[str]:
    lines = [
        f"{t['label']}: energy={t['energy']:.3f} brightness={t['brightness']:.3f}"
        for t in tracks
    ]
    resp = client.chat.completions.create(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": _SYS_ORDER},
            {"role": "user",   "content": "\n".join(lines)},
        ],
        temperature=0.5,
        max_tokens=1200,
        response_format={"type": "json_object"},
    )
    raw  = json.loads(resp.choices[0].message.content.strip())
    seq  = raw.get("sequence") or raw.get("order") or list(raw.values())[0]
    return [str(s) for s in seq]


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Mistrusic Splicer")
    ap.add_argument("--clip",   type=float, default=10.0,  help="Clip length in seconds (default: 10)")
    ap.add_argument("--fade",   type=float, default=2.0,   help="Crossfade length in seconds (default: 2)")
    ap.add_argument("--output", default="audio/splice.wav")
    ap.add_argument("--no-mistral", action="store_true",   help="Skip Mistral ordering (use random)")
    args = ap.parse_args()

    CLIP = int(args.clip * SR)
    FADE = int(args.fade * SR)

    api_key = os.environ.get("MISTRAL_API_KEY", "")
    tracks  = discover_tracks()
    label_map = {t["label"]: t for t in tracks}

    print(f"\n=== Mistrusic Splicer ===")
    print(f"  Clip    : {args.clip:.1f}s  |  Fade: {args.fade:.1f}s")
    print(f"  Library : {len(tracks)} tracks\n")

    if api_key and not args.no_mistral:
        print("Mistral : planning order...")
        t0 = time.time()
        try:
            sequence_labels = plan_order(tracks, OpenAI(base_url="https://api.mistral.ai/v1", api_key=api_key))
            # resolve labels → dicts, drop unknowns
            sequence = [label_map[l] for l in sequence_labels if l in label_map]
            print(f"          {len(sequence)} tracks selected in {int((time.time()-t0)*1000)}ms\n")
        except Exception as ex:
            print(f"          [!] Mistral error: {ex} — using random order\n")
            sequence = random.sample(tracks, min(35, len(tracks)))
    else:
        print("Ordering: random (no Mistral)\n")
        sequence = random.sample(tracks, min(35, len(tracks)))

    print("Rendering clips:")
    clips = []
    for t in sequence:
        audio = load_mono(t["path"])
        clip  = best_window(audio, CLIP)
        clip  = apply_fades(clip, FADE)
        clips.append(clip)
        dur   = len(clip) / SR
        print(f"  {t['label']:<25}  {dur:.1f}s")

    if not clips:
        print("No clips rendered."); return

    print("\nSplicing...")
    result = clips[0]
    for clip in clips[1:]:
        result = crossfade(result, clip, FADE)

    # Final normalize
    peak = np.abs(result).max()
    if peak > 1e-8:
        result /= peak / 0.92

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, result, SR)
    total = len(result) / SR
    print(f"\nOutput  : {args.output}  ({total/60:.1f}m {total%60:.0f}s, {len(clips)} tracks)")
    print("Done!")


if __name__ == "__main__":
    main()
