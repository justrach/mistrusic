#!/usr/bin/env python3
"""Mistrusic FastAPI server — trance pad generation with Mistral planning.

Usage::

    export MISTRAL_API_KEY=...
    uvicorn server:app --reload --port 8000
"""
from __future__ import annotations

import io, json, os, tempfile, subprocess, uuid, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from dataclasses import dataclass
from typing import Dict, Optional

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
from fastapi import FastAPI, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse

# Import new modules
from src.sound_library import SoundLibrary, get_library, init_default_library
from src.input_handler import InputHandler, AudioSource
from src.morph_engine import MorphEngine, MorphParams, quick_morph
from src.export import export_audio, ExportOptions, ExportFormat, get_export_options_for_format

app = FastAPI(title="Mistrusic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
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
@app.post("/generate")
async def generate(body: dict):
    """
    Plan + render a musical journey via Mistral.

    Body: { "journey": "...", "vibe": "haunted" | "hiphop" | "trance" }
    """
    journey  = body.get("journey", "euphoric melodic trance journey")
    vibe_key = body.get("vibe", "trance")
    # resolve chip label → library name
    vibe = VIBE_MAP.get(vibe_key.lower().replace("👻","").replace("🌅","").replace("🌊","")
                        .replace("🚀","").replace("🌙","").replace("🔥","")
                        .replace("🌿","").replace("❄️","").strip(), vibe_key)
    vibe = vibe if vibe in VIBE_LIBS else "trance"

    index   = json.loads(IDX_FILE.read_text()) if IDX_FILE.exists() else []
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
@app.post("/splice")
@app.post("/splice")
async def splice(body: dict):
    """Body: { "count": 8, "clip_s": 10, "vibe": "trance" }"""
    count  = int(body.get("count", 8))
    clip_s = float(body.get("clip_s", 10.0))
    vibe   = body.get("vibe", "trance")
    vibe   = vibe if vibe in VIBE_LIBS else "trance"
    index  = json.loads(IDX_FILE.read_text()) if IDX_FILE.exists() else []

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

    result = np.concatenate(clips) if clips else np.zeros(SR, dtype=np.float32)
    pk = np.abs(result).max()
    if pk > 1e-8: result /= pk / 0.88

    wav = to_wav_bytes(result)
    return StreamingResponse(io.BytesIO(wav), media_type="audio/wav",
                             headers={"Content-Disposition": "inline; filename=splice.wav"})
@app.get("/health")
@app.get("/health")
@app.post("/mix")
async def mix_tracks(body: dict):
    """
    Layer multiple tracks together into one WAV.

    Body: {
      "tracks": [
        { "id": 1, "vibe": "trance", "volume": 0.8, "offset_s": 0.0 },
        { "id": 5, "vibe": "haunted", "volume": 0.6, "offset_s": 4.0 },
        ...
      ],
      "clip_s": 30   // optional: trim output to N seconds
    }
    """
    items  = body.get("tracks", [])
    clip_s = float(body.get("clip_s", 0))

    if not items:
        return JSONResponse({"error": "No tracks provided"}, status_code=400)

    layers = []
    for item in items:
        audio = render_midi_to_audio(int(item["id"]), vibe=item.get("vibe", "trance"))
        if audio is None:
            continue
        vol    = float(item.get("volume", 1.0))
        offset = int(float(item.get("offset_s", 0)) * SR)
        if offset > 0:
            audio = np.concatenate([np.zeros(offset, dtype=np.float32), audio])
        layers.append(audio * vol)

    if not layers:
        return JSONResponse({"error": "No audio loaded"}, status_code=500)

    # Pad all layers to the same length then sum
    max_len = max(len(l) for l in layers)
    if clip_s > 0:
        max_len = min(max_len, int(clip_s * SR))
    mixed = np.zeros(max_len, dtype=np.float64)
    for l in layers:
        n = min(len(l), max_len)
        mixed[:n] += l[:n]

    # Normalize
    pk = np.abs(mixed).max()
    if pk > 1e-8:
        mixed = (mixed / pk * 0.88).astype(np.float32)

    return StreamingResponse(io.BytesIO(to_wav_bytes(mixed.astype(np.float32))),
                             media_type="audio/wav",
                             headers={"Content-Disposition": "inline; filename=mix.wav"})


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mistral": bool(MISTRAL_KEY),
        "libraries": {name: len(list(cfg["dir"].glob("*.wav"))) for name, cfg in VIBE_LIBS.items()},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SOUND MORPHING / SPLICING API
# ═══════════════════════════════════════════════════════════════════════════════

# Initialize components
_morph_engine: MorphEngine | None = None
_sound_library: SoundLibrary | None = None
_morph_jobs: dict[str, dict] = {}

def get_morph_engine() -> MorphEngine:
    """Get or create the morph engine."""
    global _morph_engine
    if _morph_engine is None:
        _morph_engine = MorphEngine(sample_rate=SR)
    return _morph_engine

def get_sound_library() -> SoundLibrary:
    """Get or create the sound library."""
    global _sound_library
    if _sound_library is None:
        _sound_library = get_library("data/sound_library")
    return _sound_library


@app.get("/api/sounds")
def list_library_sounds(category: str | None = None, tag: str | None = None):
    """List available sounds from the library.
    
    Query params:
        category: Filter by category (instruments, nature, synthetic, mechanical, percussion)
        tag: Filter by tag
    """
    lib = get_sound_library()
    sounds = lib.list_sounds(category=category, tag=tag)
    
    return {
        "sounds": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "duration": s.duration,
                "sample_rate": s.sample_rate,
                "tags": s.tags,
            }
            for s in sounds
        ],
        "count": len(sounds),
        "categories": lib.get_categories(),
        "tags": lib.get_tags(),
    }


