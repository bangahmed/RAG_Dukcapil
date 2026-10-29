"""Menambahkan root repo ke ``sys.path`` agar skrip di ``scripts/`` bisa mengimpor paket.

Skrip dijalankan langsung (``python scripts/build-index.py``), sehingga Python
hanya mengenal folder ``scripts/``; tanpa ini ``import dukcapil_pintar`` gagal.
"""

from __future__ import annotations

import sys
from pathlib import Path


def add_project_root_to_path() -> None:
    """Menyisipkan root repo di urutan pertama ``sys.path`` bila belum ada."""
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
