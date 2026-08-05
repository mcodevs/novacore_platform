---
name: narx-kelishuvi-kop-qatorli
description: 2026-08-03 — kelishuv butun hisobot bo'yicha, effective_sum xatosi; 2026-08-05 — nizoda «yakuniy qaror» yo'q (ADR-0023)
metadata:
  type: project
---

# Narx kelishuvi — bitta hisobot, ko'p xizmat

**Sana:** 2026-08-03 · Egasining real iPhone sinovidan keyingi talab.

## Qaror

Admin **har bir xizmat uchun o'z summasini** kiritadi va **bitta** kelishuv
yuboradi. Usta ham butun taklifni birdan qabul qiladi yoki rad etadi.

Ilgari UI faqat bitta qatorni tanlashga majbur qilardi (chip'lar bilan) va
bitta `amount` holati barcha qatorlarga umumiy edi — tab almashganda oldingi
xizmatning summasi qolib ketardi (egasining skrinshotida: «Kalotka» tanlangan,
lekin maydonda «Balon»ning 200 000 i turibdi).

⚠️ **Backend allaqachon to'g'ri edi:** `propose_price(changes=[(line_id, amount)])`
ko'p qatorni qabul qiladi, `accept_price` esa barcha qatorlarni birdan yopadi.
Muammo faqat UI'da edi. Kod yozishdan oldin backend imzosini tekshirish
ortiqcha ishdan saqladi.

## ⭐ Topilgan xato — `effective_sum`

Admin bir nechta xizmatdan **faqat bir qismini** kamaytirsa, tegilmagan
qatorda `approved_amount = None` bo'lib qolardi. `sum_lines(approved=True)`
uni **nol** deb sanardi → ustaga boradigan bildirishnomadagi «Admin taklifi»
haqiqatdan **kam** ko'rinardi.

Misol: 150 000 + 100 000 = 250 000 so'ralgan, admin faqat birinchisini
120 000 ga tushiradi → «Admin taklifi» **120 000** deb ketardi, aslida
**220 000** bo'lishi kerak edi.

Yechim: `engine.effective_sum(lines, kind)` — tasdiqlangan summa bor bo'lsa u,
aks holda so'ralgani. `_notify_price_proposed` shunga o'tkazildi, Mini App'dagi
jami ham. Test: `test_partial_multiline_reduction_reports_full_total`.

Bu xato bir qatorli kelishuvda ko'rinmasdi — ko'p qatorli UI uni odatiy
holatga aylantirgan bo'lardi.

ⓘ Yakuniy tasdiqlash yo'li **to'g'ri edi**: `approval._approve_lines()`
tegilmagan qatorlarga `approved = proposed` qo'yadi.

## Foto ko'ruvchi (ilova ichida)

Fotolar `<a target="_blank">` bilan tashqi brauzerda ochilardi — usta ilovadan
chiqib ketardi. Endi `Lightbox` komponenti: pinch-zoom, surish, ikki marta
bosish, fotolar orasida o'tish, pastga surib yopish.

Telegram'da bitta `BackButton` bor, lekin endi ikki qatlam undan foydalanadi
(ekranlar steki + modal). Shuning uchun `telegram.ts` ga **back-handler steki**
qo'shildi: `pushBackHandler(fn)` → eng yuqoridagisi ishlaydi. App ham shunga
o'tkazildi. Aks holda «Orqaga» bosilganda foto ham, ekran ham yopilib ketardi.

## ⭐ Nizoda «yakuniy qaror» yo'q — ADR-0023 (2026-08-05)

Egasining qarori, **domen qoidasining o'zgarishi** (UX emas): *«Yakuniy qarorni
admin qabul qilmaydi. Ikki tomon kelishmagunicha savdolashish davom etadi.»*

Ilgari `PRICE_DISPUTED` da admin izoh yozib `approve()` qilardi va **o'zining
kamaytirilgan summasi** yakuniy bo'lardi. Ya'ni ustaning «Rozi emasman»
tugmasi amalda hech narsani o'zgartirmasdi — kelishuv nomigagina kelishuv edi.

Endi nizoda ikkita yo'l:

| Yo'l | Kod | Natija |
|---|---|---|
| ✏️ Yangi narx | `pricing.propose_price` (o'zgarmadi) | `PRICE_NEGOTIATION`, sikl qaytadan |
| ✅ Usta narxiga rozilik | **`pricing.accept_author_price`** (yangi) | `APPROVED`, `approved = proposed`, kamaytirish izlari tozalanadi |

⚠️ **Eng muhim tafsilot:** `approval.REVIEWABLE` dan `PRICE_DISPUTED` olib
tashlandi — `approve()` va `reject()` endi bu holatni **serverda** rad etadi.
Faqat UI'dan tugmani olib tashlash yetarli emasdi.

- Rozilik `ApprovalDecision.price_accepted` sifatida yoziladi — enum
  o'zgarmadi, **migratsiya yo'q**
- `price_negotiated` bayrog'i o'chirilmaydi: savdolashish bo'lgan, tarix
  `approvals` da
- ➖ Nizo **cheksiz** turishi mumkin: `PRICE_DISPUTED` da 48 soatlik taymer
  ishlamaydi. Yagona chiqish — `REOPENED`
- ⓘ Admin nizo sababini faqat **bot bildirishnomasida** ko'radi
  (`notify_price_disputed`) — Mini App API'si `approvals` ni umuman
  qaytarmaydi. Kelishuv tarixi kerak bo'lsa — alohida ish

Hujjatlarda: A-19/A-23 javobi teskarisiga o'zgartirildi, N3a qoidasi qo'shildi.

Bog'liq: [[shablon-va-foto-qarorlari]] · [[qarz-daftari-modeli]] ·
[[usta-formasi-ux]]
