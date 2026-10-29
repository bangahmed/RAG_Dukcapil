"""Memecah teks regulasi menjadi chunk per pasal beserta metadatanya.

Chunking sadar-struktur (Bab 6.2) dipilih karena peraturan perundang-undangan
berstruktur jelas: satu pasal biasanya satu ketentuan utuh, dan jawaban warga
memang perlu merujuk nomor pasal.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from dukcapil_pintar.ingestion import PageText, SourceDocument

# Judul pasal berdiri di barisnya sendiri ("Pasal 34", "Pasal 79A"). Rujukan di
# tengah kalimat ("sebagaimana dimaksud dalam Pasal 5") sengaja tidak cocok.
_ARTICLE_HEADING_PATTERN = re.compile(r"^\s*Pasal\s+(\d+[A-Z]?)[lI]?\s*[^\w\s]*\s*$")
# Peraturan perubahan memuat butir "19. Di antara Pasal 79 dan ... disisipkan ..."
# tanpa judul pasal sendiri; tanpa batas ini, pasal sisipan (mis. Pasal 79A) ikut
# menelan butir perubahan sesudahnya.
_AMENDMENT_ITEM_PATTERN = re.compile(
    r"^\s*(\d{1,2})\.\s+(Ketentuan|Di antara|Diantara|Pasal|Judul|Penjelasan|BAB|Ayat)\b"
)
_AMENDMENT_TITLE_PATTERN = re.compile(r"PERUBAHAN\s+(KEDUA\s+)?ATAS", re.IGNORECASE)
# Awal baris yang harus tetap berdiri sendiri saat baris-baris hasil pindaian disambung.
_LINE_START_KEEP_PATTERN = re.compile(
    r"^\s*(\(\d+[a-z]?\)|[a-z]\.\s|\d{1,2}\.\s|Pasal\b|BAB\b|Bagian\b|Paragraf\b)"
)
# Bagian penjelasan mengulang nomor pasal; tanpa penanda ini kutipan "Pasal 1"
# bisa merujuk ke penjelasan, bukan ke batang tubuh.
_EXPLANATION_HEADING_PATTERN = re.compile(r"^\s*PENJELASAN\s*$")
_PREAMBLE_LABEL = "Pembukaan"


@dataclass(frozen=True)
class ArticleSection:
    """Teks satu pasal (atau pembukaan) beserta halaman awalnya."""

    article_label: str
    page_start: int
    text: str


@dataclass(frozen=True)
class Chunk:
    """Satu potongan teks siap di-embed, membawa identitas dokumen dan pasalnya."""

    chunk_id: str
    document_id: str
    document_title: str
    article_label: str
    page_start: int
    source_url: str
    text: str

    def to_record(self) -> dict:
        """Mengembalikan chunk sebagai dict untuk ditulis ke JSONL."""
        return asdict(self)

    @property
    def citation_label(self) -> str:
        """Mengembalikan label kutipan, mis. ``Perpres 96/2018 · Pasal 34``."""
        return f"{self.document_title} · {self.article_label}"


def _match_article_label(line: str, is_in_explanation: bool) -> str | None:
    """Mengembalikan label pasal bila baris adalah judul pasal, selain itu None."""
    match = _ARTICLE_HEADING_PATTERN.match(line)
    if match is None:
        return None
    label = f"Pasal {match.group(1)}"
    return f"Penjelasan {label}" if is_in_explanation else label


def split_into_articles(pages: list[PageText]) -> list[ArticleSection]:
    """Mengembalikan bagian per pasal dari halaman-halaman satu dokumen, berurutan."""
    sections: list[ArticleSection] = []
    is_amendment = bool(pages) and bool(_AMENDMENT_TITLE_PATTERN.search(pages[0].text[:800]))
    current_label = _PREAMBLE_LABEL
    current_page = pages[0].page_number if pages else 1
    current_lines: list[str] = []
    is_in_explanation = False

    def close_section() -> None:
        """Menyimpan bagian yang sedang dikumpulkan bila isinya tidak kosong."""
        text = "\n".join(current_lines).strip()
        if text:
            sections.append(ArticleSection(current_label, current_page, text))

    for page in pages:
        for line in page.text.splitlines():
            if _EXPLANATION_HEADING_PATTERN.match(line):
                is_in_explanation = True
            label = _match_article_label(line, is_in_explanation)
            item_match = _AMENDMENT_ITEM_PATTERN.match(line) if is_amendment else None
            if label is None and item_match and not is_in_explanation:
                label = f"Perubahan butir {item_match.group(1)}"
                close_section()
                current_label, current_page, current_lines = label, page.page_number, [line]
                continue
            if label is None:
                current_lines.append(line)
                continue
            close_section()
            current_label, current_page, current_lines = label, page.page_number, []
    close_section()
    return sections


def reflow_text(text: str) -> str:
    """Mengembalikan teks dengan baris yang terpecah di tengah kalimat disambung kembali.

    Hasil pindaian sering memecah satu kalimat menjadi satu kata per baris; baris
    yang diawali penanda ayat, huruf, atau nomor tetap berdiri sendiri.
    """
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        if lines and not _LINE_START_KEEP_PATTERN.match(line):
            lines[-1] = f"{lines[-1]} {line}"
        else:
            lines.append(line)
    return "\n".join(lines)


def split_long_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Mengembalikan potongan teks sepanjang ``max_chars`` dengan tumpang tindih.

    Potongan diakhiri di batas baris atau spasi terdekat agar kata tidak terbelah.
    """
    if len(text) <= max_chars:
        return [text]
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars harus lebih kecil dari max_chars.")

    parts = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            # Batas yang terlalu dekat dengan awal membuat potongan sangat pendek;
            # dalam kasus itu potong apa adanya.
            end = boundary if boundary > start + overlap_chars else end
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap_chars
    return [part for part in parts if part]


def build_chunks(
    pages: list[PageText],
    document: SourceDocument,
    max_chars: int,
    overlap_chars: int,
) -> list[Chunk]:
    """Mengembalikan chunk satu dokumen; tiap chunk diawali header dokumen dan pasal.

    Header ikut di-embed sehingga pertanyaan yang menyebut nama regulasi atau
    nomor pasal lebih mudah menemukan potongannya.
    """
    chunks = []
    for section in split_into_articles(pages):
        for part in split_long_text(reflow_text(section.text), max_chars, overlap_chars):
            header = f"[{document.document_title} · {section.article_label}]"
            chunks.append(
                Chunk(
                    # Nomor urut, bukan nomor pasal: UU perubahan memuat nomor pasal
                    # yang berulang, sehingga nomor pasal tidak unik.
                    chunk_id=f"{document.document_id}-{len(chunks):04d}",
                    document_id=document.document_id,
                    document_title=document.document_title,
                    article_label=section.article_label,
                    page_start=section.page_start,
                    source_url=document.source_url,
                    text=f"{header}\n{part}",
                )
            )
    return chunks
