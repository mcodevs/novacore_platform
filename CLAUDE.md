# CLAUDE.md — NovaCore Employee Platform

NovaCore (Toshkentdagi Yandex taksopark, ~150 elektromobil) xodimlari uchun ichki
platforma: **bitta Telegram bot + uning ichida bitta Mini App**.

Asosiy modul — ta'mir hisoboti: usta foto, izoh va **o'z narxini** kiritadi;
admin ko'rib chiqadi va **narxni kelishib kamaytiradi**.

> ⚠️ **`docs/` — yagona haqiqat manbai.** Kod hujjatga mos kelmasa — hujjat
> to'g'ri. Talab noaniq bo'lsa: avval hujjatni tuzat, keyin kod yoz.

## Hujjatlarni o'qish tartibi

| Qachon | Nima o'qiladi |
|---|---|
| **Har doim, birinchi** | [docs/01-product/01-roles-and-permissions.md](docs/01-product/01-roles-and-permissions.md) — rol modeli odatiy RBAC'dan farq qiladi |
| Domen mantiqi | [04-flows/04-price-negotiation.md](docs/04-flows/04-price-negotiation.md) · [02-architecture/05-state-machines.md](docs/02-architecture/05-state-machines.md) |
| Migratsiya / modellar | [02-architecture/02-data-model.md](docs/02-architecture/02-data-model.md) |
| Shablon dvigateli | [02-architecture/03-report-templates.md](docs/02-architecture/03-report-templates.md) |
| API | [02-architecture/04-api-design.md](docs/02-architecture/04-api-design.md) |
| Auth / xavfsizlik | [02-architecture/06-security.md](docs/02-architecture/06-security.md) |
| Reja va testlar | [05-delivery/01-roadmap.md](docs/05-delivery/01-roadmap.md) |
| Nima uchun shunday | [05-delivery/03-decisions.md](docs/05-delivery/03-decisions.md) — 14 ta ADR |

## Buzilmasligi SHART bo'lgan invariantlar

Bular serverda tekshiriladi. Klientga hech qachon ishonilmaydi.

| # | Qoida |
|---|---|
| **R1** | `approver_id ≠ author_id` — hech kim o'z hisobotini **qo'lda** tasdiqlay olmaydi |
| **R1a** | `role.kind == 'admin'` muallifi → hisobot **avtomatik tasdiqlanadi**: `DRAFT → APPROVED`, `approved_* = proposed_*`, `auto_approved = true`, `approvals(decision='auto_approved', actor_id=NULL)`. Narx kelishuvi bo'lmaydi |
| **R2** | `approved_amount ≤ proposed_amount` — admin narxni **faqat kamaytira oladi** (DB `CHECK`) |
| **R2a** | `proposed_*` — **immutable**. Yuborilgandan keyin hech qachon ustidan yozilmaydi |
| **R2b** | `approved < proposed` bo'lsa `price_change_reason` NOT NULL |
| **R3** | Tayanch narx (`work_catalog.reference_price`, `work_price_stats`) `reporter` roliga **API javobida ham** qaytarilmaydi — klientda yashirish yetarli emas |
| **R4** | Yopilgan davrga (`period.status = closed`) yozuv qo'shilmaydi va o'zgarmaydi |
| **R5** | To'lov varaqasi **faqat `approved_amount`** bo'yicha hisoblanadi |
| **R6** | `arrived_at` / `left_at` — **server vaqti** (tugma bosilgan lahza), klient yuborgan qiymat emas |
| **R7** | Summalar serverda **qayta hisoblanadi** (`submission_lines`dan), klient hisobiga ishonilmaydi |
| **R8** | Kamida bitta faol `kind='admin'` rolli xodim bo'lishi shart |
| **R9** | O'chirish yo'q — `deleted_at` (soft delete). `audit_log` **hech qachon** o'chirilmaydi/tahrirlanmaydi |

## Rol modeli (odatiy RBAC EMAS)

