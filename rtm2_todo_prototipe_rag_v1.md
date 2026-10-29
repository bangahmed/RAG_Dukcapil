# RTM 2 — To-Do List Prototipe RAG v1: DUKCAPIL-Pintar

**Mata kuliah:** Introduction to Generative AI (P36104), Magister AI UDINUS
**Tugas:** RTM 2 — Membangun dan Mengevaluasi Prototipe RAG v1 (Sub-CPMK 2.1, bobot 15%)
**Waktu:** 2 hari (Hari 1 = bangun, Hari 2 = evaluasi + deploy + video + kumpul)
**Disusun:** 28 Okt 2026

Prioritas: **[P0]** wajib · **[P1]** menaikkan kualitas · **[P2]** hanya jika sempat.

**Prinsip prototipe: sederhana. Fokus satu hal, yaitu RAG yang menjawab sesuai dokumen, lengkap dengan rujukan pasalnya.** Tidak ada penghitungan token/kredit/kuota di aplikasi.

**Penyedia model:** Groq (jalur utama, wajib) + **Anthropic sebagai alternatif pengganti Gemini** yang disebut di RPS. Tidak memakai OpenRouter/Gemini/Ollama.

### Pembagian peran model

| Peran | Model | Catatan |
|---|---|---|
| **Penjawab utama (default selector UI)** | Groq `gpt-oss` | Wajib menurut RTM2. Cek ID model aktif di console Groq. |
| **Penjawab pembanding + cadangan saat Groq kena batas** | Anthropic Haiku 5.5 | Pilihan kedua di selector; di laporan tandai jawaban yang berasal dari cadangan. |
| **Juri evaluasi** (relevansi, faithfulness) | Anthropic Sonnet 5.5 | Berbeda dari penjawab default supaya tidak menilai jawabannya sendiri. |
| **Penulis ulang kueri** (opsional, saklar on/off) | Anthropic Sonnet 5.5 | Bisa dijadikan percobaan iterasi. |
| **Draf kandidat set uji** | Sonnet 5.5, hanya bahan | Pertanyaan akhir, kunci jawaban, dan kriteria diputuskan dan diverifikasi sendiri ke teks korpus. |
| **Embedding** | Lokal (sentence-transformers) | Wajib lokal; Anthropic memang tidak punya embedding. |
| **Rancangan evaluasi, analisis, iterasi, laporan** | Anda sendiri | Bobot 35% + 20%; model hanya alat bantu. |

---

## Aturan kode (berlaku untuk SETIAP berkas yang dibuat, sejak berkas pertama)

Sumber: konvensi kode dan konvensi penamaan Python Anda. Tiap berkas dicek saat selesai ditulis, bukan ditumpuk ke akhir.

**Bahasa**
- Identifier (nama berkas, fungsi, variabel, kelas, konstanta) memakai **Bahasa Inggris**.
- Docstring dan komentar memakai **Bahasa Indonesia baku dan ringkas**. Istilah teknis/domain dan label di layar dibiarkan apa adanya (mis. "chunk", "top-k", "Pasal 34").
- Angka di dalam kalimat gaya Indonesia: titik untuk ribuan, koma untuk desimal (±903.000 karakter, 0,5 detik). Singkatan bulan: Jan, Feb, Mar, Apr, Mei, Jun, Jul, Agu, Sep, Okt, Nov, Des.

**Docstring dan komentar**
- Ada docstring di **setiap berkas (modul), fungsi, kelas, dan metode**. Kalimat pertama menyatakan apa yang dilakukan atau dikembalikan.
- Komentar menjelaskan **mengapa**, bukan menarasikan apa yang sudah terlihat dari kodenya.

