"""Halaman Streamlit DUKCAPIL-Pintar: tanya persyaratan dokumen kependudukan.

Jalankan dengan ``streamlit run app.py`` dari root repo, setelah indeks dibangun
dengan ``python scripts/build-index.py``.
"""

from __future__ import annotations

import os

import streamlit as st

from dukcapil_pintar.config import (
    ANSWER_MODEL_OPTIONS,
    ANTHROPIC_API_KEY_NAME,
    CHUNK_METADATA_JSONL_PATH,
    DEFAULT_ANSWER_MODEL_KEY,
    FAISS_INDEX_PATH,
    GROQ_API_KEY_NAME,
    IS_QUERY_REWRITE_ENABLED,
    STARTER_QUESTIONS,
    TOP_K,
    find_answer_model_option,
    has_secret,
)
from dukcapil_pintar.pipeline import AnswerResult, RagPipeline
from dukcapil_pintar.providers import ProviderError, RateLimitedError
from dukcapil_pintar.retrieval import ChunkIndex
from dukcapil_pintar.ui import (
    APP_TITLE,
    MODEL_SELECTOR_KEY,
    QUESTION_INPUT_KEY,
    answer_container,
    apply_page_style,
    pending_answer_container,
    render_answer,
    render_composer,
    render_disclaimer,
    render_error,
    render_hero,
    render_pending_note,
    render_user_turn,
)

_SESSION_PENDING_KEY = "pending_question"
_SESSION_ASKED_KEY = "asked_question"
_SESSION_RESULT_KEY = "last_result"
_SESSION_ERROR_KEY = "last_error"
_SESSION_IS_RATE_LIMITED_KEY = "is_rate_limited"
# Cadangan yang ditawarkan saat model terpilih kena batas laju; tidak pernah dipakai
# diam-diam: pengguna harus menekan tombolnya, dan chip jawaban menampilkan modelnya.
_FALLBACK_MODEL_KEY = "haiku"


def _export_streamlit_secrets() -> None:
    """Menyalin API key dari st.secrets ke variabel lingkungan bila belum ada.

    Modul inti membaca secret dari variabel lingkungan agar skrip CLI dan aplikasi
    memakai jalur yang sama; di Streamlit Cloud secret diisi lewat st.secrets.
    """
    for name in (GROQ_API_KEY_NAME, ANTHROPIC_API_KEY_NAME):
        if os.environ.get(name):
            continue
        try:
            value = st.secrets.get(name)
        except FileNotFoundError:
            return
        if value:
            os.environ[name] = str(value)


@st.cache_resource(show_spinner="Memuat indeks regulasi…")
def load_pipeline() -> RagPipeline:
    """Mengembalikan pipeline RAG; dimuat sekali per server karena indeks dan model besar."""
    index = ChunkIndex.load(FAISS_INDEX_PATH, CHUNK_METADATA_JSONL_PATH)
    return RagPipeline(index, TOP_K, IS_QUERY_REWRITE_ENABLED)


def _queue_question(question: str) -> None:
    """Menjadwalkan pertanyaan untuk dijalankan di render berikutnya dengan model terpilih.

    Dipakai sebagai callback, sehingga pertanyaan dan model yang dicatat adalah yang
    ada saat tombol ditekan, sebelum skrip dijalankan ulang.
    """
    cleaned = question.strip()
    if cleaned:
        st.session_state[_SESSION_PENDING_KEY] = (cleaned, st.session_state[MODEL_SELECTOR_KEY])


def _submit_typed_question() -> None:
    """Callback tombol tanya: menjadwalkan isi kolom pertanyaan lalu mengosongkannya."""
    question = st.session_state.get(QUESTION_INPUT_KEY, "")
    st.session_state[QUESTION_INPUT_KEY] = ""
    _queue_question(question)


def _switch_to_fallback_model() -> None:
    """Memindahkan selector ke model cadangan dan menjadwalkan pertanyaan yang sama diulang."""
    st.session_state[MODEL_SELECTOR_KEY] = _FALLBACK_MODEL_KEY
    _queue_question(st.session_state[_SESSION_ASKED_KEY])


