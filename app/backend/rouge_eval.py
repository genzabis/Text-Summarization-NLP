"""ROUGE evaluation berbasis rouge-score.

Dipakai oleh script benchmarking untuk membandingkan hasil model terhadap
gold summary IndoSum.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

try:
    from rouge_score import rouge_scorer
except ImportError:  # pragma: no cover
    rouge_scorer = None  # type: ignore[assignment]


def get_scorer():
    if rouge_scorer is None:
        raise ImportError(
            "Package rouge-score belum terpasang. Jalankan: pip install rouge-score"
        )
    return rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=False)


def evaluate(
    predictions: Iterable[str],
    references: Iterable[str],
) -> Dict[str, float]:
    """Hitung rata-rata ROUGE F1 antara prediction dan reference."""
    scorer = get_scorer()
    totals = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
    n = 0
    for pred, ref in zip(predictions, references):
        scores = scorer.score(ref, pred)
        for k in totals:
            totals[k] += scores[k].fmeasure
        n += 1
    if n == 0:
        return totals
    return {k: round(v / n, 4) for k, v in totals.items()}


def per_sample(predictions: List[str], references: List[str]) -> List[Dict[str, float]]:
    scorer = get_scorer()
    out: List[Dict[str, float]] = []
    for pred, ref in zip(predictions, references):
        s = scorer.score(ref, pred)
        out.append({k: round(v.fmeasure, 4) for k, v in s.items()})
    return out
