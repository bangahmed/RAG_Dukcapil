"""Konfigurasi terpusat DUKCAPIL-Pintar: path, parameter RAG, daftar model, dan secret.

Parameter yang diubah saat iterasi evaluasi (top-k, model embedding, penulis ulang
kueri) dapat ditimpa lewat variabel lingkungan berprefiks ``DUKCAPIL_``, supaya
percobaan sebelum-sesudah tidak perlu mengubah kode.
"""

from __future__ import annotations

import functools
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


def _read_env_str(name: str, default: str) -> str:
    """Mengembalikan nilai teks variabel lingkungan, atau ``default`` bila kosong."""
    return os.environ.get(name) or default


def _read_env_int(name: str, default: int) -> int:
    """Mengembalikan nilai bilangan bulat variabel lingkungan, atau ``default``."""
    raw_value = os.environ.get(name)
    return int(raw_value) if raw_value else default


def _read_env_bool(name: str, default: bool) -> bool:
    """Mengembalikan nilai boolean variabel lingkungan (1/true/yes), atau ``default``."""
    raw_value = os.environ.get(name)
    if not raw_value:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "ya"}


# --- Path -------------------------------------------------------------------

PROJECT_ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"
EVALS_DIR = PROJECT_ROOT_DIR / "evals"
EVAL_RUNS_DIR = EVALS_DIR / "runs"

SOURCES_CSV_PATH = DATA_DIR / "sources.csv"
PAGES_JSONL_PATH = PROCESSED_DIR / "pages.jsonl"
CHUNKS_JSONL_PATH = PROCESSED_DIR / "chunks.jsonl"
EMBEDDINGS_NPY_PATH = INDEX_DIR / "embeddings.npy"
FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNK_METADATA_JSONL_PATH = INDEX_DIR / "chunk_metadata.jsonl"
TEST_SET_JSONL_PATH = EVALS_DIR / "test_set.jsonl"
LOCAL_SECRETS_TOML_PATH = PROJECT_ROOT_DIR / ".streamlit" / "secrets.toml"

# --- Parameter RAG ----------------------------------------------------------

# mpnet (±1,1 GB) dipilih karena hit rate retrieval lebih baik daripada MiniLM pada uji
# awal (3 vs 2 dari 6 pertanyaan). Puncak memori terukur ±1,9 GB, di bawah batas
# ±2,7 GB hosting gratis, tetapi tipis: uji deploy lebih awal. Cadangan: MiniLM.
EMBEDDING_MODEL_NAME = _read_env_str(
    "DUKCAPIL_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
)
TOP_K = _read_env_int("DUKCAPIL_TOP_K", 4)
IS_QUERY_REWRITE_ENABLED = _read_env_bool("DUKCAPIL_QUERY_REWRITE", True)
# Cara menggabungkan hasil pertanyaan asli dan kueri tulis ulang: "max_score" atau
# "rrf" (lihat modul retrieval). Default tetap "max_score" agar putaran lama bisa diulang.
FUSION_METHOD = _read_env_str("DUKCAPIL_FUSION", "max_score")

# Batas panjang potongan dalam karakter; pasal yang lebih panjang dipecah dengan
# tumpang tindih agar kalimat di batas potongan tidak hilang konteksnya.
MAX_CHUNK_CHARS = _read_env_int("DUKCAPIL_MAX_CHUNK_CHARS", 1500)
CHUNK_OVERLAP_CHARS = _read_env_int("DUKCAPIL_CHUNK_OVERLAP_CHARS", 150)

# gpt-oss menghabiskan token untuk penalaran sebelum menjawab, jadi batasnya
# dibuat longgar; tetap dibatasi karena kuota Groq dihitung per token per menit.
ANSWER_MAX_TOKENS = _read_env_int("DUKCAPIL_ANSWER_MAX_TOKENS", 2048)
# Sonnet 5.5 berpikir sebelum menjawab dan token thinking ikut dihitung ke max_tokens:
# pada 1.500 token, teks juri terpotong atau kosong (terukur: ±3.000 token untuk satu
# penilaian faithfulness). Batas dibuat longgar; yang dibayar hanya token terpakai.
REWRITE_MAX_TOKENS = 1000
JUDGE_MAX_TOKENS = 8000

