# Ringkasan evaluasi: prompt-v1-1

Parameter putaran ada di `run_config.json`. Skor juri adalah estimasi; periksa manual pertanyaan berskor terendah di bawah.

| Jenis | n | Relevansi | Faithfulness | Hit retrieval | Penolakan benar | Token jawab (masuk+keluar) | Latency (detik) |
|---|---|---|---|---|---|---|---|
| eksplisit | 6 | 9,67 | 7,67 | 1,00 | - | 1468,00 | 7,27 |
| gabungan | 5 | 5,80 | 7,60 | 0,20 | - | 1811,40 | 5,77 |
| di_luar_cakupan | 3 | 8,00 | 10,00 | - | 1,00 | 1200,00 | 3,42 |
| semua | 14 | 7,93 | 8,14 | 0,64 | 1,00 | 1533,21 | 5,91 |

## Skor faithfulness terendah (cek manual)

- q03 (faithfulness 4,0): Apa syarat membuat KTP-el baru bagi warga negara Indonesia?
- q09 (faithfulness 5,0): Saya pindah dari Bandung ke Semarang. Dokumen apa yang harus disiapkan supaya mendapat KTP-el dan KK baru di Semarang?
- q10 (faithfulness 6,0): Saya bekerja kontrak 8 bulan di kota lain dan tinggal di kos. Apakah saya wajib mendaftar sebagai penduduk di sana, dan bagaimana caranya?
