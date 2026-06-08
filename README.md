# Text Summarization NLP — IndoSum

Aplikasi peringkas teks Bahasa Indonesia berbasis dataset **IndoSum**, dengan dua pendekatan dalam satu antarmuka: TextRank (baseline) dan Claude 4.5 Sonnet / Gemini API (LLM).

| Model | Tipe | Catatan |
|------|------|---------|
| **TextRank** | Extractive (baseline) | Implementasi sendiri (TF-IDF + cosine + PageRank) |
| **Claude 4.5 Sonnet / Gemini API** | Abstractive (LLM) | Dijalankan melalui API gateway custom / Google Generative AI |

Source dataset IndoSum (Kaggle: `linkgish/indosum`) berada di root repo sebagai `train.0X.jsonl`, `dev.0X.jsonl`, dan `test.0X.jsonl`.

## Struktur Folder

```
indosum/
├── train.01.jsonl ... test.05.jsonl   <- dataset IndoSum (sudah ada)
└── app/
    ├── backend/
    │   ├── app.py                     <- Flask server + REST API
    │   ├── data_utils.py              <- loader & preprocess IndoSum
    │   ├── textrank_summarizer.py     <- baseline TextRank
    │   ├── gemini_summarizer.py       <- wrapper Gemini & Custom API (Claude)
    │   └── rouge_eval.py              <- ROUGE F1
    ├── frontend/
    │   ├── index.html
    │   ├── styles.css
    │   └── app.js
    ├── requirements.txt
    └── .env.example
```

## Quick Start

```bash
# 1. install dependency
pip install -r app/requirements.txt

# 2. setup env (API key & Endpoint custom)
cp app/.env.example app/.env          # Windows: copy app\.env.example app\.env
# isi GEMINI_API_KEY, GEMINI_BASE_URL, dan GEMINI_MODEL_NAME pada file app/.env

# 3. jalankan server
python -m app.backend.app

# 4. buka http://127.0.0.1:5000 di browser
```

## Benchmark ROUGE

Reproduksi baseline TextRank pada test set:

```bash
python -m app.benchmark --indosum-dir . --max 500
```

## REST API

| Method | Endpoint | Body | Deskripsi |
|--------|----------|------|-----------|
| GET | `/api/status` | – | Status seluruh summarizer |
| POST | `/api/summarize` | `{ text, model, num_sentences, reference? }` | Ringkas teks |
| GET | `/api/sample?split=test&index=0` | – | Ambil sample IndoSum |
| POST | `/api/evaluate` | `{ prediction, reference }` | Hitung ROUGE |

Contoh:

```bash
curl -X POST http://127.0.0.1:5000/api/summarize \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"...artikel...\",\"model\":\"textrank\",\"num_sentences\":3}"
```

## Frontend

UI berbasis HTML/CSS/JS murni (tanpa framework) dengan tema light/blue yang modern. Tab:

1. **Ringkas Teks** — paste artikel, pilih model, hitung ROUGE vs reference.
2. **Sample Dataset** — telusuri shard IndoSum dari `.jsonl` langsung.
3. **Tentang** — dokumentasi singkat.

## Tech Stack

- Python 3.10+, Flask 3, Flask-CORS
- google-generativeai (untuk default Gemini SDK)
- rouge-score, NLTK
- Frontend: HTML + CSS + Vanilla JS (Inter + JetBrains Mono)

## Anggota Kelompok

- Atika Andrian Asmiran (234110601056)
- Fatiyatul Amelia (234110601065)
- Fikri Nofan Dwi Andika (234110601067)
- Niamilah Nabil Syahputra (234110601087)
- Novian Affan Ashofah (234110601088)
