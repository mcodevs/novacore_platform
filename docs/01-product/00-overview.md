# 00. Umumiy ko'rinish va glossariy

## 1. Biznes konteksti

NovaCore — Toshkentdagi yirik Yandex taksopark. Uning boshqa parklardan farqi:

| Xususiyat | NovaCore modeli | Odatiy taksopark |
|---|---|---|
| Mashina egasi | **Park** | Ko'pincha haydovchining o'zi |
| Mashina turi | **Elektromobil** (Comfort / Comfort+) | Aralash, benzin/gaz |
| Haydovchi to'lovi | **Oylik maosh** | Komissiya / arenda |
| Ta'mir | **Parkning o'z ustalari** (o'z ustaxonalarida) | Tashqi servis |

**Masshtab:** ~**150** elektromobil · **4–5 usta** · kuniga **3–5 ta'mir**.

Bu modelning asosiy oqibati: **mashinaning har bir xarajati va har bir bo'sh turgan
soati — bevosita parkning zarari.** Haydovchi arenda to'lamaydi, aksincha maosh oladi.
Demak park uchun ikkita raqam hal qiluvchi:

1. **Bir mashinaga oylik xarajat** (ta'mir + ehtiyot qism + zaryad + sug'urta)
2. **Downtime** — mashina liniyada bo'lmagan vaqt (= yo'qotilgan daromad)

Hozircha bu ikkala raqam ham tizimli o'lchanmaydi.

## 2. Muammo

Ta'mir jarayoni bugun shunday ketadi ([A-01](../05-delivery/02-open-questions.md) —
tasdiqlangan):

```
Mashina ustaxonaga boradi
        ↓
Usta tuzatadi
        ↓
Narx USTA BILAN YUZMA-YUZ KO'RISHIB kelishiladi   ← hech qayerda yozilmaydi
        ↓  (Telegram guruhga rasm tashlanadi yoki tashlanmaydi)
Oy oxirida admin chat'larni varaqlab Excel yig'adi
```

**Hamma narsa faqat Telegram guruhlarida.**

Bundan kelib chiqadigan muammolar:

| # | Muammo | Oqibati |
|---|---|---|
| P1 | Hisobot **chat'da tarqoq** — qidirish qiyin, yo'qoladi | "Kimga qancha qarzmiz" 1–3 kun qo'lda yig'iladi |
| P2 | Ish **haqiqatan bajarilganini tekshirib bo'lmaydi** | Yo'q ishga to'lov |
| P3 | **Narx og'zaki kelishiladi** va hech qayerda qolmaydi | Nizolar; kim qancha so'ragani va qancha kelishilgani bilinmaydi |
| P3a | Har admin har xil kelishadi, oldingi narxlar esda qolmaydi | Bir xil ish har xil narxda |
| P4 | **Ehtiyot qism** hisobi yo'q | Eng katta xarajat moddasi (60–75%) ko'rinmaydi |
| P5 | Mashina bo'yicha **tarix yo'q** | Qaysi mashina "pul yeydi" — bilinmaydi |
| P6 | Downtime o'lchanmaydi | Mashina 3 kun turgani sezilmaydi |
| P7 | Rasm **eski/boshqa mashinadan** bo'lishi mumkin | Qayta ishlatilgan "dalil" |
| P8 | Boshqa rollar (yuvuvchi, omborchi...) umuman nazoratsiz | Kengayish imkoni yo'q |

## 3. Mahsulot maqsadi

> Har bir xodimning har bir ishi — **dalil bilan** (foto, vaqt, joy), **bir marta**
> kiritiladigan va **avtomatik yig'iladigan** yozuvga aylansin.

Uchta darajali maqsad:

1. **Yig'ish va kelishish** — hisobot chat'dan bazaga ko'chsin, **har bir narx
   tizimda kelishilsin** (MVP)
2. **Nazorat** — anti-fraud belgilari, ta'minotning ajratilishi, foto talablari
3. **Boshqarish** — mashina va xodim kesimida raqamlar, byudjet, profilaktika

## 4. Muvaffaqiyat mezonlari (KPI)

