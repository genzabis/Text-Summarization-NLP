# Poster A2 — IndoSum Text Summarization

Dokumentasi singkat untuk file `index.html` + `style.css` di folder `design/`.
Kedua file ini siap di-paste ke plugin **html.to.design** Figma untuk diubah
menjadi frame yang bisa di-edit lebih lanjut.

## Ukuran & Format

- Ukuran kerja: **A2 potrait** sebenarnya — `width: 420mm; min-height: 594mm`
  (didefinisikan dengan satuan mm pada `.poster`, akurat untuk cetak).
- Body grid diberi `flex: 1` dan tiap kolom `align-items: stretch` sehingga
  konten mengisi penuh tinggi A2 tanpa whitespace kosong di bawah.
- Font: Inter (display & body) + JetBrains Mono (angka & kode).
- Palet utama: biru `#2f6feb`, biru tua `#143f9d`, ungu `#8b5cf6`, hijau `#10b981`.


## Struktur Konten

| Blok                | Tujuan                                                     |
| ------------------- | ---------------------------------------------------------- |
| Header              | Logo UIN, identitas kampus, judul, dosen, anggota Kelompok 2 |
| Abstract band       | Ringkasan paragraf + 3 metrik kunci (drop-cap di awal)      |
| Card 01             | Latar Belakang & Tujuan                                     |
| Card 02             | Metode: 3 pendekatan (TextRank · Seq2Seq · Gemini)          |
| Card 03             | Dataset IndoSum + pipeline preprocessing                    |
| Card 04             | Arsitektur Seq2Seq + Bahdanau Attention                     |
| Card 05             | Mockup antarmuka aplikasi (Flask + Vanilla JS)              |
| Card 06             | Training log (loss curve SVG) + attention heatmap αₜᵢ       |
| Card 07             | Tabel ROUGE F1 + bar chart                                   |
| Card 08             | Confusion matrix + 4 metrik klasifikasi                     |
| Card 09             | Contoh prediksi (Artikel · Gold · Pred)                     |
| Card 10             | Kesimpulan + saran pengembangan                              |
| Footer              | Repo GitHub, tech stack, branding pameran                   |

## Catatan Sebelum Cetak

1. **Logo UIN** masih placeholder lingkaran biru. Ganti blok `.logo-uin`
   dengan `<img src="logo-uin.png" alt="..." />` jika sudah punya file logo
   versi PNG/SVG.
2. **Nama dosen** di header (`[Nama Dosen, M.Kom.]`) wajib diganti dengan
   nama dosen pengampu sebenarnya.
3. **Heatmap attention** menggunakan nilai αₜᵢ dummy realistis (diagonal
   menonjol). Jika punya hasil aktual dari `seq2seq.py`, tinggal isi ulang
   `style="--a:..."` di tiap `<div class="heat__cell">`.
4. **Confusion matrix** memakai angka representatif (TP 412 · FN 118 ·
   FP 156 · TN 2.314). Jika hasil eksperimen lain, ganti di Card 08.
5. **Loss curve** berbasis SVG path inline, bukan gambar. Untuk update,
   ubah koordinat `M0,18 L80,42 L160,72 L240,98 L320,120` di `<path>`.

## Mengekspor ke Figma via html.to.design

1. Buka `index.html` di browser, biarkan font Google ter-load.
2. Buka plugin **html.to.design** di Figma.
3. Pilih tab **Import as code**, paste isi `index.html`.
4. Pada tab CSS, paste isi `style.css`.
5. Atur ukuran frame Figma menjadi **A2 (1587 × 2245 px @96dpi)** atau biarkan
   plugin menyesuaikan otomatis.

6. Klik *Convert*. Plugin akan menghasilkan auto-layout frame yang bisa
   di-edit langsung di Figma.

## Print Production

- Untuk produksi cetak A2 (420 × 594 mm), export ke PDF melalui browser
  dengan setting *Paper size: A2*, *Margins: None*, *Background graphics: ON*.
- Cek bleed minimal 3 mm jika percetakan memintanya — tinggal tambahkan
  padding pada `.poster` sebesar 12px.

## Aksesibilitas Warna

- Kontras teks utama (`#0f172a` di atas `#ffffff`) lulus WCAG AAA.
- Sub-teks (`#64748b`) lulus WCAG AA pada ukuran ≥ 12 px.
- Status warna (TP hijau, FP/FN merah, TN biru) sudah diuji untuk
  protanopia/deuteranopia dengan beda saturation cukup; tidak hanya
  mengandalkan hue.

## Kredit

Konten data (skor ROUGE, hyperparameter, log training, anggota kelompok)
diambil dari `Laporan_Project_IndoSum.docx` dan `_make_report.py` pada
repo `Text-Summarization-NLP`.
