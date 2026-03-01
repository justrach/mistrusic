#!/usr/bin/env python3
"""Run edge case tests without pytest dependency."""

import sys
import traceback
import numpy as np
import tempfile
from pathlib import Path
import soundfile as sf

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.morph_engine import (
    MorphParams, stft, istft, morph_audio, quick_morph,
    extract_spectral_envelope, MorphEngine
)
from src.input_handler import InputHandler, InputSourceType
from src.export import export_audio, ExportOptions, ExportFormat
from src.sound_library import SoundLibrary, SoundMetadata


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name):
        """Decorator to register tests."""
        def decorator(func):
            self.tests.append((name, func))
            return func
        return decorator
    
    def run(self):
        """Run all registered tests."""
        print("=" * 70)
        print("Running Edge Case Tests")
        print("=" * 70)
        
        for name, func in self.tests:
            try:
                func()
                print(f"✅ PASS: {name}")
                self.passed += 1
            except Exception as e:
                print(f"❌ FAIL: {name}")
                print(f"   Error: {str(e)[:100]}")
                self.failed += 1
        
        print("=" * 70)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print("=" * 70)
        return self.failed == 0


runner = TestRunner()


@runner.test("Silent source audio")
def test_silent_source():
    source = np.zeros(22050, dtype=np.float32)
    modulator = np.random.randn(22050).astype(np.float32) * 0.3
    result = morph_audio(source, modulator)
    assert len(result) == len(source)
    assert np.all(np.isfinite(result))


@runner.test("Silent modulator audio")
def test_silent_modulator():
    source = np.random.randn(22050).astype(np.float32) * 0.3
    modulator = np.zeros(22050, dtype=np.float32)
    result = morph_audio(source, modulator)
    assert len(result) == len(source)
    assert np.all(np.isfinite(result))


@runner.test("Both inputs silent")
def test_both_silent():
    source = np.zeros(22050, dtype=np.float32)
    modulator = np.zeros(22050, dtype=np.float32)
    result = morph_audio(source, modulator)
    assert len(result) == len(source)


@runner.test("Very short audio (< 1 frame)")
def test_very_short():
    source = np.random.randn(100).astype(np.float32)
    modulator = np.random.randn(100).astype(np.float32)
    result = morph_audio(source, modulator)
    assert np.all(np.isfinite(result))


@runner.test("Single sample audio")
def test_single_sample():
    source = np.array([0.5], dtype=np.float32)
    modulator = np.array([0.3], dtype=np.float32)
    result = morph_audio(source, modulator)
    assert np.all(np.isfinite(result))


@runner.test("Long audio (10 seconds)")
def test_long_audio():
    sr = 22050
    samples = sr * 10
    source = np.random.randn(samples).astype(np.float32) * 0.3
    modulator = np.random.randn(samples).astype(np.float32) * 0.3
    result = morph_audio(source, modulator)
    assert len(result) == len(source)
    assert np.all(np.isfinite(result))


@runner.test("Extreme volume difference")
def test_volume_difference():
    source = np.random.randn(22050).astype(np.float32) * 0.001
    modulator = np.random.randn(22050).astype(np.float32) * 0.999
    result = morph_audio(source, modulator)
    assert np.all(np.isfinite(result))
    assert np.abs(result).max() <= 1.0


@runner.test("Impulse signal")
def test_impulse():
    source = np.zeros(22050, dtype=np.float32)
    source[11025] = 1.0
    modulator = np.random.randn(22050).astype(np.float32) * 0.3
    result = morph_audio(source, modulator)
    assert np.all(np.isfinite(result))


@runner.test("Extreme blend ratios (0.0 and 1.0)")
def test_extreme_blend():
    source = np.random.randn(22050).astype(np.float32) * 0.5
    modulator = np.random.randn(22050).astype(np.float32) * 0.5
    result_0 = morph_audio(source, modulator, MorphParams(blend_ratio=0.0))
    result_1 = morph_audio(source, modulator, MorphParams(blend_ratio=1.0))
    assert np.all(np.isfinite(result_0))
    assert np.all(np.isfinite(result_1))


@runner.test("Extreme formant shift (+/- 24 semitones)")
def test_extreme_formant():
    source = np.random.randn(22050).astype(np.float32) * 0.3
    modulator = np.random.randn(22050).astype(np.float32) * 0.3
    result_up = morph_audio(source, modulator, MorphParams(formant_shift=24))
    result_down = morph_audio(source, modulator, MorphParams(formant_shift=-24))
    assert np.all(np.isfinite(result_up))
    assert np.all(np.isfinite(result_down))


@runner.test("All preset styles")
def test_all_presets():
    engine = MorphEngine()
    source = np.random.randn(22050).astype(np.float32) * 0.3
    modulator = np.random.randn(22050).astype(np.float32) * 0.3
    styles = ["subtle", "moderate", "intense", "extreme"]
    for style in styles:
        result = engine.morph_with_style(source, modulator, style)
        assert np.all(np.isfinite(result))


@runner.test("Various FFT sizes (512-4096)")
def test_various_fft():
    source = np.random.randn(22050).astype(np.float32) * 0.3
    modulator = np.random.randn(22050).astype(np.float32) * 0.3
    sizes = [512, 1024, 2048, 4096]
    for size in sizes:
        params = MorphParams(spectral_resolution=size)
        result = morph_audio(source, modulator, params)
        assert np.all(np.isfinite(result))


