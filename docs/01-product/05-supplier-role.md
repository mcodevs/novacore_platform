# 05. Ta'minotchi roli (ehtiyot qismlar)

> **Ta'minotchi — bu alohida modul emas, shunchaki rol nomi.** U ham ustaga
> o'xshab rasmga oladi, izoh yozadi, narx qo'yadi va hisobot yuboradi — faqat
> boshqa shablon bilan ([rol modeli](01-roles-and-permissions.md)).

## 1. Nima uchun alohida rol

NovaCore'da ehtiyot qismni **alohida ta'minotchi xodim** sotib oladi.
Qism odatda ta'mir xarajatining **60–75%**ini tashkil qiladi — ya'ni eng katta
xarajat moddasi.

Ta'minotchi alohida bo'lgani uchun **vazifalar tabiiy ajraladi**:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    USTA      │     │  TA'MINOTCHI │     │    ADMIN     │
│              │     │              │     │              │
│ Qaysi qism   │     │ Qismni oladi │     │ Ikkalasini   │
│ ishlatilgani │     │ narx + chek  │     │ ko'radi va   │
│ yozadi       │     │ kiritadi     │     │ tasdiqlaydi  │
│              │     │              │     │              │
│ shablonida   │     │ shablonida   │     │ narxni       │
│ qism narxi   │     │ ish haqi     │     │ kelishadi    │
│ maydoni YO'Q │     │ maydoni YO'Q │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

⚠️ **Muhim nozik jihat:** bu **qattiq texnik taqiq emas**, balki **shablon
orqali ajratish**. Ustaning shablonida qism narxi maydoni yo'q, ta'minotchining
shablonida ish haqi maydoni yo'q. Admin xohlasa shablonni o'zgartirishi mumkin —
model buni taqiqlamaydi, faqat sukut bo'yicha shunday sozlangan.

Natija: usta qism narxini shishira olmaydi (chunki kiritmaydi), ta'minotchi
ishni o'ylab topa olmaydi (chunki ta'mir qilmaydi).

## 2. Ta'minotchi shabloni — "Ehtiyot qism xaridi"

| Maydon | Turi | Majburiy | Izoh |
|---|---|---|---|
| Mashina raqami | vehicle_picker | ✅ | Qaysi mashinaga |
| Bog'liq ta'mir hisoboti | submission_picker | — | Ustaning hisobotiga bog'lash |
| Qism nomi | catalog_picker / matn | ✅ | Katalogdan yoki qo'lda |
| Soni | son | ✅ | |
| **Birlik narxi** | pul | ✅ | Faqat shu shablonda bor |
| Yetkazib beruvchi | matn / tanlov | ✅ | |
| **Chek / nakladnoy** | 📷 foto | ✅¹ | 100 000 so'mdan yuqori uchun majburiy |
| Qism fotosi | 📷 foto | ✅ | Yangi qism |
| Original / analog | tanlov | ✅ | |
| Kafolat muddati (kun) | son | — | |
| Izoh | matn | — | |

¹ Chegara sozlamada.

> **Original/analog** maydoni muhim: analog arzon, lekin tez buziladi.
> Keyinchalik "analog qismlar rework'i original'dan necha barobar ko'p"
> degan savolga javob beradi.

## 3. Ta'minotchi ekrani

```
┌─────────────────────────────┐
│  📦 NovaCore — Ta'minotchi  │
├─────────────────────────────┤
│  📝 Qoralamalar         1   │
│  💬 Narx kelishuvi      0   │
│  ⏳ Tasdiq kutmoqda     3   │
│  ✅ Bu oy tasdiqlangan  18  │
├─────────────────────────────┤
│  Bu oy: 21 400 000 so'm     │
├─────────────────────────────┤
│  [ ➕ Qism xaridi ]          │
└─────────────────────────────┘
```

Xarid qo'shayotganda **narx tarixi** ko'rsatiladi — ta'minotchining o'zi uchun
savdolashuv quroli:

```
┌──────────────────────────────────────┐
│  Tormoz kolodka (old) · BYD Chazor   │
├──────────────────────────────────────┤
│  📊 Oxirgi narxlar:                  │
│     Avto-Nur    420 000  (12.06)     │
│     Detal Plus  455 000  (03.05)     │
│     o'rtacha    435 000              │
└──────────────────────────────────────┘
```

## 4. Oqim

```
Usta ta'mir qilyapti, qism kerak
        ↓  (og'zaki / telefon orqali — tizimda zayavka yo'q)
Ta'minotchi qismni sotib oladi
        ↓
Mini App → "Qism xaridi" → narx, chek fotosi, yetkazib beruvchi
        ↓
Hisobot yuboriladi → admin ko'radi
        ↓
Ustaning ta'mir hisobotiga bog'lanadi (related_submission_id)
        ↓
Mashina xarajati = ish haqi + qism narxi
```

> 📌 **Qism so'rovi (zayavka) oqimi MVP'da yo'q.** Usta qism kerakligini
> og'zaki aytadi. Agar keyinchalik kutish vaqtini o'lchash kerak bo'lsa —
> "Qism so'rovi" shabloni qo'shiladi (Faza 4).

## 5. Ehtiyot qism nazorati

| Bayroq | Qachon | Faza |
|---|---|---|
| `no_receipt` | Chek fotosi yo'q (chegaradan yuqori) | 3 |
| `part_price_jump` | Narx 90 kunlik o'rtachadan > 40% yuqori | 3 |
| `duplicate_receipt` | Bir xil chek ikki hisobotda (pHash) 🔴 | 3 |
| `part_soon_again` | Bir mashinaga bir xil qism 60 kun ichida 🔴 | 3 |
| `same_supplier_always` | Bitta yetkazib beruvchi ulushi > 80% 🟡 | 3 |

> `same_supplier_always` — nozik bayroq. U firibgarlik degani emas (yaxshi
> hamkor bo'lishi mumkin), lekin narx solishtirish yo'qligini bildiradi.
> Chorakda bir marta muqobil narx so'rash tavsiya etiladi.

## 6. Ombor yo'q

Qism **omborga tushmaydi** — sotib olinadi va darhol ishlatiladi.
Qoldiq, inventarizatsiya, minimal zaxira **yuritilmaydi**.

`parts_catalog` faqat **nom va narx tarixi** uchun (qoldiq emas).

## 7. Fazalar bo'yicha

| Faza | Ta'minot qanday ishlaydi |
|---|---|
| **Faza 1 (MVP)** | Usta qismni **ro'yxatga oladi** (nom + soni), **narxsiz**. Narxni **admin** hisobotni ko'rib chiqishda kiritadi |
| **Faza 2** | "Ta'minotchi" roli + "Qism xaridi" shabloni ishga tushadi |
| **Faza 3** | Qism bayroqlari, narx tendensiyasi tahlili |

---

**Keyingi:** [02-architecture/01-system-architecture.md](../02-architecture/01-system-architecture.md)
