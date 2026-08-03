# 02. Firibgarlikka qarshi nazorat

> Loyihaning asosiy maqsadi — *"hisobotni yaxshilash"*. Ochiq aytilsa, bu
> **pul oqimini nazorat qilish** degani. Shuning uchun anti-fraud —
> qo'shimcha imkoniyat emas, **mahsulotning o'zagi**.

## 1. Falsafa

| ✅ To'g'ri yondashuv | ❌ Noto'g'ri yondashuv |
|---|---|
| Halol ishlashni **oson** qilish | Hamma ustani gumondor deb hisoblash |
| Shubhali holatni **ko'rinadigan** qilish | Avtomatik jazolash |
| Adminga **qaror uchun ma'lumot** berish | Tizim o'zi hukm chiqarishi |
| Bayroq — **savol**, ayblov emas | Bayroq — ayb |

> Agar tizim ustalarni dushman qilib qo'ysa, ular undan chetlab o'tadi va
> loyiha o'ladi. Maqsad — **shaffoflik**, jazo emas.

Muhim jihat: bayroqlar **bloklamaydi** (kritiklardan tashqari) — ular admin
e'tiborini yo'naltiradi. 100 ta hisobotning 95 tasi toza bo'lsa, admin
5 tasiga vaqt sarflaydi.

## 2. Qaysi teshiklarni yopamiz

| # | Firibgarlik usuli | Qanday aniqlanadi |
|---|---|---|
| F1 | Bo'lmagan ishni yozish | Foto (oldin/muammo/keyin), server vaqti, admin ko'rigi |
| F2 | **Narxni shishirish** | ⭐ **Narx kelishuvi** — admin har narxni ko'rib chiqadi va tarixiy statistikaga tayanib kamaytiradi |
| F3 | Eski/boshqa mashinadan foto qo'yish | pHash, sha256, EXIF sanasi |
| F4 | Bir ishni ikki marta yozish | Dublikat aniqlash (mashina + kategoriya + vaqt) |
| F5 | **Qismni qimmatroq ko'rsatish** | ⭐ **Tuzilmaviy yechim:** kompaniya olgan qismga usta narx **umuman kirita olmaydi** — ta'minotchi kiritadi |
| F5a | **Kompaniya olgan qismga «o'z hisobimdan» belgisini qo'yish** | ⚠️ ADR-0016 ochgan teshik. **Chek fotosi majburiy** + admin ko'rigi. Yagona to'siq — shuning uchun admin buni alohida tekshiradi |
| F6 | Qismni almashtirmasdan yozish | "Keyin" fotosi, kafolat, rework kuzatuvi |
| F7 | Admin bilan til biriktirish | **Admin narxni oshira olmaydi (R2)**, audit log, buxgalter ko'rinishi |
| F8 | O'z hisobotini o'zi tasdiqlash | `approver ≠ author` (R1). ⚠️ **Admin hisoboti avtomatik tasdiqlanadi** — bu yerda nazorat yo'q, faqat shaffoflik (`auto_approved` belgisi + oylik hisobotda alohida satr) |
| F9 | To'langan hisobotni o'zgartirish | To'langan hisobot qayta ochilmaydi, audit log |
| F10 | Kelishilgan tashqi servis | Kontragent, chek, narx solishtirish |
| F11 | Ta'minotchi qism narxini shishirishi | Chek fotosi, 90 kunlik narx tarixi, yetkazib beruvchi diversifikatsiyasi |

