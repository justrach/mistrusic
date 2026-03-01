"""Sound synthesis engine for generating library sounds on-the-fly.

Instead of loading pre-recorded audio files, we synthesize sounds
dynamically using various synthesis techniques.
"""

from __future__ import annotations

import numpy as np
from numpy.fft import fft, ifft
import random


def generate_sine_wave(
    frequency: float,
    duration: float = 2.0,
    sample_rate: int = 22050,
    amplitude: float = 0.5
) -> np.ndarray:
    """Generate a pure sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sin(2 * np.pi * frequency * t) * amplitude
    # Apply envelope
    envelope = np.ones_like(wave)
    attack = int(0.01 * sample_rate)
    release = int(0.1 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    return (wave * envelope).astype(np.float32)


def generate_saw_wave(
    frequency: float,
    duration: float = 2.0,
    sample_rate: int = 22050,
    amplitude: float = 0.3
) -> np.ndarray:
    """Generate a sawtooth wave using additive synthesis."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.zeros_like(t)
    # Add harmonics
    for n in range(1, 20):
        wave += ((-1)**(n+1)) * np.sin(2 * np.pi * frequency * n * t) / n
    wave = wave * amplitude * 0.5
    # Apply envelope
    envelope = np.ones_like(wave)
    attack = int(0.01 * sample_rate)
    release = int(0.2 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    return (wave * envelope).astype(np.float32)


def generate_square_wave(
    frequency: float,
    duration: float = 2.0,
    sample_rate: int = 22050,
    amplitude: float = 0.3
) -> np.ndarray:
    """Generate a square wave using additive synthesis."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.zeros_like(t)
    # Add odd harmonics only
    for n in range(1, 20, 2):
        wave += np.sin(2 * np.pi * frequency * n * t) / n
    wave = wave * amplitude * 0.5
    # Apply envelope
    envelope = np.ones_like(wave)
    attack = int(0.01 * sample_rate)
    release = int(0.2 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    return (wave * envelope).astype(np.float32)


def generate_noise(
    duration: float = 2.0,
    sample_rate: int = 22050,
    color: str = "white",
    amplitude: float = 0.3
) -> np.ndarray:
    """Generate colored noise.
    
    Args:
        duration: Length in seconds
        sample_rate: Sample rate
        color: 'white', 'pink', 'brown'
        amplitude: Volume
    """
    samples = int(sample_rate * duration)
    white = np.random.randn(samples)
    
    if color == "white":
        noise = white
    elif color == "pink":
        # Pink noise: 1/f spectrum
        fft_vals = fft(white)
        freqs = np.fft.fftfreq(samples)
        freqs[0] = 1.0  # Avoid division by zero
        pink_filter = 1 / np.sqrt(np.abs(freqs))
        pink_filter[0] = 0
        noise = np.real(ifft(fft_vals * pink_filter))
    elif color == "brown":
        # Brown noise: 1/f^2 spectrum
        fft_vals = fft(white)
        freqs = np.fft.fftfreq(samples)
        freqs[0] = 1.0
        brown_filter = 1 / np.abs(freqs)
        brown_filter[0] = 0
        noise = np.real(ifft(fft_vals * brown_filter))
    else:
        noise = white
    
    # Normalize and apply envelope
    noise = noise / np.abs(noise).max() * amplitude
    envelope = np.ones_like(noise)
    attack = int(0.1 * sample_rate)
    release = int(0.5 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    return (noise * envelope).astype(np.float32)


def generate_rhythm(
    bpm: float = 120.0,
    duration: float = 4.0,
    sample_rate: int = 22050,
    pattern: str = "four_on_floor"
) -> np.ndarray:
    """Generate rhythmic patterns."""
    samples = int(sample_rate * duration)
    audio = np.zeros(samples, dtype=np.float32)
    
    beat_samples = int(60.0 / bpm * sample_rate)
    
    if pattern == "four_on_floor":
        # Kick on every beat
        for i in range(0, samples, beat_samples):
            if i + int(0.1 * sample_rate) < samples:
                # Generate kick drum
                kick = generate_kick(sample_rate)
                end = min(i + len(kick), samples)
                audio[i:end] += kick[:end-i]
    
    elif pattern == "train":
        # Chug-chug pattern
        for i in range(0, samples, beat_samples // 2):
            if i + int(0.05 * sample_rate) < samples:
                # Generate mechanical chug
                chug = generate_mechanical_chug(sample_rate)
                end = min(i + len(chug), samples)
                audio[i:end] += chug[:end-i] * 0.5
    
    return audio * 0.8


def generate_kick(sample_rate: int = 22050) -> np.ndarray:
    """Generate a kick drum sound."""
    duration = 0.3
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Frequency sweep from high to low
    freq = 120 * np.exp(-t * 15)
    kick = np.sin(2 * np.pi * freq * t)
    # Envelope
    envelope = np.exp(-t * 10)
    return (kick * envelope * 0.8).astype(np.float32)


def generate_mechanical_chug(sample_rate: int = 22050) -> np.ndarray:
    """Generate a mechanical chugging sound."""
    duration = 0.2
    samples = int(sample_rate * duration)
    # Filtered noise burst
    noise = np.random.randn(samples)
    # Lowpass filter effect
    filtered = np.convolve(noise, np.ones(10)/10, mode='same')
    envelope = np.exp(-np.linspace(0, 5, samples))
    return (filtered * envelope * 0.5).astype(np.float32)


def generate_piano_note(
    frequency: float = 440.0,
    duration: float = 2.0,
    sample_rate: int = 22050
) -> np.ndarray:
    """Generate a piano-like tone using multiple sines with envelope."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Fundamental + harmonics
    wave = np.sin(2 * np.pi * frequency * t)
    wave += 0.5 * np.sin(2 * np.pi * frequency * 2 * t)
    wave += 0.25 * np.sin(2 * np.pi * frequency * 3 * t)
    wave += 0.125 * np.sin(2 * np.pi * frequency * 4 * t)
    
    # Piano envelope (sharp attack, exponential decay)
    envelope = np.exp(-t * 2)
    envelope[:int(0.01 * sample_rate)] = 1.0
    
    return (wave * envelope * 0.3).astype(np.float32)


def generate_flute_note(
    frequency: float = 440.0,
    duration: float = 2.0,
    sample_rate: int = 22050
) -> np.ndarray:
    """Generate a flute-like tone."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Sine with some breath noise
    wave = np.sin(2 * np.pi * frequency * t)
    # Add breathiness
    breath = np.random.randn(len(t)) * 0.1
    # Filter breath to be high frequency
    breath = np.convolve(breath, np.ones(5)/5, mode='same')
    
    # Soft envelope
    envelope = np.ones_like(t)
    attack = int(0.1 * sample_rate)
    release = int(0.3 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    
    return ((wave + breath) * envelope * 0.4).astype(np.float32)


def generate_bowed_string(
    frequency: float = 440.0,
    duration: float = 2.0,
    sample_rate: int = 22050
) -> np.ndarray:
    """Generate a violin/cello-like bowed string sound."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Saw-like wave with vibrato
    vibrato = 1 + 0.02 * np.sin(2 * np.pi * 5 * t)  # 5 Hz vibrato
    phase = 2 * np.pi * frequency * np.cumsum(vibrato) / sample_rate
    wave = np.sin(phase)
    
    # Add some harmonics
    wave += 0.5 * np.sin(2 * phase)
    wave += 0.25 * np.sin(3 * phase)
    
    # Slow attack, sustain, release
    envelope = np.ones_like(t)
    attack = int(0.3 * sample_rate)
    release = int(0.5 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    
    return (wave * envelope * 0.35).astype(np.float32)


def generate_gong(
    duration: float = 4.0,
    sample_rate: int = 22050
) -> np.ndarray:
    """Generate a gong-like metallic sound."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Multiple inharmonic frequencies
    freqs = [100, 117, 154, 200, 245, 300]
    wave = np.zeros_like(t)
    for f in freqs:
        wave += np.sin(2 * np.pi * f * t) * np.exp(-t * 0.5)
    
    # Add metallic ring
    ring = np.random.randn(len(t)) * 0.05
    ring = np.convolve(ring, np.ones(20)/20, mode='same')
    
    return ((wave + ring) * 0.3).astype(np.float32)


def generate_thunder(
    duration: float = 3.0,
    sample_rate: int = 22050
) -> np.ndarray:
    """Generate thunder/rumble sound."""
    # Brown noise with heavy filtering
    samples = int(sample_rate * duration)
    white = np.random.randn(samples)
    
    # Create brown noise
    fft_vals = fft(white)
    freqs = np.fft.fftfreq(samples)
    freqs[0] = 1.0
    brown_filter = 1 / np.abs(freqs)
    brown_filter[0] = 0
    noise = np.real(ifft(fft_vals * brown_filter))
    
    # Normalize
    noise = noise / (np.abs(noise).max() + 1e-8)
    
    # Apply envelope with multiple rumbles
    envelope = np.zeros_like(noise)
    for i in range(0, samples, int(0.5 * sample_rate)):
        attack = int(0.1 * sample_rate)
        release = int(0.4 * sample_rate)
        if i + attack + release < samples:
            envelope[i:i+attack] = np.linspace(0, 1, attack)
            envelope[i+attack:i+attack+release] = np.linspace(1, 0, release)
    
    return (noise * envelope * 0.5).astype(np.float32)


def generate_ocean(
    duration: float = 4.0,
    sample_rate: int = 22050
) -> np.ndarray:
    """Generate ocean waves sound."""
    samples = int(sample_rate * duration)
    
    # Pink noise
    white = np.random.randn(samples)
    fft_vals = fft(white)
    freqs = np.fft.fftfreq(samples)
    freqs[0] = 1.0
    pink_filter = 1 / np.sqrt(np.abs(freqs))
    pink_filter[0] = 0
    noise = np.real(ifft(fft_vals * pink_filter))
    
    # Normalize
    noise = noise / (np.abs(noise).max() + 1e-8)
    
    # Modulate amplitude for wave effect
    t = np.linspace(0, duration, samples, False)
    wave_mod = (np.sin(2 * np.pi * 0.2 * t) + 1) / 2  # Slow wave
    
    return (noise * wave_mod * 0.4).astype(np.float32)


def generate_birds(
    duration: float = 3.0,
    sample_rate: int = 22050
) -> np.ndarray:
    """Generate bird chirps."""
    samples = int(sample_rate * duration)
    audio = np.zeros(samples, dtype=np.float32)
    
    # Add random chirps
    for _ in range(10):
        start = random.randint(0, samples - int(0.5 * sample_rate))
        chirp_duration = random.uniform(0.1, 0.3)
        freq = random.uniform(2000, 8000)
        
        t = np.linspace(0, chirp_duration, int(sample_rate * chirp_duration), False)
        # Frequency sweep up
        sweep = freq + 1000 * t
        chirp = np.sin(2 * np.pi * sweep * t)
        envelope = np.exp(-t * 10)
        
        end = min(start + len(chirp), samples)
        audio[start:end] += chirp[:end-start] * envelope[:end-start] * 0.3
    
    return audio


def generate_wind(
    duration: float = 4.0,
    sample_rate: int = 22050
) -> np.ndarray:
    """Generate wind sound."""
    samples = int(sample_rate * duration)
    
    # Filtered noise
    white = np.random.randn(samples)
    fft_vals = fft(white)
    freqs = np.fft.fftfreq(samples)
    freqs[0] = 1.0
    
    # Bandpass filter effect
    filter_mask = (np.abs(freqs) > 0.01) & (np.abs(freqs) < 0.1)
    fft_vals *= filter_mask
    
    noise = np.real(ifft(fft_vals))
    
    # Modulate for gusts
    t = np.linspace(0, duration, samples, False)
    gusts = np.sin(2 * np.pi * 0.3 * t) * np.sin(2 * np.pi * 0.07 * t)
    gusts = (gusts + 1) / 2
    
    return (noise * gusts * 0.4).astype(np.float32)


def generate_sound_by_id(sound_id: str, duration: float = 2.0) -> np.ndarray:
    """Generate a sound based on its ID.
    
    This is the main entry point - maps sound IDs to synthesis functions.
    """
    sr = 22050
    
    # Mechanical sounds
    if sound_id == "boat_motor":
        return generate_rhythm(bpm=60, duration=duration, pattern="train")
    elif sound_id == "helicopter":
        # Low rhythmic pulse
        return generate_rhythm(bpm=300, duration=duration, pattern="train")
    elif sound_id == "train":
        return generate_rhythm(bpm=90, duration=duration, pattern="train")
    elif sound_id in ["typewriter", "clock_ticking"]:
        return generate_rhythm(bpm=120, duration=duration, pattern="four_on_floor")
    
    # Instrument sounds
    elif sound_id == "piano":
        return generate_piano_note(261.63, duration, sr)  # Middle C
    elif sound_id == "violin":
        return generate_bowed_string(440.0, duration, sr)
    elif sound_id == "cello":
        return generate_bowed_string(130.81, duration, sr)  # Low C
    elif sound_id == "flute":
        return generate_flute_note(523.25, duration, sr)  # High C
    elif sound_id == "saxophone":
        # Saw with breath
        return generate_saw_wave(220, duration, sr, 0.3)
    elif sound_id == "trumpet":
        return generate_square_wave(349.23, duration, sr, 0.3)
    
    # Synthetic sounds
    elif sound_id == "saw_wave":
        return generate_saw_wave(440, duration, sr)
    elif sound_id == "square_wave":
        return generate_square_wave(440, duration, sr)
    elif sound_id == "sine_wave":
        return generate_sine_wave(440, duration, sr)
    elif sound_id == "synth_pad":
        # Complex chord
        t = np.linspace(0, duration, int(sr * duration), False)
        wave = np.sin(2 * np.pi * 220 * t)
        wave += 0.5 * np.sin(2 * np.pi * 277.18 * t)  # C# major chord
        wave += 0.5 * np.sin(2 * np.pi * 329.63 * t)
        envelope = np.exp(-t * 0.5)
        return (wave * envelope * 0.3).astype(np.float32)
    
    # Percussion sounds
    elif sound_id == "drums":
        return generate_rhythm(bpm=120, duration=duration, pattern="four_on_floor")
    elif sound_id in ["kick_drum"]:
        return generate_kick(sr)
    elif sound_id in ["bongo_drums", "djembe", "congas"]:
        return generate_rhythm(bpm=100, duration=duration, pattern="four_on_floor")
    elif sound_id == "gong":
        return generate_gong(duration, sr)
    elif sound_id == "cymbal_crash":
        return generate_noise(duration, sr, "white", 0.3)
    
    # Nature sounds
    elif sound_id == "ocean_waves":
        return generate_ocean(duration, sr)
    elif sound_id == "thunder":
        return generate_thunder(duration, sr)
    elif sound_id == "rain":
        return generate_noise(duration, sr, "pink", 0.3)
    elif sound_id == "wind":
        return generate_wind(duration, sr)
    elif sound_id == "birds":
        return generate_birds(duration, sr)
    elif sound_id in ["whale_song"]:
        # Low frequency wails
        t = np.linspace(0, duration, int(sr * duration), False)
        freq = 100 + 50 * np.sin(2 * np.pi * 0.5 * t)
        wave = np.sin(2 * np.pi * freq * t)
        return (wave * 0.5).astype(np.float32)
    
    # Vocal sounds
    elif sound_id == "choir_aah":
        t = np.linspace(0, duration, int(sr * duration), False)
        # Major chord
        wave = np.sin(2 * np.pi * 261.63 * t)
        wave += np.sin(2 * np.pi * 329.63 * t)
        wave += np.sin(2 * np.pi * 392.00 * t)
        envelope = np.ones_like(t)
        envelope[:int(0.5*sr)] = np.linspace(0, 1, int(0.5*sr))
        envelope[-int(0.5*sr):] = np.linspace(1, 0, int(0.5*sr))
        return (wave * envelope * 0.2).astype(np.float32)
    
    # Urban sounds
    elif sound_id == "traffic":
        return generate_noise(duration, sr, "pink", 0.4)
    elif sound_id == "subway_train":
        return generate_rhythm(bpm=70, duration=duration, pattern="train")
    
    # FX sounds
    elif sound_id == "vinyl_scratch":
        return generate_noise(duration, sr, "white", 0.3)
    elif sound_id == "radio_static":
        return generate_noise(duration, sr, "white", 0.3)
    elif sound_id == "explosion":
        return generate_thunder(min(duration, 2.0), sr)
    elif sound_id == "heart_beat":
        return generate_rhythm(bpm=60, duration=duration, pattern="four_on_floor")
    elif sound_id == "laser_zap":
        t = np.linspace(0, duration, int(sr * duration), False)
        freq = 2000 * np.exp(-t * 5)
        return (np.sin(2 * np.pi * freq * t) * np.exp(-t * 3) * 0.5).astype(np.float32)
    
    # Default: generate noise
    else:
        return generate_noise(duration, sr, "pink", 0.3)
