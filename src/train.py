"""Train the StyleVocoder model with MLX on Apple Silicon.

Example::

    python -m src.train \\
        --data-dir /path/to/good-sounds \\
        --profiles profiles.npz \\
        --checkpoints checkpoints
"""
from __future__ import annotations

import argparse
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten
from tqdm import tqdm

from .model import StyleVocoderModel, N_MELS, save_checkpoint
from .style_profiles import load_profiles
from .dataset import VocoderDataset


def _make_batches(
    dataset: VocoderDataset,
    batch_size: int,
    shuffle: bool = True,
):
    """Yield (carrier, target, style) MLX arrays in NLC format."""
    indices = np.arange(len(dataset))
    if shuffle:
        np.random.shuffle(indices)

    def _load(i: int) -> dict:
        return dataset[int(i)]

    for start in range(0, len(indices), batch_size):
        idx_batch = indices[start : start + batch_size]
        with ThreadPoolExecutor(max_workers=4) as ex:
            items = list(ex.map(_load, idx_batch))

        # Transpose (N_MELS, T) → (T, N_MELS) for MLX NLC format
        carrier = mx.array(np.stack([it["carrier_mel"].T for it in items]))
        target  = mx.array(np.stack([it["target_mel"].T  for it in items]))
        style   = mx.array(np.stack([it["style_emb"]     for it in items]))
        yield carrier, target, style


def _loss_fn(
    model: StyleVocoderModel,
    carrier: mx.array,
    target: mx.array,
    style: mx.array,
) -> mx.array:
    pred = model(carrier, style)
    return mx.mean(mx.abs(pred - target))


def train(args: argparse.Namespace) -> None:
    profiles  = load_profiles(args.profiles)
    style_dim = next(iter(profiles.values())).shape[0]

    dataset = VocoderDataset(
        args.data_dir, profiles,
        segment_samples=args.segment_samples,
    )
    print(f"Dataset : {len(dataset)} pairs")

    model = StyleVocoderModel(
        n_mels=N_MELS, style_dim=style_dim, hidden_dim=args.hidden_dim,
    )
    mx.eval(model.parameters())

    n_params = sum(
        v.size for v in tree_flatten(model.parameters())[0]
        if isinstance(v, mx.array)
    )
    print(f"Params  : {n_params / 1e6:.1f}M")

    # Optionally fine-tune from an existing checkpoint
    if args.load_from:
        ckpt_weights = str(Path(args.load_from).with_suffix(".safetensors"))
        model.load_weights(ckpt_weights)
        mx.eval(model.parameters())
        print(f"Loaded weights from {ckpt_weights}")

    steps_per_epoch = math.ceil(len(dataset) / args.batch_size)

    optimizer = optim.AdamW(
        learning_rate=args.lr,
        weight_decay=1e-4,
    )
    loss_and_grad = nn.value_and_grad(model, _loss_fn)

    ckpt_dir = Path(args.checkpoints)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    config   = {"n_mels": N_MELS, "style_dim": style_dim, "hidden_dim": args.hidden_dim}

    best_loss = float("inf")

    for epoch in range(1, args.epochs + 1):
        # Cosine LR decay (manual)
        lr = args.lr * 0.5 * (1.0 + math.cos(math.pi * (epoch - 1) / args.epochs))
        optimizer.learning_rate = lr

        running = 0.0
        batches = list(_make_batches(dataset, args.batch_size, shuffle=True))

        for carrier, target, style in tqdm(
            batches, desc=f"Epoch {epoch}/{args.epochs}", leave=False
        ):
            loss, grads = loss_and_grad(model, carrier, target, style)
            optimizer.update(model, grads)
            mx.eval(model.parameters(), optimizer.state)
            running += loss.item()

        avg = running / max(len(batches), 1)
        print(f"Epoch {epoch:3d}  loss={avg:.5f}  lr={lr:.2e}")

        save_checkpoint(model, str(ckpt_dir / f"ckpt_{epoch:03d}"), config, epoch, avg)
        if avg < best_loss:
            best_loss = avg
            save_checkpoint(model, str(ckpt_dir / "best"), config, epoch, avg)
            print(f"    new best: {best_loss:.5f}")
def main() -> None:
    ap = argparse.ArgumentParser(description="Train StyleVocoder (MLX)")
    ap.add_argument("--data-dir",         required=True)
    ap.add_argument("--profiles",         required=True)
    ap.add_argument("--checkpoints",      required=True)
    ap.add_argument("--load-from",        default=None,
                    help="Checkpoint stem to fine-tune from (e.g. checkpoints/best)")
    ap.add_argument("--batch-size",       type=int,   default=8)
    ap.add_argument("--epochs",           type=int,   default=50)
    ap.add_argument("--lr",               type=float, default=3e-4)
    ap.add_argument("--hidden-dim",       type=int,   default=256)
    ap.add_argument("--segment-samples",  type=int,   default=32768)
    train(ap.parse_args())


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