| Metrika | Bugun (taxmin) | 3 oydan keyin maqsad |
|---|---|---|
| Tizimda rasmiylashtirilgan ta'mirlar ulushi | ~0% | **> 95%** |
| **Tizimda kelishilgan narxlar ulushi** | 0% (og'zaki) | **100%** |
| **Narx kelishuvi tejamkorligi** | o'lchanmaydi | **oyiga aniq raqam** |
| **Qarz holati ko'rinishi** ("kimga qancha qarzmiz") | 1–3 kun qo'lda yig'iladi | **real vaqtda, bitta ekranda** |
| Bir mashinaga oylik ta'mir xarajati ko'rinishi | yo'q | **real vaqtda dashboard** |
| O'rtacha downtime (ta'mir boshlanishidan tugashigacha) | o'lchanmaydi | **o'lchanadi + −20%** |
| Rad etilgan / shubhali hisobotlar ulushi | o'lchanmaydi | **o'lchanadi, < 5%** |
| Platformadagi faol rollar soni | 0 | **≥ 4 rol** |

## 5. Loyiha doirasi (scope)

### ✅ Kiradi
- Telegram bot + Mini App (bitta bot, hamma rollar uchun)
- Ta'mir hisoboti (foto bilan) va **narx kelishuvi**
- Tasdiqlash oqimi va **qarz daftari** (hisobot bo'yicha to'lov)
- Mashina reyestri va mashina bo'yicha to'liq tarix
- **Universal shablon va rol konstruktori** (admin yangi rol yaratadi)
- Ta'minotchi roli — ehtiyot qism xaridi
- Yandex Fleet API bilan mashina sinxroni
- Excel eksport va admin dashboard

### ❌ Kirmaydi
- **Haydovchi roli** — tizimda yo'q ([ADR-0013](../05-delivery/03-decisions.md))
- **Filial** tushunchasi — ustalar o'z ustaxonalarida ishlaydi
- **Zayavka** oqimi — usta hisobotni o'zi ochadi
- **Ombor** (qoldiq, inventarizatsiya) — qism omborga tushmaydi
- 1C / buxgalteriya integratsiyasi — faqat Excel **eksport**
- Mobil ilova (iOS/Android native) — Mini App yetarli
- Ma'lumot import qilish — 0 dan boshlanadi

## 6. Asosiy domen ob'ektlari

- **Xodim (Employee)** — Telegram akkaunti orqali kiradigan NovaCore xodimi, **bitta**
  rolga ega.
