"""Menguji pemecahan teks regulasi per pasal dan pemotongan teks panjang."""

from __future__ import annotations

from dukcapil_pintar.chunking import (
    build_chunks,
    reflow_text,
    split_into_articles,
    split_long_text,
)
from dukcapil_pintar.ingestion import PageText, SourceDocument, clean_page_text

_SAMPLE_PAGES = [
    PageText(
        "perpres_96_2018",
        1,
        "PERATURAN PRESIDEN\nNOMOR 96 TAHUN 2018\nPasal 1\nDalam Peraturan Presiden ini...",
    ),
    PageText(
        "perpres_96_2018",
        2,
        "Pasal 34\nsebagaimana dimaksud dalam Pasal 1 berlaku.\nPENJELASAN\nPasal 1\nCukup jelas.",
    ),
]
_SAMPLE_DOCUMENT = SourceDocument(
    document_id="perpres_96_2018",
    document_title="Perpres 96/2018",
    file_name="perpres_96_2018.pdf",
    source_url="https://example.invalid/perpres",
    layer="1",
    is_required=True,
)


def test_split_into_articles_labels_preamble_articles_and_explanation() -> None:
    """Memastikan pembukaan, pasal batang tubuh, dan penjelasan diberi label berbeda."""
    labels = [section.article_label for section in split_into_articles(_SAMPLE_PAGES)]
    assert labels == ["Pembukaan", "Pasal 1", "Pasal 34", "Penjelasan Pasal 1"]


def test_split_into_articles_ignores_inline_article_references() -> None:
    """Memastikan rujukan pasal di tengah kalimat tidak memulai bagian baru."""
    sections = split_into_articles(_SAMPLE_PAGES)
    article_34 = next(s for s in sections if s.article_label == "Pasal 34")
    assert "sebagaimana dimaksud dalam Pasal 1" in article_34.text
    assert article_34.page_start == 2


def test_split_long_text_respects_limit_and_overlap() -> None:
    """Memastikan potongan tidak melebihi batas dan saling tumpang tindih."""
    text = " ".join(f"kata{n}" for n in range(400))
    parts = split_long_text(text, max_chars=200, overlap_chars=30)
    assert len(parts) > 1
    assert all(len(part) <= 200 for part in parts)
    assert parts[0][-10:].split()[-1] in parts[1]


def test_build_chunks_adds_header_and_unique_ids() -> None:
    """Memastikan tiap chunk diawali header dokumen-pasal dan ID-nya unik."""
    chunks = build_chunks(_SAMPLE_PAGES, _SAMPLE_DOCUMENT, max_chars=1500, overlap_chars=150)
    assert chunks[1].text.startswith("[Perpres 96/2018 · Pasal 1]")
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_split_into_articles_tolerates_ocr_noise_in_heading() -> None:
    """Memastikan judul pasal dengan sisa OCR ("Pasal 11l") tetap terbaca sebagai Pasal 11."""
    pages = [PageText("permendagri_19_2018", 1, "Pasal 10\nisi.\nPasal 11l '\nisi lain.")]
    labels = [section.article_label for section in split_into_articles(pages)]
    assert labels == ["Pasal 10", "Pasal 11"]


def test_split_into_articles_separates_amendment_items() -> None:
    """Memastikan pasal sisipan tidak menelan butir perubahan sesudahnya pada UU perubahan."""
    pages = [
        PageText(
            "uu_24_2013",
            1,
            "UNDANG-UNDANG\nPERUBAHAN ATAS UNDANG-UNDANG NOMOR 23\n"
            "19. Di antara Pasal 79 dan Pasal 80 disisipkan 1 pasal, yakni Pasal 79A\n"
            "Pasal 79A\ntidak dipungut biaya.\n20. Di antara BAB VIII disisipkan BAB VIIIA",
        )
    ]
    sections = {s.article_label: s.text for s in split_into_articles(pages)}
    assert "tidak dipungut biaya" in sections["Pasal 79A"]
    assert "BAB VIIIA" not in sections["Pasal 79A"]


def test_reflow_text_joins_broken_lines_but_keeps_list_markers() -> None:
    """Memastikan baris hasil pindaian disambung, sedangkan ayat dan huruf tetap terpisah."""
    text = "(1) Dokumen\nkependudukan\nyang ditingkatkan:\na. KK,\n\nb. KTP-el."
    assert reflow_text(text) == "(1) Dokumen kependudukan yang ditingkatkan:\na. KK,\nb. KTP-el."


def test_clean_page_text_drops_page_noise_and_fixes_ocr_year() -> None:
    """Memastikan nomor halaman, kepala halaman, dan salah baca tahun dibereskan."""
    raw = "2019, No.1479\n- 20 -\nPasal 34 . . .\nUndang-Undang Nomor 24 Tahun 2Ol3\nisi pasal"
    assert clean_page_text(raw) == "Undang-Undang Nomor 24 Tahun 2013\nisi pasal"


def test_clean_page_text_repairs_split_and_misread_article_headings() -> None:
    """Memastikan "Pasal 1 1" dan "Pasal T2" menjadi judul Pasal 11 dan Pasal 72."""
    cleaned = clean_page_text("Pasal 1 1\nisi.\nPasal T2\nisi lain.")
    assert cleaned == "Pasal 11\nisi.\nPasal 72\nisi lain."


def test_clean_page_text_joins_article_heading_only_at_sentence_boundary() -> None:
    """Memastikan judul terpisah baris disambung, tetapi rujukan di tengah kalimat tidak."""
    heading = "KETENTUAN UMUM\nPasal\n1\nDalam Peraturan Menteri ini:"
    assert clean_page_text(heading) == "KETENTUAN UMUM\nPasal 1\nDalam Peraturan Menteri ini:"
    reference = "dikenai pidana dalam\nPasal\n77\nDipidana dengan pidana penjara"
    assert "\nPasal\n77\n" in clean_page_text(reference)
