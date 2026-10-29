# Alur Kerja DUKCAPIL-Pintar

Dokumen ini menggambarkan cara prototipe RAG v1 bekerja, dari PDF regulasi sampai jawaban
yang menyebut pasal rujukannya. Diagram memakai [Mermaid](https://mermaid.js.org/), jadi tampil
langsung di GitHub dan bisa diubah sebagai teks.

**Keterangan warna** (berlaku di semua diagram):

| Warna | Arti |
|---|---|
| Hijau | Berjalan **lokal** di mesin sendiri (tanpa mengirim teks ke provider) |
| Jingga | **Groq** (`openai/gpt-oss-120b`), jalur generasi utama |
| Clay | **Anthropic** (Claude Sonnet 5.5 dan Haiku 5.5) |
| Abu | Data, berkas, pengguna, dan titik keputusan |
| Kuning | Galat atau peringatan yang ditampilkan ke pengguna |

---

## 1. Gambaran besar

Tiga jalur memakai indeks regulasi yang sama: pembuatan indeks (sekali), aplikasi untuk warga
(tiap pertanyaan), dan evaluasi (tiap putaran uji). Aplikasi dan evaluasi memakai kelas
`RagPipeline` yang sama, sehingga yang dievaluasi persis yang didemokan.

```mermaid
flowchart LR
    classDef lokal fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef data fill:#f5f5f4,stroke:#a8a29e,color:#44403c

    subgraph OFF["Pembuatan indeks (sekali)"]
        pdf[("13 regulasi<br/>PDF dan teks OCR")]:::data
        build["scripts/<br/>build-index.py"]:::lokal
        index[("Indeks FAISS<br/>+ metadata pasal")]:::data
        pdf --> build --> index
    end

    pipe{{"RagPipeline<br/>pipeline.py"}}:::lokal

    subgraph ON["Aplikasi warga (tiap pertanyaan)"]
        warga(["Warga"]):::data
        app["app.py<br/>Streamlit"]:::lokal
        warga <--> app
    end

    subgraph EV["Evaluasi (tiap putaran)"]
        uji[("Set uji<br/>14 pertanyaan")]:::data
        eval["scripts/<br/>run-evaluation.py"]:::lokal
        hasil[("CSV dan<br/>ringkasan")]:::data
        uji --> eval --> hasil
    end

    index --> pipe
    app <--> pipe
    eval <--> pipe

    style OFF fill:#fafaf9,stroke:#d6d3d1,color:#57534e
    style ON fill:#fafaf9,stroke:#d6d3d1,color:#57534e
    style EV fill:#fafaf9,stroke:#d6d3d1,color:#57534e
```

---

## 2. Pembuatan indeks (offline, sekali jalan)

`python scripts/build-index.py` menjalankan empat langkah berurutan. Tiap langkah menyimpan
keluarannya, sehingga bisa dijalankan sebagian dengan `--only`, misalnya `--only embed,index`.

```mermaid
flowchart LR
    classDef lokal fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef data fill:#f5f5f4,stroke:#a8a29e,color:#44403c

    src[("sources.csv<br/>+ data/raw<br/>PDF dan lampiran OCR")]:::data
    s1["1 · step_extract<br/>baca teks per halaman<br/>buang noise halaman<br/>perbaiki judul pasal<br/>keluaran: pages.jsonl"]:::lokal
    s2["2 · step_chunk<br/>pecah per pasal<br/>pasal panjang dipecah<br/>maks. 1.500 karakter<br/>keluaran: chunks.jsonl<br/>±950 chunk"]:::lokal
    s3["3 · step_embed<br/>mpnet multilingual<br/>vektor 768 dimensi<br/>keluaran:<br/>embeddings.npy"]:::lokal
    s4["4 · step_index<br/>FAISS IndexFlatIP<br/>keluaran:<br/>faiss.index +<br/>chunk_metadata.jsonl"]:::lokal

    src --> s1 --> s2 --> s3 --> s4
```

Alasan chunk per pasal: peraturan berstruktur jelas, satu pasal umumnya satu ketentuan utuh, dan
jawaban harus bisa menyebut nomor pasal. Tiap chunk diawali header `[Perpres 96/2018 · Pasal 34]`
yang ikut di-embed, agar pertanyaan yang menyebut nama regulasi atau nomor pasal lebih mudah
menemukan potongannya. Bagian Penjelasan dan butir perubahan pada UU perubahan diberi label
tersendiri supaya tidak tertukar dengan batang tubuh.

---

## 3. Menjawab satu pertanyaan (online)

Urutan yang terjadi tiap kali warga bertanya. Penulis ulang kueri bersifat opsional
(`DUKCAPIL_QUERY_REWRITE`) dan kegagalannya tidak menggagalkan jawaban.

```mermaid
sequenceDiagram
    autonumber
    actor W as Warga
    participant UI as Aplikasi
    participant P as RagPipeline
    participant S as Sonnet 5.5<br/>penulis ulang
    participant L as Pencarian lokal<br/>mpnet + FAISS
    participant M as Model penjawab<br/>Groq atau Haiku

    W->>UI: pertanyaan + pilihan model
    UI->>P: answer_question()
    P->>S: ubah ke istilah regulasi
    alt berhasil
        S-->>P: kueri berbahasa regulasi
    else gagal atau dimatikan
        S-->>P: dilewati, pakai pertanyaan asli
    end
    P->>L: cari pasal untuk pertanyaan dan kueri
    L-->>P: 4 pasal teratas
    Note over P,L: hasil dua kueri digabung,<br/>skor tertinggi per chunk
    P->>M: prompt answer-v1.1<br/>konteks 4 pasal + pertanyaan
    Note over M: jawab hanya dari konteks,<br/>sertakan rujukan pasal
    M-->>P: jawaban, atau<br/>"Informasi tidak ditemukan di dokumen."
    P-->>UI: AnswerResult
    UI-->>W: jawaban, panel konteks,<br/>kartu pasal, chip model
```

Yang ditampilkan ke warga selalu memuat: jawaban, konteks yang diambil (bisa disalin), kartu
pasal dengan tautan ke sumber resmi, dan chip "Dijawab oleh {model}". Token dan latency hanya
dicatat untuk evaluasi, tidak tampil di antarmuka.

---

## 4. Pembagian peran model

| Tahap | Model | Lokasi | Catatan |
|---|---|---|---|
| Embedding pertanyaan dan pasal | `paraphrase-multilingual-mpnet-base-v2` | Lokal | Wajib lokal (syarat RTM 2). Puncak memori ±1,9 GB |
| Penulis ulang kueri | Claude Sonnet 5.5 | Anthropic | Opsional, bisa dimatikan |
| Penjawab utama (default) | Groq `openai/gpt-oss-120b` | Groq | Jalur generasi utama sesuai ketentuan RTM 2 |
| Penjawab pembanding dan cadangan | Claude Haiku 5.5 | Anthropic | Dipilih manual atau lewat tombol saat Groq kena batas |
| Juri evaluasi | Claude Sonnet 5.5 | Anthropic | Berbeda dari penjawab default, jadi tidak menilai jawabannya sendiri |

---

## 5. Rate limit dan model cadangan

Model yang tampil di antarmuka selalu model yang benar-benar menjawab. Sistem **tidak pernah**
berpindah model diam-diam: pindah ke Haiku hanya terjadi saat pengguna menekan tombolnya.

```mermaid
flowchart TD
    classDef lokal fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef claude fill:#faf0ea,stroke:#aa5233,color:#5c2a18
    classDef data fill:#f5f5f4,stroke:#a8a29e,color:#44403c
    classDef tanya fill:#f5f5f4,stroke:#78716c,color:#1c1917
    classDef galat fill:#fffbeb,stroke:#d97706,color:#78350f

    mulai(["Pertanyaan dikirim<br/>dengan model terpilih"]):::data
    kunci{"API key<br/>ada?"}:::tanya
    tanpa["Panel galat:<br/>API key belum diisi"]:::galat
    panggil["Panggil model"]:::lokal
    hasil{"Hasil<br/>panggilan?"}:::tanya
    ok(["Jawaban + chip<br/>model penjawab"]):::lokal
    retry["Coba ulang dengan jeda<br/>2, 4, lalu 8 detik<br/>maks. 4 percobaan"]:::lokal
    permanen["Galat permanen:<br/>kunci atau ID model salah<br/>dilaporkan, tanpa retry"]:::galat
    pesan["Pesan jelas: model membatasi<br/>permintaan, plus tombol<br/>Coba dengan Claude Haiku 5.5"]:::galat
    pindah["Pengguna menekan tombol:<br/>selector pindah ke Haiku,<br/>pertanyaan yang sama diulang"]:::claude

    mulai --> kunci
    kunci -- tidak --> tanpa
    kunci -- ya --> panggil --> hasil
    hasil -- berhasil --> ok
    hasil -- "429 atau koneksi putus" --> retry
    hasil -- "galat lain" --> permanen
    retry -- berhasil --> ok
    retry -- "tetap kena batas" --> pesan
    pesan --> pindah --> panggil
```

---

## 6. Evaluasi dan iterasi

### 6a. Satu putaran evaluasi

`python scripts/run-evaluation.py --run-name <nama>` menjalankan tiga langkah. Tiap jawaban dan
penilaian ditulis segera, jadi putaran yang terputus (mis. rate limit) bisa dilanjutkan dengan
perintah yang sama.

```mermaid
flowchart LR
    classDef lokal fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef groq fill:#fff7ed,stroke:#ea580c,color:#7c2d12
    classDef claude fill:#faf0ea,stroke:#aa5233,color:#5c2a18
    classDef data fill:#f5f5f4,stroke:#a8a29e,color:#44403c

    uji[("test_set.jsonl<br/>14 pertanyaan<br/>pasal kunci + kriteria")]:::data
    beku[("Kueri tulis ulang<br/>putaran pembanding<br/>--reuse-rewrites-from")]:::data
    gen["step_generate<br/>RagPipeline per pertanyaan<br/>keluaran: answers.jsonl"]:::groq
    juri["step_judge<br/>juri Sonnet 5.5<br/>relevansi dan faithfulness<br/>keluaran: judgments.jsonl"]:::claude
    rep["step_report<br/>tambah hit retrieval dan<br/>penolakan benar<br/>keluaran: CSV + summary.md"]:::lokal

    uji --> gen --> juri --> rep
    beku -.-> gen
```

Faithfulness dinilai dengan memecah jawaban menjadi klaim, lalu tiap klaim ditandai DIDUKUNG atau
TIDAK DIDUKUNG oleh konteks. Hit retrieval dan penolakan benar dihitung tanpa juri, langsung dari
pasal yang diambil dan dari kalimat "tidak ditemukan".

### 6b. Siklus iterasi

```mermaid
flowchart TD
    classDef lokal fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef data fill:#f5f5f4,stroke:#a8a29e,color:#44403c
    classDef tanya fill:#f5f5f4,stroke:#78716c,color:#1c1917

    putaran(["Hasil satu putaran"]):::data
    cek["Periksa manual<br/>3 skor faithfulness terendah"]:::lokal
    diag{"Diagnosis"}:::tanya
    ret["Chunk tidak relevan:<br/>perbaiki retrieval<br/>top-k, embedding, fusi"]:::lokal
    prm["Chunk relevan, jawaban tidak setia:<br/>perbaiki prompt"]:::lokal
    ubah["Ubah SATU parameter<br/>kueri tulis ulang tetap dibekukan"]:::lokal
    baru["Putaran baru"]:::lokal
    log[("iteration_log.md<br/>tabel sebelum dan sesudah")]:::data

    putaran --> cek --> diag
    diag -- "retrieval" --> ret --> ubah
    diag -- "generasi" --> prm --> ubah
    ubah --> baru --> log
    baru -.-> putaran
```

Dua hal dijaga agar perbandingan antarputaran jujur: hanya **satu** parameter berubah per putaran,
dan kueri tulis ulang dibekukan dari putaran pembanding karena penulis ulang tidak deterministik
(tanpa itu, retrieval ikut berubah antarputaran).

---

## 7. Peta berkas

| Tahap | Berkas |
|---|---|
| Baca PDF dan bersihkan teks | `dukcapil_pintar/ingestion.py` |
| Pecah per pasal | `dukcapil_pintar/chunking.py` |
| Embedding lokal | `dukcapil_pintar/embedding.py` |
| Indeks FAISS dan penggabungan hasil | `dukcapil_pintar/retrieval.py` |
| Prompt penjawab, penulis ulang, dan juri (berversi) | `dukcapil_pintar/prompts.py` |
| Klien Groq dan Anthropic, retry, rate limit | `dukcapil_pintar/providers.py` |
| Tulis ulang kueri dan susun jawaban | `dukcapil_pintar/generation.py` |
| Alur end-to-end | `dukcapil_pintar/pipeline.py` |
| Antarmuka | `app.py`, `dukcapil_pintar/ui.py` |
| Parameter dan daftar model | `dukcapil_pintar/config.py` |
| Pembuatan indeks | `scripts/build-index.py` |
| Evaluasi | `scripts/run-evaluation.py` |
