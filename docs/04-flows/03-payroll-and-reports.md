# 03. Hisob-kitob va analitika

## 1. Davr (period) tushunchasi

Barcha moliyaviy hisob **kalendar oy** bo'yicha yuritiladi.

```
Hisobot yuborilganda → joriy ochiq davrga biriktiriladi (period_id)
        ↓
Oy tugadi → davr yopilishi boshlanadi
        ↓
Tekshiruvlar o'tdi → CLOSED
        ↓
• Yozuvlar qulflanadi
• To'lov varaqalari generatsiya qilinadi
• Excel paket eksport qilinadi
```

⚠️ Muhim nozik jihat: hisobot **yuborilgan** sanaga qarab davrga tushadi,
ish **bajarilgan** sanaga emas. Aks holda yopilgan davrga yangi yozuv kelib
qolishi mumkin. Agar ish 31-iyulda bajarilib, 2-avgustda yuborilsa — u
**avgust davriga** tushadi, lekin `finished_at` iyulda qoladi (analitika uchun).

✅ Bu qoida tasdiqlangan — [A-08](../05-delivery/02-open-questions.md).

## 2. Oy yopilishi — qadamlar

```
1. [Oyni yopish]
        ↓
2. Precheck (GET /periods/{id}/precheck):

   ❌ To'sqinlik qiluvchi (blocking)
      • 3 ta hisobot SUBMITTED (tasdiqlanmagan)
      • 1 ta hisobot REOPENED (usta tuzatmagan)
      • 2 ta kritik bayroq hal qilinmagan

   ⚠️ Ogohlantirish (non-blocking)
      • 5 ta qoralama 10 kundan beri turibdi
      • 2 ta hisobot narx kelishuvida
        ↓
3. Har biri uchun tanlov:
   [Hal qilish] yoki [Keyingi oyga ko'chirish]
        ↓
4. Yopish tasdiqlanadi → CLOSED
        ↓
5. Avtomatik:
   • payouts generatsiya
   • Excel paket (ta'mirlar, to'lovlar, mashina xarajatlari)
   • direktorga oylik xulosa
```

## 3. To'lov varaqasi (payout)

```
┌──────────────────────────────────────────┐
│  To'lov varaqasi — Iyul 2026             │
│  Usta: Karimov B.                        │
├──────────────────────────────────────────┤
│  Tasdiqlangan ishlar:            23 ta   │
│  So'ralgan (jami):        3 850 000 so'm │
│  Kelishuvda kamaydi:       −400 000 so'm │
│  Ish haqi (tasdiqlangan): 3 450 000 so'm │
├──────────────────────────────────────────┤
│  Bonus (sifat)             +150 000 so'm │
│    sabab: "rework 0%, baho 3.8"          │
│  Jarima                    −100 000 so'm │
│    sabab: "1 ta rad etilgan hisobot"     │
├──────────────────────────────────────────┤
│  JAMI:                    3 500 000 so'm │
├──────────────────────────────────────────┤
│  Status: [Qoralama] → [Tasdiqlangan]     │
│          → [To'langan]                    │
└──────────────────────────────────────────┘
```

Qoidalar:
- Faqat **APPROVED** hisobotlar kiradi
- To'lov **faqat `approved_amount`** bo'yicha — usta so'ragan summa emas
- `PRICE_NEGOTIATION` holatidagilar kirmaydi (davr yopilishida to'siq bo'ladi)
- `REJECTED` — kirmaydi
- Bonus/jarima **qo'lda**, sabab majburiy, audit log'ga yoziladi
- To'lov varaqasi Excel'ga eksport qilinadi (buxgalteriyaga)
- ⚠️ Platforma **pul o'tkazmaydi** — faqat hisoblab beradi

> ✅ **Tasdiqlangan model ([A-04](../05-delivery/02-open-questions.md)):**
> usta **har ish uchun** to'lov oladi, narxni **o'zi taklif qiladi**, admin
> **kelishib kamaytirishi** mumkin. Shu sababli to'lov varaqasida so'ralgan va
> tasdiqlangan summa yonma-yon ko'rsatiladi.

