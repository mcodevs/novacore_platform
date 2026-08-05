# 01. Tizim arxitekturasi

## 1. Masshtab — arxitekturani belgilaydi

| Ko'rsatkich | Qiymat |
|---|---|
| Mashinalar | **~150** |
| Ustalar | **4–5** |
| Umumiy foydalanuvchilar | ~10–15 (usta, ta'minotchi, admin, buxgalter) |
| Kunlik hisobotlar | **3–5** |
| Kunlik fotolar | ~30–50 |
| Eng yuqori RPS | **< 1** |

> ⚠️ Bu **juda kichik tizim**. Shuning uchun arxitektura ataylab sodda:
> Redis yo'q, navbat serveri yo'q, mikroservis yo'q. Har qo'shimcha komponent —
> bu qo'shimcha nosozlik nuqtasi va foydasiz murakkablik.

## 2. Umumiy sxema

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│    Usta      │   │  Ta'minotchi │   │    Admin     │
│  (Telegram)  │   │  (Telegram)  │   │  (Telegram)  │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       └──────────┬───────┴──────────────────┘
                  │
      ┌───────────▼────────────┐        ┌──────────────────┐
      │   Telegram Bot API     │◄───────┤ Telegram Mini App│
      │   (webhook)            │        │ React + TS + Vite│
      └───────────┬────────────┘        └─────────┬────────┘
                  │                               │ HTTPS + initData
      ╔═══════════▼═══════════════════════════════▼════════════╗
      ║        NovaCore Platform — bitta Python ilova          ║
      ║                    (fly.io)                            ║
      ║                                                        ║
      ║  ┌───────────────────────────────────────────────┐     ║
      ║  │  FastAPI (ASGI)                               │     ║
      ║  │   ├── /api/v1/*      Mini App uchun REST      │     ║
      ║  │   ├── /tg/webhook    aiogram router           │     ║
      ║  │   └── /healthz                                │     ║
      ║  └───────────────────┬───────────────────────────┘     ║
      ║                      │                                 ║
      ║  ┌───────────────────▼───────────────────────────┐     ║
      ║  │  Domain                                       │     ║
      ║  │  ⭐ pricing (narx kelishuvi)                   │     ║
      ║  │  submission · template · role · approval      │     ║
      ║  │  payment (qarz daftari) · media · antifraud   │     ║
      ║  └───────────────────┬───────────────────────────┘     ║
      ║                      │                                 ║
      ║  ┌───────────────────▼───────────────────────────┐     ║
      ║  │  Background loop (asyncio, shu process ichida)│     ║
      ║  │  • notifications outbox                       │     ║
      ║  │  • foto qayta ishlash (thumbnail, pHash)      │     ║
      ║  │  • kunlik Fleet sinxron                       │     ║
      ║  │  • eslatmalar (48 soat, qoralama, oy oxiri)   │     ║
      ║  └───────────────────────────────────────────────┘     ║
      ╚════════════════╤═══════════════════╤═══════════════════╝
                       │                   │
             ┌─────────▼────────┐  ┌───────▼──────────┐
             │  Fly Postgres    │  │  Tigris (S3)     │
             │  asosiy baza     │  │  media ombori    │
             └──────────────────┘  └──────────────────┘
                       │
             ┌─────────▼──────────┐
             │  Yandex Fleet API  │  (kunlik sinxron)
             └────────────────────┘
```

## 3. Texnologiya steki

| Qatlam | Texnologiya | Sabab |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Mavjud tajriba (`driver_status_reporter`), avtomatik OpenAPI |
| **Bot** | aiogram 3 (FastAPI bilan **bir process**) | Async, bir ASGI ilovada birlashadi |
| **DB** | PostgreSQL (Fly Postgres) | JSONB — dinamik shablonlar uchun ideal |
| **ORM** | SQLAlchemy 2 + Alembic | |
| **Media** | **Tigris** (fly.io'ning S3-mos ombori) | fly.io bilan integratsiyalashgan, alohida provayder kerak emas |
| **Fon vazifalari** | asyncio loop + Postgres outbox | **Redis kerak emas** — kuniga ~50 xabar |
| **Mini App** | React 18 + TS + Vite + `@telegram-apps/*` | Telegram Mini App uchun standart yo'l |
| **Deploy** | fly.io (Docker) | Mavjud tajriba, `driver_status_reporter` shu yerda |

### Nima **YO'Q** va nima uchun

| Komponent | Nega kerak emas |
|---|---|
| ❌ Redis | Kuniga ~50 bildirishnoma — Postgres outbox yetadi |
| ❌ Celery / ARQ | Bitta asyncio loop yetadi |
| ❌ Alohida worker process | Yuk yo'q; bitta machine'da hammasi |
| ❌ Mikroservislar | 15 foydalanuvchi |
| ❌ CDN | 50 foto/kun |
| ❌ Kubernetes | fly.io o'zi boshqaradi |

> **Prinsip:** kodni AI yozadi, lekin **nosozlikni odam tuzatadi**. Har qo'shimcha
> komponent — bu tushunilishi kerak bo'lgan qo'shimcha qatlam. Sodda tizim
> uzoq yashaydi.

## 4. Kod tuzilmasi

```
novacore-platform/
├── backend/
│   ├── app/
│   │   ├── core/          # config, security, initData validatsiya
│   │   ├── db/            # SQLAlchemy modellar, sessiya
│   │   ├── domain/        # biznes mantiq (framework'dan mustaqil)
│   │   │   ├── pricing/       # ⭐ narx kelishuvi — eng ko'p test shu yerda
│   │   │   ├── submission/    # hisobot hayotiy sikli
│   │   │   ├── template/      # shablon dvigateli + validatsiya
│   │   │   ├── role/          # rol = nom modeli
│   │   │   ├── approval/
│   │   │   ├── antifraud/
│   │   │   ├── payment/      # qarz daftari: to'lov, FIFO, void
│   │   │   └── media/
│   │   ├── api/v1/        # FastAPI routerlar
│   │   ├── bot/           # aiogram handlerlar
│   │   ├── tasks/         # fon sikli
│   │   ├── integrations/
│   │   │   ├── fleet/     # Yandex Fleet API klienti
│   │   │   └── storage/   # Tigris / S3
│   │   └── seeds/         # boshlang'ich rollar va shablonlar (JSON)
│   ├── alembic/
│   └── tests/             # domain testlari — ustuvor
├── miniapp/               # React + TS
│   ├── src/
│   │   ├── screens/       # ro'yxat · forma · ko'rib chiqish · profil
│   │   ├── form-renderer/ # ⭐ shablon JSON → UI
│   │   ├── api/
│   │   └── i18n/          # uz + uz_cyrl + ru
└── fly.toml
```

> **`form-renderer`** — Mini App'ning yuragi. U shablon JSON'ini olib forma
> chizadi. Yangi rol/shablon = yangi kod emas.

## 5. Deploy (fly.io)

```
fly.io
├── app: novacore-platform
│   ├── 1 machine (shared-cpu-1x, 512 MB – 1 GB)
│   ├── HTTPS avtomatik (Telegram Mini App talabi)
│   └── secrets: BOT_TOKEN, YANDEX_FLEET_*, JWT_SECRET, DB_URL, S3_*
├── Fly Postgres (kichik instance + kunlik snapshot)
└── Tigris bucket (media, private)
```

Taxminiy narx: **$10–25/oy**.

### ⚠️ Ma'lumot lokalizatsiyasi — qabul qilingan xavf

Hosting **fly.io**da bo'ladi (qaror qabul qilingan). O'zbekiston qonunchiligi
fuqarolarning shaxsiy ma'lumotlarini mamlakat hududida saqlashni talab qiladi;
fly.io serverlari chet elda.

Bu **loyiha egasining qabul qilgan xavfi**. Ta'sirni kamaytirish uchun:
- Platformada **minimal shaxsiy ma'lumot**: FIO, telefon, Telegram ID.
  Passport, JSHSHIR, manzil **saqlanmaydi**
- Kerak bo'lsa keyinchalik ko'chirish oson bo'lishi uchun — hech qanday
  fly.io'ga xos xususiyat ishlatilmaydi (oddiy Docker + Postgres + S3)

Batafsil: [06-security.md](06-security.md#7-shaxsiy-malumotlar)

## 6. Muhitlar

| Muhit | Bot | DB |
|---|---|---|
| `local` | Alohida test bot | Docker postgres |
| `production` | Asosiy bot | Fly Postgres |

Staging **shart emas** — bu masshtabda ortiqcha. Xavfli o'zgarishlar lokal
muhitda sinaladi.

⚠️ Telegram bot bitta webhook URL'ga bog'lanadi — shuning uchun lokal va
production uchun **alohida bot** kerak.

## 7. Kuzatuv

| Nima | Qanday |
|---|---|
| Loglar | structlog → JSON → `fly logs` |
| Xatolar | Telegram admin guruhiga alert (`driver_status_reporter`dagi kabi) |
| Sog'liq | `/healthz` — fly.io tekshiradi |
| Biznes metrikalar | Admin dashboard |

Sentry ixtiyoriy — Telegram alert bu masshtabda yetadi.

## 8. Zaxira nusxa

| Nima | Qanday | Chastota |
|---|---|---|
| PostgreSQL | Fly Postgres snapshot + `pg_dump` → Tigris | Kuniga 1 |
| Media (Tigris) | Versiyalash yoqilgan | — |
| Tiklashni sinash | Dump'dan lokal bazaga tiklash | Oyiga 1 |

⚠️ **Tekshirilmagan backup — backup emas.**

---

**Keyingi:** [02. Ma'lumotlar modeli](02-data-model.md)
