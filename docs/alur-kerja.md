# Alur Kerja DUKCAPIL-Pintar

Dokumen ini menguraikan cara kerja prototipe RAG v1, mulai dari berkas PDF regulasi hingga
jawaban yang menyebutkan pasal rujukannya. Diagram disusun dengan [Mermaid](https://mermaid.js.org/)
sehingga dapat ditampilkan langsung pada GitHub dan dapat disunting sebagai teks.

**Keterangan warna** (berlaku pada seluruh diagram):

| Warna | Arti |
|---|---|
| Hijau | Berjalan **secara lokal** pada perangkat sendiri (teks tidak dikirim ke penyedia layanan) |
| Jingga | **Groq** (`openai/gpt-oss-120b`), jalur generasi utama |
| Clay | **Anthropic** (Claude Sonnet 5.5 dan Haiku 5.5) |
| Abu-abu | Data, berkas, pengguna, dan titik keputusan |
| Kuning | Galat atau peringatan yang ditampilkan kepada pengguna |

---

## 1. Gambaran umum

Tiga jalur menggunakan indeks regulasi yang sama, yaitu pembuatan indeks (sekali), aplikasi bagi
warga (setiap pertanyaan), dan evaluasi (setiap putaran pengujian). Aplikasi dan evaluasi
menggunakan kelas `RagPipeline` yang sama sehingga yang dievaluasi identik dengan yang
didemonstrasikan.

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

    subgraph ON["Aplikasi warga (setiap pertanyaan)"]
        warga(["Warga"]):::data
        app["app.py<br/>Streamlit"]:::lokal
        warga <--> app
    end

    subgraph EV["Evaluasi (setiap putaran)"]
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

## 2. Pembuatan indeks (luring, satu kali)

Perintah `python scripts/build-index.py` menjalankan empat langkah secara berurutan. Setiap
langkah menyimpan keluarannya sehingga dapat dijalankan sebagian dengan opsi `--only`, misalnya
`--only embed,index`.

```mermaid
flowchart LR
    classDef lokal fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef data fill:#f5f5f4,stroke:#a8a29e,color:#44403c

    src[("sources.csv<br/>+ data/raw<br/>PDF dan lampiran OCR")]:::data
    s1["1 · step_extract<br/>membaca teks per halaman<br/>menghapus elemen<br/>pengulangan halaman<br/>memperbaiki judul pasal<br/>keluaran: pages.jsonl"]:::lokal
    s2["2 · step_chunk<br/>memecah per pasal<br/>pasal panjang dipecah<br/>maks. 1.500 karakter<br/>keluaran: chunks.jsonl<br/>±950 chunk"]:::lokal
    s3["3 · step_embed<br/>mpnet multilingual<br/>vektor 768 dimensi<br/>keluaran:<br/>embeddings.npy"]:::lokal
    s4["4 · step_index<br/>FAISS IndexFlatIP<br/>keluaran:<br/>faiss.index +<br/>chunk_metadata.jsonl"]:::lokal

    src --> s1 --> s2 --> s3 --> s4
```

Pemecahan chunk per pasal dipilih karena peraturan perundang-undangan berstruktur jelas, satu
pasal umumnya memuat satu ketentuan utuh, dan jawaban harus dapat menyebutkan nomor pasal. Setiap
chunk diawali header `[Perpres 96/2018 · Pasal 34]` yang turut di-*embed* agar pertanyaan yang
menyebut nama regulasi atau nomor pasal lebih mudah menemukan potongan yang sesuai. Bagian
Penjelasan dan butir perubahan pada undang-undang perubahan diberi label tersendiri agar tidak
tertukar dengan batang tubuh.

---

## 3. Menjawab satu pertanyaan (daring)

Urutan proses yang terjadi setiap kali warga mengajukan pertanyaan. Penulis ulang kueri bersifat
opsional (`DUKCAPIL_QUERY_REWRITE`) dan kegagalannya tidak menggagalkan jawaban.

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
    else gagal atau dinonaktifkan
        S-->>P: dilewati, memakai pertanyaan asli
    end
    P->>L: cari pasal untuk pertanyaan dan kueri
    L-->>P: 4 pasal teratas
    Note over P,L: hasil dua kueri digabung,<br/>skor tertinggi per chunk
    P->>M: prompt answer-v1.1<br/>konteks 4 pasal + pertanyaan
    Note over M: menjawab hanya dari konteks,<br/>menyertakan rujukan pasal
    M-->>P: jawaban, atau<br/>"Informasi tidak ditemukan di dokumen."
    P-->>UI: AnswerResult
    UI-->>W: jawaban, panel konteks,<br/>kartu pasal, label model
```

Tampilan yang disajikan kepada warga selalu memuat jawaban, konteks yang diambil (dapat
disalin), kartu pasal beserta tautan ke sumber resmi, dan label "Dijawab oleh {model}". Jumlah
token dan latency hanya dicatat untuk keperluan evaluasi dan tidak ditampilkan pada antarmuka.

---

## 4. Pembagian peran model

| Tahap | Model | Lokasi | Catatan |
|---|---|---|---|
| Embedding pertanyaan dan pasal | `paraphrase-multilingual-mpnet-base-v2` | Lokal | Wajib lokal (persyaratan RTM 2). Puncak memori ±1,9 GB |
| Penulis ulang kueri | Claude Sonnet 5.5 | Anthropic | Opsional, dapat dinonaktifkan |
| Penjawab utama (bawaan) | Groq `openai/gpt-oss-120b` | Groq | Jalur generasi utama sesuai ketentuan RTM 2 |
| Penjawab pembanding dan cadangan | Claude Haiku 5.5 | Anthropic | Dipilih secara manual atau melalui tombol ketika Groq terkena pembatasan |
| Juri evaluasi | Claude Sonnet 5.5 | Anthropic | Berbeda dari penjawab bawaan sehingga tidak menilai jawabannya sendiri |

---

## 5. Pembatasan laju dan model cadangan

Model yang tampil pada antarmuka selalu merupakan model yang benar-benar menjawab. Sistem
**tidak pernah** berpindah model tanpa sepengetahuan pengguna: perpindahan ke Haiku hanya terjadi
ketika pengguna menekan tombol yang tersedia.

```mermaid
flowchart TD
    classDef lokal fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef claude fill:#faf0ea,stroke:#aa5233,color:#5c2a18
    classDef data fill:#f5f5f4,stroke:#a8a29e,color:#44403c
    classDef tanya fill:#f5f5f4,stroke:#78716c,color:#1c1917
    classDef galat fill:#fffbeb,stroke:#d97706,color:#78350f

    mulai(["Pertanyaan dikirim<br/>dengan model terpilih"]):::data
    kunci{"API key<br/>tersedia?"}:::tanya
    tanpa["Panel galat:<br/>API key belum diisi"]:::galat
    panggil["Memanggil model"]:::lokal
    hasil{"Hasil<br/>pemanggilan?"}:::tanya
    ok(["Jawaban + label<br/>model penjawab"]):::lokal
    retry["Percobaan ulang dengan jeda<br/>2, 4, lalu 8 detik<br/>maks. 4 percobaan"]:::lokal
    permanen["Galat permanen:<br/>kunci atau ID model salah<br/>dilaporkan tanpa percobaan ulang"]:::galat
    pesan["Pesan galat yang jelas: model<br/>membatasi permintaan, disertai tombol<br/>Coba dengan Claude Haiku 5.5"]:::galat
    pindah["Pengguna menekan tombol:<br/>selektor berpindah ke Haiku,<br/>pertanyaan yang sama diulang"]:::claude

    mulai --> kunci
    kunci -- tidak --> tanpa
    kunci -- ya --> panggil --> hasil
    hasil -- berhasil --> ok
    hasil -- "429 atau koneksi terputus" --> retry
    hasil -- "galat lain" --> permanen
    retry -- berhasil --> ok
    retry -- "tetap terkena pembatasan" --> pesan
    pesan --> pindah --> panggil
```

---

## 6. Evaluasi dan iterasi

### 6a. Satu putaran evaluasi

Perintah `python scripts/run-evaluation.py --run-name <nama>` menjalankan tiga langkah. Setiap
jawaban dan penilaian langsung ditulis ke berkas sehingga putaran yang terhenti (misalnya akibat
pembatasan laju) dapat dilanjutkan dengan perintah yang sama.

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
    rep["step_report<br/>menambahkan hit retrieval dan<br/>penolakan benar<br/>keluaran: CSV + summary.md"]:::lokal

    uji --> gen --> juri --> rep
    beku -.-> gen
```

Faithfulness dinilai dengan memecah jawaban menjadi klaim, kemudian setiap klaim ditandai
DIDUKUNG atau TIDAK DIDUKUNG oleh konteks. Hit retrieval dan penolakan benar dihitung tanpa
juri, langsung dari pasal yang diambil dan dari kalimat "tidak ditemukan".

### 6b. Siklus iterasi

```mermaid
flowchart TD
    classDef lokal fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef data fill:#f5f5f4,stroke:#a8a29e,color:#44403c
    classDef tanya fill:#f5f5f4,stroke:#78716c,color:#1c1917

    putaran(["Hasil satu putaran"]):::data
    cek["Pemeriksaan manual<br/>3 skor faithfulness terendah"]:::lokal
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

Dua prinsip dijaga agar perbandingan antarputaran sahih: hanya **satu** parameter yang diubah
pada setiap putaran, dan kueri tulis ulang dibekukan dari putaran pembanding karena penulis
ulang tidak deterministik (tanpa pembekuan, hasil retrieval ikut berubah antarputaran).

---

## 7. Peta berkas

| Tahap | Berkas |
|---|---|
| Membaca PDF dan membersihkan teks | `dukcapil_pintar/ingestion.py` |
| Memecah per pasal | `dukcapil_pintar/chunking.py` |
| Embedding lokal | `dukcapil_pintar/embedding.py` |
| Indeks FAISS dan penggabungan hasil | `dukcapil_pintar/retrieval.py` |
| Prompt penjawab, penulis ulang, dan juri (berversi) | `dukcapil_pintar/prompts.py` |
| Klien Groq dan Anthropic, percobaan ulang, pembatasan laju | `dukcapil_pintar/providers.py` |
| Penulisan ulang kueri dan penyusunan jawaban | `dukcapil_pintar/generation.py` |
| Alur menyeluruh (*end-to-end*) | `dukcapil_pintar/pipeline.py` |
| Antarmuka | `app.py`, `dukcapil_pintar/ui.py` |
| Parameter dan daftar model | `dukcapil_pintar/config.py` |
| Pembuatan indeks | `scripts/build-index.py` |
| Evaluasi | `scripts/run-evaluation.py` |
