"""Build a metadata.json training manifest from good-sounds cross-instrument pairs.

Paths in metadata.json are relative to the good-sounds root, so pass
``--sounds-dir`` as ``--data-dir`` when running ``src.train``.

Example::

    python scripts/prepare_dataset.py \\
        --sounds-dir /Users/rachpradhan/Downloads/4588740/good-sounds \\
        --out data/good_sounds_pairs/metadata.json

    python -m src.train \\
        --data-dir  /Users/rachpradhan/Downloads/4588740/good-sounds \\
        --profiles  profiles.npz \\
        --checkpoints checkpoints
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
from collections import defaultdict
from pathlib import Path


# Instruments included in training (those with sufficient reference coverage)
INSTRUMENTS = [
    "flute", "clarinet", "violin", "cello",
    "trumpet", "sax_alto", "sax_tenor", "oboe",
]


def build_metadata(
    sounds_dir: Path,
    out_json: Path,
    instruments: list[str],
    mic: str = "neumann",
    max_pairs: int = 10_000,
    seed: int = 42,
) -> None:
    random.seed(seed)
    db = sqlite3.connect(str(sounds_dir / "database.sqlite"))
    db.row_factory = sqlite3.Row

    # Collect all reference takes per instrument
    pool: dict[str, list[str]] = {}
    for inst in instruments:
        rows = db.execute("""
            SELECT t.filename FROM takes t
            JOIN sounds s ON s.id = t.sound_id
            WHERE t.microphone = ?
              AND s.instrument = ?
              AND s.reference  = 1
        """, (mic, inst)).fetchall()
        pool[inst] = [r["filename"] for r in rows]
        print(f"  {inst}: {len(pool[inst])} reference takes")

    # Sample random cross-instrument pairs, balanced across style targets
    pairs_per_style = max_pairs // (len(instruments) - 1)
    pairs: list[dict] = []

    for inst_b in instruments:
        carriers = [f for inst, files in pool.items() if inst != inst_b for f in files]
        targets  = pool[inst_b]
        if not carriers or not targets:
            continue
        for _ in range(pairs_per_style):
            pairs.append({
                "carrier": random.choice(carriers),
                "output":  random.choice(targets),
                "style":   inst_b,
            })

    random.shuffle(pairs)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as fh:
        json.dump(pairs, fh, indent=2)

    print(f"\nWrote {len(pairs)} pairs -> {out_json}")
    by_style: dict[str, int] = defaultdict(int)
    for p in pairs:
        by_style[p["style"]] += 1
    for style, cnt in sorted(by_style.items()):
        print(f"  {style}: {cnt} target pairs")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build training manifest from good-sounds cross-instrument pairs"
    )
    ap.add_argument("--sounds-dir", required=True,
                    help="Path to good-sounds dataset root")
    ap.add_argument("--out",        default="data/good_sounds_pairs/metadata.json",
                    help="Output metadata.json path")
    ap.add_argument("--mic",        default="neumann",
                    help="Microphone to use (neumann|akg|iphone)")
    ap.add_argument("--max-pairs",  type=int, default=10_000)
    ap.add_argument("--seed",       type=int, default=42)
    args = ap.parse_args()

    build_metadata(
        Path(args.sounds_dir),
        Path(args.out),
        INSTRUMENTS,
        mic=args.mic,
        max_pairs=args.max_pairs,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
