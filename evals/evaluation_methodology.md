# Metodologi Evaluasi Prototipe RAG v1: DUKCAPIL-Pintar

Dokumen ini menguraikan metodologi pengujian DUKCAPIL-Pintar, yaitu aspek yang diukur,
pertanyaan uji yang digunakan, cara penilaian, serta temuan yang diperoleh. Seluruh angka
bersumber dari hasil putaran evaluasi yang tersimpan pada direktori `evals/runs/`.

## 1. Tujuan evaluasi

Evaluasi bertujuan menilai apakah DUKCAPIL-Pintar dapat diandalkan dalam menjawab pertanyaan
warga mengenai dokumen kependudukan. Empat aspek yang diperiksa adalah sebagai berikut.

1. Jawaban sesuai dengan pertanyaan yang diajukan (relevansi).
2. Isi jawaban tidak melampaui teks peraturan yang diambil oleh sistem (kesetiaan pada sumber).
3. Pasal yang diambil merupakan pasal yang tepat.
4. Untuk pertanyaan di luar cakupan, sistem menyatakan bahwa informasi tidak ditemukan dan tidak
   memberikan jawaban tanpa dasar sumber.

Pengukuran menggunakan empat dimensi yang disyaratkan CPMK 2, yaitu relevansi, faithfulness,
biaya, dan latency. Dua ukuran tambahan yang tidak bergantung pada penilaian model, yaitu hit
retrieval dan penolakan benar, ditambahkan karena skor juri berbasis model bahasa besar (LLM)
hanya merupakan perkiraan sehingga diperlukan pembanding yang dapat dihitung secara langsung.

## 2. Set uji

### Komposisi

Set uji (`evals/test_set.jsonl`) terdiri atas 14 pertanyaan, yaitu 6 pertanyaan eksplisit,
5 pertanyaan gabungan, dan 3 pertanyaan di luar cakupan.

- **Eksplisit.** Jawabannya terdapat pada satu pasal (atau dua pasal dalam satu peraturan).
  Kategori ini memastikan fungsi paling mendasar berjalan: pasal yang tepat dapat ditemukan dan
  jawaban tidak menyimpang dari isinya.
- **Gabungan.** Jawabannya memerlukan beberapa pasal atau beberapa peraturan sekaligus.
  Kategori ini lebih menyerupai pertanyaan warga yang sebenarnya dan menguji proses pencarian
  pasal secara lebih berat.
- **Di luar cakupan.** Persoalannya merupakan kewenangan instansi lain (paspor, SIM) atau berupa
  praktik di satu daerah. Jawaban yang benar adalah "tidak ditemukan".

Dua pertanyaan sengaja dirancang sebagai pertanyaan jebakan.

- **q05** (pelapor kematian). UU 24/2013 mengubah pelapor dari "keluarganya" menjadi ketua rukun
  tetangga. Jawaban yang masih merujuk UU 23/2006 berarti tidak mutakhir.
- **q10** (kontrak kerja 8 bulan di kota lain). Penduduk nonpermanen dibatasi paling lama
  1 tahun, sehingga kasus 8 bulan seharusnya termasuk. Pertanyaan ini menguji apakah batas
  tersebut terbaca.

Terdapat satu keputusan yang menyimpang dari rencana awal. Pertanyaan tentang pencatatan nikah
siri di KUA pada Submission Minggu 2 **tidak digunakan sebagai pertanyaan di luar cakupan**.
Pemeriksaan menunjukkan bahwa korpus memuat UU 23/2006 Pasal 34 dan 36 tentang pelaporan
perkawinan, termasuk peran KUA, sehingga pertanyaan tersebut sebagian dapat dijawab. Sebagai
penggantinya digunakan pertanyaan tentang SIM dan jam buka loket Disdukcapil di satu kota.

### Penyusunan dan verifikasi kunci jawaban

Pertanyaan dan kriteria disusun berdasarkan teks pasal pada korpus, bukan berdasarkan ingatan
atau salinan langsung dari Submission. Setiap pasal kunci dibaca langsung pada teks hasil
ekstraksi. Selanjutnya, 27 frasa penting pada kriteria dicocokkan secara otomatis dengan teks
pasalnya, dan seluruhnya sesuai.

Proses ini sekaligus mengungkap satu masalah pada korpus: judul "Pasal 11" pada Perpres 96/2018
tertulis "Pasal 1 1" di berkas PDF sehingga isinya terbaca sebagai bagian dari Pasal 10. Masalah
tersebut telah diperbaiki pada `ingestion.py` dan dilengkapi pengujian otomatis.

