"""Tests for the input handler module."""

import io
import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.input_handler import (
    InputSourceType,
    AudioSource,
    InputHandler,
    load_audio_pair,
)
from src.sound_library import SoundLibrary, SoundMetadata


class TestAudioSource:
    """Test AudioSource dataclass."""
    
    def test_creation(self):
        """Test creating an AudioSource."""
        audio = np.random.randn(22050).astype(np.float32)
        source = AudioSource(
            source_type=InputSourceType.UPLOAD,
            audio=audio,
            sample_rate=22050,
            name="test.wav",
            metadata={"key": "value"},
        )
        
        assert source.source_type == InputSourceType.UPLOAD
        assert np.array_equal(source.audio, audio)
        assert source.sample_rate == 22050
        assert source.name == "test.wav"
        assert source.metadata["key"] == "value"
    
    def test_duration_property(self):
        """Test duration calculation."""
        audio = np.random.randn(44100).astype(np.float32)
        source = AudioSource(
            source_type=InputSourceType.UPLOAD,
            audio=audio,
            sample_rate=22050,
            name="test",
        )
        
        assert source.duration == 2.0  # 44100 / 22050


class TestInputHandler:
    """Test InputHandler class."""
    
    def test_supported_formats(self):
        """Test supported formats list."""
        handler = InputHandler()
        
        assert ".wav" in handler.SUPPORTED_FORMATS
        assert ".mp3" in handler.SUPPORTED_FORMATS
        assert ".flac" in handler.SUPPORTED_FORMATS


class TestFromUpload:
    """Test uploading files."""
    
    def test_upload_wav(self, tmp_path):
        """Test uploading a WAV file."""
        # Create test WAV file
        audio_path = tmp_path / "test.wav"
        test_audio = np.random.randn(22050).astype(np.float32) * 0.5
        sf.write(audio_path, test_audio, 22050)
        
        handler = InputHandler()
        
        with open(audio_path, "rb") as f:
            content = f.read()
        
        source = handler.from_upload(content, "test.wav")
        
        assert source.source_type == InputSourceType.UPLOAD
        assert source.name == "test"
        assert source.sample_rate == 22050
        assert len(source.audio) == 22050
        assert np.abs(source.audio).max() <= 1.0  # Normalized
    
    def test_upload_stereo_converts_to_mono(self, tmp_path):
        """Test stereo file is converted to mono."""
        audio_path = tmp_path / "stereo.wav"
        stereo = np.random.randn(22050, 2).astype(np.float32) * 0.3
        sf.write(audio_path, stereo, 22050)
        
        handler = InputHandler()
        
        with open(audio_path, "rb") as f:
            content = f.read()
        
        source = handler.from_upload(content, "stereo.wav")
        
        # Should be mono
        assert source.audio.ndim == 1
    
    def test_upload_resampling(self, tmp_path):
        """Test upload with different sample rate."""
        audio_path = tmp_path / "48k.wav"
        audio = np.random.randn(48000).astype(np.float32) * 0.3
        sf.write(audio_path, audio, 48000)
        
        handler = InputHandler()
        
        with open(audio_path, "rb") as f:
            content = f.read()
        
        source = handler.from_upload(content, "48k.wav")
        
        # Should be resampled to target rate
        assert source.sample_rate == 22050
    
    def test_unsupported_format(self):
        """Test unsupported file format."""
        handler = InputHandler()
        
        with pytest.raises(ValueError) as exc_info:
            handler.from_upload(b"data", "file.xyz")
        
        assert "Unsupported format" in str(exc_info.value)
    
    def test_file_size_limit(self):
        """Test file size limit."""
        handler = InputHandler()
        
        # Create data larger than max size
        large_data = b"x" * (handler.MAX_FILE_SIZE_MB * 1024 * 1024 + 1000)
        
        with pytest.raises(ValueError) as exc_info:
            handler.from_upload(large_data, "large.wav")
        
        assert "too large" in str(exc_info.value).lower()


class TestFromLibrary:
    """Test loading from library."""
    
    def test_from_library(self, tmp_path):
        """Test loading from sound library."""
        # Create a mock library
        lib = SoundLibrary(tmp_path)
        
        # Create a real audio file
        audio_path = tmp_path / "test_audio.wav"
        test_audio = np.random.randn(22050).astype(np.float32) * 0.5
        sf.write(audio_path, test_audio, 22050)
        
        # Add to library
        meta = SoundMetadata(
            id="test_sound",
            name="Test Sound",
            description="Desc",
            category="test",
            path=str(audio_path.relative_to(tmp_path)),
            duration=1.0,
            sample_rate=22050,
            tags=[],
        )
        lib._index["test_sound"] = meta
        
        handler = InputHandler(lib)
        source = handler.from_library("test_sound")
        
        assert source.source_type == InputSourceType.LIBRARY
        assert source.name == "Test Sound"
        assert len(source.audio) == 22050
    
    def test_library_sound_not_found(self):
        """Test loading non-existent library sound."""
        lib = SoundLibrary()
        handler = InputHandler(lib)
        
        with pytest.raises(KeyError):
            handler.from_library("nonexistent")
    
    def test_max_duration_truncation(self, tmp_path):
        """Test truncating long library sounds."""
        lib = SoundLibrary(tmp_path)
        
        # Create 5 second audio
        audio_path = tmp_path / "long.wav"
        long_audio = np.random.randn(110250).astype(np.float32) * 0.3  # 5 seconds at 22k
        sf.write(audio_path, long_audio, 22050)
        
        meta = SoundMetadata(
            id="long_sound",
            name="Long Sound",
            description="Desc",
            category="test",
            path=str(audio_path.relative_to(tmp_path)),
            duration=5.0,
            sample_rate=22050,
            tags=[],
        )
        lib._index["long_sound"] = meta
        
        handler = InputHandler(lib)
        
        # Load with 2 second max
        source = handler.from_library("long_sound", max_duration=2.0)
        
        assert abs(source.duration - 2.0) < 0.1


