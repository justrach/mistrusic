# Mistrusic — Product Requirements Document

> Agentic audio morphing powered by Mistral AI + ElevenLabs + HuggingFace smolagents.
> Mistral AI Worldwide Hackathon, Singapore — Feb 28 – Mar 1, 2026

---

## 1. Problem Statement

Audio transformation today requires specialized DAW knowledge, manual plugin chaining, and technical DSP understanding. There is no tool that lets a non-technical user describe a desired audio transformation in plain English and have an AI agent autonomously figure out how to achieve it — selecting the right techniques, executing them, evaluating the result, and refining until it sounds right.

---

## 2. Product Overview

**Mistrusic** is a web application where users upload one or two audio files and describe a transformation in natural language. An AI agent (powered by Mistral) autonomously:

1. Analyzes the input audio (classification, feature extraction)
2. Plans a transformation strategy based on the user's description
3. Executes DSP operations and/or calls ElevenLabs APIs
4. Evaluates its own output using Mistral-powered self-assessment
5. Iteratively refines until quality meets a threshold or max iterations reached
6. Returns the morphed audio with a full reasoning trace

The entire agent reasoning process is streamed to the UI in real-time, showing each decision and tool call as it happens.

---

## 3. Target Users

- **Sound designers** — quickly prototype audio textures ("make this footstep sound metallic")
- **Musicians/producers** — creative exploration ("morph my guitar into an underwater piano")
- **Podcasters/content creators** — voice transformation and audio cleanup
- **Game audio devs** — generate and layer environmental audio from descriptions

---

## 4. Hackathon Track Alignment

| Track/Challenge | How Mistrusic Aligns |
|---|---|
| **Mistral AI Track** | Mistral is the LLM backbone for all agent reasoning, tool selection, and self-evaluation |
| **HuggingFace — best use of agent skills** | Built on HF's `smolagents` CodeAgent framework; uses HF audio classification model as an agent tool; deployed to HF Spaces |
| **ElevenLabs — best use of ElevenLabs** | Three deep ElevenLabs API integrations as core agent tools: Sound Effects generation, Audio Isolation, Voice Changer |

---

## 5. User Flow

```
1. User opens Gradio app (hosted on HuggingFace Spaces)
2. User uploads Sound A (required) — the source audio
3. User optionally uploads Sound B — the "target" or "filter" audio
   - If no Sound B: user describes the desired sound in text
4. User types a natural language transformation prompt
   e.g., "Make my voice sound like it's in a cathedral during a thunderstorm"
5. User clicks "Morph!"
6. Agent reasoning trace streams in real-time on the right panel:
   - "Classifying Sound A... detected: speech (92% confidence)"
   - "No Sound B uploaded. Generating thunderstorm sound effect via ElevenLabs..."
   - "Isolating vocals from Sound A..."
   - "Applying convolution with cathedral-like reverb..."
   - "Mixing thunderstorm layer at 30% ratio..."
   - "Evaluating output... Score: 6/10. Suggestion: increase reverb wet/dry to 0.8"
   - "Refining... Applying convolution with wet_dry=0.8"
   - "Re-evaluating... Score: 8/10. Finalizing."
7. Morphed audio appears in output player
8. User can play, download, or try another transformation
```

---

## 6. Architecture

