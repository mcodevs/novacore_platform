"""Telefon raqamini normalizatsiya — `+998XXXXXXXXX`."""

from __future__ import annotations

import re

_DIGITS = re.compile(r"\D+")


def normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = _DIGITS.sub("", raw)
    if not digits:
        return None
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 9:  # 901234567
        return f"+998{digits}"
    if digits.startswith("8") and len(digits) == 10:  # 8 90 123 45 67
        return f"+998{digits[1:]}"
    return f"+{digits}"


def normalize_plate(raw: str | None) -> str | None:
    """`01 A 123 BC` → `01A123BC` (bo'sh joysiz, katta harf)."""
    if not raw:
        return None
    cleaned = re.sub(r"[^0-9A-Za-zА-Яа-я]", "", raw).upper()
    return cleaned or None


def display_plate(plate: str) -> str:
    """`01A123BC` → `01 A 123 BC` (o'qish uchun)."""
    match = re.fullmatch(r"(\d{2})([A-Z])(\d{3})([A-Z]{2})", plate)
    if match:
        return " ".join(match.groups())
    return plate
