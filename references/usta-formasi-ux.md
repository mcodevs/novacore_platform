---
name: usta-formasi-ux
description: 2026-08-05 — usta formasi UX tuzatmalari — qadamlar mustaqil (ADR-0022), chek majburiy emas (ADR-0021), qo'lda yozilgan nom, narx placeholder'i
metadata:
  type: project
---

# Usta formasi — UX tuzatmalari (2026-08-05)

Egasi prodda o'z ustalarini kuzatib sakkizta muammo yozib berdi. Barchasining
ildizi bitta: **funksionallik ishlaydi, lekin usta nima qilish kerakligini
tushunmaydi**. Kod to'g'ri edi, forma esa ustaning ish ritmiga emas, dasturchi
tasavvuridagi «bir o'tirishda to'ldirish» ritmiga qurilgan edi.

## 1. Qadamlar mustaqil — «saqla va chiq» (ADR-0022)

Eng katta o'zgarish. «Davom etish» tugmasi keyingi qadamga **darhol**
o'tkazardi. Ustaning kuni esa ajralgan: mashina keldi (raqam) → bir soatdan
keyin diagnostika (foto) → kechqurun ta'mir (ishlar) → oxirida yakun.

Endi har qadamda **bitta amal — «💾 Saqlash»**: saqlanadi va ekran yopiladi.

Uchta narsa buni ishlaydigan qiladi (biri yetishmasa oqim buziladi):

1. `FormRenderer.firstIncompleteStep()` — qoralama qayta ochilganda **birinchi
   to'ldirilmagan qadam**. Bo'lmasa usta har safar 1-qadamdan boshlanardi
2. **Qadam indikatori bosiladigan** (`.stepper button`) — oldinga yurishning
   yagona yo'li. Aks holda 2-qadamni tashlab 3-qadamga o'tib bo'lmaydi.
   ⚠️ CSS tuzoq: 3 px chiziqni barmoq bilan bosib bo'lmaydi → `padding` bilan
   teginish maydoni 27 px ga kengaytirildi, rang esa `background-clip:
   content-box` bilan chiziqda qoldi
3. **Bosh ekranda `draft` qatori formaga to'g'ridan-to'g'ri boradi**
   (`HomeScreen.onContinue`). `reopened` esa kartochkaga — u yerda adminning
   qaytarish sababi bor. Usta bitta hisobotga 3–4 marta qaytadi, oradagi
   «kartochka → ✏️» har safar ikki ortiqcha teginish edi

## 2. «Mashina ketdi» + «Yuborish» → bitta tugma

Usta uchun bu bitta hodisa. Ikkita tugma bo'lgani uchun birinchisini bosib
to'xtaganlar hisobotni qoralamada qoldirardi.

`finish()`: `patch` → `mark-left` (agar `left_at` yo'q bo'lsa) → `submit`.
Tasdiq oynasi bilan — bitta teginish endi qaytarib bo'lmaydigan amal.

⚠️ **Server xatosi boshqa qadamdagi maydonda bo'lishi mumkin.** Ilgari
`setErrors()` qilinardi-yu, usta oxirgi qadamda turib **hech narsa
ko'rmasdi**. Endi `stepOfField()` aybdor qadamga olib boradi. `_left_at` kabi
xizmat kodlari (`_` bilan boshlanadi) o'tkazib yuboriladi.

## 3. Katalog chipi — taklif, to'siq emas

Usta «Benzonasos» deb yozib, siyohrang «✍️ Benzonasos» chipini bosish
kerakligini tushunmay pastga o'tib ketardi — qator qo'shilmasdi.

`LinesField` da `picked` state o'rniga `name` + `catalogId`: **yozilgan
matnning o'zi tanlov**. Katalog chiplari faqat nomni to'ldiradi. «✍️» chip
umuman yo'q. `allow_custom: false` bo'lsa `catalogId` majburiy bo'lib qoladi.