- **Rol** — bu **nom** (Usta, Ta'minotchi, Elektrik…) + uch turdan biri
  (`reporter` / `admin` / `accountant`). Admin yangisini o'zi yaratadi.
- **Mashina (Vehicle)** — parkning elektromobili; davlat raqami — asosiy identifikator.
- **Hisobot (Submission)** — shablon bo'yicha to'ldirilgan yozuv. Ta'mir hisoboti,
  qism xaridi, yuvish — hammasi shu.
- **Narx kelishuvi** — usta so'ragan (`proposed`) va admin tasdiqlagan
  (`approved`) summa o'rtasidagi muzokara jarayoni.
- **Shablon (Template)** — istalgan rol uchun hisobot formasi tavsifi (maydonlar ro'yxati).
- **Tasdiqlash (Approval)** — hisobotni ko'rib chiqish natijasi.
- **Qarz (Debt)** — tasdiqlangan hisobotning to'lanmagan qoldig'i
  (`payable_amount − paid_amount`). Oy yopish tushunchasi yo'q
  ([ADR-0015](../05-delivery/03-decisions.md#adr-0015--qarz-daftari-oy-yopish-orniga-hisobot-boyicha-tolov-)).
- **To'lov (Payment)** — xodimga berilgan pul; bir yoki bir nechta hisobotga
  taqsimlanadi. O'zgarmas — xato bo'lsa `void` qilinadi.
- **Ustaxona** — ustaning o'z ish joyi (ixtiyoriy ma'lumot; filial tushunchasi yo'q).

## 7. Yuqori darajadagi oqim

```
        Usta                    Platforma                    Admin
          │                         │                          │
  [🚗 Mashina keldi] ──────────────►│  arrived_at              │
          │                         │  mashina → TA'MIRDA      │
          │                         │                          │
   Ish + foto + O'Z NARXI ─────────►│                          │
          │                         │                          │
  [🚙 Mashina ketdi] ──────────────►│  left_at                 │
          │                         │  downtime hisoblandi     │
          │                         │                          │
   [📤 Yuborish] ──────────────────►│ ────────────────────────►│
          │                         │   narx tarixi bilan      │
          │                         │                          │
          │      ⭐ NARX KELISHUVI  │◄── taklif: 180 000 ──────┤
          │◄────────────────────────│                          │
   [✅ Roziman] ───────────────────►│ ────────────────────────►│
          │                         │                          │
          │                         │◄──── tasdiqlandi ────────┤
          │                         │                          │
          │  Har tasdiqlangan hisobot → qarz → to'lov → arxiv  │
```

⚠️ **Haydovchi tizimda yo'q** — mashinaning kelgani va ketgani ustaning ikki
tugmasi bilan qayd etiladi. **Downtime = `left_at − arrived_at`**.

Batafsil: [04-flows/01-repair-lifecycle.md](../04-flows/01-repair-lifecycle.md)

## 8. Glossariy

| Atama | Ma'nosi |
|---|---|
| **Usta** | Parkning ta'mirlovchi xodimi (mexanik) |
| **Admin** | Hisobotlarni ko'radi, narx kelishadi, tasdiqlaydi, rol yaratadi |
| **Rol** | **Nom** + tur (`reporter` / `admin` / `accountant`) |
| **Hisobot** | Shablon bo'yicha to'ldirilgan yozuv (`submission`) |
| **Ish haqi** | Usta shu ish uchun oladigan summa (ehtiyot qism narxidan alohida) |
| **Ta'minotchi** | Ehtiyot qismni sotib oladigan alohida xodim |
| **So'ralgan narx** (`proposed`) | Usta taklif qilgan summa — o'zgarmaydi |
| **Tasdiqlangan narx** (`approved`) | Kelishuvdan keyingi yakuniy summa — to'lov shundan |
| **Tayanch narx** (`reference`) | Adminning savdolashuv mo'ljali (ustaga ko'rsatilmaydi) |
| **Downtime** | Mashina liniyada bo'lmagan vaqt |
| **Ustaxona** | Ustaning o'z ish joyi |
| **Smena** | Ish smenasi (kunduzgi / tungi) |
| **Fleet API** | Yandex Fleet partner API — park ma'lumotlari |
| **Mini App** | Telegram ichida ochiladigan veb-ilova |
| **initData** | Telegram Mini App autentifikatsiya ma'lumoti |
| **TO** | Texnik ko'rik (planli profilaktika) |
| **SOH** | State of Health — akkumulyator holati (%) |
| **Qarz** | Tasdiqlangan hisobotning to'lanmagan qoldig'i (`payable_amount − paid_amount`) |
| **To'lov** | Xodimga berilgan pul; hisobotlarga taqsimlanadi (`payments`) |
| **Rework** | Qayta ta'mir — yaqinda tuzatilgan joyning yana buzilishi |

---

## 9. Tasdiqlangan asosiy qarorlar

| Savol | Javob | Manba |
|---|---|---|
| Usta to'lovi | Har ish uchun, **narxni o'zi taklif qiladi**, admin kelishadi | [A-04](../05-delivery/02-open-questions.md) · [ADR-0009](../05-delivery/03-decisions.md) |
| Ehtiyot qism | **Alohida ta'minotchi xodim** sotib oladi | [A-05](../05-delivery/02-open-questions.md) · [ADR-0010](../05-delivery/03-decisions.md) |
| MVP doirasi | **Faqat usta + admin** | [A-07](../05-delivery/02-open-questions.md) · [ADR-0011](../05-delivery/03-decisions.md) |
| Jamoa | **Yolg'iz dasturchi** (Python tajribasi bor) | [A-17](../05-delivery/02-open-questions.md) · [ADR-0005](../05-delivery/03-decisions.md) |

---

**Keyingi:** [01. Rollar va ruxsatlar](01-roles-and-permissions.md)
