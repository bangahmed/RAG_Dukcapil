# DUKCAPIL-Pintar: Prototipe RAG v1

Asisten generatif berbasis Retrieval-Augmented Generation untuk panduan persyaratan dokumen kependudukan. Setiap jawaban disusun **hanya dari teks regulasi nasional** dan menyebut pasal rujukannya.

Tugas mata kuliah Introduction to Generative AI, Magister Kecerdasan Buatan, Universitas Dian Nuswantoro.

Anggota kelompok:

| No | Nama | NIM |
|----|------|-----|
| 1 | Arif Alamsah | P36.2026.00055 |
| 2 | Djoko Purnomo | P36.2026.00046 |
| 3 | Efendy Aprianto | P36.2026.00042 |
| 4 | Akhmadi | P36.2026.00001 |

## Arsitektur

```
OFFLINE  (scripts/build-index.py)
  PDF regulasi → ekstrak teks → chunk per pasal → embedding lokal → indeks FAISS

ONLINE   (app.py)
  pertanyaan → [Sonnet 5.5] tulis ulang kueri (opsional)
             → embed lokal → FAISS top-k
             → [Groq gpt-oss-120b | Haiku 5.5] jawab hanya dari konteks + rujukan pasal

EVALUASI (scripts/run-evaluation.py)
  set uji → pipeline → [Sonnet 5.5 sebagai juri] → CSV hasil + ringkasan
```

| Peran | Model |
|---|---|
| Penjawab utama (default) | Groq `openai/gpt-oss-120b` |
| Penjawab pembanding / cadangan | Anthropic Claude Haiku 5.5 |
| Juri evaluasi, penulis ulang kueri | Anthropic Claude Sonnet 5.5 |
| Embedding | Lokal, sentence-transformers `paraphrase-multilingual-mpnet-base-v2` |

Anthropic dipakai sebagai pengganti Gemini (penyedia yang disebut RPS). Groq tetap jalur generasi utama sesuai ketentuan RTM 2.

Diagram alur lengkap (pembuatan indeks, satu pertanyaan, rate limit dan model cadangan, evaluasi dan iterasi) ada di [docs/alur-kerja.md](docs/alur-kerja.md).

## Struktur

```
app.py                     halaman Streamlit (tata letak ala halaman Ask CICADA)
dukcapil_pintar/           paket inti
  config.py                path, parameter RAG, daftar model, pembaca secret
  ingestion.py             baca PDF/TXT → teks per halaman
  chunking.py              pecah per pasal + metadata
  embedding.py             embedding lokal
  retrieval.py             indeks FAISS + pencarian
  prompts.py               prompt penjawab, tulis ulang, juri (berversi)
  providers.py             klien Groq & Anthropic + retry
  generation.py            tulis ulang kueri, susun jawaban
  pipeline.py              alur end-to-end (dipakai app dan evaluasi)
  ui.py                    komponen tampilan
  formatting.py            format angka gaya Indonesia
scripts/
  build-index.py           --only extract,chunk,embed,index
  run-evaluation.py        --only generate,judge,report
  smoke-test-providers.py  cek API key dan ID model
data/sources.csv           13 regulasi + tautan resmi
evals/                     set uji, metodologi, catatan iterasi, hasil per putaran
docs/                      diagram alur kerja (Mermaid)
tests/                     unit test chunking, provider (retry, rate limit), pipeline, dan fusi retrieval
```

## Persiapan

