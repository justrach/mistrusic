import numpy as np
import librosa
from scipy.signal import fftconvolve, butter, sosfiltfilt
from scipy.ndimage import uniform_filter1d
from smolagents import Tool
from utils.audio_utils import load_audio, save_audio, temp_path, match_length, DEFAULT_SR


class MixAudioTool(Tool):
    name = "mix_audio"
    description = """Mixes two audio files together with a weighted ratio. ratio=0.0 gives 100% audio A, ratio=1.0 gives 100% audio B, ratio=0.5 is an equal blend. Use this to layer sounds together."""
    inputs = {
        "audio_a_path": {
            "type": "string",
            "description": "Path to the first audio file",
        },
        "audio_b_path": {
            "type": "string",
            "description": "Path to the second audio file",
        },
        "ratio": {
            "type": "number",
            "description": "Mix ratio from 0.0 (all A) to 1.0 (all B). Default 0.5.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, audio_a_path: str, audio_b_path: str, ratio: float = 0.5) -> str:
        ratio = max(0.0, min(1.0, float(ratio)))
        y_a, _ = load_audio(audio_a_path)
        y_b, _ = load_audio(audio_b_path)
        y_a, y_b = match_length(y_a, y_b)
        mixed = (1.0 - ratio) * y_a + ratio * y_b
        out = temp_path()
        save_audio(mixed, out)
        return out


class SpectralImprintTool(Tool):
    name = "spectral_imprint"
    description = """Applies Sound B's magnitude spectrum as a frequency-domain filter on Sound A. Uses time-varying spectral envelope for natural results. This transfers B's tonal character/texture onto A. Use for imposing tonal color, warmth, brightness, or texture from one sound onto another. smoothing controls how much B's spectrum is smoothed before applying (0=sharp, 1=very smooth)."""
    inputs = {
        "audio_a_path": {
            "type": "string",
            "description": "Path to the source audio (Sound A) that will be filtered",
        },
        "audio_b_path": {
            "type": "string",
            "description": "Path to the filter audio (Sound B) whose spectral shape is applied",
        },
        "smoothing": {
            "type": "number",
            "description": "Spectral smoothing for B's magnitude (0.0 to 1.0). Higher = smoother, broader filter shape. Default 0.3.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, audio_a_path: str, audio_b_path: str, smoothing: float = 0.4) -> str:
        smoothing = max(0.0, min(1.0, float(smoothing)))
        y_a, sr = load_audio(audio_a_path)
        y_b, _ = load_audio(audio_b_path)

        n_fft = 2048
        hop = 512
        S_a = librosa.stft(y_a, n_fft=n_fft, hop_length=hop)
        S_b = librosa.stft(y_b, n_fft=n_fft, hop_length=hop)

        mag_b = np.abs(S_b)

        # Time-varying spectral envelope using 500ms windows instead of static average
        window_frames = max(1, int(0.5 * sr / hop))  # 500ms in STFT frames
        # Smooth across time with a rolling window for time-varying envelope
        spectral_profile = uniform_filter1d(mag_b, size=window_frames, axis=1)

        # Align frame counts
        min_frames = min(S_a.shape[1], spectral_profile.shape[1])
        S_a = S_a[:, :min_frames]
        spectral_profile = spectral_profile[:, :min_frames]

        # Normalize per-frame to [0, 1]
        max_val = np.max(spectral_profile, axis=0, keepdims=True)
        max_val[max_val == 0] = 1.0
        spectral_profile = spectral_profile / max_val

        # Apply frequency-axis smoothing
        kernel_size = max(3, int(smoothing * 150))
        if kernel_size % 2 == 0:
            kernel_size += 1
        spectral_profile = uniform_filter1d(spectral_profile, size=kernel_size, axis=0)

        # Blend B's profile with flat (1.0) — use smoothing param to control strength
        blend_strength = 0.3 + smoothing * 0.5  # range 0.3-0.8 based on smoothing
        blended_profile = (1.0 - blend_strength) + blend_strength * spectral_profile
        S_out = S_a * blended_profile
        y_out = librosa.istft(S_out, hop_length=hop)

        out = temp_path()
        save_audio(y_out, out)
        return out


class ConvolutionTool(Tool):
    name = "convolution"
    description = """Convolves audio A through audio B using FFT convolution. This effectively uses B as an impulse response, transferring its spatial/reverb character onto A. Best when B has reverb, room tone, environmental, or percussive character. wet_dry controls how much of the convolved signal is mixed with the original (0=dry, 1=fully convolved). IR is trimmed to max 2 seconds with fade-out to prevent muddiness."""
    inputs = {
        "audio_path": {
            "type": "string",
            "description": "Path to the source audio to be convolved",
        },
        "impulse_path": {
            "type": "string",
            "description": "Path to the impulse response / environment audio",
        },
        "wet_dry": {
            "type": "number",
            "description": "Wet/dry mix from 0.0 (fully dry) to 1.0 (fully convolved). Default 0.5.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, audio_path: str, impulse_path: str, wet_dry: float = 0.5) -> str:
        wet_dry = max(0.0, min(1.0, float(wet_dry)))
        y_a, sr = load_audio(audio_path)
        y_ir, _ = load_audio(impulse_path)

        # Trim IR to max 2 seconds
        max_ir_samples = int(2.0 * sr)
        if len(y_ir) > max_ir_samples:
            y_ir = y_ir[:max_ir_samples]

        # Apply fade-out to IR tail (last 25%)
        fade_len = len(y_ir) // 4
        if fade_len > 0:
            fade = np.linspace(1.0, 0.0, fade_len)
            y_ir[-fade_len:] *= fade

        # Normalize impulse response
        ir_peak = np.max(np.abs(y_ir))
        if ir_peak > 0:
            y_ir = y_ir / ir_peak

        # Convolve
        convolved = fftconvolve(y_a, y_ir, mode="full")
        # Trim to original length
        convolved = convolved[: len(y_a)]

        # High-pass the convolved output at 60 Hz to reduce muddiness
        sos_hp = butter(4, 60, btype='high', fs=sr, output='sos')
        convolved = sosfiltfilt(sos_hp, convolved).astype(np.float32)

        # Wet/dry blend
        y_out = (1.0 - wet_dry) * y_a + wet_dry * convolved

        out = temp_path()
        save_audio(y_out, out)
        return out


class CrossSynthesisTool(Tool):
    name = "cross_synthesize"
    description = """Phase vocoder cross-synthesis via STFT. Takes the spectral envelope (timbre/formants) from the envelope source and the fine structure (pitch/rhythm) from the excitation source. This morphs the identity of one sound onto the temporal pattern of another. Most creative and dramatic option. strength controls how much of the cross-synthesis is blended (0=all original, 1=full cross-synthesis)."""
    inputs = {
        "envelope_source_path": {
            "type": "string",
            "description": "Path to audio providing the timbre/formant envelope",
        },
        "excitation_source_path": {
            "type": "string",
            "description": "Path to audio providing the pitch and rhythm (fine structure)",
        },
        "strength": {
            "type": "number",
            "description": "Cross-synthesis strength from 0.0 (all original) to 1.0 (full cross-synthesis). Default 0.6.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, envelope_source_path: str, excitation_source_path: str, strength: float = 0.6) -> str:
        strength = max(0.0, min(1.0, float(strength)))
        y_env, _ = load_audio(envelope_source_path)
        y_exc, _ = load_audio(excitation_source_path)

        n_fft = 2048
        hop = 256

        S_env = librosa.stft(y_env, n_fft=n_fft, hop_length=hop)
        S_exc = librosa.stft(y_exc, n_fft=n_fft, hop_length=hop)

        # Align frame counts
        min_frames = min(S_env.shape[1], S_exc.shape[1])
        S_env = S_env[:, :min_frames]
        S_exc = S_exc[:, :min_frames]

        # Compute smoothed spectral envelope (size=10 for more detail/character transfer)
        mag_env = np.abs(S_env)
        envelope = uniform_filter1d(mag_env, size=10, axis=0)

        # Normalize excitation magnitude per-frame
        mag_exc = np.abs(S_exc)
        exc_max = np.max(mag_exc, axis=0, keepdims=True)
        exc_max[exc_max == 0] = 1.0
        norm_exc = mag_exc / exc_max

        # Cross-synthesis: envelope source's spectral shape × excitation's fine structure
        cross_mag = envelope * norm_exc

        # At high strength, also blend in raw envelope magnitude for stronger character transfer
        if strength > 0.7:
            env_blend = (strength - 0.7) / 0.3  # 0-1 ramp above 0.7
            cross_mag = (1.0 - env_blend * 0.4) * cross_mag + (env_blend * 0.4) * mag_env

        out_mag = strength * cross_mag + (1.0 - strength) * mag_exc
        phase_exc = np.angle(S_exc)
        S_out = out_mag * np.exp(1j * phase_exc)

        y_out = librosa.istft(S_out, hop_length=hop)

        out = temp_path()
        save_audio(y_out, out)
        return out
