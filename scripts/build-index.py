"""Membangun indeks RAG dari dokumen regulasi: ekstrak, chunk, embed, lalu indeks.

Contoh:
    python scripts/build-index.py                    # semua langkah
    python scripts/build-index.py --only chunk,embed,index
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import asdict

import numpy as np
from _project_root import add_project_root_to_path

add_project_root_to_path()

from dukcapil_pintar.chunking import Chunk, build_chunks  # noqa: E402
from dukcapil_pintar.config import (  # noqa: E402
    CHUNK_METADATA_JSONL_PATH,
    CHUNK_OVERLAP_CHARS,
    CHUNKS_JSONL_PATH,
    EMBEDDING_MODEL_NAME,
    EMBEDDINGS_NPY_PATH,
    FAISS_INDEX_PATH,
    MAX_CHUNK_CHARS,
    PAGES_JSONL_PATH,
    RAW_DIR,
    SOURCES_CSV_PATH,
)
from dukcapil_pintar.embedding import embed_texts  # noqa: E402
from dukcapil_pintar.formatting import format_thousands  # noqa: E402
from dukcapil_pintar.ingestion import (  # noqa: E402
    PageText,
    SourceDocument,
    extract_pages,
    load_source_documents,
)
from dukcapil_pintar.retrieval import (  # noqa: E402
    build_faiss_index,
    read_jsonl,
    save_index,
    write_jsonl,
)


def _find_missing_documents(documents: list[SourceDocument]) -> list[SourceDocument]:
    """Mengembalikan dokumen yang berkasnya belum ada di ``data/raw/``."""
    return [doc for doc in documents if not (RAW_DIR / doc.file_name).exists()]


def step_extract() -> None:
    """Mengekstrak teks tiap dokumen di ``data/raw/`` ke ``pages.jsonl``."""
    documents = load_source_documents(SOURCES_CSV_PATH)
    missing = _find_missing_documents(documents)
    missing_required = [doc.file_name for doc in missing if doc.is_required]
    # Dokumen wajib yang hilang menghentikan proses: korpus yang diam-diam tidak
    # lengkap akan membuat evaluasi menyesatkan.
    if missing_required:
        raise SystemExit("Berkas wajib belum ada di data/raw/: " + ", ".join(missing_required))
    for doc in missing:
        print(f"[lewati] {doc.file_name} (opsional, belum ada)")

    missing_ids = {doc.document_id for doc in missing}
    all_pages: list[PageText] = []
    for doc in documents:
        if doc.document_id in missing_ids:
            continue
        pages = extract_pages(RAW_DIR / doc.file_name, doc.document_id)
        char_count = sum(len(page.text) for page in pages)
        char_label = format_thousands(char_count)
        print(f"{doc.document_title:<28} {len(pages):>4} halaman  {char_label:>9} karakter")
        all_pages.extend(pages)

    write_jsonl([asdict(page) for page in all_pages], PAGES_JSONL_PATH)
    total_chars = sum(len(page.text) for page in all_pages)
    print(
        f"Total: {format_thousands(len(all_pages))} halaman, "
        f"{format_thousands(total_chars)} karakter → {PAGES_JSONL_PATH}"
    )


def step_chunk() -> None:
    """Memecah ``pages.jsonl`` menjadi chunk per pasal dan menyimpannya ke ``chunks.jsonl``."""
    documents_by_id = {doc.document_id: doc for doc in load_source_documents(SOURCES_CSV_PATH)}
    pages_by_document: dict[str, list[PageText]] = defaultdict(list)
    for record in read_jsonl(PAGES_JSONL_PATH):
        pages_by_document[record["document_id"]].append(PageText(**record))

    all_chunks: list[Chunk] = []
    for document_id, pages in pages_by_document.items():
        document = documents_by_id[document_id]
        chunks = build_chunks(pages, document, MAX_CHUNK_CHARS, CHUNK_OVERLAP_CHARS)
        article_count = len({chunk.article_label for chunk in chunks})
        print(f"{document.document_title:<28} {article_count:>4} pasal  {len(chunks):>5} chunk")
        all_chunks.extend(chunks)

    write_jsonl([chunk.to_record() for chunk in all_chunks], CHUNKS_JSONL_PATH)
    print(f"Total: {format_thousands(len(all_chunks))} chunk → {CHUNKS_JSONL_PATH}")


def step_embed() -> None:
    """Meng-embed seluruh chunk dengan model lokal dan menyimpan matriksnya ke .npy."""
    chunks = read_jsonl(CHUNKS_JSONL_PATH)
    print(f"Meng-embed {format_thousands(len(chunks))} chunk dengan {EMBEDDING_MODEL_NAME}…")
    embeddings = embed_texts([chunk["text"] for chunk in chunks], EMBEDDING_MODEL_NAME, True)
    EMBEDDINGS_NPY_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_NPY_PATH, embeddings)
    print(f"Embedding {embeddings.shape} → {EMBEDDINGS_NPY_PATH}")


def step_index() -> None:
    """Membangun indeks FAISS dari embedding dan menyimpannya bersama metadata chunk."""
    chunks = [Chunk(**record) for record in read_jsonl(CHUNKS_JSONL_PATH)]
    embeddings = np.load(EMBEDDINGS_NPY_PATH)
    # Ketidakcocokan jumlah berarti step_chunk dijalankan ulang tanpa step_embed;
    # indeks seperti itu akan mengembalikan teks pasal yang salah.
    if len(chunks) != embeddings.shape[0]:
        raise SystemExit("Jumlah chunk dan embedding berbeda. Jalankan ulang --only embed,index.")
    save_index(build_faiss_index(embeddings), chunks, FAISS_INDEX_PATH, CHUNK_METADATA_JSONL_PATH)
    print(f"Indeks {format_thousands(len(chunks))} vektor → {FAISS_INDEX_PATH}")


STEPS = {
    "extract": step_extract,
    "chunk": step_chunk,
    "embed": step_embed,
    "index": step_index,
}


def parse_args() -> argparse.Namespace:
    """Mengembalikan argumen CLI; ``--only`` berisi daftar langkah dipisah koma."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--only",
        default=",".join(STEPS),
        help=f"Langkah yang dijalankan, dipisah koma. Pilihan: {', '.join(STEPS)}.",
    )
    return parser.parse_args()


def main() -> None:
    """Menjalankan langkah-langkah yang dipilih sesuai urutan baku di ``STEPS``."""
    # Konsol Windows bawaan (cp1252) tidak bisa mencetak "→" dan "…".
    sys.stdout.reconfigure(encoding="utf-8")
    selected = {name.strip() for name in parse_args().only.split(",") if name.strip()}
    unknown = selected - STEPS.keys()
    if unknown:
        raise SystemExit(f"Langkah tidak dikenal: {', '.join(sorted(unknown))}")
    for name, step in STEPS.items():
        if name in selected:
            print(f"\n== step_{name} ==")
            step()


if __name__ == "__main__":
    main()
