# Ringkasan evaluasi: top-k-6

Parameter putaran ada di `run_config.json`. Skor juri adalah estimasi; periksa manual pertanyaan berskor terendah di bawah.

| Jenis | n | Relevansi | Faithfulness | Hit retrieval | Penolakan benar | Token jawab (masuk+keluar) | Latency (detik) |
|---|---|---|---|---|---|---|---|
| eksplisit | 6 | 9,17 | 8,00 | 1,00 | - | 2004,83 | 3,21 |
| gabungan | 5 | 7,40 | 8,80 | 0,40 | - | 2143,40 | 3,20 |
| di_luar_cakupan | 3 | 7,33 | 10,00 | - | 1,00 | 1855,00 | 1,83 |
| semua | 14 | 8,14 | 8,71 | 0,73 | 1,00 | 2022,21 | 2,91 |

## Skor faithfulness terendah (cek manual)

- q03 (faithfulness 6,0): Apa syarat membuat KTP-el baru bagi warga negara Indonesia?
- q02 (faithfulness 7,0): Berapa lama KTP-el atau Kartu Keluarga harus selesai setelah semua persyaratan saya lengkap?
- q05 (faithfulness 8,0): Siapa yang wajib melaporkan kematian anggota keluarga, dan paling lambat berapa hari?
