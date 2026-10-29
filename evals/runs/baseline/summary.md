# Ringkasan evaluasi: baseline

Parameter putaran ada di `run_config.json`. Skor juri adalah estimasi; periksa manual pertanyaan berskor terendah di bawah.

| Jenis | n | Relevansi | Faithfulness | Hit retrieval | Penolakan benar | Token jawab (masuk+keluar) | Latency (detik) |
|---|---|---|---|---|---|---|---|
| eksplisit | 6 | 8,67 | 4,92 | 1,00 | - | 1884,67 | 5,49 |
| gabungan | 5 | 7,40 | 6,20 | 0,40 | - | 1955,40 | 5,55 |
| di_luar_cakupan | 3 | 8,00 | 10,00 | - | 1,00 | 1087,33 | 3,54 |
| semua | 14 | 8,07 | 6,46 | 0,73 | 1,00 | 1739,07 | 5,09 |

## Skor faithfulness terendah (cek manual)

- q03 (faithfulness 2,5): Apa syarat membuat KTP-el baru bagi warga negara Indonesia?
- q01 (faithfulness 3,0): Apakah mengurus dokumen kependudukan dipungut biaya?
- q09 (faithfulness 3,0): Saya pindah dari Bandung ke Semarang. Dokumen apa yang harus disiapkan supaya mendapat KTP-el dan KK baru di Semarang?
