#!/usr/bin/env python3
"""Tag all rendered WAV files with ID3 metadata via Mistral.

Generates titles, genres, moods, and descriptions for every track
and embeds them using mutagen. Also tags the splice + big_song composites.

Usage::

    export MISTRAL_API_KEY=...
    python tag_tracks.py
"""
from __future__ import annotations

import json, os, time
from pathlib import Path

import numpy as np
from openai import OpenAI
from mutagen.wave import WAVE
from mutagen.id3 import (
    ID3NoHeaderError, TIT2, TPE1, TALB, TCON, COMM, TXXX
)

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY   = os.environ.get("MISTRAL_API_KEY", "")
MODEL     = "mistral-small-latest"
ALBUM     = "Mistrusic"
ARTIST    = "Mistrusic / Mistral AI"

IDX_FILE  = Path("audio/edm_index.json")

# ── Mistral helpers ───────────────────────────────────────────────────────────

_SYS = """\
You are a music metadata expert. Given a list of audio tracks with their \
audio features or names, output a JSON array where each element has:
  - "title":  short evocative track title (3-6 words, title case)
  - "genre":  one genre tag (e.g. "EDM", "Jazz", "Cinematic", "Reggae", "Trap")
  - "mood":   2-3 mood words separated by commas (e.g. "dark, driving, tense")
  - "bpm":    estimated BPM as integer (80-170 range; use audio energy as hint)
  - "desc":   one sentence describing the track (≤20 words)

Output valid JSON array ONLY. One object per input track, same order.
"""

def _ask_mistral(client: OpenAI, tracks: list[dict]) -> list[dict]:
    """Send a batch of track descriptors to Mistral and get metadata back."""
    user_lines = []
    for i, t in enumerate(tracks):
        user_lines.append(f"{i}: {t['hint']}")

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYS},
            {"role": "user",   "content": "\n".join(user_lines)},
        ],
        temperature=0.5,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content.strip()
    parsed = json.loads(raw)
    # unwrap if Mistral wraps in object
    if isinstance(parsed, list):
        return parsed
    for v in parsed.values():
        if isinstance(v, list):
            return v
    return list(parsed.values())


# ── WAV tagging ───────────────────────────────────────────────────────────────

def tag_wav(path: Path, meta: dict) -> None:
    try:
        audio = WAVE(str(path))
    except Exception as e:
        print(f"  [!] Could not open {path}: {e}")
        return

    # Ensure ID3 header exists
    try:
        audio.tags.delete(str(path))
    except Exception:
        pass
    audio.add_tags()

    tags = audio.tags
    tags.add(TIT2(encoding=3, text=meta.get("title", path.stem)))
    tags.add(TPE1(encoding=3, text=ARTIST))
    tags.add(TALB(encoding=3, text=ALBUM))
    tags.add(TCON(encoding=3, text=meta.get("genre", "")))
    tags.add(COMM(encoding=3, lang="eng", desc="", text=meta.get("desc", "")))

    # Custom frames
    for key, val in [
        ("mood",  meta.get("mood", "")),
        ("bpm",   str(meta.get("bpm", ""))),
        ("source","Mistrusic / Mistral AI"),
    ]:
        tags.add(TXXX(encoding=3, desc=key, text=val))

    audio.save()


# ── Track collectors ──────────────────────────────────────────────────────────

def _feat_hint(entry: dict) -> str:
    """Human-readable feature summary for Mistral prompt."""
    e  = entry["energy"]
    br = entry["brightness"]
    dk = entry["darkness"]
    sp = entry["spread"]
    dur = entry["duration"]
    energy_word = "high-energy" if e > 0.5 else ("mid-energy" if e > 0.3 else "low-energy")
    bright_word = "bright" if br > -0.7 else "dark"
    return (
        f"EDM chord progression #{entry['id']:03d}, {energy_word}, "
        f"{bright_word} tone, spread={sp:.2f}, duration={dur:.0f}s"
    )


