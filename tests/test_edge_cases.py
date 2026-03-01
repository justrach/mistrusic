"""Edge case tests for the sound morphing system."""

import pytest
import numpy as np
import soundfile as sf
import io
import tempfile
from pathlib import Path

from src.morph_engine import (
    MorphParams, stft, istft, morph_audio, quick_morph, 
    extract_spectral_envelope, cross_synthesize, MorphEngine
)
from src.input_handler import InputHandler, AudioSource, InputSourceType
from src.export import export_audio, ExportOptions, ExportFormat
from src.sound_library import SoundLibrary, SoundMetadata


class TestMorphEngineEdgeCases:
    """Edge cases for the morphing engine."""
    
    def test_silence_source(self):
        """Test morphing with silent source audio."""
        source = np.zeros(22050, dtype=np.float32)
        modulator = np.random.randn(22050).astype(np.float32) * 0.3
        
        result = morph_audio(source, modulator)
        
        assert len(result) == len(source)
        assert np.all(np.isfinite(result))
        assert result.dtype == np.float32
    
    def test_silence_modulator(self):
        """Test morphing with silent modulator."""
        source = np.random.randn(22050).astype(np.float32) * 0.3
        modulator = np.zeros(22050, dtype=np.float32)
        
        result = morph_audio(source, modulator)
        
        assert len(result) == len(source)
        assert np.all(np.isfinite(result))
    
    def test_both_silent(self):
        """Test morphing when both inputs are silent."""
        source = np.zeros(22050, dtype=np.float32)
        modulator = np.zeros(22050, dtype=np.float32)
        
        result = morph_audio(source, modulator)
        
        assert len(result) == len(source)
        assert np.all(result == 0)
    
    def test_very_short_audio(self):
        """Test with very short audio (< 1 frame)."""
        source = np.random.randn(100).astype(np.float32)
        modulator = np.random.randn(100).astype(np.float32)
        
        result = morph_audio(source, modulator)
        
        assert np.all(np.isfinite(result))
    
    def test_single_sample(self):
        """Test with single sample audio."""
        source = np.array([0.5], dtype=np.float32)
        modulator = np.array([0.3], dtype=np.float32)
        
        result = morph_audio(source, modulator)
        
        assert np.all(np.isfinite(result))
    
    def test_very_long_audio(self):
        """Test with long audio (30 seconds)."""
        sr = 22050
        duration = 30  # seconds
        samples = sr * duration
        
        source = np.random.randn(samples).astype(np.float32) * 0.3
        modulator = np.random.randn(samples).astype(np.float32) * 0.3
        
        result = morph_audio(source, modulator)
        
        assert len(result) == len(source)
        assert np.all(np.isfinite(result))
    
    def test_extreme_volume_difference(self):
        """Test with very different volume levels."""
        source = np.random.randn(22050).astype(np.float32) * 0.001  # Very quiet
        modulator = np.random.randn(22050).astype(np.float32) * 0.999  # Very loud
        
        result = morph_audio(source, modulator)
        
        assert np.all(np.isfinite(result))
        assert np.abs(result).max() <= 1.0
    
    def test_extreme_frequency_content(self):
        """Test with extreme frequency content."""
        sr = 22050
        t = np.linspace(0, 1, sr)
        
        # Very low frequency
        source = np.sin(2 * np.pi * 20 * t).astype(np.float32)  # 20 Hz
        # Very high frequency
        modulator = np.sin(2 * np.pi * 10000 * t).astype(np.float32)  # 10 kHz
        
        result = morph_audio(source, modulator)
        
        assert len(result) == len(source)
        assert np.all(np.isfinite(result))
    
    def test_impulse_source(self):
        """Test with impulse signal (single spike)."""
        source = np.zeros(22050, dtype=np.float32)
        source[11025] = 1.0  # Single spike in middle
        modulator = np.random.randn(22050).astype(np.float32) * 0.3
        
        result = morph_audio(source, modulator)
        
        assert np.all(np.isfinite(result))
    
    def test_repeated_pattern(self):
        """Test with periodic/repeated patterns."""
        pattern = np.random.randn(1000).astype(np.float32)
        source = np.tile(pattern, 22)[:22050]
        modulator = np.tile(pattern[::-1], 22)[:22050]
        
        result = morph_audio(source, modulator)
        
        assert len(result) == len(source)
        assert np.all(np.isfinite(result))
    
    def test_nan_inf_handling(self):
        """Test handling of NaN/Inf in input."""
        source = np.random.randn(22050).astype(np.float32)
        source[1000] = np.nan
        source[2000] = np.inf
        
        modulator = np.random.randn(22050).astype(np.float32)
        
        # Should handle gracefully
        result = morph_audio(source, modulator)
        
        assert np.all(np.isfinite(result))
    
    def test_extreme_blend_ratios(self):
        """Test with extreme blend ratios."""
        source = np.random.randn(22050).astype(np.float32) * 0.5
        modulator = np.random.randn(22050).astype(np.float32) * 0.5
        
        # Full source
        result_0 = morph_audio(source, modulator, MorphParams(blend_ratio=0.0))
        # Full modulator
        result_1 = morph_audio(source, modulator, MorphParams(blend_ratio=1.0))
        
        assert np.all(np.isfinite(result_0))
        assert np.all(np.isfinite(result_1))
    
    def test_extreme_formant_shift(self):
        """Test with extreme formant shift."""
        source = np.random.randn(22050).astype(np.float32) * 0.3
        modulator = np.random.randn(22050).astype(np.float32) * 0.3
        
        # Max shift up and down
        result_up = morph_audio(source, modulator, MorphParams(formant_shift=24))
        result_down = morph_audio(source, modulator, MorphParams(formant_shift=-24))
        
        assert np.all(np.isfinite(result_up))
        assert np.all(np.isfinite(result_down))
    
    def test_all_presets(self):
        """Test all preset styles don't crash."""
        engine = MorphEngine()
        source = np.random.randn(22050).astype(np.float32) * 0.3
        modulator = np.random.randn(22050).astype(np.float32) * 0.3
        
        styles = ["subtle", "moderate", "intense", "extreme", "invalid_style"]
        
        for style in styles:
            result = engine.morph_with_style(source, modulator, style)
            assert np.all(np.isfinite(result))
    
    def test_various_fft_sizes(self):
        """Test various FFT window sizes."""
        source = np.random.randn(22050).astype(np.float32) * 0.3
        modulator = np.random.randn(22050).astype(np.float32) * 0.3
        
        sizes = [512, 1024, 2048, 4096, 8192]
        
        for size in sizes:
            params = MorphParams(spectral_resolution=size)
            result = morph_audio(source, modulator, params)
            assert np.all(np.isfinite(result))
    
    def test_transient_preservation_toggle(self):
        """Test with transient preservation on/off."""
        # Create signal with sharp transient
        source = np.zeros(22050, dtype=np.float32)
        source[5000:5020] = 1.0  # Sharp attack
        modulator = np.random.randn(22050).astype(np.float32) * 0.3
        
        with_transients = morph_audio(source, modulator, MorphParams(preserve_transients=True))
        without_transients = morph_audio(source, modulator, MorphParams(preserve_transients=False))
        
        assert np.all(np.isfinite(with_transients))
        assert np.all(np.isfinite(without_transients))


