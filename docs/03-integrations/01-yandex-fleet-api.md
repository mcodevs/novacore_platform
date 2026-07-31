# 01. Yandex Fleet API integratsiyasi

> Bu hujjat NovaCore'da allaqachon ishlab turgan `driver_status_reporter` loyihasida
> to'plangan **tasdiqlangan** bilimga tayanadi. Fleet API'ning to'liq tavsifi
> o'sha loyihaning `references/yandex-fleet-api-reference.md` faylida.

## 1. Nima uchun kerak

Fleet API integratsiyasisiz ham platforma ishlaydi, lekin u bilan:

| Foyda | Tafsilot |
|---|---|
| **Qo'lda kiritish yo'qoladi** | Mashina va haydovchi reyestri avtomatik to'ladi |
| **Haydovchi ↔ mashina bog'lanishi doim to'g'ri** | `car-bindings` sinxroni |
| **Ta'mirda zakaz kelmaydi** | Mashina statusini `repairing` ga o'tkazish |
| **Downtime real o'lchanadi** | Fleet'dagi status + platformadagi vaqt |
| **Xarajat 1 km ga hisoblanadi** | Buyurtmalar/probeg ma'lumoti bilan |

## 2. Ulanish parametrlari

| Parametr | Qiymat |
|---|---|
| Base URL | `https://fleet-api.taxi.yandex.net` |
| Auth headerlar | `X-Client-ID: taxi/park/<park_id>`, `X-Api-Key: <key>` |
| Park ID | `.env` da (mavjud) |
| Rasmiy hujjat | `https://fleet.yandex.uz/docs/api/ru/` |

⚠️ Kalitlar `.env` / secret manager'da. Repoda **yo'q**.

## 3. Ishlatiladigan endpointlar

| Endpoint | Nima uchun | Chastota |
|---|---|---|
| `POST /v1/parks/cars/list` | Mashina reyestri sinxroni | 1×/kun + qo'lda |
| `POST /v1/parks/driver-profiles/list` | Haydovchi reyestri, telefon, `car` bog'lanishi | 1×/kun + qo'lda |
| `PUT /v2/parks/vehicles/car` | Mashina statusini `repairing` ↔ `working` | Hodisa bo'yicha |
| `GET/POST` `contractor-profiles/car-bindings` | Haydovchi ↔ mashina bog'lanishi | 1×/kun |
| `POST /v1/parks/orders/list` | Probeg/daromad tahlili (v4) | 1×/kun |
| `.../supply-hours` | Liniyadagi soatlar → downtime bilan solishtirish (v4) | 1×/kun |

## 4. Sinxronizatsiya strategiyasi

```
┌──────────────────────────────────────────────────────────┐
│  YANDEX FLEET — haqiqat manbai (source of truth)         │
│  • mashina mavjudligi, davlat raqami, marka/model        │
│  • haydovchi mavjudligi, FIO, telefon, ish holati        │
│  • haydovchi ↔ mashina bog'lanishi                       │
└────────────────────────┬─────────────────────────────────┘
                         │ kuniga 1× + qo'lda [🔄 Sinxron]
                         ▼
┌──────────────────────────────────────────────────────────┐
│  NOVACORE PLATFORMA — haqiqat manbai                     │
│  • ta'mir tarixi, xarajat, hisobotlar                    │
│  • rollar, hisobotlar, narx kelishuvi                    │
│  • batareya holati, TO jadvali, ichki eslatmalar         │
└────────────────────────┬─────────────────────────────────┘
                         │ hodisa bo'yicha (ta'mir boshlandi/tugadi)
                         ▼
              PUT /v2/parks/vehicles/car → status
```

**Prinsip:** har bir maydonning **bitta egasi** bor. Ikki tomonlama tahrirlash
(bidirectional sync) — konflikt manbai, undan qochamiz.