**Penamaan Python**
- Skrip yang dijalankan langsung: `kebab-case.py` di `scripts/`, bentuk kata kerja + objek (`build-index.py`, `run-evaluation.py`). Modul yang di-import: `snake_case.py`.
- Fungsi dan variabel `snake_case`, fungsi diawali kata kerja. Kelas `PascalCase`. Konstanta `UPPER_SNAKE_CASE` bernama sesuai isinya. Yang hanya dipakai di dalam modul diawali `_`.
- Langkah skrip bernama `step_<nama>` dan cocok dengan pilihan `--only`. Flag CLI `--kebab-case`. Variabel lingkungan `UPPER_SNAKE_CASE` dengan prefiks sistem (mis. `DUKCAPIL_TOP_K`); nama kunci provider (`GROQ_API_KEY`, `ANTHROPIC_API_KEY`) mengikuti nama baku provider.
- Sufiks satuan/bentuk: `_s` (detik), `_ms`, `_ts`, `_day`, `_id`/`_ids`, `_path`/`_dir`, `_csv` (mis. `latency_s`, `chunks_path`). Boolean diawali `is_`/`has_`/`can_` atau memakai nama flag-nya.
- Nama satu-dua huruf hanya di lingkup sempit (`r`, `n`, `k`, `x`, `y`, `m`, `fh`, `exc`, `ln`).
- Berkas keluaran `snake_case` yang menyebut isinya (`evaluation_results.csv`); header CSV `snake_case`. **Tidak ada kredensial** di kode maupun nama keluaran.

**Struktur**
- Satu fungsi satu tugas, maksimal 4 tingkat nesting, tanpa import siklik, tanpa kode mati, tanpa logika yang diduplikasi.

---

## 0. Luaran yang dikumpulkan

1. **Source code pipeline RAG** di GitHub, terdokumentasi (README + docstring).
2. **Dokumen metodologi evaluasi + hasilnya** (set uji 10-15 pertanyaan, kriteria jawaban, skor, minimal 1 putaran iterasi dengan perbandingan sebelum-sesudah).
3. **Video demo** maks. 5 menit (tautan), cadangan rate-limit untuk UTS.
4. **Antarmuka Streamlit** bergaya halaman Ask CICADA (dengan selector model), dipublikasikan dari GitHub.

## 1. Arsitektur

```
OFFLINE (sekali, scripts/build-index.py)
  13 PDF → ekstrak teks → chunk per pasal → embedding lokal (sentence-transformers)
         → indeks FAISS + metadata (dokumen, pasal, halaman, tautan resmi)

ONLINE (tiap pertanyaan)
  pertanyaan warga
    → [Anthropic Sonnet 5.5] ubah ke kueri berbahasa regulasi   (bisa dimatikan)
    → embed kueri (lokal) → FAISS top-k
    → prompt: "jawab HANYA dari konteks, sertakan pasal"
    → [model terpilih di UI] Groq gpt-oss (default) | Anthropic Haiku 5.5
       (Groq kena batas → pesan jelas + tawarkan pindah ke Haiku; tidak diam-diam)
    → UI: jawaban + checklist, konteks yang diambil, kartu pasal

EVAL (scripts/run-evaluation.py, hanya di skrip, tidak tampil di UI)
  test_set.jsonl → pipeline → [Sonnet 5.5 sebagai juri] relevansi + faithfulness 0-10
                → jumlah token + latency → evaluation_results.csv
```

## 2. Keputusan & asumsi

