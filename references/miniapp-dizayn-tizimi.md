---
name: miniapp-dizayn-tizimi
description: Mini App CSS konvensiyalari — bo'shliq shkalasi (--s-*) va ikkita takrorlanuvchi CSS tuzog'i
metadata:
  type: reference
---

# Mini App dizayn tizimi — konvensiyalar

**Sana:** 2026-08-03 · `miniapp/src/styles.css`

## Bo'shliq shkalasi — yangi qoida

Ekran «zich» bo'lib qolgani uchun 4 px bazali shkala joriy etildi. **Yangi
qoidada tasodifiy raqam yozilmaydi** — eng yaqin qadam tanlanadi:

`--s-1:4 · --s-2:8 · --s-3:12 · --s-4:16 · --s-5:20 · --s-6:24 · --s-8:32`

Ustiga ma'noli aliaslar: `--gap` (bloklar orasi), `--card-pad`, `--row-pad`.
Ritmni o'zgartirish uchun **bitta joyni** tuzatish kifoya.

Istisno hujjatlashtirilgan: pill ichidagi 3–5 px optik to'ldirish shkaladan
tashqarida.

## ⚠️ Ikkita CSS tuzog'i (ikkalasi ham real xato bo'lgan)

**1. Umumiy `.card label` qoidasi komponent yorliqlarini bosib ketadi.**
`.card label { display: block; font-weight: 600 }` — `.check-row` ham `label`
bo'lgani uchun uning `display: flex` i bekor bo'lardi va **chekbox har doim
qatorning ustida** turardi. Tuzatish: `.card label:not(.check-row):not(.switch)`.
Yangi `label` asosidagi komponent qo'shsangiz — shu ro'yxatga qo'shing.

**2. Tugma ko'rinishidagi qator tugma uslubini bekor qilishi SHART.**
`<button className="link-row">` / `.photo-open` da `box-shadow`, `min-height`,
`border-radius`, `padding`, `background` ni qaytarmasa — har bir qator
«ko'tarilgan oq quticha» bo'lib ko'rinadi.

## `.row` endi grid

`display: grid; grid-template-columns: minmax(0,1fr) auto`. Sabab: flex'da
qator uzilishi siqilishdan **oldin** hisoblanadi, shuning uchun uzun yorliq
summani ikkinchi qatorga itarardi (`1 240 / 000 so'm`).

`Row` ning uchinchi bolasi — `.row-hint`, `grid-column: 1 / -1` bilan butun en
bo'ylab yoziladi (yorliq ichida bo'lsa tor ustunda siqilardi).

**Summalar hech qachon sinmaydi:** `white-space: nowrap` + tabular raqamlar.

## Ilova ichidagi qatlamlar

Foto ko'ruvchi uslublari alohida faylda — `src/lightbox.css`. Sabab: u dizayn
tizimi emas, mustaqil modal; ranglari ataylab qattiq (qora fon), tema
o'zgarishidan qat'i nazar bir xil bo'lishi kerak.

Bog'liq: [[narx-kelishuvi-kop-qatorli]]
