"""Symlink good-sounds reference recordings into raw_instruments/ layout
and build profiles.npz.

Example::

    python scripts/prepare_profiles.py \\
        --sounds-dir /Users/rachpradhan/Downloads/4588740/good-sounds \\
        --raw-dir raw_instruments \\
        --out profiles.npz
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
import sys

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.style_profiles import build_profiles

# Instruments with enough high-quality reference recordings
DEFAULT_INSTRUMENTS = [
    "flute", "clarinet", "violin", "cello",
    "trumpet", "sax_alto", "sax_tenor", "oboe",
]


def prepare_profiles(
    sounds_dir: Path,
    raw_dir: Path,
    profiles_path: Path,
    instruments: list[str],
    mic: str = "neumann",
    max_per_instrument: int = 50,
) -> None:
    db = sqlite3.connect(str(sounds_dir / "database.sqlite"))
    db.row_factory = sqlite3.Row

    print(f"Building profiles from {sounds_dir}")
    for inst in instruments:
        inst_dir = raw_dir / inst
        inst_dir.mkdir(parents=True, exist_ok=True)

        rows = db.execute("""
            SELECT t.filename
            FROM takes t
            JOIN sounds s ON s.id = t.sound_id
            WHERE t.microphone = ?
              AND s.instrument = ?
              AND s.reference  = 1
              AND s.klass      = 'good-sound'
            LIMIT ?
        """, (mic, inst, max_per_instrument)).fetchall()

        n = 0
        for row in rows:
            src = (sounds_dir / row["filename"]).resolve()
            dst = inst_dir / src.name
            if dst.exists():
                continue
            try:
                dst.symlink_to(src)
                n += 1
            except Exception as exc:
                print(f"  warn [{inst}]: {exc}")
        print(f"  {inst}: {n} symlinks created")

    build_profiles(raw_dir, profiles_path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build style profiles from good-sounds")
    ap.add_argument("--sounds-dir",          required=True,
                    help="Path to good-sounds dataset root")
    ap.add_argument("--raw-dir",             default="raw_instruments",
                    help="Destination dir for symlinked wav files")
    ap.add_argument("--out",                 default="profiles.npz",
                    help="Output .npz profile path")
    ap.add_argument("--mic",                 default="neumann",
                    help="Microphone to use (neumann|akg|iphone)")
    ap.add_argument("--max-per-instrument",  type=int, default=50)
    args = ap.parse_args()

    prepare_profiles(
        Path(args.sounds_dir),
        Path(args.raw_dir),
        Path(args.out),
        DEFAULT_INSTRUMENTS,
        mic=args.mic,
        max_per_instrument=args.max_per_instrument,
    )


if __name__ == "__main__":
    main()
