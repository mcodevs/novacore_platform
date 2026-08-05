# 03. Admin oqimi

Admin — tizimning **yagona nazorat nuqtasi**. Ko'p bosqichli tasdiqlash yo'q,
direktorga ko'tarish yo'q: hisobotni admin ko'radi, narxni admin kelishadi.
Buxgalter ko'radi, eksport qiladi va to'lovlarni qayd etadi.

⚠️ **«Yagona nazorat nuqtasi» ≠ «oxirgi so'z».** Narx nizosida adminda yakuniy
qaror **yo'q** ([ADR-0023](../05-delivery/03-decisions.md#adr-0023--nizoda-yakuniy-qaror-yoq)):
u yo yangi narx taklif qiladi, yo ustaning narxiga rozi bo'ladi.

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
Usta ❌ Rozi emas → admin qayta ko'radi. Ikkita yo'l (N3a):
                    ✏️ Yangi narx        → sikl qaytadan
                    ✅ Usta narxiga rozi → APPROVED (250 000)
48 soat javobsiz  → avtomatik rozilik
```

⚠️ Nizoda **«Tasdiqlash» ham, «Rad etish» ham yo'q** — server ham qabul
qilmaydi. Ish bajarilgan, gap faqat summada.

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
| Qarzlar va to'lovlar | xodim × sana oralig'i | Excel (buxgalteriyaga) |

Import **kerak emas** — faqat eksport.
Batafsil: [04-flows/03-payroll-and-reports.md](../04-flows/03-payroll-and-reports.md)

## 6. Qarz va to'lov

⚠️ **Oy yopilishi yo'q.** Davr (`periods`) va to'lov varaqasi (`payouts`)
tushunchalari olib tashlangan
([ADR-0015](../05-delivery/03-decisions.md#adr-0015--qarz-daftari-oy-yopish-orniga-hisobot-boyicha-tolov-)).
Moliyaviy hisob kalendar oyga emas, **hisobotga** bog'langan: har bir
tasdiqlangan hisobot — muallifga qarz, u to'langunicha ochiq turadi.

To'lovni **buxgalter ham, admin ham** qayd eta oladi — ekran bir xil:

```
Hisobot APPROVED
        ↓
Qarz = payable_amount − paid_amount        ← 0 dan katta bo'lsa, qarzlar ro'yxatida
        ↓
