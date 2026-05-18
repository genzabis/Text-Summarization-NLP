"""Flask backend untuk aplikasi Text Summarization IndoSum.

Endpoint:
    GET  /                     -> serve halaman index frontend
    GET  /api/status           -> status semua summarizer
    POST /api/summarize        -> ringkas teks via model yang dipilih
    GET  /api/sample           -> ambil sample artikel dari IndoSum test split
    POST /api/evaluate         -> hitung ROUGE bila reference disediakan
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Pastikan paket `app` bisa di-import saat dijalankan langsung.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_BACKEND_DIR)
_ROOT_DIR = os.path.dirname(_APP_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from app.backend import textrank_summarizer  # noqa: E402
from app.backend.data_utils import (  # noqa: E402
    flatten_article_text,
    flatten_summary,
    iter_jsonl_split,
)
from app.backend.gemini_summarizer import GeminiSummarizer  # noqa: E402
from app.backend.rouge_eval import evaluate  # noqa: E402
from app.backend.seq2seq_summarizer import Seq2SeqSummarizer  # noqa: E402


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv(os.path.join(_APP_DIR, ".env"))

FRONTEND_DIR = os.path.join(_APP_DIR, "frontend")

# Path resolusi: relatif terhadap folder app/
def _resolve(p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(_APP_DIR, p))


INDOSUM_DIR = _resolve(os.getenv("INDOSUM_DIR", ".."))
SEQ2SEQ_CKPT = _resolve(os.getenv("SEQ2SEQ_CHECKPOINT", "models/checkpoints/seq2seq_best.pt"))
SEQ2SEQ_VOCAB = _resolve(os.getenv("SEQ2SEQ_VOCAB", "models/checkpoints/vocab.json"))

gemini = GeminiSummarizer()
seq2seq = Seq2SeqSummarizer(SEQ2SEQ_CKPT, SEQ2SEQ_VOCAB)

app = Flask(__name__, static_folder=None)
CORS(app)


# ---------------------------------------------------------------------------
# Frontend serving
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename: str):
    full = os.path.join(FRONTEND_DIR, filename)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, filename)
    # SPA-friendly fallback ke index.
    return send_from_directory(FRONTEND_DIR, "index.html")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "textrank": {"ready": True},
        "seq2seq": seq2seq.status(),
        "gemini": gemini.status(),
        "indosum_dir": INDOSUM_DIR,
    })


@app.route("/api/summarize", methods=["POST"])
def summarize():
    data = request.get_json(silent=True) or {}
    text: str = (data.get("text") or "").strip()
    model: str = (data.get("model") or "textrank").lower()
    n: int = int(data.get("num_sentences") or 3)
    reference: Optional[str] = data.get("reference") or None

    if not text:
        return jsonify({"error": "Field 'text' kosong."}), 400
    if n < 1:
        n = 1
    if n > 10:
        n = 10

    try:
        if model == "textrank":
            summary = textrank_summarizer.summarize(text, n)
        elif model == "seq2seq":
            if not seq2seq.is_ready():
                return jsonify({
                    "error": (
                        "Model Seq2Seq belum dilatih. Jalankan `python -m app.train` "
                        "untuk menghasilkan checkpoint, atau gunakan model lain."
                    ),
                }), 503
            summary = seq2seq.summarize(text)
        elif model == "gemini":
            if not gemini.is_ready():
                return jsonify({
                    "error": (
                        "Gemini API belum di-set. Tambahkan GEMINI_API_KEY pada file .env "
                        "lalu restart server."
                    ),
                }), 503
            summary = gemini.summarize(text, n_sentences=n)
        else:
            return jsonify({"error": f"Model '{model}' tidak dikenal."}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Gagal meringkas: {exc}"}), 500

    payload = {
        "model": model,
        "num_sentences": n,
        "summary": summary,
        "stats": {
            "input_chars": len(text),
            "input_words": len(text.split()),
            "summary_chars": len(summary),
            "summary_words": len(summary.split()),
            "compression": (
                round(len(summary.split()) / max(len(text.split()), 1), 3)
            ),
        },
    }

    if reference:
        try:
            payload["rouge"] = evaluate([summary], [reference])
        except Exception as exc:  # noqa: BLE001
            payload["rouge_error"] = str(exc)

    return jsonify(payload)


@app.route("/api/sample", methods=["GET"])
def sample():
    """Ambil 1 sample artikel + gold summary dari split tertentu."""
    split = request.args.get("split", "test")
    try:
        index = int(request.args.get("index", "0"))
    except ValueError:
        index = 0
    if index < 0:
        index = 0

    found = None
    for i, item in enumerate(iter_jsonl_split(INDOSUM_DIR, split)):
        if i == index:
            found = item
            break

    if not found:
        return jsonify({"error": f"Tidak menemukan sample index {index} pada split '{split}'."}), 404

    article = flatten_article_text(found.get("paragraphs", []))
    gold = flatten_summary(found.get("summary", []))
    return jsonify({
        "split": split,
        "index": index,
        "id": found.get("id"),
        "category": found.get("category"),
        "source": found.get("source"),
        "source_url": found.get("source_url"),
        "article": article,
        "gold_summary": gold,
    })


@app.route("/api/evaluate", methods=["POST"])
def evaluate_route():
    data = request.get_json(silent=True) or {}
    pred = data.get("prediction") or ""
    ref = data.get("reference") or ""
    if not pred or not ref:
        return jsonify({"error": "Field 'prediction' dan 'reference' wajib."}), 400
    try:
        scores = evaluate([pred], [ref])
        return jsonify({"rouge": scores})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in {"1", "true", "yes"}
    print(f"[server] http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