> ⭐ **NovaCore modelida ikkita eng katta teshik tuzilmaviy hal qilingan:**
> narxni admin kelishadi (F2) va qism narxini usta kiritmaydi (F5). Bu
> algoritmik bayroqlardan ko'ra kuchliroq — chunki imkoniyatning o'zi yo'q.
>
> ⚠️ **Istisno — F5a:** usta qismni o'z hisobidan olsa, narx kirita oladi
> ([ADR-0016](../05-delivery/03-decisions.md#adr-0016--usta-oz-hisobidan-olgan-qism-ham-qarzga-kiradi)).
> Bu yerda tuzilmaviy himoya yo'q — faqat **chek fotosi** va admin ko'rigi.

## 3. Bayroqlar katalogi

| Kod | Nomi | Qachon | Darajasi |
|---|---|---|---|
| `price_above_history` | Narx tarixiy o'rtachadan yuqori | So'ralgan narx `avg_approved`dan > 30% | 🟡 warning |
| `price_far_above_history` | Katta chetlanish | > 100% | 🔴 critical |
| `mechanic_high_reduction` | Usta doim ko'p so'raydi | Ustaning `avg_reduction_pct` > 25% | 🟡 warning |
| `price_dispute_repeat` | Takroriy nizo | Usta oyiga > 3 marta kelishmagan | 🟡 warning |
| `auto_accepted_price` | Sukut bilan qabul | 48 soat javobsiz o'tgan | 🔵 info |
| `duplicate_photo` | Takroriy foto | pHash masofa ≤ 8 | 🔴 critical |
| `identical_file` | Aynan bir xil fayl | sha256 mos | 🔴 critical |
| `photo_not_fresh` | Eski foto | EXIF sanasi > 24 soat oldin | 🟡 warning |
| `photo_no_exif` | EXIF yo'q | Galereyadan olingan ehtimoli | 🔵 info |
| `rework` | Qayta ta'mir | Shu mashina + kategoriya, 30 kun ichida | 🟡 warning |
| `rework_warranty` | Kafolat ichida qayta | Kafolat muddati ichida | 🔴 critical |
| `frequent_repair` | Tez-tez ta'mir | Bir mashina oyiga > 3 marta | 🟡 warning |
| `high_amount` | Katta summa | Chegaradan yuqori | 🟡 warning |
| `geo_mismatch` | Joylashuv mos emas | Ustaxona koordinatasidan > 2 km | 🟡 warning |
| `geo_missing` | Joylashuv yo'q | Geo ruxsati berilmagan | 🔵 info |
| `short_downtime` | Juda qisqa ta'mir | `left_at − arrived_at` normativ vaqtdan < 30% | 🟡 warning |
| `no_receipt` | Chek yo'q | Qism > 100 000 so'm, chek yo'q | 🟡 warning |
| `part_price_jump` | Qism narxi sakradi | O'rtacha 90 kunlik narxdan > 40% | 🟡 warning |
| `mechanic_outlier` | Usta anomaliyasi | Ustaning o'rtacha narxi boshqalardan > 40% yuqori | 🟡 warning |
| `late_submit` | Kech yuborilgan | Ish tugagandan > 3 kun keyin | 🔵 info |
| `weekend_night` | Norasmiy vaqt | Tungi/dam olish kunidagi ish | 🔵 info |

## 4. Foto asosidagi nazorat — batafsil

### Nima uchun foto eng muhim dalil

Foto — yagona narsa, uni **soxtalashtirish qiyin va tekshirish oson**.
Shuning uchun foto talablari qattiq:

| Talab | Sabab |
|---|---|
| Mashina umumiy ko'rinishi **raqam bilan** | Bu ayni o'sha mashina ekanligi |
| Muammo fotosi (yaqindan) | Nosozlik haqiqatan bor |
| "Keyin" fotosi **shu rakursda** | Solishtirish mumkin |
| Chek/nakladnoy fotosi | Qism narxi haqiqiy |

### pHash dublikat qidiruvi

```
Yangi foto
    ↓
phash (64-bit perceptual hash)
    ↓
Oxirgi 90 kundagi barcha fotolar bilan Hamming masofasi
    ↓
≤ 4   → 🔴 deyarli aynan bir xil
5–8   → 🔴 juda o'xshash (kesilgan/siqilgan bo'lishi mumkin)
9–12  → 🟡 o'xshash (bir xil model detali bo'lishi mumkin)
> 12  → toza
```

**Muhim nozik jihat:** bir xil model mashinalarning bir xil detali tabiiy
o'xshash bo'ladi. Shuning uchun:
- Chegaralar **sozlanadigan** bo'lishi kerak
- `false_positive` statistikasi yig'iladi va chegaralar shunga qarab sozlanadi
- Bayroq **kontekst bilan** ko'rsatiladi: "shu foto #WO-1198 da ham ishlatilgan"
  + ikkala foto yonma-yon

### EXIF signallari

| Signal | Nima anglatadi |
|---|---|
| EXIF yo'q | Skrinshot, tarmoqdan olingan, yoki qayta ishlangan |
| EXIF sanasi > 24 soat | Eski foto |
| EXIF sanasi kelajakda | Telefon vaqti o'zgartirilgan |
| EXIF GPS ustaxonadan uzoq | Boshqa joyda olingan |
| Qurilma modeli har safar boshqa | Shubhali |

⚠️ EXIF **ishonchli dalil emas** — uni o'zgartirish mumkin. Lekin firibgarlikning
90%i shunchalik murakkab bo'lmaydi. EXIF — arzon va foydali filtr.

## 5. Narx nazorati — kelishuv orqali

NovaCore'da narx nazorati **algoritm emas, jarayon**: usta o'z narxini qo'yadi,
admin uni ko'rib chiqadi va kamaytirishi mumkin. Bayroqlar bu jarayonga
**ma'lumot beradi**, uning o'rnini bosmaydi.

```
Usta 250 000 so'm so'radi
        ↓
Tizim tarixni ko'radi: bu ish oxirgi 8 marta o'rtacha 175 000 ga tasdiqlangan
        ↓
+43% → 🚩 price_above_history bayrog'i
        ↓
Admin ekranida: so'ralgan narx + tarix + ustaning o'z statistikasi
        ↓
Admin: "180 000" + sabab → usta rozi bo'ladi yoki bahslashadi
```

To'liq mexanizm: [04-price-negotiation.md](04-price-negotiation.md)

**Tayanch narxnoma (`reference_price`) roli:**

| Tavsiya | Sabab |
|---|---|
| Tayanch narx **ustaga ko'rsatilmaydi** | Aks holda barcha narxlar tayanchga yopishadi, kelishuv ma'nosini yo'qotadi |
| 30–60 ta eng ko'p ishdan boshlash | Hammasini qamrash shart emas |
| **Tarixiy statistika tayanchdan muhimroq** | Real tasdiqlangan narxlar — eng kuchli dalil |
| Har chorakda qayta ko'rib chiqish | Narxlar o'zgaradi |

**Ustaning narx xulqi — asosiy signal:**

| Ko'rsatkich | Talqin |
|---|---|
| `avg_reduction_pct` < 10% | Halol narx qo'yadi ✅ |
| `avg_reduction_pct` 10–25% | Normal savdolashuv |
| `avg_reduction_pct` > 25% | Har safar "havoga" so'raydi 🟡 — suhbat kerak |
| `dispute_rate` > 20% | Kelishuvga qiyin 🟡 |

> ⚠️ Diqqat: bu raqamlar **suhbat uchun asos**, avtomatik jazo uchun emas.
> Usta murakkabroq ishlarni olayotgan bo'lishi ham mumkin.

## 6. Ikki tomonlama tasdiq — bu tizimda YO'Q

Haydovchilar tizimda rolga ega emas
([ADR-0013](../05-delivery/03-decisions.md)), shuning uchun "usta dedi —
haydovchi tasdiqladi" mexanizmi ishlamaydi.

**Buning o'rniga nazorat uch narsaga tayanadi:**

| Nazorat | Kuchi |
|---|---|
| **Narx kelishuvi** — admin har summani ko'radi va tarixga solishtiradi | 🟢 Kuchli |
| **Foto** — oldin / muammo / keyin, kamerada olingan | 🟢 Kuchli |
| **Server vaqtlari** — `arrived_at` / `left_at` tugma bosilgan lahzada | 🟡 O'rtacha |

⚠️ **Ochiq zaiflik:** mashinaning kelgani/ketganini ustaning **o'zi** belgilaydi.
U ta'mir qilmasdan ikkala tugmani bosishi mumkin. Buni faqat foto ushlaydi
(oldin/keyin rasmi haqiqiy bo'lishi kerak). Shuning uchun **foto talablari
qattiq** va pHash dublikat tekshiruvi Faza 3'da muhim bo'ladi.

Agar keyinchalik bu zaiflik real muammoga aylansa — haydovchini bitta tugma
bilan qo'shish ([o'chirilgan haydovchi oqimi](../05-delivery/03-decisions.md#adr-0013--haydovchi-tizimda-rolga-ega-emas))
eng arzon yechim bo'ladi.

## 7. Statistik anomaliyalar (v3)

Bir hisobotga emas, **naqshga** qaraydigan tekshiruvlar:

| Tekshiruv | Nima ko'rsatadi |
|---|---|
| Usta × o'rtacha chek | Kimdir doim qimmatroq yozadi |
| Usta × rework % | Sifatsiz ish yoki soxta ta'mir |
| **Usta × `avg_reduction_pct`** | Doimiy "havoga" so'rash |
| **Admin × kamaytirish %** | Bir admin umuman kamaytirmasa — nima uchun? |
| Ta'minotchi × qism narxi tendensiyasi | Yetkazib beruvchi bilan kelishuv |
| Mashina × ta'mir chastotasi | Yo bu mashina yomon, yo hisobotlar soxta |
| Haydovchi × zayavka chastotasi | Ehtiyotsiz haydash yoki noto'g'ri foydalanish |
| Qism × narx tarixi | Yetkazib beruvchi qimmatlashtirmoqda |
| Kun × hisobotlar soni | Oy oxirida "to'planib qolish" |

**Oyiga bir marta** avtomatik anomaliya hisoboti direktorga yuboriladi.

## 8. Nima QILMAYMIZ

Halol bo'lish kerak — bu tizim hamma narsani ushlamaydi:

| Ushlanmaydi | Nima uchun |
|---|---|
| **Adminning o'z hisoboti** | Avtomatik tasdiqlanadi — tekshiruvchi yo'q (A-25 qarori). Faqat `auto_approved` belgisi va oylik hisobotdagi alohida satr orqali **ko'rinadi** |
| Yaxshi tayyorlangan til biriktirish | Usta + admin kelishsa |
| Qismning past sifatlisini qo'yish | Foto orqali bilinmaydi |
| Ish sifatining pastligi | Faqat rework orqali, keyinroq |
| Chekni soxtalashtirish | Yetkazib beruvchi bilan tekshirilmaydi |

Bularga qarshi — **tashkiliy choralar**: ustalarni almashtirib turish
(rotatsiya), tasodifiy tekshiruv (admin o'zi borib ko'radi), yetkazib
beruvchilarni davriy qayta ko'rib chiqish.

> Platforma **100% firibgarlikni to'xtata olmaydi**, lekin uni:
> qiyinlashtiradi, qimmatlashtiradi, va **ko'rinadigan** qiladi.
> Amalda bu 80% samara beradi.

## 9. Bosqichma-bosqich joriy etish

⚠️ Barcha bayroqlarni birdan yoqish — noto'g'ri. Odamlar cho'chiydi.

| Faza | Nima yoqiladi |
|---|---|
| **v1** | Majburiy foto + **narx kelishuvi** + tarixiy narx statistikasi (bayroqsiz) |
| **v2** | Bayroqlar yoqiladi (pHash, EXIF, rework), **hech narsa bloklanmaydi** — admin ko'radi. Qism narxi ta'minotchiga o'tadi |
| **v3** | Kritik bayroqlar tasdiqlashni bloklaydi |
| **v3+** | Statistik anomaliyalar, usta narx xulqi hisoboti, oylik xulosa |

> v1'da bayroqlar yo'q bo'lsa ham nazorat bor — **admin har bir narxni
> ko'rib chiqadi**. Bayroqlar keyinchalik uning ishini yengillashtirish uchun
> qo'shiladi (100 tadan 5 tasiga e'tibor qaratish).

Har fazadan keyin `false_positive` statistikasiga qarab chegaralar sozlanadi.

---

**Keyingi:** [03. Hisob-kitob va analitika](03-payroll-and-reports.md)