| # | Keputusan / asumsi | Catatan |
|---|---|---|
| A-1 | **Sonnet 5.5 = juri evaluasi + penulis ulang kueri.** **Model di selector UI = penjawab akhir** (Groq default, Haiku 5.5 pilihan kedua). | Memenuhi aturan RTM 2 bahwa generasi jawaban *wajib* Groq sebagai jalur utama. Jika Sonnet 5.5 hendak dijadikan penjawab akhir, tanyakan dosen karena menyimpang dari "Groq jalur utama". |
| A-2 | **Anthropic menggantikan Gemini** sebagai penyedia alternatif. Haiku 5.5 = pembanding + cadangan. | RPS hanya menyebut OpenRouter/Groq/Gemini/Ollama; Anthropic tidak disebut dan tidak dilarang. **Catat di dokumen evaluasi** bahwa Sonnet/Haiku dipakai sebagai juri dan pembanding berbayar. |
| A-2b | **Batas gratis Groq** `gpt-oss-120b` (sumber pihak ketiga, belum dicocokkan dengan halaman resmi): ±30 permintaan/menit, ±8.000 token/menit, ±200.000 token/hari, berlaku **per organisasi**. **Cek halaman limits akun Groq Anda.** | Perkiraan kasar: 1 pertanyaan ±3.000-4.000 token (belum diukur), jadi evaluasi 15 pertanyaan kena batas per menit. Dipakai untuk menentukan top-k, jeda, retry. |
| A-3 | Embedding **lokal** (syarat RTM 2). Anthropic tidak punya embedding, jadi tidak ada konflik. | Buku memakai `paraphrase-multilingual-mpnet-base-v2`, tetapi berkasnya ±1,1 GB (terlihat di tangkapan layar buku). Untuk hosting gratis, uji model multilingual yang lebih kecil dulu. Batas memori Streamlit Community Cloud: **verifikasi** di dokumentasinya. |
| A-4 | Vector store: **FAISS** | RPS menyebut FAISS/Chroma. Hanya ±723 vektor. Chroma (Bab 6.3) juga boleh; **verifikasi** kompatibilitasnya saat deploy. |
| A-5 | v1 **tanpa guardrail** selain instruksi "informasi tidak ditemukan" | Itu mitigasi dasar Bab 6.5. RTM 3 akan membandingkan v1 vs v2, jadi v1 dibiarkan sebagai baseline. |
| A-6 | Biaya & latency **hanya diukur di skrip evaluasi** (token dari `response.usage`, waktu dari timer). Tanpa harga/dolar. | Rubrik dan CPMK 2 mewajibkan dimensi biaya & latency; Bab 7.2 mendefinisikan biaya sebagai jumlah token per pertanyaan. |
| A-7 | Aplikasi publik memakai API key Anda | Cukup pasang **batas pengeluaran di Anthropic Console** (tanpa kode). Opsional: kata sandi sederhana atau aplikasi privat dengan dosen sebagai viewer (**verifikasi** opsinya). |
| A-8 | 13 dokumen sumber sudah Anda pegang atau bisa diunduh dari tautan di Submission Minggu 2 | ±613 halaman, ±903.000 karakter |

## 3. Alokasi waktu menurut rubrik

| Kriteria RTM 2 | Bobot |
|---|---|
| Kebenaran pipeline (embedding, retrieval, generasi) | 35% |
| Kualitas rancangan metodologi evaluasi sendiri | 35% |
| Kedalaman analisis hasil + iterasi | 20% |
| Kualitas video demo + walkthrough UTS | 10% |

UI tidak dinilai langsung, jadi **dibatasi ±3 jam**. Kalau telat, potong UI, bukan evaluasi.

## 4. Struktur repo

Konvensi: identifier Inggris, docstring & komentar Bahasa Indonesia, skrip yang dijalankan langsung = `kebab-case.py` di `scripts/`, modul = `snake_case.py`.

