# IndoSum Text Summarizer

Aplikasi peringkas teks Bahasa Indonesia berbasis dataset **IndoSum**, dengan tiga
pendekatan dalam satu antarmuka:

| Model                   | Tipe                      | Catatan                                                  |
| ----------------------- | ------------------------- | -------------------------------------------------------- |
| **TextRank**            | Extractive (baseline)     | Implementasi sendiri (TF-IDF + cosine + PageRank)        |
| **Seq2Seq + Attention** | Abstractive (model utama) | Encoder GRU bidirectional + Bahdanau attention (PyTorch) |
| **Google Gemini API**   | Abstractive (LLM)         | `gemini-1.5-flash` via `google-generativeai`             |

## Struktur Folder

```
indosum/
├── train.01.jsonl ... test.05.jsonl   <- dataset IndoSum (sudah ada)
└── app/
    ├── backend/
    │   ├── app.py                     <- Flask server + REST API
    │   ├── data_utils.py              <- loader & preprocess IndoSum
    │   ├── textrank_summarizer.py     <- baseline TextRank
    │   ├── seq2seq_summarizer.py      <- wrapper inferensi Seq2Seq
    │   ├── gemini_summarizer.py       <- wrapper Gemini API
    │   └── rouge_eval.py              <- ROUGE F1
    ├── models/
    │   ├── seq2seq.py                 <- arsitektur Seq2Seq + Attention
    │   ├── vocab.py                   <- tokenizer & vocab
    │   └── checkpoints/               <- otomatis dibuat saat training
    ├── frontend/
    │   ├── index.html
    │   ├── styles.css
    │   └── app.js
    ├── train.py                       <- script latih Seq2Seq
    ├── benchmark.py                   <- ROUGE benchmark di test set
    ├── requirements.txt
    └── .env.example
```

## Quick Start

```bash
# 1. install dependency (gunakan venv bila perlu)
pip install -r app/requirements.txt

# 2. setup env (Gemini opsional)
cp app/.env.example app/.env          # Windows: copy app\.env.example app\.env
# isi GEMINI_API_KEY pada file app/.env

# 3. jalankan server
python -m app.backend.app

# 4. buka http://127.0.0.1:5000
```

> **Catatan:** TextRank dan Gemini bisa langsung dipakai. Untuk model Seq2Seq,
> butuh training dulu (lihat bagian berikut).

## Training Model Seq2Seq

```bash
# subset cepat (CPU friendly, ~beberapa menit per epoch)
python -m app.train --indosum-dir . --epochs 3 --max-train 5000 --max-val 500

# full training (idealnya pakai GPU)
python -m app.train --indosum-dir . --epochs 10 --max-train 50000 --max-val 2000
```

Hyper-parameter penting:

- `--max-src-len 400` panjang maksimum artikel (token)
- `--max-tgt-len 80` panjang maksimum ringkasan (token)
- `--emb-dim 128 --hidden-dim 256` ukuran model
- `--batch-size 16 --lr 1e-3 --teacher-forcing 0.85`
- `--resume` lanjutkan dari checkpoint terakhir (vocab + bobot di-load ulang)

Checkpoint terbaik (val loss) disimpan ke
`app/models/checkpoints/seq2seq_best.pt` bersama `vocab.json`. Setelah ini,
endpoint Seq2Seq otomatis aktif di server.

Contoh resume training (lanjut dari yang sudah ada):

```bash
python -m app.train --resume --epochs 3 --max-train 4000 --lr 5e-4
```

> **Catatan kualitas Seq2Seq di CPU:** training Seq2Seq+Bahdanau attention
> sangat berat di CPU. Dengan 2000 sampel × 4 epoch model masih
> _under-fit_ dan sering memprediksi `<unk>` atau token yang sangat sering
> muncul. Untuk ROUGE yang kompetitif (mendekati TextRank ~0.42), butuh
> minimal 30000+ sampel × 10+ epoch di GPU. Endpoint TextRank dan Gemini
> tetap berkualitas baik tanpa training.

## Benchmark ROUGE

Reproduksi baseline TextRank pada test set:

```bash
python -m app.benchmark --indosum-dir . --max 500
```

Bandingkan TextRank vs Seq2Seq:

```bash
python -m app.benchmark --indosum-dir . --max 500 --models textrank,seq2seq
```

## REST API

| Method | Endpoint                         | Body                                         | Deskripsi                 |
| ------ | -------------------------------- | -------------------------------------------- | ------------------------- |
| GET    | `/api/status`                    | –                                            | Status seluruh summarizer |
| POST   | `/api/summarize`                 | `{ text, model, num_sentences, reference? }` | Ringkas teks              |
| GET    | `/api/sample?split=test&index=0` | –                                            | Ambil sample IndoSum      |
| POST   | `/api/evaluate`                  | `{ prediction, reference }`                  | Hitung ROUGE              |

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
