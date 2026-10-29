"""Menguji retry, batas laju, dan kunci hilang pada lapisan provider tanpa memanggil API asli."""

from __future__ import annotations

from unittest.mock import MagicMock

import openai
import pytest

from dukcapil_pintar import providers
from dukcapil_pintar.config import ANSWER_MODEL_OPTIONS, SONNET_OPTION
from dukcapil_pintar.providers import (
    CompletionResult,
    MissingApiKeyError,
    ProviderError,
    RateLimitedError,
)

_GROQ_OPTION = ANSWER_MODEL_OPTIONS[0]


def _make_error(error_class: type[openai.APIStatusError], status_code: int) -> openai.APIError:
    """Mengembalikan galat SDK openai bertipe ``error_class`` dengan status HTTP tertentu."""
    # Respons tiruan: tipe respons HTTP berbeda antar versi SDK, sedangkan yang
    # dipakai konstruktor galat hanya status_code, headers, dan request.
    response = MagicMock(status_code=status_code)
    response.headers.get.return_value = None
    return error_class("galat uji", response=response, body=None)


@pytest.fixture(autouse=True)
def _skip_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mematikan jeda backoff agar tes tidak menunggu belasan detik."""
    monkeypatch.setattr(providers.time, "sleep", lambda _seconds: None)


def _patch_groq_call(monkeypatch: pytest.MonkeyPatch, outcomes: list) -> list[int]:
    """Mengganti panggilan Groq dengan urutan hasil/galat; mengembalikan penghitung panggilan."""
    calls: list[int] = []

    def fake_call(*_args: object) -> CompletionResult:
        """Mengembalikan atau melempar hasil berikutnya dari ``outcomes``."""
        calls.append(1)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setitem(providers._PROVIDER_CALLS, "groq", fake_call)
    return calls


def test_complete_retries_rate_limit_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memastikan satu galat 429 dicoba ulang dan percobaan berikutnya dikembalikan."""
    ok = CompletionResult("jawaban", "m", 1, 1)
    calls = _patch_groq_call(monkeypatch, [_make_error(openai.RateLimitError, 429), ok])
    assert providers.complete(_GROQ_OPTION, "s", "u", 10) == ok
    assert len(calls) == 2


def test_complete_raises_rate_limited_error_after_all_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan 429 beruntun berakhir sebagai RateLimitedError dengan pesan yang jelas."""
    error = _make_error(openai.RateLimitError, 429)
    calls = _patch_groq_call(monkeypatch, [error] * providers.RETRY_MAX_ATTEMPTS)
    with pytest.raises(RateLimitedError, match="rate limit"):
        providers.complete(_GROQ_OPTION, "s", "u", 10)
    assert len(calls) == providers.RETRY_MAX_ATTEMPTS


def test_complete_does_not_retry_rejected_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memastikan galat permanen (mis. kunci salah, 401) langsung dilaporkan tanpa retry."""
    calls = _patch_groq_call(monkeypatch, [_make_error(openai.AuthenticationError, 401)])
    with pytest.raises(ProviderError, match="menolak permintaan"):
        providers.complete(_GROQ_OPTION, "s", "u", 10)
    assert len(calls) == 1


def test_complete_reports_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memastikan kunci yang belum diisi menghasilkan MissingApiKeyError, bukan galat SDK."""
    monkeypatch.setattr(providers, "get_secret", lambda _name: None)
    with pytest.raises(MissingApiKeyError, match="GROQ_API_KEY"):
        providers.complete(_GROQ_OPTION, "s", "u", 10)


def test_complete_with_anthropic_rejects_truncated_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Memastikan respons Anthropic yang terpotong di max_tokens menjadi galat."""
    truncated = MagicMock(stop_reason="max_tokens", content=[])
    client = MagicMock()
    client.messages.create.return_value = truncated
    monkeypatch.setattr(providers, "_get_anthropic_client", lambda _key: client)
    monkeypatch.setattr(providers, "get_secret", lambda _name: "kunci-uji")
    with pytest.raises(ProviderError, match="terpotong"):
        providers.complete(SONNET_OPTION, "s", "u", 10)

