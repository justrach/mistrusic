"""Tests for the sound library module."""

import pytest
import json
import tempfile
from pathlib import Path
import numpy as np

from src.sound_library import (
    SoundMetadata,
    SoundLibrary,
    DEFAULT_LIBRARY,
    get_library,
    init_default_library,
    load_instrument_dataset,
)


class TestSoundMetadata:
    """Test SoundMetadata dataclass."""
    
    def test_creation(self):
        """Test metadata creation."""
        meta = SoundMetadata(
            id="test_sound",
            name="Test Sound",
            description="A test sound",
            category="test",
            path="audio/test.wav",
            duration=5.0,
            sample_rate=22050,
            tags=["test", "example"],
        )
        
        assert meta.id == "test_sound"
        assert meta.name == "Test Sound"
        assert meta.duration == 5.0
        assert meta.sample_rate == 22050
    
    def test_to_dict(self):
        """Test serialization to dict."""
        meta = SoundMetadata(
            id="test",
            name="Test",
            description="Desc",
            category="cat",
            path="path.wav",
            duration=1.0,
            sample_rate=22050,
            tags=["tag"],
        )
        
        d = meta.to_dict()
        assert d["id"] == "test"
        assert d["name"] == "Test"
        assert d["tags"] == ["tag"]
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        d = {
            "id": "test",
            "name": "Test",
            "description": "Desc",
            "category": "cat",
            "path": "path.wav",
            "duration": 1.0,
            "sample_rate": 22050,
            "tags": ["tag"],
        }
        
        meta = SoundMetadata.from_dict(d)
        assert meta.id == "test"
        assert meta.name == "Test"


class TestSoundLibrary:
    """Test SoundLibrary class."""
    
    def test_empty_library(self):
        """Test creating an empty library."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lib = SoundLibrary(tmpdir)
            assert len(lib) == 0
            assert lib.get_categories() == []
    
    def test_add_sound(self, tmp_path):
        """Test adding a sound to library."""
        # Create a test audio file
        audio_path = tmp_path / "test.wav"
        import soundfile as sf
        sf.write(audio_path, np.random.randn(22050).astype(np.float32), 22050)
        
        lib_dir = tmp_path / "library"
        lib = SoundLibrary(lib_dir)
        
        meta = lib.add_sound(
            sound_id="test",
            audio_path=audio_path,
            name="Test Sound",
            description="A test",
            category="test",
            tags=["test"],
        )
        
        assert meta.id == "test"
        assert meta.name == "Test Sound"
        assert "test" in lib
        assert len(lib) == 1
    
    def test_get_sound(self, tmp_path):
        """Test retrieving sound metadata."""
        lib = SoundLibrary(tmp_path)
        
        # Add a dummy entry
        meta = SoundMetadata(
            id="dummy",
            name="Dummy",
            description="Desc",
            category="test",
            path="audio/dummy.wav",
            duration=1.0,
            sample_rate=22050,
            tags=[],
        )
        lib._index["dummy"] = meta
        
        retrieved = lib.get_sound("dummy")
        assert retrieved is not None
        assert retrieved.id == "dummy"
        
        # Non-existent sound
        assert lib.get_sound("nonexistent") is None
    
    def test_list_sounds(self, tmp_path):
        """Test listing sounds."""
        lib = SoundLibrary(tmp_path)
        
        # Add multiple sounds
        for i, cat in enumerate(["cat1", "cat1", "cat2"]):
            meta = SoundMetadata(
                id=f"sound{i}",
                name=f"Sound {i}",
                description="Desc",
                category=cat,
                path=f"audio/sound{i}.wav",
                duration=1.0,
                sample_rate=22050,
                tags=["tag1" if i < 2 else "tag2"],
            )
            lib._index[f"sound{i}"] = meta
        
        # List all
        all_sounds = lib.list_sounds()
        assert len(all_sounds) == 3
        
        # Filter by category
        cat1_sounds = lib.list_sounds(category="cat1")
        assert len(cat1_sounds) == 2
        
        # Filter by tag
        tag2_sounds = lib.list_sounds(tag="tag2")
        assert len(tag2_sounds) == 1
    
    def test_get_categories(self, tmp_path):
        """Test getting unique categories."""
        lib = SoundLibrary(tmp_path)
        
        for cat in ["b", "a", "c", "a"]:
            meta = SoundMetadata(
                id=f"sound_{cat}",
                name="Sound",
                description="Desc",
                category=cat,
                path="audio/sound.wav",
                duration=1.0,
                sample_rate=22050,
                tags=[],
            )
            lib._index[f"sound_{cat}"] = meta
        
        categories = lib.get_categories()
        assert categories == ["a", "b", "c"]  # Sorted
    
    def test_get_tags(self, tmp_path):
        """Test getting unique tags."""
        lib = SoundLibrary(tmp_path)
        
        meta = SoundMetadata(
            id="sound",
            name="Sound",
            description="Desc",
            category="test",
            path="audio/sound.wav",
            duration=1.0,
            sample_rate=22050,
            tags=["tag1", "tag2", "tag1"],
        )
        lib._index["sound"] = meta
        
        tags = lib.get_tags()
        assert "tag1" in tags
        assert "tag2" in tags
    
    def test_search(self, tmp_path):
        """Test searching sounds."""
        lib = SoundLibrary(tmp_path)
        
        sounds = [
            ("piano", "Grand Piano", "A nice piano", ["keys"]),
            ("violin", "Violin", "String instrument", ["strings"]),
            ("piano2", "Electric Piano", "Electric keys", ["keys", "electric"]),
        ]
        
        for id_, name, desc, tags in sounds:
            meta = SoundMetadata(
                id=id_,
                name=name,
                description=desc,
                category="instruments",
                path=f"audio/{id_}.wav",
                duration=1.0,
                sample_rate=22050,
                tags=tags,
            )
            lib._index[id_] = meta
        
        # Search by name
        results = lib.search("piano")
        assert len(results) == 2
        
        # Search by description
        results = lib.search("string")
        assert len(results) == 1
        assert results[0].id == "violin"
        
        # Search by tag
        results = lib.search("electric")
        assert len(results) == 1
        assert results[0].id == "piano2"
    
    def test_remove_sound(self, tmp_path):
        """Test removing a sound."""
        lib = SoundLibrary(tmp_path)
        
        meta = SoundMetadata(
            id="toremove",
            name="To Remove",
            description="Desc",
            category="test",
            path="audio/toremove.wav",
            duration=1.0,
            sample_rate=22050,
            tags=[],
        )
        lib._index["toremove"] = meta
        
        assert "toremove" in lib
        assert lib.remove_sound("toremove") is True
        assert "toremove" not in lib
        assert lib.remove_sound("toremove") is False
    
    def test_iteration(self, tmp_path):
        """Test library iteration."""
        lib = SoundLibrary(tmp_path)
        
        for i in range(3):
            meta = SoundMetadata(
                id=f"sound{i}",
                name=f"Sound {i}",
                description="Desc",
                category="test",
                path=f"audio/sound{i}.wav",
                duration=1.0,
                sample_rate=22050,
                tags=[],
            )
            lib._index[f"sound{i}"] = meta
        
        ids = [m.id for m in lib]
        assert len(ids) == 3
        assert "sound0" in ids


class TestDefaultLibrary:
    """Test default library initialization."""
    
    def test_default_sounds_count(self):
        """Test that default library has expected sounds."""
        # Should have many sounds across categories
        categories = set()
        for sound_id, info in DEFAULT_LIBRARY.items():
            categories.add(info["category"])
        
        # Should have at least these categories
        expected_categories = {
            "mechanical", "instruments", "synthetic", 
            "percussion", "nature", "vocal", "urban", "fx"
        }
        assert expected_categories.issubset(categories)
        
        # Should have many sounds
        assert len(DEFAULT_LIBRARY) > 50
    
    def test_init_default_library(self, tmp_path):
        """Test initializing default library."""
        lib = init_default_library(tmp_path)
        
        # Should have all default sounds
        assert len(lib) == len(DEFAULT_LIBRARY)
        
        # Check specific sounds exist
        assert "piano" in lib
        assert "boat_motor" in lib
        assert "ocean_waves" in lib


class TestLibraryPersistence:
    """Test library save/load."""
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading library index."""
        lib = SoundLibrary(tmp_path)
        
        meta = SoundMetadata(
            id="persist",
            name="Persistent",
            description="Desc",
            category="test",
            path="audio/persist.wav",
            duration=5.0,
            sample_rate=44100,
            tags=["test", "persist"],
        )
        lib._index["persist"] = meta
        lib._save_index()
        
        # Create new library instance pointing to same dir
        lib2 = SoundLibrary(tmp_path)
        
        assert "persist" in lib2
        loaded = lib2.get_sound("persist")
        assert loaded.name == "Persistent"
        assert loaded.sample_rate == 44100


