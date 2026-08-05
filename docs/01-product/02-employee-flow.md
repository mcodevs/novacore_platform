# 02. Xodim hisobot oqimi

> Bu oqim **barcha rollar uchun bir xil**. Quyida u **usta** misolida
> tasvirlangan, chunki ta'mir hisoboti — birinchi va asosiy shablon.
> Ta'minotchi, yuvuvchi va admin yaratgan boshqa rollar **xuddi shu ekranlarda**,
> faqat boshqa maydonlar bilan ishlaydi ([rol modeli](01-roles-and-permissions.md)).

## 1. Foydalanuvchi sharoiti

| Jihat | Holat | Dizaynga ta'siri |
|---|---|---|
| Ish joyi | Ustaning **o'z ustaxonasi** | Internet zaif → offline-tolerant, qayta urinish |
| Qo'llar | Moyli, qo'lqopda | Katta tugmalar, kam yozish, ko'p tanlash |
| Til | O'zbek (lotin/kirill) / rus | i18n 1-kundan (ikkalasi ham kerak) |
| Telefon | O'rtacha Android | Og'ir JS bundle yaramaydi, foto siqish shart |
| Kompyuter savodxonligi | O'rtacha/past | Qadam-baqadam forma, bir ekranda 1–2 maydon |

> **Dizayn prinsipi:** hisobot **3 daqiqada** to'ldirilishi kerak. Aks holda
> odamlar yana Telegram guruhga qaytadi (hozirgi holat).

## 2. Asosiy ekran

```
┌─────────────────────────────┐
│  🔧 NovaCore — Usta         │   ← rol nomi shu yerda ko'rinadi
├─────────────────────────────┤
│  🚗 Ustaxonada          1   │   ← mashina keldi, ish tugamagan
│  📝 Qoralamalar         1   │
│  💬 Narx kelishuvi      2   │   ← ❗ javob kutmoqda
│  ⏳ Tasdiq kutmoqda     4   │
│  ✅ Bu oy tasdiqlangan  12  │
├─────────────────────────────┤
│  💰 Bu oy                   │
│     So'radim:   3 850 000   │
│     Tasdiqlandi:3 450 000   │
│     Kamaydi:       −10.4%   │
├─────────────────────────────┤
│  [ 🚗 Mashina keldi ]       │
└─────────────────────────────┘
```

## 3. Oqim: mashina keldi → ish → mashina ketdi → hisobot

Haydovchilar tizimda **rolga ega emas**. Mashinaning kelgani va ketgani —
**ustaning o'zi** tomonidan belgilanadi.

```
[ 🚗 Mashina keldi ]
        ↓  arrived_at = hozir  ·  mashina statusi: TA'MIRDA
Qadam 1 — Mashina raqami
        ↓
Qadam 2 — Ta'mirgacha (foto, muammo)
        ↓
Qadam 3 — Bajarilgan ishlar + o'z narxi
        ↓
Qadam 4 — Ta'mirdan keyin (foto, izoh)
        ↓
[ 🚙 Mashina ketdi ]
        ↓  left_at = hozir  ·  mashina statusi: LINIYADA
[ 📤 Hisobotni yuborish ]
```

**Downtime = `left_at − arrived_at`.** Ikkita tugma — butun downtime analitikasi
shundan chiqadi.

### Qadam 1 — Mashinani aniqlash

```
┌─────────────────────────────┐
│  Mashina raqami             │
│  ┌───────────────────────┐  │
│  │ 01 A 123 BC           │  │  ← maska bilan
│  └───────────────────────┘  │
│  [ 📋 Ro'yxatdan tanlash ]   │
├─────────────────────────────┤
│  ✓ Topildi:                 │
│  BYD Chazor · oq · 2024     │
│  Haydovchi: Ahmadov A.      │   ← Fleet'dan, faqat ma'lumot
│  Oxirgi ta'mir: 12 kun oldin│
│  ⚠️ Bu oy 2-marta ta'mirda  │
└─────────────────────────────┘
```