| Maydon | Egasi | Platformada tahrirlanadimi |
|---|---|---|
| Davlat raqami, VIN, marka, model | Fleet | ❌ (faqat o'qish) |
| Mashina statusi | **Platforma** (ta'mir holati bo'yicha) | ✅ → Fleet'ga yoziladi |
| Batareya, TO jadvali, ichki eslatmalar | Platforma | ✅ |
| Haydovchi FIO, telefon | Fleet | ❌ |
| Rol, ruxsat | Platforma | ✅ |

## 5. Sinxron algoritmi (mashinalar)

```
1. cars/list  (limit=1000, offset, sahifalar orasida ~1.5 s pauza)
2. Har bir mashina uchun:
   • fleet_car_id bo'yicha topamiz
   • yo'q bo'lsa → yangi vehicle (status = active, branch = null → admin belgilaydi)
   • bor bo'lsa → Fleet egalik qiladigan maydonlarni yangilaymiz
3. Fleet'da yo'q, platformada bor → `sync_missing` bayrog'i (o'chirmaymiz!)
4. Natija: admin uchun hisobot "3 ta yangi, 1 ta yo'qolgan, 12 ta yangilandi"
```

⚠️ **Hech qachon avtomatik o'chirilmaydi.** Fleet'dan yo'qolgan mashinaning
ta'mir tarixi platformada qoladi.

## 6. Ta'mir statusini Fleet'ga yozish

```
Usta [🚗 Mashina keldi] bosdi  (arrived_at)
        ↓
PUT /v2/parks/vehicles/car  { status: "repairing" }
        ↓
Yandex zakaz bermaydi → mashina liniyadan chiqadi
        ↓
Usta [🚙 Mashina ketdi] bosdi  (left_at)
        ↓
PUT /v2/parks/vehicles/car  { status: "working" }
```

⚠️ **Ma'lum cheklov (`references/yandex-fleet-api-reference.md`dan):** ДКК
(fotokontrol) o'tgan mashinada ba'zi maydonlarni tahrirlash bloklanadi
(`cannot_edit_required_fields_when_dkk_passed`). Shu sababli:

- ✅ **Faqat `status` maydonini yuborish** kerak, boshqa maydonlarga tegmaslik
- ✅ Xato qaytsa — hisobot baribir saqlanadi, faqat `fleet_sync_failed` bayrog'i
  qo'yiladi va adminga xabar boradi
- ❌ Fleet xatosi tufayli ish jarayoni **to'xtamasligi kerak**

📌 Bu — sinovdan o'tkazilishi kerak bo'lgan taxmin
([A-09](../05-delivery/02-open-questions.md)).

## 7. Ma'lum cheklovlar (tasdiqlangan)

| Cheklov | Oqibati |
|---|---|
| **GPS / real-vaqt joylashuv yo'q** (partner API'da) | Mashina qayerdaligini Fleet'dan bilib bo'lmaydi. Geo — Mini App'dan olinadi |
| **Фотоконтроль (ДКК) natijasi yo'q** | Fotokontrol holatini platformaga tortib bo'lmaydi |
| **Reyting / "Приоритет" yo'q** | Haydovchi KPI'sini Fleet'dan olib bo'lmaydi |
| **Rate limit (429) real** | Backoff + retry, sahifalar orasida pauza majburiy |
| Ichki veb-API (cookie bilan) mavjud, lekin **beqaror** | Ishlab chiqarishda tayanmaslik |

> Bu cheklovlar `driver_status_reporter` loyihasida 31 ta endpoint spetsifikatsiyasi
> to'liq skanerlanib tasdiqlangan. Qayta tekshirishga hojat yo'q.

## 8. Xatolarga chidamlilik

| Vaziyat | Xatti-harakat |
|---|---|
| Fleet API javob bermayapti | Sinxron kechiktiriladi, keyingi urinishda davom etadi. Platforma ishlashda davom etadi |
| 429 (rate limit) | Eksponensial backoff, maksimal 5 urinish |
| 401/403 (kalit) | Adminga darhol Telegram alert |
| Qisman sinxron | Tranzaksiya har mashina uchun alohida — bittasi xato bo'lsa qolganlari saqlanadi |
| Status yozish xatosi | `fleet_sync_failed` bayrog'i, qayta urinish navbati, admin ko'radi |

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