```
dukcapil-pintar/
├─ app.py                         # entrypoint Streamlit (halaman Ask)
├─ requirements.txt               # torch CPU + pustaka inti; pin versi setelah uji lokal
├─ requirements-dev.txt           # + ruff, pytest
├─ pyproject.toml                 # aturan ruff (docstring D, penamaan N) + pytest
├─ README.md
├─ .gitignore                     # secrets.toml, .venv, data/raw/*, embeddings.npy
├─ .streamlit/
│  ├─ config.toml                 # tema slate + biru
│  └─ secrets.toml.example        # GROQ_API_KEY, ANTHROPIC_API_KEY (tanpa nilai)
├─ data/
│  ├─ sources.csv                 # 13 regulasi + lampiran OCR, nama berkas, tautan resmi
│  ├─ raw/                        # PDF/TXT sumber (tidak di-commit)
│  ├─ processed/                  # pages.jsonl + chunks.jsonl
│  └─ index/                      # faiss.index + chunk_metadata.jsonl
├─ dukcapil_pintar/               # paket di root (bukan src/) agar app.py di Streamlit Cloud langsung bisa mengimpor
│  ├─ config.py                   # path, konstanta UPPER_SNAKE, daftar model, pembaca secret
│  ├─ ingestion.py                # baca PDF/TXT → teks per halaman
│  ├─ chunking.py                 # pecah per pasal (+ penanda Penjelasan) + metadata
│  ├─ embedding.py                # sentence-transformers lokal
│  ├─ retrieval.py                # FAISS top-k + baca/tulis JSONL
│  ├─ prompts.py                  # prompt penjawab, penulis ulang, juri (berversi)
│  ├─ providers.py                # klien Groq (OpenAI-compatible) + Anthropic + retry
│  ├─ generation.py               # tulis ulang kueri, susun jawaban
│  ├─ pipeline.py                 # answer_question() → AnswerResult
│  ├─ ui.py                       # komponen tampilan ala Ask CICADA
│  └─ formatting.py               # angka gaya Indonesia
├─ scripts/
│  ├─ _project_root.py            # menambahkan root repo ke sys.path
│  ├─ build-index.py              # --only extract,chunk,embed,index  (step_<nama>)
│  ├─ run-evaluation.py           # --only generate,judge,report, --run-name, --pause-s
│  └─ smoke-test-providers.py     # cek kunci + ID model aktif
├─ tests/
│  └─ test_chunking.py
└─ evals/
   ├─ test_set_template.jsonl     # salin ke test_set.jsonl lalu lengkapi
   ├─ evaluation_methodology.md
   ├─ iteration_log.md
   └─ runs/<run-name>/            # answers, judgments, evaluation_results.csv, summary.md, run_config.json
```

---

## 5. HARI 1 — Pipeline RAG + UI sederhana (±8 jam)

### Fase A — Setup (±1 jam)
- [ ] **[P0]** Buat repo GitHub + venv; pasang `pymupdf`, `sentence-transformers`, `faiss-cpu`, `openai`, `anthropic`, `streamlit`.
- [ ] **[P0]** Pakai **akun Groq pribadi** (aturan RTM 2: kuota gratis per akun) dan buat API key Anthropic. Pasang batas pengeluaran di Anthropic Console.
- [ ] **[P0]** Kunci hanya di `.streamlit/secrets.toml` (masuk `.gitignore`) + `secrets.toml.example` tanpa nilai.
- [ ] **[P0]** Pasang `ruff` dengan aturan docstring dan penamaan (pydocstyle `D`, pep8-naming `N`) di `pyproject.toml`, lalu jalankan setiap selesai satu berkas. Sisanya (bahasa docstring, komentar "mengapa", angka gaya Indonesia) dicek manual dengan daftar di atas.
- [ ] **[P0]** `scripts/smoke-test-providers.py`: satu panggilan ke tiap provider. Ambil **ID model dari daftar model aktif** (Bab 5.6: katalog Groq berubah). Titik awal: `openai/gpt-oss-120b` (contoh buku), `claude-sonnet-5-5`, `claude-haiku-5-5`. Simpan di `config.py`.

### Fase B — Korpus (±1,5 jam)
- [ ] **[P0]** Unduh 13 dokumen dari tautan di Submission Minggu 2 (Lapis 1: Permendagri 108/2019, Perpres 96/2018, Permendagri 109/2019, UU 23/2006, UU 24/2013. Lapis 2: Permendagri 72/2022, 2/2016, 74/2022, 96/2019, 7/2019, 2/2023, 19/2018 versi OCR, 95/2019).
- [ ] **[P0]** Ekstrak teks per dokumen dengan PyMuPDF (Bab 6.1). Cocokkan total dengan klaim submission (±903.000 karakter).
- [ ] **[P0]** Periksa manual dokumen OCR (Permendagri 19/2018, lampiran 96/2019): nomor pasal terbaca benar?
- [ ] **[P0]** Commit teks hasil ekstraksi + tautan sumber, bukan 613 halaman PDF mentah.

