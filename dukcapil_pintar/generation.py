"""Tahap generasi: menulis ulang kueri warga dan menyusun jawaban dari konteks."""

from __future__ import annotations

import dataclasses
import re

from dukcapil_pintar.config import (
    ANSWER_MAX_TOKENS,
    REWRITE_MAX_TOKENS,
    SONNET_OPTION,
    ModelOption,
)
from dukcapil_pintar.prompts import (
    ANSWER_SYSTEM_PROMPT,
    REWRITE_SYSTEM_PROMPT,
    build_answer_user_prompt,
)
from dukcapil_pintar.providers import CompletionResult, complete
from dukcapil_pintar.retrieval import RetrievedChunk

# Sonnet kadang menulis blok <reasoning> sebelum kueri; blok itu harus dibuang
# agar tidak ikut di-embed sebagai kueri pencarian.
_REASONING_BLOCK_PATTERN = re.compile(r"<reasoning>.*?(?:</reasoning>|$)", re.DOTALL)


def rewrite_query(question: str) -> CompletionResult:
    """Mengembalikan kueri berbahasa regulasi hasil tulis ulang Sonnet dari pertanyaan warga.

    Warga jarang memakai istilah resmi ("akta lahir anak tanpa buku nikah"),
    sedangkan korpus berbahasa hukum ("SPTJM"); jarak istilah ini menurunkan
    kualitas retrieval.
    """
    completion = complete(SONNET_OPTION, REWRITE_SYSTEM_PROMPT, question, REWRITE_MAX_TOKENS)
    clean_text = _REASONING_BLOCK_PATTERN.sub("", completion.text).strip()
    return dataclasses.replace(completion, text=clean_text)


def generate_answer(
    question: str,
    retrieved: list[RetrievedChunk],
    option: ModelOption,
) -> CompletionResult:
    """Mengembalikan jawaban model ``option`` yang disusun hanya dari chunk hasil retrieval."""
    user_prompt = build_answer_user_prompt(question, retrieved)
    return complete(option, ANSWER_SYSTEM_PROMPT, user_prompt, ANSWER_MAX_TOKENS)
