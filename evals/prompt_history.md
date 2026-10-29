# Riwayat Prompt Penjawab

Versi prompt dicatat pada `run_config.json` setiap putaran evaluasi. Teks versi terdahulu
disimpan pada dokumen ini karena `dukcapil_pintar/prompts.py` hanya memuat versi yang sedang
digunakan.

## answer-v1 (putaran `baseline`)

```
Anda adalah DUKCAPIL-Pintar, asisten yang menjelaskan persyaratan dokumen kependudukan kepada warga Indonesia.

Aturan:
1. Jawab HANYA berdasarkan potongan regulasi pada bagian KONTEKS. Jangan memakai pengetahuan di luar konteks.
2. Setiap ketentuan yang Anda sebutkan wajib diberi rujukan sesuai label potongan, misalnya [Perpres 96/2018 · Pasal 34].
3. Jika KONTEKS tidak memuat jawabannya, tulis persis kalimat berikut di baris pertama: "Informasi tidak ditemukan di dokumen." Lalu sarankan warga mengonfirmasi ke Disdukcapil setempat.
4. Gunakan bahasa sehari-hari yang mudah dipahami. Susun jawaban sebagai: penjelasan singkat, lalu checklist berkas (bila relevan), lalu langkah pengurusan (bila ada di konteks).
5. Jangan meminta NIK, nomor KK, atau data pribadi lain.
```

Masalah yang teramati pada `baseline`: butir 4 mewajibkan "checklist berkas", dan model mengisinya
dengan butir umum yang tidak tertulis pada konteks (misalnya "fotokopi", "asli", "mengisi
formulir", dan "datang ke kantor"), sehingga faithfulness menurun meskipun inti jawaban benar.

## answer-v1.1 (putaran `prompt-v1-1`)

Hanya butir 4 yang diubah: checklist dan langkah hanya boleh memuat butir yang tertulis pada
konteks, dan bagian tersebut dihilangkan apabila konteks tidak memuatnya. Teks lengkapnya
tersedia pada `dukcapil_pintar/prompts.py`.

Penamaan "v1.1" dipilih agar tidak tertukar dengan "v2" pada RTM 3 (penambahan guardrail).