[ To'langanlar ]  [ Qarzlar ]
        ↓  Qarzlar → qarzdor xodim → uning to'lanmagan hisobotlari
        ↓
Uch usul:
   ☑ belgilab       — tanlangan hisobotlarning qolgan qarzi to'liq yopiladi
   💰 summa kiritib — FIFO: eng eski qarzdan, oxirgisi qisman yopiladi
   📄 kartochkadan  — bitta hisobot, to'liq yoki qisman
        ↓
paid_amount == payable_amount  →  status PAID
```

| Qoida | Tafsilot |
|---|---|
| Faqat **`APPROVED`** hisobot to'lanadi | Kelishuvda turgan hisobot qarz emas |
| `paid_amount ≤ payable_amount` | Ortiqcha to'lov qabul qilinmaydi (DB `CHECK`) |
| To'lov **o'zgarmas** | Xato bo'lsa — `void` (sabab majburiy): qarz qayta ochiladi, `audit_log`ga yoziladi |
| Platforma pul **o'tkazmaydi** | Faqat **qayd etadi** |
| Oylik kesim kerak bo'lsa | `submitted_at` sanasi bo'yicha filtr — alohida davr jadvali yo'q |

⭐ Ustaning qarzi ish haqidan tashqari **o'z hisobidan olgan qismlar**ni ham
o'z ichiga oladi (chek fotosi majburiy) —
[ADR-0016](../05-delivery/03-decisions.md#adr-0016--usta-oz-hisobidan-olgan-qism-ham-qarzga-kiradi).

To'liq mexanizm: [04-flows/03-payroll-and-reports.md](../04-flows/03-payroll-and-reports.md)

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
| "Avtomatik tasdiqlangan: N ta, X so'm" | Oylik hisobot va buxgalterning qarzlar ekrani |
| `approvals` yozuvi (`actor_id = NULL`) | Audit log |
| Buxgalter hammasini ko'radi | To'lovni qayd etishda |

Buxgalter — de-fakto kuzatuvchi: u barcha hisobotlarni ko'radi va to'lovni
o'zi qayd etadi.

## 8. E'lon (broadcast)

Adminning barcha xodimlarga bir vaqtda xabar yetkazish vositasi: «ertaga ombor
yopiq», «yangi qism narxi», «shanba ish kuni». Ilgari bu Telegram guruhida
qilinardi — endi platformada, **iz bilan**.

**Amal Mini App'da, yetkazish bot orqali.** Admin matnni Mini App'da yozadi;
xabar har bir xodimga **shaxsiy** chatda keladi. Botda e'lon yozadigan buyruq
**yo'q** ([bot doirasi](../03-integrations/02-telegram-bot-miniapp.md#1-vazifalarni-bolish)).

```
┌───────────────────────────────────────┐
│  📢 E'lon                              │
├───────────────────────────────────────┤
│  ┌───────────────────────────────────┐│
│  │ Ertaga ombor yopiq. Qism          ││
│  │ kerak bo'lsa bugun oling.         ││
│  │                                   ││
│  └───────────────────────────────────┘│
│  142 / 3500 belgi                     │
│                                        │
│  Qabul qiladi: 24 xodim               │
│  ⚠️ Yuborilgan e'lon qaytarilmaydi     │
│  [ 📤 Yuborish ]                       │
├───────────────────────────────────────┤
│  Tarix                                 │
│  02.08 10:14 · 24 ta                  │
│  «Ertaga ombor yopiq…»                │
│  ✅ 24  ⏳ 0  ❌ 0                      │
└───────────────────────────────────────┘
```

### Kimga boradi

| Shart | Sabab |
|---|---|
| `status = active` | Bloklangan/ishdan ketgan xodim xabar olmaydi |
| `deleted_at IS NULL` | O'chirilgan yozuv |
| `tg_user_id IS NOT NULL` | Botga hali bog'lanmagan xodimga yuborib bo'lmaydi |

Rol farqi **yo'q** — e'lon hammaga: usta ham, ta'minotchi ham, buxgalter ham.

### Qoidalar

| Qoida | Tafsilot |
|---|---|
| Faqat **admin** yuboradi | `role.kind = 'admin'`, serverda tekshiriladi |
| Matn — **3500 belgigacha** | Telegram xabar chegarasidan zaxira bilan pastda |
| Bo'sh matn qabul qilinmaydi | Faqat probel — xato |
| **Qaytarib bo'lmaydi** | Yuborilgach o'chirish/tahrirlash yo'q — shuning uchun tasdiq oynasi |
| Har e'lon `audit_log`da | `broadcast_sent` — kim, qachon, necha kishiga (R9) |
| E'lon **hech qachon o'chirilmaydi** | Tarix — soft delete ham yo'q |

### Yetkazish hisobi

E'lon darhol emas, **navbat orqali** yetadi (`notifications` outbox). Tarixda
har e'lon uchun uchta raqam ko'rinadi:

| Belgi | Ma'nosi |
|---|---|
| ✅ **Yetkazildi** | Bot xabarni yubordi |
| ⏳ **Navbatda** | Hali yuborilmagan yoki qayta urinishda |
| ❌ **Yetmadi** | Xodim botni bloklagan yoki urinishlar tugadi |

~150 xodimga to'liq yetkazish **~8 sekund** oladi (bitta fon tiki ichida), lekin
oddiy bildirishnomalar e'londan **oldin** ketadi — narx kelishuvi e'lon ortida
qolib ketmasin. Sabab va raqamlar:
[bot bildirishnomalari](../03-integrations/02-telegram-bot-miniapp.md#elon-broadcast-yetkazish).

**Bir xil matn ikki marta:** e'lon qaytarib bo'lmaydigan amal, shuning uchun
bitta admin 60 sekund ichida aynan bir xil matnni qayta yuborsa yangi e'lon
yaratilmaydi — mavjudi qaytariladi. Bu zaif internetdagi takroriy so'rovdan
himoya (klient javobni ololmay so'rovni takrorlashi mumkin).

---

**Keyingi:** [04. Rollar va shablonlar](04-roles-and-templates.md)
