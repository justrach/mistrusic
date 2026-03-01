"""Tests for the spectral morphing engine."""

import pytest
import numpy as np
from src.morph_engine import (
    MorphParams,
    stft,
    istft,
    extract_spectral_envelope,
    cross_synthesize,
    morph_audio,
    quick_morph,
    MorphEngine,
)


class TestMorphParams:
    """Test MorphParams dataclass."""
    
    def test_default_values(self):
        """Test default parameter values."""
        params = MorphParams()
        assert params.spectral_resolution == 2048
        assert params.sharpness == 0.5
        assert params.harmonic_balance == 0.5
        assert params.blend_ratio == 0.5
        assert params.formant_shift == 0.0
        assert params.preserve_transients is True
        assert params.smoothing == 0.3
    
    def test_auto_hop_size(self):
        """Test hop size auto-calculation."""
        params = MorphParams(spectral_resolution=2048)
        assert params.hop_size == 512  # 2048 // 4
    
    def test_clamping(self):
        """Test parameter clamping."""
        params = MorphParams(
            spectral_resolution=100,  # Too small
            sharpness=2.0,  # Too large
            harmonic_balance=-0.5,  # Too small
            formant_shift=50,  # Too large
        )
        assert params.spectral_resolution == 512  # Clamped to min
        assert params.sharpness == 1.0
        assert params.harmonic_balance == 0.0
        assert params.formant_shift == 24.0
    
    def test_power_of_two_rounding(self):
        """Test FFT size is rounded to power of 2."""
        params = MorphParams(spectral_resolution=3000)
        # Should round to nearest power of 2
        assert params.spectral_resolution in [2048, 4096]


class TestSTFT:
    """Test STFT/ISTFT functions."""
    
    def test_stft_dimensions(self):
        """Test STFT output dimensions."""
        sr = 22050
        audio = np.random.randn(sr).astype(np.float32)  # 1 second
        window_size = 2048
        hop_size = 512
        
        spec = stft(audio, window_size, hop_size)
        
        # Frequency bins = window_size // 2 + 1
        assert spec.shape[0] == window_size // 2 + 1
        # Time frames approximately sample_count / hop_size
        expected_frames = 1 + (len(audio) + window_size * 2 - window_size) // hop_size
        assert abs(spec.shape[1] - expected_frames) < 5
    
    def test_istft_reconstruction(self):
        """Test perfect reconstruction with no modification."""
        sr = 22050
        audio = np.random.randn(sr).astype(np.float32)
        audio = audio / np.abs(audio).max() * 0.5
        
        window_size = 2048
        hop_size = 512
        
        spec = stft(audio, window_size, hop_size)
        reconstructed = istft(spec, window_size, hop_size, original_length=len(audio))
        
        # Should be close to original (within tolerance for overlap-add)
        assert len(reconstructed) == len(audio)
        # Reconstruction won't be perfect due to windowing, but should be close
        correlation = np.corrcoef(audio, reconstructed)[0, 1]
        assert correlation > 0.95


class TestSpectralEnvelope:
    """Test spectral envelope extraction."""
    
    def test_envelope_smoothness(self):
        """Test that extracted envelope is smoother than original."""
        # Create a spectrum with peaks
        spectrum = np.abs(np.random.randn(1025)) + 1.0
        
        envelope = extract_spectral_envelope(spectrum, smoothing=0.5)
        
        # Envelope should have lower variance (smoother)
        spectrum_var = np.var(spectrum)
        envelope_var = np.var(envelope)
        assert envelope_var < spectrum_var
    
    def test_envelope_positive(self):
        """Test envelope is always positive."""
        spectrum = np.abs(np.random.randn(1025))
        envelope = extract_spectral_envelope(spectrum, smoothing=0.3)
        assert np.all(envelope > 0)