# --- Provider dan model -----------------------------------------------------

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_API_KEY_NAME = "GROQ_API_KEY"
ANTHROPIC_API_KEY_NAME = "ANTHROPIC_API_KEY"

# ID model wajib dicocokkan dengan daftar model aktif tiap provider sebelum dipakai,
# karena katalog provider berubah dari waktu ke waktu.
GROQ_ANSWER_MODEL_ID = _read_env_str("DUKCAPIL_GROQ_MODEL", "openai/gpt-oss-120b")
HAIKU_MODEL_ID = _read_env_str("DUKCAPIL_HAIKU_MODEL", "claude-haiku-5-5")
SONNET_MODEL_ID = _read_env_str("DUKCAPIL_SONNET_MODEL", "claude-sonnet-5-5")

RETRY_MAX_ATTEMPTS = 4
RETRY_BASE_DELAY_S = 2.0


@dataclass(frozen=True)
class ModelOption:
    """Satu pilihan model penjawab yang tampil di selector antarmuka."""

    key: str
    label: str
    provider: str
    model_id: str
    secret_name: str


ANSWER_MODEL_OPTIONS = (
    ModelOption(
        key="groq",
        # Label diturunkan dari ID model agar tampilan selalu sama dengan model yang menjawab.
        label=f"Groq · {GROQ_ANSWER_MODEL_ID.split('/')[-1]} (default)",
        provider="groq",
        model_id=GROQ_ANSWER_MODEL_ID,
        secret_name=GROQ_API_KEY_NAME,
    ),
    ModelOption(
        key="haiku",
        label="Anthropic · Claude Haiku 5.5",
        provider="anthropic",
        model_id=HAIKU_MODEL_ID,
        secret_name=ANTHROPIC_API_KEY_NAME,
    ),
)
DEFAULT_ANSWER_MODEL_KEY = "groq"

# Sonnet dipakai sebagai juri dan penulis ulang kueri, bukan penjawab, agar juri
# berbeda dari penjawab default dan jalur generasi utama tetap Groq (aturan RTM 2).
SONNET_OPTION = ModelOption(
    key="sonnet",
    label="Anthropic · Claude Sonnet 5.5",
    provider="anthropic",
    model_id=SONNET_MODEL_ID,
    secret_name=ANTHROPIC_API_KEY_NAME,
)


def find_answer_model_option(key: str) -> ModelOption:
    """Mengembalikan pilihan model penjawab berdasarkan ``key``; gagal bila tidak dikenal."""
    for option in ANSWER_MODEL_OPTIONS:
        if option.key == key:
            return option
    known_keys = ", ".join(option.key for option in ANSWER_MODEL_OPTIONS)
    raise ValueError(f"Model '{key}' tidak dikenal. Pilihan: {known_keys}.")


@functools.cache
def _read_local_secrets() -> dict[str, str]:
    """Mengembalikan isi ``.streamlit/secrets.toml`` lokal, atau dict kosong bila tidak ada."""
    if not LOCAL_SECRETS_TOML_PATH.exists():
        return {}
    with LOCAL_SECRETS_TOML_PATH.open("rb") as fh:
        return {key: str(value) for key, value in tomllib.load(fh).items()}


def get_secret(name: str) -> str | None:
    """Mengembalikan secret dari variabel lingkungan, lalu dari secrets.toml lokal."""
    return os.environ.get(name) or _read_local_secrets().get(name)


def has_secret(name: str) -> bool:
    """Mengembalikan True bila secret ``name`` tersedia dan tidak kosong."""
    return bool(get_secret(name))