@app.get("/api/sounds/categories")
def list_categories():
    """Get all available sound categories."""
    lib = get_sound_library()
    return {"categories": lib.get_categories()}


@app.get("/api/sounds/{sound_id}")
def get_sound_details(sound_id: str):
    """Get details for a specific sound."""
    lib = get_sound_library()
    sound = lib.get_sound(sound_id)
    
    if sound is None:
        return JSONResponse(
            {"error": f"Sound not found: {sound_id}"},
            status_code=404
        )
    
    return {
        "id": sound.id,
        "name": sound.name,
        "description": sound.description,
        "category": sound.category,
        "duration": sound.duration,
        "sample_rate": sound.sample_rate,
        "tags": sound.tags,
    }


@app.get("/api/sounds/{sound_id}/preview")
def get_sound_preview(sound_id: str, clip_s: float = Query(default=0, ge=0, le=30)):
    """Get preview audio for a library sound.
    
    Args:
        sound_id: Sound identifier
        clip_s: Clip duration in seconds (0 = full, max 30s)
    """
    lib = get_sound_library()
    
    if sound_id not in lib:
        return JSONResponse(
            {"error": f"Sound not found: {sound_id}"},
            status_code=404
        )
    
    try:
        audio = lib.load_audio(sound_id, target_sr=SR)
        
        if clip_s > 0:
            n_samples = int(clip_s * SR)
            audio = audio[:n_samples]
        
        wav = to_wav_bytes(audio)
        return StreamingResponse(
            io.BytesIO(wav),
            media_type="audio/wav",
            headers={"Content-Disposition": f"inline; filename={sound_id}_preview.wav"}
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to load sound: {str(e)}"},
            status_code=500
        )