def _run_pending_question(question: str, answer_model_key: str) -> None:
    """Menjalankan pipeline untuk satu pertanyaan dan menyimpan hasilnya di sesi.

    Pertanyaan ditampilkan lebih dulu bersama logo berdenyut, agar warga melihat
    bahwa pertanyaannya sedang diproses.
    """
    answer_model = find_answer_model_option(answer_model_key)
    st.session_state[_SESSION_ASKED_KEY] = question
    st.session_state[_SESSION_RESULT_KEY] = None
    st.session_state[_SESSION_ERROR_KEY] = None
    st.session_state[_SESSION_IS_RATE_LIMITED_KEY] = False
    render_user_turn(question)
    if not has_secret(answer_model.secret_name):
        st.session_state[_SESSION_ERROR_KEY] = (
            f"{answer_model.label} belum bisa dipakai: API key belum diisi."
        )
        return
    with pending_answer_container():
        render_pending_note()
        try:
            pipeline = load_pipeline()
            st.session_state[_SESSION_RESULT_KEY] = pipeline.answer_question(question, answer_model)
        except RateLimitedError as exc:
            st.session_state[_SESSION_ERROR_KEY] = str(exc)
            st.session_state[_SESSION_IS_RATE_LIMITED_KEY] = True
        except ProviderError as exc:
            st.session_state[_SESSION_ERROR_KEY] = str(exc)


def _render_fallback_button() -> None:
    """Menawarkan tombol coba ulang dengan model cadangan bila model terpilih kena rate limit."""
    fallback = find_answer_model_option(_FALLBACK_MODEL_KEY)
    is_offered = (
        st.session_state.get(_SESSION_IS_RATE_LIMITED_KEY)
        and st.session_state.get(MODEL_SELECTOR_KEY) != fallback.key
        and has_secret(fallback.secret_name)
    )
    if is_offered:
        st.button(f"Coba dengan {fallback.label}", on_click=_switch_to_fallback_model)


def _render_exchange() -> None:
    """Menampilkan pertanyaan terakhir beserta jawabannya atau pesan galatnya."""
    render_user_turn(st.session_state[_SESSION_ASKED_KEY])
    error_message = st.session_state.get(_SESSION_ERROR_KEY)
    result: AnswerResult | None = st.session_state.get(_SESSION_RESULT_KEY)
    with answer_container():
        if error_message:
            render_error(error_message)
            _render_fallback_button()
        elif result is not None:
            render_answer(result)


def main() -> None:
    """Merender halaman: disclaimer, keadaan kosong atau satu giliran, lalu composer."""
    st.set_page_config(page_title=APP_TITLE, page_icon="🪪", layout="centered")
    _export_streamlit_secrets()
    apply_page_style()
    render_disclaimer()

    if not FAISS_INDEX_PATH.exists():
        st.error("Indeks belum dibangun. Jalankan `python scripts/build-index.py` dulu.")
        st.stop()

    # Wadah pertukaran dibuat dulu, composer dirender sebelum pipeline dijalankan:
    # Streamlit membuang state widget yang tidak dirender dalam satu putaran, jadi
    # tanpa itu pilihan model akan kembali ke default setiap kali ada pertanyaan.
    # st.empty menggantikan seluruh isinya sekaligus, sehingga sisa elemen layar
    # sebelumnya (mis. chip contoh) tidak tampak pudar selama pipeline berjalan.
    exchange_slot = st.empty()
    render_composer(ANSWER_MODEL_OPTIONS, DEFAULT_ANSWER_MODEL_KEY, _submit_typed_question)

    # Dikosongkan dulu: tanpa ini, elemen lama di jalur yang sama bertahan pudar
    # sampai skrip selesai.
    exchange_slot.empty()
    with exchange_slot.container():
        pending = st.session_state.pop(_SESSION_PENDING_KEY, None)
        if pending is not None:
            _run_pending_question(*pending)
            st.rerun()
        elif st.session_state.get(_SESSION_ASKED_KEY) is None:
            render_hero(STARTER_QUESTIONS, _queue_question)
        else:
            _render_exchange()


main()