## 4. Mayda, lekin ko'rinadigan

| Muammo | Yechim |
|---|---|
| `MoneyInput` placeholder'i `250 000` — to'ldirilgan qiymatdek ko'rinardi | matnli: «Summani yozing» + `Mening narxim *` |
| «Ish qo'shish» tugmasi izohga yopishgan | `.lines-add { margin-top: var(--s-4) }` — `.hint` da faqat `margin-top` bor |
| Tekshiruv xatosi `10+` | `t('min_chars')` — «Kamida 3 ta belgi yozing». **Xato matni har doim buyruq bo'lsin** |
| `min_length: 10` | 3 ga tushirildi (`problem_description`, `comment`): «Tozalandi» ham to'liq javob |
| «Tavsiya (keyingi ish)» maydoni | olib tashlandi — ixtiyoriy edi, to'ldirilmasdi |
| Chek fotosi majburiy edi | ADR-0021 — [[shablon-va-foto-qarorlari]] |
| Kelishuv kartochkasida tugmalar izohga yopishgan | `.hint + button/.btn-row/textarea` — **umumiy** qoida. Bir xil xato ikki joyda chiqqach, uchinchisini kutmadik |

## Shablon versiyasi

`car_repair` **v1 → v2**. Seed `TemplateVersion` snapshot'ini versiya bo'yicha
yozadi, shuning uchun eski hisobotlar v1 sxemasida o'qiladi va «Tavsiya»
matni ko'rinishda qoladi. ⚠️ Versiyani ko'tarmasdan JSON'ni o'zgartirish v1
snapshot'ini **ustidan yozadi** — tarixdagi hisobotlar jimgina o'zgaradi.

⚠️ Testlar seed versiyasiga bog'lanmasin:
`test_old_submission_uses_its_own_schema_version` `template.version` dan
o'qiydigan qilib qayta yozildi (ilgari `== 1` deb qotib qolgan edi).

## ✅ Prodda — 2026-08-05

Commit `546a928` (main, push qilingan), bundle `index-CzKWPYog.js` +
`index-2u-vX6kA.css` — **lokal build hashi bilan bir xil** (Docker Mini App'ni
o'zi yig'adi, shuning uchun hash mos kelishi serverda aynan sinalgan kod
turganini bildiradi).

Migratsiya yo'q. `seed_completed` logda — `car_repair` **v2** nashr etildi,
`usable_version` endi 2 ni qaytaradi. Boot paytida (~6 s: alembic + seed) bitta
health-check xatosi chiqadi va o'zi tuzaladi — bu normal.

⏳ **Egasi hal qiladigan ikkita savol:**

1. Ta'minotchi shablonida (`part_purchase.json` → `photo_receipt`) chek hamon
   `required: true`. ADR-0021 faqat ustaning ta'mir hisobotiga tegdi —
   ta'minotchi do'kondan nakladnoy bilan oladi, shuning uchun tegilmadi
2. Nizo sababi Mini App'da ko'rinmaydi (API `approvals` ni qaytarmaydi), admin
   uni faqat bot bildirishnomasidan o'qiydi. ADR-0023 dan keyin u aynan shu
   izohga qarab qaror qiladi → kelishuv tarixini kartochkaga chiqarish kerak
   bo'lishi mumkin
3. `kelishuv_*.xlsx` eksporti butunlay savdolashish haqida («TEJALDI»,
   «Kamaytirish %»). ADR-0019 va [[eksport-ustunlari]] mantig'i bo'yicha u ham
   ortiqcha bo'lishi mumkin — egasi hal qiladi
4. Ustaning bosh ekranida hero'da «Bu oy tasdiqlandi» turibdi, qarz esa
   pastdagi kartochkada. Almashtirish taklifi berilgan, javob kutilmoqda

Bog'liq: [[miniapp-dizayn-tizimi]] · [[shablon-va-foto-qarorlari]] ·
[[narx-kelishuvi-kop-qatorli]]
