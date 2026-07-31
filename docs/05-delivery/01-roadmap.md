# 01. Roadmap

## 1. Kontekst: kodni AI yozadi

Loyiha egasi kod yozmaydi — **AI yozadi**, egasi yo'naltiradi va tekshiradi.
Bu rejalashtirish uslubini o'zgartiradi:

| An'anaviy reja | Bu loyihada |
|---|---|
| Haftalar bilan o'lchanadi | **Iteratsiyalar** bilan o'lchanadi |
| Dasturchi kontekstni boshida saqlaydi | Kontekst **hujjatlarda** bo'lishi shart |
| "Keyin tushuntiraman" mumkin | Noaniq talab → noto'g'ri kod |
| Test ixtiyoriy | Test **majburiy** — AI kodini shu tekshiradi |

> ⚠️ **Shu sababli bu hujjatlar to'plami — texnik topshiriq.** Har bir faza
> boshida tegishli hujjatlar AI'ga to'liq beriladi. Hujjat noaniq bo'lsa —
> avval hujjat tuzatiladi, keyin kod yoziladi.

## 2. AI bilan ishlash tartibi (har faza uchun)

```
1. Faza hujjatlarini o'qish (docs/… tegishli fayllar)
2. Migratsiya + modellar → tekshirish
3. Domain qatlami + TESTLAR → testlar o'tishi shart
4. API endpointlari → OpenAPI ko'rib chiqish
5. Bot handlerlari
6. Mini App ekranlari
7. Seed ma'lumot (rollar, shablonlar, ish turlari)
8. Lokal sinov → fly.io deploy → real qurilmada sinash
```

**Har qadamdan keyin ishlaydigan holat.** "Hammasini yozib bo'lgach sinaymiz"
— AI bilan ishlashda eng xavfli yondashuv.

## 3. Fazalar

```
Faza 0        Faza 1 (MVP)         Faza 2            Faza 3
Tayyorgarlik  Yadro + ta'mir +     Rol konstruktori  Fleet + analitika
              narx kelishuvi       + ta'minotchi     + anti-fraud
   │              │                    │                  │
 3-5 kun      2-3 hafta            1-2 hafta          1-2 hafta
```

---

## Faza 0 — Tayyorgarlik (3–5 kun)

| # | Vazifa | Kim | Nima uchun kritik |
|---|---|---|---|
| 0.1 | 🔬 **Kamera sinovi** — `capture="environment"` Android va iOS Telegram'da | AI + egasi | ⚠️ Butun foto-dalil g'oyasi shunga bog'liq |
| 0.2 | 🔬 **Fleet API sinovi** — `status=repairing` yozish ishlaydimi | AI | Kalitlar `driver_status_reporter`da bor |
| 0.3 | **Mashina reyestri** — Fleet'dan 150 ta mashinani eksport qilish | AI + egasi | Boshlang'ich ma'lumot |
| 0.4 | **Xodimlar ro'yxati** — FIO, telefon, rol (4–5 usta + admin + buxgalter) | Egasi | Kirish shunga bog'liq |
| 0.5 | **Ish turlari ro'yxati** (30–60 ta) + tayanch narxlar | Egasi | Narx kelishuvi shunga tayanadi |
| 0.6 | fly.io app, Postgres, Tigris bucket, 2 ta bot (test + prod) | AI | |

> 📌 **0.5 haqida:** tayanch narxlar **faqat admin uchun**. Ustalarga
> ko'rsatilmaydi. Boshida taxminiy bo'lsa ham bo'ladi — 2–3 oydan keyin real
> tasdiqlangan narxlar statistikasi uni almashtiradi.

---

## Faza 1 — MVP: yadro + ta'mir + narx kelishuvi (2–3 hafta)

**Maqsad:** ta'mir hisoboti Telegram guruhdan bazaga ko'chsin va har bir narx
tizimda kelishilsin.

### Kiradi

