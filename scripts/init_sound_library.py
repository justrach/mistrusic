#!/usr/bin/env python3
"""Initialize the default sound library with metadata.

Usage:
    python scripts/init_sound_library.py
    
This creates the library index file. To add actual audio files,
use the library.add_sound() method or place WAV files in:
    data/sound_library/audio/{sound_id}.wav
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sound_library import init_default_library


def main():
    print("Initializing default sound library...")
    
    lib = init_default_library("data/sound_library")
    
    print(f"\nLibrary initialized at: data/sound_library")
    print(f"Total sounds in index: {len(lib)}")
    print(f"\nCategories: {', '.join(lib.get_categories())}")
    
    print("\nTo add audio files, place them at:")
    print("  data/sound_library/audio/{sound_id}.wav")
    print("\nOr use the API to add sounds dynamically.")
    
    print("\n\nAvailable sounds:")
    for sound in lib:
        print(f"  - {sound.id}: {sound.name} ({sound.category})")


if __name__ == "__main__":
    main()