### Fase C — Chunking + indeks (±2 jam)
- [ ] **[P0]** Chunk **per pasal** (sadar-struktur, Bab 6.2). Alasannya: dokumen hukum berstruktur jelas, dan submission sudah menghitung ±723 potongan setingkat pasal. Tulis ini di dokumen evaluasi.
- [ ] **[P0]** Pasal terlalu panjang dipecah dengan overlap; awali tiap chunk dengan header `[Perpres 96/2018 · Pasal 34]` agar kutipan membawa identitas pasalnya.
- [ ] **[P0]** Metadata per chunk: `document_id`, `document_title`, `article_label`, `page_start`, `source_url`.
- [ ] **[P0]** Embedding lokal → FAISS di `data/index/`. `build-index.py` dengan `step_extract`, `step_chunk`, `step_embed`, `step_index` dan `--only`.
- [ ] **[P0]** Uji cepat retrieval: 18 pertanyaan di Submission §5 punya pasal rujukan. Cek apakah pasal itu muncul di top-k.

### Fase D — Generasi (±2 jam)
- [ ] **[P0]** `prompts.py`, prompt penjawab: (1) jawab **hanya** dari konteks, (2) sertakan rujukan pasal, (3) bila tidak ada: "Informasi tidak ditemukan di dokumen" + sarankan konfirmasi ke Disdukcapil, (4) format penjelasan + checklist berkas, (5) tidak meminta NIK. Beri nomor versi prompt.
- [ ] **[P0]** `providers.py`: Groq lewat SDK `openai` dengan `base_url="https://api.groq.com/openai/v1"` (Bab 5.6); Anthropic lewat SDK resminya.
- [ ] **[P0]** `generation.py`: router berdasarkan pilihan model. **Model yang tampil di UI harus model yang benar-benar menjawab.**
- [ ] **[P0]** Penulis ulang kueri oleh Sonnet 5.5 (bahasa sehari-hari warga → istilah regulasi), dengan saklar `ENABLE_QUERY_REWRITE`.
- [ ] **[P0]** `pipeline.answer_question()` mengembalikan `AnswerResult`: jawaban, chunk yang dipakai, kutipan, nama model, serta token dan latency (dipakai skrip evaluasi saja, UI mengabaikannya).
- [ ] **[P0]** Error rate-limit Groq: retry + backoff, tidak crash. Bila tetap gagal, tampilkan pesan jelas dan tawarkan pindah ke Haiku 5.5. **Jangan berpindah model diam-diam:** model yang tampil harus model yang menjawab.
- [ ] **[P0]** Mulai dengan `TOP_K` kecil (3-4 pasal) dan batasi panjang jawaban (`max_tokens`) agar muat di batas 8.000 token/menit Groq. Catat nilai awalnya karena akan menjadi bahan iterasi.

### Fase E — UI sederhana, batas ±3 jam
- [ ] **[P0]** Bagian 7 berjalan end-to-end. Berhenti di jam ke-3.

**Checkpoint Hari 1:** pertanyaan dari UI → jawaban + pasal dari model default; model bisa diganti ke Haiku.

---

## 6. HARI 2 — Evaluasi, deploy, video, kumpul (±8 jam)