| Blok | Tafsilot |
|---|---|
| **Auth** | `/start` → telefon → reyestr tekshiruvi → JWT |
| **Rol modeli** | `roles` (kind: reporter/admin/accountant), `role_templates` |
| **Shablon dvigateli** ⭐ | `templates` + `template_fields` + form renderer + validatsiya |
| **Ta'mir shabloni** | Seed sifatida yuklanadi (JSON) |
| **Hisobot oqimi** | Mashina keldi → forma → mashina ketdi → yuborish |
| **Foto** | Klientda siqish, Tigris'ga presigned upload, qayta urinish |
| **Qoralama** | Avtosaqlash, davom ettirish |
| **Narx kelishuvi** ⭐ | Admin kamaytiradi + sabab → usta rozi/nizo → 48 soat avtomatik |
| **Narx tarixi paneli** ⭐ | Admin uchun: o'rtacha/min/max + xodimning statistikasi |
| **Tasdiqlash** | Tasdiqlash / qaytarish / rad etish |
| **Bildirishnomalar** | Yuborildi · narx taklifi · tasdiqlandi · qaytarildi |
| **Admin CRUD** | Mashina, xodim, ish turlari |
| **Davr** | Oy yopilishi, qulflash, to'lov varaqasi |
| **Eksport** | Excel: hisobotlar, to'lovlar, kelishuv tejamkorligi |
| **i18n** | uz + ru |

