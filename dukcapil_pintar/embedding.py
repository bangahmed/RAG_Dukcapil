"""Mengubah teks menjadi vektor dengan model sentence-transformers yang berjalan lokal.

Embedding wajib lokal menurut RTM 2, sehingga teks korpus dan pertanyaan tidak
dikirim ke provider untuk tahap ini.
"""

from __future__ import annotations

import functools

import numpy as np
from sentence_transformers import SentenceTransformer

_ENCODE_BATCH_SIZE = 32


@functools.cache
def load_embedding_model(model_name: str) -> SentenceTransformer:
    """Mengembalikan model embedding; dimuat sekali per proses karena ukurannya besar."""
    return SentenceTransformer(model_name, device="cpu")


def embed_texts(texts: list[str], model_name: str, show_progress: bool = False) -> np.ndarray:
    """Mengembalikan matriks embedding float32 ternormalisasi, satu baris per teks.

    Normalisasi membuat inner product setara cosine similarity, sesuai indeks FAISS
    ``IndexFlatIP`` di modul retrieval.
    """
    model = load_embedding_model(model_name)
    vectors = model.encode(
        texts,
        batch_size=_ENCODE_BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=show_progress,
    )
    return vectors.astype(np.float32)
