"""Klien provider LLM (Groq dan Anthropic) di balik satu fungsi ``complete``.

Groq diakses lewat SDK ``openai`` karena API-nya OpenAI-compatible (Bab 5.6).
Retry dengan backoff ditangani di sini, satu kali, supaya pemanggil tidak perlu
tahu bentuk error tiap provider.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from dataclasses import dataclass

import anthropic
import openai

from dukcapil_pintar.config import (
    GROQ_BASE_URL,
    RETRY_BASE_DELAY_S,
    RETRY_MAX_ATTEMPTS,
    ModelOption,
    get_secret,
)

# Error sementara yang layak dicoba ulang; error lain (kunci salah, ID model salah)
# langsung dilaporkan karena mencoba ulang tidak akan mengubah hasilnya.
_RETRYABLE_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
)
_RATE_LIMIT_ERRORS = (openai.RateLimitError, anthropic.RateLimitError)


class ProviderError(Exception):
    """Kegagalan memanggil provider LLM yang pesannya aman ditampilkan ke pengguna."""


class MissingApiKeyError(ProviderError):
    """API key provider belum diisi di secrets."""


class RateLimitedError(ProviderError):
    """Provider tetap menolak karena batas laju setelah semua percobaan ulang."""


@dataclass(frozen=True)
class CompletionResult:
    """Teks balasan model beserta jumlah token yang dilaporkan provider."""

    text: str
    model_id: str
    input_tokens: int
    output_tokens: int


def _require_api_key(secret_name: str) -> str:
    """Mengembalikan API key dari secrets; gagal dengan pesan jelas bila kosong."""
    api_key = get_secret(secret_name)
    if not api_key:
        raise MissingApiKeyError(f"{secret_name} belum diisi di secrets.")
    return api_key


@functools.cache
def _get_groq_client(api_key: str) -> openai.OpenAI:
    """Mengembalikan klien Groq; dibuat sekali per API key."""
    # Retry bawaan SDK dimatikan agar hanya ada satu lapis retry (milik modul ini).
    return openai.OpenAI(api_key=api_key, base_url=GROQ_BASE_URL, max_retries=0)


@functools.cache
def _get_anthropic_client(api_key: str) -> anthropic.Anthropic:
    """Mengembalikan klien Anthropic; dibuat sekali per API key."""
    return anthropic.Anthropic(api_key=api_key, max_retries=0)


def _complete_with_groq(
    option: ModelOption,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float | None,
) -> CompletionResult:
    """Mengembalikan balasan model Groq lewat endpoint chat completions."""
    client = _get_groq_client(_require_api_key(option.secret_name))
    optional_args = {} if temperature is None else {"temperature": temperature}
    response = client.chat.completions.create(
        model=option.model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=max_tokens,
        **optional_args,
    )
    usage = response.usage
    return CompletionResult(
        text=response.choices[0].message.content or "",
        model_id=option.model_id,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
    )


def _complete_with_anthropic(
    option: ModelOption,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float | None,
) -> CompletionResult:
    """Mengembalikan balasan model Anthropic lewat Messages API."""
    # API model Anthropic terbaru menolak temperature (galat 400); gagal lebih awal
    # daripada diam-diam mengabaikannya, agar klaim "suhu 0" tidak menyesatkan.
    if temperature is not None:
        raise ValueError("Model Anthropic ini tidak menerima parameter temperature.")
    client = _get_anthropic_client(_require_api_key(option.secret_name))
    response = client.messages.create(
        model=option.model_id,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    # Terpotong berarti thinking atau jawaban melewati batas token; teks parsial atau
    # kosong akan lolos sebagai skor/jawaban palsu, jadi dilaporkan sebagai galat.
    if response.stop_reason == "max_tokens":
        raise ProviderError(
            f"{option.label} terpotong di batas {max_tokens} token. Naikkan batas token."
        )
    text = "".join(block.text for block in response.content if block.type == "text")
    return CompletionResult(
        text=text,
        model_id=option.model_id,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


_PROVIDER_CALLS: dict[str, Callable[..., CompletionResult]] = {
    "groq": _complete_with_groq,
    "anthropic": _complete_with_anthropic,
}


def _call_with_retry(call: Callable[[], CompletionResult], option: ModelOption) -> CompletionResult:
    """Mengembalikan hasil ``call``, mencoba ulang error sementara dengan backoff eksponensial."""
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            return call()
        except _RETRYABLE_ERRORS as exc:
            if attempt == RETRY_MAX_ATTEMPTS:
                if isinstance(exc, _RATE_LIMIT_ERRORS):
                    raise RateLimitedError(
                        f"{option.label} sedang membatasi permintaan (rate limit). "
                        "Tunggu sebentar atau pilih model lain."
                    ) from exc
                raise ProviderError(f"{option.label} tidak dapat dihubungi: {exc}") from exc
            time.sleep(RETRY_BASE_DELAY_S * 2 ** (attempt - 1))
        except (openai.APIError, anthropic.APIError) as exc:
            raise ProviderError(f"{option.label} menolak permintaan: {exc}") from exc
    raise AssertionError("Perulangan retry selesai tanpa hasil.")


def complete(
    option: ModelOption,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float | None = None,
) -> CompletionResult:
    """Mengembalikan balasan model ``option`` untuk satu pasang prompt sistem dan pengguna."""
    provider_call = _PROVIDER_CALLS.get(option.provider)
    if provider_call is None:
        raise ValueError(f"Provider '{option.provider}' tidak dikenal.")
    return _call_with_retry(
        lambda: provider_call(option, system_prompt, user_prompt, max_tokens, temperature),
        option,
    )
