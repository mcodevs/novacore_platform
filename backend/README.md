# NovaCore Platform — backend

FastAPI + aiogram 3 **bitta ASGI ilovada, bitta process** (ADR-0004).
Hujjatlar — [`../docs/`](../docs/) — yagona haqiqat manbai.

## Tuzilma

```
backend/
├── app/
│   ├── core/          config · i18n (uz/ru) · security (initData, JWT) · errors · phone · logging
│   ├── db/            SQLAlchemy 2 modellar (base.py — portativ tiplar), sessiya
│   ├── domain/        biznes mantiq — framework'dan mustaqil
│   │   ├── pricing/      ⭐ narx kelishuvi (R2, R2a, R2b, N1–N9)
│   │   ├── submission/   hisobot hayotiy sikli (arrived/left, submit)
│   │   ├── approval/     tasdiqlash (R1, R1a)
│   │   ├── template/     shablon dvigateli: sxema → forma → validatsiya → promoted
│   │   ├── role/         ruxsatlar (`role.kind` + biznes qoida, R3, R8)
│   │   ├── period/       davr, precheck, oy yopilishi (R4)
│   │   ├── payout/       to'lov varaqalari (R5)
│   │   ├── media/        foto saqlash, MIME sniffing, signed URL
│   │   ├── antifraud/    bayroqlar (Faza 1'da o'chirilgan)
│   │   ├── notify/       outbox
│   │   └── export/       Excel (openpyxl)
│   ├── api/v1/        REST — Mini App uchun (OpenAPI: /docs)
│   ├── bot/           aiogram handlerlar, klaviaturalar, matnlar, notifier
│   ├── tasks/         fon sikli (48 soat, eslatmalar, outbox)
│   ├── integrations/  storage (local | Tigris S3) · fleet (Faza 3)
│   └── seeds/         rollar, shablonlar, ish turlari — JSON
├── alembic/           migratsiyalar
└── tests/             domen + bot e2e testlari
```

## Ishga tushirish (lokal)

```bash
python3.12 -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt
cp .env.example .env          # BOT_TOKEN — BotFather'dan (lokal uchun ALOHIDA bot!)

python manage.py demo         # sxema + seed + 3 ta mashina
python manage.py employee-add "Admin A." +998901234567 admin
python manage.py employee-add "Karimov B." +998901234568 mechanic

uvicorn app.main:app --reload --port 8000
```

Lokal rejimda `DATABASE_URL=sqlite+aiosqlite:///./var/novacore.db` yetadi —
sxema va seed avtomatik yuklanadi. Postgres uchun `docker compose up`.

## Buyruqlar

| Buyruq | Nima qiladi |
|---|---|
| `python manage.py seed` | Rollar, shablonlar, ish turlari, qismlar, kategoriyalar |
| `python manage.py employee-add "F.I.Sh." +998… role` | Reyestrga xodim (keyin u `/start` bosadi) |
| `python manage.py employee-list` | Xodimlar va ular Telegram'ga bog'langanmi |
| `python manage.py vehicle-add 01A123BC BYD Chazor 2024` | Mashina |
| `python manage.py vehicles-load fleet.csv` | Reyestrni CSV'dan (Faza 0.3) |
| `python manage.py bot-info` | `getMe` + webhook holati |
| `python manage.py set-webhook` / `delete-webhook` | Prod ↔ lokal rejim |
| `pytest` | Testlar (majburiy) |
| `alembic upgrade head` | Migratsiya (Postgres) |

## Muhim qarorlar

- **Bot o'zi yetarli.** Butun oqim chatda ishlaydi: forma, foto, narx, kelishuv,
  tasdiqlash, eksport. Mini App — tezlashtiruvchi qatlam, majburiy emas.
- **Shablon dvigateli.** Yangi rol/shablon = `app/seeds/templates/*.json`,
  kod yozilmaydi. `next_field()` formani ketma-ket chizadi (bot uchun ham,
  Mini App uchun ham bir xil sxema).
- **Summalar serverda.** `recalculate_amounts()` har doim `submission_lines`dan
  hisoblaydi — klient yuborgan summaga ishonilmaydi (R7).
- **`proposed_*` immutable.** Kelishuv faqat `approved_*` ni o'zgartiradi (R2a),
  DB darajasida `CHECK` bilan qulflangan (R2, R2b).
- **Tayanch narx.** `reference_price` va narx tarixi `reporter` javobidan
  **serverda** chiqarib tashlanadi (R3) — `serializers.work_catalog_out`,
  `pricing.price_context`.
- **SQLite** faqat lokal ishlash va testlar uchun; modellar `with_variant`
  orqali PG/SQLite ikkalasiga mos. Prod — PostgreSQL.

## Testlar

```bash
pytest                      # 74 ta
pytest tests/test_pricing.py -v
```

| Fayl | Nima tekshiriladi |
|---|---|
| `test_pricing.py` | R2 · R2a · R2b · 48 soat avtomatik rozilik · nizo · R1a · R3 · statistika |
| `test_approval.py` | R1 · holat o'tishlari · reopen kelishuvni bekor qiladi |
| `test_period.py` | R4 · precheck · to'lov `approved_amount` bo'yicha (R5) |
| `test_template.py` | Majburiy maydonlar · foto min/max · versiyalash · promoted ustunlar |
| `test_role.py` | R3 · `kind` ruxsatlari · R8 · yangi rol kodsiz qo'shiladi |
| `test_submission.py` | `arrived_at`/`left_at` · probeg monotonligi · raqamlash · soft delete |
| `test_bot_flow.py` | **Uchidan-uchiga bot oqimi** soxta Telegram sessiyasi bilan |

## Deploy (fly.io)

```bash
fly secrets set BOT_TOKEN=… JWT_SECRET=… WEBHOOK_SECRET=… \
                S3_ACCESS_KEY=… S3_SECRET_KEY=…
fly deploy                     # Dockerfile: alembic → seed → uvicorn
```

`BOT_MODE=webhook` bo'lsa ilova ishga tushganda webhook o'zi o'rnatiladi
(`BASE_URL` + `/tg/webhook`, `WEBHOOK_SECRET` bilan tekshiriladi).
