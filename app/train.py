"""Training script untuk model Seq2Seq pada dataset IndoSum.

Cara pakai:
    cd app
    python -m app.train --indosum-dir .. --epochs 5 --max-train 20000

Catatan:
- Default hyper-parameter sengaja ringan supaya bisa jalan di CPU/GPU kecil.
- Gunakan --max-train / --max-val untuk membatasi dataset saat eksperimen.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from typing import List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# Pastikan import paket relatif jalan saat dieksekusi sebagai script.
_PKG_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_PARENT not in sys.path:
    sys.path.insert(0, _PKG_PARENT)

from app.backend.data_utils import (  # noqa: E402
    flatten_article_text,
    flatten_summary,
    iter_jsonl_split,
)
from app.models.seq2seq import EOS_ID, PAD_ID, SOS_ID, Seq2Seq  # noqa: E402
from app.models.vocab import Vocab  # noqa: E402


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class IndoSumDataset(Dataset):
    def __init__(
        self,
        items: List[Tuple[str, str]],
        vocab: Vocab,
        max_src_len: int = 400,
        max_tgt_len: int = 80,
    ) -> None:
        self.items = items
        self.vocab = vocab
        self.max_src_len = max_src_len
        self.max_tgt_len = max_tgt_len

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        article, summary = self.items[idx]
        src_ids = self.vocab.encode(article, add_special=False, max_len=self.max_src_len)
        tgt_ids = self.vocab.encode(summary, add_special=True, max_len=self.max_tgt_len)
        if not src_ids:
            src_ids = [PAD_ID]
        if len(tgt_ids) < 2:
            tgt_ids = [SOS_ID, EOS_ID]
        return torch.tensor(src_ids, dtype=torch.long), torch.tensor(tgt_ids, dtype=torch.long)


def collate_batch(batch):
    srcs, tgts = zip(*batch)
    src_lens = torch.tensor([s.size(0) for s in srcs], dtype=torch.long)
    tgt_lens = torch.tensor([t.size(0) for t in tgts], dtype=torch.long)
    src_pad = nn.utils.rnn.pad_sequence(srcs, batch_first=True, padding_value=PAD_ID)
    tgt_pad = nn.utils.rnn.pad_sequence(tgts, batch_first=True, padding_value=PAD_ID)
    return src_pad, src_lens, tgt_pad, tgt_lens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def collect_pairs(indosum_dir: str, split: str, max_items: int | None) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for i, item in enumerate(iter_jsonl_split(indosum_dir, split)):
        if max_items is not None and i >= max_items:
            break
        article = flatten_article_text(item.get("paragraphs", []))
        summary = flatten_summary(item.get("summary", []))
        if article and summary:
            pairs.append((article, summary))
    return pairs


def epoch_loop(
    model: Seq2Seq,
    loader: DataLoader,
    optim: torch.optim.Optimizer | None,
    criterion: nn.Module,
    device: str,
    teacher_forcing: float = 1.0,
    clip: float = 1.0,
) -> float:
    is_train = optim is not None
    model.train(is_train)
    total_loss = 0.0
    n_batches = 0
    for src, src_len, tgt, _ in loader:
        src = src.to(device)
        tgt = tgt.to(device)
        if is_train:
            optim.zero_grad()
        outputs = model(src, tgt, src_lengths=src_len, teacher_forcing_ratio=teacher_forcing)
        # outputs: (B, T, V). Bandingkan dari posisi 1 (skip <sos>).
        B, T, V = outputs.shape
        logits = outputs[:, 1:].reshape(-1, V)
        targets = tgt[:, 1:].reshape(-1)
        loss = criterion(logits, targets)
        if is_train:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
            optim.step()
        total_loss += float(loss.item())
        n_batches += 1
    return total_loss / max(n_batches, 1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Default path absolute supaya tidak tergantung cwd.
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))
    _DEFAULT_INDOSUM = os.path.normpath(os.path.join(_APP_DIR, ".."))
    _DEFAULT_CKPT_DIR = os.path.join(_APP_DIR, "models", "checkpoints")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--indosum-dir",
        default=_DEFAULT_INDOSUM,
        help="Folder berisi *.jsonl IndoSum",
    )
    parser.add_argument("--checkpoint-dir", default=_DEFAULT_CKPT_DIR)
    parser.add_argument("--max-train", type=int, default=20000)
    parser.add_argument("--max-val", type=int, default=1000)
    parser.add_argument("--max-src-len", type=int, default=400)
    parser.add_argument("--max-tgt-len", type=int, default=80)
    parser.add_argument("--vocab-min-freq", type=int, default=3)
    parser.add_argument("--vocab-size", type=int, default=30000)
    parser.add_argument("--emb-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--enc-layers", type=int, default=1)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--teacher-forcing", type=float, default=0.85)
    parser.add_argument("--device", default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Lanjutkan dari checkpoint terakhir bila ada (model + vocab dipakai ulang).",
    )
    args = parser.parse_args()

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[info] device = {device}")
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    # ------------------------------------------------------------------ data
    print("[info] memuat data train ...")
    train_pairs = collect_pairs(args.indosum_dir, "train", args.max_train)
    print(f"[info] train pairs: {len(train_pairs)}")
    print("[info] memuat data dev ...")
    dev_pairs = collect_pairs(args.indosum_dir, "dev", args.max_val)
    print(f"[info] dev pairs: {len(dev_pairs)}")

    # ------------------------------------------------------------------ vocab
    vocab_path = os.path.join(args.checkpoint_dir, "vocab.json")
    ckpt_path = os.path.join(args.checkpoint_dir, "seq2seq_best.pt")
    if args.resume and os.path.exists(vocab_path):
        print(f"[info] resume: load vocab dari {vocab_path}")
        vocab = Vocab.load(vocab_path)
    else:
        print("[info] membangun vocabulary ...")
        texts = []
        for a, s in train_pairs:
            texts.append(a)
            texts.append(s)
        vocab = Vocab.build(texts, min_freq=args.vocab_min_freq, max_size=args.vocab_size)
        vocab.save(vocab_path)
    print(f"[info] vocab size: {vocab.size} -> {vocab_path}")

    # --------------------------------------------------------------- dataloader
    train_ds = IndoSumDataset(train_pairs, vocab, args.max_src_len, args.max_tgt_len)
    dev_ds = IndoSumDataset(dev_pairs, vocab, args.max_src_len, args.max_tgt_len)
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_batch,
    )
    dev_loader = DataLoader(
        dev_ds,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_batch,
    )

    # ----------------------------------------------------------------- model
    config = {
        "emb_dim": args.emb_dim,
        "hidden_dim": args.hidden_dim,
        "enc_layers": args.enc_layers,
        "dropout": args.dropout,
        "max_src_len": args.max_src_len,
        "max_tgt_len": args.max_tgt_len,
    }

    if args.resume and os.path.exists(ckpt_path):
        print(f"[info] resume: load checkpoint dari {ckpt_path}")
        prev = torch.load(ckpt_path, map_location=device)
        prev_cfg = prev.get("config", {})
        # Pakai config lama agar dimensi cocok dengan checkpoint.
        config.update({k: prev_cfg.get(k, v) for k, v in config.items()})
        model = Seq2Seq(
            vocab_size=vocab.size,
            emb_dim=config["emb_dim"],
            hidden_dim=config["hidden_dim"],
            enc_layers=config["enc_layers"],
            dropout=config["dropout"],
        ).to(device)
        try:
            model.load_state_dict(prev["model_state"])
            print("[info] state checkpoint berhasil dimuat.")
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] gagal load state ({exc}); mulai dari nol.")
    else:
        model = Seq2Seq(
            vocab_size=vocab.size,
            emb_dim=config["emb_dim"],
            hidden_dim=config["hidden_dim"],
            enc_layers=config["enc_layers"],
            dropout=config["dropout"],
        ).to(device)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"[info] model params: {n_params/1e6:.2f} M")

    optim = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss(ignore_index=PAD_ID)

    # ----------------------------------------------------------------- train
    best_val = math.inf

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss = epoch_loop(
            model, train_loader, optim, criterion, device,
            teacher_forcing=args.teacher_forcing,
        )
        val_loss = epoch_loop(model, dev_loader, None, criterion, device, teacher_forcing=1.0)
        dt = time.time() - t0
        print(
            f"[epoch {epoch}/{args.epochs}] "
            f"train_loss={train_loss:.4f} val_loss={val_loss:.4f} "
            f"time={dt:.1f}s"
        )
        if val_loss < best_val:
            best_val = val_loss
            torch.save(
                {"model_state": model.state_dict(), "config": config},
                ckpt_path,
            )
            print(f"  -> saved best checkpoint to {ckpt_path}")

    print(f"[done] best val_loss = {best_val:.4f}")


if __name__ == "__main__":
    main()
