# 06. Xavfsizlik

## 1. Tahdid modeli — kimdan himoyalanamiz

| # | Tahdid | Ehtimollik | Ta'siri | Choralar |
|---|---|---|---|---|
| T1 | **Ichki firibgarlik** — soxta hisobot, shishirilgan narx | 🔴 Yuqori | 🔴 Katta | Narx kelishuvi, foto talablari, anti-fraud bayroqlar, audit |
| T2 | **Begona odam tizimga kirishi** | 🟡 O'rta | 🔴 Katta | Reyestr + telefon tasdig'i, initData HMAC |
| T3 | **Rolni chetlab o'tish** (usta admin API'ga so'rov) | 🟡 O'rta | 🔴 Katta | Serverda `role.kind` tekshiruvi, klientga ishonmaslik |
| T3a | **Tayanch narxni ko'rib olish** (usta API'dan) | 🟡 O'rta | 🟡 O'rta | `reference_price` `reporter` javobidan **serverda** chiqarib tashlanadi |
| T4 | **Maosh/moliya ma'lumoti sizishi** | 🟡 O'rta | 🟡 O'rta | `role.kind` tekshiruvi, log'da maskalash |
| T5 | **Media URL'lari ochiq qolishi** | 🟡 O'rta | 🟡 O'rta | Signed URL, qisqa muddat, ochiq bucket yo'q |
| T6 | **Ma'lumot yo'qolishi** | 🟢 Past | 🔴 Katta | Backup + tiklashni sinash |
| T7 | **Bot token o'g'irlanishi** | 🟢 Past | 🔴 Katta | Secret boshqaruvi, repoda yo'q, rotatsiya rejasi |
| T8 | **Qonun buzilishi** (shaxsiy ma'lumot) | 🟡 O'rta | 🔴 Katta | Minimal ma'lumot, ko'chirish osonligi (7-bo'lim) |

> Bu loyihada **eng katta xavf — tashqi haker emas, ichki firibgarlik**.
> Shuning uchun anti-fraud alohida hujjatga chiqarilgan:
> [04-flows/02-antifraud.md](../04-flows/02-antifraud.md)

## 2. Telegram Mini App autentifikatsiyasi

### initData tekshiruvi

Telegram Mini App ochilganda `window.Telegram.WebApp.initData` beriladi — bu
imzolangan string. **Serverda majburiy tekshiriladi:**

```python
# Konseptual algoritm (Telegram rasmiy sxemasi)
# 1. initData'ni parse qilamiz, `hash` ni ajratamiz
# 2. Qolgan kalitlarni alifbo bo'yicha "key=value\n" ko'rinishida yig'amiz
# 3. secret_key = HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
# 4. calculated = HMAC_SHA256(key=secret_key, msg=data_check_string)
# 5. hmac.compare_digest(calculated, hash)  ← doimiy vaqtli solishtirish
# 6. auth_date yangimi? (now - auth_date < 3600 s)
```

**Qattiq qoidalar:**
- ❌ initData'dan `user.id` ni **tekshirmasdan** ishlatish taqiqlanadi
- ✅ `auth_date` eskirgan bo'lsa rad etiladi (replay hujumidan himoya)
- ✅ `hmac.compare_digest` — oddiy `==` emas (timing attack)
- ✅ Bot token faqat serverda, **hech qachon frontendda emas**
- ✅ Tekshiruvdan keyin o'z **qisqa muddatli JWT** beriladi; initData har so'rovda
  qayta yuborilmaydi

### JWT

| Token | Muddat | Saqlanish | Izoh |
|---|---|---|---|
| `access_token` | 15 daqiqa | Xotirada (localStorage emas) | `employee_id`, `role_code`, `role_kind` |
| `refresh_token` | 30 kun | `sessionStorage` / xotira | DB'da saqlanadi, bekor qilish mumkin |

- Rol o'zgarsa → barcha refresh tokenlar bekor qilinadi
- Xodim `blocked`/`fired` bo'lsa → tokenlar darhol bekor
- Token ichidagi `role_kind` — **kesh**, server baribir har so'rovda tekshiradi

## 3. Ro'yxatdan o'tish va identifikatsiya

```
/start
  ↓
"Telefon raqamingizni yuboring" [📱 Raqamni yuborish]  ← request_contact
  ↓
contact.user_id == message.from.id ?     ← ❗MUHIM
  ├─ Yo'q → rad etiladi (boshqa odamning raqami)
  └─ Ha  → normalizatsiya (+998XXXXXXXXX)
              ↓
        employees jadvalida bormi?
          ├─ Yo'q → "Ro'yxatda yo'qsiz. Adminga murojaat qiling."
          └─ Ha  → tg_user_id biriktiriladi (bir marta)
                     ↓
                   audit_log yoziladi
```

**Nima uchun `contact.user_id == from.id` tekshiruvi kerak:** Telegram'da
kontaktni forward qilib boshqa odamning raqamini yuborish mumkin. Bu tekshiruvsiz
xodim boshqa xodimning akkauntini "egallab" olishi mumkin edi.

**`tg_user_id` almashtirish** (telefon o'zgardi, akkaunt yo'qoldi):
faqat admin, sabab bilan, audit log'ga yozilib.

## 4. Ruxsatlar (RBAC) — serverda

```python
# Har bir endpointda:
@router.post("/submissions/{id}/approve")
async def approve(id: int, actor = Depends(require_kind("admin"))):
    sub = await get_submission(id)
    ensure_not_self_approval(actor, sub.author_id)  # R1 qoidasi
    ensure_period_open(sub.period_id)               # R4
    ...
```

**Ikki darajali tekshiruv** (rol modeli sodda bo'lgani uchun):
1. **`role.kind`** — `reporter` / `admin` / `accountant`
2. **Biznes qoida** — o'z hisobotimi (R1), davr ochiqmi (R4), holat mos keladimi

> Filial ko'lami **yo'q** — [rol modeli](../01-product/01-roles-and-permissions.md#8-filial-branch-tushunchasi--yoq).

> ❗ Mini App'dagi tugmalarni yashirish — **UX**, xavfsizlik emas.
> API baribir hamma narsani qayta tekshiradi.

### Ataylab qilingan yagona ochiqlik: `GET /submissions/linkable`

Ta'minotchi qism xaridini **ustaning** ta'mir hisobotiga biriktiradi
(`submission_picker`, Faza 2) — demak u o'zi muallif bo'lmagan hisobotni
ko'rishi kerak. Ochiqlik quyidagicha cheklangan:

| Cheklov | Nima uchun |
|---|---|
| `reporter` uchun `vehicle_id` **majburiy** | Butun bazani varaqlab chiqa olmaydi |
| `DRAFT` hisobotlar chiqmaydi | Tugallanmagan ish ko'rinmaydi |
| Javobda **summa yo'q** — faqat raqam, mashina, muallif, sana | R3 ruhi saqlanadi: narx ma'lumoti `reporter`ga berilmaydi |

To'liq kartochkani (`GET /submissions/{id}`) ochish huquqi o'zgarmagan —
u yerda `ensure_can_view_submission` ishlaydi.

## 5. Media xavfsizligi

| Chora | Tafsilot |
|---|---|
| Ochiq bucket yo'q | Tigris (S3-mos) — private, faqat signed URL |
| Signed URL muddati | 15 daqiqa |
| MIME tekshiruvi | Kengaytmaga emas, **fayl mazmuniga** qarab (magic bytes) |
| Hajm limiti | Foto 10 MB, video 50 MB (yuklashdan oldin siqiladi) |
| Ruxsat | Media faqat bog'langan hisobotni ko'ra oladigan xodimga |
| Zararli fayl | Faqat `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `application/pdf` |
| Qayta ishlash | Rasm serverda qayta kodlanadi (EXIF metadata bazaga ko'chib, fayldan tozalanadi) |

## 6. Maxfiy ma'lumotlar (secrets)

| Nima | Qayerda | Qoida |
|---|---|---|
| `BOT_TOKEN` | Env / secret manager | Repoda yo'q, `.gitignore` |
| `YANDEX_FLEET_API_KEY` | Env | `driver_status_reporter`dagi kabi |
| DB parol | Env | |
| JWT `SECRET_KEY` | Env | ≥ 32 bayt tasodifiy |
| S3 kalitlari | Env | |

- `.env.example` — repoda (qiymatsiz), `.env` — repoda **yo'q**
- Log'larda token/parol **maskalanadi**
- Rotatsiya rejasi: bot token va API kalitlari yiliga 1 marta yoki hodisa yuz berganda

## 7. Shaxsiy ma'lumotlar va qonunchilik

Platformada saqlanadigan shaxsiy ma'lumotlar:

| Ma'lumot | Zarurmi | Izoh |
|---|---|---|
| FIO | ✅ | Hisobot identifikatsiyasi |
| Telefon | ✅ | Autentifikatsiya |
| Telegram ID / username | ✅ | Kanal |
| Rol, ustaxona nomi, ishga kirgan sana | ✅ | Ish jarayoni |
| Ish haqi / to'lovlar | ✅ | Asosiy funksiya |
| Geolokatsiya | ⚠️ | Faqat hisobot yuborilgan payt, doimiy kuzatuv **yo'q** |
| Passport / JSHSHIR | ❌ | **Saqlanmaydi** — kerak emas |
| Foto (yuz) | ⚠️ | Maqsad — mashina fotosi; odam tushib qolishi mumkin |

### Amaliy qoidalar

1. **Minimallik** — kerak bo'lmagan ma'lumot yig'ilmaydi (passport, JSHSHIR yo'q)
2. **Maqsadlilik** — geolokatsiya faqat hisobot yuborilgan lahzada, doimiy trekingsiz
3. **Xabardorlik** — xodimlar tizimga kirishda nima yig'ilishini biladi
   (birinchi `/start` da qisqa matn + rozilik tugmasi)
4. **Saqlash muddati** — ishdan bo'shagandan keyin N yil (yurist bilan belgilanadi)
5. **Kirish nazorati** — maosh ma'lumoti faqat tegishli rollarga

### ⚠️ Ma'lumot lokalizatsiyasi — qabul qilingan xavf

Hosting **fly.io**da bo'ladi (qaror qabul qilingan —
[A-12](../05-delivery/02-open-questions.md)). O'zbekiston qonunchiligi
fuqarolarning shaxsiy ma'lumotlarini mamlakat hududida saqlashni talab qiladi;
fly.io serverlari chet elda.

Bu **loyiha egasining qabul qilgan xavfi**. Ta'sirni kamaytirish choralari:

| Chora | Tafsilot |
|---|---|
| **Minimal ma'lumot** | Faqat FIO, telefon, Telegram ID. Passport/JSHSHIR/manzil **yo'q** |
| **Ko'chirish osonligi** | Hech qanday fly.io'ga xos xususiyat ishlatilmaydi — oddiy Docker + Postgres + S3. Kerak bo'lsa UZ hostingga ko'chirish bir necha soatlik ish |
| **Shifrlash** | DB va S3 — provayder darajasida shifrlangan (at rest) |
| **Telegram** | Bot xabarlarida ortiqcha shaxsiy ma'lumot yuborilmaydi |

## 8. Audit

Quyidagilar **majburiy** audit log'ga yoziladi:

| Kategoriya | Hodisalar |
|---|---|
| Autentifikatsiya | Kirish, muvaffaqiyatsiz urinish, `tg_user_id` biriktirish/almashtirish |
| Ruxsat | Rol berish/olib tashlash, ruxsat o'zgarishi |
| Moliya | Tasdiqlash, rad etish, summa o'zgarishi, to'lov varaqasi tuzatish |
| Davr | Yopish, qayta ochish |
| Spravochnik | Narxnoma o'zgarishi, mashina qo'shish/o'chirish |
| Shablon | Nashr qilish, maydon o'zgarishi |
| Bayroq | Hal qilish (`false_positive` deb belgilash) |

Audit yozuvi: **kim, qachon, nima, qanday qiymatdan qanday qiymatga, qaysi IP/TG ID**.

**Audit o'chirilmaydi va tahrirlanmaydi.** Bu texnik cheklov sifatida ham qo'yiladi
(alohida rol, `REVOKE DELETE/UPDATE`).

## 9. Xavfsizlik amaliyotlari (dev)

| Amaliyot | Izoh |
|---|---|
| Bog'liqliklarni skanerlash | `pip-audit` / Dependabot — CI'da |
| SQL injection | Faqat ORM / parametrlashtirilgan so'rovlar |
| XSS | Mini App — React (avtomatik escape), `dangerouslySetInnerHTML` taqiqlanadi |
| CSRF | JWT header orqali (cookie emas) → CSRF muammosi yo'q |
| CORS | Faqat Mini App domeni |
| HTTPS | Majburiy (Telegram Mini App shartsiz HTTPS talab qiladi) |
| Sirlarni tekshirish | `gitleaks` pre-commit hook |
| Log'lar | Shaxsiy ma'lumot va tokenlar maskalanadi |

---

**Keyingi:** [03-integrations/01-yandex-fleet-api.md](../03-integrations/01-yandex-fleet-api.md)
