"""Memformat angka gaya Indonesia (titik ribuan, koma desimal) untuk keluaran manusia."""

from __future__ import annotations


def format_thousands(value: int) -> str:
    """Mengembalikan bilangan bulat dengan titik pemisah ribuan, mis. ``903.000``."""
    return f"{value:,}".replace(",", ".")


def format_decimal(value: float, digits: int = 2) -> str:
    """Mengembalikan bilangan desimal dengan koma desimal, mis. ``1,25``."""
    return f"{value:.{digits}f}".replace(".", ",")
