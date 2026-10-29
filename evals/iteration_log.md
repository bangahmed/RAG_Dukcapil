# Catatan Iterasi

> Satu putaran = satu parameter diubah (Bab 7.6). Bandingkan dengan putaran sebelumnya.
> Angka di bawah dari `evals/runs/<run-name>/summary.md`. Bagian analisis adalah **draf**
> dan perlu ditulis ulang dengan kata-kata sendiri.

## Iterasi 1: prompt penjawab `answer-v1` → `answer-v1.1`

- **Masalah yang terlihat:** pada `baseline`, faithfulness rata-rata hanya 6,46, paling rendah
  justru di pertanyaan eksplisit (4,92) padahal hit retrieval-nya 1,00 (q01 3,0; q03 2,5; q05 4,0).
- **Diagnosis:** generasi, bukan retrieval (Bab 7.6: chunk relevan tetapi jawaban tidak
  faithful). Pemeriksaan manual q01 dan q03 membenarkan juri: inti jawaban benar, tetapi
  jawaban ditambah checklist dan langkah umum yang tidak tertulis di konteks (mis. "fotokopi",
  "KK asli", "mengisi formulir", "datang ke kantor"). Penyebabnya butir 4 prompt v1 yang
  mewajibkan format "penjelasan, checklist, langkah".
- **Parameter yang diubah:** hanya butir 4 prompt penjawab: checklist dan langkah hanya boleh
  memuat butir yang tertulis di konteks, dan bagian itu dihilangkan bila konteks tidak memuatnya.
  Teks lama ada di `prompt_history.md`. Model, embedding, `TOP_K`, dan penulis ulang kueri tetap.
- **Perintah (perbandingan bersih):**
  `python scripts/run-evaluation.py --run-name prompt-v1-1-frozen --reuse-rewrites-from baseline`

### Perbandingan bersih: kueri tulis ulang dibekukan dari baseline

Penulis ulang kueri (Sonnet 5.5) tidak deterministik dan suhunya tidak bisa diatur. Putaran
`prompt-v1-1` pertama memakai kueri baru dan berbeda di 14 dari 14 pertanyaan, sehingga hit
retrieval ikut bergeser dan tidak bisa dikaitkan ke prompt (lihat bagian berikutnya). Putaran
`prompt-v1-1-frozen` memakai kueri tulis ulang yang sama persis dengan `baseline`. Hasilnya
top-4 identik di 14 dari 14 pertanyaan, jadi selisih di bawah hanya datang dari prompt.

| Metrik | baseline | iterasi 1 | Selisih |
|---|---|---|---|
| Faithfulness | 6,46 | 7,93 | +1,47 |
| Relevansi | 8,07 | 8,21 | +0,14 |
| Hit retrieval | 0,73 | 0,73 | 0 (identik, sesuai rancangan) |
| Penolakan benar | 1,00 | 1,00 | 0 |
| Token jawab per pertanyaan | 1.739 | 1.585 | -154 |
| Latency (detik) | 5,09 | 3,10 | tidak sebanding: putaran beku melewati tahap tulis ulang |

Per jenis pertanyaan:

| Jenis | Faithfulness | Relevansi | Hit retrieval |
|---|---|---|---|
| eksplisit (6) | 4,92 → 7,67 | 8,67 → 9,00 | 1,00 → 1,00 |
| gabungan (5) | 6,20 → 7,00 | 7,40 → 7,20 | 0,40 → 0,40 |
| di luar cakupan (3) | 10,00 → 10,00 | 8,00 → 8,33 | - |

Faithfulness naik di 8 dari 14 pertanyaan, sama di 6 (3 di antaranya sudah 10 di baseline),
dan tidak turun di satu pun. Pola yang sama muncul di putaran tanpa pembekuan (rata-rata 8,14),
jadi kenaikannya konsisten, bukan kebetulan satu putaran.

### Putaran pertama tanpa pembekuan (`prompt-v1-1`), untuk dokumentasi

Faithfulness 8,14, tetapi hit retrieval turun ke 0,64 dan relevansi pertanyaan gabungan turun
ke 5,80. Itu bukan efek prompt: q07 kehilangan semua pasal kuncinya dari top-4 karena kueri
tulis ulang yang baru, lalu dijawab "tidak ditemukan" (relevansi 1,0). Putaran ini
menunjukkan bahwa tanpa pembekuan, variasi penulis ulang saja bisa menggeser metrik retrieval
sebesar itu antarputaran.

### Analisis (draf)

- **Membaik:** faithfulness naik terutama di pertanyaan eksplisit (q01 3,0 → 10,0; q05 4,0 → 9,0;
  q06 5,0 → 8,0). Token turun karena jawaban lebih pendek. Penolakan 3/3 tetap.