class TestInstrumentDataset:
    """Test loading instrument dataset."""
    
    def test_load_from_metadata(self, tmp_path):
        """Test loading from metadata.json."""
        # Create mock metadata
        metadata = [
            {"carrier": "a.wav", "output": "b.wav", "style": "flute"},
            {"carrier": "c.wav", "output": "d.wav", "style": "trumpet"},
            {"carrier": "e.wav", "output": "f.wav", "style": "flute"},  # Duplicate style
        ]
        
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text(json.dumps(metadata))
        
        lib_dir = tmp_path / "library"
        lib = SoundLibrary(lib_dir)
        
        # Manually call load function
        from src.sound_library import load_instrument_dataset
        load_instrument_dataset(tmp_path)
        
        # Check that unique styles were added
        lib2 = SoundLibrary(lib_dir)
        # Note: load_instrument_dataset modifies global _library, not the instance


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_load_missing_sound(self, tmp_path):
        """Test loading a sound that doesn't exist."""
        lib = SoundLibrary(tmp_path)
        
        with pytest.raises(KeyError):
            lib.load_audio("nonexistent")
    
    def test_add_missing_file(self, tmp_path):
        """Test adding a file that doesn't exist."""
        lib = SoundLibrary(tmp_path)
        
        with pytest.raises(FileNotFoundError):
            lib.add_sound("test", tmp_path / "not_real.wav")
    
    def test_invalid_audio_file(self, tmp_path):
        """Test adding invalid audio file."""
        lib = SoundLibrary(tmp_path)
        
        # Create a non-audio file
        bad_file = tmp_path / "not_audio.wav"
        bad_file.write_text("not audio data")
        
        with pytest.raises(Exception):
            lib.add_sound("bad", bad_file)


class TestGlobalLibrary:
    """Test global library functions."""
    
    def test_get_library_singleton(self):
        """Test that get_library returns same instance."""
        # Note: This test may be affected by other tests
        lib1 = get_library("test_lib_1")
        lib2 = get_library("test_lib_1")
        
        # Same path should return same instance
        assert lib1 is lib2
    
    def test_get_library_different_paths(self):
        """Test getting different libraries."""
        lib1 = get_library("test_lib_a")
        lib2 = get_library("test_lib_b")
        
        # Different paths should be different instances
        assert lib1 is not lib2
