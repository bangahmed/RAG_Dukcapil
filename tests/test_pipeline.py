"""Menguji bahwa kueri tulis ulang beku dipakai tanpa memanggil penulis ulang."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dukcapil_pintar import pipeline
from dukcapil_pintar.config import ANSWER_MODEL_OPTIONS
from dukcapil_pintar.providers import CompletionResult

_MODEL = ANSWER_MODEL_OPTIONS[0]


@pytest.fixture
def fake_stages(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Mengganti embedding, penulis ulang, dan generasi dengan tiruan; mengembalikannya."""
    stages = {
        "embed": MagicMock(return_value="vektor"),
        "rewrite": MagicMock(return_value=CompletionResult("kueri baru", "m", 5, 6)),
        "generate": MagicMock(return_value=CompletionResult("jawaban", "m", 1, 2)),
    }
    monkeypatch.setattr(pipeline, "embed_texts", stages["embed"])
    monkeypatch.setattr(pipeline, "rewrite_query", stages["rewrite"])
    monkeypatch.setattr(pipeline, "generate_answer", stages["generate"])
    return stages


def _make_pipeline() -> pipeline.RagPipeline:
    """Mengembalikan pipeline dengan indeks tiruan dan penulis ulang aktif."""
    index = MagicMock()
    index.search.return_value = []
    return pipeline.RagPipeline(index, top_k=4, is_query_rewrite_enabled=True)


def test_answer_question_uses_frozen_rewrite_without_calling_rewriter(
    fake_stages: dict[str, MagicMock],
) -> None:
    """Memastikan kueri beku di-embed bersama pertanyaan dan penulis ulang tidak dipanggil."""
    result = _make_pipeline().answer_question("tanya?", _MODEL, frozen_rewrite="kueri beku")
    fake_stages["rewrite"].assert_not_called()
    assert fake_stages["embed"].call_args.args[0] == ["tanya?", "kueri beku"]
    assert result.rewritten_query == "kueri beku"
    assert "rewrite" not in result.token_usage


def test_answer_question_without_frozen_rewrite_calls_rewriter(
    fake_stages: dict[str, MagicMock],
) -> None:
    """Memastikan tanpa kueri beku, penulis ulang dipanggil seperti biasa."""
    result = _make_pipeline().answer_question("tanya?", _MODEL)
    fake_stages["rewrite"].assert_called_once()
    assert fake_stages["embed"].call_args.args[0] == ["tanya?", "kueri baru"]
    assert result.token_usage["rewrite"] == {"input_tokens": 5, "output_tokens": 6}


def test_answer_question_with_empty_frozen_rewrite_uses_question_only(
    fake_stages: dict[str, MagicMock],
) -> None:
    """Memastikan kueri beku kosong (tulis ulang gagal di putaran asal) tidak ikut di-embed."""
    _make_pipeline().answer_question("tanya?", _MODEL, frozen_rewrite="")
    assert fake_stages["embed"].call_args.args[0] == ["tanya?"]