Pertanyaan dan kriteria disusun dari teks pasal pada korpus, dengan bantuan alat berbasis model
bahasa untuk menghasilkan draf awal. Seluruh pasal kunci dan kriteria pada versi akhir diperiksa
dan dicocokkan dengan teks korpus oleh kelompok.

### Tabel pertanyaan dan kriteria jawaban yang diterima

Tabel berikut merupakan ringkasan; teks lengkap tersedia pada `test_set.jsonl`.

| ID  | Jenis           | Pertanyaan (ringkas)                                   | Pasal kunci                                                                  | Butir yang harus muncul                                                                             |
| --- | --------------- | ------------------------------------------------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| q01 | eksplisit       | Apakah mengurus dokumen kependudukan dipungut biaya?   | UU 24/2013 Pasal 79A                                                         | Tidak dipungut biaya                                                                                |
| q02 | eksplisit       | Berapa lama KTP-el/KK selesai setelah syarat lengkap?  | Permendagri 19/2018 Pasal 3                                                  | 1 jam, paling lama 24 jam; pengecualian gangguan jaringan                                           |
| q03 | eksplisit       | Syarat KTP-el baru bagi WNI                            | Perpres 96/2018 Pasal 15                                                     | Usia 17 tahun, sudah kawin, atau pernah kawin; dan KK                                               |
| q04 | eksplisit       | Berkas KIA anak 8 tahun                                | Permendagri 2/2016 Pasal 3                                                   | Akta kelahiran, KK asli, KTP-el kedua orang tua, pas foto 2x3 (2 lembar)                            |
| q05 | eksplisit       | Siapa wajib lapor kematian, berapa hari?               | UU 24/2013 Pasal 44                                                          | Ketua RT; paling lambat 30 hari                                                                     |
| q06 | eksplisit       | Batas lapor kelahiran dan akibat terlambat             | UU 24/2013 Pasal 27, 32                                                      | 60 hari; lewat 60 hari memerlukan keputusan Kepala Instansi Pelaksana                               |
| q07 | gabungan        | Akta lahir, anak lahir di kota lain, tanpa buku nikah  | Perpres 96/2018 Pasal 34; Permendagri 108/2019 Pasal 43; UU 24/2013 Pasal 27 | Syarat pencatatan; surat pernyataan tanggung jawab mutlak + 2 saksi; lapor 60 hari                  |
| q08 | gabungan        | Dokumen hilang akibat banjir                           | Perpres 96/2018 Pasal 29; Permendagri 96/2019 Pasal 11; UU 23/2006 Pasal 81  | Penduduk rentan didata Disdukcapil; tata cara pendataan; surat keterangan pengganti tanda identitas |
| q09 | gabungan        | Pindah Bandung ke Semarang: dokumen KTP-el dan KK baru | Perpres 96/2018 Pasal 17, 11                                                 | Surat keterangan pindah; KK; buku nikah/akta perceraian                                             |
| q10 | gabungan        | Kontrak 8 bulan di kota lain, wajib daftar?            | Permendagri 74/2022 Pasal 1, 2                                               | Penduduk nonpermanen (maks. 1 tahun); wajib daftar dengan NIK; daring atau manual                   |
| q11 | gabungan        | Mengurus KK/KTP-el/akta tanpa datang ke kantor         | Permendagri 7/2019 Pasal 5, 6, 7                                             | Layanan Adminduk daring: pendaftaran penduduk dan pencatatan sipil                                  |
| q12 | di luar cakupan | Biaya dan syarat paspor                                | (tidak ada)                                                                  | "Tidak ditemukan"; tidak menyebut angka                                                             |
| q13 | di luar cakupan | Perpanjang SIM                                         | (tidak ada)                                                                  | "Tidak ditemukan"; tidak menyebut prosedur                                                          |
| q14 | di luar cakupan | Jam buka loket Disdukcapil Surabaya                    | (tidak ada)                                                                  | "Tidak ditemukan"; tidak memberikan informasi tanpa dasar                                           |

## 3. Metrik

| Dimensi         | Cara mengukur                                                                                               | Skala    |
| --------------- | ----------------------------------------------------------------------------------------------------------- | -------- |
| Relevansi       | Juri LLM (Sonnet 5.5), prompt `judge-v1`                                                                  | 0-10     |
| Faithfulness    | Juri memecah jawaban menjadi klaim, setiap klaim DIDUKUNG/TIDAK DIDUKUNG konteks (Bab 7.4), skor akhir 0-10 | 0-10     |
| Biaya           | Jumlah token jawaban per pertanyaan (masuk + keluar) dari `response.usage`, tanpa harga                   | token    |
| Latency         | Waktu dari pertanyaan sampai jawaban, per tahap                                                             | detik    |
| Hit retrieval   | Minimal satu pasal kunci masuk top-k; hanya untuk pertanyaan berpasal kunci (11)                            | proporsi |
| Penolakan benar | Pertanyaan di luar cakupan dijawab "Informasi tidak ditemukan di dokumen"                                   | proporsi |

