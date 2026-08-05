---
name: savdolashish-fokusdan-olindi
description: 2026-08-04 — kelishuv ko'rsatkichlari UI'dan olib tashlandi (ADR-0019); backend tegilmadi
metadata:
  type: project
---

# Savdolashish endi fokusda emas — ADR-0019

> ♻️ **Davomi bor:** 2026-08-05 da shu mantiq **Excel eksportga** ham yetdi —
> [[eksport-ustunlari]]. Bir joydan olib tashlangan ko'rsatkich boshqa
> chiqishda qolib ketishi mumkinligini yodda tuting.

**Sana:** 2026-08-04 · Egasining qarori · `docs/05-delivery/03-decisions.md`

## Muammo

Egasining so'zi: *«Botdagi asosiy fokus kelishtirish bo'lib qolgan. Ha,
savdolashish bor, ammo bu asosiy maqsad emas.»*

Kelishuv shu qadar ko'p joyda ko'rinardi-ki, ilova o'zini «narxni qanchaga
tushirdik» tizimi qilib ko'rsatardi: admin hero'sida «Tejaldi … · 16.5%» va
so'ralgan/tasdiqlangan meteri, ustada «Kamaydi …», plitkada «Kelishuvda»,
profilda «Mening narx statistikam», **har hisobot kartochkasida** narx tarixi
va «👤 falonchi o'rtachasi · narxi 45% hollarda kamaytirilgan», har yangi
hisobot bildirishnomasida «📊 o'rtacha …», eksportda «Kelishuv tejamkorligi».

Platformaning maqsadi esa — **ishni qayd etish va pulni to'lash**
([[qarz-daftari-modeli]]).

## Qoida (yangi ADR bilan mustahkamlandi)

> Kelishuvga oid qiymat/matn **faqat kelishuv sodir bo'ladigan joyda** turadi.

| Qoladi | Olib tashlandi |
|---|---|
| Admin «Narxni kamaytirish» oynasi + shu yerda ishning narx tarixi | Hisobot kartochkasidagi narx tarixi |
| Ustaning roziman/nizo kartasi va plitkasi (48 soat muddat bor) | Profildagi «Mening narx statistikam» |
| `price_negotiation`/`price_disputed` statuslari va filtri | Hero'dagi «Tejaldi», «Kamaydi», meter |
| Kelishuv bildirishnomalari | Bildirishnomadagi «📊 o'rtacha …» (`_price_hint`) |
| `price_change_reason` | Eksport «Kelishuv tejamkorligi»; admin plitkasi «Kelishuvda» → **«Umumiy qarz»** |

- Ustani **profillovchi** qator («narxi N% hollarda kamaytirilgan») kamaytirish
  oynasida ham qoldirilmadi — u kelishuvni hamkorlikdan bahsga aylantiradi
- Hisobotda «So'radim» faqat narx **haqiqatan** kamaytirilganda ko'rinadi
- Bo'shagan joy asosiy mavzuga berildi: admin plitkasi endi qarz

## ⚠️ Backend tegilmadi

Hisob-kitob, `/me/price-stats`, `/reports/negotiation-savings`,
`price_context` va R2/R2a/R2b — hammasi joyida. Faqat interfeys va
bildirishnoma matni o'zgardi, ya'ni qaror qaytarilsa ma'lumot yo'qolmagan.
Klientdan esa `PriceStats` tipi va `myPriceStats()` o'chirildi, `ExportKind`
dan `savings` chiqarildi.

## Nima o'chdi (o'lik kod)

`Hero` dan `share`/`foot`/`delta` proplari va ular bilan `.meter`,
`.hero-foot`, `.delta` uslublari — boshqa hech kim ishlatmayotgan edi
([[miniapp-dizayn-tizimi]]).

Hujjatlar: ADR-0019 · `04-price-negotiation.md` (KPI jadvali «ekranda yo'q»
ogohlantirishi bilan) · `02-employee-flow.md` · CLAUDE.md dagi
«Ataylab YO'Q» ro'yxati.

Tekshiruv: miniapp 16/16 · backend 256/256 · build ✅.

## Holat

✅ **Prodda** — 2026-08-04, commit `e47781e` (main'ga push qilingan), bundle
`index-DC1S1lMO.js` (lokal build hashi bilan bir xil). Migratsiya yo'q.

Prodda tekshirildi: bundle ichida «Tejaldi», «Kamaydi», «narx statistikam»,
«hollarda kamaytirilgan» — **0 ta**; «Umumiy qarz» (yangi admin plitkasi) va
«Narx kelishuvi» (ustaning roziman/nizo kartasi) — joyida.
