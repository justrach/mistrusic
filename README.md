# Mistrusic

> **Text → personalized soundtrack, in seconds.**  
> Built for the Mistral Worldwide Hackathon 2026.

Mistrusic combines a **custom-trained neural vocoder**, a **Mistral cascade planner**, and **300 pre-rendered audio progressions** to turn a single vibe description into a full musical journey — with a mixing studio and architecture explorer on top.

---

## How it works

```
"dark haunted forest at 3am"
        │
        ▼
┌─────────────────────┐
│  Keyword Detector   │  client-side regex → routes to sound library
│  (Next.js)          │
└────────┬────────────┘
         │ POST /generate
         ▼
┌─────────────────────┐
│  Mistral Planner    │  mistral-small-latest reads track index
│  (Journey Arc)      │  (energy, brightness, duration per track)
│                     │  → returns ordered segment list + reasoning
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Audio Render       │  cache hit  → stream WAV directly (<1s)
│  Engine (FastAPI)   │  cache miss → FluidSynth + FX chain → cache
└────────┬────────────┘
         │ WAV stream
         ▼
┌─────────────────────┐
│  Browser Player     │  Web Audio API · rAF timer · mm:ss display
└─────────────────────┘
```

---

## The StyleVocoder Model

At the core of Mistrusic is **StyleVocoder** — a mel-domain U-Net we built and trained from scratch using [MLX](https://github.com/ml-explore/mlx) on Apple Silicon.

### Architecture

```
carrier audio  ──► mel spectrogram ──► Encoder (3 blocks, downsamples 4×)
                                              │
text prompt ──► Mistral StyleAgent ──► style embedding
                                              │ FiLM conditioning
                                       Bottleneck ResBlock
                                              │
                                       Decoder (skip connections)
                                              │
                                       predicted mel ──► Griffin-Lim / phase reconstruct ──► audio out
```

- **Encoder/Decoder**: 1D conv blocks with stride-2 downsampling and skip connections
- **FiLM conditioning**: style embedding modulates every layer via affine feature-wise linear modulation
- **Style blending**: Mistral maps a text prompt to a weighted blend of named instrument profiles (e.g. `{"sax_tenor": 0.6, "clarinet": 0.4}`)
- **Training**: MAE loss on log-mel spectrograms, AdamW + cosine LR schedule, batch size 8

### Text-driven style control

```bash
python -m src.infer \
  --checkpoint checkpoints/best \
  --profiles profiles.npz \
  --input guitar.wav \
  --prompt "warm smoky jazz saxophone with a hint of muted trumpet" \
  --output out.wav --reverb
```

Mistral receives the list of available instrument profiles and the text prompt, and returns a JSON blend that gets linearly interpolated in embedding space.

---

## Sound Libraries

Three distinct sound worlds, each with 100 tracks:

| Library | Instrument | FX Chain |
|---------|-----------|----------|
| **Trance** | GM Polysynth (#90) | Hi-pass 80Hz → 4-voice chorus ±14¢ → 6s hall reverb (91% decay) → 375ms delay |
| **Haunted** | GM Choir Aahs (#52) | Hi-pass 180Hz → tremolo 4.5Hz → 7s dark reverb (94% decay, 72% wet) |
| **Hip Hop** | GM Rhodes (#4) | Lo-pass 9kHz → vinyl saturation (tanh) → warm room reverb (62% decay, 32% wet) |

Each track is the same underlying MIDI progression rendered through a different GM program and FX chain — giving **300 unique tracks from 100 MIDI files**.

All tracks are pre-rendered and cached to disk. Preview latency is under 1 second.

---

## Frontend Pages

| Page | URL | Description |
|------|-----|-------------|
| **Generate** | `/` | Type a vibe → auto-detects genre → Mistral builds journey → streams audio |
| **Studio** | `/studio` | Layer tracks from any library, set volumes + time offsets, render a mixed WAV |
| **Architecture** | `/arch` | Interactive pipeline diagram of the full system |

---

## Project Structure

```
mistrusic/
├── src/
│   ├── model.py          # StyleVocoder U-Net (MLX)
│   ├── train.py          # Training loop (AdamW + cosine LR)
│   ├── infer.py          # Inference: named style, reference audio, or text prompt
│   ├── style_agent.py    # Mistral StyleAgent — text → blended embedding
│   ├── style_profiles.py # Build/load instrument profile embeddings
│   ├── dataset.py        # VocoderDataset — carrier/target mel pairs
│   └── plugin_runtime.py # Plugin-style runtime with overlap-add
├── server.py             # FastAPI backend — /generate /track /mix /splice /health
├── frontend/             # Next.js 16 app
│   └── src/app/
│       ├── page.tsx      # Generate page
│       ├── studio/       # Studio mixing page
│       ├── arch/         # Architecture explainer page
│       └── layout.tsx    # Nav + global layout
├── scripts/
│   ├── prepare_dataset.py
│   └── prepare_profiles.py
├── audio/
│   ├── trance_raw/       # 100 pre-rendered trance WAVs
│   ├── haunted_raw/      # 100 pre-rendered haunted WAVs
│   └── hiphop_raw/       # 100 pre-rendered hip hop WAVs
└── tag_tracks.py         # Mistral-powered ID3 metadata tagger
```

---

## Setup

### Backend

```bash
# Python deps
pip install fastapi uvicorn soundfile scipy numpy mistralai openai mlx

# FluidR3 soundfont (needed for MIDI rendering)
wget -O /tmp/FluidR3_GM.sf2 https://member.keymusician.com/Member/FluidR3_GM/FluidR3_GM.sf2

# Set API key
export MISTRAL_API_KEY=your_key_here

# Start server
uvicorn server:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Train StyleVocoder

```bash
# 1. Build instrument profiles from reference audio
python -m src.style_profiles \
  --styles-dir raw_instruments \
  --out profiles.npz

# 2. Train
python -m src.train \
  --data-dir data/vocoder_synthetic \
  --profiles profiles.npz \
  --checkpoints checkpoints \
  --epochs 50

# 3. Infer with text prompt
python -m src.infer \
  --checkpoint checkpoints/best \
  --profiles profiles.npz \
  --input my_audio.wav \
  --prompt "dark trance pad with long reverb tail" \
  --output styled.wav --reverb
```

---

## Mistral Integration

| Where | Model | Role |
|-------|-------|------|
| Journey planner | `mistral-small-latest` | Reads track index (energy/brightness/duration), returns ordered segment list with narrative reasoning |
| StyleAgent | `mistral-small-latest` | Maps text prompt → weighted blend of instrument profiles for the vocoder |
| Metadata tagger | `mistral-small-latest` | Generates title, genre, mood, BPM, description for all 300 tracks |

---

## Numbers

- **300** pre-rendered tracks (3 libs × 100 progressions)
- **<1s** preview latency (direct cache read)
- **3** FX chains (trance · haunted · hip hop)
- **1** neural model (StyleVocoder, trained on Apple Silicon with MLX)
- **2** Mistral roles (planner + style agent)

---

## Built with

- [Mistral AI](https://mistral.ai) — journey planning, style resolution, metadata tagging
- [MLX](https://github.com/ml-explore/mlx) — StyleVocoder training on Apple Silicon
- [FluidSynth](https://www.fluidsynth.org) — MIDI → WAV synthesis
- [FastAPI](https://fastapi.tiangolo.com) — streaming audio backend
- [Next.js 16](https://nextjs.org) — frontend
