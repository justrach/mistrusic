#!/usr/bin/env python3
"""Mistrusic FastAPI server — trance pad generation with Mistral planning.

Usage::

    export MISTRAL_API_KEY=...
    uvicorn server:app --reload --port 8000
"""
from __future__ import annotations

import io, json, os, tempfile, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import numpy as np
import soundfile as sf
import scipy.signal

SR        = 22050
SF2       = "/tmp/FluidR3_GM.sf2"
MIDI_DIR  = Path("/Users/rachpradhan/Downloads/Free-Chord-Progressions-main/EDM Progressions")
IDX_FILE  = Path("audio/edm_index.json")
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY", "")

# vibe → (cache dir, GM program, fx name)
VIBE_LIBS = {
    "trance":  {"dir": Path("audio/trance_raw"),  "prefix": "trance",  "program": 90},
    "haunted": {"dir": Path("audio/haunted_raw"), "prefix": "haunted", "program": 52},
    "hiphop":  {"dir": Path("audio/hiphop_raw"),  "prefix": "hiphop",  "program": 4},
}
# which vibes each frontend chip maps to
VIBE_MAP = {
    "haunted house":   "haunted",
    "dark forest":     "haunted",
    "late night drive":"hiphop",
    "festival peak":   "trance",
    "euphoric sunrise":"trance",
    "deep ocean":      "trance",
    "space station":   "trance",
    "arctic drift":    "trance",
}
from openai import OpenAI
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

app = FastAPI(title="Mistrusic API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Plan", "X-Vibe"],
)

# ── Config ────────────────────────────────────────────────────────────────────

SR        = 22050
SF2       = "/tmp/FluidR3_GM.sf2"
MIDI_DIR  = Path("/Users/rachpradhan/Downloads/Free-Chord-Progressions-main/EDM Progressions")
TRANCE_DIR = Path("audio/trance_raw")
IDX_FILE  = Path("audio/edm_index.json")
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY", "")

# ── Mistral client ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(base_url="https://api.mistral.ai/v1", api_key=MISTRAL_KEY)

# ── Audio FX ──────────────────────────────────────────────────────────────────

def chorus(audio: np.ndarray, voices=4, depth=14, dms=20) -> np.ndarray:
    out = audio.astype(np.float64)
    for v in range(voices):
        cents = depth * (v / max(voices-1,1) - 0.5) * 2
        ratio = 2 ** (cents / 1200)
        n     = int(len(audio) * ratio)
        s     = np.interp(np.linspace(0, len(audio)-1, n), np.arange(len(audio)), audio)
        s     = s[:len(audio)] if len(s) >= len(audio) else np.pad(s, (0, len(audio)-len(s)))
        d     = int(dms * v / max(voices-1,1) * SR / 1000)
        out  += np.roll(s, d) * 0.45
    pk = np.abs(out).max()
    return (out/pk*0.90).astype(np.float32) if pk > 1e-8 else out.astype(np.float32)

def reverb_fx(audio: np.ndarray, room=6.0, decay=0.91, wet=0.68) -> np.ndarray:
    ir_len = int(room * SR)
    t  = np.linspace(0, room, ir_len)
    ir = np.random.default_rng(42).standard_normal(ir_len) * np.exp(-t*(1-decay)*5.0)
    ir[0] = 1.0; ir /= np.abs(ir).max()
    verb = scipy.signal.fftconvolve(audio, ir)[:len(audio)]
    out  = (1-wet)*audio + wet*verb
    pk   = np.abs(out).max()
    return (out/pk*0.90).astype(np.float32) if pk > 1e-8 else out.astype(np.float32)

def delay_fx(audio: np.ndarray, ms=375, fb=0.50, wet=0.38) -> np.ndarray:
    d   = int(ms * SR / 1000)
    out = audio.astype(np.float64)
    buf = np.zeros(d)
    for i in range(len(out)):
        echo=buf[i%d]; buf[i%d]=out[i]+echo*fb; out[i]+=echo*wet
    return out.astype(np.float32)

def trance_fx(audio: np.ndarray) -> np.ndarray:
    b, a = scipy.signal.butter(2, 90/(SR/2), btype='high')
    audio = scipy.signal.lfilter(b, a, audio).astype(np.float32)
    audio = chorus(audio)
    audio = reverb_fx(audio)
    audio = delay_fx(audio)
    pk = np.abs(audio).max()
    return (audio/pk*0.88).astype(np.float32) if pk > 1e-8 else audio

