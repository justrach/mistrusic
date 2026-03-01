"""Spectral morphing engine for cross-synthesis between audio signals.

This module implements the core "light through colored glass" effect:
taking a source signal and filtering it through the spectral characteristics
of a modulator signal, with full control over spectral parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np
from numpy.fft import fft, ifft, fftfreq
import scipy.signal
from scipy.ndimage import gaussian_filter1d


@dataclass
class MorphParams:
    """Parameters for spectral morphing control.
    
    These parameters give full control over the spectral transformation process,
    similar to adjusting how light passes through different materials.
    
    Attributes:
        spectral_resolution: FFT window size (power of 2, e.g., 1024, 2048, 4096)
            Higher = better frequency resolution, lower time resolution
        hop_size: Frame overlap (typically window_size // 4)
        sharpness: How sharply the filter is applied (0.0 = smooth, 1.0 = sharp)
        harmonic_balance: Balance between harmonic and noise content (0-1)
        blend_ratio: Mix between source and modulator (0.0 = all source, 1.0 = all modulator)
        formant_shift: Shift formant frequencies (semitones, -12 to +12)
        preserve_transients: Keep sharp attacks from source (True/False)
        smoothing: Temporal smoothing of spectral envelope (0.0 = none, 1.0 = heavy)
    """
    spectral_resolution: int = 2048  # FFT window size
    hop_size: int | None = None  # None = auto (window // 4)
    sharpness: float = 0.5  # 0.0 to 1.0
    harmonic_balance: float = 0.5  # 0.0 to 1.0
    blend_ratio: float = 0.5  # 0.0 to 1.0
    formant_shift: float = 0.0  # semitones
    preserve_transients: bool = True
    smoothing: float = 0.3  # 0.0 to 1.0
    
    def __post_init__(self):
        if self.hop_size is None:
            self.hop_size = self.spectral_resolution // 4
        
        # Clamp values to valid ranges
        self.spectral_resolution = max(512, min(8192, self.spectral_resolution))
        self.spectral_resolution = 2 ** int(np.log2(self.spectral_resolution))
        self.sharpness = max(0.0, min(1.0, self.sharpness))
        self.harmonic_balance = max(0.0, min(1.0, self.harmonic_balance))
        self.blend_ratio = max(0.0, min(1.0, self.blend_ratio))
        self.formant_shift = max(-24.0, min(24.0, self.formant_shift))
        self.smoothing = max(0.0, min(1.0, self.smoothing))


def stft(
    audio: np.ndarray,
    window_size: int,
    hop_size: int,
    window: str = "hann"
) -> np.ndarray:
    """Short-Time Fourier Transform.
    
    Args:
        audio: Input audio signal
        window_size: FFT window size
        hop_size: Hop between frames
        window: Window function name
        
    Returns:
        Complex STFT matrix (freq_bins x time_frames)
    """
    # Pad audio to handle edges
    pad_len = window_size
    audio = np.pad(audio, (pad_len, pad_len), mode="constant")
    
    # Create window
    if window == "hann":
        win = np.hanning(window_size)
    elif window == "hamming":
        win = np.hamming(window_size)
    else:
        win = np.ones(window_size)
    
    # Calculate frames
    n_frames = 1 + (len(audio) - window_size) // hop_size
    n_freq = window_size // 2 + 1
    
    stft_matrix = np.zeros((n_freq, n_frames), dtype=np.complex64)
    
    for i in range(n_frames):
        start = i * hop_size
        frame = audio[start:start + window_size] * win
        stft_matrix[:, i] = fft(frame)[:n_freq]
    
    return stft_matrix


def istft(
    stft_matrix: np.ndarray,
    window_size: int,
    hop_size: int,
    window: str = "hann",
    original_length: int | None = None
) -> np.ndarray:
    """Inverse Short-Time Fourier Transform.
    
    Args:
        stft_matrix: Complex STFT matrix
        window_size: FFT window size
        hop_size: Hop between frames
        window: Window function name
        original_length: Expected output length
        
    Returns:
        Reconstructed audio signal
    """
    n_freq, n_frames = stft_matrix.shape
    
    # Create window
    if window == "hann":
        win = np.hanning(window_size)
    elif window == "hamming":
        win = np.hamming(window_size)
    else:
        win = np.ones(window_size)
    
    # Window compensation for overlap-add
    window_sum = np.zeros(n_frames * hop_size + window_size)
    for i in range(n_frames):
        window_sum[i * hop_size:i * hop_size + window_size] += win ** 2
    window_sum = np.maximum(window_sum, 1e-8)
    
    # Reconstruct
    audio = np.zeros(n_frames * hop_size + window_size)
    
    for i in range(n_frames):
        # Reconstruct full FFT from half
        spec = stft_matrix[:, i]
        full_spec = np.concatenate([spec, np.conj(spec[-2:0:-1])])
        frame = np.real(ifft(full_spec))
        audio[i * hop_size:i * hop_size + window_size] += frame * win
    
    # Normalize by window sum
    audio /= window_sum
    
    # Remove padding
    audio = audio[window_size:-window_size]
    
    if original_length is not None:
        audio = audio[:original_length]
    
    return audio.astype(np.float32)


def extract_spectral_envelope(
    magnitude: np.ndarray,
    smoothing: float = 0.3
) -> np.ndarray:
    """Extract smooth spectral envelope using cepstral smoothing.
    
    Args:
        magnitude: Magnitude spectrum
        smoothing: Smoothing factor (0-1)
        
    Returns:
        Smoothed spectral envelope
    """
    # Convert to log domain
    log_mag = np.log(magnitude + 1e-8)
    
    # Cepstral analysis
    cepstrum = np.real(ifft(log_mag))
    
    # Smooth by keeping only low quefrencies
    # Higher smoothing = more aggressive lowpass
    cutoff = int(len(cepstrum) * (1 - smoothing) * 0.5)
    cepstrum_smooth = cepstrum.copy()
    cepstrum_smooth[cutoff:-cutoff] = 0
    
    # Back to spectral domain
    envelope = np.exp(np.real(fft(cepstrum_smooth, n=len(magnitude))))
    
    return envelope


def apply_formant_shift(
    spectrum: np.ndarray,
    shift_semitones: float,
    sample_rate: int
) -> np.ndarray:
    """Shift formant frequencies of a spectrum.
    
    Args:
        spectrum: Magnitude spectrum
        shift_semitones: Shift amount in semitones
        sample_rate: Audio sample rate
        
    Returns:
        Formant-shifted spectrum
    """
    if abs(shift_semitones) < 0.1:
        return spectrum
    
    n_bins = len(spectrum)
    
    # Calculate frequency per bin
    freqs = np.linspace(0, sample_rate / 2, n_bins)
    
    # Shift factor
    shift_factor = 2 ** (shift_semitones / 12)
    
    # Interpolate to shift
    new_freqs = freqs / shift_factor
    shifted = np.interp(freqs, new_freqs, spectrum, left=spectrum[0], right=spectrum[-1])
    
    return shifted


def cross_synthesize(
    source_spec: np.ndarray,
    modulator_spec: np.ndarray,
    params: MorphParams,
    sample_rate: int
) -> np.ndarray:
    """Perform cross-synthesis between two spectra.
    
    This is the core "light through colored glass" effect - the source
    spectrum (light) is filtered through the modulator spectrum (colored glass).
    
    Args:
        source_spec: Source magnitude spectrum
        modulator_spec: Modulator/filter magnitude spectrum
        params: Morphing parameters
        sample_rate: Audio sample rate
        
    Returns:
        Cross-synthesized magnitude spectrum
    """
    # Extract spectral envelopes
    source_env = extract_spectral_envelope(source_spec, params.smoothing)
    modulator_env = extract_spectral_envelope(modulator_spec, params.smoothing)
    
    # Apply formant shift to modulator
    if abs(params.formant_shift) > 0.1:
        modulator_env = apply_formant_shift(modulator_env, params.formant_shift, sample_rate)
    
    # Calculate spectral ratio (how much to apply the filter)
    # Avoid division by zero
    source_env_safe = np.maximum(source_env, 1e-8)
    spectral_ratio = modulator_env / source_env_safe
    
    # Apply sharpness control
    # 0 = very smooth transition, 1 = sharp/filter-like
    if params.sharpness < 0.5:
        # Smooth: soften the ratio
        alpha = 1 - (0.5 - params.sharpness) * 2  # 0 to 1
        spectral_ratio = spectral_ratio ** alpha
    else:
        # Sharp: make more selective
        alpha = 1 + (params.sharpness - 0.5) * 2  # 1 to 2
        spectral_ratio = np.clip(spectral_ratio ** alpha, 0, 10)
    
    # Apply harmonic balance
    # 0 = preserve more source texture (noise), 1 = more harmonic structure
    harmonic_factor = params.harmonic_balance
    
    # Get fine structure (harmonics) and coarse structure (envelope)
    source_fine = source_spec / np.maximum(source_env, 1e-8)
    
    # Blend between original and filtered
    # The filtered version applies the modulator's envelope
    filtered = source_spec * spectral_ratio
    
    # Mix based on harmonic balance and blend ratio
    # harmonic_balance controls how much envelope vs fine structure
    result = (source_env * harmonic_factor + source_fine * (1 - harmonic_factor))
    result *= spectral_ratio ** params.blend_ratio
    result *= source_spec ** (1 - params.blend_ratio)
    
    # Ensure finite values
    result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
    
    return result


def detect_transients(
    audio: np.ndarray,
    window_size: int = 512,
    threshold: float = 2.0
) -> np.ndarray:
    """Detect transient locations in audio.
    
    Args:
        audio: Input audio
        window_size: Analysis window
        threshold: Detection threshold
        
    Returns:
        Boolean array indicating transient positions
    """
    # Compute onset envelope using energy flux
    energy = audio ** 2
    
    # Local energy difference
    local_diff = np.diff(energy, prepend=energy[0])
    
    # Positive changes only (energy increases)
    onset_env = np.maximum(local_diff, 0)
    
    # Smooth
    onset_env = np.convolve(onset_env, np.ones(window_size) / window_size, mode="same")
    
    # Normalize
    onset_env /= np.maximum(onset_env.max(), 1e-8)
    
    # Detect peaks above threshold
    transient_mask = onset_env > threshold * onset_env.mean()
    
    return transient_mask


def morph_audio(
    source: np.ndarray,
    modulator: np.ndarray,
    params: MorphParams | None = None,
    sample_rate: int = 22050
) -> np.ndarray:
    """Morph two audio signals using spectral cross-synthesis.
    
    This is the main entry point - takes a source signal and filters it
    through the spectral characteristics of the modulator.
    
    Args:
        source: Source audio signal (the "light")
        modulator: Modulator audio signal (the "colored glass")
        params: Morphing parameters (uses defaults if None)
        sample_rate: Audio sample rate
        
    Returns:
        Morphed audio signal
    """
    if params is None:
        params = MorphParams()
    
    # Clean inputs - replace NaN/Inf with zeros
    source = np.nan_to_num(source, nan=0.0, posinf=0.0, neginf=0.0)
    modulator = np.nan_to_num(modulator, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Ensure same length (loop shorter one)
    max_len = max(len(source), len(modulator))
    if len(source) < max_len:
        source = np.tile(source, int(np.ceil(max_len / len(source))))[:max_len]
    if len(modulator) < max_len:
        modulator = np.tile(modulator, int(np.ceil(max_len / len(modulator))))[:max_len]
    
    source = source[:max_len]
    modulator = modulator[:max_len]
    
    # Detect transients in source if requested
    transient_mask = None
    if params.preserve_transients:
        transient_mask = detect_transients(source)
    
    # STFT of both signals
    source_stft = stft(source, params.spectral_resolution, params.hop_size)
    modulator_stft = stft(modulator, params.spectral_resolution, params.hop_size)
    
    # Get magnitudes and phases
    source_mag = np.abs(source_stft)
    source_phase = np.angle(source_stft)
    modulator_mag = np.abs(modulator_stft)
    
    # Cross-synthesize each frame
    n_frames = source_stft.shape[1]
    result_mag = np.zeros_like(source_mag)
    
    for i in range(n_frames):
        result_mag[:, i] = cross_synthesize(
            source_mag[:, i],
            modulator_mag[:, i],
            params,
            sample_rate
        )
    
    # Preserve transients if requested
    if transient_mask is not None:
        # Map transient mask to STFT frames
        hop = params.hop_size
        for i in range(n_frames):
            frame_start = i * hop
            frame_end = min(frame_start + params.spectral_resolution, len(transient_mask))
            if frame_end > frame_start and transient_mask[frame_start:frame_end].any():
                # Blend back some original magnitude at transients
                blend = 0.5  # 50% original at transients
                result_mag[:, i] = blend * source_mag[:, i] + (1 - blend) * result_mag[:, i]
    
    # Reconstruct with original phase (phase vocoder approach)
    # More advanced: use phase from modulator in some frequency regions
    result_stft = result_mag * np.exp(1j * source_phase)
    
    # ISTFT
    result = istft(result_stft, params.spectral_resolution, params.hop_size, original_length=max_len)
    
    # Normalize output
    peak = np.abs(result).max()
    if peak > 1e-8:
        result = result / peak * 0.95
    
    return result.astype(np.float32)


def quick_morph(
    source: np.ndarray,
    modulator: np.ndarray,
    intensity: float = 0.5,
    sample_rate: int = 22050
) -> np.ndarray:
    """Quick morph with simplified controls.
    
    Args:
        source: Source audio
        modulator: Modulator audio
        intensity: Morphing intensity (0-1)
        sample_rate: Audio sample rate
        
    Returns:
        Morphed audio
    """
    params = MorphParams(
        spectral_resolution=2048,
        sharpness=intensity,
        harmonic_balance=0.5,
        blend_ratio=intensity,
        preserve_transients=True,
        smoothing=0.5 - intensity * 0.3
    )
    return morph_audio(source, modulator, params, sample_rate)


class MorphEngine:
    """High-level interface for the morphing engine."""
    
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        self._cached_modulator: tuple[np.ndarray, np.ndarray] | None = None
    
    def morph(
        self,
        source: np.ndarray,
        modulator: np.ndarray,
        params: MorphParams | None = None
    ) -> np.ndarray:
        """Apply morphing effect."""
        return morph_audio(source, modulator, params, self.sample_rate)
    
    def morph_with_style(
        self,
        source: np.ndarray,
        modulator: np.ndarray,
        style: Literal["subtle", "moderate", "intense", "extreme"]
    ) -> np.ndarray:
        """Morph with preset style."""
        presets = {
            "subtle": MorphParams(blend_ratio=0.25, sharpness=0.3, smoothing=0.5),
            "moderate": MorphParams(blend_ratio=0.5, sharpness=0.5, smoothing=0.3),
            "intense": MorphParams(blend_ratio=0.75, sharpness=0.7, smoothing=0.2),
            "extreme": MorphParams(blend_ratio=0.9, sharpness=0.9, smoothing=0.1),
        }
        params = presets.get(style, presets["moderate"])
        return self.morph(source, modulator, params)
