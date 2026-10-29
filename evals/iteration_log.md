# Catatan Iterasi

Pada setiap putaran hanya **satu** parameter yang diubah (Bab 7.6), kemudian hasilnya dibandingkan
dengan putaran sebelumnya. Angka bersumber dari `evals/runs/<run-name>/summary.md`.

## Iterasi 1: prompt penjawab `answer-v1` → `answer-v1.1`

- **Masalah yang teramati.** Pada putaran `baseline`, rata-rata faithfulness hanya 6,46. Skor
  terendah justru berada pada pertanyaan eksplisit (4,92), padahal pasal yang tepat telah
  ditemukan pada seluruh pertanyaan tersebut (hit retrieval 1,00). Contohnya q01 (3,0), q03 (2,5),
  dan q05 (4,0).
- **Diagnosis.** Pasal yang diambil telah tepat, tetapi jawaban kurang setia pada sumber.
  Dengan demikian, masalah terletak pada tahap generasi (prompt), bukan pada retrieval, sesuai
  panduan diagnosis pada Bab 7.6. Pemeriksaan manual terhadap q01 dan q03 menunjukkan bahwa
  penilaian juri sesuai: inti jawaban benar, tetapi model menambahkan checklist berkas dan
  langkah umum yang tidak terdapat pada teks pasal (misalnya "fotokopi", "KK asli", "mengisi
  formulir", dan "datang ke kantor"). Sumbernya adalah aturan nomor 4 pada prompt v1 yang
  mewajibkan format penjelasan, checklist, dan langkah, sehingga model terdorong mengisinya
  meskipun konteks tidak memuat informasi tersebut.
- **Parameter yang diubah.** Hanya aturan nomor 4 pada prompt: checklist dan langkah hanya
  boleh ditulis apabila terdapat pada konteks, dan bagian tersebut dihilangkan apabila tidak ada.
  Teks lama disimpan pada `prompt_history.md`. Model, embedding, `TOP_K`, dan penulis ulang kueri
  tidak diubah.
- **Perintah (perbandingan terkontrol):**
  `python scripts/run-evaluation.py --run-name prompt-v1-1-frozen --reuse-rewrites-from baseline`

### Perbandingan terkontrol: kueri tulis ulang dibekukan dari baseline

Penulis ulang kueri (Sonnet 5.5) tidak selalu menghasilkan kueri yang sama dan suhunya tidak
dapat diatur. Pada penjalanan pertama dengan prompt baru tanpa pembekuan (`prompt-v1-1`), kueri
tulis ulang berbeda pada 14 dari 14 pertanyaan. Akibatnya, hit retrieval ikut bergeser sehingga
perubahan skor tidak dapat dikaitkan dengan prompt.

Oleh karena itu, evaluasi dijalankan ulang sebagai `prompt-v1-1-frozen` dengan kueri tulis ulang
yang identik dengan `baseline`. Hasilnya, top-4 identik pada 14 dari 14 pertanyaan sehingga
selisih pada tabel berikut bersumber semata-mata dari perubahan prompt.

| Metrik | baseline | iterasi 1 | Selisih |
|---|---|---|---|
| Faithfulness | 6,46 | 7,93 | +1,47 |
| Relevansi | 8,07 | 8,21 | +0,14 |
| Hit retrieval | 0,73 | 0,73 | 0 (identik, sesuai rancangan) |
| Penolakan benar | 1,00 | 1,00 | 0 |
| Token jawab per pertanyaan | 1.739 | 1.585 | -154 |
| Latency (detik) | 5,09 | 3,10 | tidak sebanding: putaran beku melewati tahap tulis ulang |

Rincian per jenis pertanyaan:

| Jenis | Faithfulness | Relevansi | Hit retrieval |
|---|---|---|---|
| eksplisit (6) | 4,92 → 7,67 | 8,67 → 9,00 | 1,00 → 1,00 |
| gabungan (5) | 6,20 → 7,00 | 7,40 → 7,20 | 0,40 → 0,40 |
| di luar cakupan (3) | 10,00 → 10,00 | 8,00 → 8,33 | - |

Faithfulness meningkat pada 8 dari 14 pertanyaan, tetap pada 6 pertanyaan (3 di antaranya telah
bernilai 10 pada baseline), dan tidak menurun pada satu pun. Pola serupa juga tampak pada putaran
tanpa pembekuan (rata-rata 8,14), sehingga peningkatan tersebut konsisten dan bukan kebetulan
pada satu putaran.

### Putaran pertama tanpa pembekuan (`prompt-v1-1`), sebagai dokumentasi

Pada putaran ini faithfulness mencapai 8,14, tetapi hit retrieval turun menjadi 0,64 dan relevansi
pertanyaan gabungan turun menjadi 5,80. Penurunan tersebut bukan akibat prompt. Pada q07, seluruh
pasal kunci tidak lagi masuk top-4 akibat kueri tulis ulang yang baru, sehingga sistem menjawab
"tidak ditemukan" (relevansi 1,0). Hal ini menunjukkan bahwa variasi pada penulis ulang kueri saja
telah cukup untuk menggeser metrik retrieval sebesar itu.

### Analisis

- **Aspek yang membaik.** Peningkatan faithfulness paling besar terjadi pada pertanyaan eksplisit
  (q01 3,0 → 10,0; q05 4,0 → 9,0; q06 5,0 → 8,0). Jumlah token juga menurun karena jawaban
  menjadi lebih ringkas. Penolakan terhadap pertanyaan di luar cakupan tetap 3 dari 3.
- **Aspek yang belum teratasi.**
  - q03 masih rendah (3,0; sebelumnya 2,5). Model menuliskan syarat usia dan status kawin
    seolah-olah harus dipenuhi keduanya ("dan"), padahal Perpres 96/2018 Pasal 15 menyatakannya
    sebagai pilihan ("atau"). Hal ini merupakan kesalahan isi, bukan sekadar informasi
    tambahan. Selain itu, masih terdapat kalimat penutup mengenai tempat pengajuan yang tidak
    terdapat pada konteks.
  - q09 dan q10 (hit retrieval gagal pada kedua putaran) serta q11 (hit gagal, dijawab "tidak
    ditemukan", relevansi 2,0) merupakan masalah retrieval, sehingga tidak terpengaruh oleh
    perubahan prompt.
- **Dugaan penyebab.** Aturan nomor 4 yang baru berhasil mengurangi karangan langkah dan
  checklist, tetapi model masih cenderung menambahkan kalimat penutup yang bersifat ramah dan
  keliru membaca "atau" sebagai "dan".
- **Keputusan.** `answer-v1.1` ditetapkan sebagai prompt v1 final. Iterasi berikutnya diarahkan
  pada retrieval untuk pertanyaan gabungan (q09 sampai q11), dengan kueri tulis ulang tetap
  dibekukan agar perbandingan terkontrol.

## Iterasi 2: `TOP_K` 4 → 6

- **Masalah yang teramati.** Hit retrieval pertanyaan gabungan hanya 0,40. Pada q09, q10, dan
  q11, pasal kunci tidak terdapat pada top-4, sehingga q11 dijawab "tidak ditemukan"
  (relevansi 2,0).
- **Diagnosis.** Retrieval. Dugaan awal, pasal kunci berada sedikit di bawah batas top-4 sehingga
  cukup dengan memperlebar jangkauan.
- **Parameter yang diubah.** Hanya `DUKCAPIL_TOP_K` (4 → 6). Prompt tetap `answer-v1.1` dan
  kueri tulis ulang dibekukan dari `baseline`. Pembandingnya adalah `prompt-v1-1-frozen`.
- **Perintah:**
  `DUKCAPIL_TOP_K=6 python scripts/run-evaluation.py --run-name top-k-6 --reuse-rewrites-from baseline`

| Metrik | iterasi 1 (k=4) | iterasi 2 (k=6) | Selisih |
|---|---|---|---|
| Faithfulness | 7,93 | 8,71 | +0,78 |
| Relevansi | 8,21 | 8,14 | -0,07 |
| Hit retrieval | 0,73 | 0,73 | 0 |
| Penolakan benar | 1,00 | 1,00 | 0 |
| Token jawab per pertanyaan | 1.585 | 2.022 | +437 (+28%) |

Rincian per jenis: faithfulness eksplisit 7,67 → 8,00, gabungan 7,00 → 8,80, dan di luar cakupan
10 → 10; relevansi gabungan 7,20 → 7,40 dan di luar cakupan 8,33 → 7,33.

### Analisis

- **Hit retrieval tidak berubah.** Pasal kunci q09, q10, dan q11 tetap tidak muncul pada top-6.
  Dengan demikian, dugaan awal tidak terbukti: memperlebar top-k tidak memperbaiki retrieval.
- **Faithfulness meningkat** (terbesar pada q09, 4,0 → 9,0, dan q03, 3,0 → 6,0). Karena hit
  retrieval tidak berubah, peningkatan ini diduga bukan disebabkan masuknya pasal kunci.
  Penjelasan yang lebih mungkin adalah bahwa konteks tambahan membuat model lebih sering
  menemukan butir yang sah. Selisih sekitar 0,8 juga belum dapat dibedakan dari variasi, sebab
  juri tidak dapat ditetapkan pada suhu 0 dan jawaban Groq tidak selalu identik. Sebagian
  pertanyaan bahkan menurun 1 poin (q02 dan q05).
- **Biaya meningkat 28%** dalam jumlah token per pertanyaan. Hal ini penting karena kuota gratis
  Groq dibatasi per menit dan per hari.
- **Peringkat pasal kunci** dengan kueri beku (diamati hingga peringkat 60):

  | Pertanyaan | Pasal kunci | Pertanyaan saja | Tulis ulang saja | Digabung (dipakai sistem) |
  |---|---|---|---|---|
  | q09 | Perpres 96/2018 Pasal 17 | **1** | 52 | 52 |
  | q09 | Perpres 96/2018 Pasal 11 | 8 | 29 | 29 |
  | q10 | Permendagri 74/2022 Pasal 1 | 10 | 7 | 7 |
  | q11 | Permendagri 7/2019 Pasal 5, 6, 7 | di luar 60 | di luar 60 | di luar 60 |
  | q03 | Perpres 96/2018 Pasal 15 | di luar 60 | **1** | 1 |

- **Temuan penyebab yang penting.** Fungsi pencarian menggabungkan hasil dua kueri (pertanyaan
  asli dan hasil tulis ulang) dengan mengambil skor kemiripan tertinggi untuk setiap chunk.
  Kueri tulis ulang yang padat kata kunci hampir selalu memperoleh skor lebih tinggi (sekitar
  0,70) dibandingkan pertanyaan asli (sekitar 0,57), sehingga hasil dari pertanyaan asli hampir
  tidak pernah unggul. Secara praktis, hasil tulis ulang **menggantikan** pertanyaan asli. Hal
  ini menjelaskan mengapa q09 kehilangan Pasal 17 yang sebenarnya berada pada peringkat 1 untuk
  pertanyaan asli, sedangkan q03 justru terbantu oleh tulis ulang. Dengan kata lain, skor dari
  dua kueri tidak dapat dibandingkan secara langsung, sedangkan penggabungan berbasis peringkat
  (*reciprocal rank fusion*) tidak dipengaruhi oleh perbedaan skala skor tersebut.
- **Keputusan.** Belum diputuskan. `TOP_K=6` meningkatkan faithfulness tanpa memperbaiki
  retrieval dan menambah jumlah token sebesar 28%. Pengujian dilanjutkan pada iterasi 3, yaitu
  mengganti cara penggabungan dengan *reciprocal rank fusion* (satu parameter: metode fusi),
  dengan kueri tetap dibekukan.

## Iterasi 3: penggabungan skor-maks → reciprocal rank fusion (RRF)

- **Masalah yang teramati.** Berdasarkan iterasi 2, penggabungan skor-maks menyebabkan hasil
  tulis ulang menggantikan pertanyaan asli (misalnya q09 kehilangan Pasal 17 yang berperingkat 1
  untuk pertanyaan asli).
- **Diagnosis.** Retrieval, tepatnya cara menggabungkan dua kueri yang skornya tidak sebanding.
- **Parameter yang diubah.** Hanya metode fusi (`DUKCAPIL_FUSION=rrf`, konstanta 60, kedalaman
  30 per kueri). `TOP_K` dikembalikan ke 4, prompt tetap `answer-v1.1`, dan kueri dibekukan dari
  `baseline`. Pembandingnya adalah `prompt-v1-1-frozen`.
- **Perintah:**
  `DUKCAPIL_FUSION=rrf python scripts/run-evaluation.py --run-name rrf --reuse-rewrites-from baseline`

| Metrik | iterasi 1 (skor-maks) | iterasi 3 (RRF) | Selisih |
|---|---|---|---|
| Faithfulness | 7,93 | 7,93 | 0 |
| Relevansi | 8,21 | 7,50 | -0,71 |
| Hit retrieval | 0,73 | 0,73 | 0 |
| Penolakan benar | 1,00 | 1,00 | 0 |
| Token jawab per pertanyaan | 1.585 | 1.622 | +37 |

Rincian per jenis: hit retrieval eksplisit 1,00 → 0,83 dan gabungan 0,40 → 0,60; relevansi
eksplisit 9,00 → 7,83 dan di luar cakupan 8,33 → 7,00.

### Analisis

- **Hit rate keseluruhan tidak berubah, tetapi komposisinya bergeser.** q09 membaik (Pasal 17
  kembali masuk top-4), sedangkan q01 memburuk (Pasal 79A keluar dari top-4 sehingga dijawab
  "tidak ditemukan" dan relevansi turun dari 10 menjadi 2). q03, q10, dan q11 tidak berubah.
- **Penyebab q01 memburuk.** RRF memberi bobot lebih pada chunk yang muncul di kedua daftar
  (konsensus). Pasal 79A hanya muncul pada daftar tulis ulang (peringkat 1), sedangkan
  Permendagri 108/2019 Pasal 38 dan 37 muncul pada kedua daftar sehingga skor gabungannya lebih
  tinggi. Dengan demikian, RRF menguntungkan apabila kedua kueri sama-sama menemukan jawaban,
  tetapi merugikan jawaban yang hanya ditemukan oleh satu kueri pada peringkat 1.
- **Pola yang teramati.** Tiga pasal kunci yang bermasalah (q01, q03, dan q09) seluruhnya berada
  pada **peringkat 1 pada salah satu kueri**. Berdasarkan pola ini, diajukan gagasan untuk iterasi
  berikutnya, yaitu penggabungan bergantian (*round-robin*) yang menjamin peringkat teratas setiap
  kueri turut dimasukkan. Namun, gagasan ini diturunkan dari tiga pertanyaan yang telah diamati
  sehingga berisiko hanya sesuai dengan data ini (*overfitting*) dan perlu diuji pada pertanyaan
  baru.
- **Penurunan relevansi** terutama disebabkan oleh q01 serta q12 (9 → 6) yang tidak berkaitan
  dengan fusi. Pada q12, jawaban penolakan dinilai berbeda oleh juri, sehingga selisih semacam
  itu masih berada dalam rentang variasi juri.
- **Keputusan.** **RRF tidak digunakan** karena tidak meningkatkan hit rate dan menurunkan
  relevansi. Konfigurasi akhir sementara adalah skor-maks, `TOP_K=4`, dan `answer-v1.1`.

## Keterbatasan pengukuran yang telah diketahui

- Juri Sonnet 5.5 tidak dapat ditetapkan pada suhu 0 (API menolak `temperature`), sehingga skor
  dapat berbeda antarputaran. Besarnya perbedaan belum diukur. Salah satu caranya adalah menilai
  ulang satu putaran yang sama sebanyak dua kali, kemudian membandingkan hasilnya.
- Jawaban Groq juga tidak selalu identik antarputaran meskipun konteksnya sama.
- Pengujian hanya memakai 14 pertanyaan dengan satu putaran untuk setiap konfigurasi, sehingga
  selisih kecil (di bawah sekitar 1 poin) belum dapat dibedakan dari variasi acak.
- Penulis ulang kueri (Sonnet) kadang memasukkan pengetahuannya sendiri ke dalam kueri, bahkan
  nomor pasal (kueri q01 memuat "Pasal 79A"). Hal ini membantu retrieval pada set uji ini,
  tetapi hasilnya belum tentu sama untuk pertanyaan yang pasalnya tidak "dikenal" oleh model.
  Dengan kata lain, hit rate sebagian bergantung pada pengetahuan model, bukan hanya pada isi
  korpus.
- Pembekuan kueri hanya menyamakan bagian retrieval. Jawaban dan penilaian juri tetap dapat
  berbeda.
