"""Menguji API key dan ID model tiap provider dengan satu panggilan pendek.

Jalankan sebelum membangun apa pun di atas provider, karena katalog model Groq
dan Anthropic bisa berubah. Contoh: ``python scripts/smoke-test-providers.py``.
"""

from __future__ import annotations

import time

from _project_root import add_project_root_to_path

add_project_root_to_path()

from dukcapil_pintar.config import ANSWER_MODEL_OPTIONS, SONNET_OPTION  # noqa: E402
from dukcapil_pintar.formatting import format_decimal  # noqa: E402
from dukcapil_pintar.providers import ProviderError, complete  # noqa: E402

_SMOKE_SYSTEM_PROMPT = "Balas dengan satu kata saja."
_SMOKE_USER_PROMPT = "Tulis kata: siap"
# Cukup longgar untuk gpt-oss yang menghabiskan token penalaran sebelum menjawab.
_SMOKE_MAX_TOKENS = 256


def main() -> None:
    """Memanggil tiap model sekali dan mencetak status, latency, serta jumlah token."""
    is_all_ok = True
    for option in (*ANSWER_MODEL_OPTIONS, SONNET_OPTION):
        started = time.perf_counter()
        try:
            result = complete(option, _SMOKE_SYSTEM_PROMPT, _SMOKE_USER_PROMPT, _SMOKE_MAX_TOKENS)
        except ProviderError as exc:
            is_all_ok = False
            print(f"[GAGAL] {option.label} ({option.model_id}): {exc}")
            continue
        latency_s = time.perf_counter() - started
        print(
            f"[OK]    {option.label} ({option.model_id}) {format_decimal(latency_s)} detik, "
            f"{result.input_tokens} masuk / {result.output_tokens} keluar: {result.text!r}"
        )
    if not is_all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
