"""Vocabulary tokenizer untuk model Seq2Seq."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Dict, Iterable, List

from .seq2seq import EOS_ID, PAD_ID, SOS_ID, SPECIAL_TOKENS, UNK_ID


_TOKEN_RE = re.compile(r"[A-Za-z]+|\d+|[\.,!?;:\-]")


def tokenize(text: str) -> List[str]:
    """Tokenizer ringan: lowercase + split kata/angka/tanda baca."""
    return _TOKEN_RE.findall(text.lower())


class Vocab:
    def __init__(self, token2id: Dict[str, int]) -> None:
        self.token2id = token2id
        self.id2token = {i: t for t, i in token2id.items()}

    # --------------------------------------------------------------- build
    @classmethod
    def build(
        cls,
        texts: Iterable[str],
        min_freq: int = 2,
        max_size: int = 30000,
    ) -> "Vocab":
        counter: Counter = Counter()
        for txt in texts:
            counter.update(tokenize(txt))

        token2id: Dict[str, int] = {tok: i for i, tok in enumerate(SPECIAL_TOKENS)}
        next_id = len(SPECIAL_TOKENS)
        for tok, freq in counter.most_common():
            if freq < min_freq:
                break
            if next_id >= max_size:
                break
            if tok in token2id:
                continue
            token2id[tok] = next_id
            next_id += 1
        return cls(token2id)

    # -------------------------------------------------------------- io
    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.token2id, f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "Vocab":
        with open(path, "r", encoding="utf-8") as f:
            token2id = json.load(f)
        return cls(token2id)

    # -------------------------------------------------------------- props
    def __len__(self) -> int:
        return len(self.token2id)

    @property
    def size(self) -> int:
        return len(self.token2id)

    # -------------------------------------------------------------- encode
    def encode(self, text: str, add_special: bool = False, max_len: int | None = None) -> List[int]:
        ids = [self.token2id.get(tok, UNK_ID) for tok in tokenize(text)]
        if add_special:
            ids = [SOS_ID] + ids + [EOS_ID]
        if max_len is not None:
            if add_special:
                # Pastikan EOS tetap ada di akhir.
                if len(ids) > max_len:
                    ids = ids[: max_len - 1] + [EOS_ID]
            else:
                ids = ids[:max_len]
        return ids

    def decode(self, ids: Iterable[int]) -> str:
        toks = []
        for i in ids:
            if i in (PAD_ID, SOS_ID, EOS_ID):
                continue
            toks.append(self.id2token.get(int(i), "<unk>"))
        # Rapikan tanda baca yang diawali spasi.
        text = " ".join(toks)
        text = re.sub(r"\s+([\.,!?;:])", r"\1", text)
        return text
