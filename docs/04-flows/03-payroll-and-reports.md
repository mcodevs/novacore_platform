# 03. Hisob-kitob va analitika

## 1. Qarz daftari — asosiy model

> ⚠️ **Oy yopish tushunchasi YO'Q.** `periods`, `payouts`, precheck va R4 —
> olib tashlangan ([ADR-0015](../05-delivery/03-decisions.md#adr-0015--qarz-daftari-oy-yopish-orniga-hisobot-boyicha-tolov-)).
> Moliyaviy hisob **kalendar oyga emas, hisobotga** bog'langan.

Har bir **tasdiqlangan** (`APPROVED`) hisobot — muallifga qarz:

```
Hisobot APPROVED bo'ldi
        ↓
payable_amount hisoblanadi  ← serverda, submission_lines'dan (R7)
        ↓
Qarz = payable_amount − paid_amount        ← 0 dan katta bo'lsa, qarz
        ↓
Buxgalter to'laydi (to'liq yoki qisman)
        ↓
paid_amount == payable_amount  →  status = PAID
```

### 1.1. Qarz summasi nimadan iborat

```
payable_amount  =  tasdiqlangan ish haqi          (labor qatorlari)
                +  o'z hisobidan olingan qismlar  (part qatorlari, «o'z hisobimdan» ✅)
```

| Qator turi | «O'z hisobimdan» | Narx maydoni | Qarzga kiradi |
|---|---|---|---|
| `labor` (ish haqi) | — | ochiq | ✅ ha |
| `part` (qism) | ✅ qo'yilgan | ochiq (chek so'raladi, majburiy emas — [ADR-0021](../05-delivery/03-decisions.md#adr-0021--chek-fotosi-majburiy-emas)) | ✅ ha |
| `part` (qism) | ⬜ qo'yilmagan | **yopiq** | ❌ yo'q |

Ya'ni **narx bor = qarz bor**
([ADR-0016](../05-delivery/03-decisions.md#adr-0016--usta-oz-hisobidan-olgan-qism-ham-qarzga-kiradi)).
Kompaniya to'lagan qism hisobotda **nomi va soni bilan** qoladi (analitika
uchun), lekin narxsiz — u ta'minotchi hisobotidan keladi.

Belgi **serverda narxdan kelib chiqadi** (klientga ishonilmaydi, R7): narx
kiritilgan qism doim `self_funded`, narxsiz qism doim kompaniyaniki.

> **Ta'minotchi ham qarzdor.** U qismni o'z puliga oladi va kompaniya qaytaradi.
> Uning xaridi narx bilan kiritilgani uchun avtomatik `self_funded` bo'ladi —
> alohida qoida kerak emas, u ham qarzdorlar ro'yxatida ko'rinadi.

### 1.2. Qat'iy qoidalar

| # | Qoida |
|---|---|
| **P1** | To'lov faqat `APPROVED` hisobotga qo'llanadi |
| **P2** | `paid_amount ≤ payable_amount` — **bitta hisobot** qarzidan ortiq yopilmaydi (DB `CHECK`) |
| **P3** | `payable_amount` **serverda** `submission_lines`dan qayta hisoblanadi (R7) |
| **P4** | `sum(payment_allocations.amount) ≤ payments.amount`; qoldiq — **avans** |
| **P5** | To'lov **o'zgarmas**. Xato → `void` (sabab majburiy, `audit_log`) |
| **P6** | Narxi yo'q qism qatori kelishuvga kirmaydi (`proposed_amount = 0`) → R2 buzilmaydi |
| **P7** | Qarzdan ortiq to'langan pul — **avans**: xodim hisobida turadi va yangi qarz paydo bo'lishi bilan avtomatik ishlatiladi |

Oylik kesim kerak bo'lsa — `submitted_at` sanasi bo'yicha filtrlanadi.
Buning uchun alohida jadval kerak emas.

## 2. Buxgalter ekrani — navigatsiya

Buxgalter uchun hisobotlar **ikkita kesimda** ko'rinadi:

```
┌─────────────────────────────────────────────┐
│  [ To'langanlar ]   [ Qarzlar ]             │   ← ikkita tab
├─────────────────────────────────────────────┤
│  💰 Umumiy qarz:            8 450 000 so'm  │   ← bosiladi
└─────────────────────────────────────────────┘
                    ↓  bosildi
┌─────────────────────────────────────────────┐
│  Qarzdorlar                                 │
├─────────────────────────────────────────────┤
│  Karimov B.  (7 ta ish)     3 450 000 so'm →│
│  Sobirov A.  (5 ta ish)     2 900 000 so'm →│
│  Yusupov D.  (3 ta ish)     2 100 000 so'm →│
└─────────────────────────────────────────────┘
                    ↓  usta tanlandi
┌─────────────────────────────────────────────┐
│  Karimov B. — qarz 3 450 000                │
├─────────────────────────────────────────────┤
│  ☐ #124  01 A 123 BC   12-avg   450 000     │
│  ☐ #131  01 B 456 CD   14-avg   890 000     │
│  ☐ #138  01 C 789 DE   16-avg   320 000 ⚠️  │  ← qisman: 180 000 to'langan
│  …                                          │
├─────────────────────────────────────────────┤
│  Belgilangan (2 ta ish)         1 340 000   │
│  Summa: [ 1 340 000 ]                       │
│  [ To'lovni qayd etish ]                    │
└─────────────────────────────────────────────┘
```

- **Qarzlar** tab = `payable_amount − paid_amount > 0` (qisman to'langanlar ham
  shu yerda, qolgan summasi bilan)
- **To'langanlar** tab = `status = PAID` (to'liq yopilgan)
- Ro'yxat **eng eskisidan** boshlab tartiblanadi (FIFO tartibi ko'rinib tursin)

## 3. To'lov usullari — uchta

Uchalasi ham bitta mexanizmga tushadi: `payment` yoziladi va u
`payment_allocations` orqali hisobotlarga taqsimlanadi.

### 3.1. Belgilab to'lash (chekbox)

Buxgalter ro'yxatdan bir nechta hisobotni belgilaydi → belgilanganlarning
qolgan qarzi **to'liq** yopiladi.

```
☑ #124  450 000        payment(amount = 1 340 000)
☑ #131  890 000   →      ├→ #124 : 450 000
☐ #138  320 000          └→ #131 : 890 000
```

⚠️ **Ekranda alohida «Belgilanganlarni to'lash» tugmasi YO'Q** (2026-08-04).
Chekbox tanlovi **Summa maydonini to'ldiradi**, kartada esa bitta amal tugmasi
qoladi. Ya'ni ilova §3.1 ni har doim `submission_ids` + `amount` (server
3-rejim) orqali yuboradi — natija yuqoridagi bilan bir xil, lekin buxgalter
summani tahrirlab **belgilanganlarga qisman** ham to'lay oladi (u holda pul
belgilanganlar ichida **yana FIFO** taqsimlanadi — §3.2 bilan bitta qoida).