```
┌──────────────────────────────────────────────────┐
│                  Gradio UI (app.py)               │
│  ┌─────────┐  ┌───────────┐  ┌────────────────┐  │
│  │ Audio A  │  │ Audio B   │  │ Text Prompt    │  │
│  │ Upload   │  │ (optional)│  │                │  │
│  └────┬─────┘  └─────┬─────┘  └───────┬────────┘  │
│       └──────────────┼────────────────┘            │
│                      v                             │
│  ┌───────────────────────────────────────────┐     │
│  │     smolagents CodeAgent (agent.py)       │     │
│  │     LLM: Mistral Large via LiteLLM       │     │
│  │     Max steps: 15                         │     │
│  │                                           │     │
│  │  Tools:                                   │     │
│  │  ┌─────────────────────────────────────┐  │     │
│  │  │ ElevenLabs (3)                      │  │     │
│  │  │  - generate_sound_effect            │  │     │
│  │  │  - isolate_audio                    │  │     │
│  │  │  - change_voice                     │  │     │
│  │  ├─────────────────────────────────────┤  │     │
│  │  │ HuggingFace (2)                     │  │     │
│  │  │  - classify_audio                   │  │     │
│  │  │  - extract_audio_features           │  │     │
│  │  ├─────────────────────────────────────┤  │     │
│  │  │ DSP (4)                             │  │     │
│  │  │  - convolution                      │  │     │
│  │  │  - spectral_imprint                 │  │     │
│  │  │  - cross_synthesize                 │  │     │
│  │  │  - mix_audio                        │  │     │
│  │  ├─────────────────────────────────────┤  │     │
│  │  │ Evaluation (1)                      │  │     │
│  │  │  - evaluate_morph (calls Mistral)   │  │     │
│  │  ├─────────────────────────────────────┤  │     │
│  │  │ Utility (1)                         │  │     │
│  │  │  - get_audio_info                   │  │     │
│  │  └─────────────────────────────────────┘  │     │
│  └──────────────────┬────────────────────────┘     │
│                     v                              │
│  ┌──────────────┐  ┌────────────────────────────┐  │
│  │ Output Audio │  │ Reasoning Trace (streamed)  │  │
│  └──────────────┘  └────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

---

## 7. Tool Specifications

### 7.1 ElevenLabs Tools

| Tool | Purpose | Inputs | Output |
|---|---|---|---|
| `generate_sound_effect` | Generate audio from text description | `text` (str), `duration_seconds` (float, 0.5-30) | Audio file path |
| `isolate_audio` | Remove background noise / extract vocals | `audio_path` (str) | Cleaned audio file path |
| `change_voice` | Transform voice identity, preserve emotion | `audio_path` (str), `voice_id` (str) | Voice-changed audio file path |

**ElevenLabs integration rationale**: These aren't wrappers — they're the creative engine. `generate_sound_effect` means users don't even need Sound B. The agent can generate intermediate textures, environmental sounds, or layering elements on the fly. `isolate_audio` is preprocessing intelligence. `change_voice` enables speech-specific morphing that DSP alone can't achieve.

### 7.2 HuggingFace Tools

| Tool | Purpose | Model | Output |
|---|---|---|---|
| `classify_audio` | Identify audio type (speech, guitar, rain, etc.) | `MIT/ast-finetuned-audioset-10-10-0.4593` | Top-5 labels with confidence scores |
| `extract_audio_features` | Quantitative feature extraction | librosa | JSON: duration, RMS, spectral centroid, tempo, ZCR, MFCCs |

**HF integration rationale**: `classify_audio` gives the agent "ears" — it can understand what kind of audio it's working with and make informed decisions. A HuggingFace model running inference inside a smolagents tool, deployed on HF Spaces, is a strong "agent skills" story.

### 7.3 DSP Tools

| Tool | Purpose | Key Params |
|---|---|---|
| `convolution` | Convolve source through impulse response (reverb/space transfer) | `wet_dry` (0-1) |
| `spectral_imprint` | Apply Sound B's magnitude spectrum as filter on Sound A | `smoothing` (0-1) |
| `cross_synthesize` | Phase vocoder: envelope of one sound + fine structure of another | `envelope_source`, `excitation_source` |
| `mix_audio` | Weighted sum of two audio files | `ratio` (0-1) |

### 7.4 Evaluation Tool

| Tool | Purpose | Mechanism |
|---|---|---|
| `evaluate_morph` | Rate transformation quality, suggest improvements | Calls Mistral with original vs. morphed features + target description. Returns score (1-10), reasoning, suggestions. |

**This is the key differentiator.** The agent doesn't just blindly apply transforms — it evaluates its own work using Mistral, then acts on the suggestions. This creates a visible "think → act → evaluate → refine" loop that demos exceptionally well.

---

## 8. Agent Behavior

The smolagents `CodeAgent` receives a system prompt that guides its workflow:

1. **ANALYZE**: Call `classify_audio` and `extract_audio_features` on inputs
2. **PLAN**: Reason about which tools to use based on audio type and user intent
3. **EXECUTE**: Apply transformations (may chain multiple tools)
4. **EVALUATE**: Extract features from output, call `evaluate_morph`
5. **REFINE**: If score < 7/10, follow suggestions and retry (max 3 refinement rounds)

**Decision heuristics encoded in the system prompt:**
- No Sound B + text description → `generate_sound_effect` (ElevenLabs)
- Audio classified as speech + voice transform requested → `isolate_audio` then `change_voice`
- "reverb", "space", "room" → `convolution`
- "tone", "warmth", "texture" → `spectral_imprint`
- "morph into", "sound like" → `cross_synthesize`

The agent writes Python code to compose tools (CodeAgent advantage over JSON tool-calling), enabling logic like:
```python
# Agent-generated code example
features_a = classify_audio(audio_path=sound_a)
if "speech" in features_a:
    clean = isolate_audio(audio_path=sound_a)
    result = change_voice(audio_path=clean, voice_id="deep_narrator")
