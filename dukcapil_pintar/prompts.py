"""Prompt penjawab, penulis ulang kueri, dan juri evaluasi, beserta nomor versinya.

Versi prompt dicatat di setiap putaran evaluasi supaya perubahan skor dapat
ditelusuri ke perubahan prompt (Bab 7.6).
"""

from __future__ import annotations

from dukcapil_pintar.retrieval import RetrievedChunk

ANSWER_PROMPT_VERSION = "answer-v1.1"
REWRITE_PROMPT_VERSION = "rewrite-v1"
JUDGE_PROMPT_VERSION = "judge-v1"

# Kalimat ini juga dipakai untuk mendeteksi penolakan, jadi harus persis sama
# dengan yang diminta di prompt penjawab.
NOT_FOUND_MESSAGE = "Informasi tidak ditemukan di dokumen."

# v1 sengaja hanya memuat mitigasi dasar Bab 6.5 (jawab dari konteks, akui bila
# tidak ada). Guardrail lain ditambahkan di v2 (RTM 3) agar perbandingannya jujur.
ANSWER_SYSTEM_PROMPT = f"""Anda adalah DUKCAPIL-Pintar, asisten yang menjelaskan persyaratan \
dokumen kependudukan kepada warga Indonesia.

Aturan:
1. Jawab HANYA berdasarkan potongan regulasi pada bagian KONTEKS. Jangan memakai \
pengetahuan di luar konteks.
2. Setiap ketentuan yang Anda sebutkan wajib diberi rujukan sesuai label potongan, \
misalnya [Perpres 96/2018 · Pasal 34].
3. Jika KONTEKS tidak memuat jawabannya, tulis persis kalimat berikut di baris pertama: \
"{NOT_FOUND_MESSAGE}" Lalu sarankan warga mengonfirmasi ke Disdukcapil setempat.
4. Gunakan bahasa sehari-hari yang mudah dipahami. Susun jawaban sebagai penjelasan \
singkat. Tambahkan checklist berkas HANYA bila KONTEKS menyebut daftar berkasnya, dan \
langkah pengurusan HANYA bila KONTEKS menyebut tahapannya. Isi keduanya hanya dengan butir \
yang tertulis di KONTEKS; jangan menambahkan berkas atau langkah umum yang tidak tertulis \
di sana. Bila KONTEKS tidak memuatnya, jangan buat bagian tersebut.
5. Jangan meminta NIK, nomor KK, atau data pribadi lain."""

REWRITE_SYSTEM_PROMPT = """Anda membantu mesin pencari regulasi administrasi kependudukan \
Indonesia. Ubah pertanyaan warga yang memakai bahasa sehari-hari menjadi satu kueri \
pencarian berisi istilah resmi regulasi (mis. "akta kelahiran", "SPTJM", "pindah datang", \
"KTP-el", "Kartu Identitas Anak"). Balas HANYA dengan kueri tersebut dalam satu baris, \
tanpa penjelasan."""

FAITHFULNESS_JUDGE_PROMPT = """Anda adalah juri evaluasi. Berikut sebuah jawaban dan konteks \
sumbernya. Pecah jawaban menjadi klaim-klaim kecil, lalu untuk tiap klaim tentukan apakah \
DIDUKUNG oleh konteks atau TIDAK DIDUKUNG. Kalimat yang hanya menyatakan informasi tidak \
ditemukan atau menyarankan konfirmasi ke Disdukcapil tidak dihitung sebagai klaim.

Konteks:
{context}

Jawaban:
{answer}

Format keluaran:
Klaim 1: [teks klaim] - [DIDUKUNG/TIDAK DIDUKUNG]
Klaim 2: ...
Skor Faithfulness: [angka 0-10]"""

RELEVANCE_JUDGE_PROMPT = """Anda adalah juri evaluasi. Nilai seberapa langsung jawaban \
berikut menjawab pertanyaan yang diajukan, terlepas dari benar tidaknya isi jawaban \
terhadap sumber. Jawaban yang menyatakan informasi tidak ditemukan bernilai tinggi hanya \
bila pertanyaannya memang di luar cakupan regulasi administrasi kependudukan nasional.

Pertanyaan:
{question}

Jawaban:
{answer}

Format keluaran:
Alasan: [satu-dua kalimat]
Skor Relevansi: [angka 0-10]"""


def format_context(retrieved: list[RetrievedChunk]) -> str:
    """Mengembalikan teks konteks: chunk hasil retrieval dipisah baris kosong.

    Setiap chunk sudah diawali header dokumen dan pasal sehingga model bisa
    menyalin label rujukannya.
    """
    return "\n\n".join(item.chunk.text for item in retrieved)


def build_answer_user_prompt(question: str, retrieved: list[RetrievedChunk]) -> str:
    """Mengembalikan pesan pengguna untuk model penjawab: konteks lalu pertanyaan."""
    return f"KONTEKS:\n{format_context(retrieved)}\n\nPERTANYAAN WARGA:\n{question}"


def is_not_found_answer(answer: str) -> bool:
    """Mengembalikan True bila jawaban menyatakan informasi tidak ditemukan."""
    return NOT_FOUND_MESSAGE.lower() in answer.lower()
