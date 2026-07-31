# 01. Yandex Fleet API integratsiyasi

> Bu hujjat NovaCore'da allaqachon ishlab turgan `driver_status_reporter` loyihasida
> to'plangan **tasdiqlangan** bilimga tayanadi. Fleet API'ning to'liq tavsifi
> o'sha loyihaning `references/yandex-fleet-api-reference.md` faylida.

## 1. Nima uchun kerak

> ⚠️ **Doira (egasining qarori, 2026-08-01): Fleet FAQAT O'QISH uchun** —
> *mashina raqami bo'yicha mashina va haydovchi ma'lumotini olish*. Platforma
> Fleet'ga **hech narsa yozmaydi**. Boshqa maqsadda ishlatilmaydi.

Fleet integratsiyasisiz ham platforma to'liq ishlaydi, u bilan esa:

| Foyda | Tafsilot |
|---|---|
| **Qo'lda kiritish yo'qoladi** | Usta raqamni kiritadi — marka, model, yil o'zi to'ladi |
| **Joriy haydovchi ko'rinadi** | Kartochkada «kim minadi» yoziladi |
| **Reyestr o'zi yangilanadi** | Yangi mashina qo'shilsa keyingi sinxronda paydo bo'ladi |

## 2. Ulanish parametrlari

| Parametr | Qiymat |
|---|---|
| Base URL | `https://fleet-api.taxi.yandex.net` |
| Auth headerlar | `X-Client-ID: taxi/park/<park_id>`, `X-Api-Key: <key>` |
| Park ID | `.env` da (mavjud) |
| Rasmiy hujjat | `https://fleet.yandex.uz/docs/api/ru/` |

⚠️ Kalitlar `.env` / secret manager'da. Repoda **yo'q**.

## 3. Ishlatiladigan endpointlar

**Ishlatiladigani — ikkita, ikkalasi ham o'qish:**

| Endpoint | Nima uchun | Chastota |
|---|---|---|
| `POST /v1/parks/cars/list` | Mashina reyestri | 1×/kun + qo'lda + noma'lum raqam so'ralganda |
| `POST /v1/parks/driver-profiles/list` | Haydovchi ↔ mashina bog'lanishi (javobdagi `car` maydoni) | shu bilan birga |

