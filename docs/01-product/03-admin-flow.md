# 03. Admin oqimi

Admin — tizimning **yagona nazorat nuqtasi**. Ko'p bosqichli tasdiqlash yo'q,
direktorga ko'tarish yo'q: hisobotni admin ko'radi, narxni admin kelishadi,
oxirgi so'z adminda. Buxgalter faqat ko'radi, eksport qiladi va oyni yopadi.

## 1. Asosiy ekran (dashboard)

```
┌───────────────────────────────────────┐
│  📊 NovaCore — Admin      Iyul 2026 ▾ │
├───────────────────────────────────────┤
│  ⏳ Tasdiq kutmoqda        7   →      │
│  💬 Kelishuvda             3   →      │
│  🔧 Hozir ustaxonada       4 mashina  │
├───────────────────────────────────────┤
│  Bu oy                                │
│  Ta'mirlar soni:              84      │
│  Ish haqi (so'ralgan): 11 200 000     │
│  Ish haqi (tasdiqlangan):9 350 000    │
│  💰 Kelishuv tejamkorligi: 1 850 000  │
│  Ehtiyot qism:       21 400 000 so'm  │
│  JAMI:               30 750 000 so'm  │
│  1 mashinaga o'rtacha:  205 000 so'm  │
│  ▲ o'tgan oyga nisbatan +12%          │
├───────────────────────────────────────┤
│  ⚠️ E'tibor talab qiladi              │
│  • 01 A 123 BC — bu oy 3-ta'mir       │
│  • Usta Sobirov — narxi 25% kamaytiril│
│  • 01 B 456 CD — 4 kundan beri ustaxo.│
└───────────────────────────────────────┘
```

## 2. Hisobotni ko'rib chiqish va narx kelishuvi

Bu — adminning **eng ko'p vaqt oladigan** ekrani. Kuniga 3–5 hisobot keladi,
shuning uchun u tez va ma'lumotga boy bo'lishi kerak.

```
┌───────────────────────────────────────┐
│  Hisobot #WO-1247 · Usta: Karimov B.  │
│  🚩 narx tarixiy o'rtachadan yuqori    │
├───────────────────────────────────────┤
│  Mashina:  01 A 123 BC · BYD Chazor   │
│  Keldi:    29.07 09:14                │
│  Ketdi:    29.07 12:40 (3 s 26 daq)   │
│  Probeg:   48 250 km                  │
├───────────────────────────────────────┤
│  📷 OLDIN        📷 MUAMMO   📷 KEYIN  │
│  [ ▣ ][ ▣ ]      [ ▣ ][ ▣ ]   [ ▣ ]   │
├───────────────────────────────────────┤
│  💰 ISH HAQI — kelishuv                │
│  Old tormoz kolodka almashtirish      │
│                                        │
│  Usta so'radi:          250 000 so'm  │
│                                        │
│  📊 Tarix (oxirgi 8 marta)            │
│     o'rtacha   175 000                 │
│     eng past   150 000 (Yusupov 12.06)│
│     eng yuqori 210 000 (Karimov 03.07)│
│  👤 Karimov o'rtachasi: 205 000 (+17%)│
│  📉 Narxi 42% hollarda kamaytirilgan  │
│                                        │
│  [ ✅ 250 000 tasdiqlash ]             │
│  [ ✏️ Boshqa summa: _______ ]          │
│     [175 000] [200 000] [210 000]     │
├───────────────────────────────────────┤
│  📦 QISMLAR (ta'minotchi kiritgan)     │
│  • Tormoz kolodka ×1  420 000 📷chek  │
│    Avto-Nur · original · kafolat 6 oy │
│    ⓘ 90 kunlik o'rtacha: 435 000 ✅   │
├───────────────────────────────────────┤
│  Usta izohi: "Kolodka to'liq yeyilgan,│
│  disk normal, boltlar zanglagan edi"  │
├───────────────────────────────────────┤
│  [ ✅ Tasdiqlash ]                     │
│  [ ↩️ Qaytarish (sabab bilan) ]        │
│  [ ❌ Rad etish ]                      │
└───────────────────────────────────────┘
```

Prinsiplar:
- **Narx kelishuvi — ekranning markazi.** Admin har safar noldan savdolashmasligi
  uchun tarixiy statistika shu yerda
- **Tez tanlov tugmalari** (`[175 000]`) — admin summani qo'lda yozmaydi
- **Foto to'liq ekranda ochiladi**, yonma-yon solishtiriladi (oldin ↔ keyin)
- **Ommaviy tasdiqlash** — narxi tarixiy o'rtachaga mos hisobotlarni belgilab
  birdan tasdiqlash

To'liq mexanizm: [04-flows/04-price-negotiation.md](../04-flows/04-price-negotiation.md)

### Narxni kamaytirish

```
[ ✏️ Boshqa summa: 180 000 ]
        ↓  sabab majburiy
Hisobot → PRICE_NEGOTIATION, ustaga bildirishnoma
        ↓
Usta ✅ Roziman   → APPROVED (180 000)
Usta ❌ Rozi emas → admin qayta ko'radi → yakuniy qaror adminda
48 soat javobsiz  → avtomatik rozilik
```

⚠️ Admin narxni **oshira olmaydi** (R2). Usta xato kam so'ragan bo'lsa —
hisobot `REOPENED` qilinadi va usta o'zi tuzatadi.

### Qaytarish vs Rad etish

| Amal | Qachon | Natija |
|---|---|---|
| **↩️ Qaytarish** | Ma'lumot to'liq emas / foto yomon | Ustaga qaytadi, tahrirlaydi, qayta yuboradi. Tarix saqlanadi |
| **❌ Rad etish** | Ish umuman bajarilmagan / soxta | Hisobot yopiladi, to'lovga kirmaydi. Sabab majburiy |