Chekbox ustidagi «Belgilangan · N ta ish → jami» qatori — **xulosa**, tugma
emas. `amount`siz `submission_ids` rejimi API'da qoladi (bot/skript uchun),
Mini App uni ishlatmaydi.

### 3.2. Summa kiritib to'lash (FIFO) ⭐

Buxgalter faqat summani kiritadi. Tizim **eng eski qarzdan** boshlab
taqsimlaydi; pul yetmagan joyda oxirgi hisobot **qisman** yopiladi.

```
Kiritildi: 1 500 000

#124 (12-avg)  450 000  →  to'liq   ✅  qoldi: 1 050 000
#131 (14-avg)  890 000  →  to'liq   ✅  qoldi:   160 000
#138 (16-avg)  320 000  →  qisman   ⚠️  160 000 to'landi, 160 000 qarz
                            qoldi: 0
```

- Tartib — `submitted_at` bo'yicha **o'sish tartibida** (eng eskisi birinchi)
- Pul ortib qolsa (barcha qarz yopilgach) → ortiqcha summa **avans** bo'ladi
  (P7, §3.3a) — rad etilmaydi

### 3.3. Bitta hisobot ichidan

Har bir tasdiqlangan hisobot kartochkasida **«To'lov qilish»** tugmasi:
to'liq summa taklif qilinadi, buxgalter uni **kamaytirib** qisman to'lay oladi.

