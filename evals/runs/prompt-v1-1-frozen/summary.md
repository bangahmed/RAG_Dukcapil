# Ringkasan evaluasi: prompt-v1-1-frozen

Parameter putaran ada di `run_config.json`. Skor juri adalah estimasi; periksa manual pertanyaan berskor terendah di bawah.

| Jenis | n | Relevansi | Faithfulness | Hit retrieval | Penolakan benar | Token jawab (masuk+keluar) | Latency (detik) |
|---|---|---|---|---|---|---|---|
| eksplisit | 6 | 9,00 | 7,67 | 1,00 | - | 1636,83 | 3,79 |
| gabungan | 5 | 7,20 | 7,00 | 0,40 | - | 1798,40 | 3,24 |
| di_luar_cakupan | 3 | 8,33 | 10,00 | - | 1,00 | 1126,67 | 1,48 |
| semua | 14 | 8,21 | 7,93 | 0,73 | 1,00 | 1585,21 | 3,10 |

## Skor faithfulness terendah (cek manual)

- q03 (faithfulness 3,0): Apa syarat membuat KTP-el baru bagi warga negara Indonesia?
- q09 (faithfulness 4,0): Saya pindah dari Bandung ke Semarang. Dokumen apa yang harus disiapkan supaya mendapat KTP-el dan KK baru di Semarang?
- q10 (faithfulness 6,0): Saya bekerja kontrak 8 bulan di kota lain dan tinggal di kos. Apakah saya wajib mendaftar sebagai penduduk di sana, dan bagaimana caranya?
