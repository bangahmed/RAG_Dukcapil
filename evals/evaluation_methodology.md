# Metodologi Evaluasi Prototipe RAG v1: DUKCAPIL-Pintar

> **Status: draf.** Angka, tabel, dan perintah di bawah diambil dari hasil putaran evaluasi.
> Alasan perancangan (bagian 1, 2, dan 8) adalah usulan yang perlu Anda baca, ubah, dan tulis
> ulang dengan kata-kata sendiri, karena rancangan evaluasi harus hasil pemikiran Anda.

## 1. Tujuan evaluasi

Membuktikan bahwa prototipe (a) menjawab relevan dengan pertanyaan warga, (b) setia pada teks
regulasi di konteks, (c) menyebut pasal yang benar, dan (d) menolak pertanyaan di luar cakupan
dengan "informasi tidak ditemukan" alih-alih mengarang. Keempat hal itu diukur dengan empat
dimensi CPMK 2 (relevansi, faithfulness, biaya, latency) ditambah dua ukuran objektif (hit
retrieval, penolakan benar).

## 2. Set uji

**Komposisi 14 pertanyaan** (`evals/test_set.jsonl`): 6 eksplisit, 5 gabungan, 3 di luar cakupan.

- *Eksplisit*: jawaban ada pada satu pasal (atau dua pasal dari satu regulasi); menguji
  retrieval dasar dan kesetiaan jawaban.
- *Gabungan*: jawaban butuh beberapa pasal atau regulasi; menguji retrieval lintas dokumen.
- *Di luar cakupan*: kewenangan instansi lain atau praktik lokal; jawaban benar adalah
  "tidak ditemukan".
- Dua pertanyaan sengaja berupa jebakan: q05 (UU 24/2013 mengubah pelapor kematian dari
  keluarga menjadi ketua RT, jadi versi UU 23/2006 sudah tidak mutakhir) dan q10 (batas penduduk
  nonpermanen 1 tahun; kasusnya 8 bulan).
- Pertanyaan KUA/nikah siri dari Submission Minggu 2 **tidak dipakai sebagai di luar cakupan**:
  korpus memuat UU 23/2006 Pasal 34 dan 36 tentang pelaporan perkawinan, jadi pertanyaannya
  sebagian terjawab. Diganti SIM dan praktik loket daerah.

**Cara menyusun dan memverifikasi kunci jawaban.** Pertanyaan dan kriteria disusun dari teks
pasal di korpus. Setiap `expected_articles` dibaca langsung di teks hasil ekstraksi, dan 27
frasa kunci di kriteria dicocokkan otomatis ke teks pasalnya (semua cocok). Satu perbaikan
korpus lahir dari proses ini: judul "Pasal 11" di Perpres 96/2018 tertulis "Pasal 1 1" di PDF
sehingga isinya salah masuk ke Pasal 10; diperbaiki di `ingestion.py` dan diberi tes.

**Tabel pertanyaan dan kriteria jawaban diterima** (ringkas; teks lengkap di `test_set.jsonl`):

