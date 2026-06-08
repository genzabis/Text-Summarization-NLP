# Text Summarization NLP — IndoSum

Aplikasi peringkas teks Bahasa Indonesia berbasis dataset **IndoSum**, dengan tiga pendekatan dalam satu antarmuka: TextRank (baseline), Seq2Seq (abstraktif), dan Google Gemini API (LLM).

| Model | Tipe | Catatan |
|------|------|---------|
| **TextRank** | Extractive (baseline) | Implementasi sendiri (TF-IDF + cosine + PageRank) |
| **Seq2Seq** | Abstractive | Model sequence-to-sequence dengan Bahdanau Attention (lokal/mocked) |
| **Google Gemini API** | Abstractive (LLM) | Dijalankan melalui Google Generative AI / API gateway custom |

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

## Audit Kesiapan Deploy VPS

Status saat audit: **siap dideploy ke VPS dengan Docker Compose**.

Yang sudah tersedia untuk deployment:

- `Dockerfile` memakai `python:3.11-slim` dan menjalankan aplikasi via **Gunicorn**.
- `docker-compose.yml` expose aplikasi di port `5000` dan restart otomatis `unless-stopped`.
- Frontend statis (`app/frontend`) diserve langsung oleh Flask, jadi tidak perlu Node.js/Nginx khusus untuk build frontend.
- Dataset IndoSum `.jsonl` sudah berada di root repo dan `INDOSUM_DIR=/app` sudah cocok untuk container.
- Endpoint health/status tersedia di `/api/status`.

Catatan penting sebelum deploy:

- File checkpoint asli Seq2Seq `models/checkpoints/seq2seq_best.pt` **belum ada** di repo saat audit. Yang ada baru `vocab.json`.
  - Model **TextRank** tetap bisa jalan tanpa checkpoint.
  - Model **Gemini** bisa jalan kalau `GEMINI_API_KEY` diisi.
  - Model **Seq2Seq** akan error `503` kalau checkpoint belum tersedia dan Gemini API key tidak diisi.
- Ukuran repo cukup besar karena dataset IndoSum ikut masuk Docker image. Pastikan VPS punya ruang disk cukup.
- Untuk akses publik, minimal buka port `5000`, atau lebih direkomendasikan pasang Nginx reverse proxy + HTTPS.

Rekomendasi minimal VPS:

| Kebutuhan | Rekomendasi |
|---|---|
| OS | Ubuntu 22.04 / 24.04 LTS |
| CPU | 2 vCPU atau lebih |
| RAM | Minimal 2 GB, rekomendasi 4 GB kalau pakai Torch/Seq2Seq |
| Disk | Minimal 10 GB kosong untuk repo, image Docker, dataset, dan cache |
| Runtime | Docker Engine + Docker Compose plugin |

## Cara Deploy ke VPS

Panduan ini diasumsikan memakai Ubuntu VPS dan Docker Compose.

### 1. Masuk ke VPS

```bash
ssh username@IP_VPS
```

Ganti `username` dan `IP_VPS` sesuai data VPS kamu.

### 2. Install Docker dan Compose Plugin

Kalau Docker belum ada di VPS:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

Opsional biar bisa jalanin Docker tanpa `sudo`:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Cek instalasi:

```bash
docker --version
docker compose version
```

### 3. Upload / Clone Project

Kalau repo sudah ada di GitHub/GitLab:

```bash
git clone URL_REPO_KAMU Text-Summarization-NLP
cd Text-Summarization-NLP
```

Kalau belum pakai Git, upload folder project ke VPS pakai `scp` atau SFTP.

### 4. Siapkan File Environment

Buat file `.env` dari contoh:

```bash
cp app/.env.example app/.env
nano app/.env
```

Isi minimal seperti ini:

```env
GEMINI_API_KEY=isi_api_key_gemini_kamu
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False
INDOSUM_DIR=/app
SEQ2SEQ_CHECKPOINT=/app/models/checkpoints/seq2seq_best.pt
SEQ2SEQ_VOCAB=/app/models/checkpoints/vocab.json
```

Kalau belum punya Gemini API key, kosongkan saja `GEMINI_API_KEY`, tapi fitur Gemini tidak akan aktif.

### 5. Siapkan Checkpoint Seq2Seq Jika Ada

Kalau kamu punya model hasil training, upload file checkpoint ke:

```text
models/checkpoints/seq2seq_best.pt
```

Struktur akhirnya:

```text
models/checkpoints/
├── seq2seq_best.pt
└── vocab.json
```

Kalau checkpoint belum ada, aplikasi tetap bisa deploy, tapi gunakan model `TextRank` atau `Gemini`.

### 6. Build dan Jalankan Container

Dari folder root project:

```bash
docker compose up -d --build
```

Cek status container:

```bash
docker compose ps
docker compose logs -f indosum-summarizer
```

### 7. Test Aplikasi

Test endpoint status:

```bash
curl http://localhost:5000/api/status
```

Test ringkas pakai TextRank:

```bash
curl -X POST http://localhost:5000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"text":"Presiden menyampaikan kebijakan baru untuk meningkatkan kualitas pendidikan di Indonesia. Program ini akan diterapkan secara bertahap di berbagai daerah.","model":"textrank","num_sentences":2}'
```

Kalau dari browser, buka:

```text
http://IP_VPS:5000
```

### 8. Buka Firewall VPS

Kalau memakai UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 5000/tcp
sudo ufw enable
sudo ufw status
```

Pastikan juga security group/firewall dari provider VPS membuka port `5000`.

### 9. Update Aplikasi Setelah Ada Perubahan

```bash
git pull
docker compose up -d --build
```

### 10. Perintah Operasional Penting

```bash
# Lihat log
docker compose logs -f indosum-summarizer

# Restart aplikasi
docker compose restart indosum-summarizer

# Stop aplikasi
docker compose down

# Rebuild dari nol
docker compose build --no-cache
docker compose up -d
```

## Opsional: Reverse Proxy Nginx + Domain

Kalau kamu punya domain dan ingin akses tanpa `:5000`, pasang Nginx di VPS:

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/indosum
```

Isi konfigurasi berikut, ganti `domainkamu.com`:

```nginx
server {
    listen 80;
    server_name domainkamu.com www.domainkamu.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Aktifkan config:

```bash
sudo ln -s /etc/nginx/sites-available/indosum /etc/nginx/sites-enabled/indosum
sudo nginx -t
sudo systemctl reload nginx
```

Untuk HTTPS gratis:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d domainkamu.com -d www.domainkamu.com
```

## Anggota Kelompok

- Atika Andrian Asmiran (234110601056)
- Fatiyatul Amelia (234110601065)
- Fikri Nofan Dwi Andika (234110601067)
- Niamilah Nabil Syahputra (234110601087)
- Novian Affan Ashofah (234110601088)
