"""Input handling for dual audio sources.

Supports both file uploads and library selection as input sources,
with validation, preprocessing, and format conversion.
"""

from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO
import numpy as np
import soundfile as sf

from .sound_library import SoundLibrary, get_library
from .utils_audio import to_mono, resample_audio, normalize_wave


class InputSourceType(Enum):
    """Type of audio input source."""
    UPLOAD = "upload"
    LIBRARY = "library"


@dataclass
class AudioSource:
    """Represents an audio input source."""
    source_type: InputSourceType
    audio: np.ndarray
    sample_rate: int
    name: str
    metadata: dict | None = None
    
    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return len(self.audio) / self.sample_rate


class InputHandler:
    """Handles loading and validation of audio from various sources."""
    
    # Supported formats
    SUPPORTED_FORMATS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
    
    # Limits
    MAX_FILE_SIZE_MB = 50
    MAX_DURATION_SEC = 300  # 5 minutes
    TARGET_SAMPLE_RATE = 22050
    
    def __init__(self, library: SoundLibrary | None = None):
        self.library = library or get_library()
        self._temp_files: list[Path] = []
    
    def from_upload(
        self,
        file_data: bytes | BinaryIO,
        filename: str = "upload",
        original_sample_rate: int | None = None
    ) -> AudioSource:
        """Load audio from uploaded file data.
        
        Args:
            file_data: Raw file bytes or file-like object
            filename: Original filename for extension detection
            original_sample_rate: Optional hint for sample rate
            
        Returns:
            AudioSource with loaded audio
            
        Raises:
            ValueError: If file format not supported or invalid
        """
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {ext}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        # Read bytes
        if isinstance(file_data, bytes):
            data = file_data
        else:
            data = file_data.read()
        
        # Check size
        size_mb = len(data) / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"File too large: {size_mb:.1f}MB (max {self.MAX_FILE_SIZE_MB}MB)"
            )
        
        # Load with soundfile
        try:
            audio, sr = sf.read(io.BytesIO(data), always_2d=False)
        except Exception as e:
            raise ValueError(f"Failed to load audio: {e}")
        
        # Convert to mono
        audio = to_mono(audio)
        
        # Check duration
        duration = len(audio) / sr
        if duration > self.MAX_DURATION_SEC:
            raise ValueError(
                f"Audio too long: {duration:.1f}s (max {self.MAX_DURATION_SEC}s)"
            )
        
        # Resample if needed
        if sr != self.TARGET_SAMPLE_RATE:
            audio = resample_audio(audio, sr, self.TARGET_SAMPLE_RATE)
            sr = self.TARGET_SAMPLE_RATE
        
        # Normalize
        audio = normalize_wave(audio)
        
        return AudioSource(
            source_type=InputSourceType.UPLOAD,
            audio=audio,
            sample_rate=sr,
            name=Path(filename).stem,
            metadata={"original_filename": filename, "size_mb": size_mb}
        )
    
    def from_library(
        self,
        sound_id: str,
        max_duration: float | None = None
    ) -> AudioSource:
        """Load audio from the sound library.
        
        Args:
            sound_id: Library sound identifier
            max_duration: Optional max duration to load (truncates if longer)
            
        Returns:
            AudioSource with loaded audio
            
        Raises:
            KeyError: If sound not found in library
        """
        meta = self.library.get_sound(sound_id)
        if meta is None:
            raise KeyError(f"Sound not found in library: {sound_id}")
        
        # Load audio
        audio = self.library.load_audio(sound_id, self.TARGET_SAMPLE_RATE)
        
        # Truncate if needed
        if max_duration is not None:
            max_samples = int(max_duration * self.TARGET_SAMPLE_RATE)
            audio = audio[:max_samples]
        
        return AudioSource(
            source_type=InputSourceType.LIBRARY,
            audio=audio,
            sample_rate=self.TARGET_SAMPLE_RATE,
            name=meta.name,
            metadata={
                "sound_id": sound_id,
                "category": meta.category,
                "tags": meta.tags,
                "description": meta.description
            }
        )
    
    def from_path(
        self,
        path: Path | str,
        name: str | None = None
    ) -> AudioSource:
        """Load audio from a file path.
        
        Args:
            path: Path to audio file
            name: Optional display name
            
        Returns:
            AudioSource with loaded audio
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        # Load
        audio, sr = sf.read(path, always_2d=False)
        audio = to_mono(audio)
        
        # Resample
        if sr != self.TARGET_SAMPLE_RATE:
            audio = resample_audio(audio, sr, self.TARGET_SAMPLE_RATE)
            sr = self.TARGET_SAMPLE_RATE
        
        audio = normalize_wave(audio)
        
        return AudioSource(
            source_type=InputSourceType.UPLOAD,
            audio=audio,
            sample_rate=sr,
            name=name or path.stem,
            metadata={"path": str(path)}
        )
    
    def prepare_pair(
        self,
        source: AudioSource | tuple[str, bytes | BinaryIO],
        modulator: AudioSource | tuple[str, bytes | BinaryIO] | str,
    ) -> tuple[AudioSource, AudioSource]:
        """Prepare a pair of audio sources for morphing.
        
        Args:
            source: Source audio (AudioSource or (filename, data) tuple)
            modulator: Modulator audio (AudioSource, (filename, data) tuple, or library ID)
            
        Returns:
            Tuple of (source, modulator) AudioSources
        """
        # Process source
        if isinstance(source, AudioSource):
            src = source
        else:
            filename, data = source
            src = self.from_upload(data, filename)
        
        # Process modulator
        if isinstance(modulator, AudioSource):
            mod = modulator
        elif isinstance(modulator, str):
            # Library ID
            mod = self.from_library(modulator, max_duration=src.duration)
        else:
            filename, data = modulator
            mod = self.from_upload(data, filename)
        
        return src, mod
    
    def cleanup(self) -> None:
        """Clean up any temporary files."""
        for path in self._temp_files:
            if path.exists():
                path.unlink()
        self._temp_files.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.cleanup()


def load_audio_pair(
    source_input: dict,
    modulator_input: dict,
    library: SoundLibrary | None = None
) -> tuple[AudioSource, AudioSource]:
    """Convenience function to load an audio pair from dict specifications.
    
    Args:
        source_input: Dict with 'type' ('upload'|'library') and 'data' or 'id'
        modulator_input: Same format as source_input
        library: Optional SoundLibrary instance
        
    Returns:
        Tuple of (source, modulator) AudioSources
        
    Example:
        source = {"type": "upload", "data": file_bytes, "filename": "piano.wav"}
        modulator = {"type": "library", "id": "boat_motor"}
        src, mod = load_audio_pair(source, modulator)
    """
    handler = InputHandler(library)
    
    # Load source
    if source_input.get("type") == "library":
        source = handler.from_library(source_input["id"])
    else:
        source = handler.from_upload(
            source_input["data"],
            source_input.get("filename", "upload")
        )
    
    # Load modulator
    if modulator_input.get("type") == "library":
        modulator = handler.from_library(modulator_input["id"])
    else:
        modulator = handler.from_upload(
            modulator_input["data"],
            modulator_input.get("filename", "upload")
        )
    
    return source, modulator
