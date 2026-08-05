---
name: kirill-lokal-translit
description: 2026-08-05 — uchinchi til `uz_cyrl` qo'shildi; kirillcha lug'at qo'lda emas, lotinchadan avtomatik translitatsiya
metadata:
  type: project
---

# Kirillcha lokal — avtomatik translitatsiya (2026-08-05)

Uchinchi til qo'shildi: `uz` (lotin) · **`uz_cyrl` (kirill)** · `ru`.

## Asosiy qaror: ikkinchi lug'at YO'Q

Kirillcha matnlar `T` lug'atida **takrorlanmaydi** — `uz` qiymatidan ish vaqtida
translitatsiya qilinadi:

- `backend/app/core/translit.py` → `to_cyrillic()`, `i18n._fill_cyrillic()`
  import paytida `T` ning har bir yozuviga `uz_cyrl` ni qo'yadi
- `miniapp/src/translit.ts` → `toCyrillic()`, `i18n.resolve()` chaqiradi

Sabab: ~200 kalitni ikki nusxada yuritish bir necha kunda uziladi, yangi kalit
esa kirillchada **hech kim eslamasdan** paydo bo'lishi kerak. Zarur bo'lsa
kalitga `"uz_cyrl": "…"` ni ochiq yozish avtomatikani bekor qiladi.

⚠️ Ikkita nusxa (Python + TS) bir xil qoidalarga amal qiladi — **birini
o'zgartirsang, ikkinchisini ham**. Ikkalasida ham test bor
(`tests/test_translit.py`, `src/translit.test.ts`).

## Nozik joylar (test bilan qotirilgan)

- `yo'q` → `йўқ`, `ёъқ` emas: apostrofli birikma (`o'`, `g'`) `yo`/`ya`/`yu`
  dan **kuchliroq** — juftlikni yutishdan oldin keyingi juftlik tekshiriladi
- So'z ichidagi apostrof — tutuq belgisi: `ta'mir` → `таъмир`
- So'z boshida `e` → `э` (`Elektrik` → `Электрик`), `ye` → `е` (`yer` → `ер`)
- Tegilmaydi: `{param}`, HTML teg, URL, `/buyruq` va `KEEP_WORDS`
  (NovaCore, Telegram, Excel, Yandex…) — aks holda `{number}` buzilib,
  foydalanuvchi xom shablonni ko'radi

## Baza tegilmadi

`employees.lang` — oddiy `text`, **migratsiya yo'q**. Bazadagi ikki tilli
nomlar (`name_uz`/`name_ru`, `label_uz`, `hint_uz`) uchun **uchinchi ustun
qo'shilmadi**: yangi `i18n.pick(lang, uz, ru)` helperi `uz_cyrl` da lotinchani
o'giradi. `models.py`, `template/engine.py` shunga ko'chirildi; API javoblari
o'zgarmadi — Mini App `label()` da o'zi o'giradi.

## Qolgan o'zgarishlar

- Bot: `/til` da uchinchi tugma «🇺🇿 Ўзбекча», `setMyCommands` kirillcha,
  menyu matni handlerlari uch tilni ham tanidi (`LANGS` bo'yicha)
- Mini App: Profil ekranida uchinchi chip, `document.documentElement.lang`
  BCP 47 uchun `uz-Cyrl` ga aylantiriladi, `format.ts` birliklari — `с` / `дақ`
- Hujjat: `docs/03-integrations/02-telegram-bot-miniapp.md` §4 va CLAUDE.md

Bog'liq: [[miniapp-dizayn-tizimi]] · [[shablon-va-foto-qarorlari]]