@app.post("/api/morph")
async def morph_sounds(
    background_tasks: BackgroundTasks,
    source_type: str = Form(..., description="'upload' or 'library'"),
    modulator_type: str = Form(..., description="'upload' or 'library'"),
    source_id: str | None = Form(None, description="Library sound ID if source_type='library'"),
    modulator_id: str | None = Form(None, description="Library sound ID if modulator_type='library'"),
    source_file: UploadFile | None = File(None, description="Audio file if source_type='upload'"),
    modulator_file: UploadFile | None = File(None, description="Audio file if modulator_type='upload'"),
    spectral_resolution: int = Form(default=2048, description="FFT window size (512-8192)"),
    sharpness: float = Form(default=0.5, ge=0, le=1, description="Filter sharpness (0-1)"),
    harmonic_balance: float = Form(default=0.5, ge=0, le=1, description="Harmonic vs noise balance (0-1)"),
    blend_ratio: float = Form(default=0.5, ge=0, le=1, description="Source/modulator blend (0-1)"),
    formant_shift: float = Form(default=0, ge=-24, le=24, description="Formant shift in semitones"),
    preserve_transients: bool = Form(default=True, description="Keep source transients"),
    smoothing: float = Form(default=0.3, ge=0, le=1, description="Spectral smoothing (0-1)"),
    output_format: str = Form(default="wav", description="Output format: wav, mp3, flac, ogg"),
):
    """Morph two sounds together using spectral cross-synthesis.
    
    Like shining light through colored glass - the source sound passes through
    the spectral characteristics of the modulator sound.
    
    Form data:
        source_type: 'upload' or 'library'
        modulator_type: 'upload' or 'library'
        source_id: Library ID (if source_type='library')
        modulator_id: Library ID (if modulator_type='library')
        source_file: File (if source_type='upload')
        modulator_file: File (if modulator_type='upload')
        ... plus morphing parameters
    
    Returns:
        Job info with ID to track progress
    """
    job_id = str(uuid.uuid4())
    
    try:
        handler = InputHandler(get_sound_library())
        
        # Load source
        if source_type == "library":
            if not source_id:
                return JSONResponse(
                    {"error": "source_id required when source_type='library'"},
                    status_code=400
                )
            source = handler.from_library(source_id)
        else:
            if not source_file:
                return JSONResponse(
                    {"error": "source_file required when source_type='upload'"},
                    status_code=400
                )
            content = await source_file.read()
            source = handler.from_upload(content, source_file.filename)
        
        # Load modulator
        if modulator_type == "library":
            if not modulator_id:
                return JSONResponse(
                    {"error": "modulator_id required when modulator_type='library'"},
                    status_code=400
                )
            modulator = handler.from_library(modulator_id, max_duration=source.duration)
        else:
            if not modulator_file:
                return JSONResponse(
                    {"error": "modulator_file required when modulator_type='upload'"},
                    status_code=400
                )
            content = await modulator_file.read()
            modulator = handler.from_upload(content, modulator_file.filename)
        
        # Create morph params
        params = MorphParams(
            spectral_resolution=spectral_resolution,
            sharpness=sharpness,
            harmonic_balance=harmonic_balance,
            blend_ratio=blend_ratio,
            formant_shift=formant_shift,
            preserve_transients=preserve_transients,
            smoothing=smoothing,
        )
        
        # Store job
        _morph_jobs[job_id] = {
            "id": job_id,
            "status": "processing",
            "source_name": source.name,
            "modulator_name": modulator.name,
            "created_at": time.time(),
            "params": {
                "spectral_resolution": spectral_resolution,
                "sharpness": sharpness,
                "harmonic_balance": harmonic_balance,
                "blend_ratio": blend_ratio,
                "formant_shift": formant_shift,
                "preserve_transients": preserve_transients,
                "smoothing": smoothing,
            },
            "result": None,
            "error": None,
        }
        
        # Process in background
        background_tasks.add_task(
            _process_morph_job,
            job_id,
            source.audio,
            modulator.audio,
            params,
            output_format
        )
        
        return {
            "job_id": job_id,
            "status": "processing",
            "source": source.name,
            "modulator": modulator.name,
            "estimated_duration": source.duration,
        }
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to start morph job: {str(e)}"},
            status_code=500
        )


def _process_morph_job(
    job_id: str,
    source_audio: np.ndarray,
    modulator_audio: np.ndarray,
    params: MorphParams,
    output_format: str
) -> None:
    """Process a morph job in the background."""
    try:
        engine = get_morph_engine()
        
        # Perform morphing
        result = engine.morph(source_audio, modulator_audio, params)
        
        # Export to requested format
        options = get_export_options_for_format(output_format, quality="high")
        audio_bytes = export_audio(result, options, sample_rate=SR)
        
        # Save to temp file
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"morph_{job_id}.{options.extension}"
        
        if isinstance(audio_bytes, bytes):
            output_path.write_bytes(audio_bytes)
        else:
            output_path = audio_bytes
        
        # Update job
        _morph_jobs[job_id]["status"] = "completed"
        _morph_jobs[job_id]["result"] = {
            "file_path": str(output_path),
            "format": output_format,
            "duration": len(result) / SR,
        }
        
    except Exception as e:
        _morph_jobs[job_id]["status"] = "failed"
        _morph_jobs[job_id]["error"] = str(e)


@app.get("/api/morph/{job_id}/status")
def get_morph_status(job_id: str):
    """Get status of a morph job."""
    if job_id not in _morph_jobs:
        return JSONResponse(
            {"error": f"Job not found: {job_id}"},
            status_code=404
        )
    
    job = _morph_jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "source": job["source_name"],
        "modulator": job["modulator_name"],
        "params": job["params"],
        "created_at": job["created_at"],
        "error": job["error"],
    }


@app.get("/api/morph/{job_id}/result")
def get_morph_result(job_id: str, download: bool = False):
    """Get the result of a completed morph job.
    
    Args:
        job_id: The job ID
        download: If true, triggers file download
    """
    if job_id not in _morph_jobs:
        return JSONResponse(
            {"error": f"Job not found: {job_id}"},
            status_code=404
        )
    
    job = _morph_jobs[job_id]
    
    if job["status"] == "processing":
        return JSONResponse(
            {"error": "Job still processing", "status": "processing"},
            status_code=202
        )
    
    if job["status"] == "failed":
        return JSONResponse(
            {"error": f"Job failed: {job['error']}"},
            status_code=500
        )
    
    result = job["result"]
    file_path = Path(result["file_path"])
    
    if not file_path.exists():
        return JSONResponse(
            {"error": "Result file not found"},
            status_code=404
        )
    
    # Determine content type
    ext = file_path.suffix.lower()
    content_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }
    content_type = content_types.get(ext, "application/octet-stream")
    
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{file_path.name}"'
    
    return FileResponse(
        file_path,
        media_type=content_type,
        headers=headers,
        filename=file_path.name if download else None
    )


