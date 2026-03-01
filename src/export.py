"""Audio export functionality for multiple formats.

Supports WAV, MP3, FLAC, and OGG output formats with quality settings.
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


class ExportFormat(Enum):
    """Supported export formats."""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"


@dataclass
class ExportOptions:
    """Options for audio export.
    
    Attributes:
        format: Export format
        sample_rate: Output sample rate
        bitrate: Bitrate for lossy formats (MP3, OGG) in kbps
        quality: Quality level (0-10, used for some formats)
        normalize: Whether to normalize output
        metadata: Optional metadata tags
    """
    format: ExportFormat = ExportFormat.WAV
    sample_rate: int = 22050
    bitrate: int = 192  # kbps
    quality: int = 5  # 0-10
    normalize: bool = True
    metadata: dict | None = None
    
    @property
    def extension(self) -> str:
        return self.format.value
    
    @property
    def mime_type(self) -> str:
        mime_types = {
            ExportFormat.WAV: "audio/wav",
            ExportFormat.MP3: "audio/mpeg",
            ExportFormat.FLAC: "audio/flac",
            ExportFormat.OGG: "audio/ogg",
        }
        return mime_types.get(self.format, "application/octet-stream")


def normalize_audio(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """Normalize audio to target peak level.
    
    Args:
        audio: Input audio array
        target_peak: Target peak amplitude (0-1)
        
    Returns:
        Normalized audio
    """
    peak = np.abs(audio).max()
    if peak < 1e-8:
        return audio.astype(np.float32)
    return (audio / peak * target_peak).astype(np.float32)


def export_audio(
    audio: np.ndarray,
    options: ExportOptions | None = None,
    output_path: Path | str | None = None
) -> bytes | Path:
    """Export audio to various formats.
    
    Args:
        audio: Audio data as float32 array
        options: Export options (uses defaults if None)
        output_path: Optional path to save to file (returns bytes if None)
        
    Returns:
        Audio bytes or Path to saved file
    """
    if options is None:
        options = ExportOptions()
    
    # Normalize if requested
    if options.normalize:
        audio = normalize_audio(audio)
    
    # Ensure float32
    audio = audio.astype(np.float32)
    
    # Clip to [-1, 1]
    audio = np.clip(audio, -1.0, 1.0)
    
    # Export based on format
    if options.format == ExportFormat.WAV:
        return _export_wav(audio, options, output_path)
    elif options.format == ExportFormat.FLAC:
        return _export_flac(audio, options, output_path)
    elif options.format == ExportFormat.MP3:
        return _export_mp3(audio, options, output_path)
    elif options.format == ExportFormat.OGG:
        return _export_ogg(audio, options, output_path)
    else:
        raise ValueError(f"Unsupported format: {options.format}")


def _export_wav(
    audio: np.ndarray,
    options: ExportOptions,
    output_path: Path | str | None = None
) -> bytes | Path:
    """Export to WAV format."""
    if output_path is not None:
        sf.write(output_path, audio, options.sample_rate, format="WAV")
        return Path(output_path)
    else:
        buffer = io.BytesIO()
        sf.write(buffer, audio, options.sample_rate, format="WAV")
        return buffer.getvalue()


def _export_flac(
    audio: np.ndarray,
    options: ExportOptions,
    output_path: Path | str | None = None
) -> bytes | Path:
    """Export to FLAC format."""
    if output_path is not None:
        sf.write(output_path, audio, options.sample_rate, format="FLAC")
        return Path(output_path)
    else:
        buffer = io.BytesIO()
        sf.write(buffer, audio, options.sample_rate, format="FLAC")
        return buffer.getvalue()


def _export_mp3(
    audio: np.ndarray,
    options: ExportOptions,
    output_path: Path | str | None = None
) -> bytes | Path:
    """Export to MP3 format using external encoder if available."""
    # soundfile doesn't support MP3 directly, use pydub if available
    try:
        from pydub import AudioSegment
        
        # First write to temporary WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            sf.write(tmp_wav.name, audio, options.sample_rate)
            tmp_wav_path = tmp_wav.name
        
        # Convert to MP3
        segment = AudioSegment.from_wav(tmp_wav_path)
        
        # Set bitrate
        bitrate_str = f"{options.bitrate}k"
        
        if output_path is not None:
            segment.export(output_path, format="mp3", bitrate=bitrate_str)
            Path(tmp_wav_path).unlink()
            return Path(output_path)
        else:
            buffer = io.BytesIO()
            segment.export(buffer, format="mp3", bitrate=bitrate_str)
            Path(tmp_wav_path).unlink()
            return buffer.getvalue()
            
    except ImportError:
        # Fallback to WAV if pydub not available
        import warnings
        warnings.warn("pydub not installed, falling back to WAV format")
        return _export_wav(audio, options, output_path)


def _export_ogg(
    audio: np.ndarray,
    options: ExportOptions,
    output_path: Path | str | None = None
) -> bytes | Path:
    """Export to OGG Vorbis format."""
    if output_path is not None:
        sf.write(output_path, audio, options.sample_rate, format="OGG")
        return Path(output_path)
    else:
        buffer = io.BytesIO()
        sf.write(buffer, audio, options.sample_rate, format="OGG")
        return buffer.getvalue()


def generate_filename(
    prefix: str = "morphed",
    options: ExportOptions | None = None
) -> str:
    """Generate a filename for exported audio.
    
    Args:
        prefix: Filename prefix
        options: Export options (determines extension)
        
    Returns:
        Generated filename
    """
    from datetime import datetime
    
    options = options or ExportOptions()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{options.extension}"


class AudioExporter:
    """High-level audio exporter with file management."""
    
    def __init__(self, output_dir: Path | str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._exports: list[Path] = []
    
    def export(
        self,
        audio: np.ndarray,
        filename: str | None = None,
        options: ExportOptions | None = None,
        sample_rate: int = 22050
    ) -> Path:
        """Export audio to a file.
        
        Args:
            audio: Audio data
            filename: Output filename (auto-generated if None)
            options: Export options
            sample_rate: Audio sample rate
            
        Returns:
            Path to exported file
        """
        options = options or ExportOptions()
        options.sample_rate = sample_rate
        
        if filename is None:
            filename = generate_filename("morphed", options)
        
        output_path = self.output_dir / filename
        export_audio(audio, options, output_path)
        self._exports.append(output_path)
        
        return output_path
    
    def export_bytes(
        self,
        audio: np.ndarray,
        options: ExportOptions | None = None,
        sample_rate: int = 22050
    ) -> bytes:
        """Export audio to bytes.
        
        Args:
            audio: Audio data
            options: Export options
            sample_rate: Audio sample rate
            
        Returns:
            Audio bytes
        """
        options = options or ExportOptions()
        options.sample_rate = sample_rate
        return export_audio(audio, options)
    
    def get_recent_exports(self, limit: int = 10) -> list[Path]:
        """Get list of recently exported files."""
        return sorted(self._exports, key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    
    def cleanup_old_exports(self, max_age_hours: float = 24.0) -> int:
        """Remove old export files.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of files removed
        """
        from time import time
        
        max_age_sec = max_age_hours * 3600
        current_time = time()
        removed = 0
        
        for path in self.output_dir.glob("*"):
            if path.is_file():
                age = current_time - path.stat().st_mtime
                if age > max_age_sec:
                    path.unlink()
                    removed += 1
        
        return removed


def get_export_options_for_format(
    format_str: str,
    quality: str = "high"
) -> ExportOptions:
    """Get export options for a format string.
    
    Args:
        format_str: Format name (wav, mp3, flac, ogg)
        quality: Quality preset (low, medium, high)
        
    Returns:
        ExportOptions configured for the format
    """
    fmt = ExportFormat(format_str.lower())
    
    quality_settings = {
        "low": {"bitrate": 96, "quality": 2},
        "medium": {"bitrate": 128, "quality": 5},
        "high": {"bitrate": 192, "quality": 8},
        "lossless": {"bitrate": 320, "quality": 10},
    }
    
    settings = quality_settings.get(quality, quality_settings["high"])
    
    return ExportOptions(
        format=fmt,
        bitrate=settings["bitrate"],
        quality=settings["quality"],
        normalize=True
    )
