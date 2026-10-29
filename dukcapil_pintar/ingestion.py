"""Membaca daftar dokumen sumber dan mengekstrak teks regulasi per halaman.

PDF dibaca dengan PyMuPDF (Bab 6.1 buku pegangan). Dokumen hasil OCR ulang boleh
disimpan sebagai ``.txt``; halaman dipisah dengan karakter form feed bila ada.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

_PAGE_BREAK = "\f"
_EXCESS_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")
_TRAILING_SPACES_PATTERN = re.compile(r"[ \t]+\n")
# Baris yang berulang di tiap halaman (nomor halaman, kepala Berita Negara, situs JDIH,
# lambang) dan petunjuk sambungan seperti "Pasal 34 . . .". Dibuang karena menyela isi
# pasal yang melintasi halaman dan mengotori embedding.
_PAGE_NOISE_LINE_PATTERNS = (
    re.compile(r"^-\s*\d+\s*-$"),
    re.compile(r"^\d{4},\s*No\.\s*\d+$"),
    re.compile(r"^www\.peraturan\.go\.id$"),
    re.compile(r"^(SALINAN|REPUBLIK INDONESIA|PRESIDEN|PRES\s*I?\s*DEN)$"),
    re.compile(r"^(Pasal|Ayat|Angka)\s*\(?\d*[A-Z]?\)?\s*(\.\s*){2,}$"),
)
# Nomor pasal yang terpecah atau salah baca OCR pada baris judul: "Pasal 1 1" (=11),
# "Pasal T2" (=72). Hanya baris yang berisi judul saja yang diperbaiki.
_SPLIT_DIGITS_HEADING_PATTERN = re.compile(r"^(\s*Pasal\s+)(\d)\s+(\d)\s*$")
_OCR_SEVEN_HEADING_PATTERN = re.compile(r"^(\s*Pasal\s+)T(\d)\s*$")
_ARTICLE_NUMBER_LINE_PATTERN = re.compile(r"^\s*\d+[A-Z]?\s*$")
# Salah baca OCR pada tahun, mis. "2Ol3" untuk "2013".
_OCR_YEAR_PATTERN = re.compile(r"\b[12][0-9Ol]{3}\b")


@dataclass(frozen=True)
class SourceDocument:
    """Satu regulasi di korpus, sesuai baris pada ``data/sources.csv``."""

    document_id: str
    document_title: str
    file_name: str
    source_url: str
    layer: str
    is_required: bool


@dataclass(frozen=True)
class PageText:
    """Teks bersih dari satu halaman sebuah dokumen."""

    document_id: str
    page_number: int
    text: str


def load_source_documents(sources_csv_path: Path) -> list[SourceDocument]:
    """Mengembalikan daftar dokumen sumber yang tercatat di berkas CSV."""
    with sources_csv_path.open(encoding="utf-8", newline="") as fh:
        return [
            SourceDocument(
                document_id=row["document_id"],
                document_title=row["document_title"],
                file_name=row["file_name"],
                source_url=row["source_url"],
                layer=row["layer"],
                is_required=row["is_required"].strip().lower() == "true",
            )
            for row in csv.DictReader(fh)
        ]


def _fix_ocr_year(match: re.Match[str]) -> str:
    """Mengembalikan token tahun dengan huruf O dan l dikembalikan menjadi angka 0 dan 1."""
    return match.group(0).replace("O", "0").replace("l", "1")


def _is_page_noise(line: str) -> bool:
    """Mengembalikan True bila baris adalah nomor halaman, kepala halaman, atau sambungan."""
    stripped = line.strip()
    return any(pattern.match(stripped) for pattern in _PAGE_NOISE_LINE_PATTERNS)


def _is_sentence_boundary(previous_line: str) -> bool:
    """Mengembalikan True bila baris sebelumnya mengakhiri kalimat atau berupa judul kapital."""
    stripped = previous_line.strip()
    return not stripped or stripped[-1] in ".:;" or stripped.isupper()


def _repair_article_headings(lines: list[str]) -> list[str]:
    """Mengembalikan baris dengan judul pasal yang terpecah atau salah baca diperbaiki.

    "Pasal" dan nomornya yang terpisah baris hanya disambung bila baris sebelumnya
    mengakhiri kalimat; jika tidak, itu rujukan di tengah kalimat ("... dalam Pasal 77
    dipidana ...") yang tidak boleh menjadi judul.
    """
    repaired: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        is_split = (
            line.strip() == "Pasal"
            and index + 2 < len(lines)
            and _ARTICLE_NUMBER_LINE_PATTERN.match(lines[index + 1])
            and lines[index + 2].lstrip()[:1].isupper()
            and _is_sentence_boundary(repaired[-1] if repaired else "")
        )
        if is_split:
            repaired.append(f"Pasal {lines[index + 1].strip()}")
            index += 2
            continue
        line = _SPLIT_DIGITS_HEADING_PATTERN.sub(r"\g<1>\g<2>\g<3>", line)
        repaired.append(_OCR_SEVEN_HEADING_PATTERN.sub(r"\g<1>7\g<2>", line))
        index += 1
    return repaired


def clean_page_text(text: str) -> str:
    """Mengembalikan teks halaman tanpa baris noise, dengan spasi dan baris kosong dirapikan."""
    normalized = text.replace("\xa0", " ").replace("\r\n", "\n")
    lines = _repair_article_headings(normalized.split("\n"))
    kept_lines = [line for line in lines if not _is_page_noise(line)]
    normalized = _OCR_YEAR_PATTERN.sub(_fix_ocr_year, "\n".join(kept_lines))
    normalized = _TRAILING_SPACES_PATTERN.sub("\n", normalized)
    return _EXCESS_BLANK_LINES_PATTERN.sub("\n\n", normalized).strip()


def _extract_pdf_pages(file_path: Path) -> list[str]:
    """Mengembalikan teks mentah tiap halaman PDF secara berurutan."""
    with pymupdf.open(file_path) as document:
        return [page.get_text() for page in document]


def _extract_txt_pages(file_path: Path) -> list[str]:
    """Mengembalikan teks mentah berkas .txt, dipecah per halaman bila ada form feed."""
    return file_path.read_text(encoding="utf-8").split(_PAGE_BREAK)


def extract_pages(file_path: Path, document_id: str) -> list[PageText]:
    """Mengembalikan halaman bertek dari sebuah PDF atau .txt; halaman kosong dibuang."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        raw_pages = _extract_pdf_pages(file_path)
    elif suffix == ".txt":
        raw_pages = _extract_txt_pages(file_path)
    else:
        raise ValueError(f"Format {suffix} belum didukung: {file_path.name}")

    pages = []
    for page_number, raw_text in enumerate(raw_pages, start=1):
        text = clean_page_text(raw_text)
        # Halaman kosong biasanya hasil pindaian tanpa lapisan teks; dibuang agar
        # tidak menghasilkan chunk kosong, dan jumlahnya terlihat di laporan ekstraksi.
        if text:
            pages.append(PageText(document_id=document_id, page_number=page_number, text=text))
    return pages