## 4. Analitika — asosiy hisobotlar

### 4.1. Mashina bo'yicha xarajat

```
┌────────────────────────────────────────────────────────────┐
│  Mashina xarajatlari — Iyul 2026            [Excel ⬇]      │
├──────────────┬────────┬──────────┬──────────┬──────────────┤
│ Mashina      │ Ta'mir │ Ish haqi │ Qismlar  │ JAMI         │
├──────────────┼────────┼──────────┼──────────┼──────────────┤
│ 01 A 123 BC  │   3    │  450 000 │ 1 850 000│ 2 300 000 🔴 │
│ 01 B 456 CD  │   1    │  120 000 │   380 000│   500 000    │
│ 01 C 789 DE  │   0    │        0 │         0│         0 ✅ │
├──────────────┼────────┼──────────┼──────────┼──────────────┤
│ O'RTACHA     │  1.2   │  180 000 │   420 000│   600 000    │
└──────────────┴────────┴──────────┴──────────┴──────────────┘
```

**Qo'shimcha kesimlar:**
- Mashina yoshi / probegi bo'yicha
- 1 km ga xarajat (probeg ma'lum bo'lsa)
- Umr davomidagi jami xarajat (mashina sotilishi kerakmi degan savol uchun)

> **Eng qimmatli savol:** *"Qaysi mashinani sotish kerak?"* Agar mashina yiliga
> o'z qiymatining 40%ini ta'mirga yesa — u zarar keltiryapti. Bu hisobotsiz
> bilinmaydi.

### 4.2. Usta samaradorligi va narx xulqi

| Usta | Ishlar | So'radi | Tasdiqlandi | Kamaytirish % | Nizo % | Rework % | Bayroqlar |
|---|---|---|---|---|---|---|---|
| Karimov B. | 23 | 3 850 000 | 3 450 000 | 10% | 4% | 4% | 2 |
| Sobirov A. | 31 | 7 900 000 | 5 890 000 | **25%** 🔴 | 19% 🔴 | 18% 🔴 | 7 🔴 |
| Yusupov D. | 18 | 2 180 000 | 2 100 000 | **4%** ✅ | 0% ✅ | 0% ✅ | 0 ✅ |

**Kamaytirish %** — bu jadvaldagi eng qimmatli ustun. Yusupov halol narx
qo'yadi (4%), Sobirov har safar chorak ortiqcha so'raydi (25%) va admin
vaqtini yeyadi. Bu — aniq raqamli suhbat mavzusi.

⚠️ **Ehtiyot bo'ling:** bu jadval odamlarni taqqoslaydi. Noto'g'ri ishlatilsa
zarar keltiradi:
- Ustalar turli murakkablikdagi ishlarni oladi
- Kam ish = yomon degani emas
- Raqamlar **suhbat uchun asos**, avtomatik jazo uchun emas

### 4.3. Downtime tahlili

| Mashina | Downtime (soat) | Qism kutish | Ta'mir | Hisobot kutish | Yo'qotilgan daromad* |
|---|---|---|---|---|---|
| 01 A 123 BC | 47 | 31 (66%) | 12 | 4 | ~2 800 000 |
| 01 B 456 CD | 12 | 0 | 10 | 2 | ~720 000 |

\* Yo'qotilgan daromad = downtime soat × o'rtacha soatlik daromad
(bu koeffitsient sozlamalarda belgilanadi)

**Bu hisobot ta'mir xarajatidan ham muhimroq bo'lishi mumkin:** 47 soat
downtime 2.8 mln so'm yo'qotish, ta'mirning o'zi esa 2.3 mln.

### 4.3a. Narx kelishuvi tejamkorligi ⭐

```
┌────────────────────────────────────────────┐
│  Iyul 2026 — narx kelishuvi                │
├────────────────────────────────────────────┤
│  Ustalar so'radi:          11 200 000 so'm │
│  Tasdiqlandi:               9 350 000 so'm │
│  ────────────────────────────────────────  │
│  💰 TEJALDI:                1 850 000 so'm │
│                                    (16.5%) │
├────────────────────────────────────────────┤
│  Kelishuvlar:                   38 / 84    │
│  O'rtacha kamaytirish:              19%    │
│  Nizolar:                        3 (3.6%)  │
│  48 soat sukut bilan:            7 (8.3%)  │
├────────────────────────────────────────────┤
│  ⓘ Avtomatik tasdiqlangan (admin):         │
│     3 ta · 1 240 000 so'm · kelishuvsiz    │
└────────────────────────────────────────────┘
```