class TestInputHandlerEdgeCases:
    """Edge cases for input handling."""
    
    def test_empty_file(self, tmp_path):
        """Test handling empty file."""
        empty_file = tmp_path / "empty.wav"
        sf.write(empty_file, np.array([], dtype=np.float32), 22050)
        
        handler = InputHandler()
        
        with open(empty_file, "rb") as f:
            content = f.read()
        
        # Should handle gracefully
        source = handler.from_upload(content, "empty.wav")
        assert len(source.audio) == 0
    
    def test_very_long_upload(self, tmp_path):
        """Test handling long audio file."""
        long_file = tmp_path / "long.wav"
        # 6 minutes (exceeds 5 min limit)
        audio = np.random.randn(22050 * 360).astype(np.float32) * 0.3
        sf.write(long_file, audio, 22050)
        
        handler = InputHandler()
        
        with open(long_file, "rb") as f:
            content = f.read()
        
        with pytest.raises(ValueError) as exc_info:
            handler.from_upload(content, "long.wav")
        
        assert "too long" in str(exc_info.value).lower()
    
    def test_unsupported_format(self):
        """Test unsupported file format."""
        handler = InputHandler()
        
        with pytest.raises(ValueError) as exc_info:
            handler.from_upload(b"fake data", "file.xyz")
        
        assert "unsupported" in str(exc_info.value).lower()
    
    def test_corrupted_audio_file(self, tmp_path):
        """Test corrupted audio file."""
        corrupt_file = tmp_path / "corrupt.wav"
        corrupt_file.write_text("not valid audio data")
        
        handler = InputHandler()
        
        with open(corrupt_file, "rb") as f:
            content = f.read()
        
        with pytest.raises(Exception):
            handler.from_upload(content, "corrupt.wav")
    
    def test_different_sample_rates(self, tmp_path):
        """Test handling different sample rates."""
        rates = [8000, 16000, 22050, 44100, 48000, 96000]
        
        for rate in rates:
            audio_file = tmp_path / f"audio_{rate}.wav"
            duration = 1.0  # 1 second
            audio = np.random.randn(int(rate * duration)).astype(np.float32) * 0.3
            sf.write(audio_file, audio, rate)
            
            handler = InputHandler()
            
            with open(audio_file, "rb") as f:
                content = f.read()
            
            source = handler.from_upload(content, f"audio_{rate}.wav")
            assert source.sample_rate == 22050  # Should resample to target
    
    def test_stereo_to_mono_conversion(self, tmp_path):
        """Test stereo to mono conversion."""
        stereo_file = tmp_path / "stereo.wav"
        stereo = np.random.randn(22050, 2).astype(np.float32) * 0.3
        sf.write(stereo_file, stereo, 22050)
        
        handler = InputHandler()
        
        with open(stereo_file, "rb") as f:
            content = f.read()
        
        source = handler.from_upload(content, "stereo.wav")
        assert source.audio.ndim == 1  # Should be mono
    
    def test_multichannel_audio(self, tmp_path):
        """Test multi-channel (5.1) audio handling."""
        multichannel_file = tmp_path / "multichannel.wav"
        multi = np.random.randn(22050, 6).astype(np.float32) * 0.3
        sf.write(multichannel_file, multi, 22050)
        
        handler = InputHandler()
        
        with open(multichannel_file, "rb") as f:
            content = f.read()
        
        source = handler.from_upload(content, "multichannel.wav")
        assert source.audio.ndim == 1  # Should be mono
    
    def test_library_sound_not_found(self):
        """Test requesting non-existent library sound."""
        lib = SoundLibrary()
        handler = InputHandler(lib)
        
        with pytest.raises(KeyError):
            handler.from_library("nonexistent_sound_12345")
    
    def test_library_audio_file_missing(self, tmp_path):
        """Test when library audio file is missing."""
        lib = SoundLibrary(tmp_path)
        
        # Add metadata for non-existent file
        meta = SoundMetadata(
            id="missing",
            name="Missing",
            description="Desc",
            category="test",
            path="audio/missing.wav",
            duration=1.0,
            sample_rate=22050,
            tags=[],
        )
        lib._index["missing"] = meta
        
        with pytest.raises(FileNotFoundError):
            lib.load_audio("missing")


