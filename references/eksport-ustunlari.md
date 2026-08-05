---
name: eksport-ustunlari
description: 2026-08-05 — eksportdan savdolashish ustunlari olib tashlandi, «Mashina» va «Avans» varag'i qo'shildi; sarlavhalar testda qotirildi
metadata:
  type: project
---

# Eksport ustunlari — nima ataylab yo'q

Egasi haqiqiy prod faylini (`tamirlar_20260801_20260901.xlsx`) ochib ko'rib
qaror qildi. Bu [[savdolashish-fokusdan-olindi]] (ADR-0019) ning **eksportga
yetib borishi**: UI'dan olib tashlangan narsa Excel'da qolib ketgan edi.

## Olib tashlangan ustunlar

| Varaq | Ketdi |
|---|---|
| Ta'mirlar | «So'ralgan ish haqi», «Kamaytirildi» |
| Ish qatorlari | «So'ralgan», «Kamaytirish sababi», «Rozilik» |

Qo'shildi: **«Mashina»** (2-varaqda, `Hisobot` yonida — mashina kesimida
filtrlaganda ikkalasi yonma-yon turgani qulay).

⚠️ **Ma'lumot yo'qolmadi:** `proposed_amount`, `price_change_reason`,
`mechanic_accept_mode` bazada va `approvals` / `audit_log` da to'liq turibdi.
Faqat kundalik Excel'dan chiqarildi. Savdolashish raqamlari kerak bo'lsa —
`kelishuv_*.xlsx` alohida eksporti bor.

## ⭐ Sarlavhalar endi testda qotirilgan

`tests/test_export.py` — `REPAIRS_HEADER` va `LINES_HEADER` ro'yxatlari bilan
**aynan tenglik** tekshiriladi, qiymatlar esa sarlavhaga `zip(..., strict=True)`
orqali bog'lanadi.

Sabab: **eksport hech qayerda ko'rinmaydi.** Xato ustun yoki bir pozitsiyaga
surilgan qator faqat buxgalter faylni ochganda bilinadi — o'shanda ham darrov
emas. Ustun qo'shish/olib tashlash ataylab qilinadigan ish, shuning uchun u
testni ham o'zgartirishni talab qilsin.

Ilgari eksportga umuman test yo'q edi.

## Topilgan xato — pul formati bir ustunga surilgan

`iter_rows(min_col=9, max_col=16)` deb yozilgan edi, aslida pul ustunlari
8–15 edi. Natijada birinchi pul ustuni **formatsiz** qolar, matnli «Avtomatik
tasdiq» ga esa `#,##0` berilardi. Ko'zga tashlanmasdi, chunki matnga son
formati ta'sir qilmaydi.

Endi `test_money_format_covers_exactly_the_money_columns` har ustunni
sarlavhasi bo'yicha tekshiradi — indeks emas, **nom** bilan.

> 📌 Umumiy saboq: `openpyxl` da ustun indekslari qo'lda yoziladi va sarlavha
> ro'yxati bilan avtomatik bog'lanmaydi. Ustun qo'shsangiz — format oralig'ini
> ham suring.

## `qarzlar_*.xlsx` — «Avans» varag'i qo'shildi

Egasi prod faylini ochib: *«Xodimda mavjud bo'lgan avans ham ushbu hujjatda
yozilsin.»*

⚠️ **Ma'lumot aslida faylga kirib kelgan edi, faqat ko'rinmasdi.**
`payment.debt_summary()` ro'yxatiga avansi bor, lekin qarzi yo'q xodim ham
tushadi (P7) — u yerda `count = 0`, `debt = 0`. Eksport shuni o'zgarishsiz
chizardi va prod faylida `Islom · 0 · 0` degan ma'nosiz qator turardi.

Yechim [[qarz-daftari-modeli]] dagi UI qarori bilan bir xil (2026-08-04:
avans alohida tabda — aralash qatorlar «kimga qancha qarzmiz?» savolini
ko'mib qo'yardi):

- **Qarzlar** varag'ida endi faqat haqiqiy qarzdorlar (`count > 0`)
- **Avans** — alohida varaq: `Xodim · Avans` + JAMI, ustida P7 izohi
- Fayl uch varaqli bo'ldi: `Qarzlar · Avans · To'lovlar`

> 📌 Bir xil ma'lumot ikki xil savolga javob beradi. «Kimga qarzmiz» va «kimda
> bizning pulimiz turibdi» — ikki xil jadval, bitta ro'yxat emas.

## Hujjat

`docs/04-flows/03-payroll-and-reports.md` §6 haqiqiy holatga keltirildi: u
yerda hali amalga oshirilmagan **5 ta fayl** sanalgan edi (`tolovlar_`,
`mashina_xarajatlari_`, `qismlar_`, `oylik_xulosa_.pdf`) va eksport «fon
vazifasi» deb yozilgandi. Aslida uchta fayl bor va ular sinxron yig'iladi.

Bog'liq: [[savdolashish-fokusdan-olindi]] · [[qarz-daftari-modeli]] ·
[[usta-formasi-ux]]