Butuh Python 3.11 atau lebih baru; versi pustaka di `requirements.txt` dipatok dari Python 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # lalu isi API key
python scripts/smoke-test-providers.py
```

Setiap anggota kelompok memakai akun Groq sendiri, karena kuota tier gratis berlaku per akun/organisasi.

## Menyiapkan korpus dan indeks

1. Unduh dokumen dari kolom `source_url` di `data/sources.csv`, simpan di `data/raw/` dengan nama persis seperti kolom `file_name`. Dokumen hasil OCR boleh berupa `.txt` (pisah halaman dengan karakter form feed bila ada).
2. Bangun indeks:
   ```bash
   python scripts/build-index.py
   ```
   Bandingkan total karakter dengan Submission Minggu 2 (±903.000) dan periksa jumlah pasal per dokumen.

## Menjalankan aplikasi

```bash
streamlit run app.py
```

## Evaluasi

1. Set uji ada di `evals/test_set.jsonl` (14 pertanyaan). Format `evals/test_set_template.jsonl` untuk menambah pertanyaan; verifikasi setiap `expected_articles` (format `document_id:Pasal N`) langsung ke teks korpus.
2. Jalankan putaran awal:
   ```bash
   python scripts/run-evaluation.py --run-name baseline
   ```
3. Ubah satu parameter lewat variabel lingkungan, lalu jalankan putaran baru, misalnya:
   ```bash
   set DUKCAPIL_TOP_K=6                 # macOS/Linux: export DUKCAPIL_TOP_K=6
   python scripts/run-evaluation.py --run-name top-k-6 --reuse-rewrites-from baseline
   ```
   `--reuse-rewrites-from` memakai kueri tulis ulang dari putaran pembanding. Penulis ulang
   kueri tidak deterministik, jadi tanpa opsi ini retrieval ikut berubah antarputaran dan
   mengacaukan perbandingan.
4. Catat perbandingannya di `evals/iteration_log.md`.

Bila terhenti karena rate limit, jalankan ulang perintah yang sama: pertanyaan yang sudah selesai dilewati.

Parameter yang bisa diubah: `DUKCAPIL_TOP_K`, `DUKCAPIL_QUERY_REWRITE`, `DUKCAPIL_FUSION` (`max_score` atau `rrf`), `DUKCAPIL_EMBEDDING_MODEL`, `DUKCAPIL_MAX_CHUNK_CHARS`, `DUKCAPIL_CHUNK_OVERLAP_CHARS`, `DUKCAPIL_ANSWER_MAX_TOKENS`, `DUKCAPIL_GROQ_MODEL`, `DUKCAPIL_HAIKU_MODEL`, `DUKCAPIL_SONNET_MODEL`. Mengganti model embedding atau ukuran chunk mewajibkan `build-index.py` dijalankan ulang.

## Deploy ke Streamlit Community Cloud

1. Pastikan `data/index/faiss.index` dan `data/index/chunk_metadata.jsonl` ikut di-commit, dan `.streamlit/secrets.toml` **tidak** ikut.
2. Push ke GitHub, lalu di Streamlit Community Cloud pilih New app → repo, branch, `app.py`.
3. Di Advanced settings → Secrets, tempel `GROQ_API_KEY` dan `ANTHROPIC_API_KEY`.
4. Pasang batas pengeluaran di Anthropic Console karena aplikasi publik memakai API key Anda.
5. Pilih Python 3.13 di Advanced settings agar cocok dengan versi pustaka yang dipatok. Model
   embedding mpnet (±1,1 GB) diunduh saat start pertama. Puncak memori terukur lokal ±1,9 GB
   dari batas ±2,7 GB (dokumen Streamlit, Feb 2024), jadi **uji deploy lebih awal**. Bila
   melewati batas, ganti ke MiniLM: set `DUKCAPIL_EMBEDDING_MODEL` dan jalankan ulang
   `scripts/build-index.py` (indeks harus dibangun dengan model yang sama).

## Yang perlu diverifikasi

- ID model aktif tiap provider (`smoke-test-providers.py`).
- Model Anthropic terbaru (Sonnet 5.5) menolak parameter `temperature`, sehingga juri tidak berjalan pada suhu 0; skor juri bisa bervariasi antarputaran (lihat keterbatasan di `evals/evaluation_methodology.md`).
- Batas memori Streamlit Community Cloud terhadap mpnet (lihat bagian deploy); belum diuji di server sungguhan.
- Batas laju Groq tier gratis di halaman limits akun Anda, untuk menentukan `--pause-s`.

## Konvensi kode

Identifier berbahasa Inggris; docstring dan komentar berbahasa Indonesia; skrip yang dijalankan langsung bernama `kebab-case.py` di `scripts/`; langkah skrip `step_<nama>` sama dengan pilihan `--only`. Periksa dengan:

```bash
ruff check .
pytest
```