Rol = **nom** + `kind` + qaysi shablonlarni ko'rishi. `kind` faqat uchta:
`reporter` · `admin` · `accountant`. Nomlar cheksiz — admin panelidan yaratiladi
(Usta, Ta'minotchi, Elektrik…). Xodimda **bitta** rol.

- ❌ `permissions` / `role_permissions` jadvallari **yo'q**
- Ruxsat tekshiruvi: `role.kind` + biznes qoida. Xolos
- Vazifalarni ajratish **shablon orqali** (ustaning shablonida qism narxi
  maydoni yo'q), qattiq taqiq orqali emas

## Ataylab YO'Q — qayta kiritmang

Bular unutilgan emas, **ataylab olib tashlangan**. "Foydali bo'lardi" deb
qo'shmang — har biri ADR bilan rad etilgan:

| Yo'q | Nima uchun |
|---|---|
| **Haydovchi roli** | ADR-0013. Mashina kelgani/ketgani ustaning ikki tugmasi bilan |
| **Filial (branch)** | Ustalar o'z ustaxonalarida ishlaydi |
| **Zayavka (`service_requests`)** | Usta hisobotni o'zi ochadi |
| **Ombor / qoldiq** | Qism omborga tushmaydi |
| **`part_requests` jadvali** | Ta'minotchining xaridi — oddiy `submission` |
| **Redis / Celery / worker / mikroservis** | ADR-0004. RPS < 1, kuniga 3–5 hisobot |
| **Ma'lumot importi** | Faqat Excel **eksport** |
| **Media avtomatik arxivlash** | Qo'lda (`media.deleted_at`) |
| **Ko'p bosqichli tasdiqlash** | Bitta bosqich, direktorga ko'tarish yo'q |

## Stack

- **Python 3.12** · FastAPI + **aiogram 3 bitta ASGI ilovada, bitta process**
- SQLAlchemy 2 + Alembic · PostgreSQL (Fly Postgres)
- Media: **Tigris** (fly.io S3-mos), private bucket + presigned URL
- Fon vazifalari: **asyncio sikli + Postgres `notifications` outbox** (Redis yo'q)
- Mini App: React 18 + TS + Vite + `@telegram-apps/*`, tayyor UI kit, 4 ekran
- Deploy: **fly.io** (Docker). Lokal: `docker compose`

**Konvensiyalar:** pul — `NUMERIC(14,2)`, valyuta doim UZS (ustun kerak emas) ·
vaqt — `TIMESTAMPTZ`, saqlash UTC, ko'rsatish `Asia/Tashkent` · nomlash
`snake_case` · i18n **uz + ru 1-kundan**.

## Testlar — majburiy

Kodni AI yozgani uchun domen testlarisiz ishonch yo'q. Eng kam qamrov:

| Modul | Nima tekshiriladi |
|---|---|
| `pricing` | R2, R2a, R2b · 48 soat avtomatik rozilik · nizo oqimi · R1a (admin → avtomatik tasdiq, kelishuvsiz) |
| `period` | R4 · precheck to'siqlari · to'lov `approved_amount` bo'yicha (R5) |
| `approval` | R1 · holat o'tishlari |
| `template` | Majburiy maydonlar · foto min/max · versiyalash (eski hisobot buzilmasin) |
| `role` | R3 (tayanch narx yopiqligi) · `kind` bo'yicha ruxsatlar · R8 |

## Yandex Fleet API (Faza 3) — tasdiqlangan cheklovlar

`driver_status_reporter` loyihasida 31 endpoint spec skanerlangan, **qayta
tekshirish shart emas**:

- Partner API'da **GPS / real-vaqt joylashuv YO'Q**
- **Фотоконтроль (ДКК) natijasi YO'Q**, reyting / "Приоритет" / brending ham yo'q
- **Rate-limit (429) real** — backoff + sahifalar orasida pauza majburiy
- Mashina statusi: `working` / `not_working` / `repairing` / `no_driver` / `pending`
- ⚠️ ДКК o'tgan mashinada ba'zi maydonlar qulflanadi → **faqat `status`
  maydonini yuborish**; xato bo'lsa platforma to'xtamaydi (`fleet_sync_failed`)
- Sinxron **bir tomonlama**: Fleet → platforma (mashina ma'lumoti), platforma →
  Fleet (faqat `status`)

## Ish uslubi

- **Har qadamdan keyin ishlaydigan holat.** "Hammasini yozib bo'lgach sinaymiz" —
  eng xavfli yondashuv
- **Birinchi kesim ingichka va uchidan-uchiga:** usta hisobot yuboradi → admin
  narxni kamaytiradi → usta rozi bo'ladi. Qatlamlarni birma-bir to'liq yozib
  chiqish (butun DB → butun API → butun UI) mumkin emas
- **Deploy birinchi kunda** — HTTPS, Telegram webhook va Mini App domeni
  kutilmagan muammolar manbai
- Foydalanuvchi bilan muloqot va barcha UI matnlari — **o'zbek tilida**

## Ochiq texnik xavf

`<input type="file" accept="image/*" capture="environment">` Telegram
WebView'ida (ayniqsa **iOS**) galereyani bloklaydimi — **hali sinalmagan**.
Ishlamasa foto-dalil g'oyasi zaiflashadi; zaxira: EXIF tekshiruvi
(`photo_not_fresh`, `photo_no_exif`) va bot orqali foto yuborish oqimi.
Bu — **Faza 0 ning birinchi vazifasi**.
