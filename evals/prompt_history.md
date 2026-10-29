# Riwayat Prompt Penjawab

Versi prompt dicatat di `run_config.json` tiap putaran evaluasi. Teks versi lama disimpan
di sini karena `dukcapil_pintar/prompts.py` hanya memuat versi yang sedang dipakai.

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

Masalah yang terlihat di baseline: butir 4 mewajibkan "checklist berkas" dan model mengisinya
dengan butir umum yang tidak tertulis di konteks (mis. "fotokopi", "asli", "mengisi formulir",
"datang ke kantor"), sehingga faithfulness turun walau inti jawaban benar.

## answer-v1.1 (putaran `prompt-v1-1`)

Hanya butir 4 yang berubah: checklist dan langkah hanya boleh memuat butir yang tertulis di
konteks, dan bagian itu dihilangkan bila konteks tidak memuatnya. Teks lengkapnya ada di
`dukcapil_pintar/prompts.py`.

Nama "v1.1" dipilih agar tidak tertukar dengan "v2" pada RTM 3 (penambahan guardrail).
