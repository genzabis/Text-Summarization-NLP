"""Utility untuk loading dan preprocessing dataset IndoSum.

Format setiap baris jsonl IndoSum:
{
  "category": str,
  "gold_labels": List[List[bool]],
  "id": str,
  "paragraphs": List[List[List[str]]],   # paragraf -> kalimat -> token
  "source": str,
  "source_url": str,
  "summary": List[List[str]]              # kalimat -> token
}
"""

from __future__ import annotations

import json
import os
import re
from glob import glob
from typing import Iterable, Iterator, List


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_jsonl(path: str) -> List[dict]:
    """Load satu file jsonl menjadi list of dict."""
    data: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


def iter_jsonl_split(indosum_dir: str, split: str) -> Iterator[dict]:
    """Iterate seluruh shard untuk split tertentu (train/dev/test).

    IndoSum punya 5 shard per split (mis. train.01.jsonl ... train.05.jsonl).
    """
    pattern = os.path.join(indosum_dir, f"{split}.*.jsonl")
    files = sorted(glob(pattern))
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)


def load_split(indosum_dir: str, split: str, limit: int | None = None) -> List[dict]:
    """Load seluruh data untuk satu split, dengan opsi limit."""
    data: List[dict] = []
    for i, item in enumerate(iter_jsonl_split(indosum_dir, split)):
        if limit is not None and i >= limit:
            break
        data.append(item)
    return data


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

_PUNCT_FIX_RE = re.compile(r"\s+([,.;:?!\)])")
_OPEN_PAREN_FIX_RE = re.compile(r"([\(])\s+")
_MULTI_SPACE_RE = re.compile(r"\s+")


def detokenize(tokens: Iterable[str]) -> str:
    """Gabungkan token menjadi kalimat dengan spasi yang dirapikan."""
    text = " ".join(tokens)
    text = _PUNCT_FIX_RE.sub(r"\1", text)
    text = _OPEN_PAREN_FIX_RE.sub(r"\1", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text


def flatten_article(paragraphs: List[List[List[str]]]) -> List[str]:
    """Pecah artikel menjadi list kalimat (string)."""
    sentences: List[str] = []
    for para in paragraphs:
        for sent_tokens in para:
            sentences.append(detokenize(sent_tokens))
    return sentences


def flatten_article_text(paragraphs: List[List[List[str]]]) -> str:
    """Gabungkan seluruh artikel menjadi satu string panjang."""
    return " ".join(flatten_article(paragraphs))


def flatten_summary(summary: List[List[str]]) -> str:
    """Gabungkan summary (list kalimat token) menjadi satu string."""
    return " ".join(detokenize(s) for s in summary)


def split_sentences(text: str) -> List[str]:
    """Pecah teks bebas (input user) menjadi kalimat secara cerdas.

    Menggunakan teknik placeholder untuk singkatan bahasa Indonesia (PT., Rp., Jl., dll.)
    dan bilangan numerik (10.000) agar kalimat tidak terpecah di tengah jalan.
    """
    text = text.strip()
    if not text:
        return []

    # Singkatan umum Bahasa Indonesia yang diikuti titik
    abbreviations = [
        "pt", "rp", "jl", "dr", "prof", "ir", "kab", "kec", "kel", "no", 
        "tbk", "capt", "drs", "st", "s.pd", "m.kom", "dll", "dst", "dsb", "dsk",
        "wib", "wita", "wit", "kpk", "dpr", "dki", "diy", "as", "us", "ri",
        "jan", "feb", "mar", "apr", "mei", "jun", "jul", "agt", "sep", "okt", "nov", "des",
        "hal", "art", "vol", "hlm", "h", "m"
    ]
    
    # Ganti titik pada singkatan (case-insensitive) dengan placeholder khusus
    temp_text = text
    for abbr in abbreviations:
        # Regex yang mencocokkan batas kata + singkatan + titik
        pattern = re.compile(rf"\b{abbr}\.", re.IGNORECASE)
        temp_text = pattern.sub(f"{abbr}[DOT]", temp_text)
        
    # Juga untuk desimal/ribuan: "10.000" -> "10[DOT]000"
    temp_text = re.sub(r"(\d+)\.(\d+)", r"\1[DOT]\2", temp_text)
    
    # Pisah berdasarkan tanda . ! ? yang diikuti spasi/akhir kalimat
    parts = re.split(r"(?<=[\.\!\?])\s+", temp_text)
    
    sentences = []
    for p in parts:
        p_clean = p.strip()
        if p_clean:
            # Kembalikan placeholder [DOT] menjadi titik semula
            p_restored = p_clean.replace("[DOT]", ".")
            sentences.append(p_restored)
            
    return sentences


def simple_tokenize(text: str) -> List[str]:
    """Tokenizer sederhana berbasis regex untuk kata + tanda baca."""
    text = text.lower()
    return re.findall(r"[a-z0-9]+|[\.,!?;:]", text)