- Raqam **reyestrda bo'lishi shart**. Yo'q bo'lsa — "Adminga murojaat qiling".
- Tizim darhol **kontekst ko'rsatadi**: oxirgi ta'mirlar, shu oydagi xarajat.
- ⚠️ Ogohlantirishlar (takroriy ta'mir) shu yerda chiqadi.

### Qadam 2 — Ta'mirgacha bo'lgan holat

| Maydon | Turi | Majburiy | Izoh |
|---|---|---|---|
| Mashina umumiy ko'rinishi | 📷 foto | ✅ | Raqam ko'rinsin — bu ayni o'sha mashina |
| Muammo fotosi | 📷 1–5 ta | ✅ | Nosozlik joyi |
| Muammo tavsifi | matn | ✅ | |
| Nosozlik kategoriyasi | tanlov | ✅ | Tormoz / Xodovoy / Elektr / Kuzov / Salon / Shina / Batareya / Boshqa |

> 📷 **Ikki yo'l:** «Suratga olish» (kamera) yoki «Galereyadan» (ADR-0020).
> Manba yozib qo'yiladi, tekshiruv esa admin ko'rigida.
> Texnik cheklovlar: [media hujjati](../03-integrations/03-media-and-storage.md).

### Qadam 3 — Bajarilgan ishlar va **o'z narxi**

```
┌─────────────────────────────────────┐
│  Bajarilgan ishlar                  │
├─────────────────────────────────────┤
│  🔧 Old tormoz kolodkasini almashtirish│
│     Mening narxim:   250 000 so'm   │
│     [ ✏️ ]  [ 🗑 ]                   │
├─────────────────────────────────────┤
│  [ ➕ Ish qo'shish ]                 │
├─────────────────────────────────────┤
│  Ishlatilgan qismlar (ixtiyoriy)    │
│  📦 Tormoz kolodka (old)  ×1        │
│     ⓘ narxni ta'minotchi kiritadi   │
├─────────────────────────────────────┤
│  Mening ish haqim:   250 000 so'm   │
│  (admin tasdig'idan keyin yakuniy)  │
└─────────────────────────────────────┘
```

**Narx qoidalari:**

| Qoida | Sabab |
|---|---|
| Usta **o'z narxini** erkin kiritadi | Real bozor narxi ko'rinadi |
| **Tayanch narx ko'rsatilmaydi** | Aks holda hamma narx tayanchga yopishadi |
| Usta **o'z oldingi narxlarini** ko'radi | Izchil bo'lishi uchun |
| Yuborilgach narx admin ixtiyorida | Kelishuv boshlanadi |

To'liq mexanizm: [04-flows/04-price-negotiation.md](../04-flows/04-price-negotiation.md)

**Ehtiyot qismlar:** usta faqat **qaysi qism ishlatilganini** yozadi. Narxni
"Ta'minotchi" rolidagi xodim o'z shablonida kiritadi (chek bilan) —
[05-supplier-role.md](05-supplier-role.md).

### Qadam 4 — Ta'mirdan keyingi holat

| Maydon | Turi | Majburiy |
|---|---|---|
| Tuzatilgan joy fotosi | 📷 1–5 ta | ✅ |
| Mashina umumiy ko'rinishi (keyin) | 📷 | ✅ |
| Izoh | matn | ✅ |
| Tavsiya (keyingi ish kerakmi) | matn | — |

### Qadam 5 — Yuborish

Yuborilgandan keyin:
- Status: `DRAFT` → `SUBMITTED`
- **Usta endi tahrirlay olmaydi** (faqat admin `reopen` qilsa)
- Adminga bildirishnoma (narx tarixi statistikasi bilan)

### Qadam 6 — Narx kelishuvi (agar admin kamaytirsa)

```
┌─────────────────────────────────────┐
│  💬 Narx bo'yicha taklif             │
├─────────────────────────────────────┤
│  #WO-1247 · 01 A 123 BC             │
│  Old tormoz kolodka almashtirish    │
│                                      │
│  Siz so'radingiz:      250 000 so'm │
│  Admin taklifi:        180 000 so'm │
│                                      │
│  Admin izohi:                        │
│  "Bu ish odatda 175 000 ga bo'lgan" │
├─────────────────────────────────────┤
│  [ ✅ Roziman ]                       │
│  [ ❌ Rozi emasman (izoh yozish) ]    │
├─────────────────────────────────────┤
│  ⏱ 48 soat javob bermasangiz —      │
│     avtomatik rozilik hisoblanadi   │
└─────────────────────────────────────┘
```

- **Roziman** → `APPROVED`, to'lov varaqasiga 180 000 kiradi
- **Rozi emasman** → admin qayta ko'radi; **oxirgi so'z adminda**
- Har ikkala qadam `audit_log`da qoladi — nizo bo'lmaydi

## 4. Qoralama (draft) mexanikasi

- Har qadamda **avtomatik saqlanadi** (server + `localStorage` zaxira)
- Mini App yopilsa — "Tugallanmagan ish bor, davom etasizmi?"
- Qoralama 24 soatdan ortiq tursa — eslatma
- Qoralama 7 kundan ortiq tursa — adminga signal

## 5. Bot nima uchun kerak

⚠️ **Botda amal yo'q** (2026-08-01 qarori) — hamma ish Mini App'da.

| Buyruq / amal | Natija |
|---|---|
| `/start` | Ro'yxatdan o'tish (telefon) / menyu |
| `/app` yoki «🧩 Mini App» | Ilovani ochish |
| `/til` | uz ↔ ru |
| `/yordam` | Qo'llanma |
| Bildirishnomaga «🧩 Ochish» | Mini App'da **o'sha kartochka** ochiladi |

Narx taklifiga rozilik, hisobot yozish, statistika — hammasi ilovada.
Batafsil: [03-integrations/02-telegram-bot-miniapp.md](../03-integrations/02-telegram-bot-miniapp.md) §1

## 6. Xodim nimani ko'radi

| Ko'radi | Ko'rmaydi |
|---|---|
| O'z hisobotlari va statuslari | Boshqalarning hisobotlari va daromadi |
| O'z bu oygi summasi (so'ralgan / tasdiqlangan) | Umumiy park xarajati |
| O'z kelishuv taklifi (roziman / nizo) | ❌ Narx statistikasi — ekranda yo'q (ADR-0019) |
| Mashinaning ta'mir tarixi | ❗ **Tayanch narx** (ataylab yopiq) |
| O'z kelishuv tarixi va sabablar | Audit log, ehtiyot qism marjasi |

## 7. Chekka holatlar

| Holat | Yechim |
|---|---|
| Bir mashinada 2 usta ishlayapti | `co_authors[]` — ish haqi alohida qatorlarga yoziladi |
| Ish bir necha kun davom etadi | `arrived_at` / `left_at` alohida; downtime shundan |
| Ehtiyot qism kutilmoqda | Hisobot qoralamada qoladi, mashina `WAITING_PARTS` |
| Ta'mir kerak emas ekan (diagnostika) | Ish haqi = 0 yoki diagnostika narxi; `resolution = no_defect` |
| Mashina tashqi servisga ketdi | `is_external = true`, kontragent nomi, ish haqi = 0 |
| Usta xato raqam kiritdi | `SUBMITTED`gacha o'zi tuzatadi; keyin — `reopen` orqali |
| Internet yo'q | Qoralama lokal saqlanadi, foto navbatga, tarmoq kelganda yuboriladi |
| Usta narxni juda kam so'radi (xato) | Admin oshira olmaydi (R2) → `REOPENED`, usta o'zi tuzatadi |
| Usta narxga rozi bo'lmadi | Admin qayta ko'radi, **yakuniy qaror adminda** |

---

**Keyingi:** [03. Admin oqimi](03-admin-flow.md)