class TestExportEdgeCases:
    """Edge cases for export functionality."""
    
    def test_export_silence(self):
        """Test exporting silent audio."""
        audio = np.zeros(22050, dtype=np.float32)
        opts = ExportOptions(format=ExportFormat.WAV)
        
        result = export_audio(audio, opts)
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_export_clipping(self):
        """Test export handles values > 1.0 by clipping."""
        audio = np.array([1.5, -1.5, 2.0, -2.0], dtype=np.float32)
        opts = ExportOptions(format=ExportFormat.WAV, normalize=False)
        
        result = export_audio(audio, opts)
        assert isinstance(result, bytes)
    
    def test_export_all_formats(self):
        """Test exporting all supported formats."""
        audio = np.random.randn(22050).astype(np.float32) * 0.3
        
        formats = [ExportFormat.WAV, ExportFormat.FLAC, ExportFormat.OGG]
        
        for fmt in formats:
            opts = ExportOptions(format=fmt)
            result = export_audio(audio, opts)
            assert isinstance(result, bytes)
            assert len(result) > 0
    
    def test_export_different_sample_rates(self):
        """Test exporting different sample rates."""
        audio = np.random.randn(22050).astype(np.float32) * 0.3
        
        rates = [8000, 16000, 22050, 44100, 48000]
        
        for rate in rates:
            opts = ExportOptions(format=ExportFormat.WAV, sample_rate=rate)
            result = export_audio(audio, opts)
            assert isinstance(result, bytes)
    
    def test_export_very_short_audio(self):
        """Test exporting very short audio."""
        audio = np.array([0.5], dtype=np.float32)
        opts = ExportOptions(format=ExportFormat.WAV)
        
        result = export_audio(audio, opts)
        assert isinstance(result, bytes)
    
    def test_export_to_file_permissions(self, tmp_path):
        """Test export file permissions issues."""
        # Try to write to read-only directory
        audio = np.random.randn(22050).astype(np.float32) * 0.3
        opts = ExportOptions(format=ExportFormat.WAV)
        
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o555)  # Read-only
        
        output_path = read_only_dir / "test.wav"
        
        with pytest.raises(PermissionError):
            export_audio(audio, opts, output_path)
        
        read_only_dir.chmod(0o755)  # Restore permissions


