# Ringkasan evaluasi: rrf

Parameter putaran ada di `run_config.json`. Skor juri adalah estimasi; periksa manual pertanyaan berskor terendah di bawah.

| Jenis | n | Relevansi | Faithfulness | Hit retrieval | Penolakan benar | Token jawab (masuk+keluar) | Latency (detik) |
|---|---|---|---|---|---|---|---|
| eksplisit | 6 | 7,83 | 7,17 | 0,83 | - | 1667,50 | 5,06 |
| gabungan | 5 | 7,40 | 7,60 | 0,60 | - | 1831,60 | 2,76 |
| di_luar_cakupan | 3 | 7,00 | 10,00 | - | 1,00 | 1180,33 | 2,14 |
| semua | 14 | 7,50 | 7,93 | 0,73 | 1,00 | 1621,71 | 3,61 |

## Skor faithfulness terendah (cek manual)

- q03 (faithfulness 5,0): Apa syarat membuat KTP-el baru bagi warga negara Indonesia?
- q10 (faithfulness 5,0): Saya bekerja kontrak 8 bulan di kota lain dan tinggal di kos. Apakah saya wajib mendaftar sebagai penduduk di sana, dan bagaimana caranya?
- q02 (faithfulness 6,0): Berapa lama KTP-el atau Kartu Keluarga harus selesai setelah semua persyaratan saya lengkap?
