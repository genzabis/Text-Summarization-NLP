# IndoSum Text Summarizer

Aplikasi peringkas teks Bahasa Indonesia berbasis dataset **IndoSum**, dengan tiga pendekatan dalam satu antarmuka: TextRank (baseline), Seq2Seq (abstraktif), dan Google Gemini API (LLM).

| Model | Tipe | Catatan |
|------|------|---------|
| **TextRank** | Extractive (baseline) | Implementasi sendiri (TF-IDF + cosine + PageRank) |
| **Seq2Seq** | Abstractive | Model sequence-to-sequence dengan Bahdanau Attention (lokal/mocked) |
| **Google Gemini API** | Abstractive (LLM) | Dijalankan melalui Google Generative AI / API gateway custom |

## Struktur Folder

```
indosum/
├── train.01.jsonl ... test.05.jsonl   <- dataset IndoSum (sudah ada)
└── app/
    ├── backend/
    │   ├── app.py                     <- Flask server + REST API
    │   ├── data_utils.py              <- loader & preprocess IndoSum
    │   ├── textrank_summarizer.py     <- baseline TextRank
    │   ├── seq2seq_summarizer.py      <- model Seq2Seq + Bahdanau
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

## Deploy ke VPS dengan Docker

Konfigurasi Docker tersedia di root project:

- `Dockerfile` untuk build image aplikasi Flask + frontend statis.
- `docker-compose.yml` untuk menjalankan container di VPS.
- `.dockerignore` untuk mengecilkan build context dan menjaga `.env` tidak ikut masuk image.

File `app/.env` bersifat opsional untuk TextRank, tapi tetap disarankan dibuat di VPS supaya konfigurasi environment jelas. Jika file ini tidak ada, container tetap memakai default environment dari `docker-compose.yml`.

### 1. Persiapan di VPS

Install Docker dan plugin Compose di VPS, lalu clone/copy project ini ke server:

```bash
git clone https://github.com/genzabis/Text-Summarization-NLP.git
cd Text-Summarization-NLP
```

Kalau project sudah ada di VPS, cukup masuk ke folder project dan pull versi terbaru:

```bash
git pull
```

### 2. Setup environment

```bash
cp app/.env.example app/.env
nano app/.env
```

Minimal pastikan konfigurasi server seperti ini:

```env
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False
INDOSUM_DIR=/app
SEQ2SEQ_CHECKPOINT=/app/models/checkpoints/seq2seq_best.pt
SEQ2SEQ_VOCAB=/app/models/checkpoints/vocab.json
```

Jika ingin memakai Gemini, isi juga:

```env
GEMINI_API_KEY=isi_api_key_gemini
```

> Catatan: file `app/.env` tidak dimasukkan ke image Docker dan jangan di-commit ke Git.

### 3. Build dan jalankan container

```bash
docker compose --env-file app/.env up -d --build
```

Kalau belum butuh Gemini dan tidak membuat `app/.env`, jalankan:

```bash
docker compose up -d --build
```

Cek status dan log:

```bash
docker compose ps
docker compose logs -f indosum-summarizer
```

Aplikasi akan tersedia di:

```text
http://IP_VPS:5000
```

### 4. Update aplikasi di VPS

```bash
git pull
docker compose --env-file app/.env up -d --build
```

### 5. Stop aplikasi

```bash
docker compose down
```

### Opsional: reverse proxy domain

Jika punya domain, arahkan domain ke IP VPS lalu pasang Nginx/Caddy sebagai reverse proxy dari port `80/443` ke container `127.0.0.1:5000`.

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

## Anggota Kelompok

- Atika Andrian Asmiran (234110601056)
- Fatiyatul Amelia (234110601065)
- Fikri Nofan Dwi Andika (234110601067)
- Niamilah Nabil Syahputra (234110601087)
- Novian Affan Ashofah (234110601088)
