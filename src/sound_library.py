"""Sound library/catalog system for curated audio samples.

Provides a browsable collection of sounds organized by category,
with metadata for each sound (duration, sample rate, tags, etc.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator
import numpy as np
import soundfile as sf

from .utils_audio import load_waveform, to_mono, resample_audio, normalize_wave


@dataclass
class SoundMetadata:
    """Metadata for a sound in the library."""
    id: str
    name: str
    description: str
    category: str
    path: str
    duration: float
    sample_rate: int
    tags: list[str]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> SoundMetadata:
        return cls(**d)


# Default curated sounds library
DEFAULT_LIBRARY = {
    "boat_motor": {
        "name": "Boat Motor",
        "description": "Rhythmic mechanical chugging with rich harmonic content",
        "category": "mechanical",
        "tags": ["rhythmic", "mechanical", "engine", "percussive"],
    },
    "piano": {
        "name": "Piano",
        "description": "Clean acoustic piano with rich harmonic overtones",
        "category": "instruments",
        "tags": ["melodic", "acoustic", "harmonic", "musical"],
    },
    "saw_wave": {
        "name": "Saw Wave",
        "description": "Bright, buzzy sawtooth wave synthesis",
        "category": "synthetic",
        "tags": ["buzzy", "bright", "electronic", "harmonic"],
    },
    "ocean_waves": {
        "name": "Ocean Waves",
        "description": "Gentle ocean waves with natural white noise characteristics",
        "category": "nature",
        "tags": ["ambient", "natural", "calm", "noise"],
    },
    "thunder": {
        "name": "Thunder",
        "description": "Deep rumbling thunder with low-frequency energy",
        "category": "nature",
        "tags": ["rumble", "deep", "impact", "low-freq"],
    },
    "birds": {
        "name": "Birds",
        "description": "Birdsong with melodic chirping patterns",
        "category": "nature",
        "tags": ["melodic", "natural", "light", "airy"],
    },
    "flute": {
        "name": "Flute",
        "description": "Breathy woodwind tone with soft attack",
        "category": "instruments",
        "tags": ["breathy", "woodwind", "soft", "airy"],
    },
    "violin": {
        "name": "Violin",
        "description": "String instrument with rich bow harmonics",
        "category": "instruments",
        "tags": ["string", "bowed", "expressive", "harmonic"],
    },
    "saxophone": {
        "name": "Saxophone",
        "description": "Brassy reed instrument with warm tone",
        "category": "instruments",
        "tags": ["brassy", "reed", "warm", "jazz"],
    },
    "synth_pad": {
        "name": "Synth Pad",
        "description": "Ethereal synthesizer pad with slow attack",
        "category": "synthetic",
        "tags": ["ambient", "electronic", "evolving", "smooth"],
    },
    "drums": {
        "name": "Drums",
        "description": "Acoustic drum kit with punchy transients",
        "category": "percussion",
        "tags": ["rhythmic", "percussive", "punchy", "transient"],
    },
    "rain": {
        "name": "Rain",
        "description": "Steady rainfall with textured white noise",
        "category": "nature",
        "tags": ["ambient", "natural", "texture", "noise"],
    },
    "wind": {
        "name": "Wind",
        "description": "Howling wind with spectral movement",
        "category": "nature",
        "tags": ["ambient", "natural", "moving", "spectral"],
    },
    "helicopter": {
        "name": "Helicopter",
        "description": "Rhythmic helicopter blades with pulsing character",
        "category": "mechanical",
        "tags": ["rhythmic", "mechanical", "pulsing", "heavy"],
    },
    "typewriter": {
        "name": "Typewriter",
        "description": "Mechanical typing with rhythmic percussive clicks",
        "category": "mechanical",
        "tags": ["rhythmic", "mechanical", "clicks", "percussive"],
    },
}


class SoundLibrary:
    """Manages a catalog of curated audio samples."""
    
    def __init__(self, library_dir: Path | str = "data/sound_library"):
        self.library_dir = Path(library_dir)
        self.index_file = self.library_dir / "index.json"
        self._index: dict[str, SoundMetadata] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load the library index from disk."""
        if self.index_file.exists():
            data = json.loads(self.index_file.read_text())
            self._index = {
                k: SoundMetadata.from_dict(v) 
                for k, v in data.get("sounds", {}).items()
            }
    
    def _save_index(self) -> None:
        """Save the library index to disk."""
        self.library_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "sounds": {k: v.to_dict() for k, v in self._index.items()},
            "categories": self.get_categories(),
        }
        self.index_file.write_text(json.dumps(data, indent=2))
    
    def add_sound(
        self,
        sound_id: str,
        audio_path: Path | str,
        name: str | None = None,
        description: str = "",
        category: str = "uncategorized",
        tags: list[str] | None = None,
        target_sr: int = 22050,
    ) -> SoundMetadata:
        """Add a sound to the library.
        
        Args:
            sound_id: Unique identifier for the sound
            audio_path: Path to the audio file
            name: Display name (defaults to sound_id)
            description: Description of the sound
            category: Category for grouping
            tags: List of searchable tags
            target_sr: Target sample rate for storage
            
        Returns:
            SoundMetadata for the added sound
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Load and normalize audio
        audio, sr = sf.read(audio_path, always_2d=False)
        audio = to_mono(audio)
        audio = resample_audio(audio, sr, target_sr)
        audio = normalize_wave(audio)
        
        # Save to library directory
        lib_path = self.library_dir / "audio" / f"{sound_id}.wav"
        lib_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(lib_path, audio, target_sr)
        
        # Create metadata
        duration = len(audio) / target_sr
        meta = SoundMetadata(
            id=sound_id,
            name=name or sound_id.replace("_", " ").title(),
            description=description,
            category=category,
            path=str(lib_path.relative_to(self.library_dir)),
            duration=duration,
            sample_rate=target_sr,
            tags=tags or [],
        )
        
        self._index[sound_id] = meta
        self._save_index()
        return meta
    
    def get_sound(self, sound_id: str) -> SoundMetadata | None:
        """Get metadata for a specific sound."""
        return self._index.get(sound_id)
    
    def load_audio(self, sound_id: str, target_sr: int | None = None) -> np.ndarray:
        """Load the audio data for a sound.
        
        Args:
            sound_id: The sound identifier
            target_sr: Optional target sample rate (defaults to stored rate)
            
        Returns:
            Audio array as float32
        """
        meta = self._index.get(sound_id)
        if meta is None:
            raise KeyError(f"Sound not found: {sound_id}")
        
        audio_path = self.library_dir / meta.path
        audio, sr = sf.read(audio_path, always_2d=False)
        audio = to_mono(audio)
        
        if target_sr is not None and target_sr != sr:
            audio = resample_audio(audio, sr, target_sr)
            sr = target_sr
        
        return audio.astype(np.float32)
    
    def list_sounds(
        self,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[SoundMetadata]:
        """List sounds with optional filtering.
        
        Args:
            category: Filter by category
            tag: Filter by tag
            
        Returns:
            List of matching SoundMetadata
        """
        results = list(self._index.values())
        
        if category:
            results = [s for s in results if s.category == category]
        
        if tag:
            results = [s for s in results if tag in s.tags]
        
        return results
    
    def get_categories(self) -> list[str]:
        """Get all unique categories in the library."""
        categories = set(s.category for s in self._index.values())
        return sorted(categories)
    
    def get_tags(self) -> list[str]:
        """Get all unique tags in the library."""
        tags = set()
        for s in self._index.values():
            tags.update(s.tags)
        return sorted(tags)
    
    def search(self, query: str) -> list[SoundMetadata]:
        """Search sounds by name, description, or tags.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching SoundMetadata
        """
        query = query.lower()
        results = []
        
        for s in self._index.values():
            if (query in s.name.lower() or 
                query in s.description.lower() or
                any(query in t.lower() for t in s.tags)):
                results.append(s)
        
        return results
    
    def remove_sound(self, sound_id: str) -> bool:
        """Remove a sound from the library.
        
        Args:
            sound_id: The sound to remove
            
        Returns:
            True if removed, False if not found
        """
        if sound_id not in self._index:
            return False
        
        meta = self._index.pop(sound_id)
        audio_path = self.library_dir / meta.path
        
        if audio_path.exists():
            audio_path.unlink()
        
        self._save_index()
        return True
    
    def __len__(self) -> int:
        return len(self._index)
    
    def __iter__(self) -> Iterator[SoundMetadata]:
        return iter(self._index.values())
    
    def __contains__(self, sound_id: str) -> bool:
        return sound_id in self._index


# Global library instance
_library: SoundLibrary | None = None


def get_library(library_dir: Path | str | None = None) -> SoundLibrary:
    """Get the global sound library instance.
    
    Args:
        library_dir: Optional directory path (uses default if not specified)
        
    Returns:
        SoundLibrary instance
    """
    global _library
    if _library is None or library_dir is not None:
        _library = SoundLibrary(library_dir or "data/sound_library")
    return _library


def init_default_library(library_dir: Path | str | None = None) -> SoundLibrary:
    """Initialize the library with default sounds.
    
    This creates placeholder entries for the default library.
    Actual audio files need to be added separately.
    
    Args:
        library_dir: Optional directory path
        
    Returns:
        Initialized SoundLibrary
    """
    lib = get_library(library_dir)
    
    for sound_id, info in DEFAULT_LIBRARY.items():
        if sound_id not in lib:
            # Create placeholder metadata
            # Note: This won't have audio until files are added
            meta = SoundMetadata(
                id=sound_id,
                name=info["name"],
                description=info["description"],
                category=info["category"],
                path=f"audio/{sound_id}.wav",
                duration=0.0,
                sample_rate=22050,
                tags=info["tags"],
            )
            lib._index[sound_id] = meta
    
    lib._save_index()
    return lib
