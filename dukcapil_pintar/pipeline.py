"""Pipeline RAG end-to-end: tulis ulang kueri, retrieval, lalu generasi jawaban.

Dipakai bersama oleh antarmuka Streamlit dan skrip evaluasi, supaya yang
dievaluasi persis sama dengan yang didemokan.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from dukcapil_pintar.config import EMBEDDING_MODEL_NAME, FUSION_METHOD, ModelOption
from dukcapil_pintar.embedding import embed_texts
from dukcapil_pintar.generation import generate_answer, rewrite_query
from dukcapil_pintar.prompts import is_not_found_answer
from dukcapil_pintar.providers import CompletionResult, ProviderError
from dukcapil_pintar.retrieval import ChunkIndex, RetrievedChunk


@dataclass
class AnswerResult:
    """Hasil satu pertanyaan: jawaban, bukti, model, dan ukuran untuk evaluasi."""

    question: str
    answer: str
    answer_model: ModelOption
    retrieved: list[RetrievedChunk]
    is_answer_found: bool
    rewritten_query: str | None = None
    rewrite_error: str | None = None
    # Token dicatat per tahap karena tahap tulis ulang dan tahap jawab bisa berada
    # di provider berbeda; dipakai skrip evaluasi, tidak ditampilkan di antarmuka.
    token_usage: dict[str, dict[str, int]] = field(default_factory=dict)
    stage_latency_s: dict[str, float] = field(default_factory=dict)

    @property
    def total_latency_s(self) -> float:
        """Mengembalikan total waktu semua tahap dalam detik."""
        return sum(self.stage_latency_s.values())


def _record_tokens(result: AnswerResult, stage: str, completion: CompletionResult) -> None:
    """Mencatat token masuk dan keluar satu tahap ke ``result``."""
    result.token_usage[stage] = {
        "input_tokens": completion.input_tokens,
        "output_tokens": completion.output_tokens,
    }


class RagPipeline:
    """Menjawab pertanyaan warga dari korpus regulasi yang sudah diindeks."""

    def __init__(self, index: ChunkIndex, top_k: int, is_query_rewrite_enabled: bool) -> None:
        """Menyimpan indeks dan parameter yang menentukan perilaku retrieval."""
        self._index = index
        self._top_k = top_k
        self._is_query_rewrite_enabled = is_query_rewrite_enabled

    def answer_question(
        self,
        question: str,
        answer_model: ModelOption,
        frozen_rewrite: str | None = None,
    ) -> AnswerResult:
        """Mengembalikan jawaban berdasar dokumen untuk ``question`` dari ``answer_model``.

        ``frozen_rewrite`` memakai kueri tulis ulang yang sudah ada (mis. dari putaran
        evaluasi sebelumnya) tanpa memanggil penulis ulang. Penulis ulang tidak
        deterministik, jadi tanpa ini retrieval ikut berubah antarputaran dan
        mengacaukan perbandingan perubahan parameter lain.
        """
        result = AnswerResult(
            question=question,
            answer="",
            answer_model=answer_model,
            retrieved=[],
            is_answer_found=False,
        )
        if frozen_rewrite is None:
            queries = [question] + self._rewrite(question, result)
        else:
            result.rewritten_query = frozen_rewrite
            queries = [question] + ([frozen_rewrite] if frozen_rewrite else [])

        started = time.perf_counter()
        query_vectors = embed_texts(queries, EMBEDDING_MODEL_NAME)
        result.retrieved = self._index.search(query_vectors, self._top_k, FUSION_METHOD)
        result.stage_latency_s["retrieval"] = time.perf_counter() - started

        started = time.perf_counter()
        completion = generate_answer(question, result.retrieved, answer_model)
        result.stage_latency_s["generation"] = time.perf_counter() - started
        _record_tokens(result, "generation", completion)

        result.answer = completion.text.strip()
        result.is_answer_found = not is_not_found_answer(result.answer)
        return result

    def _rewrite(self, question: str, result: AnswerResult) -> list[str]:
        """Mengembalikan kueri tambahan hasil tulis ulang, atau list kosong bila tidak dipakai.

        Kegagalan tulis ulang tidak menggagalkan jawaban: retrieval tetap jalan dengan
        pertanyaan asli, dan kegagalannya dicatat agar terlihat, bukan disembunyikan.
        """
        if not self._is_query_rewrite_enabled:
            return []
        started = time.perf_counter()
        try:
            completion = rewrite_query(question)
        except ProviderError as exc:
            result.rewrite_error = str(exc)
            return []
        finally:
            result.stage_latency_s["rewrite"] = time.perf_counter() - started
        _record_tokens(result, "rewrite", completion)
        result.rewritten_query = completion.text.strip()
        return [result.rewritten_query] if result.rewritten_query else []
