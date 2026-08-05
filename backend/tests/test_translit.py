"""Kirillcha lokal — lotinchadan avtomatik translitatsiya (`app/core/translit.py`).

Muhimi: kirillcha alohida qo'lda yuritilmaydi, shuning uchun `T` dagi **har bir**
kalitda `uz_cyrl` bo'lishi va shablon parametrlari buzilmasligi shart.
"""

from __future__ import annotations

import pytest

from app.core.i18n import CYRILLIC_LANG, LANGS, T, fmt_duration, pick, t
from app.core.translit import to_cyrillic


@pytest.mark.parametrize(
    ("latin", "cyrillic"),
    [
        ("Ta'mir hisoboti yo'q", "Таъмир ҳисоботи йўқ"),
        ("Qo'shish", "Қўшиш"),
        ("g'isht", "ғишт"),
        ("Chiqish vaqti", "Чиқиш вақти"),
        ("yer", "ер"),
        ("Elektrik", "Электрик"),
        ("NARX", "НАРХ"),
    ],
)
def test_basic_rules(latin: str, cyrillic: str) -> None:
    assert to_cyrillic(latin) == cyrillic


@pytest.mark.parametrize(
    "text",
    ["Hisobot {number}", "<b>Narx</b> {sum}", "/yordam", "https://example.com/a"],
)
def test_protected_fragments_survive(text: str) -> None:
    """Parametr, HTML teg, buyruq va URL — o'girilmaydi."""
    for fragment in ("{number}", "{sum}", "<b>", "</b>", "/yordam", "https://example.com/a"):
        if fragment in text:
            assert fragment in to_cyrillic(text)


def test_brand_names_kept_latin() -> None:
    assert to_cyrillic("Telegram bot va Excel eksport") == "Telegram bot ва Excel экспорт"


def test_every_key_has_cyrillic() -> None:
    missing = [key for key, entry in T.items() if CYRILLIC_LANG not in entry]
    assert not missing, f"kirillchasiz kalitlar: {missing}"


def test_placeholders_not_broken() -> None:
    """Shablon parametrlari kirillchada ham ishlaydi."""
    for key, entry in T.items():
        assert entry["uz"].count("{") == entry[CYRILLIC_LANG].count("{"), key


def test_langs_registered() -> None:
    assert CYRILLIC_LANG in LANGS


def test_t_returns_cyrillic() -> None:
    assert t("currency", CYRILLIC_LANG) == "сўм"


def test_fmt_duration_units() -> None:
    assert fmt_duration(12600, CYRILLIC_LANG) == "3 с 30 дақ"


def test_pick_transliterates_db_names() -> None:
    assert pick(CYRILLIC_LANG, "Ta'minotchi", "Снабженец") == "Таъминотчи"
    assert pick("ru", "Ta'minotchi", "Снабженец") == "Снабженец"
    assert pick("uz", "Ta'minotchi", "Снабженец") == "Ta'minotchi"