> Bu hisobot — **platformaning o'zini oqlashi**. "Tizim bu oyda 1.85 mln so'm
> tejadi" degan raqam loyihani rahbariyat oldida himoya qiladi va uni
> kengaytirish uchun asos beradi.

### 4.4. Nosozliklar TOP

```
Iyul 2026 — kategoriya bo'yicha
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shina/g'ildirak    ████████████ 24 (28%)
Tormoz             ████████ 16 (19%)
Podveska/xodovoy   ███████ 14 (17%)
Elektr             █████ 11 (13%)
Kuzov              ████ 9 (11%)
Batareya/zaryad    ███ 6 (7%)
Boshqa             ██ 4 (5%)
```

**EV parkiga xos kutilayotgan naqsh:** shina va podveska ustunlik qiladi —
elektromobil og'irroq (batareya) va Toshkent yo'llari qattiq. Bu ma'lumot
xarid qarorlariga ta'sir qiladi (qaysi shinani olish, qaysi model afzal).

### 4.5. Ehtiyot qismlar

| Qism | Soni | Jami | O'rtacha narx | 90 kunlik o'zgarish |
|---|---|---|---|---|
| Tormoz kolodka (old) | 12 | 5 040 000 | 420 000 | +18% 🟡 |
| Shina 215/55 R17 | 8 | 6 400 000 | 800 000 | +2% |
| Amortizator | 5 | 3 250 000 | 650 000 | −5% |

Yetkazib beruvchilar kesimida ham ko'rsatiladi — narx solishtirish uchun.

## 5. Dashboard (real vaqtda)

| Blok | Ko'rsatkich |
|---|---|
| **Bugun** | Ochiq zayavkalar, ta'mirdagi mashinalar, tasdiq kutayotganlar |
| **Bu oy** | Ta'mirlar soni, jami xarajat, o'rtacha chek, o'tgan oyga nisbatan |
| **E'tibor** | Kritik bayroqlar, SLA buzilishi, uzoq downtime |
| **Trend** | So'nggi 6 oy xarajat grafigi |

## 6. Eksport

| Fayl | Mazmuni | Kim uchun |
|---|---|---|
| `tamirlar_2026_07.xlsx` | Barcha hisobotlar, to'liq ma'lumot | Admin |
| `tolovlar_2026_07.xlsx` | Usta × summa | Buxgalteriya |
| `mashina_xarajatlari_2026_07.xlsx` | Mashina × xarajat | Direktor |
| `qismlar_2026_07.xlsx` | Qism × narx × yetkazib beruvchi | Ta'minot |
| `oylik_xulosa_2026_07.pdf` | 1 sahifalik xulosa | Direktor |

Eksport **fon vazifasi** sifatida bajariladi (katta hajm), tayyor bo'lgach
Telegram orqali fayl yuboriladi.

## 7. Kelajakdagi kengaytmalar (v4+)

| Imkoniyat | Nima beradi |
|---|---|
| **1 km ga xarajat** (Fleet probeg bilan) | Haqiqiy solishtirish mezoni |
| **Byudjet vs fakt** | Oylik ta'mir byudjeti belgilanadi, oshib ketish signali |
| **Prognoz** | "Shu tendensiya bilan yil oxirida X so'm" |
| **Zaryad xarajati** | EV uchun ikkinchi eng katta xarajat moddasi |
| **Mashina TCO** | Sotib olish + ta'mir + zaryad + sug'urta − qoldiq qiymat |
| **Haydovchi reytingi** | Ta'mir chastotasi, shikast, downtime bo'yicha |

---

**Keyingi:** [05-delivery/01-roadmap.md](../05-delivery/01-roadmap.md)
