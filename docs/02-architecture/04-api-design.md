# 04. API dizayni

REST, JSON, `/api/v1`. FastAPI avtomatik OpenAPI hujjatini `/docs` da beradi —
Mini App shundan foydalanadi.

## 1. Umumiy konvensiyalar

| Jihat | Qoida |
|---|---|
| Format | `application/json`, UTF-8 |
| Vaqt | ISO 8601, UTC (`2026-07-31T09:14:00Z`) |
| Pul | `number` (masalan `150000.00`), valyuta doim UZS |
| Nomlash | `snake_case` |
| Pagination | `?limit=20&cursor=<opaque>` |
| Til | `Accept-Language: uz` yoki `ru` |
| Idempotentlik | `Idempotency-Key` header — POST uchun |

## 2. Autentifikatsiya

```
POST /api/v1/auth/telegram   { init_data: "query_id=..." }
        ↓  HMAC tekshiruv + auth_date < 1 soat
        ↓  tg_user_id → employee → role
   { access_token (15 daq), refresh_token (30 kun),
     employee: {...}, role: { code, name, kind, icon },
     templates: [...] }
```

| Endpoint | Tavsif |
|---|---|
| `POST` `/auth/telegram` | initData → JWT |
| `POST` `/auth/refresh` | refresh → yangi access |
| `POST` `/auth/logout` | refresh'ni bekor qilish |
| `GET` `/me` | Profil, rol, ko'rinadigan shablonlar, sozlamalar |

Batafsil: [06-security.md](06-security.md)

## 3. Spravochniklar