@runner.test("Transient preservation toggle")
def test_transient_toggle():
    source = np.zeros(22050, dtype=np.float32)
    source[5000:5020] = 1.0
    modulator = np.random.randn(22050).astype(np.float32) * 0.3
    with_t = morph_audio(source, modulator, MorphParams(preserve_transients=True))
    without_t = morph_audio(source, modulator, MorphParams(preserve_transients=False))
    assert np.all(np.isfinite(with_t))
    assert np.all(np.isfinite(without_t))


@runner.test("STFT with short signal")
def test_stft_short():
    audio = np.random.randn(10).astype(np.float32)
    spec = stft(audio, 512, 128)
    assert spec.shape[0] == 257


@runner.test("Spectral envelope with zeros")
def test_envelope_zeros():
    spectrum = np.zeros(1025)
    envelope = extract_spectral_envelope(spectrum, smoothing=0.5)
    assert np.all(np.isfinite(envelope))


@runner.test("Export silent audio")
def test_export_silent():
    audio = np.zeros(22050, dtype=np.float32)
    opts = ExportOptions(format=ExportFormat.WAV)
    result = export_audio(audio, opts)
    assert isinstance(result, bytes)
    assert len(result) > 0


@runner.test("Export with clipping")
def test_export_clipping():
    audio = np.array([1.5, -1.5, 2.0, -2.0], dtype=np.float32)
    opts = ExportOptions(format=ExportFormat.WAV, normalize=False)
    result = export_audio(audio, opts)
    assert isinstance(result, bytes)


@runner.test("Export all formats")
def test_export_formats():
    audio = np.random.randn(22050).astype(np.float32) * 0.3
    formats = [ExportFormat.WAV, ExportFormat.FLAC, ExportFormat.OGG]
    for fmt in formats:
        opts = ExportOptions(format=fmt)
        result = export_audio(audio, opts)
        assert isinstance(result, bytes)


@runner.test("Input handler - stereo to mono conversion")
def test_stereo_mono():
    with tempfile.TemporaryDirectory() as tmpdir:
        stereo_file = Path(tmpdir) / "stereo.wav"
        stereo = np.random.randn(22050, 2).astype(np.float32) * 0.3
        sf.write(stereo_file, stereo, 22050)
        
        handler = InputHandler()
        with open(stereo_file, "rb") as f:
            content = f.read()
        
        source = handler.from_upload(content, "stereo.wav")
        assert source.audio.ndim == 1


@runner.test("Input handler - different sample rates")
def test_sample_rates():
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = InputHandler()
        rates = [8000, 16000, 44100, 48000]
        
        for rate in rates:
            audio_file = Path(tmpdir) / f"audio_{rate}.wav"
            audio = np.random.randn(rate).astype(np.float32) * 0.3
            sf.write(audio_file, audio, rate)
            
            with open(audio_file, "rb") as f:
                content = f.read()
            
            source = handler.from_upload(content, f"audio_{rate}.wav")
            assert source.sample_rate == 22050


@runner.test("Quick morph function")
def test_quick_morph():
    source = np.random.randn(22050).astype(np.float32) * 0.3
    modulator = np.random.randn(22050).astype(np.float32) * 0.3
    result = quick_morph(source, modulator, intensity=0.5)
    assert len(result) == len(source)
    assert np.abs(result).max() <= 1.0


@runner.test("NaN/Inf handling in input")
def test_nan_inf():
    source = np.random.randn(22050).astype(np.float32)
    source[1000] = np.nan
    source[2000] = np.inf
    modulator = np.random.randn(22050).astype(np.float32)
    result = morph_audio(source, modulator)
    assert np.all(np.isfinite(result))


@runner.test("Repeated pattern audio")
def test_repeated_pattern():
    pattern = np.random.randn(1000).astype(np.float32)
    source = np.tile(pattern, 22)[:22050]
    modulator = np.tile(pattern[::-1], 22)[:22050]
    result = morph_audio(source, modulator)
    assert len(result) == len(source)
    assert np.all(np.isfinite(result))


@runner.test("Full pipeline integration")
def test_full_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source
        source_file = Path(tmpdir) / "source.wav"
        sf.write(source_file, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        
        # Create modulator
        mod_file = Path(tmpdir) / "mod.wav"
        sf.write(mod_file, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        
        # Load
        handler = InputHandler()
        with open(source_file, "rb") as f:
            source = handler.from_upload(f.read(), "source.wav")
        with open(mod_file, "rb") as f:
            modulator = handler.from_upload(f.read(), "mod.wav")
        
        # Morph
        result = morph_audio(source.audio, modulator.audio)
        
        # Export
        opts = ExportOptions(format=ExportFormat.WAV)
        exported = export_audio(result, opts)
        
        assert isinstance(exported, bytes)
        assert len(exported) > 0


@runner.test("Various durations")
def test_various_durations():
    durations = [0.1, 0.5, 1.0, 5.0]
    for duration in durations:
        samples = int(22050 * duration)
        source = np.random.randn(samples).astype(np.float32) * 0.3
        modulator = np.random.randn(samples).astype(np.float32) * 0.3
        result = morph_audio(source, modulator)
        assert len(result) >= len(source)


if __name__ == "__main__":
    success = runner.run()
    sys.exit(0 if success else 1)
