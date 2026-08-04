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
| **R4** | To'lov faqat `APPROVED` hisobotga. `paid_amount ≤ payable_amount` (DB `CHECK`). Qarzdan ortgani — **avans** (P7), xodim hisobida turadi va yangi qarzga avtomatik ishlatiladi |
| **R5** | `payable_amount` = tasdiqlangan ish haqi + **`self_funded`** qismlar. Serverda `submission_lines`dan qayta hisoblanadi |
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
| **Oy yopish / davr (`periods`) / `payouts`** | ADR-0015. To'lov oyga emas, **hisobotga** bog'langan — qarz daftari |
| **Probeg hisobotda** (`odometer_*`) | ADR-0018. Har hisobotda spidometr fotosi — eng qimmat, eng foydasiz maydon edi. `vehicles.odometer_km` (Fleet'dan) qoladi |
| **Foto galereyadan** | ADR-0017. Faqat kamera (`capture`). Serverda ham `source=gallery` rad etiladi |
| **Savdolashish ko'rsatkichlari UI'da** | ADR-0019. «Tejaldi», «Kamaydi», narx statistikasi, hisobotdagi narx tarixi — olib tashlandi. Kelishuv qoladi, lekin **faqat sodir bo'ladigan joyda**: admin kamaytirish oynasi, ustaning roziman/nizo kartasi, statuslar va bildirishnomalar. Hisob-kitob serverda joyida |

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
| `payment` | R4/P2 · R5 (`payable_amount` hisobi) · FIFO taqsimot · qisman to'lov · **avans (P7)**: ortiqcha to'lov → avans → yangi qarzga avtomatik · `void` → qarz va avans qaytadi · daftar balansi |
| `approval` | R1 · holat o'tishlari |
| `template` | Majburiy maydonlar · foto min/max · versiyalash (eski hisobot buzilmasin) |
| `role` | R3 (tayanch narx yopiqligi) · `kind` bo'yicha ruxsatlar · R8 |

## Yandex Fleet API (Faza 3) — tasdiqlangan cheklovlar

⚠️ **Fleet FAQAT O'QISH uchun** (egasining qarori, 2026-08-01): *raqam bo'yicha
mashina va haydovchi ma'lumotini olish*. Platforma Fleet'ga **hech narsa
yozmaydi** — status ham. Boshqa maqsadda ishlatilmaydi.

`driver_status_reporter` loyihasida 31 endpoint spec skanerlangan, **qayta
tekshirish shart emas**:

- Partner API'da **GPS / real-vaqt joylashuv YO'Q**
- **Фотоконтроль (ДКК) natijasi YO'Q**, reyting / "Приоритет" / brending ham yo'q
- **Rate-limit (429) real** — backoff + sahifalar orasida pauza majburiy
- Mashina statusi (`working` / `not_working` / `repairing` / `no_driver` /
  `pending`) — faqat **o'qiladi**, ma'lumot uchun
- Ishlatiladigan endpointlar: `POST /v1/parks/cars/list` va
  `POST /v1/parks/driver-profiles/list` (haydovchi ↔ mashina bog'lanishi shu
  javobdagi `car` maydonidan olinadi)
- Fleet o'chirilgan yoki javob bermasa — platforma **to'liq ishlaydi**
- ⚠️ Real parkda (2026-08-01): bitta raqamga **bir nechta** Fleet yozuvi bor
  (292 yozuv ↔ 164 raqam) → deterministik tanlov; «joriy haydovchi» esa
  API'dan **aniqlanmaydi** (bitta mashinada 71 ta faol profil) → noaniq bo'lsa
  **yozilmaydi**. Batafsil: `docs/03-integrations/01-yandex-fleet-api.md` §6a

## Ish uslubi

- **Har qadamdan keyin ishlaydigan holat.** "Hammasini yozib bo'lgach sinaymiz" —
  eng xavfli yondashuv
- **Birinchi kesim ingichka va uchidan-uchiga:** usta hisobot yuboradi → admin
  narxni kamaytiradi → usta rozi bo'ladi. Qatlamlarni birma-bir to'liq yozib
  chiqish (butun DB → butun API → butun UI) mumkin emas
- **Deploy birinchi kunda** — HTTPS, Telegram webhook va Mini App domeni
  kutilmagan muammolar manbai
- Foydalanuvchi bilan muloqot va barcha UI matnlari — **o'zbek tilida**

## Bot va Mini App doirasi (2026-08-01 qarori)

⭐ **Barcha AMALLAR — Mini App'da.** *«Botdan ham, Mini App'dan ham bir amalni
qilish odamni chalkashtiradi.»*

| Botda | Mini App'da |
|---|---|
| `/start` → telefon → bog'lash | **Boshqa hammasi** |
| Bildirishnomalar (+ yagona «🧩 Ochish» tugmasi) | hisobot, ko'rik, narx kelishuvi |
| `/til`, `/yordam`, `/app` | davr, eksport, arxiv, xodimlar, konstruktor |
| Excel'ni hujjat sifatida **yetkazish** | |

- Botda **handler yozmang** — `report`, `review`, `negotiation`, `stats`,
  `period` handlerlari ataylab o'chirilgan (~2100 qator)
- Kirish botda qoladi, chunki `initData` da **telefon raqami yo'q** — bu texnik
  cheklov, tanlov emas
- Bildirishnomada tez tugma yo'q: `kb.open_app(lang, submission_id)` →
  `?submission=<id>` bilan kartochkani ochadi

## Ochiq texnik xavf

`<input type="file" accept="image/*" capture="environment">` Telegram
WebView'ida (ayniqsa **iOS**) kamerani ochadimi — **hali sinalmagan**.

🔴 **Zaxira yo'l umuman qolmadi.** Botdagi foto oqimi Mini App qarori bilan
o'chgan edi; «🖼 Galereyadan» tugmasi esa ADR-0017 bilan **ataylab** olib
tashlandi (foto faqat kameradan). Ya'ni `capture` ishlamasa — **foto umuman
yuklab bo'lmaydi va ta'mir hisoboti yuborilmaydi**.

Shuning uchun real iOS qurilmada kamera sinovi — **bloklovchi**, birinchi
navbatdagi vazifa. Ishlamasa ADR-0017 qayta ko'rib chiqiladi.