### Fase F — Set uji (±1,5 jam) → bobot 35%
- [ ] **[P0]** 12-15 pertanyaan di `evals/test_set.jsonl`. Kolom: `question_id`, `question`, `question_type`, `expected_articles`, `acceptance_criteria`.
- [ ] **[P0]** Komposisi: ±6 **eksplisit**, ±5 **gabungan** (butuh beberapa pasal/regulasi), ±3 **di luar cakupan** (jawaban benar = "tidak ditemukan").
- [ ] **[P0]** Bahan: pertanyaan di Submission §5. Eksplisit: biaya (UU 24/2013 Pasal 79A), lama penyelesaian (Permendagri 19/2018 Pasal 3), KIA, KTP-el 17 tahun. Gabungan: akta lahir tanpa buku nikah + lahir di luar domisili, korban bencana kehilangan seluruh dokumen. Di luar cakupan: pencatatan perkawinan warga muslim (KUA) dan praktik khas satu daerah, keduanya sudah Anda nyatakan di luar cakupan.
- [ ] **[P1]** Sonnet 5.5 boleh dipakai mengusulkan kandidat pertanyaan dari teks pasal, **hanya sebagai bahan**. Pilihan pertanyaan akhir, komposisi, dan kriteria jawaban Anda putuskan sendiri (syarat "dirancang sendiri").
- [ ] **[P0]** **Verifikasi tiap nomor pasal di `expected_articles` langsung ke teks korpus** sebelum jadi kunci jawaban; jangan menyalin dari submission tanpa dicek.
- [ ] **[P0]** Tulis kriteria jawaban diterima per pertanyaan (butir kunci yang harus muncul) dalam dokumen yang dibaca manusia (Tabel 7.1 buku).
- [ ] **[P1]** Ambil 3 pertanyaan yang lolos sebagai **chip contoh** di halaman utama.

### Fase G — Jalankan evaluasi (±2 jam)
- [ ] **[P0]** `run-evaluation.py` dengan `step_generate`, `step_judge`, `step_report`. Simpan keluaran mentah per langkah agar bisa dilanjutkan bila kena rate-limit.
- [ ] **[P0]** Atur laju panggilan Groq (jeda antarpertanyaan + retry dengan backoff). Hitung dulu jatah: 2-3 putaran evaluasi (sebelum dan sesudah iterasi) harus muat di batas harian Groq; cek angka resminya di akun.
- [ ] **[P0]** Seluruh jawaban yang dievaluasi untuk perbandingan sebelum-sesudah **berasal dari model yang sama (Groq)**. Jawaban hasil cadangan Haiku dipisah dan diberi label.
- [ ] **[P0]** Empat dimensi (Bab 7.2):
  - **Relevansi** (0-10, juri LLM)
  - **Faithfulness** (0-10; juri memecah jawaban jadi klaim, tiap klaim DIDUKUNG/TIDAK terhadap konteks, Bab 7.4)
  - **Biaya** = jumlah token per pertanyaan (dari `response.usage`, tanpa harga)
  - **Latency** = detik dari pertanyaan sampai jawaban
- [ ] **[P0]** Tambahan objektif: **hit rate retrieval** (pasal kunci masuk top-k) dan **penolakan benar** untuk pertanyaan di luar cakupan.
- [ ] **[P0]** Juri: Sonnet 5.5, suhu 0, prompt juri diberi versi, model dipin. Penjawab default (Groq) berbeda dari juri, sehingga tidak menilai jawabannya sendiri.
- [ ] **[P0]** Skor juri adalah estimasi (Bab 7.4). **Periksa manual minimal 3 pertanyaan berskor terendah** dan catat apakah juri benar.

### Fase H — Iterasi (±1,5 jam) → bobot 20%
- [ ] **[P0]** Cari kategori terlemah. Diagnosis Bab 7.6: chunk tak relevan → masalah retrieval; chunk relevan tapi jawaban tak faithful → masalah prompt.
- [ ] **[P0]** Ubah **satu** parameter (kandidat: `TOP_K`, penulis ulang kueri on/off, model embedding, instruksi prompt), jalankan ulang, catat sebelum-sesudah di `evals/iteration_log.md`.
- [ ] **[P0]** Tulis analisis: apa yang membaik, apa yang memburuk, dugaan sebabnya, dan keterbatasan sistem secara jujur.

