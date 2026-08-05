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

**3. `.card label` ning 16 px pastki bo'shlig'i `.stack` ichida qo'shilib ketadi.**
`.card label:not(.check-row):not(.switch)` da `margin-bottom: var(--s-4)` bor;
`label.field` to'g'ridan-to'g'ri `.stack` bolasi bo'lsa u to'plamning
`margin-top: var(--s-4)` iga **qo'shiladi** → 32 px, ritm buziladi. `.stack > *`
bekor qila olmaydi (selektor yengilroq). Yechim — `.card .stack > label.field
{ margin-bottom: 0 }`, ataylab o'sha qoidadan **keyin** (og'irlik teng, manba
tartibi hal qiladi). To'lov ekranida shu tuzoq bo'lgan
([[qarz-daftari-modeli]]).

**4. Plitkaga (`.tile`) summa qo'ysangiz — u sinadi.** 375 px'da plitka ichki
eni ~133 px, qiymat esa 28 px: «7 300 000» ikki qatorga bo'linib plitkani
cho'zadi va yonidagisi bilan bo'yi teng bo'lmay qoladi (2026-08-04, admin
paneliga «Umumiy qarz» qo'shilganda chiqdi). Yechim — `Tile` ga `money`
bayrog'i → `.tile-money`: 22 px + `nowrap` + tabular raqamlar.

⚠️ `line-height` ham moslanadi (**1.46**): 22 × 1.46 ≈ 28 × 1.15 — qator
balandligi oddiy plitkaniki bilan bir xil bo'lsagina yonma-yon plitkalarning
**yorliqlari bir chiziqda** turadi. `.grid` esa `align-items: stretch`.

## Xulosa qatori ≠ amal

`.pick-total` (belgilangan hisobotlar jami) — **xulosa**, shuning uchun tugma
emas va to'liq urg'u rangi berilmaydi: yupqa `--accent-soft` qatlam + urg'u
rangidagi raqam. To'liq indigo kartadagi **yagona haqiqiy amalga** qoladi.
Bir kartada ikkita to'la urg'uli tugma bo'lsa, foydalanuvchi qaysi biri
«asosiy» ekanini bilmaydi.


## Summa maydoni — faqat `MoneyInput` (2026-08-04)

Pul kiritiladigan **har bir** maydon `ui.tsx` dagi `MoneyInput` dan
foydalanadi: to'lov summasi, shablondagi `money` maydoni (usta narxi), qism
narxi (`LinesField`), admin kamaytirgan narx (`DetailScreen`). Yozilayotgan
raqam darhol guruhlanadi (`90 000`) — nol ko'p bo'lgani uchun «250000» va
«2500000» ko'z bilan farqlanmaydi.

- Tashqariga **toza raqam** chiqadi (`'90000'`) → chaqiruvchi `Number(...)`
  bilan ishlayveradi, probel tozalash kerak emas
- `type="number"` **ishlamaydi** — probelli qiymatni ushlab tura olmaydi
  (brauzer uni yaroqsiz deb `value` ni bo'shatadi). `inputMode="numeric"`
  telefonda baribir raqamli klaviatura ochadi
- Kursor o'rni raqamlar soni bo'yicha qayta tiklanadi, aks holda probel
  qo'shilganda kursor oxiriga sakrab, o'rtaga raqam qo'shib bo'lmaydi
- Miqdor (`qty`) va oddiy `number` maydoni tegilmagan — ular kasr bo'lishi mumkin

### ⚠️ Tuzoq: server `Decimal` ni QATOR qilib beradi

JSON'da summa `"250000.00"` bo'lib keladi (TS tipida `number` yozilgan bo'lsa
ham!). Raqamlarni ko'r-ko'rona yig'ib olsak nuqta tushib qoladi va maydonda
**25 000 000** — 100 barobar katta summa — paydo bo'ladi. Shuning uchun
`groupDigits` kasrli qiymatni avval **yaxlitlaydi**; chiplardan
(`quick_amounts`) yoziladigan qiymat ham `Math.round` bilan o'tadi.

Mantiq alohida modulda — `src/group-digits.ts` + 4 ta test (`unwrap.ts` bilan
bir uslubda: sof funksiya, `i18n` ga bog'liq emas, shuning uchun Node testida
import qilinadi). Bog'liq: [[qarz-daftari-modeli]]


### Holat

✅ Prodda — 2026-08-04, `fly deploy` (bundle `index-BZynp3CB.js`, lokal build
hashi bilan bir xil). Migratsiya yo'q.

⚠️ **Bu deploy commit qilinmagan ishchi papkadan chiqdi** — `fly deploy` git'ga
emas, papkaga qaraydi. Ya'ni shu lahzada prodda `git` da yo'q kod turibdi;
keyingi safar boshqa mashinadan deploy qilinsa u **yo'qoladi**. Deploydan
oldin commit qilish odat bo'lsin.

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

## Mashina raqami qidiruvi — so'rovlar poygasi (2026-08-05)

Prodda ko'rindi: to'liq raqam yozilgach «Mashina reyestrda topilmadi» chiqardi,
oxirgi belgini o'chirib qayta yozganda esa topardi.

Sabab — **javoblarning tartibsizligi**, raqam yoki serverda emas. Har bosilgan
harf uchun so'rov ketardi (`01718K`, `01718KN`, `01718KNA`); to'liq raqamning
«topildi» javobi kelib bo'lgach, undan oldingi qisqa raqamning «topilmadi»
javobi kechikib kelib natijani **bosib ketardi**.

Yechim (`form-renderer/fields.tsx` → `VehicleField`):

- **Navbat raqami** (`ticketRef`) — faqat eng oxirgi so'rov natijani yozadi.
  Asosiy tuzatish shu, kechikish emas
- 350 ms kechikish — 3 so'rov o'rniga 1 ta, oraliq xato chaqnamaydi
- `onChange` **ref orqali** effektga uzatiladi: har renderda yangi funksiya
  bo'lgani uchun bog'lanishga tushsa qidiruv cheksiz qayta ishga tushardi
- Raqam 6 belgidan qisqarsa — topilgan mashina tanlovi bekor qilinadi

⚠️ **Umumiy qoida:** yozilayotgan matnga bog'liq HAR QANDAY so'rovda (qidiruv,
tekshiruv, avtoto'ldirish) natijani yozishdan oldin uning **hali dolzarbligi**
tekshirilishi shart.

Bog'liq: [[qarz-daftari-modeli]]
