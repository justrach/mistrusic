"""Tests for the export module."""

import io
import pytest
import numpy as np
import soundfile as sf
from pathlib import Path

from src.export import (
    ExportFormat,
    ExportOptions,
    normalize_audio,
    export_audio,
    generate_filename,
    AudioExporter,
    get_export_options_for_format,
)


class TestExportFormat:
    """Test ExportFormat enum."""
    
    def test_format_values(self):
        """Test format enum values."""
        assert ExportFormat.WAV.value == "wav"
        assert ExportFormat.MP3.value == "mp3"
        assert ExportFormat.FLAC.value == "flac"
        assert ExportFormat.OGG.value == "ogg"


class TestExportOptions:
    """Test ExportOptions dataclass."""
    
    def test_default_values(self):
        """Test default option values."""
        opts = ExportOptions()
        
        assert opts.format == ExportFormat.WAV
        assert opts.sample_rate == 22050
        assert opts.bitrate == 192
        assert opts.quality == 5
        assert opts.normalize is True
        assert opts.metadata is None
    
    def test_extension_property(self):
        """Test extension property."""
        opts = ExportOptions(format=ExportFormat.MP3)
        assert opts.extension == "mp3"
        
        opts = ExportOptions(format=ExportFormat.FLAC)
        assert opts.extension == "flac"
    
    def test_mime_type(self):
        """Test MIME type property."""
        opts = ExportOptions(format=ExportFormat.WAV)
        assert opts.mime_type == "audio/wav"
        
        opts = ExportOptions(format=ExportFormat.MP3)
        assert opts.mime_type == "audio/mpeg"


class TestNormalizeAudio:
    """Test audio normalization."""
    
    def test_normalization(self):
        """Test basic normalization."""
        audio = np.array([0.5, 1.0, 0.5], dtype=np.float32)
        normalized = normalize_audio(audio, target_peak=0.9)
        
        assert np.abs(normalized).max() == pytest.approx(0.9, abs=0.01)
    
    def test_silence_handling(self):
        """Test normalizing silent audio."""
        audio = np.zeros(100, dtype=np.float32)
        normalized = normalize_audio(audio)
        
        assert np.all(normalized == 0)
    
    def test_already_normalized(self):
        """Test audio already at target peak."""
        audio = np.array([0.9, -0.9, 0.5], dtype=np.float32)
        normalized = normalize_audio(audio, target_peak=0.9)
        
        assert np.array_equal(audio, normalized)


class TestExportAudio:
    """Test export_audio function."""
    
    def test_export_wav_bytes(self):
        """Test exporting WAV to bytes."""
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        opts = ExportOptions(format=ExportFormat.WAV)
        
        result = export_audio(audio, opts)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        # Check WAV header
        assert result[:4] == b"RIFF"
    
    def test_export_wav_file(self, tmp_path):
        """Test exporting WAV to file."""
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        opts = ExportOptions(format=ExportFormat.WAV)
        output_path = tmp_path / "output.wav"
        
        result = export_audio(audio, opts, output_path)
        
        assert isinstance(result, Path)
        assert result.exists()
        assert result.suffix == ".wav"
    
    def test_export_flac(self):
        """Test exporting FLAC."""
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        opts = ExportOptions(format=ExportFormat.FLAC)
        
        result = export_audio(audio, opts)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_export_ogg(self):
        """Test exporting OGG."""
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        opts = ExportOptions(format=ExportFormat.OGG)
        
        result = export_audio(audio, opts)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_export_with_normalization(self):
        """Test export with normalization."""
        audio = np.array([2.0, -2.0, 1.0], dtype=np.float32)  # Over 1.0
        opts = ExportOptions(normalize=True)
        
        result = export_audio(audio, opts)
        
        # Should not raise error, audio should be normalized/clipped
        assert isinstance(result, bytes)
    
    def test_export_without_normalization(self):
        """Test export without normalization."""
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        opts = ExportOptions(normalize=False)
        
        result = export_audio(audio, opts)
        
        assert isinstance(result, bytes)


