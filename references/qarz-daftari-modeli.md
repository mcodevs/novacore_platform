---
name: qarz-daftari-modeli
description: 2026-08-03 — oy yopish olib tashlandi, o'rniga hisobot bo'yicha qarz daftari + avans (ADR-0015/0016)
metadata:
  type: project
---

# Qarz daftari — davr modelini almashtirdi

**Sana:** 2026-08-03 · **ADR-0015** va **ADR-0016** (`docs/05-delivery/03-decisions.md`)

## Nima uchun

Egasi oyni tasodifan yopib qo'yib, ishlay olmay qoldi ([[prod-data-reset-2026-08]]).
Sabab chuqurroq edi: to'lov real hayotda **oy chegarasiga bo'ysunmaydi** —
ustaga hafta o'rtasida, qisman, bir nechta ish uchun birdan pul beriladi.
Buxgalterning yagona savoli — *«kimga qancha qarzmiz?»* — davr modelida umuman
hisoblanmasdi, `payouts` esa all-or-nothing edi.

## Yangi model

**Oy yopish tushunchasi butunlay yo'q.** `periods`, `payouts`, `period_id`,
precheck, davr holat mashinasi — o'chirildi (~1440 qator).

- Har `APPROVED` hisobot = muallifga qarz: `payable_amount − paid_amount`
- To'lov: `payments` + `payment_allocations` daftari; o'zgarmas, xato → `void`
  (sabab majburiy, qarz qayta ochiladi)
- Uch usul: chekbox · summa kiritish (**FIFO**, eng eskidan, oxirgisi qisman) ·
  bitta hisobot kartochkasidan
- Oylik kesim `submitted_at` bo'yicha filtrlanadi — alohida jadval kerak emas

## Eng muhim g'oya — «narx bor = qarz bor»

Usta qismni **o'z cho'ntagidan** olishi mumkin (ADR-0016). Belgi va pul
**bitta harakat**: `self_funded` serverda narxdan kelib chiqadi —
`kind == part AND (belgi OR narx > 0)`; belgisiz qism narxi `0` ga tushiriladi.
Shu sababli «belgi yo'q, lekin qarz bor» holati **printsipial imkonsiz**.

⚠️ **Ta'minotchi ham qarzdor** (egasining qarori): u ham o'z puliga oladi va
kompaniya qaytaradi. Uning xaridi doim narx bilan kiritilgani uchun avtomatik
`self_funded` — alohida qoida yozilmadi, bitta qoida ikkala rolni qamradi.

⚠️ **ADR-0010 teshigi qisman qayta ochildi** (F5a): usta kompaniya olgan qismga
soxta belgi qo'yishi mumkin. Yagona to'siq — **chek fotosi** + admin ko'rigi.

## Avans (P7) — 2026-08-03 qo'shimchasi

Qarzdan **ortiq** to'lov rad etilmaydi: ortiqcha summa xodim hisobida **avans**
bo'lib turadi va yangi qarz tasdiqlanishi bilan **avtomatik** (FIFO) ishlatiladi.

- Avans = `Σ(to'lovlar) − Σ(allokatsiyalar)` — **alohida jadval yo'q**
- Avans allokatsiyasi o'sha to'lov yozuviga biriktiriladi → `void` avansni ham
  izsiz qaytaradi
- Qarzi yo'q xodimga to'lov ham mumkin — sof avans
- `apply_advance()` `approve` / `auto_approve` / `accept_price` oxirida chaqiriladi

## Invariantlar (yangi raqamlash)

`P1` faqat `APPROVED` to'lanadi · `P2` `paid ≤ payable` (DB CHECK, **bitta
hisobot** darajasida) · `P3` `payable` serverda hisoblanadi ·
`P4` `sum(allocations) ≤ payment.amount`, qoldiq — avans · `P5` to'lov
o'zgarmas, faqat `void` · `P6` kompaniya qismida narx yo'q · **`P7` avans**.

`CLAUDE.md` da **R4** va **R5** shunga mos qayta yozildi (eski R4 «yopiq davr»
endi yo'q).

## Ataylab qilinmagan

- **Bonus / jarima** — eski `payouts` da bor edi, olib tashlandi. Qarz doim
  aniq hisobotga bog'lanadi; kerak bo'lsa kelajakda `adjustment` yozuvi

## Holat (2026-08-03)

✅ **Prodga chiqarildi** — 2026-08-03, commit `e2dd3e0` (main), fly deploy.
Migratsiyalar `0004` + `0005` avtomatik bajarildi (`alembic upgrade head`
konteyner CMD ida). Prodda tasdiqlandi: `payments`/`payment_allocations` bor,
`periods`/`payouts` o'chgan, `payable_amount`/`paid_amount`/`self_funded` bor,
`odometer_km` o'chgan, `car_repair` 12 maydon + `photo_receipt`.
Zaxira: MPG `20260803-153435F` (deploy oldidan).

Backfill to'g'ri ishladi: yagona mavjud hisobot (`WO-2026-000022`, `paid`,
240 000) `payable = paid = 240000` bo'ldi — qarz bo'lib qayta paydo bo'lmadi.

✅ 253 backend + 8 miniapp test · chek fotosi majburiyligi (F5a) ·
«o'z hisobimdan» chekboksi — [[shablon-va-foto-qarorlari]]

❌ **Qolgan yagona xavf:** iOS'da kamera sinovi (ADR-0017 — zaxira yo'l yo'q).

Bog'liq: [[shablon-va-foto-qarorlari]]


## ⚠️ Ikki marta takrorlangan tuzoq — `MissingGreenlet`

`payment` modulida **ikki marta** bir xil sabab bo'yicha xato chiqdi: yangi
qurilgan `Payment` obyektining bog'lanishiga murojaat qilinganda SQLAlchemy
lazy yuklashga urinadi va async kontekstdan tashqarida yiqiladi.

1. **Testda topilgan:** `flush()` dan keyin `payment.allocations` ga murojaat.
   Yechim — allokatsiyalarni **obyekt qurilishida** biriktirish.
2. **Prodda topilgan (2026-08-03):** API `_payment_out()` da
   `payment.employee.full_name`. Yechim — `employee` bog'lanishini ham
   qurilishda biriktirish (`Payment(employee=obj, ...)`).

**Qoida:** yangi ORM obyektini qurganda, chaqiruvchi o'qishi mumkin bo'lgan
**har bir bog'lanish** konstruktorda berilishi kerak. `lazy="selectin"` faqat
**bazadan yuklangan** obyektlarga yordam beradi, yangi qurilganiga emas.

### Nima uchun testlar ushlamadi

Servis darajasidagi testlar `create_payment()` ni chaqirardi, lekin **javobni
serializatsiya qilmasdi** — xato esa aynan API qatlamida edi. Endi
`test_accountant_payment_flow` bor: qarz → to'lov → avans → tarix → `void`
oqimi **HTTP orqali** o'tadi. Test tuzatishsiz aynan `MissingGreenlet` bilan
yiqilishi tekshirib ko'rilgan.

ⓘ Ikkinchi kamchilik: klient JSON bo'lmagan javobni (`Internal Server Error`)
ko'r-ko'rona `JSON.parse` qilardi va foydalanuvchiga «JSON Parse error…»
ko'rsatib, asl muammoni yashirardi. `api.ts` endi tushunarli xato beradi.
