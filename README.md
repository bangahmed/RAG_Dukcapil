# DUKCAPIL-Pintar: Prototipe RAG v1

Asisten generatif berbasis *Retrieval-Augmented Generation* (RAG) untuk panduan persyaratan dokumen kependudukan. Setiap jawaban disusun **hanya berdasarkan teks regulasi nasional** dan menyebutkan pasal rujukannya.

Aplikasi daring: <https://dukcapil-pintar.streamlit.app>

Tugas mata kuliah Introduction to Generative AI, Magister Kecerdasan Buatan, Universitas Dian Nuswantoro.

Anggota kelompok:

| No | Nama            | NIM            |
| -- | --------------- | -------------- |
| 1  | Arif Alamsah    | P36.2026.00055 |
| 2  | Djoko Purnomo   | P36.2026.00046 |
| 3  | Efendy Aprianto | P36.2026.00042 |
| 4  | Akhmadi         | P36.2026.00001 |

## Arsitektur

```text
LURING   (scripts/build-index.py)
  PDF regulasi → ekstraksi teks → chunk per pasal → embedding lokal → indeks FAISS

DARING   (app.py)
  pertanyaan → [Sonnet 5.5] penulisan ulang kueri (opsional)
             → embedding lokal → FAISS top-k
             → [Groq gpt-oss-120b | Haiku 5.5] menjawab hanya dari konteks + rujukan pasal

EVALUASI (scripts/run-evaluation.py)
  set uji → pipeline → [Sonnet 5.5 sebagai juri] → CSV hasil + ringkasan
```

| Peran                                 | Model                                                                |
| ------------------------------------- | -------------------------------------------------------------------- |
| Penjawab utama (bawaan)               | Groq `openai/gpt-oss-120b`                                           |
| Penjawab pembanding dan cadangan      | Anthropic Claude Haiku 5.5                                           |
| Juri evaluasi dan penulis ulang kueri | Anthropic Claude Sonnet 5.5                                          |
| Embedding                             | Lokal, sentence-transformers `paraphrase-multilingual-mpnet-base-v2` |

Anthropic digunakan sebagai pengganti Gemini (penyedia yang disebutkan dalam RPS). Groq tetap menjadi jalur generasi utama sesuai ketentuan RTM 2.

Diagram alur lengkap (pembuatan indeks, penanganan satu pertanyaan, pembatasan laju dan model cadangan, serta evaluasi dan iterasi) tersedia pada [docs/alur-kerja.md](docs/alur-kerja.md).

## Struktur

```text
app.py                     halaman utama aplkasi (Streamlit)
dukcapil_pintar/           paket inti
  config.py                lokasi berkas, parameter RAG, daftar model, pembaca secret
  ingestion.py             membaca PDF/TXT → teks per halaman
  chunking.py              memecah per pasal + metadata
  embedding.py             embedding lokal
  retrieval.py             indeks FAISS + pencarian
  prompts.py               prompt penjawab, penulis ulang, dan juri (berversi)
  providers.py             klien Groq dan Anthropic + percobaan ulang
  generation.py            penulisan ulang kueri, penyusunan jawaban
  pipeline.py              alur menyeluruh (digunakan oleh aplikasi dan evaluasi)
  ui.py                    komponen tampilan
  formatting.py            format angka gaya Indonesia
scripts/
  build-index.py           --only extract,chunk,embed,index
  run-evaluation.py        --only generate,judge,report
  smoke-test-providers.py  pemeriksaan API key dan ID model
data/sources.csv           13 regulasi + tautan resmi
evals/                     set uji, metodologi, catatan iterasi, hasil per putaran
docs/                      diagram alur kerja (Mermaid)
tests/                     uji unit chunking, provider (percobaan ulang, pembatasan laju), pipeline, dan fusi retrieval
```

## Persiapan