| ID | Jenis | Pertanyaan (ringkas) | Pasal kunci | Butir yang harus muncul |
|---|---|---|---|---|
| q01 | eksplisit | Apakah mengurus dokumen kependudukan dipungut biaya? | UU 24/2013 Pasal 79A | Tidak dipungut biaya |
| q02 | eksplisit | Berapa lama KTP-el/KK selesai setelah syarat lengkap? | Permendagri 19/2018 Pasal 3 | 1 jam, paling lama 24 jam; pengecualian gangguan jaringan |
| q03 | eksplisit | Syarat KTP-el baru bagi WNI | Perpres 96/2018 Pasal 15 | Usia 17 tahun, sudah kawin, atau pernah kawin; dan KK |
| q04 | eksplisit | Berkas KIA anak 8 tahun | Permendagri 2/2016 Pasal 3 | Akta kelahiran, KK asli, KTP-el kedua orang tua, pas foto 2x3 (2 lembar) |
| q05 | eksplisit | Siapa wajib lapor kematian, berapa hari? | UU 24/2013 Pasal 44 | Ketua RT; paling lambat 30 hari |
| q06 | eksplisit | Batas lapor kelahiran dan akibat terlambat | UU 24/2013 Pasal 27, 32 | 60 hari; lewat 60 hari butuh keputusan Kepala Instansi Pelaksana |
| q07 | gabungan | Akta lahir, anak lahir di kota lain, tanpa buku nikah | Perpres 96/2018 Pasal 34; Permendagri 108/2019 Pasal 43; UU 24/2013 Pasal 27 | Syarat pencatatan; surat pernyataan tanggung jawab mutlak + 2 saksi; lapor 60 hari |
| q08 | gabungan | Dokumen hilang akibat banjir | Perpres 96/2018 Pasal 29; Permendagri 96/2019 Pasal 11; UU 23/2006 Pasal 81 | Penduduk rentan didata Disdukcapil; tata cara pendataan; surat keterangan pengganti tanda identitas |
| q09 | gabungan | Pindah Bandung ke Semarang: dokumen KTP-el dan KK baru | Perpres 96/2018 Pasal 17, 11 | Surat keterangan pindah; KK; buku nikah/akta perceraian |
| q10 | gabungan | Kontrak 8 bulan di kota lain, wajib daftar? | Permendagri 74/2022 Pasal 1, 2 | Penduduk nonpermanen (maks. 1 tahun); wajib daftar dengan NIK; daring atau manual |
| q11 | gabungan | Mengurus KK/KTP-el/akta tanpa datang ke kantor | Permendagri 7/2019 Pasal 5, 6, 7 | Layanan Adminduk daring: pendaftaran penduduk dan pencatatan sipil |
| q12 | di luar cakupan | Biaya dan syarat paspor | (tidak ada) | "Tidak ditemukan"; tidak menyebut angka |
| q13 | di luar cakupan | Perpanjang SIM | (tidak ada) | "Tidak ditemukan"; tidak menyebut prosedur |
| q14 | di luar cakupan | Jam buka loket Disdukcapil Surabaya | (tidak ada) | "Tidak ditemukan"; tidak mengarang |

## 3. Metrik

| Dimensi | Cara mengukur | Skala |
|---|---|---|
| Relevansi | Juri LLM (Sonnet 5.5), prompt `judge-v1` | 0-10 |
| Faithfulness | Juri memecah jawaban menjadi klaim, tiap klaim DIDUKUNG/TIDAK DIDUKUNG konteks (Bab 7.4), skor akhir 0-10 | 0-10 |
| Biaya | Jumlah token jawaban per pertanyaan (masuk + keluar) dari `response.usage`, tanpa harga | token |
| Latency | Waktu dari pertanyaan sampai jawaban, per tahap | detik |
| Hit retrieval | Minimal satu pasal kunci masuk top-k; hanya untuk pertanyaan berpasal kunci (11) | proporsi |
| Penolakan benar | Pertanyaan di luar cakupan dijawab "Informasi tidak ditemukan di dokumen" | proporsi |

## 4. Juri dan alasannya

- Juri: Claude Sonnet 5.5, prompt diberi versi. Suhu tidak dapat diatur ke 0 karena API model
  ini menolak parameter `temperature`, sehingga skor juri bisa bervariasi antarputaran.
- Penjawab default: Groq `openai/gpt-oss-120b`, sehingga juri tidak menilai jawabannya sendiri.
- Anthropic dipakai sebagai pengganti Gemini (penyedia di RPS) untuk juri, penulis ulang kueri,
  dan penjawab pembanding berbayar.
- Token thinking Sonnet 5.5 ikut dihitung ke `max_tokens`; batas juri 8.000 token (pada 1.500
  token, teks juri terpotong dan skor hilang). Respons terpotong kini menjadi galat, bukan
  skor kosong.
- Keterbatasan: skor juri adalah estimasi (Bab 7.4); pemeriksaan manual atas skor terendah
  dicatat di bagian 6.

## 5. Cara mereproduksi

```
python scripts/build-index.py
python scripts/run-evaluation.py --run-name baseline
python scripts/run-evaluation.py --run-name prompt-v1-1-frozen --reuse-rewrites-from baseline
DUKCAPIL_TOP_K=6 python scripts/run-evaluation.py --run-name top-k-6 --reuse-rewrites-from baseline
DUKCAPIL_FUSION=rrf python scripts/run-evaluation.py --run-name rrf --reuse-rewrites-from baseline
```

Parameter tiap putaran tersimpan di `evals/runs/<run-name>/run_config.json`. Putaran
`baseline` dijalankan dengan prompt `answer-v1` (teks di `prompt_history.md`); putaran lain
memakai `answer-v1.1`. Opsi `--reuse-rewrites-from` memakai kueri tulis ulang dari putaran
pembanding karena penulis ulang tidak deterministik (lihat bagian 8).

## 6. Hasil

**Putaran awal (`baseline`)**, Groq gpt-oss-120b, embedding mpnet, top-4, prompt `answer-v1`:

