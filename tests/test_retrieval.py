"""Menguji penggabungan hasil dua kueri: skor maksimum versus reciprocal rank fusion."""

from __future__ import annotations

import numpy as np
import pytest

from dukcapil_pintar.chunking import Chunk
from dukcapil_pintar.retrieval import (
    FUSION_MAX_SCORE,
    FUSION_RRF,
    ChunkIndex,
    build_faiss_index,
)


def _make_chunk(chunk_id: str) -> Chunk:
    """Mengembalikan chunk uji dengan ID tertentu."""
    return Chunk(chunk_id, "doc", "Dok", f"Pasal {chunk_id}", 1, "https://x.invalid", chunk_id)


@pytest.fixture
def index() -> ChunkIndex:
    """Mengembalikan indeks berisi empat chunk pada vektor 2 dimensi ternormalisasi."""
    angles = np.radians([0, 20, 40, 60])
    vectors = np.stack([np.cos(angles), np.sin(angles)], axis=1).astype(np.float32)
    chunks = [_make_chunk(name) for name in "ABCD"]
    return ChunkIndex(build_faiss_index(vectors), chunks)


def _labels(results: list) -> list[str]:
    """Mengembalikan ID chunk hasil pencarian, berurutan."""
    return [item.chunk.chunk_id for item in results]


def test_max_score_lets_higher_scaled_query_dominate(index: ChunkIndex) -> None:
    """Memastikan skor maksimum memenangkan kueri berskala besar, meski kueri lain cocok A."""
    question = np.array([[1.0, 0.0]], dtype=np.float32)  # paling dekat dengan A
    rewrite = np.array([[0.5, 1.5]], dtype=np.float32)  # skala besar, paling dekat dengan D
    results = index.search(np.vstack([question, rewrite]), 2, FUSION_MAX_SCORE)
    assert "A" not in _labels(results)


def test_rrf_keeps_best_chunk_of_each_query(index: ChunkIndex) -> None:
    """Memastikan RRF mengangkat chunk teratas dari tiap kueri tanpa terpengaruh skala skor."""
    question = np.array([[1.0, 0.0]], dtype=np.float32)
    rewrite = np.array([[0.5, 1.5]], dtype=np.float32)
    results = index.search(np.vstack([question, rewrite]), 2, FUSION_RRF)
    assert set(_labels(results)) == {"A", "D"}


def test_rrf_with_single_query_matches_plain_ranking(index: ChunkIndex) -> None:
    """Memastikan dengan satu kueri, RRF dan skor maksimum menghasilkan urutan yang sama."""
    query = np.array([[1.0, 0.2]], dtype=np.float32)
    assert _labels(index.search(query, 3, FUSION_RRF)) == _labels(
        index.search(query, 3, FUSION_MAX_SCORE)
    )


def test_search_rejects_unknown_fusion_method(index: ChunkIndex) -> None:
    """Memastikan nama metode fusi yang salah ditolak, bukan diam-diam diabaikan."""
    with pytest.raises(ValueError, match="tidak dikenal"):
        index.search(np.array([[1.0, 0.0]], dtype=np.float32), 2, "acak")