### 3.3a. Avans — qarzdan ortiq to'lov ⭐

Buxgalter qarzdan **ko'proq** to'lasa (yoki qarzi yo'q xodimga to'lasa), ortiqcha
summa **rad etilmaydi** — u xodim hisobida **avans** bo'lib turadi:

```
Qarz: 300 000        Kiritildi: 500 000
        ↓
#124  300 000  →  to'liq   ✅
Avans:  200 000  ←  hech qaysi hisobotga biriktirilmaydi
        ↓
Usta yangi ish topshirdi va u tasdiqlandi (250 000)
        ↓
Avansdan 200 000 avtomatik ishlatiladi  →  qarz 50 000 bo'lib qoladi
```

- **Avans = `Σ(to'lovlar) − Σ(allokatsiyalar)`** — alohida jadval kerak emas
- Yangi qarz paydo bo'lishi bilan **avtomatik** ishlatiladi (FIFO, eng eski qarzdan)
- Avans allokatsiyasi **o'sha to'lov yozuviga** biriktiriladi → to'lov `void`
  qilinsa, avans ham izsiz qaytadi
- Qarzi umuman yo'q xodimga to'lov qilish mumkin — bu **sof avans**
- ⚠️ P2 buzilmaydi: bitta hisobot hech qachon o'z qarzidan ortiq yopilmaydi;
  ortiqcha pul hisobotga **umuman tegmaydi**

### 3.4. Umumiy qoidalar

- Faqat **`APPROVED`** hisobot to'lanadi (P1). `SUBMITTED`, `REOPENED`,
  `PRICE_NEGOTIATION`, `PRICE_DISPUTED`, `REJECTED` — qarz ro'yxatiga tushmaydi
- Qarzdan ortiq to'lov **rad etilmaydi** — u avansga aylanadi (P7, §3.3a)
- To'lov asosi — **tasdiqlangan** summa (`payable_amount`), usta so'ragan emas
- ⚠️ Platforma **pul o'tkazmaydi** — faqat qayd etadi
- «To'lovni qayd etish» **tasdiq oynasi** bilan (2026-08-04): summa, taqsimot
  usuli va — qarzdan oshsa — avansga qoladigan qism aytiladi. Summa maydoni
  ostida izoh yo'q; matn aynan qaror lahzasida ko'rsatiladi
- Xato to'lov → **`void`** (sabab majburiy): allokatsiyalar qaytariladi,
  hisobot qarzi qayta ochiladi, `audit_log`ga yoziladi (P5)
- Barcha to'lovlar Excel'ga eksport qilinadi (sana oralig'i bo'yicha)

> ✅ **Tasdiqlangan model ([A-04](../05-delivery/02-open-questions.md)):**
> usta **har ish uchun** to'lov oladi, narxni **o'zi taklif qiladi**, admin
> **kelishib kamaytirishi** mumkin.

> ❌ **Bonus / jarima YO'Q** (2026-08-03 qarori). Eski `payouts` modelida bu
> maydonlar bor edi, lekin qarz daftarida qarz har doim **aniq hisobotga**
> bog'lanadi — xodimga "shunchaki" pul qo'shish yoki ayirish uchun joy yo'q.
> Kerak bo'lsa kelajakda alohida `adjustment` yozuvi sifatida qo'shiladi.

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
- Mashina yoshi bo'yicha
- 1 km ga xarajat — **faqat `vehicles.odometer_km`** ma'lum bo'lsa (Fleet
  sinxronidan). Hisobotda probeg so'ralmaydi (ADR-0018)
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

Faqat **eksport** — import yo'q. Fayl nomida sana oralig'i turadi
(`<boshi>_<oxiri>`, Toshkent vaqti); `periods` yo'q (ADR-0015). Excel Telegram
orqali hujjat bo'lib keladi.