def collect_tracks(edm_index: list[dict]) -> list[dict]:
    """Build a flat list of {path, hint} dicts for all tracks."""
    tracks = []

    # --- EDM raw progressions ---
    id_map = {e["id"]: e for e in edm_index}
    for n in range(1, 101):
        p = Path(f"audio/edm_raw/prog_{n:03d}.wav")
        if not p.exists():
            continue
        entry = id_map.get(n, {})
        hint  = _feat_hint(entry) if entry else f"EDM chord progression #{n:03d}"
        tracks.append({"path": p, "hint": hint})

    # --- Altered Dominant ---
    for p in sorted(Path("audio/altered").glob("*.wav")):
        key = p.stem.replace("_Altered_Dominant", "").replace("_", "").strip()
        tracks.append({
            "path": p,
            "hint": f"Jazz altered dominant chord in {key}, chromatic tension, modal jazz",
        })

    # --- More Genres ---
    for p in sorted(Path("audio/more_genres").glob("*.wav")):
        name = p.stem.replace("_", " ")
        tracks.append({
            "path": p,
            "hint": f"{name} chord progression, rhythmic, genre-specific feel",
        })

    # --- Composite tracks ---
    composites = [
        (Path("audio/splice.wav"),
         "DJ splice compilation — 26 × 3-second clips from EDM, jazz, and genre progressions, "
         "tight crossfades, energetic journey"),
        (Path("audio/big_song.wav"),
         "Full composed song — Mistral-curated chord progression arc, "
         "verse/chorus/bridge structure, dynamic build"),
        (Path("audio/song.wav"),
         "Rendered song arrangement from MIDI chord progressions"),
        (Path("audio/cascade_output.wav"),
         "Mistral-directed musical cascade — 5 EDM progressions blended with instrument timbres"),
    ]
    for p, hint in composites:
        if p.exists():
            tracks.append({"path": p, "hint": hint})

    return tracks


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not API_KEY:
        print("Error: set MISTRAL_API_KEY"); return

    client = OpenAI(base_url="https://api.mistral.ai/v1", api_key=API_KEY)

    edm_index = json.loads(IDX_FILE.read_text()) if IDX_FILE.exists() else []
    tracks    = collect_tracks(edm_index)
    print(f"Found {len(tracks)} WAV files to tag\n")

    # Batch into groups of 25 (keep Mistral responses tight)
    BATCH = 25
    all_meta: list[dict] = []
    for i in range(0, len(tracks), BATCH):
        batch = tracks[i:i + BATCH]
        print(f"  Mistral → batch {i//BATCH + 1} ({len(batch)} tracks)...", end=" ", flush=True)
        t0 = time.time()
        try:
            meta = _ask_mistral(client, batch)
            # Pad if Mistral returns fewer items
            while len(meta) < len(batch):
                meta.append({"title": batch[len(meta)]["path"].stem,
                             "genre": "EDM", "mood": "electronic",
                             "bpm": 120, "desc": "Chord progression."})
            all_meta.extend(meta[:len(batch)])
            print(f"done in {int((time.time()-t0)*1000)}ms")
        except Exception as ex:
            print(f"ERROR: {ex}")
            all_meta.extend([{"title": t["path"].stem, "genre": "EDM",
                              "mood": "", "bpm": 120, "desc": ""} for t in batch])
        time.sleep(0.3)  # be polite

    # Write tags
    print(f"\nWriting ID3 tags...")
    ok = 0
    for track, meta in zip(tracks, all_meta):
        p = track["path"]
        tag_wav(p, meta)
        print(f"  {p.name:<40}  \"{meta.get('title','')}\"  [{meta.get('genre','')}] {meta.get('mood','')}")
        ok += 1

    print(f"\n✓ Tagged {ok}/{len(tracks)} files")
    print("Done!")


if __name__ == "__main__":
    main()