@app.post("/api/morph/quick")
async def quick_morph_endpoint(
    source_type: str = Form(...),
    modulator_type: str = Form(...),
    source_id: str | None = Form(None),
    modulator_id: str | None = Form(None),
    source_file: UploadFile | None = File(None),
    modulator_file: UploadFile | None = File(None),
    intensity: float = Form(default=0.5, ge=0, le=1),
):
    """Quick morph with simplified controls.
    
    Performs morphing synchronously and returns the result directly.
    Best for shorter audio clips (< 30 seconds).
    """
    try:
        handler = InputHandler(get_sound_library())
        
        # Load source
        if source_type == "library":
            source = handler.from_library(source_id)
        else:
            content = await source_file.read()
            source = handler.from_upload(content, source_file.filename)
        
        # Load modulator
        if modulator_type == "library":
            modulator = handler.from_library(modulator_id, max_duration=source.duration)
        else:
            content = await modulator_file.read()
            modulator = handler.from_upload(content, modulator_file.filename)
        
        # Limit duration for quick morph
        max_samples = int(30 * SR)  # 30 seconds max
        source_audio = source.audio[:max_samples]
        modulator_audio = modulator.audio[:max_samples]
        
        # Perform quick morph
        result = quick_morph(source_audio, modulator_audio, intensity, SR)
        
        # Export to WAV
        wav = to_wav_bytes(result)
        
        return StreamingResponse(
            io.BytesIO(wav),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=morph_quick.wav"}
        )
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Morphing failed: {str(e)}"},
            status_code=500
        )


@app.post("/api/morph/style")
async def morph_with_style(
    source_type: str = Form(...),
    modulator_type: str = Form(...),
    source_id: str | None = Form(None),
    modulator_id: str | None = Form(None),
    source_file: UploadFile | None = File(None),
    modulator_file: UploadFile | None = File(None),
    style: str = Form(default="moderate", description="subtle, moderate, intense, extreme"),
):
    """Morph using preset style.
    
    Styles:
        subtle: Light touch, mostly source with hint of modulator
        moderate: Balanced blend
        intense: Strong modulator influence
        extreme: Maximum effect
    """
    try:
        handler = InputHandler(get_sound_library())
        
        # Load source
        if source_type == "library":
            source = handler.from_library(source_id)
        else:
            content = await source_file.read()
            source = handler.from_upload(content, source_file.filename)
        
        # Load modulator
        if modulator_type == "library":
            modulator = handler.from_library(modulator_id, max_duration=source.duration)
        else:
            content = await modulator_file.read()
            modulator = handler.from_upload(content, modulator_file.filename)
        
        # Limit duration
        max_samples = int(30 * SR)
        source_audio = source.audio[:max_samples]
        modulator_audio = modulator.audio[:max_samples]
        
        # Morph with style
        engine = get_morph_engine()
        result = engine.morph_with_style(source_audio, modulator_audio, style)
        
        # Export
        wav = to_wav_bytes(result)
        
        return StreamingResponse(
            io.BytesIO(wav),
            media_type="audio/wav",
            headers={"Content-Disposition": f"inline; filename=morph_{style}.wav"}
        )
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Morphing failed: {str(e)}"},
            status_code=500
        )


@app.get("/api/morph/presets")
def list_morph_presets():
    """Get available morphing presets."""
    return {
        "presets": [
            {
                "id": "subtle",
                "name": "Subtle",
                "description": "Light touch, mostly source with hint of modulator",
                "params": {
                    "blend_ratio": 0.25,
                    "sharpness": 0.3,
                    "smoothing": 0.5,
                }
            },
            {
                "id": "moderate",
                "name": "Moderate",
                "description": "Balanced blend between source and modulator",
                "params": {
                    "blend_ratio": 0.5,
                    "sharpness": 0.5,
                    "smoothing": 0.3,
                }
            },
            {
                "id": "intense",
                "name": "Intense",
                "description": "Strong modulator influence",
                "params": {
                    "blend_ratio": 0.75,
                    "sharpness": 0.7,
                    "smoothing": 0.2,
                }
            },
            {
                "id": "extreme",
                "name": "Extreme",
                "description": "Maximum effect, heavy transformation",
                "params": {
                    "blend_ratio": 0.9,
                    "sharpness": 0.9,
                    "smoothing": 0.1,
                }
            },
        ]
    }
