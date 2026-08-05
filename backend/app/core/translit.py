"""Lotin → kirill translitatsiyasi (o'zbek tili).

Kirillcha lokal **alohida lug'at emas**: `uz` matnidan avtomatik olinadi.
Sababi — 900 ga yaqin kalitni ikki nusxada saqlash bir necha kunda bir-biridan
uzilib qoladi; qo'shilgan har bir yangi kalit esa kirillchada shu zahoti,
hech kim eslamasdan paydo bo'lishi kerak.

Himoyalangan bo'laklar (`{param}`, HTML teg, URL, `/buyruq`, `&nbsp;`)
tegilmaydi. Emoji va boshqa lotin bo'lmagan belgilar o'zgarishsiz o'tadi.

Mos keladigan TS nusxasi: `miniapp/src/translit.ts` — ikkalasi bir xil
qoidalarga amal qiladi.
"""

from __future__ import annotations

import re

#: O'girilmaydigan atoqli nomlar va brendlar (registrga qaramay)
KEEP_WORDS = frozenset(
    {
        "novacore",
        "telegram",
        "excel",
        "yandex",
        "fleet",
        "mini",
        "app",
        "id",
        "pdf",
        "sms",
        "qr",
        "uzs",
        "web",
        "bot",
    }
)

#: Tegilmaydigan bo'laklar: shablon parametri, HTML teg, URL, bot buyrug'i, HTML entity
_PROTECTED = re.compile(
    r"(\{[^{}]*\}|<[^<>]*>|https?://\S+|/[A-Za-z_][A-Za-z0-9_]*|&[a-z]+;|"
    + r"\b(?:" + "|".join(sorted(KEEP_WORDS)) + r")\b)",
    re.IGNORECASE,
)

#: Apostrof variantlari (tutuq belgisi va o'/g' uchun) — bittasiga keltiriladi
_APOSTROPHES = "'‘’ʻʼ`´"

_DIGRAPHS: dict[str, str] = {
    "o'": "ў",
    "g'": "ғ",
    "sh": "ш",
    "ch": "ч",
    "yo": "ё",
    "ye": "е",  # «yer» → «ер», «йер» emas
    "yu": "ю",
    "ya": "я",
    "ts": "ц",
}

_SINGLES: dict[str, str] = {
    "a": "а",
    "b": "б",
    "d": "д",
    "e": "е",  # so'z boshida — э (pastda alohida)
    "f": "ф",
    "g": "г",
    "h": "ҳ",
    "i": "и",
    "j": "ж",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "q": "қ",
    "r": "р",
    "s": "с",
    "t": "т",
    "u": "у",
    "v": "в",
    "w": "в",
    "x": "х",
    "y": "й",
    "z": "з",
    "c": "к",
}


def _apply_case(source: str, target: str) -> str:
    """Manba bo'lagining registrini natijaga ko'chiradi."""
    if source.isupper() and len(source.strip(_APOSTROPHES)) > 1:
        return target.upper()
    if source[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


def _is_letter(char: str) -> bool:
    return char.isalpha() or char in _APOSTROPHES


def _convert(text: str) -> str:
    out: list[str] = []
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        lower = char.lower()

        # --- ikki harfli birikmalar ---
        pair = text[i : i + 2]
        pair_key = pair.lower()
        if pair_key and pair_key[-1] in _APOSTROPHES:
            pair_key = pair_key[0] + "'"
        # «yo'q» — bu «yo» + «q» emas, «y» + «o'» + «q». Apostrofli birikma
        # kuchliroq: keyingi juftlik o'/g' bo'lsa, joriy juftlikni yutmaymiz.
        nxt = text[i + 1 : i + 3].lower()
        nxt_key = (nxt[0] + "'") if len(nxt) == 2 and nxt[1] in _APOSTROPHES else nxt
        if pair_key in _DIGRAPHS and nxt_key not in ("o'", "g'"):
            out.append(_apply_case(pair, _DIGRAPHS[pair_key]))
            i += 2
            continue

        # --- tutuq belgisi: o'/g' emas, demak «ъ» (ta'mir → таъмир) ---
        if char in _APOSTROPHES:
            prev = out[-1] if out else ""
            # so'z ichida bo'lsagina — chekkadagi qo'shtirnoq tegilmaydi
            if prev and _is_letter(text[i - 1]) and i + 1 < length and text[i + 1].isalpha():
                out.append("ъ")
            else:
                out.append(char)
            i += 1
            continue

        if lower in _SINGLES:
            word_start = i == 0 or not _is_letter(text[i - 1])
            if lower == "e" and word_start:
                out.append(_apply_case(char, "э"))
            else:
                out.append(_apply_case(char, _SINGLES[lower]))
            i += 1
            continue

        out.append(char)
        i += 1
    return "".join(out)


#: Qoidadan chetga chiqadigan, ruschadan kirgan so'zlar
_FIXES = {"рейестр": "реестр"}


def to_cyrillic(text: str) -> str:
    """Lotincha o'zbek matnini kirillchaga o'giradi.

    >>> to_cyrillic("Ta'mir hisoboti yo'q")
    'Таъмир ҳисоботи йўқ'
    """
    if not text:
        return text
    parts = _PROTECTED.split(text)
    # split() himoyalangan bo'laklarni toq indekslarda qoldiradi
    result = "".join(part if idx % 2 else _convert(part) for idx, part in enumerate(parts))
    for wrong, right in _FIXES.items():
        result = result.replace(wrong, right).replace(wrong.capitalize(), right.capitalize())
    return result