## 3. ⭐ Rol yaratish (admin uchun asosiy vosita)

NovaCore'da rol — bu **nom** ([rol modeli](01-roles-and-permissions.md)). Admin
istalgan paytda yangisini yaratadi:

```
┌──────────────────────────────────────────┐
│  Yangi rol                               │
├──────────────────────────────────────────┤
│  Nomi (uz):  Elektrik                    │
│  Nomi (ru):  Электрик                    │
│  Ikonka:     ⚡                           │
│                                           │
│  Turi:  (•) Hisobot beruvchi              │
│         ( ) Admin                         │
│         ( ) Buxgalter                     │
│                                           │
│  Shablonlar:                              │
│   ☑ Ta'mir hisoboti                       │
│   ☐ Ehtiyot qism xaridi                   │
│   ☑ Elektr ishlari  [+ Yangi shablon]     │
├──────────────────────────────────────────┤
│  [ Saqlash ]                              │
└──────────────────────────────────────────┘
```

Bundan keyin xodimga shu rol beriladi va u Mini App'da **"⚡ Elektrik"** menyusini
ko'radi. Kod yozilmaydi, deploy qilinmaydi.

Shablon konstruktori: [04-roles-and-templates.md](04-roles-and-templates.md)

## 4. Spravochniklar

| Spravochnik | Nima saqlanadi |
|---|---|
| **Mashinalar** | Raqam, VIN, marka, model, yil, tarif, status, batareya |
| **Xodimlar** | FIO, telefon, rol, ustaxona (ixtiyoriy), ishga kirgan sana, status |
| **Rollar** | Nom (uz/ru), turi, shablonlar |
| **Shablonlar** | Maydonlar, kim to'ldiradi |
| **Ish turlari** | Kod, nom, kategoriya, **tayanch narx** (faqat admin ko'radi) |
| **Ehtiyot qism katalogi** | Nom, artikul, oxirgi narx, yetkazib beruvchi |
| **Nosozlik kategoriyalari** | Kod, nom, ikonka |

> **Mashinalar** Yandex Fleet API'dan sinxronlanadi —
> [Fleet integratsiyasi](../03-integrations/01-yandex-fleet-api.md).

## 5. Hisobotlar va eksport

| Hisobot | Kesim | Format |
|---|---|---|
| **Narx kelishuvi tejamkorligi** ⭐ | oy × xodim | jadval + diagramma |
| Mashina bo'yicha xarajat | mashina × oy | jadval + Excel |
| Xodim samaradorligi (narx xulqi bilan) | xodim × oy | jadval + Excel |
| Downtime | mashina × sabab | jadval |
| Ehtiyot qism xarajati | qism × yetkazib beruvchi | Excel |
| To'lov varaqasi | xodim × davr | Excel (buxgalteriyaga) |

Import **kerak emas** — faqat eksport.
Batafsil: [04-flows/03-payroll-and-reports.md](../04-flows/03-payroll-and-reports.md)

## 6. Oy yopilishi

```
1. Admin yoki buxgalter "Oyni yopish" tugmasini bosadi
        ↓
2. Tizim tekshiradi:
   ❌ 3 ta hisobot tasdiqlanmagan
   ❌ 2 ta hisobot narx kelishuvida (usta javob bermagan)
   ⚠️ 1 ta qoralama 10 kundan beri turibdi
        ↓
3. Har biri: [Hal qilish] yoki [Keyingi oyga ko'chirish]
        ↓
4. Davr CLOSED:
   • Yozuvlar qulflanadi
   • To'lov varaqalari generatsiya qilinadi
   • Excel paket eksport qilinadi
        ↓
5. Qayta ochish — faqat admin, sabab bilan, audit log'ga yozilib
```

## 7. Admin ham hisobot yozadi — avtomatik tasdiqlanadi

Admin `reporter` imkoniyatlariga ham ega: u ham mashina raqamini kiritib, foto
qo'yib, narx yozib hisobot yubora oladi.

✅ **Qaror ([A-25](../05-delivery/02-open-questions.md)):** admin o'z-o'zini
tasdiqlamaydi — uning hisoboti **avtomatik tasdiqlanadi**. Tasdiqlovchi
kerak emas.

```
Admin hisobot yuboradi
        ↓
DRAFT ──────────────────► APPROVED       (tasdiqlash bosqichisiz)
        ↓
approved_amount = proposed_amount        (narx kelishuvi ham yo'q)
auto_approved = true
approvals(decision='auto_approved', actor_id=NULL)
```

**Nima uchun narx kelishuvi ham yo'q:** kelishadigan ikkinchi tomon mavjud emas —
admin o'zi bilan savdolashmaydi. Shuning uchun `approved = proposed`.

### Shaffoflik chorasi

Bu — nazorat halqasidagi yagona ochiq joy, shuning uchun u **yashirilmaydi**:

| Chora | Qayerda ko'rinadi |
|---|---|
| `auto_approved` belgisi | Hisobot kartochkasida |
| "Avtomatik tasdiqlangan: N ta, X so'm" | Oylik hisobot va oy yopish ekrani |
| `approvals` yozuvi (`actor_id = NULL`) | Audit log |
| Buxgalter hammasini ko'radi | Oy yopilishida |

Buxgalter — de-fakto kuzatuvchi: u barcha hisobotlarni ko'radi va oyni yopadi.

---

**Keyingi:** [04. Rollar va shablonlar](04-roles-and-templates.md)