### Kirmaydi
- Rol konstruktori UI (rollar **seed**da: usta, ta'minotchi, admin, buxgalter)
- Ta'minotchi shabloni (Faza 2)
- Anti-fraud bayroqlari (narx tarixi ko'rsatiladi, bayroqsiz)
- Fleet integratsiya
- Analitika dashboard (faqat Excel)

### Chiqish mezoni
- ✅ 4–5 usta 2 hafta davomida faqat platformadan foydalanadi
- ✅ Ta'mirlarning ≥ 90%i tizimda
- ✅ Narxlarning 100%i tizimda kelishilgan (og'zaki kelishuv yo'q)
- ✅ Admin oyni tizimdan yopadi, Excel buxgalterga mos keladi
- ✅ **"Bu oy kelishuv X so'm tejadi"** raqami ko'rsatiladi

---

## Faza 2 — Rol konstruktori va ta'minotchi (1–2 hafta)

**Maqsad:** admin **kod yozmasdan** yangi rol va shablon yarata olsin.

| Blok | Tafsilot |
|---|---|
| **Rol konstruktori UI** ⭐ | Nom (uz/ru), ikonka, turi, shablonlar |
| **Shablon konstruktori** ⭐ | Maydonlarni qo'shish/tartiblash, sozlash, nashr |
| **Shablon versiyalash** | Eski hisobotlar buzilmasin |
| **Ta'minotchi shabloni** | Qism nomi, narx, chek fotosi, yetkazib beruvchi, original/analog |
| **Bog'liq hisobotlar** | Qism xaridi ↔ ta'mir hisoboti |
| **Xodim narx statistikasi** | "Narxim 10% kamaytirilgan" ekrani |

### Chiqish mezoni
- ✅ Admin **30 daqiqada** yangi rol + shablon yaratadi va u ishlaydi
- ✅ Qism xarajatlari chek bilan tizimda

---

## Faza 3 — Integratsiya va analitika (1–2 hafta)

| Blok | Tafsilot |
|---|---|
| **Fleet sinxron** | Mashina reyestri + joriy haydovchi + `repairing` statusi |
| **Anti-fraud bayroqlari** | pHash, EXIF, rework, narx tarixi — **bloklamaydi** |
| **Bayroqlarni hal qilish** | Admin ekrani |
| **Analitika dashboard** | Mashina xarajati, xodim samaradorligi, downtime, kelishuv tejamkorligi |
| **Downtime hisoboti** | `left_at − arrived_at` bo'yicha |

---

## Faza 4+ — Keyingi g'oyalar

| Imkoniyat | Qiymati | Murakkabligi |
|---|---|---|
| Planli TO (probeg bo'yicha avtomatik) | 🔴 Yuqori | 🟡 O'rta |
| Statistik anomaliyalar (oylik avtomatik) | 🟡 O'rta | 🟡 O'rta |
| Zayavka (ta'mir so'rovi) moduli | 🟡 O'rta | 🟡 O'rta |
| Ombor (qism qoldig'i) | 🟢 Past | 🔴 Yuqori |
| Batareya SOH monitoringi | 🟡 O'rta | 🟡 O'rta |
| Ovozdan matnga | 🟢 Past | 🟡 O'rta |
| Foto AI tahlili (shikast aniqlash) | 🟢 Past | 🔴 Yuqori |

---

## 4. Asosiy xavflar

| # | Xavf | Ehtimollik | Ta'siri | Yumshatish |
|---|---|---|---|---|
| X1 | **Ustalar ishlatmaydi** | 🔴 Yuqori | 🔴 Katta | Pilot, sodda forma, **"hisobotsiz to'lov yo'q"** qoidasi |
| X2 | **Ustalar narx kelishuvidan norozi** | 🟡 O'rta | 🔴 Katta | Kamaytirishda sabab majburiy, tarixga tayanish, nizo huquqi, og'zaki suhbat saqlanadi |
| X3 | **Kamera majburlash ishlamaydi** | 🟡 O'rta | 🔴 Katta | Faza 0.1 da erta sinash, zaxira: EXIF tekshiruvi |
| X4 | **AI kodi ko'rinishidan ishlaydi, aslida noto'g'ri** | 🔴 Yuqori | 🔴 Katta | Domain testlari majburiy; narx kelishuvi va davr yopilishi to'liq qoplanadi |
| X5 | Noaniq hujjat → noto'g'ri kod | 🟡 O'rta | 🟡 O'rta | Faza boshida hujjatni qayta o'qish, noaniqlikni avval hujjatda hal qilish |
| X6 | Zaif internet ustaxonada | 🟡 O'rta | 🟡 O'rta | Offline qoralama, foto siqish, qayta urinish |
| X7 | Ma'lumot lokalizatsiyasi (fly.io) | 🟡 O'rta | 🟡 O'rta | Minimal shaxsiy ma'lumot; ko'chirish oson bo'lishi uchun standart Docker/Postgres/S3 |
| X8 | Scope creep | 🔴 Yuqori | 🟡 O'rta | Fazalar qat'iy, yangi g'oya → Faza 4 ro'yxatiga |

## 5. Testlar — AI kodi uchun majburiy

Bularsiz AI yozgan kodga ishonib bo'lmaydi:

| Modul | Nima tekshiriladi |
|---|---|
| **`pricing`** ⭐ | `approved ≤ proposed`; sabab majburiyligi; 48 soat avtomatik rozilik; nizo oqimi; `proposed` o'zgarmasligi |
| **`period`** | Yopilgan davrga yozuv kirmasligi; precheck to'sqinliklari; to'lov varaqasi `approved` bo'yicha hisoblanishi |
| **`approval`** | R1 — muallif o'z hisobotini qo'lda tasdiqlay olmasligi; **R1a — `admin` muallifi → avtomatik `APPROVED`, `approved = proposed`, kelishuvsiz** |
| **`template`** | Majburiy maydonlar; foto min/max; versiyalash — eski hisobot buzilmasligi |
| **`role`** | `reporter` tayanch narxni ko'ra olmasligi; `kind` bo'yicha ruxsatlar |
| **`submission`** | Holat o'tishlari; `arrived_at`/`left_at` mantiqi |

## 6. Joriy etish

```
Hafta 1–2 (pilot)
  2 usta + admin
  Eski usul (Telegram guruh) ham ishlaydi — parallel
  Har kuni fikr-mulohaza
        ↓
Hafta 3
  Barcha 4–5 usta
  Telegram guruhda hisobot qabul qilinmaydi
        ↓
Hafta 4+
  "Tizimda yo'q ish — to'lanmaydi" qoidasi kuchga kiradi
```

> ⚠️ **Eng muhim tashkiliy qaror:** *"hisobot tizimda bo'lmasa, ish haqi
> to'lanmaydi"*. Busiz odamlar Telegram guruhga qaytadi. Bu **texnik emas,
> boshqaruv qarori**.

---

**Keyingi:** [02. Ochiq savollar](02-open-questions.md)
