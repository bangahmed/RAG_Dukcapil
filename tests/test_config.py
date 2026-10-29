"""Menguji bahwa chip contoh di halaman utama berasal dari set uji."""

from __future__ import annotations

import json

from dukcapil_pintar.config import STARTER_QUESTIONS, TEST_SET_JSONL_PATH


def test_starter_questions_are_verbatim_test_set_questions() -> None:
    """Memastikan tiap chip contoh sama persis dengan satu pertanyaan di set uji."""
    with TEST_SET_JSONL_PATH.open(encoding="utf-8") as fh:
        test_set = {json.loads(line)["question"]: json.loads(line) for line in fh if line.strip()}
    for question in STARTER_QUESTIONS:
        assert question in test_set, f"Chip tidak ada di set uji: {question}"


def test_starter_questions_have_a_key_article_and_are_not_out_of_scope() -> None:
    """Memastikan chip hanya memakai pertanyaan berpasal kunci, bukan di luar cakupan."""
    with TEST_SET_JSONL_PATH.open(encoding="utf-8") as fh:
        test_set = {json.loads(line)["question"]: json.loads(line) for line in fh if line.strip()}
    for question in STARTER_QUESTIONS:
        assert test_set[question]["expected_articles"], question
