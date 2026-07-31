# NovaCore Employee Platform

> 📄 **Repo holati:** Faza 1 (MVP) backend + **to'liq ishlaydigan Telegram bot**
> yozilgan (`backend/`). Hujjatlar — yagona haqiqat manbai va texnik topshiriq.
> Ishga tushirish: [Tez boshlash](#tez-boshlash) · Reja:
> [docs/05-delivery/01-roadmap.md](docs/05-delivery/01-roadmap.md)

**NovaCore** — Toshkent shahridagi yirik Yandex taksopark. Park o'z haydovchilariga
Comfort / Comfort+ tarifida ishlash uchun **o'ziga qarashli elektromobillarni** beradi
va haydovchilarga **oylik maosh** to'laydi. Parkning ~150 mashinasini **o'z ustalari**
(4–5 kishi, o'z ustaxonalarida) ta'mirlaydi.

**NovaCore Employee Platform** — Telegram bot + Mini App ko'rinishidagi ichki platforma.
Maqsadi: xodimlarning ishini **hujjatlashtirilgan, tekshiriladigan va raqamlar bilan
o'lchanadigan** holga keltirish.

---

## Ikkita asosiy g'oya

### ⭐ 1. Narx kelishuvi — platformaning yuragi

Usta har ish uchun to'lov oladi va **narxni o'zi taklif qiladi**; admin uni
ko'rib chiqadi va **kelishib kamaytirishi** mumkin. Bugun bu savdolashuv
og'zaki (yuzma-yuz) ketadi va hech qayerda qolmaydi.

Platforma uni raqamlashtiradi: kim qancha so'radi, admin qancha taklif qildi,
nima uchun, usta rozi bo'ldimi — hammasi yoziladi va o'lchanadi.
Natija: **"bu oy kelishuv X so'm tejadi"** degan aniq raqam.

📄 [04-flows/04-price-negotiation.md](docs/04-flows/04-price-negotiation.md)

### ⭐ 2. Rol = nom, ruxsat to'plami emas

NovaCore'da barcha xodimlar bir xil ishni qiladi: **rasmga oladi → izoh yozadi →
narx qo'yadi → hisobot yuboradi**. Hatto admin ham. Farq faqat **nomda** va
**qaysi shablon bilan ishlashida**.

Shuning uchun katta ruxsat matritsasi yo'q. Uch tur bor (`reporter` / `admin` /
`accountant`), nomlar esa cheksiz — **admin ularni o'zi yaratadi** (Usta,
Ta'minotchi, Elektrik, Yuvuvchi…), kod yozmasdan.

📄 [01-product/01-roles-and-permissions.md](docs/01-product/01-roles-and-permissions.md)

---

## Hujjatlar tuzilmasi

### 📦 01. Mahsulot (PRD / funksional talablar)
| Hujjat | Nima haqida |
|---|---|
| [00. Umumiy ko'rinish va glossariy](docs/01-product/00-overview.md) | Biznes konteksti, muammo, maqsad, KPI, atamalar |
| [01. Rollar va ruxsatlar](docs/01-product/01-roles-and-permissions.md) ⭐ | **Rol = nom** modeli |
| [02. Xodim hisobot oqimi](docs/01-product/02-employee-flow.md) | Mashina keldi → ish → ketdi → hisobot |
| [03. Admin oqimi](docs/01-product/03-admin-flow.md) | Ko'rib chiqish, **narx kelishuvi**, rol yaratish |
| [04. Rollar va shablonlar konstruktori](docs/01-product/04-roles-and-templates.md) | Kod yozmasdan yangi rol qo'shish |
| [05. Ta'minotchi roli](docs/01-product/05-supplier-role.md) | Ehtiyot qism xaridi (rol nomi misolida) |

### 🏗 02. Arxitektura
| Hujjat | Nima haqida |
|---|---|
| [01. Tizim arxitekturasi](docs/02-architecture/01-system-architecture.md) | fly.io, bitta process, Redis'siz |
| [02. Ma'lumotlar modeli (ER)](docs/02-architecture/02-data-model.md) | ~15 jadval, filialsiz, zayavkasiz |
| [03. Hisobot shablonlari](docs/02-architecture/03-report-templates.md) | Form konstruktor — yadro abstraksiya |
| [04. API dizayni](docs/02-architecture/04-api-design.md) | REST endpointlar, xatolar |
| [05. Holat mashinalari](docs/02-architecture/05-state-machines.md) | Hisobot, mashina, davr |
| [06. Xavfsizlik](docs/02-architecture/06-security.md) | initData auth, `role.kind`, audit |

### 🔌 03. Integratsiyalar
| Hujjat | Nima haqida |
|---|---|
| [01. Yandex Fleet API](docs/03-integrations/01-yandex-fleet-api.md) | Mashina sinxroni, `repairing` statusi |
| [02. Telegram bot + Mini App](docs/03-integrations/02-telegram-bot-miniapp.md) | Bitta bot, ekranlar, texnik cheklovlar |
| [03. Media va saqlash](docs/03-integrations/03-media-and-storage.md) | Foto yuklash, siqish, Tigris |

### 🔄 04. Jarayonlar
| Hujjat | Nima haqida |
|---|---|
| [01. Ta'mir hayotiy sikli](docs/04-flows/01-repair-lifecycle.md) | Mashina keldi → to'lovgacha |
| [02. Firibgarlikka qarshi nazorat](docs/04-flows/02-antifraud.md) | Qaysi teshiklarni yopamiz |
| [03. Hisob-kitob va analitika](docs/04-flows/03-payroll-and-reports.md) | Oy yopilishi, to'lovlar, hisobotlar |
| [**04. Narx kelishuvi**](docs/04-flows/04-price-negotiation.md) ⭐ | **Asosiy nazorat mexanizmi** |

### 🚀 05. Yetkazib berish
| Hujjat | Nima haqida |
|---|---|
| [01. Roadmap](docs/05-delivery/01-roadmap.md) | Fazalar, AI bilan ishlash tartibi, testlar |
| [02. Qarorlar va ochiq savollar](docs/05-delivery/02-open-questions.md) | A-01…A-25 registri |
| [03. Arxitektura qarorlari (ADR)](docs/05-delivery/03-decisions.md) | 13 ta ADR |

---

## Texnologiya steki

| Qatlam | Texnologiya | Izoh |
|---|---|---|
| **Backend + bot** | Python 3.12 · FastAPI + aiogram 3 | **Bitta process**, bitta ASGI ilova |
| **DB** | PostgreSQL (Fly Postgres) | JSONB — dinamik shablonlar |
| **Media** | Tigris (fly.io S3-mos ombori) | Telegram `file_id` — faqat kesh |
| **Fon vazifalari** | asyncio loop + Postgres outbox | **Redis kerak emas** |
| **Mini App** | React + TS + Vite + `@telegram-apps/*` | 4 ta ekran, tayyor UI kit |
| **Deploy** | fly.io (Docker) | ~$10–25/oy |

> Arxitektura **ataylab kichik**: 150 mashina, 4–5 usta, kuniga 3–5 hisobot,
> RPS < 1. Redis, worker, mikroservis — foydasiz murakkablik bo'lardi.

---

## Tez boshlash

```bash
make install                 # python3.12 venv + bog'liqliklar
cp backend/.env.example backend/.env   # BOT_TOKEN ni yozing (BotFather)
make demo                    # seed: rollar, shablonlar, ish turlari + 3 mashina
cd backend && python manage.py employee-add "Admin A." +998901234567 admin
make run                     # bot (polling) + API bitta process'da
make test                    # 74 ta domen va bot testi
```

Telegram'da botga `/start` → telefon raqamini yuborish → menyu ochiladi.

**Postgres bilan (compose):** `make compose-up` · **Prod:** `fly deploy`
(webhook rejimi, `fly secrets set BOT_TOKEN=… JWT_SECRET=… WEBHOOK_SECRET=…`).

Batafsil: [backend/README.md](backend/README.md)

### Bot nima qila oladi (Faza 1)

| Rol | Imkoniyatlar |
|---|---|
| **Usta** (`reporter`) | 🚗 Mashina keldi → shablon bo'yicha ketma-ket forma (foto, probeg, muammo, **ishlar + o'z narxi**) → 🚙 Mashina ketdi → 📤 Yuborish · narx taklifiga ✅/❌ javob · `/mening`, `/hisob`, `/kelishuv` |
| **Admin** | ⏳ Tasdiq navbati · kartochkada **tarixiy narx statistikasi** · ✅ tasdiqlash · ✏️ narxni kamaytirish (sabab majburiy) · ↩️ qaytarish · ❌ rad etish · `/kunlik`, `/davr`, `/eksport` · o'z hisoboti **avtomatik tasdiqlanadi** (R1a) |
| **Buxgalter** | Davr precheck, oyni yopish, to'lov varaqalari, Excel eksport |

Fon sikli: 48 soatlik avtomatik rozilik, 24 soatlik eslatmalar, bildirishnoma
outbox'i, uzoq downtime signali.

---

## Loyiha holati

| | |
|---|---|
| **Versiya** | 1.0 (Faza 1 — MVP) |
| **Bosqich** | Backend + bot yozilgan · Mini App (React) — keyingi qadam |
| **Sana** | 2026-07-31 |
| **Kodni kim yozadi** | **AI** (egasi yo'naltiradi va tekshiradi) |
| **Testlar** | 74 ta (pricing · approval · period · template · role · submission · bot e2e) |

> ⚠️ **Bu hujjatlar to'plami — texnik topshiriq.** Kodni AI yozgani uchun
> kontekst hujjatlarda bo'lishi shart: noaniq hujjat → noto'g'ri kod.
> Har faza boshida tegishli hujjatlar to'liq beriladi.

### Keyingi qadamlar

1. ⚙️ **Deploy** — fly.io app + Postgres + Tigris, webhook (`BOT_MODE=webhook`)
2. 📋 **Real ma'lumot** — mashina reyestri (`manage.py vehicles-load fleet.csv`),
   xodimlar, ish turlari uchun tayanch narxlar (faqat admin ko'radi)
3. 🧪 **Pilot** — 2 usta + admin, 1–2 hafta (roadmap §6)
4. 🧩 **Mini App** (React + TS) — bot to'liq ishlaydi, Mini App uni tezlashtiradi;
   backend API (`/api/v1`, initData auth) allaqachon tayyor
5. 🔬 **Kamera sinovi** — `capture="environment"` Mini App'da (A-10 ochiq xavf);
   botda foto oqimi zaxira sifatida allaqachon ishlaydi
6. 🔌 **Faza 3** — Yandex Fleet sinxroni, anti-fraud bayroqlari
   (`ANTIFRAUD_ENABLED=true` bilan yoqiladi)

Batafsil: [05-delivery/01-roadmap.md](docs/05-delivery/01-roadmap.md)