| Metod | Yo'l | Tavsif |
|---|---|---|
| `GET` | `/vehicles` | `?q=01A123&status=` |
| `GET` | `/vehicles/{id}` | Kartochka + oxirgi hisobotlar + shu oydagi xarajat |
| `GET` | `/vehicles/{id}/history` | To'liq ta'mir tarixi |
| `GET` | `/vehicles/lookup?plate=01A123BC` | Raqam bo'yicha tez qidiruv. Reyestrda bo'lmasa — **Fleet'dan** tortiladi (Faza 3, faqat o'qish) |
| `GET` | `/employees` | `?role_id=&status=` |
| `GET` | `/work-catalog` | Ish turlari. ⚠️ `reference_price` `reporter` roliga **qaytarilmaydi** |
| `GET` | `/parts-catalog` | `?q=` |
| `GET` | `/templates` | **Menga tegishli** shablonlar (rolim bo'yicha, faqat **nashr etilganlari**) |
| `GET` | `/templates/{code}` | To'liq sxema (forma chizish uchun). `?version=` — eski hisobot uchun |

## 4. Hisobotlar

| Metod | Yo'l | Tavsif |
|---|---|---|
| `GET` | `/submissions` | `?status=&author_id=me&period_id=&vehicle_id=&limit=&offset=`. `status` vergulli bo'lishi mumkin: `submitted,in_review` |
| `POST` | `/submissions` | Yangi qoralama: `{ template_code, vehicle_id? }` → **`arrived_at` server vaqti bilan yoziladi** |
| `GET` | `/submissions/{id}` | Sxema + qiymatlar + media + bayroqlar + kelishuv tarixi |
| `PATCH` | `/submissions/{id}` | Qoralamani qisman saqlash `{ data: {...} }` |
| `PUT` | `/submissions/{id}/lines` | Qatorlarni to'liq almashtirish |
| `POST` | `/submissions/{id}/mark-left` | ⭐ "Mashina ketdi" → `left_at` server vaqti |
| `POST` | `/submissions/{id}/submit` | Yuborish. ⭐ Muallif `admin` bo'lsa → darhol `APPROVED` (R1a) |
| `POST` | `/submissions/{id}/approve` | `{ comment? }` — narx o'zgarishsiz |
| `POST` | `/submissions/{id}/reject` | `{ comment }` — majburiy |
| `POST` | `/submissions/{id}/reopen` | `{ comment }` — muallifga qaytarish |
| `DELETE` | `/submissions/{id}` | Faqat `DRAFT`, faqat muallif |
| `GET` | `/submissions/linkable` | `submission_picker` nomzodlari: `?template_code=&vehicle_id=&exclude_id=`. **Summasiz** javob; `reporter` uchun `vehicle_id` majburiy |

## 5. Narx kelishuvi ⭐

| Metod | Yo'l | Tavsif |
|---|---|---|
| `GET` | `/submissions/{id}/price-context` | **Admin uchun:** har qator bo'yicha tarixiy statistika (o'rtacha/min/max, muallifning o'z tarixi) |
| `POST` | `/submissions/{id}/propose-price` | `{ lines: [{line_id, amount}], comment }` — **comment majburiy** |
| `POST` | `/submissions/{id}/accept-price` | Muallif rozilik beradi |
| `POST` | `/submissions/{id}/dispute-price` | `{ comment }` — majburiy |
| `GET` | `/submissions/{id}/price-history` | Kelishuvning to'liq izi |
| `GET` | `/me/price-stats` | ⭐ Xodimning **o'z** narx statistikasi |
| `GET` | `/work-catalog/{id}/price-stats` | Ish turi bo'yicha statistika (**admin**) |

**Server tekshiruvlari:**

| Tekshiruv | Xato |
|---|---|
| `amount < proposed_amount` | `422 price_increase_forbidden` |
| `accept/dispute` — faqat `author_id == me` | `403 forbidden` |
| `price-context`, `price-stats` — `reporter`ga yopiq | `403 price_reference_hidden` |
| `approve` — `author_id ≠ me` | `409 self_approval_forbidden` |

## 6. Media

| Metod | Yo'l | Tavsif |
|---|---|---|
| `POST` | `/media/upload-url` | Presigned URL: `{ submission_id, field_code, mime, size, sha256, exif? }` |
| `POST` | `/media/{id}/complete` | Yuklash tugadi → fon qayta ishlash |
| `GET` | `/media/{id}` | Vaqtinchalik ko'rish URL (signed, 15 daq) |
| `DELETE` | `/media/{id}` | **Qo'lda** o'chirish (admin) — `deleted_at` |

Batafsil: [03-integrations/03-media-and-storage.md](../03-integrations/03-media-and-storage.md)

## 7. Admin

| Metod | Yo'l | Tavsif |
|---|---|---|
| `GET/POST/PATCH` | `/admin/vehicles` | Mashina reyestri |
| `GET/POST/PATCH` | `/admin/employees` | Xodimlar |
| `POST` | `/admin/employees/{id}/role` | `{ role_id }` — R8 tekshiriladi |
| `POST` | `/admin/employees/{id}/status` | `{ status }`: `active` / `blocked` / `fired`. R5 — kirish yopiladi, ma'lumot qoladi |
| **`GET/POST`** | **`/admin/roles`** | ⭐ Rol yaratish: `{ code, name_uz, name_ru, icon, kind, template_ids[] }` |
| **`PATCH`** | **`/admin/roles/{id}`** | Nom, ikonka, `kind`, `template_ids`, `is_active`. `code` o'zgarmas |
| `GET` | `/admin/templates` | Barcha shablonlar + qoralama holati (`is_draft`, `published_version`) |
| `GET` | `/admin/templates/{id}` | Joriy sxema (`definition`) — konstruktor shuni ochadi |
| `POST/PATCH` | `/admin/templates`, `/admin/templates/{id}` | Sxema seed JSON'i bilan bir xil ko'rinishda |
| `POST` | `/admin/templates/{id}/publish` | Nashr — snapshot yoziladi va o'zgarmas bo'ladi |
| `GET/POST/PATCH` | `/admin/work-catalog` | Ish turlari + tayanch narx |
| `GET` | `/admin/audit` | `?actor_id=&entity=&from=&to=` |
| `GET` | `/admin/flags` | Bayroqlar |
| `POST` | `/admin/flags/{id}/resolve` | `{ resolution, comment }` |
| `POST` | `/admin/fleet/sync` | Qo'lda Fleet sinxroni. Xato bo'lsa ham **200** + `error` — platforma Fleet'siz ishlaydi |
| **`POST`** | **`/admin/broadcasts`** | ⭐ E'lon yuborish: `{ body }` → barcha faol xodimlar navbatga qo'yiladi |
| **`GET`** | **`/admin/broadcasts`** | E'lonlar tarixi + yetkazish hisobi. `?limit=20` |

⚠️ `POST /admin/roles` — `kind` faqat `reporter` / `admin` / `accountant`

⚠️ `PATCH /admin/roles/{id}`:
- `is_system` rol (seed: usta, ta'minotchi, admin, buxgalter) — turi
  o'zgarmaydi va o'chirilmaydi (`business_rule_violated`)
- `kind='admin'` rolni boshqa turga o'tkazish shu roldagi **barcha** xodimlarni
  admin huquqidan mahrum qiladi → R8 tekshiriladi (`last_admin_required`)
bo'lishi mumkin. Oxirgi `admin` rolli xodimni o'chirish `409` beradi (R8).

### E'lon (broadcast) ⭐

Butun `/admin/*` kabi — **faqat `role.kind = 'admin'`**. Klient tekshiruviga
ishonilmaydi; boshqa rol `403 forbidden` oladi.

**Yuborish**

```
POST /api/v1/admin/broadcasts
{ "body": "Ertaga ombor yopiq. Qism kerak bo'lsa bugun oling." }
        ↓  201
{ "id": 7,
  "body": "Ertaga ombor yopiq. Qism kerak bo'lsa bugun oling.",
  "recipients_total": 24,
  "created_at": "2026-08-02T05:14:00Z",
  "author_name": "Aliyev A." }
```

- `body` — **xom matn**, javobda ham xom qaytadi (escape faqat botga yuborishda)
- Qabul qiluvchilar: `status = active` **va** `deleted_at IS NULL` **va**
  `tg_user_id IS NOT NULL`
- `recipients_total` — navbatga (`notifications`) qo'yilganlar soni, **yetkazilgan
  emas**
- Har yuborish `audit_log`ga tushadi: `broadcast_sent`
- ⚠️ **Takror so'rovga chidamli:** bitta admin **60 sekund** ichida aynan bir xil
  `body` yuborsa yangi e'lon yaratilmaydi — mavjudi qaytariladi (201, o'sha `id`).
  Sabab: `fetch` javob yo'lda yo'qolganda ham rad etadi, klient esa so'rovni
  takrorlashi mumkin — e'lon esa qaytarib bo'lmaydigan amal

**Tarix**

```
GET /api/v1/admin/broadcasts?limit=20
        ↓  200
[ { "id": 7, "body": "Ertaga ombor yopiq…",
    "recipients_total": 24,
    "created_at": "2026-08-02T05:14:00Z",
    "author_name": "Aliyev A.",
    "delivered": 22, "failed": 1, "pending": 1 } ]
```

`delivered` / `failed` / `pending` — `notifications.broadcast_id` bo'yicha
status hisobi; ular vaqt o'tishi bilan o'zgaradi (outbox sikli).

**Xatolar**

| HTTP | `code` | Qachon |
|---|---|---|
| 400 | `validation_failed` | `body` bo'sh (yoki faqat probel) |
| 400 | `validation_failed` | `body` uzunligi **3500** belgidan oshdi |
| 403 | `forbidden` | Yuboruvchi `admin` emas |

⚠️ E'lonni **o'chirish yoki tahrirlash endpointi yo'q** — yuborilgan xabar
qaytarilmaydi, tarix o'zgarmaydi (R9).

## 8. Davr va to'lovlar

| Metod | Yo'l | Tavsif |
|---|---|---|
| `GET` | `/periods` | Davrlar |
| `GET` | `/periods/{id}/precheck` | Yopishga to'sqinlik qiluvchilar ro'yxati |
| `POST` | `/periods/{id}/close` | Yopish |
| `POST` | `/periods/{id}/reopen` | `{ reason }` — faqat admin |
| `GET` | `/payouts?period_id=` | To'lov varaqalari |
| `POST` | `/payouts/{id}/adjust` | `{ bonus, penalty, reason }` |
| `POST` | `/payouts/{id}/mark-paid` | |

## 9. Analitika va eksport

| Metod | Yo'l | Tavsif |
|---|---|---|
| `GET` | `/reports/dashboard` | Asosiy ko'rsatkichlar |
| `GET` | `/reports/negotiation-savings` | ⭐ Kelishuv tejamkorligi |
| `GET` | `/reports/vehicle-costs` | Mashina × davr |
| `GET` | `/reports/employee-performance` | Xodim × davr (narx xulqi bilan) |
| `GET` | `/reports/downtime` | `left_at − arrived_at` bo'yicha |
| `POST` | `/reports/export` | Excel generatsiya → `task_id` |
| `GET` | `/reports/export/{task_id}` | Tayyor faylni olish |

Import endpointi **yo'q** — faqat eksport.

## 10. Javob formatlari

```json
{ "data": { "id": 1247, "number": "WO-2026-001247", "status": "submitted" },
  "meta": { "request_id": "01J..." } }
```

```json
{ "error": {
    "code": "validation_failed",
    "message": "Forma to'liq to'ldirilmagan",
    "fields": { "photo_after": "Kamida 1 ta foto kerak" },
    "request_id": "01J..." } }
```

### Xato kodlari

| HTTP | `code` | Qachon |
|---|---|---|
| 400 | `validation_failed` | Forma xatosi |
| 401 | `unauthenticated` / `invalid_init_data` | Token yo'q / HMAC noto'g'ri |
| 403 | `forbidden` | Ruxsat yo'q |
| 403 | `not_in_registry` | Telegram akkaunt xodim emas |
| 403 | `price_reference_hidden` | `reporter` tayanch narxni so'radi |
| 404 | `not_found` | |
| 409 | `invalid_state_transition` | Holat o'tishi mumkin emas |
| 409 | `period_closed` | Davr yopilgan |
| 409 | `self_approval_forbidden` | O'z hisobotini tasdiqlash (R1) |
| 409 | `last_admin_required` | Oxirgi adminni o'chirish (R8) |
| 413 | `file_too_large` | |
| 422 | `price_increase_forbidden` | Admin narxni oshirmoqchi (R2) |
| 422 | `business_rule_violated` | Probeg kamaygan, `left_at < arrived_at` va h.k. |
| 429 | `rate_limited` | |

## 11. Hisobot yuborish — batafsil oqim

```
POST /submissions/{id}/submit
        │
        ▼
1. Ruxsat:  author == me ?
2. Holat:   status ∈ {DRAFT, REOPENED} ?
3. Davr:    joriy davr ochiqmi ?
4. left_at to'ldirilganmi ? (mashina ketgan bo'lishi kerak)
5. Shablon validatsiyasi: majburiy maydonlar, foto min/max, lines bo'sh emas
6. Biznes tekshiruvlar: probeg kamaymadimi, left_at > arrived_at
7. Summalar QAYTA hisoblanadi (klientga ishonilmaydi)
8. Promoted ustunlar to'ldiriladi (field_mapping)
9. Bayroqlar hisoblanadi → flags
10. Muallifning role.kind:
    ├─ reporter → status = SUBMITTED, adminga bildirishnoma
    └─ admin    → status = APPROVED (R1a):
                  approved_* = proposed_*, auto_approved = true,
                  approvals(decision='auto_approved', actor_id=NULL)
                  ⓘ bildirishnoma yo'q, narx kelishuvi yo'q
11. submitted_at = now(), period_id belgilanadi
12. Fon: pHash hisoblash, Fleet status (Faza 3)
13. audit_log
```

1–11 — **bitta tranzaksiyada**, 12 — `after commit`.

## 12. Rate limiting

| Guruh | Limit |
|---|---|
| `POST /auth/*` | 10 / daq / IP |
| `POST /media/*` | 60 / daq / xodim |
| `POST /submissions/*/submit` | 20 / soat / xodim |
| Boshqa `GET` | 300 / daq / xodim |

---

**Keyingi:** [05. Holat mashinalari](05-state-machines.md)
