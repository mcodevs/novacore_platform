"""Davlat raqami va telefon normalizatsiyasi."""

from __future__ import annotations

import pytest

from app.core.phone import display_plate, normalize_phone, normalize_plate


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01A123BC", "01A123BC"),
        ("01 A 123 BC", "01A123BC"),
        ("01-a-123-bc", "01A123BC"),
        ("01760LMA", "01760LMA"),
        ("01 760 LMA", "01760LMA"),
        ("  30 777 aaa ", "30777AAA"),
    ],
)
def test_plate_normalization(raw, expected):
    """Qidiruv doim normalizatsiya qilingan ko'rinish bo'yicha ketadi."""
    assert normalize_plate(raw) == expected


@pytest.mark.parametrize(
    ("plate", "expected"),
    [
        ("01A123BC", "01 A 123 BC"),  # eski ko'rinish
        ("01760LMA", "01 760 LMA"),  # yangi ko'rinish
        ("30777AAA", "30 777 AAA"),
        ("XYZ", "XYZ"),  # tanilmagan — o'zgarishsiz
    ],
)
def test_plate_display(plate, expected):
    assert display_plate(plate) == expected


def test_plate_roundtrip_is_stable():
    for raw in ("01 A 123 BC", "01 760 LMA"):
        normalized = normalize_plate(raw)
        assert normalize_plate(display_plate(normalized)) == normalized


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+998993081155", "+998993081155"),
        ("998993081155", "+998993081155"),
        ("99 308 11 55", "+998993081155"),
        ("+998 99 308-11-55", "+998993081155"),
        ("8993081155", "+998993081155"),
    ],
)
def test_phone_normalization(raw, expected):
    assert normalize_phone(raw) == expected