**Ishlatilmaydi:** `PUT /v2/parks/vehicles/car` (yozish — doiradan tashqari) ·
`car-bindings` (kerak emas: bog'lanish `driver-profiles/list` da bor) ·
`orders/list`, `supply-hours` (Faza 4+ g'oyalari).

## 4. Sinxronizatsiya strategiyasi

```
┌──────────────────────────────────────────────────────────┐
│  YANDEX FLEET — haqiqat manbai (source of truth)         │
│  • mashina mavjudligi, davlat raqami, marka/model, VIN   │
│  • haydovchi FIO, telefon, ish holati                    │
│  • haydovchi ↔ mashina bog'lanishi                       │
└────────────────────────┬─────────────────────────────────┘
                         │ kuniga 1× + qo'lda [🔄 Sinxron]
                         │ + noma'lum raqam so'ralganda
                         ▼
┌──────────────────────────────────────────────────────────┐
│  NOVACORE PLATFORMA — haqiqat manbai                     │
│  • ta'mir tarixi, xarajat, hisobotlar                    │
│  • rollar, narx kelishuvi                                │
│  • batareya holati, TO jadvali, ichki eslatmalar         │
└──────────────────────────────────────────────────────────┘
                    ✋ orqaga yozish YO'Q
```

**Prinsip:** har bir maydonning **bitta egasi** bor. Ikki tomonlama tahrirlash
(bidirectional sync) — konflikt manbai, undan qochamiz.

| Maydon | Egasi | Platformada tahrirlanadimi |
|---|---|---|
| Davlat raqami, VIN, marka, model | Fleet | ❌ (faqat o'qish) |
| Mashina statusi | Fleet | ❌ (faqat o'qish — ma'lumot uchun) |
| Batareya, TO jadvali, ichki eslatmalar | Platforma | ✅ |
| Haydovchi FIO, telefon | Fleet | ❌ |
| Rol, ruxsat | Platforma | ✅ |

## 5. Sinxron algoritmi (mashinalar)

```
1. cars/list  (limit=1000, offset, sahifalar orasida ~1.5 s pauza)
2. Har bir mashina uchun:
   • fleet_car_id bo'yicha topamiz
   • topilmasa — davlat raqami bo'yicha (qo'lda kiritilgan mashina bog'lanadi)
   • yo'q bo'lsa → yangi vehicle (status = active)
   • bor bo'lsa → Fleet egalik qiladigan maydonlarni yangilaymiz
3. driver-profiles/list → `car.id` bo'yicha joriy haydovchi biriktiriladi
   (`work_status != working` bo'lsa biriktirilmaydi)
4. Fleet'da yo'q, platformada bor → `vehicles.fleet_missing` (o'chirmaymiz!)
5. Natija: admin uchun hisobot "3 ta yangi, 1 ta yo'qolgan, 12 ta yangilandi"
```

Ishga tushirish: kuniga 1× fon siklida (`FLEET_SYNC_HOUR`, Toshkent vaqti) ·
qo'lda `POST /api/v1/admin/fleet/sync` yoki `manage.py fleet-sync` ·
noma'lum raqam so'ralganda avtomatik (`manage.py fleet-lookup 01A123BC`).

⚠️ **Hech qachon avtomatik o'chirilmaydi.** Fleet'dan yo'qolgan mashinaning
ta'mir tarixi platformada qoladi.

## 6. Nima uchun Fleet'ga yozmaymiz

Avvalgi rejada mashina ustaxonaga kelganda Fleet'da `repairing`, ketganda
`working` qilib qo'yish bor edi. **Bekor qilindi** — ikki sabab:

**1. Egasining qarori (2026-08-01):** Fleet faqat *raqam bo'yicha mashina va
haydovchi ma'lumotini olish* uchun kerak.

**2. Texnik jihatdan ham qimmat edi.** `PUT /v2/parks/vehicles/car` — bu
**to'liq almashtirish** (full replace), rasmiy spetsifikatsiyada uchala obyekt
ham majburiy:

| Obyekt | Majburiy maydonlar |
|---|---|
| `park_profile` | `callsign`, `fuel_type`, `status` |
| `vehicle_licenses` | `licence_plate_number` |
| `vehicle_specifications` | `brand`, `color`, `model`, `transmission`, `year` |

Ya'ni «faqat `status` yuborish» **mumkin emas**: statusni o'zgartirish uchun
avval `GET /v2/parks/vehicles/car` bilan kartochkani olib, aynan ДКК
qulflaydigan maydonlarni (`brand`, `model`, `licence_plate_number`…) qaytarib
yuborish kerak bo'lardi — `cannot_edit_required_fields_when_dkk_passed` xavfi
bilan. Yozish yo'q ekan, bu xavf ham yo'q: **[A-09](../05-delivery/02-open-questions.md)
sinovi endi kerak emas.**

> 📌 Agar kelajakda «ta'mirda zakaz kelmasin» talab qaytsa — GET→PUT yo'li
> shu yerda yozilgan, lekin ДКК cheklovi avval sinovdan o'tkazilishi kerak.

## 6a. ⚠️ Real parkda topilgan ikkita muammo (2026-08-01, 292 yozuv skanerlandi)

Birinchi haqiqiy sinxronda hujjatning ikki taxmini rad etildi.

### 1. Bitta raqamga bir nechta Fleet yozuvi

292 ta `cars/list` yozuvi, atigi **164 ta unikal davlat raqami**. 66 raqamda
2–5 tadan yozuv bor va **hammasi `working`** — ya'ni `status` ajratmaydi.

Platformada raqam unikal (bitta jismoniy mashina = bitta yozuv), shuning uchun
sinxron **deterministik** tanlaydi: avval platformaga allaqachon bog'langan
yozuv, aks holda `id` bo'yicha eng kichigi. Aks holda `fleet_car_id` har
sinxronda sakrab yurardi. Dublikatlar soni admin hisobotiga chiqadi —
tozalash **Fleet tomonida** qilinadi.

### 2. «Joriy haydovchi» — `driver-profiles/list` bunga javob bermaydi

`driver_profiles[].car` — *tarixiy* bog'lanish, joriy emas. Bitta mashinaga
**71 tagacha** har xil `working` profil uchradi (71 unikal telefon, 71 unikal
FIO). 188 mashinadan atigi 53 tasi bir ma'noli edi.

Partner API'da ishonchli signal **yo'q**: `car-bindings` da `GET` yo'q
(faqat `PUT`/`DELETE`), `cars/list` da haydovchi maydoni yo'q
(`id`, `number`, `vin`, `brand`, `model`, `year`, `color`, `status`,
`callsign`, `registration_cert`, `amenities`, `category` — boshqa yo'q).

**Qaror:** noaniq bo'lsa **haydovchi yozilmaydi**. Noto'g'ri ism usta
hisobotida qolib ketishidan ko'ra bo'sh qolgani yaxshi. Hozircha real natija:
164 mashina · 27 tasida haydovchi aniq · 76 tasi noaniq.

> 📌 Agar joriy haydovchi muhim bo'lib qolsa — yagona yo'l ichki veb-API
> (cookie bilan, `driver_status_reporter` da bor, lekin **beqaror**) yoki
> parkni Fleet tomonida tozalash.

## 7. Ma'lum cheklovlar (tasdiqlangan)

| Cheklov | Oqibati |
|---|---|
| **GPS / real-vaqt joylashuv yo'q** (partner API'da) | Mashina qayerdaligini Fleet'dan bilib bo'lmaydi. Geo — Mini App'dan olinadi |
| **Фотоконтроль (ДКК) natijasi yo'q** | Fotokontrol holatini platformaga tortib bo'lmaydi |
| **Reyting / "Приоритет" yo'q** | Haydovchi KPI'sini Fleet'dan olib bo'lmaydi |
| **Rate limit (429) real** | Backoff + retry majburiy — birinchi sinxronda 3 marta 429 olindi |
| **Bir raqam ↔ bir nechta yozuv** | Deterministik tanlov kerak (§6a) |
| **Joriy haydovchi aniqlanmaydi** | Profil↔mashina bog'lanishi tarixiy (§6a) |
| Ichki veb-API (cookie bilan) mavjud, lekin **beqaror** | Ishlab chiqarishda tayanmaslik |

> Bu cheklovlar `driver_status_reporter` loyihasida 31 ta endpoint spetsifikatsiyasi
> to'liq skanerlanib tasdiqlangan. Qayta tekshirishga hojat yo'q.

## 8. Xatolarga chidamlilik

| Vaziyat | Xatti-harakat |
|---|---|
| Fleet API javob bermayapti | Sinxron kechiktiriladi, keyingi urinishda davom etadi. Platforma ishlashda davom etadi |
| 429 (rate limit) | Eksponensial backoff, maksimal 5 urinish |
| 401/403 (kalit) | Adminga darhol Telegram alert |
| Qisman sinxron | Har mashina alohida — bittasi xato bo'lsa qolganlari saqlanadi (`report.skipped`) |
| Raqam noma'lum formatda | O'tkazib yuboriladi, hisobotda ko'rsatiladi — sinxron to'xtamaydi |
| Fleet umuman o'chirilgan | `FLEET_ENABLED=false` — platforma to'liq ishlaydi, qidiruv faqat lokal reyestrdan |

## 9. Mavjud bot bilan aloqasi

`driver_status_reporter` (status kuzatuvi) va yangi platforma — **ikki alohida
mahsulot**. Ularni birlashtirish shart emas, lekin:

| Variant | Baho |
|---|---|
| Alohida qoldirish | ✅ Tavsiya. Har biri o'z ishini qiladi, xavf kam |
| Fleet klientini umumiy kutubxona qilish | 🟡 Foydali, lekin majburiy emas |
| Bitta botga birlashtirish | ❌ Kerak emas — auditoriya boshqa (kuzatuv guruhi ↔ xodimlar) |

Kelajakda foydali bo'ladigan bog'lanish: platformada mashina `repairing` bo'lsa,
status-kuzatuv boti o'sha haydovchini "offline" deb alert qilmasin.

---

**Keyingi:** [02. Telegram bot + Mini App](02-telegram-bot-miniapp.md)