class TestCrossSynthesis:
    """Test cross-synthesis function."""
    
    def test_output_shape(self):
        """Test output has same shape as input."""
        source = np.abs(np.random.randn(1025))
        modulator = np.abs(np.random.randn(1025))
        params = MorphParams()
        
        result = cross_synthesize(source, modulator, params, sample_rate=22050)
        
        assert result.shape == source.shape
    
    def test_blend_ratio_effect(self):
        """Test that blend ratio affects output."""
        source = np.ones(1025) * 0.5
        modulator = np.ones(1025) * 1.0
        
        # With blend_ratio=0, should be closer to source
        params_low = MorphParams(blend_ratio=0.1, sharpness=0.5)
        result_low = cross_synthesize(source, modulator, params_low, 22050)
        
        # With blend_ratio=1, should be closer to modulator
        params_high = MorphParams(blend_ratio=0.9, sharpness=0.5)
        result_high = cross_synthesize(source, modulator, params_high, 22050)
        
        # High blend should result in higher values (modulator > source)
        assert np.mean(result_high) > np.mean(result_low)


class TestMorphAudio:
    """Test the main morph_audio function."""
    
    def test_output_length(self):
        """Test output length matches input."""
        sr = 22050
        source = np.random.randn(sr).astype(np.float32)
        modulator = np.random.randn(sr).astype(np.float32)
        
        result = morph_audio(source, modulator)
        
        assert len(result) == len(source)
    
    def test_output_normalized(self):
        """Test output is normalized."""
        source = np.random.randn(22050).astype(np.float32)
        modulator = np.random.randn(22050).astype(np.float32)
        
        result = morph_audio(source, modulator)
        
        assert np.abs(result).max() <= 1.0
    
    def test_different_length_inputs(self):
        """Test morphing with different length inputs."""
        source = np.random.randn(22050).astype(np.float32)
        modulator = np.random.randn(11025).astype(np.float32)  # Half length
        
        result = morph_audio(source, modulator)
        
        # Should match longer length
        assert len(result) == len(source)
    
    def test_quick_morph(self):
        """Test quick_morph convenience function."""
        source = np.random.randn(22050).astype(np.float32)
        modulator = np.random.randn(22050).astype(np.float32)
        
        result = quick_morph(source, modulator, intensity=0.5)
        
        assert len(result) == len(source)
        assert np.abs(result).max() <= 1.0


class TestMorphEngine:
    """Test MorphEngine class."""
    
    def test_morph_method(self):
        """Test engine morph method."""
        engine = MorphEngine(sample_rate=22050)
        source = np.random.randn(22050).astype(np.float32)
        modulator = np.random.randn(22050).astype(np.float32)
        
        result = engine.morph(source, modulator)
        
        assert len(result) == len(source)
    
    def test_preset_styles(self):
        """Test preset style morphing."""
        engine = MorphEngine()
        source = np.random.randn(22050).astype(np.float32)
        modulator = np.random.randn(22050).astype(np.float32)
        
        styles = ["subtle", "moderate", "intense", "extreme"]
        for style in styles:
            result = engine.morph_with_style(source, modulator, style)
            assert len(result) == len(source)
    
    def test_invalid_style(self):
        """Test invalid style falls back to moderate."""
        engine = MorphEngine()
        source = np.random.randn(22050).astype(np.float32)
        modulator = np.random.randn(22050).astype(np.float32)
        
        # Should not raise error
        result = engine.morph_with_style(source, modulator, "invalid_style")
        assert len(result) == len(source)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_silence_input(self):
        """Test handling of silent input."""
        source = np.zeros(22050, dtype=np.float32)
        modulator = np.random.randn(22050).astype(np.float32)
        
        result = morph_audio(source, modulator)
        
        # Should handle gracefully without errors
        assert len(result) == len(source)
        assert np.all(np.isfinite(result))
    
    def test_very_short_audio(self):
        """Test with very short audio."""
        source = np.random.randn(100).astype(np.float32)
        modulator = np.random.randn(100).astype(np.float32)
        
        result = morph_audio(source, modulator)
        
        assert len(result) >= len(source)  # May be padded
    
    def test_single_channel(self):
        """Test with mono audio."""
        source = np.random.randn(22050).astype(np.float32)
        modulator = np.random.randn(22050).astype(np.float32)
        
        result = morph_audio(source, modulator)
        
        # Result should be 1D
        assert result.ndim == 1
