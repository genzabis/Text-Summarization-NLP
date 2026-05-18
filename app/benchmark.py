"""Benchmark TextRank baseline (dan opsional Seq2Seq) terhadap IndoSum test set.

Cara pakai:
    cd app
    python -m app.benchmark --indosum-dir .. --max 500
    python -m app.benchmark --indosum-dir .. --max 500 --models textrank,seq2seq
"""

from __future__ import annotations

import argparse
import os
import sys

_PKG_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_PARENT not in sys.path:
    sys.path.insert(0, _PKG_PARENT)

from app.backend.data_utils import (  # noqa: E402
    flatten_article_text,
    flatten_summary,
    iter_jsonl_split,
)
from app.backend.rouge_eval import evaluate  # noqa: E402
from app.backend import textrank_summarizer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indosum-dir", default="..")
    parser.add_argument("--split", default="test")
    parser.add_argument("--max", type=int, default=500)
    parser.add_argument("--num-sentences", type=int, default=3)
    parser.add_argument("--models", default="textrank")
    parser.add_argument("--checkpoint", default="models/checkpoints/seq2seq_best.pt")
    parser.add_argument("--vocab", default="models/checkpoints/vocab.json")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print(f"[info] benchmarking models: {models}")

    articles, refs = [], []
    for i, item in enumerate(iter_jsonl_split(args.indosum_dir, args.split)):
        if i >= args.max:
            break
        articles.append(flatten_article_text(item.get("paragraphs", [])))
        refs.append(flatten_summary(item.get("summary", [])))
    print(f"[info] eval samples: {len(articles)}")

    if "textrank" in models:
        preds = [textrank_summarizer.summarize(a, args.num_sentences) for a in articles]
        scores = evaluate(preds, refs)
        print("[textrank]", scores)

    if "seq2seq" in models:
        from app.backend.seq2seq_summarizer import Seq2SeqSummarizer

        s2s = Seq2SeqSummarizer(args.checkpoint, args.vocab)
        if not s2s.is_ready():
            print("[seq2seq] checkpoint belum tersedia; lewati.")
        else:
            preds = [s2s.summarize(a) for a in articles]
            scores = evaluate(preds, refs)
            print("[seq2seq]", scores)


if __name__ == "__main__":
    main()