## 4. Juri dan alasan pemilihannya

- **Juri: Claude Sonnet 5.5.** Penjawab utama yang digunakan adalah Groq gpt-oss-120b, sehingga
  juri berbeda dari penjawab dan tidak menilai jawabannya sendiri. Prompt juri diberi nomor versi
  (`judge-v1`) agar dapat ditelusuri.
- **Anthropic menggantikan Gemini.** RPS menyebut Gemini sebagai salah satu penyedia, tetapi
  Anthropic digunakan sebagai juri, penulis ulang kueri, dan penjawab pembanding (Haiku 5.5).
  Karena layanan tersebut berbayar, penggunaannya dicatat pada dokumen ini.
- **Suhu juri tidak dapat ditetapkan pada 0.** Rancangan awal menjalankan juri pada suhu 0 agar
  hasilnya konsisten. Namun, API Sonnet 5.5 menolak parameter `temperature`, sehingga skor juri
  dapat berbeda sedikit antarputaran.
- **Batas token juri dinaikkan menjadi 8.000.** Pada percobaan awal, batas 1.500 token
  menyebabkan banyak skor faithfulness kosong. Penyebabnya, token proses berpikir (*thinking*)
  Sonnet turut dihitung terhadap batas tersebut sehingga teks penilaian terpotong. Saat ini,
  respons yang terpotong diperlakukan sebagai galat dan tidak lagi menghasilkan skor kosong.
- Skor juri tetap merupakan perkiraan (Bab 7.4). Oleh karena itu, tiga skor terendah diperiksa
  secara manual (lihat bagian 6).

## 5. Reproduksi hasil

```
python scripts/build-index.py
python scripts/run-evaluation.py --run-name baseline
python scripts/run-evaluation.py --run-name prompt-v1-1-frozen --reuse-rewrites-from baseline
DUKCAPIL_TOP_K=6 python scripts/run-evaluation.py --run-name top-k-6 --reuse-rewrites-from baseline
DUKCAPIL_FUSION=rrf python scripts/run-evaluation.py --run-name rrf --reuse-rewrites-from baseline
```

Parameter setiap putaran tersimpan pada `evals/runs/<run-name>/run_config.json`. Putaran
`baseline` menggunakan prompt `answer-v1` (teksnya tersedia pada `prompt_history.md`),
sedangkan putaran lainnya menggunakan `answer-v1.1`. Opsi `--reuse-rewrites-from` memakai
kembali kueri tulis ulang dari putaran pembanding karena penulis ulang tidak selalu
menghasilkan kueri yang sama (diuraikan pada bagian 8).

## 6. Hasil

**Putaran awal (`baseline`)** dengan Groq gpt-oss-120b, embedding mpnet, top-4, dan prompt
`answer-v1`.

| Jenis           | n  | Relevansi | Faithfulness | Hit retrieval | Penolakan benar | Token jawab | Latency (detik) |
| --------------- | -- | --------- | ------------ | ------------- | --------------- | ----------- | --------------- |
| eksplisit       | 6  | 8,67      | 4,92         | 1,00          | -               | 1.885       | 5,49            |
| gabungan        | 5  | 7,40      | 6,20         | 0,40          | -               | 1.955       | 5,55            |
| di luar cakupan | 3  | 8,00      | 10,00        | -             | 1,00            | 1.087       | 3,54            |
| semua           | 14 | 8,07      | 6,46         | 0,73          | 1,00            | 1.739       | 5,09            |

**Ringkasan iterasi.** Rincian dan analisis tersedia pada `iteration_log.md`. Pada tiga putaran
terakhir, kueri tulis ulang dibekukan dari putaran `baseline`.

| Putaran            | Perubahan              | Faithfulness | Relevansi | Hit retrieval | Token jawab |
| ------------------ | ---------------------- | ------------ | --------- | ------------- | ----------- |
| baseline           | -                      | 6,46         | 8,07      | 0,73          | 1.739       |
| prompt-v1-1-frozen | prompt `answer-v1.1` | 7,93         | 8,21      | 0,73          | 1.585       |
| top-k-6            | `TOP_K` 4 → 6       | 8,71         | 8,14      | 0,73          | 2.022       |
| rrf                | fusi skor-maks → RRF  | 7,93         | 7,50      | 0,73          | 1.622       |