### Fase I — Deploy Streamlit dari GitHub (±1 jam)
- [ ] **[P0]** Uji lokal bersih (venv baru, `pip install -r requirements.txt`, `streamlit run app.py`); pin versi.
- [ ] **[P0]** Indeks + metadata ikut di repo (di bawah batas berkas GitHub) supaya aplikasi tidak membangun ulang saat start.
- [ ] **[P0]** Push ke GitHub; periksa riwayat commit: tidak ada kunci/`secrets.toml`.
- [ ] **[P0]** Streamlit Community Cloud: New app → repo, branch, `app.py` → **Advanced settings → Secrets**, tempel `GROQ_API_KEY` dan `ANTHROPIC_API_KEY`.
- [ ] **[P0]** Uji di URL publik: model default, pindah ke Haiku, pertanyaan di luar cakupan, aplikasi tidak kehabisan memori saat start.
- [ ] **[P1]** Buka aplikasi sebelum demo/UTS (aplikasi gratis dapat tertidur bila lama tidak diakses).

### Fase J — Video demo, maks. 5 menit (±1 jam)
- [ ] **[P0]** Skrip:
  - 0:00-0:30 masalah dan pengguna Dukcapil
  - 0:30-1:00 arsitektur (diagram bagian 1)
  - 1:00-2:30 demo 3 pertanyaan: eksplisit, gabungan, di luar cakupan (tunjukkan kartu pasal)
  - 2:30-3:00 ganti model Groq → Haiku
  - 3:00-4:15 tabel evaluasi + sebelum-sesudah iterasi
  - 4:15-5:00 keterbatasan + rencana RTM 3
- [ ] **[P0]** Rekam dari aplikasi ter-deploy, unggah, simpan tautan.

### Fase K — Dokumen, konvensi, kumpul (±1 jam)
- [ ] **[P0]** `evals/evaluation_methodology.md`: set uji, metrik, juri + alasan, perintah persis untuk mereproduksi, hasil, iterasi, keterbatasan. Cantumkan peran tiap model (tabel "Pembagian peran model") dan catatan bahwa Anthropic dipakai sebagai pengganti Gemini untuk juri dan pembanding berbayar.
- [ ] **[P0]** README: arsitektur, cara menjalankan, nama variabel secret (tanpa nilai), keputusan desain.
- [ ] **[P0]** Audit konvensi terakhir sebelum push akhir, menyapu seluruh repo dengan "Aturan kode" di atas (docstring di tiap berkas/fungsi/kelas, komentar "mengapa", penamaan, `step_<nama>` cocok dengan `--only`, tanpa kode mati/duplikat, maks. 4 tingkat nesting, tanpa kredensial). Ini audit, bukan pertama kali memeriksa.
- [ ] **[P0]** Kumpulkan lewat e-learning: tautan repo, dokumen evaluasi, tautan video, tautan aplikasi. Batas: akhir Minggu 7 (cek tanggal pastinya di e-learning).
- [ ] **[P1]** Pastikan tiap anggota kelompok punya akun Groq sendiri untuk walkthrough UTS Minggu 8.

---

## 7. UI: halaman Ask CICADA → Streamlit (versi sederhana)

Acuan: `frontend/src/pages/Ask.tsx` dan `ask/ModelSelector.tsx`. Yang dipertahankan adalah perilaku dan hierarkinya, bukan kodenya.