else:
    thunder = generate_sound_effect(text="rolling thunder", duration_seconds=10)
    result = cross_synthesize(envelope_source=thunder, excitation_source=sound_a)
```

---

## 9. UI Design

**Framework**: Gradio `gr.Blocks`
**Layout**: Two-panel

### Left Panel — Inputs
- **Sound A** upload (`gr.Audio`, required, type="filepath")
- **Sound B** upload (`gr.Audio`, optional, type="filepath")
- **Transformation prompt** (`gr.Textbox`, placeholder: "Describe how you want to transform the audio...")
- **Morph button** (`gr.Button`)
- **Example presets** row — clickable chips that pre-fill prompt + load demo audio:
  - "Underwater guitar"
  - "Voice morph to narrator"
  - "Piano in a thunderstorm"
  - "Add vinyl warmth"

### Right Panel — Outputs
- **Output audio player** (`gr.Audio`)
- **Reasoning trace** (`gr.Markdown` or `gr.Chatbot`, streaming) — shows each agent step in real-time with tool name, inputs, outputs, timing
- **Download button**

---

## 10. Repo Structure

```
mistrusic/
├── app.py                      # Gradio UI entry point
├── agent.py                    # smolagents CodeAgent setup + system prompt
├── tools/
│   ├── __init__.py
│   ├── elevenlabs_tools.py     # 3 ElevenLabs tool classes
│   ├── hf_tools.py             # 2 HuggingFace tool classes
│   ├── dsp_tools.py            # 4 DSP tool classes
│   ├── evaluation_tool.py      # Mistral-powered evaluation tool
│   └── file_tools.py           # AudioInfoTool
├── utils/
│   └── audio_utils.py          # Shared: load, save, resample, normalize, temp paths
├── requirements.txt
├── .env.example
└── README.md
```

---

## 11. Tech Stack

| Component | Technology |
|---|---|
| Agent framework | `smolagents` CodeAgent (HuggingFace) |
| LLM | Mistral Large via LiteLLM |
| Audio generation/processing | ElevenLabs Python SDK |
| Audio ML classification | HuggingFace `transformers` pipeline |
| DSP | `numpy`, `scipy`, `librosa`, `soundfile` |
| UI | Gradio 4.x |
| Deployment | HuggingFace Spaces |

### Dependencies
```
smolagents[litellm]
gradio>=4.0
elevenlabs>=2.0
mistralai>=1.0.0
transformers
librosa
scipy
numpy
soundfile
torch
python-dotenv
```

---

## 12. Implementation Phases

### Phase 1: Foundation (Saturday morning, ~4h)
- Repo setup, dependencies, directory structure
- `utils/audio_utils.py` — core audio I/O helpers
- `tools/file_tools.py` — AudioInfoTool (validates smolagents Tool pattern)
- `tools/dsp_tools.py` — MixAudioTool + SpectralImprintTool
- `agent.py` — CodeAgent with Mistral + 3 tools
- `app.py` — minimal Gradio: audio in, text in, audio out
- **Milestone**: Agent can mix two files based on a text prompt

### Phase 2: ElevenLabs Integration (Saturday afternoon, ~3h)
- `tools/elevenlabs_tools.py` — GenerateSoundEffectTool first
- Test: "Generate a thunderstorm and mix it with my guitar"
- Add AudioIsolationTool and VoiceChangerTool
- **Milestone**: Agent can generate sounds from text and transform voices

### Phase 3: HuggingFace + Evaluation (Saturday evening, ~3h)
- `tools/hf_tools.py` — AudioClassifierTool (HF transformers pipeline)
- `tools/evaluation_tool.py` — Mistral-powered self-evaluation
- `tools/hf_tools.py` — AudioFeatureExtractorTool
- Remaining DSP: ConvolutionTool, CrossSynthesisTool
- **Milestone**: Full analyze → transform → evaluate → refine loop works

### Phase 4: UI Polish + Trace (Sunday morning, ~3h)
- Upgrade app.py to two-panel gr.Blocks with streaming reasoning trace
- Add example presets with demo audio
- Test all demo scenarios, ensure <60s completion
- **Milestone**: Demo-ready UI with live reasoning trace

### Phase 5: Deploy + Submit (Sunday afternoon, ~2h)
- Deploy to HuggingFace Spaces (hackathon HF org)
- Write README with architecture diagram
- Record 2-minute demo video
- Submit to hackiterate.com

---

## 13. Demo Script (2-minute video)

**0:00-0:15** — "Mistrusic is an AI agent that morphs audio. You describe what you want in English, and the agent figures out how to do it."

**0:15-0:45** — Demo 1: Upload a dry guitar recording. Type "Make this sound like it's being played underwater." Show the reasoning trace streaming: classify → generate water effects (ElevenLabs) → spectral imprint → evaluate → refine → finalize. Play the output.

**0:45-1:15** — Demo 2: Upload speech. Type "Change this voice to a deep narrator." Trace shows: classify as speech → isolate vocals (ElevenLabs) → change voice (ElevenLabs) → evaluate → done. Play output.

**1:15-1:45** — Show the architecture: smolagents CodeAgent + Mistral backbone + 11 tools spanning ElevenLabs, HuggingFace, and custom DSP. Highlight the self-evaluation loop.

**1:45-2:00** — "Mistrusic — agentic audio morphing. Built with Mistral AI, HuggingFace smolagents, and ElevenLabs."

---

## 14. Judging Criteria Scoring Strategy

| Criterion | Score Driver |
|---|---|
| **Technicality** | smolagents CodeAgent with 11 tools across 3 APIs; iterative self-evaluation via separate Mistral call; DSP algorithms (cross-synthesis, spectral imprint, FFT convolution); code agent writes composable Python |
| **Creativity** | Novel concept — no existing tool does NL-driven agentic audio morphing. Agent generates sounds from text (no Sound B needed). Self-evaluating loop. Audio-in, audio-out is immediately tangible. |
| **Usefulness** | Clear target users (sound designers, musicians, podcasters). Solves a real workflow bottleneck. Natural language interface removes the DAW learning curve. |
| **Demo** | Reasoning trace is visually compelling and streams in real-time. Audio plays in room. Pre-tested scenarios ensure smooth demo. Gradio provides polished UI. |
| **Track alignment** | Mistral: LLM backbone for reasoning + evaluation. HuggingFace: smolagents + HF audio model + HF Spaces. ElevenLabs: 3 deep integrations as core tools. |

---

## 15. Risk Mitigation

| Risk | Mitigation |
|---|---|
| ElevenLabs rate limits | Cache generated SFX; bundle pre-generated fallback audio files for demo |
| Agent too slow (>60s) | `max_steps=15`; try `mistral-small-latest` if Large is slow; pre-classify common audio |
| smolagents CodeAgent errors | Fall back to `ToolCallingAgent` (JSON-based, more predictable) |
| HF audio model slow locally | Use HF Inference API or pre-download small model (AST: 87M params) |
| Cross-synthesis sounds bad | Evaluation loop catches this; agent retries; `mix_audio` as fallback |
| API keys exhausted | Monitor usage; have offline-capable DSP path as minimum viable demo |

---

## 16. Success Criteria

- [ ] Agent processes a transformation request end-to-end in <60 seconds
- [ ] All 11 tools are callable by the agent
- [ ] At least 3 demo scenarios produce good-sounding output
- [ ] Reasoning trace streams visibly in the UI
- [ ] App deployed and accessible on HuggingFace Spaces
- [ ] 2-minute demo video recorded and submitted
- [ ] Submitted to hackiterate.com before deadline