Diperlukan Python 3.11 atau yang lebih baru; versi pustaka pada `requirements.txt` ditetapkan berdasarkan Python 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # kemudian isi API key
python scripts/smoke-test-providers.py
```

Setiap anggota kelompok menggunakan akun Groq masing-masing karena kuota tingkat gratis berlaku per akun atau organisasi.

## Penyiapan korpus dan indeks

1. Unduh dokumen dari kolom `source_url` pada `data/sources.csv`, lalu simpan di `data/raw/` dengan nama yang persis sama dengan kolom `file_name`. Dokumen hasil OCR dapat berupa berkas `.txt` (halaman dipisahkan dengan karakter *form feed* apabila ada).
2. Bangun indeks:

   ```bash
   python scripts/build-index.py
   ```

   Bandingkan total karakter dengan Submission Minggu 2 (±903.000) dan periksa jumlah pasal pada setiap dokumen.

## Menjalankan aplikasi

```bash
streamlit run app.py
```

## Evaluasi

1. Set uji tersedia pada `evals/test_set.jsonl` (14 pertanyaan). Format `evals/test_set_template.jsonl` dapat digunakan untuk menambah pertanyaan; setiap `expected_articles` (format `document_id:Pasal N`) harus diverifikasi langsung terhadap teks korpus.
2. Jalankan putaran awal:

   ```bash
   python scripts/run-evaluation.py --run-name baseline
   ```

3. Ubah satu parameter melalui variabel lingkungan, kemudian jalankan putaran baru, misalnya:

   ```bash
   set DUKCAPIL_TOP_K=6                 # macOS/Linux: export DUKCAPIL_TOP_K=6
   python scripts/run-evaluation.py --run-name top-k-6 --reuse-rewrites-from baseline
   ```

   Opsi `--reuse-rewrites-from` memakai kembali kueri tulis ulang dari putaran pembanding.
   Penulis ulang kueri tidak deterministik sehingga tanpa opsi ini hasil retrieval ikut
   berubah antarputaran dan mengganggu keabsahan perbandingan.
4. Catat hasil perbandingan pada `evals/iteration_log.md`.

Apabila proses terhenti akibat pembatasan laju (*rate limit*), jalankan kembali perintah yang sama: pertanyaan yang telah selesai akan dilewati.

Parameter yang dapat diubah: `DUKCAPIL_TOP_K`, `DUKCAPIL_QUERY_REWRITE`, `DUKCAPIL_FUSION` (`max_score` atau `rrf`), `DUKCAPIL_EMBEDDING_MODEL`, `DUKCAPIL_MAX_CHUNK_CHARS`, `DUKCAPIL_CHUNK_OVERLAP_CHARS`, `DUKCAPIL_ANSWER_MAX_TOKENS`, `DUKCAPIL_GROQ_MODEL`, `DUKCAPIL_HAIKU_MODEL`, dan `DUKCAPIL_SONNET_MODEL`. Perubahan model embedding atau ukuran chunk mengharuskan `build-index.py` dijalankan ulang.

## Penerapan ke Streamlit Community Cloud

1. Pastikan `data/index/faiss.index` dan `data/index/chunk_metadata.jsonl` disertakan pada *commit*, sedangkan `.streamlit/secrets.toml` **tidak** disertakan.
2. Unggah (*push*) ke GitHub, kemudian pada Streamlit Community Cloud pilih New app, lalu tentukan repositori, cabang, dan berkas `app.py`.
3. Pada Advanced settings → Secrets, masukkan `GROQ_API_KEY` dan `ANTHROPIC_API_KEY`.
4. Tetapkan batas pengeluaran pada Anthropic Console karena aplikasi publik menggunakan API key pemilik.
5. Pilih Python 3.13 pada Advanced settings agar sesuai dengan versi pustaka yang ditetapkan. Model
   embedding mpnet (±1,1 GB) diunduh pada saat awal dijalankan. Puncak pemakaian memori yang
   terukur secara lokal adalah ±1,9 GB dari batas ±2,7 GB (dokumentasi Streamlit, Februari 2024),
   sehingga **pengujian penerapan sebaiknya dilakukan sejak dini**. Apabila batas terlampaui,
   gunakan MiniLM dengan mengatur `DUKCAPIL_EMBEDDING_MODEL` dan menjalankan ulang
   `scripts/build-index.py` (indeks harus dibangun dengan model yang sama).

## Butir yang perlu diverifikasi

- ID model aktif pada setiap penyedia layanan (`smoke-test-providers.py`).
- Model Anthropic terbaru (Sonnet 5.5) menolak parameter `temperature`, sehingga juri tidak berjalan pada suhu 0 dan skor juri dapat bervariasi antarputaran (lihat keterbatasan pada `evals/evaluation_methodology.md`).
- Batas memori Streamlit Community Cloud terhadap mpnet (lihat bagian penerapan); belum diuji pada server yang sesungguhnya.
- Batas laju Groq tingkat gratis pada halaman *limits* akun masing-masing, sebagai dasar penentuan nilai `--pause-s`.

## Konvensi kode

Pengenal (*identifier*) berbahasa Inggris; docstring dan komentar berbahasa Indonesia; skrip yang dijalankan langsung bernama `kebab-case.py` pada `scripts/`; langkah skrip `step_<nama>` sama dengan pilihan `--only`. Pemeriksaan dilakukan dengan:

```bash
ruff check .
pytest
```