class TestFromPath:
    """Test loading from file path."""
    
    def test_from_path(self, tmp_path):
        """Test loading from a file path."""
        audio_path = tmp_path / "file.wav"
        audio = np.random.randn(22050).astype(np.float32) * 0.3
        sf.write(audio_path, audio, 22050)
        
        handler = InputHandler()
        source = handler.from_path(audio_path, "Custom Name")
        
        assert source.name == "Custom Name"
        assert source.source_type == InputSourceType.UPLOAD
    
    def test_from_path_not_found(self, tmp_path):
        """Test loading non-existent path."""
        handler = InputHandler()
        
        with pytest.raises(FileNotFoundError):
            handler.from_path(tmp_path / "not_real.wav")


class TestPreparePair:
    """Test preparing source/modulator pairs."""
    
    def test_both_uploads(self, tmp_path):
        """Test preparing two uploaded files."""
        # Create two audio files
        path1 = tmp_path / "source.wav"
        path2 = tmp_path / "mod.wav"
        
        sf.write(path1, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        sf.write(path2, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        
        handler = InputHandler()
        
        with open(path1, "rb") as f:
            data1 = f.read()
        with open(path2, "rb") as f:
            data2 = f.read()
        
        source, modulator = handler.prepare_pair(
            ("source.wav", data1),
            ("mod.wav", data2),
        )
        
        assert source.name == "source"
        assert modulator.name == "mod"
    
    def test_upload_and_library(self, tmp_path):
        """Test upload + library combination."""
        # Setup library
        lib = SoundLibrary(tmp_path)
        audio_path = tmp_path / "lib_sound.wav"
        sf.write(audio_path, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        
        meta = SoundMetadata(
            id="lib_sound",
            name="Library Sound",
            description="Desc",
            category="test",
            path=str(audio_path.relative_to(tmp_path)),
            duration=1.0,
            sample_rate=22050,
            tags=[],
        )
        lib._index["lib_sound"] = meta
        
        # Create upload file
        upload_path = tmp_path / "upload.wav"
        sf.write(upload_path, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        
        handler = InputHandler(lib)
        
        with open(upload_path, "rb") as f:
            upload_data = f.read()
        
        source, modulator = handler.prepare_pair(
            ("upload.wav", upload_data),
            "lib_sound",  # Library ID
        )
        
        assert source.source_type == InputSourceType.UPLOAD
        assert modulator.source_type == InputSourceType.LIBRARY


class TestContextManager:
    """Test context manager functionality."""
    
    def test_context_manager(self):
        """Test using handler as context manager."""
        with InputHandler() as handler:
            assert handler is not None
        # Should complete without error


class TestLoadAudioPair:
    """Test load_audio_pair convenience function."""
    
    def test_load_pair_dicts(self, tmp_path):
        """Test loading from dictionary specs."""
        # Setup library
        lib = SoundLibrary(tmp_path)
        audio_path = tmp_path / "sound.wav"
        sf.write(audio_path, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        
        meta = SoundMetadata(
            id="lib_sound",
            name="Lib Sound",
            description="Desc",
            category="test",
            path=str(audio_path.relative_to(tmp_path)),
            duration=1.0,
            sample_rate=22050,
            tags=[],
        )
        lib._index["lib_sound"] = meta
        
        # Create upload file
        upload_path = tmp_path / "upload.wav"
        sf.write(upload_path, np.random.randn(22050).astype(np.float32) * 0.3, 22050)
        
        with open(upload_path, "rb") as f:
            upload_data = f.read()
        
        source_input = {
            "type": "upload",
            "data": upload_data,
            "filename": "upload.wav",
        }
        modulator_input = {
            "type": "library",
            "id": "lib_sound",
        }
        
        source, modulator = load_audio_pair(source_input, modulator_input, lib)
        
        assert source.source_type == InputSourceType.UPLOAD
        assert modulator.source_type == InputSourceType.LIBRARY


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_audio(self, tmp_path):
        """Test handling of empty/silent audio."""
        audio_path = tmp_path / "empty.wav"
        sf.write(audio_path, np.zeros(22050, dtype=np.float32), 22050)
        
        handler = InputHandler()
        
        with open(audio_path, "rb") as f:
            content = f.read()
        
        source = handler.from_upload(content, "empty.wav")
        
        assert len(source.audio) == 22050
        assert source.audio.dtype == np.float32
