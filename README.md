# Mistrusic Style Vocoder Plugin

A lightweight, practical implementation for an instrument-style vocoder that can be used as a plugin-style audio effect:
- feed a dry instrument signal (carrier),
- choose a target style from a few reference instruments,
- output a transformed signal.

This replaces the PRD-only branch with executable code.

## Architecture

- `src/style_profiles.py`
  - builds/loads instrument profiles from a few reference audio files.
- `src/dataset.py`
  - dataset loader for `(carrier, modulator, target)` wav triplets.
- `src/model.py`
  - conditional waveform model that uses carrier+modulator+style.
- `src/train.py`
  - trains the model on synthetic or real triplets.
- `src/infer.py`
  - offline inference for one file.
- `src/plugin_runtime.py`
  - plugin-style runtime class with `process_block` and overlap-add support.

## Quick setup

```bash
pip install -r requirements.txt
```

## 1) Build instrument profiles (few-shot)

Create profile folders with short examples per style:

```bash
raw_instruments/
  ├─ flute/*.wav
  ├─ sax/*.wav
  └─ violin/*.wav
```

```bash
python -m src.style_profiles \
  --styles-dir raw_instruments \
  --out profiles.npz
```

## 2) Train

Expect triplets in `data/vocoder_synthetic` with `carrier/`, `modulator/`, `output/`, `metadata.json`:

```bash
python -m src.train \
  --data-dir data/vocoder_synthetic \
  --profiles profiles.npz \
  --checkpoints checkpoints \
  --batch-size 2 \
  --epochs 20
```

## 3) Inference (plugin-style transform)

```bash
python -m src.infer \
  --checkpoint checkpoints/best.pt \
  --profiles profiles.npz \
  --input audio_in.wav \
  --style flute \
  --output audio_out.wav
```

Use a direct style reference instead of a named profile:

```bash
python -m src.infer \
  --checkpoint checkpoints/best.pt \
  --profiles profiles.npz \
  --input audio_in.wav \
  --reference ref_sax.wav \
  --output audio_out.wav
```

## Plugin runtime

```python
from src.plugin_runtime import StyleVocoderPlugin

plugin = StyleVocoderPlugin(
    checkpoint="checkpoints/best.pt",
    profiles="profiles.npz",
)

# process float32 np.ndarray in [-1, 1] at model sample rate
wet = plugin.process(audio, block_size=131072, style="flute", sample_rate=32000)
```

## Notes

- This implementation is intentionally pragmatic: it prioritizes a functional, trainable core over a JUCE-level VST wrapper.
- For a native VST/AU plugin you can package this runtime behind a C++ host bridge, or call the script from a local wrapper later.