class TestSTFTEdgeCases:
    """Edge cases for STFT/ISTFT."""
    
    def test_stft_very_short_signal(self):
        """Test STFT with very short signal."""
        audio = np.random.randn(10).astype(np.float32)
        
        spec = stft(audio, 512, 128)
        assert spec.shape[0] == 257  # n_fft // 2 + 1
    
    def test_stft_window_larger_than_signal(self):
        """Test when window is larger than signal."""
        audio = np.random.randn(100).astype(np.float32)
        
        spec = stft(audio, 2048, 512)
        assert spec.shape[1] >= 1  # At least one frame
    
    def test_istft_perfect_reconstruction(self):
        """Test perfect reconstruction with no modification."""
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        audio = audio / np.abs(audio).max()  # Normalize
        
        window_size = 2048
        hop_size = 512
        
        spec = stft(audio, window_size, hop_size)
        reconstructed = istft(spec, window_size, hop_size, original_length=len(audio))
        
        # Should be close to original
        assert len(reconstructed) == len(audio)
        correlation = np.corrcoef(audio, reconstructed)[0, 1]
        assert correlation > 0.9
    
    def test_spectral_envelope_zeros(self):
        """Test envelope extraction with zeros."""
        spectrum = np.zeros(1025)
        
        envelope = extract_spectral_envelope(spectrum, smoothing=0.5)
        
        assert np.all(np.isfinite(envelope))
    
    def test_spectral_envelope_very_sparse(self):
        """Test envelope with sparse spectrum."""
        spectrum = np.zeros(1025)
        spectrum[100] = 1.0
        spectrum[500] = 0.5
        spectrum[1000] = 0.3
        
        envelope = extract_spectral_envelope(spectrum, smoothing=0.3)
        
        assert np.all(envelope > 0)
        assert np.all(np.isfinite(envelope))


class TestPerformanceEdgeCases:
    """Performance and stress tests."""
    
    def test_large_file_handling(self):
        """Test handling of large audio files."""
        # 5 minutes at 22kHz (max allowed)
        sr = 22050
        duration = 300  # 5 minutes
        samples = sr * duration
        
        source = np.random.randn(samples).astype(np.float32) * 0.3
        modulator = np.random.randn(samples).astype(np.float32) * 0.3
        
        # Should complete without memory error
        result = morph_audio(source, modulator)
        
        assert len(result) == len(source)
    
    def test_repeated_morph_calls(self):
        """Test multiple morph calls don't accumulate memory."""
        import gc
        
        source = np.random.randn(22050).astype(np.float32) * 0.3
        modulator = np.random.randn(22050).astype(np.float32) * 0.3
        
        # Run multiple times
        for _ in range(10):
            result = morph_audio(source, modulator)
            del result
            gc.collect()
        
        # If we get here without OOM, test passed
        assert True
    
    def test_parallel_morph_different_params(self):
        """Test morphing with various parameter combinations."""
        source = np.random.randn(22050).astype(np.float32) * 0.3
        modulator = np.random.randn(22050).astype(np.float32) * 0.3
        
        params_list = [
            MorphParams(blend_ratio=0.0),
            MorphParams(blend_ratio=1.0),
            MorphParams(sharpness=0.0),
            MorphParams(sharpness=1.0),
            MorphParams(formant_shift=12),
            MorphParams(formant_shift=-12),
            MorphParams(spectral_resolution=512),
            MorphParams(spectral_resolution=4096),
        ]
        
        for params in params_list:
            result = morph_audio(source, modulator, params)
            assert np.all(np.isfinite(result))


class TestIntegrationEdgeCases:
    """Integration-level edge cases."""
    
    def test_full_pipeline_silent_audio(self, tmp_path):
        """Test complete pipeline with silent audio."""
        # Create silent file
        silent_file = tmp_path / "silent.wav"
        sf.write(silent_file, np.zeros(22050, dtype=np.float32), 22050)
        
        # Load
        handler = InputHandler()
        with open(silent_file, "rb") as f:
            source = handler.from_upload(f.read(), "silent.wav")
        
        # Create modulator
        mod_file = tmp_path / "mod.wav"
        sf.write(mod_file, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        with open(mod_file, "rb") as f:
            modulator = handler.from_upload(f.read(), "mod.wav")
        
        # Morph
        result = morph_audio(source.audio, modulator.audio)
        
        # Export
        opts = ExportOptions(format=ExportFormat.WAV)
        exported = export_audio(result, opts)
        
        assert isinstance(exported, bytes)
    
    def test_full_pipeline_various_durations(self, tmp_path):
        """Test pipeline with various audio durations."""
        durations = [0.1, 0.5, 1.0, 5.0, 10.0]  # seconds
        
        for duration in durations:
            samples = int(22050 * duration)
            
            source = np.random.randn(samples).astype(np.float32) * 0.3
            modulator = np.random.randn(samples).astype(np.float32) * 0.3
            
            result = morph_audio(source, modulator)
            assert len(result) >= len(source)  # May be padded
            
            opts = ExportOptions(format=ExportFormat.WAV)
            exported = export_audio(result, opts)
            assert isinstance(exported, bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