| Jenis | n | Relevansi | Faithfulness | Hit retrieval | Penolakan benar | Token jawab | Latency (detik) |
|---|---|---|---|---|---|---|---|
| eksplisit | 6 | 8,67 | 4,92 | 1,00 | - | 1.885 | 5,49 |
| gabungan | 5 | 7,40 | 6,20 | 0,40 | - | 1.955 | 5,55 |
| di luar cakupan | 3 | 8,00 | 10,00 | - | 1,00 | 1.087 | 3,54 |
| semua | 14 | 8,07 | 6,46 | 0,73 | 1,00 | 1.739 | 5,09 |

**Ringkasan iterasi** (rincian dan analisis di `iteration_log.md`; kueri tulis ulang beku dari
`baseline` pada tiga putaran terakhir):

| Putaran | Perubahan | Faithfulness | Relevansi | Hit retrieval | Token jawab |
|---|---|---|---|---|---|
| baseline | - | 6,46 | 8,07 | 0,73 | 1.739 |
| prompt-v1-1-frozen | prompt `answer-v1.1` | 7,93 | 8,21 | 0,73 | 1.585 |
| top-k-6 | `TOP_K` 4 → 6 | 8,71 | 8,14 | 0,73 | 2.022 |
| rrf | fusi skor-maks → RRF | 7,93 | 7,50 | 0,73 | 1.622 |

Latency tidak dibandingkan antarputaran beku karena tahap tulis ulang dilewati.

**Cek manual tiga skor faithfulness terendah di `baseline`:**

| Pertanyaan | Skor juri | Hasil cek |
|---|---|---|
| q03 | 2,5 (juri benar) | Inti benar, tetapi jawaban menambah berkas dan langkah yang tidak ada di konteks (mis. fotokopi KTP-el lama, bukti usia, formulir, foto biometrik). |
| q01 | 3,0 (juri benar) | Klaim biaya didukung (Pasal 79A); skor turun karena checklist dan langkah umum yang tidak tertulis di konteks. |
| q09 | 3,0 (juri benar) | Kegagalan retrieval: konteks memuat pasal KIA dan penduduk nonpermanen, bukan Pasal 17 dan 11 Perpres 96/2018, sehingga jawaban memakai pasal yang tidak relevan. |

## 7. Iterasi

Lihat `iteration_log.md`. Ringkasnya: iterasi 1 (prompt) menaikkan faithfulness +1,47 tanpa ada
pertanyaan yang turun; iterasi 2 (`TOP_K=6`) menaikkan faithfulness lagi tetapi tidak
memperbaiki hit retrieval dan menambah token 28%; iterasi 3 (RRF) tidak menaikkan hit rate dan
menurunkan relevansi, sehingga tidak dipakai. Pengaturan akhir sementara: skor-maks,
`TOP_K=4`, `answer-v1.1`.

## 8. Keterbatasan

- **Juri tidak deterministik**: API Sonnet 5.5 menolak `temperature`. Belum diukur seberapa
  besar variasinya; satu cara: menilai ulang satu putaran yang sama dua kali.
- **Penulis ulang kueri tidak deterministik**: antara dua putaran tanpa pembekuan, kueri dan
  himpunan top-4 berbeda di 14 dari 14 pertanyaan. Karena itu iterasi memakai kueri beku.
- **Penulis ulang menyisipkan pengetahuan model**, bahkan nomor pasal (kueri q01 memuat "Pasal
  79A"), sehingga hit retrieval sebagian bergantung pada pengetahuan model, bukan hanya korpus.
- **Penjawab Groq tidak deterministik**: jawaban sedikit berbeda antarputaran.
- **Sampel kecil**: 14 pertanyaan dan satu putaran per konfigurasi; selisih di bawah ±1 poin
  belum bisa dibedakan dari variasi. Hit retrieval dihitung dari 11 pertanyaan.
- **Retrieval pertanyaan gabungan masih lemah** (hit 0,40): q09, q10, q11 tidak memuat pasal
  kunci di top-4 maupun top-6. Pasal Permendagri 7/2019 (q11) tidak masuk 60 besar sama sekali.
- **Sisa kesalahan isi**: q03 masih menulis syarat usia dan kawin sebagai kumulatif ("dan"),
  padahal Pasal 15 menyatakan alternatif ("atau").
- **Tanpa guardrail** selain instruksi "tidak ditemukan" (disengaja sebagai baseline v1;
  guardrail ditambahkan di RTM 3).
- **Hipotesis round-robin untuk fusi kueri** diturunkan dari 3 pertanyaan yang sudah terlihat
  dan belum diuji pada pertanyaan baru.
