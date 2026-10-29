"""Menyimpan dan mencari chunk paling relevan dengan indeks vektor FAISS.

FAISS dipilih (RPS menyebut FAISS/Chroma) karena korpus hanya ±723 chunk, indeks
berupa satu berkas kecil yang bisa ikut di repo, dan tidak membutuhkan server.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from dukcapil_pintar.chunking import Chunk

FUSION_MAX_SCORE = "max_score"
FUSION_RRF = "rrf"
# Konstanta 60 adalah nilai baku reciprocal rank fusion (Cormack dkk. 2009): meredam
# beda besar antara peringkat 1 dan 2 agar satu daftar tidak menguasai hasil.
_RRF_RANK_CONSTANT = 60
# Kedalaman daftar tiap kueri yang ikut digabung; jauh di bawah ±950 chunk, tetapi cukup
# agar pasal di peringkat belasan pada satu kueri tetap bisa terangkat oleh kueri lain.
_RRF_DEPTH = 30


@dataclass(frozen=True)
class RetrievedChunk:
    """Chunk hasil pencarian beserta skor kemiripannya (cosine, makin besar makin mirip)."""

    chunk: Chunk
    score: float


def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """Mengembalikan indeks inner product berisi seluruh embedding chunk."""
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


def write_jsonl(records: list[dict], path: Path) -> None:
    """Menulis daftar dict ke berkas JSONL, satu record per baris."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Mengembalikan seluruh record dari berkas JSONL."""
    with path.open(encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def save_index(
    index: faiss.IndexFlatIP,
    chunks: list[Chunk],
    index_path: Path,
    metadata_path: Path,
) -> None:
    """Menyimpan indeks FAISS dan metadata chunk dengan urutan baris yang sama."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    write_jsonl([chunk.to_record() for chunk in chunks], metadata_path)


def _fuse_by_max_score(scores: np.ndarray, positions: np.ndarray) -> dict[int, float]:
    """Mengembalikan skor per posisi chunk: skor cosine tertinggi dari semua kueri.

    Skor kueri berbeda tidak sebanding (tulis ulang yang padat kata kunci berskor lebih
    tinggi), sehingga satu kueri bisa menguasai hasil.
    """
    best_score_by_position: dict[int, float] = {}
    for row_scores, row_positions in zip(scores, positions, strict=True):
        for score, position in zip(row_scores, row_positions, strict=True):
            # FAISS mengisi -1 bila indeks berisi lebih sedikit vektor dari top_k.
            if position < 0:
                continue
            previous = best_score_by_position.get(int(position), float("-inf"))
            best_score_by_position[int(position)] = max(previous, float(score))
    return best_score_by_position


def _fuse_by_rank(positions: np.ndarray) -> dict[int, float]:
    """Mengembalikan skor reciprocal rank fusion per posisi chunk.

    Tiap kueri menyumbang 1 / (60 + peringkat), jadi yang dihitung peringkatnya, bukan
    skornya, dan kueri dengan skala skor berbeda tetap setara.
    """
    fused: dict[int, float] = {}
    for row_positions in positions:
        for rank, position in enumerate(row_positions, start=1):
            if position < 0:
                continue
            fused[int(position)] = fused.get(int(position), 0.0) + 1 / (_RRF_RANK_CONSTANT + rank)
    return fused


class ChunkIndex:
    """Indeks vektor siap pakai: mencari chunk untuk satu atau beberapa kueri."""

    def __init__(self, index: faiss.Index, chunks: list[Chunk]) -> None:
        """Menyimpan indeks dan chunk; urutan chunk harus sama dengan urutan vektor."""
        if index.ntotal != len(chunks):
            raise ValueError(
                f"Jumlah vektor ({index.ntotal}) tidak sama dengan jumlah chunk ({len(chunks)})."
            )
        self._index = index
        self._chunks = chunks

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path) -> ChunkIndex:
        """Mengembalikan ChunkIndex yang dimuat dari berkas indeks dan metadata."""
        index = faiss.read_index(str(index_path))
        chunks = [Chunk(**record) for record in read_jsonl(metadata_path)]
        return cls(index, chunks)

    @property
    def chunk_count(self) -> int:
        """Mengembalikan jumlah chunk di indeks."""
        return len(self._chunks)

    def search(
        self,
        query_vectors: np.ndarray,
        top_k: int,
        fusion_method: str = FUSION_MAX_SCORE,
    ) -> list[RetrievedChunk]:
        """Mengembalikan ``top_k`` chunk terbaik dari gabungan semua vektor kueri.

        Bila ada beberapa kueri (pertanyaan asli + hasil tulis ulang), hasilnya digabung
        dengan ``fusion_method``: ``max_score`` (skor tertinggi per chunk) atau ``rrf``
        (reciprocal rank fusion). Satu chunk tidak pernah muncul dua kali.
        """
        if fusion_method not in (FUSION_MAX_SCORE, FUSION_RRF):
            raise ValueError(f"Metode fusi '{fusion_method}' tidak dikenal.")
        depth = max(top_k, _RRF_DEPTH) if fusion_method == FUSION_RRF else top_k
        scores, positions = self._index.search(query_vectors, depth)
        if fusion_method == FUSION_RRF:
            fused = _fuse_by_rank(positions)
        else:
            fused = _fuse_by_max_score(scores, positions)

        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
        return [
            RetrievedChunk(chunk=self._chunks[position], score=score)
            for position, score in ranked[:top_k]
        ]