def to_wav_bytes(audio: np.ndarray, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()

# ── MIDI rendering ────────────────────────────────────────────────────────────

def inject_program(mid_path: Path, program: int = 90) -> Path:
    mid = mido.MidiFile(mid_path)
    new = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
    for track in mid.tracks:
        nt = mido.MidiTrack()
        done: set = set()
        for msg in track:
            if msg.type == 'note_on' and msg.channel not in done and msg.channel != 9:
                nt.append(mido.Message('program_change', channel=msg.channel, program=program, time=0))
                done.add(msg.channel)
            nt.append(msg)
        new.tracks.append(nt)
    tmp = Path(tempfile.mktemp(suffix=".mid"))
    new.save(str(tmp))
    return tmp

def render_midi_to_audio(n: int, loops: int = 4, vibe: str = "trance") -> np.ndarray | None:
    """Return cached or freshly rendered audio for MIDI n under the given vibe."""
    lib    = VIBE_LIBS.get(vibe, VIBE_LIBS["trance"])
    cached = lib["dir"] / f"{lib['prefix']}_{n:03d}.wav"
    if cached.exists():
        audio, _ = sf.read(str(cached), dtype="float32", always_2d=False)
        if audio.ndim > 1: audio = audio.mean(axis=1)
        return audio

    mid_path = MIDI_DIR / f"generated_progression_{n:03d}.mid"
    if not mid_path.exists(): return None

    tmp_mid = inject_program(mid_path, lib["program"])
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out_path = Path(f.name)
    subprocess.run(
        ["fluidsynth", "-ni", "-r", str(SR), "-g", "1.2",
         "-F", str(out_path), SF2, str(tmp_mid)],
        capture_output=True
    )
    tmp_mid.unlink()
    if not out_path.exists(): return None
    audio, _ = sf.read(str(out_path), dtype="float32", always_2d=False)
    out_path.unlink()
    if audio.ndim > 1: audio = audio.mean(axis=1)
    if np.abs(audio).max() < 1e-8: return None

    fade = int(0.1 * SR); looped = audio.copy()
    for _ in range(loops - 1):
        seam   = looped[-fade:] * np.linspace(1,0,fade) + audio[:fade] * np.linspace(0,1,fade)
        looped = np.concatenate([looped[:-fade], seam, audio[fade:]])
    return trance_fx(looped)
# ── Mistral cascade planner ───────────────────────────────────────────────────

_PLAN_SYS = """\
You are a trance DJ planning a musical journey. Given a library of EDM chord \
progressions with audio features and a journey description, select 4-6 progressions \
that form a compelling arc.

Return JSON: {"segments": [{"id": <int>, "reason": "<short why>"}]}
Valid JSON only. IDs must exist in the library.
"""

def plan_journey(journey: str, index: list[dict]) -> list[dict]:
    lines = [
        f"#{e['id']:03d}: energy={e['energy']:.3f} brightness={e['brightness']:.3f} dur={e['duration']}s"
        for e in index
    ]
    resp = get_client().chat.completions.create(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": _PLAN_SYS},
            {"role": "user",   "content": f"Journey: \"{journey}\"\n\nLibrary:\n" + "\n".join(lines)},
        ],
        temperature=0.5,
        max_tokens=512,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(resp.choices[0].message.content)
    segs   = parsed.get("segments") or list(parsed.values())[0]
    return segs

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/tracks")
def list_tracks():
    """List all available trance tracks with metadata."""
    index = json.loads(IDX_FILE.read_text()) if IDX_FILE.exists() else []
    tracks = []
    for e in index:
        tracks.append({
            "id":         e["id"],
            "energy":     e["energy"],
            "brightness": e["brightness"],
            "darkness":   e["darkness"],
            "spread":     e["spread"],
            "duration":   e["duration"],
            "cached":     (TRANCE_DIR / f"trance_{e['id']:03d}.wav").exists(),
        })
    return {"tracks": tracks, "count": len(tracks)}


@app.get("/track/{track_id}/audio")
def get_track_audio(track_id: int, clip_s: float = Query(default=0, ge=0), vibe: str = Query(default="trance")):
    """Stream audio for a specific track."""
    audio = render_midi_to_audio(track_id, vibe=vibe)
    if audio is None:
        return JSONResponse({"error": f"Track {track_id} not found"}, status_code=404)
    if clip_s > 0:
        audio = audio[:int(clip_s * SR)]
    wav = to_wav_bytes(audio)
    return StreamingResponse(io.BytesIO(wav), media_type="audio/wav",
                             headers={"Content-Disposition": f"inline; filename={vibe}_{track_id:03d}.wav"})
@app.post("/generate")
async def generate(body: dict):
    """
    Plan + render a musical journey via Mistral.

    Body: { "journey": "...", "vibe": "haunted" | "hiphop" | "trance" }
    """
    try:
        journey  = body.get("journey", "euphoric melodic trance journey")
        vibe_key = body.get("vibe", "trance")
        # resolve chip label → library name
        vibe = VIBE_MAP.get(vibe_key.lower().replace("\U0001f47b","").replace("\U0001f305","").replace("\U0001f30a","")
                            .replace("\U0001f680","").replace("\U0001f319","").replace("\U0001f525","")
                            .replace("\U0001f33f","").replace("\u2744\ufe0f","").strip(), vibe_key)
        vibe = vibe if vibe in VIBE_LIBS else "trance"

        index   = json.loads(IDX_FILE.read_text()) if IDX_FILE.exists() else []
        if not index:
            return JSONResponse({"error": "No track library found. Run tag_tracks.py first to build audio/edm_index.json"}, status_code=503)

        if not MISTRAL_KEY:
            return JSONResponse({"error": "MISTRAL_API_KEY not set"}, status_code=503)

        plan    = plan_journey(journey, index)

        segments = []
        for seg in plan:
            audio = render_midi_to_audio(int(seg["id"]), vibe=vibe)
            if audio is not None:
                segments.append(audio)

        if not segments:
            return JSONResponse({"error": "No segments rendered"}, status_code=500)

        fade   = int(2.0 * SR)
        result = segments[0]
        for s in segments[1:]:
            f       = min(fade, len(result), len(s))
            overlap = result[-f:] * np.linspace(1,0,f) + s[:f] * np.linspace(0,1,f)
            result  = np.concatenate([result[:-f], overlap, s[f:]])

        pk = np.abs(result).max()
        if pk > 1e-8: result /= pk / 0.88

        wav = to_wav_bytes(result)
        return StreamingResponse(
            io.BytesIO(wav), media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=journey.wav",
                "X-Plan": json.dumps([{"id": s["id"], "reason": s.get("reason","")} for s in plan]),
                "X-Vibe": vibe,
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
@app.post("/splice")
async def splice(body: dict):
    """Body: { "count": 8, "clip_s": 10, "vibe": "trance" }"""
    try:
        count  = int(body.get("count", 8))
        clip_s = float(body.get("clip_s", 10.0))
        vibe   = body.get("vibe", "trance")
        vibe   = vibe if vibe in VIBE_LIBS else "trance"
        index  = json.loads(IDX_FILE.read_text()) if IDX_FILE.exists() else []

        if not index:
            return JSONResponse({"error": "No track library found. Run tag_tracks.py first to build audio/edm_index.json"}, status_code=503)

        picked = sorted(index, key=lambda x: x["energy"])
        step   = max(1, len(picked) // count)
        chosen = picked[::step][:count]

        clips = []
        for e in chosen:
            audio = render_midi_to_audio(e["id"], vibe=vibe)
            if audio is not None:
                n    = int(clip_s * SR)
                clip = audio[:n] if len(audio) >= n else np.pad(audio, (0, n-len(audio)))
                clips.append(clip)

        if not clips:
            return JSONResponse({"error": "No clips rendered"}, status_code=500)

        result = np.concatenate(clips)
        pk = np.abs(result).max()
        if pk > 1e-8: result /= pk / 0.88

        wav = to_wav_bytes(result)
        return StreamingResponse(io.BytesIO(wav), media_type="audio/wav",
                                 headers={"Content-Disposition": "inline; filename=splice.wav"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
@app.post("/mix")
async def mix_tracks(body: dict):
    """
    Layer multiple tracks with per-track volume and time offset.

    Body: { "tracks": [{"id": 1, "vibe": "trance", "volume": 0.8, "offset_s": 0}], "clip_s": 30 }
    """
    try:
        tracks = body.get("tracks", [])
        clip_s = float(body.get("clip_s", 30.0))
        if not tracks:
            return JSONResponse({"error": "No tracks provided"}, status_code=400)

        total_samples = int(clip_s * SR)
        mixed = np.zeros(total_samples, dtype=np.float64)

        for t in tracks:
            tid    = int(t["id"])
            vibe   = t.get("vibe", "trance")
            vol    = float(t.get("volume", 1.0))
            offset = float(t.get("offset_s", 0.0))
            vibe   = vibe if vibe in VIBE_LIBS else "trance"

            audio = render_midi_to_audio(tid, vibe=vibe)
            if audio is None:
                continue

            start = int(offset * SR)
            if start < 0:
                start = 0
            end = min(start + len(audio), total_samples)
            n   = end - start
            if n <= 0:
                continue
            mixed[start:end] += audio[:n] * vol

        pk = np.abs(mixed).max()
        if pk > 1e-8:
            mixed = (mixed / pk * 0.88).astype(np.float32)
        else:
            mixed = mixed.astype(np.float32)

        wav = to_wav_bytes(mixed)
        return StreamingResponse(
            io.BytesIO(wav), media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=mix.wav"}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "mistral": bool(MISTRAL_KEY),
        "libraries": {name: len(list(cfg["dir"].glob("*.wav"))) for name, cfg in VIBE_LIBS.items()},
    }