- **Belum beres:**
  - q03 masih 3,0 (naik dari 2,5). Model menulis syarat usia dan kawin sebagai kumulatif ("dan"),
    padahal Perpres 96/2018 Pasal 15 menyatakan alternatif ("atau"); ini kesalahan isi, bukan
    sekadar tambahan. Masih ada kalimat penutup tentang tempat pengajuan yang tidak ada di
    konteks.
  - q09 dan q10 (hit retrieval gagal di kedua putaran) dan q11 (hit gagal, dijawab "tidak
    ditemukan", relevansi 2,0): masalah retrieval, tidak tersentuh oleh perubahan prompt.
- **Dugaan penyebab:** butir 4 efektif mengurangi karangan terstruktur, tetapi model masih
  menambah kalimat penutup bergaya ramah dan salah membaca "atau" menjadi "dan".
- **Keputusan:** pakai `answer-v1.1` sebagai v1 final. Iterasi berikutnya sebaiknya menyasar
  retrieval pada pertanyaan gabungan (q09 sampai q11), dengan kueri tulis ulang tetap dibekukan
  agar perbandingannya bersih.

## Iterasi 2: `TOP_K` 4 → 6

- **Masalah yang terlihat:** hit retrieval 0,73 pada pertanyaan gabungan (0,40): q09, q10, dan
  q11 tidak memuat pasal kunci di top-4, sehingga q11 dijawab "tidak ditemukan" (relevansi 2,0).
- **Diagnosis:** retrieval. Dugaan awal: pasal kunci hanya sedikit di bawah batas top-4.
- **Parameter yang diubah:** hanya `DUKCAPIL_TOP_K` (4 → 6). Prompt tetap `answer-v1.1`,
  kueri tulis ulang dibekukan dari `baseline`. Pembandingnya `prompt-v1-1-frozen`.
- **Perintah:**
  `DUKCAPIL_TOP_K=6 python scripts/run-evaluation.py --run-name top-k-6 --reuse-rewrites-from baseline`

| Metrik | iterasi 1 (k=4) | iterasi 2 (k=6) | Selisih |
|---|---|---|---|
| Faithfulness | 7,93 | 8,71 | +0,78 |
| Relevansi | 8,21 | 8,14 | -0,07 |
| Hit retrieval | 0,73 | 0,73 | 0 |
| Penolakan benar | 1,00 | 1,00 | 0 |
| Token jawab per pertanyaan | 1.585 | 2.022 | +437 (+28%) |

Per jenis: faithfulness eksplisit 7,67 → 8,00, gabungan 7,00 → 8,80, di luar cakupan 10 → 10;
relevansi gabungan 7,20 → 7,40, di luar cakupan 8,33 → 7,33.

- **Analisis (draf):**
  - Hit retrieval **tidak berubah**: q09, q10, q11 tetap meleset di top-6. Dugaan awal salah;
    memperlebar top-k tidak memperbaiki retrieval.
  - Faithfulness naik (terbesar q09 4,0 → 9,0 dan q03 3,0 → 6,0), tetapi sebagian besar kenaikan
    ini kemungkinan bukan karena pasal kunci masuk (hit tidak berubah), melainkan konteks
    tambahan yang membuat model lebih sering menemukan butir yang sah. Juri tidak dapat
    diatur ke suhu 0 dan jawaban Groq tidak deterministik, jadi selisih sekitar 0,8 belum bisa
    dibedakan pasti dari variasi (beberapa pertanyaan turun 1 poin: q02, q05).
  - Biaya: +28% token per pertanyaan, penting karena batas Groq tier gratis per menit/hari.
  - Peringkat pasal kunci dengan kueri beku (top-60), diukur terpisah:

    | Pertanyaan | Pasal kunci | Pertanyaan saja | Tulis ulang saja | Digabung (dipakai sistem) |
    |---|---|---|---|---|
    | q09 | Perpres 96/2018 Pasal 17 | **1** | 52 | 52 |
    | q09 | Perpres 96/2018 Pasal 11 | 8 | 29 | 29 |
    | q10 | Permendagri 74/2022 Pasal 1 | 10 | 7 | 7 |
    | q11 | Permendagri 7/2019 Pasal 5, 6, 7 | di luar 60 | di luar 60 | di luar 60 |
    | q03 | Perpres 96/2018 Pasal 15 | di luar 60 | **1** | 1 |

- **Temuan penyebab (penting):** `ChunkIndex.search` menggabungkan kueri dengan mengambil skor
  cosine tertinggi per chunk. Kueri tulis ulang yang padat kata kunci selalu berskor lebih
  tinggi (mis. 0,70) daripada pertanyaan asli (0,57), sehingga hasil pertanyaan asli hampir
  tak pernah menang dan tulis ulang praktis **menggantikan** pertanyaan. Akibatnya q09 kehilangan
  Pasal 17 yang berada di peringkat 1 untuk pertanyaan asli, sedangkan q03 hanya terbantu oleh
  tulis ulang. Skor dari dua kueri tidak sebanding secara langsung. Penggabungan berbasis
  peringkat (reciprocal rank fusion) tidak bergantung pada skala skor.
- **Keputusan:** belum diputuskan. `TOP_K=6` menaikkan faithfulness tanpa memperbaiki
  retrieval dan menambah token 28%. Usulan iterasi 3: ganti penggabungan skor-maks dengan
  reciprocal rank fusion (satu parameter: metode fusi), kueri tetap beku.

## Iterasi 3: penggabungan kueri skor-maks → reciprocal rank fusion (RRF)

- **Masalah yang terlihat:** pada iterasi 2, penggabungan skor-maks membuat tulis ulang
  menggantikan pertanyaan asli (mis. q09 kehilangan Pasal 17 yang peringkat 1 untuk
  pertanyaan asli).
- **Diagnosis:** retrieval, khususnya cara menggabungkan dua kueri yang skornya tidak sebanding.
- **Parameter yang diubah:** hanya metode fusi (`DUKCAPIL_FUSION=rrf`, konstanta 60, kedalaman
  30 per kueri). `TOP_K` kembali 4, prompt `answer-v1.1`, kueri beku dari `baseline`.
  Pembandingnya `prompt-v1-1-frozen`.
- **Perintah:**
  `DUKCAPIL_FUSION=rrf python scripts/run-evaluation.py --run-name rrf --reuse-rewrites-from baseline`

| Metrik | iterasi 1 (skor-maks) | iterasi 3 (RRF) | Selisih |
|---|---|---|---|
| Faithfulness | 7,93 | 7,93 | 0 |
| Relevansi | 8,21 | 7,50 | -0,71 |
| Hit retrieval | 0,73 | 0,73 | 0 |
| Penolakan benar | 1,00 | 1,00 | 0 |
| Token jawab per pertanyaan | 1.585 | 1.622 | +37 |

Per jenis: hit eksplisit 1,00 → 0,83, hit gabungan 0,40 → 0,60; relevansi eksplisit
9,00 → 7,83, di luar cakupan 8,33 → 7,00.

- **Analisis (draf):**
  - Hit rate netto **tidak berubah**, tetapi isinya bergeser: q09 membaik (Pasal 17 kembali masuk
    top-4), sedangkan q01 memburuk (Pasal 79A keluar dari top-4, dijawab "tidak ditemukan",
    relevansi 10 → 2). q03, q10, dan q11 tidak berubah hit-nya.
  - Penyebab q01: RRF memberi bobot pada konsensus antar daftar. Pasal 79A hanya muncul di
    daftar tulis ulang (peringkat 1), sedangkan Permendagri 108/2019 Pasal 38 dan 37 muncul di
    kedua daftar sehingga skor gabungannya lebih tinggi. RRF unggul saat dua kueri sama-sama
    menemukan jawaban, tetapi merugikan jawaban yang hanya ditemukan satu kueri di
    peringkat 1.
  - Pola dari data peringkat: ketiga pasal kunci yang bermasalah (q01, q03, q09) berada di
    **peringkat 1 pada salah satu kueri**. Hipotesis iterasi berikutnya: gabungan bergantian
    (round-robin) yang menjamin peringkat teratas tiap kueri ikut masuk. Hipotesis ini diturunkan
    dari 3 pertanyaan yang sudah dilihat, jadi risiko overfitting tinggi dan perlu diuji pada
    pertanyaan baru.
  - Relevansi turun karena q01, serta q12 (9 → 6) yang tidak berkaitan dengan fusi (jawaban
    penolakan yang dinilai juri berbeda): selisih seperti ini masuk dalam variasi juri.
- **Keputusan:** **tidak memakai RRF**. Tidak menaikkan hit rate dan menurunkan relevansi.
  Pengaturan akhir sementara: skor-maks, `TOP_K=4`, `answer-v1.1`.

## Keterbatasan pengukuran yang sudah diketahui

- Juri Sonnet 5.5 tidak dapat diatur ke suhu 0 (API menolak `temperature`), jadi skor juri bisa
  bervariasi antarputaran. Belum diukur seberapa besar; satu cara: nilai ulang satu putaran yang
  sama dua kali dan bandingkan.
- Penjawab Groq juga tidak deterministik (jawaban sedikit berbeda antarputaran walau konteks
  sama).
- Satu putaran per konfigurasi, 14 pertanyaan: selisih kecil (< ±1 poin) belum bisa dibedakan
  dari variasi.
- Penulis ulang kueri (Sonnet) kadang menyisipkan pengetahuannya sendiri ke kueri, bahkan
  nomor pasalnya (kueri q01 memuat "Pasal 79A"). Itu membantu retrieval pada set uji ini
  tetapi tidak mencerminkan kinerja untuk pertanyaan tanpa pengetahuan tersebut, dan
  menyiratkan hit rate sebagian bergantung pada pengetahuan model, bukan hanya pada korpus.
- Pembekuan kueri hanya menetapkan bagian retrieval; jawaban dan juri tetap bervariasi.
