"""Wrapper inferensi untuk model Seq2Seq.

Karena tidak semua user akan ikut training (butuh GPU + waktu), modul ini
mendukung graceful fallback: bila checkpoint belum tersedia maka method
``is_ready`` akan mengembalikan False dan API memberi pesan jelas.
"""

from __future__ import annotations

import os
from threading import Lock
from typing import List, Optional

import torch

from ..models.seq2seq import EOS_ID, PAD_ID, SOS_ID, Seq2Seq
from ..models.vocab import Vocab


def _resolve_existing(primary: str, *fallbacks: str) -> str:
    """Return primary jika ada, kalau tidak coba fallback yang valid."""
    if os.path.exists(primary):
        return primary
    for fb in fallbacks:
        if fb and os.path.exists(fb):
            return fb
    return primary  # tetap kembalikan primary supaya pesan errornya jelas


class Seq2SeqSummarizer:
    def __init__(self, checkpoint_path: str, vocab_path: str, device: Optional[str] = None) -> None:
        # Cari fallback di root repo (dua level di atas) jika file utama belum ada.
        # Ini berguna saat user menjalankan `python -m app.train` dari cwd repo root
        # sehingga checkpoint tertulis ke <root>/models/checkpoints/.
        root_alt_ckpt = checkpoint_path.replace(
            os.path.normpath("app/models/"), "models/", 1
        ) if os.path.isabs(checkpoint_path) else checkpoint_path
        root_alt_vocab = vocab_path.replace(
            os.path.normpath("app/models/"), "models/", 1
        ) if os.path.isabs(vocab_path) else vocab_path

        self.checkpoint_path = _resolve_existing(checkpoint_path, root_alt_ckpt)
        self.vocab_path = _resolve_existing(vocab_path, root_alt_vocab)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model: Optional[Seq2Seq] = None
        self._vocab: Optional[Vocab] = None
        self._max_src_len: int = 400
        self._lock = Lock()

    # ----------------------------------------------------------------- ready
    def _refresh_paths(self) -> None:
        # Bila checkpoint awalnya belum ada (misalnya saat server start),
        # cek lagi sebelum tiap pemanggilan supaya bisa hot-detect file baru.
        for attr in ("checkpoint_path", "vocab_path"):
            cur = getattr(self, attr)
            if not os.path.exists(cur):
                # Coba lokasi alternatif di root repo.
                alt = cur.replace(os.path.normpath("app/models/"), "models/", 1)
                if alt != cur and os.path.exists(alt):
                    setattr(self, attr, alt)

    def is_ready(self) -> bool:
        self._refresh_paths()
        return os.path.exists(self.checkpoint_path) and os.path.exists(self.vocab_path)

    def status(self) -> dict:
        return {
            "ready": self.is_ready(),
            "checkpoint": self.checkpoint_path,
            "vocab": self.vocab_path,
            "device": self.device,
            "loaded": self._model is not None,
        }

    # ------------------------------------------------------------------ load
    def _load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            if not self.is_ready():
                raise FileNotFoundError(
                    "Checkpoint atau vocab Seq2Seq belum tersedia. "
                    "Silakan jalankan `python -m app.train` dulu."
                )

            self._vocab = Vocab.load(self.vocab_path)
            ckpt = torch.load(self.checkpoint_path, map_location=self.device)

            cfg = ckpt.get("config", {})
            self._max_src_len = cfg.get("max_src_len", 400)
            model = Seq2Seq(
                vocab_size=self._vocab.size,
                emb_dim=cfg.get("emb_dim", 128),
                hidden_dim=cfg.get("hidden_dim", 256),
                enc_layers=cfg.get("enc_layers", 1),
                dropout=cfg.get("dropout", 0.3),
            )
            model.load_state_dict(ckpt["model_state"])
            model.to(self.device)
            model.eval()
            self._model = model

    # --------------------------------------------------------------- predict
    def summarize(self, text: str, max_len: int = 80) -> str:
        if not text or not text.strip():
            return ""
        self._load()
        assert self._model is not None and self._vocab is not None

        ids = self._vocab.encode(text, add_special=False, max_len=self._max_src_len)
        if not ids:
            return ""
        src = torch.tensor([ids], dtype=torch.long, device=self.device)
        src_lengths = torch.tensor([len(ids)], dtype=torch.long)
        out_ids = self._model.greedy_generate(src, max_len=max_len, src_lengths=src_lengths)
        return self._vocab.decode(out_ids[0])