| Fayl | Mazmuni | Kim uchun |
|---|---|---|
| `tamirlar_<from>_<to>.xlsx` | Hisobotlar + ish qatorlari (ikki varaq) | Admin |
| `qarzlar_<sana>.xlsx` | Qarzdorlar + **avans** + to'lovlar tarixi (uch varaq) | Buxgalteriya |
| `kelishuv_<from>_<to>.xlsx` | Narx kelishuvi tejamkorligi + xodimlar kesimi | Direktor |

### `tamirlar_*.xlsx` — ustunlar

**1-varaq «Ta'mirlar»** — bitta hisobot = bitta qator:

`Raqam · Holat · Xodim · Mashina · Keldi · Ketdi · Downtime (soat) ·
Tasdiqlangan ish haqi · Qismlar · Jami · Qarz asosi · To'langan · Qolgan qarz ·
Avtomatik tasdiq · Yuborilgan`

**2-varaq «Ish qatorlari»** — bitta ish/qism = bitta qator:

`Hisobot · Mashina · Xodim · Tur · Nomi · Soni · Tasdiqlangan · O'z hisobidan`

> 🚫 **Ataylab yo'q ustunlar** (2026-08-05, egasining qarori — ADR-0019 ruhi:
> hisobot mavzusi *bajarilgan ish va qarz*, savdolashish emas):
>
> | Varaq | Olib tashlangan |
> |---|---|
> | Ta'mirlar | «So'ralgan ish haqi», «Kamaytirildi» |
> | Ish qatorlari | «So'ralgan», «Kamaytirish sababi», «Rozilik» |
>
> Bu ma'lumot bazada qoladi (`proposed_amount`, `price_change_reason`,
> `mechanic_accept_mode`) va `audit_log` / `approvals` da to'liq ko'rinadi —
> faqat kundalik Excel'dan chiqarildi. Kelishuv raqamlari kerak bo'lsa —
> `kelishuv_*.xlsx` bor.
>
> «Mashina» ustuni **qo'shildi** (2-varaq): mashina kesimida filtrlash uchun.

### `qarzlar_*.xlsx` — uchta varaq

| Varaq | Mazmuni |
|---|---|
| **Qarzlar** | `Xodim · Ishlar soni · Qarz` + JAMI. **Hozirgi holat** — sana oralig'iga bog'liq emas (qarz yopilmaguncha ochiq turadi) |
| **Avans** ⭐ | `Xodim · Avans` + JAMI — ishlatilmagan qoldiq (P7) |
| **To'lovlar** | To'lovlar tarixi; oraliq berilgan bo'lsa faqat shu oraliqdagilar |

⚠️ **Avans nega alohida varaqda:** `debt_summary` ro'yxatiga avansi bor, lekin
qarzi yo'q xodim ham tushadi — u yerda `count = 0`, `debt = 0`. Bunday qator
qarzdorlar jadvalida «0 ish · 0 qarz» bo'lib turardi va *«kimga qancha
qarzmiz?»* degan savolni loyqalatardi. Mini App'da bu 2026-08-04 da alohida
tab bilan hal qilingan edi — eksport ham shu qarorga keltirildi (2026-08-05).

Ya'ni **«Qarzlar» varag'ida faqat haqiqiy qarzdorlar** (`count > 0`) turadi.

Ustunlar tarkibi `tests/test_export.py` da qotirilgan — eksport hech qayerda
ko'rinmaydi, xato faqat buxgalter faylni ochganda bilinadi.

## 7. Kelajakdagi kengaytmalar (v4+)

| Imkoniyat | Nima beradi |
|---|---|
| **1 km ga xarajat** (`vehicles.odometer_km`, Fleet sinxronidan) | Haqiqiy solishtirish mezoni |
| **Byudjet vs fakt** | Oylik ta'mir byudjeti belgilanadi, oshib ketish signali |
| **Prognoz** | "Shu tendensiya bilan yil oxirida X so'm" |
| **Zaryad xarajati** | EV uchun ikkinchi eng katta xarajat moddasi |
| **Mashina TCO** | Sotib olish + ta'mir + zaryad + sug'urta − qoldiq qiymat |
| **Haydovchi reytingi** | Ta'mir chastotasi, shikast, downtime bo'yicha |

---

**Keyingi:** [05-delivery/01-roadmap.md](../05-delivery/01-roadmap.md)
