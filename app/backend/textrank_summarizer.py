"""Baseline TextRank summarizer (extractive).

Implementasi sendiri agar tidak bergantung pada NLTK punkt download saat runtime.
Menggunakan kalimat-kalimat yang sudah dipotong, vektor TF-IDF sederhana,
similaritas cosine, dan PageRank-style power iteration.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Sequence, Tuple

from .data_utils import simple_tokenize, split_sentences


# ---------------------------------------------------------------------------
# Stopwords ringan Bahasa Indonesia
# ---------------------------------------------------------------------------
_STOPWORDS = {
    "yang", "di", "ke", "dari", "untuk", "pada", "dalam", "dan", "atau",
    "ini", "itu", "adalah", "akan", "telah", "sudah", "juga", "sebagai",
    "agar", "supaya", "karena", "jika", "kalau", "tetapi", "tapi", "namun",
    "sehingga", "oleh", "para", "saat", "ketika", "saja", "pun", "lagi",
    "lebih", "paling", "hanya", "bisa", "dapat", "harus", "tidak", "tak",
    "bukan", "ada", "tidaklah", "sebuah", "seorang", "ia", "dia", "mereka",
    "kami", "kita", "anda", "saya", "kau", "kamu", "nya", "yaitu", "yakni",
    "tersebut", "itulah", "begini", "begitu", "demikian", "antara", "kepada",
    "tentang", "bagi", "hingga", "sampai", "lalu", "kemudian",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_tokens(tokens: Sequence[str]) -> List[str]:
    return [t for t in tokens if t.isalnum() and t not in _STOPWORDS]


def _term_freq(tokens: Sequence[str]) -> Counter:
    return Counter(tokens)


def _build_idf(docs_tokens: Sequence[Sequence[str]]) -> Dict[str, float]:
    n_docs = len(docs_tokens)
    df: Dict[str, int] = {}
    for tokens in docs_tokens:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    return {
        term: math.log((n_docs + 1) / (count + 1)) + 1.0
        for term, count in df.items()
    }


def _tfidf_vector(tokens: Sequence[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = _term_freq(tokens)
    if not tf:
        return {}
    max_tf = max(tf.values())
    return {t: (0.5 + 0.5 * c / max_tf) * idf.get(t, 0.0) for t, c in tf.items()}


def _cosine(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    if not v1 or not v2:
        return 0.0
    # Iterate vector terkecil untuk efisiensi.
    if len(v1) > len(v2):
        v1, v2 = v2, v1
    dot = sum(w * v2.get(t, 0.0) for t, w in v1.items())
    n1 = math.sqrt(sum(w * w for w in v1.values()))
    n2 = math.sqrt(sum(w * w for w in v2.values()))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def _pagerank(
    sim_matrix: List[List[float]],
    damping: float = 0.85,
    epsilon: float = 1e-4,
    max_iter: int = 100,
) -> List[float]:
    n = len(sim_matrix)
    if n == 0:
        return []
    # Normalisasi baris.
    norm: List[List[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        row_sum = sum(sim_matrix[i])
        if row_sum > 0:
            for j in range(n):
                norm[i][j] = sim_matrix[i][j] / row_sum

    scores = [1.0 / n] * n
    for _ in range(max_iter):
        new_scores = [(1.0 - damping) / n] * n
        for j in range(n):
            for i in range(n):
                new_scores[j] += damping * scores[i] * norm[i][j]
        diff = sum(abs(new_scores[k] - scores[k]) for k in range(n))
        scores = new_scores
        if diff < epsilon:
            break
    return scores


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def summarize(text_or_sentences, num_sentences: int = 3) -> str:
    """Ringkas teks menggunakan TextRank.

    Argument bisa berupa string panjang atau list kalimat.
    """
    if isinstance(text_or_sentences, str):
        sentences = split_sentences(text_or_sentences)
    else:
        sentences = [s for s in text_or_sentences if s and s.strip()]

    if len(sentences) <= num_sentences:
        return " ".join(sentences)

    docs_tokens = [_filter_tokens(simple_tokenize(s)) for s in sentences]
    idf = _build_idf(docs_tokens)
    vectors = [_tfidf_vector(tokens, idf) for tokens in docs_tokens]

    n = len(sentences)
    sim: List[List[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            s = _cosine(vectors[i], vectors[j])
            sim[i][j] = s
            sim[j][i] = s

    scores = _pagerank(sim)
    ranked: List[Tuple[float, int]] = sorted(
        ((scores[i], i) for i in range(n)),
        key=lambda x: x[0],
        reverse=True,
    )
    selected_idx = sorted(idx for _, idx in ranked[:num_sentences])
    return " ".join(sentences[i] for i in selected_idx)