Latency tidak dibandingkan antarputaran yang kueri tulis ulangnya dibekukan karena tahap
penulisan ulang kueri dilewati pada putaran tersebut.

**Pemeriksaan manual tiga skor faithfulness terendah pada `baseline`.** Hasil pemeriksaan
menunjukkan bahwa penilaian juri sesuai pada ketiganya.

| Pertanyaan | Skor juri | Hasil pemeriksaan                                                                                                                                                                              |
| ---------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| q03        | 2,5       | Inti jawaban benar, tetapi model menambahkan berkas dan langkah yang tidak terdapat pada konteks (misalnya fotokopi KTP-el lama, bukti usia, formulir, dan perekaman biometrik).               |
| q01        | 3,0       | Klaim mengenai biaya didukung oleh Pasal 79A. Skor menurun akibat checklist dan langkah umum yang tidak tertulis pada konteks.                                                                 |
| q09        | 3,0       | Penyebabnya kegagalan retrieval: konteks yang diambil memuat pasal KIA dan penduduk nonpermanen, bukan Pasal 17 dan 11 Perpres 96/2018, sehingga jawaban menggunakan pasal yang tidak relevan. |

## 7. Iterasi

Dilakukan tiga iterasi (rincian pada `iteration_log.md`).

1. **Prompt (`answer-v1` → `answer-v1.1`).** Faithfulness meningkat 1,47 poin dan tidak terdapat
   pertanyaan yang skornya menurun.
2. **`TOP_K` 4 → 6.** Faithfulness meningkat kembali, tetapi hit retrieval tidak membaik dan
   jumlah token per pertanyaan bertambah 28%.
3. **Reciprocal rank fusion (RRF).** Hit rate tidak meningkat dan relevansi menurun, sehingga
   metode ini tidak digunakan.

Konfigurasi akhir sementara adalah penggabungan skor-maks, `TOP_K=4`, dan prompt `answer-v1.1`.

## 8. Keterbatasan

Beberapa keterbatasan berikut perlu dinyatakan secara terbuka.

- **Skor juri tidak sepenuhnya konsisten.** Karena parameter `temperature` tidak dapat
  ditetapkan, penilaian terhadap jawaban yang sama dapat berbeda sedikit. Besarnya perbedaan
  belum diukur; pengukuran dapat dilakukan dengan menilai ulang satu putaran yang sama sebanyak
  dua kali.
- **Penulis ulang kueri tidak konsisten.** Antara dua putaran tanpa pembekuan, kueri dan hasil
  top-4 berbeda pada 14 dari 14 pertanyaan. Oleh karena itu, iterasi menggunakan kueri yang
  dibekukan.
- **Penulis ulang kueri dapat menyisipkan pengetahuannya sendiri**, bahkan menyebut nomor pasal
  (kueri q01 memuat "Pasal 79A"). Akibatnya, hit retrieval sebagian ditopang pengetahuan model,
  bukan semata-mata isi korpus, dan hasilnya belum tentu sama untuk pertanyaan lain.
- **Jawaban Groq tidak selalu identik** antarputaran.
- **Ukuran sampel kecil.** Pengujian hanya memakai 14 pertanyaan dengan satu putaran untuk setiap
  konfigurasi. Selisih di bawah sekitar 1 poin belum dapat dibedakan dari variasi acak. Hit
  retrieval pun hanya dihitung dari 11 pertanyaan.
- **Retrieval untuk pertanyaan gabungan masih lemah** (hit 0,40). Pasal kunci q09, q10, dan q11
  tidak masuk top-4 maupun top-6. Pada q11, pasal Permendagri 7/2019 bahkan tidak termasuk dalam
  60 peringkat teratas.
- **Masih terdapat kesalahan isi.** Pada q03, model menuliskan syarat usia dan status kawin
  seolah-olah harus dipenuhi keduanya ("dan"), padahal Pasal 15 menyatakannya sebagai pilihan
  ("atau").
- **Belum terdapat guardrail** selain instruksi "informasi tidak ditemukan". Hal ini disengaja
  karena versi 1 berfungsi sebagai pembanding; guardrail akan ditambahkan pada RTM 3.
- **Gagasan penggabungan bergantian (round-robin) belum teruji.** Gagasan ini diturunkan dari
  tiga pertanyaan yang telah diamati, sehingga berpotensi hanya sesuai dengan data ini
  (*overfitting*) dan perlu diuji pada pertanyaan baru.