class TestGenerateFilename:
    """Test filename generation."""
    
    def test_default_prefix(self):
        """Test default prefix."""
        opts = ExportOptions(format=ExportFormat.WAV)
        filename = generate_filename(options=opts)
        
        assert filename.startswith("morphed_")
        assert filename.endswith(".wav")
        # Should have timestamp
        assert len(filename) > 20
    
    def test_custom_prefix(self):
        """Test custom prefix."""
        opts = ExportOptions(format=ExportFormat.MP3)
        filename = generate_filename(prefix="custom", options=opts)
        
        assert filename.startswith("custom_")
        assert filename.endswith(".mp3")
    
    def test_unique_filenames(self):
        """Test that generated filenames are unique."""
        import time
        
        opts = ExportOptions()
        filename1 = generate_filename(options=opts)
        time.sleep(0.01)  # Small delay to ensure different timestamp
        filename2 = generate_filename(options=opts)
        
        assert filename1 != filename2


class TestAudioExporter:
    """Test AudioExporter class."""
    
    def test_export_to_file(self, tmp_path):
        """Test exporting to file."""
        exporter = AudioExporter(tmp_path)
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        opts = ExportOptions(format=ExportFormat.WAV)
        
        result_path = exporter.export(audio, "test.wav", opts, sample_rate=22050)
        
        assert result_path.exists()
        assert result_path.suffix == ".wav"
        assert result_path in exporter._exports
    
    def test_export_auto_filename(self, tmp_path):
        """Test export with auto-generated filename."""
        exporter = AudioExporter(tmp_path)
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        
        result_path = exporter.export(audio, sample_rate=22050)
        
        assert result_path.exists()
        assert "morphed" in result_path.name
    
    def test_export_bytes(self):
        """Test export to bytes."""
        exporter = AudioExporter()
        audio = np.random.randn(22050).astype(np.float32) * 0.5
        opts = ExportOptions(format=ExportFormat.WAV)
        
        result = exporter.export_bytes(audio, opts, sample_rate=22050)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_get_recent_exports(self, tmp_path):
        """Test getting recent exports."""
        exporter = AudioExporter(tmp_path)
        audio = np.random.randn(22050).astype(np.float32) * 0.3
        
        # Create a few exports
        path1 = exporter.export(audio, "file1.wav", sample_rate=22050)
        path2 = exporter.export(audio, "file2.wav", sample_rate=22050)
        path3 = exporter.export(audio, "file3.wav", sample_rate=22050)
        
        recent = exporter.get_recent_exports(limit=2)
        
        assert len(recent) == 2
        assert recent[0] == path3  # Most recent first
    
    def test_cleanup_old_exports(self, tmp_path):
        """Test cleaning up old exports."""
        import time
        
        exporter = AudioExporter(tmp_path)
        audio = np.random.randn(22050).astype(np.float32) * 0.3
        
        # Create an export
        exporter.export(audio, "old.wav", sample_rate=22050)
        
        # Cleanup with very short max age (should remove nothing, file is new)
        removed = exporter.cleanup_old_exports(max_age_hours=0)
        
        # The file was just created, so it should not be removed
        assert removed == 0


class TestGetExportOptions:
    """Test get_export_options_for_format function."""
    
    def test_wav_options(self):
        """Test WAV options."""
        opts = get_export_options_for_format("wav", quality="high")
        
        assert opts.format == ExportFormat.WAV
        assert opts.normalize is True
    
    def test_mp3_quality_settings(self):
        """Test MP3 quality presets."""
        low = get_export_options_for_format("mp3", quality="low")
        high = get_export_options_for_format("mp3", quality="high")
        
        assert low.bitrate < high.bitrate
        assert low.quality < high.quality
    
    def test_flac_lossless(self):
        """Test FLAC options."""
        opts = get_export_options_for_format("flac", quality="lossless")
        
        assert opts.format == ExportFormat.FLAC
        assert opts.quality == 10


class TestEdgeCases:
    """Test edge cases."""
    
    def test_very_short_audio(self):
        """Test exporting very short audio."""
        audio = np.array([0.5], dtype=np.float32)
        opts = ExportOptions()
        
        result = export_audio(audio, opts)
        
        assert isinstance(result, bytes)
    
    def test_silence_export(self):
        """Test exporting silence."""
        audio = np.zeros(22050, dtype=np.float32)
        opts = ExportOptions()
        
        result = export_audio(audio, opts)
        
        assert isinstance(result, bytes)
    
    def test_output_directory_creation(self, tmp_path):
        """Test creating output directory if not exists."""
        output_dir = tmp_path / "nested" / "dirs"
        exporter = AudioExporter(output_dir)
        
        assert output_dir.exists()