| # | Elemen | Di DUKCAPIL-Pintar | Prio |
|---|---|---|---|
| 1 | Disclaimer tetap di atas, tidak bisa ditutup | "Jawaban dibuat AI dari teks regulasi. Verifikasi sebelum diandalkan dan konfirmasi ke Disdukcapil setempat." | P0 |
| 2 | Keadaan kosong: logo, judul, 1 kalimat, 3 chip pertanyaan | "DUKCAPIL-Pintar" + subjudul + 3 chip dari set uji | P0 |
| 3 | Satu giliran, bukan thread (tidak ada memori) | Simpan hanya pertanyaan terakhir; jawaban baru menggantikan yang lama | P0 |
| 4 | Pertanyaan sebagai gelembung kanan; jawaban bertanda logo; indikator tahap | Gelembung pengguna + `st.status("Mengambil konteks regulasi…")` | P0 |
| 5 | **Jawaban dulu, bukti sesudahnya** | (a) jawaban + checklist, (b) panel konteks, (c) kartu pasal | P0 |
| 6 | Panel amber dengan peringatan + tombol Copy | Panel amber "Konteks yang diambil. Tinjau sebelum mengandalkan." berisi chunk (`st.code` sudah ada tombol salin) | P0 |
| 7 | Kartu sitasi yang bisa diklik | "Berdasarkan N pasal": dokumen · pasal · halaman, tautan ke sumber resmi. Pertanyaan di luar cakupan tetap menampilkan penjelasan + saran konfirmasi, bukan jalan buntu. | P0 |
| 8 | Chip "Answered by {model}" | Chip "Dijawab oleh {model}" | P0 |
| 9 | Composer menempel di bawah, selector model di sebelah tombol Ask | `st.chat_input` di bawah; selector tepat di atasnya (**verifikasi** API kontainer bawah di versi Streamlit yang dipin) | P0 |
| 10 | Selector: urutan tetap, nonaktif + alasan bila tak tersedia | `Groq · gpt-oss (default)` lalu `Anthropic · Claude Haiku 5.5`. Kunci hilang → nonaktif + alasan. | P0 |
| 11 | Tema slate + biru | `config.toml`: latar `#f8fafc`, sekunder `#f1f5f9`, teks `#0f172a`, primer `#2563eb` | P2 |

**Sengaja tidak dibuat:** credit readout, kuota, batas biaya, chip biaya/latency, umpan balik 👍/👎.

Cek tiap API Streamlit yang dipakai (`st.chat_input`, `st.status`, kontainer bawah) ada di versi yang dipin sebelum menyusun tampilan.

## 8. Risiko dan batas pemotongan

| Risiko | Penanganan |
|---|---|
| Rate-limit Groq tier gratis saat evaluasi/demo (±8.000 token/menit, belum diverifikasi resmi) | Top-k kecil, `max_tokens` dibatasi, jeda + retry, simpan keluaran per langkah; Haiku 5.5 sebagai cadangan yang diberi label; video demo sebagai cadangan UTS |
| Aplikasi kehabisan memori di hosting gratis | Model embedding kecil; indeks sudah jadi di repo |
| API key dipakai orang lain lewat aplikasi publik | Batas pengeluaran Anthropic Console; opsional kata sandi/aplikasi privat |
| Nomor pasal hasil OCR keliru | Verifikasi tiap `expected_articles` ke teks korpus |
| Juri LLM tidak konsisten | Suhu 0, prompt dipin, cek manual 3 skor terendah, tambah metrik objektif |
| Waktu 2 hari ketat | Potong berurutan: **P2 → chip contoh → ablasi penulis ulang kueri**. Jangan potong set uji, evaluasi, iterasi, video. |

## 9. Referensi

- RPS Introduction to Generative AI, Format Rencana Tugas Mahasiswa 2
- Buku pegangan Bab 5 (RAG, Groq, embedding lokal), Bab 6 (membangun RAG), Bab 7 (evaluasi & iterasi), Bab 10.5 (deployment Streamlit)
- Es dkk. (2024) RAGAs · Izacard & Grave (2021) Fusion-in-Decoder · Huyen (2025) AI Engineering
- Submission Minggu 2 (13 dokumen + 18 pertanyaan uji cakupan), Use-Case Brief DUKCAPIL-Pintar
