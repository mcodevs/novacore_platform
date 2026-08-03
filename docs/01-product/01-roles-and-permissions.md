# 01. Rollar va ruxsatlar

> ⚠️ **Bu hujjat NovaCore'ning o'ziga xos rol modelini tasvirlaydi.** U odatiy
> RBAC'dan farq qiladi va butun arxitekturani soddalashtiradi — avval shu
> bo'limni o'qing.

## 1. Asosiy g'oya: rol — bu **nom**, ruxsat to'plami emas

NovaCore'da barcha xodimlar **bir xil ishni** qiladi:

> rasmga oladi → izoh yozadi → narx qo'yadi → hisobot yuboradi

Usta ham, ta'minotchi ham, yuvuvchi ham — hammasi shu. Hatto **admin ham** shu
imkoniyatlarga ega. Farq faqat **nomda** va **qaysi shablon bilan ishlashida**.

```
                    ┌──────────────────────────────────┐
                    │   BAZAVIY IMKONIYAT (hammada)    │
                    │                                  │
                    │   📷 rasmga olish                │
                    │   💬 izoh yozish                 │
                    │   💰 narx qo'yish                │
                    │   📤 hisobot yuborish            │
                    │   ✅ narx kelishuviga javob      │
                    │   👁 o'z hisobotlarini ko'rish   │
                    └────────────────┬─────────────────┘
                                     │
         ┌──────────┬────────────────┼────────────────┬──────────┐
         ▼          ▼                ▼                ▼          ▼
    ┌────────┐ ┌──────────┐  ┌────────────┐  ┌──────────┐ ┌──────────┐
    │ "Usta" │ │"Ta'minot-│  │ "Yuvuvchi" │  │"Elektrik"│ │ ... admin│
    │        │ │  chi"    │  │            │  │          │ │ yaratgan │
    └────────┘ └──────────┘  └────────────┘  └──────────┘ └──────────┘

    Bularning hammasi — FAQAT NOM. Ular bir xil dvigatelda ishlaydi.
    Admin istalgan paytda yangisini yaratadi.
```

**Amaliy natija:** yangi rol qo'shish = admin panelda nom yozish va shablon
tanlash. Kod yozilmaydi, deploy qilinmaydi, dasturchi chaqirilmaydi.

## 2. Rol turlari (`role.kind`)

Tizimda **faqat uchta** tur bor. Nomlar cheksiz, turlar uchta:

| Tur | Nima qiladi | Nechta bo'lishi mumkin |
|---|---|---|
| **`reporter`** | Hisobot yuboradi (bazaviy imkoniyat) | ♾ Cheksiz — admin yaratadi |
| **`admin`** | Ko'rib chiqadi, narx kelishadi, tasdiqlaydi, boshqaradi | 1–2 ta |
| **`accountant`** | Ko'radi, **qarzlarni to'laydi**, eksport qiladi | 1 ta |

Boshlang'ich (seed) rollar:

| Nom | Turi | Shablon |
|---|---|---|
| Usta | `reporter` | Ta'mir hisoboti |
| Ta'minotchi | `reporter` | Ehtiyot qism hisoboti |
| Admin | `admin` | Barchasi + ta'mir hisoboti (o'zi ham yozishi mumkin) |
| Buxgalter | `accountant` | — |

Keyin admin xohlagancha qo'shadi: *Elektrik, Yuvuvchi, Shinamontaj, Kuzovchi,
Dispetcher…* — har biri o'z shabloni bilan.

## 3. Rol nima belgilaydi

| Rol nimani belgilaydi | Rol nimani belgilamaydi |
|---|---|
| ✅ Ko'rinadigan **shablonlar** ro'yxati | ❌ Rasm olish imkoniyati (hammada bor) |
| ✅ Menyudagi **nom** va ikonka | ❌ Narx qo'yish imkoniyati (hammada bor) |
| ✅ Hisobotlar qanday **guruhlanishi** | ❌ Izoh yozish (hammada bor) |
| ✅ To'lov varaqasida qanday **ko'rsatilishi** | ❌ Ma'lumot ko'lami (filial yo'q) |

## 4. Ruxsatlar — soddalashtirilgan

Katta ruxsat matritsasi **kerak emas**. Faqat quyidagilar:

| Amal | reporter | admin | accountant |
|---|:--:|:--:|:--:|
| Hisobot yaratish / yuborish | ✅ | ✅¹ | — |
| Foto, izoh, narx qo'yish | ✅ | ✅ | — |
| **O'z** hisobotlarini ko'rish | ✅ | ✅ | ✅ |
| **Barcha** hisobotlarni ko'rish | — | ✅ | ✅ |
| Narx kelishuviga rozilik/nizo | ✅ (o'ziniki) | — ¹ | — |
| **Narxni kamaytirish** | — | ✅ | — |
| **Narx tarixi va tayanch narx** | ❌² | ✅ | ✅ |
| **Tasdiqlash / rad etish / qaytarish** | — | ✅ | — |
| O'z narx statistikasi | ✅³ | ✅ | ✅ |
| Mashina reyestri (yozish) | — | ✅ | — |
| Xodim qo'shish, rol berish | — | ✅ | — |
| **Yangi rol yaratish** | — | ✅ | — |
| Shablon yaratish / tahrirlash | — | ✅ | — |
| Ish turlari + tayanch narx | — | ✅ | — |
| **Qarzlarni ko'rish (kimga qancha)** | — | ✅ | ✅ |
| **To'lov qilish** (to'liq / qisman / FIFO) | — | ✅ | ✅ |
| **To'lovni bekor qilish** (`void`, sabab bilan) | — | ✅ | ✅ |
| Eksport (Excel) | — | ✅ | ✅ |
| Audit log | — | ✅ | — |

¹ Admin hisoboti **avtomatik tasdiqlanadi** — tasdiqlash va narx kelishuvi
bosqichlaridan o'tmaydi (R1a).
² **Ataylab yopiq:** tayanch narx `reporter`ga ko'rsatilmaydi — aks holda barcha
narxlar tayanchga yopishadi va kelishuv ma'nosini yo'qotadi
([ADR-0009](../05-delivery/03-decisions.md)).
³ Xodim **o'zining** "narxim necha % kamaytirilgan" statistikasini ko'radi
(boshqalarnikini emas) — bu o'z-o'zini tuzatishga undaydi.

## 5. Qattiq qoidalar (serverda tekshiriladi)

| # | Qoida | Sabab |
|---|---|---|
| R1 | **Muallif o'z hisobotini tasdiqlay olmaydi** (`approver_id ≠ author_id`) | Manfaatlar to'qnashuvi |
| R1a | **`admin` turidagi muallifning hisoboti tizim tomonidan avtomatik tasdiqlanadi** | Adminga tasdiqlovchi kerak emas ([A-25](../05-delivery/02-open-questions.md)) |
| R2 | **Admin narxni faqat kamaytira oladi**, oshira olmaydi | Til biriktirib summa ko'tarishning oldini olish |
| R3 | Tasdiqlangan hisobot tahrirlanmaydi — faqat `reopen` orqali | Audit yaxlitligi |
| R4 | **To'lov faqat `APPROVED` hisobotga; `paid_amount ≤ payable_amount`** | Ortiqcha to'lov bo'lmasin ([ADR-0015](../05-delivery/03-decisions.md#adr-0015--qarz-daftari-oy-yopish-orniga-hisobot-boyicha-tolov-)) |
| R5 | Xodim `fired` bo'lsa — kirish bloklanadi, ma'lumotlari qoladi | Ma'lumot yo'qolmasin |
| R6 | Bitta Telegram akkaunt = bitta xodim (`tg_user_id` unique) | Identifikatsiya |
| R7 | Rol/ruxsat o'zgarishi `audit_log`ga yoziladi | Nazorat |
| R8 | Kamida bitta `admin` turidagi rol egasi bo'lishi shart | O'zini qulflab qo'yishning oldini olish |

> **R1 va R1a birga ishlaydi:** hech kim o'z hisobotini **qo'lda** tasdiqlay
> olmaydi. Admin hisoboti esa **tizim tomonidan** avtomatik tasdiqlanadi —
> unga tasdiqlovchi kerak emas ([A-25](../05-delivery/02-open-questions.md)).
> Avtomatik tasdiqlangan hisobotlar `auto_approved` belgisi bilan alohida
> ko'rsatiladi va oylik hisobotda ayrim satr sifatida chiqadi.

## 6. Vazifalarni ajratish — qoida emas, shablon orqali

Oldingi versiyada "usta qism narxini kirita olmaydi" degan **qattiq texnik
cheklov** bor edi. Yangi modelda bu **shablon darajasida** hal qilinadi:

```
"Usta" roli   →  Ta'mir shabloni       →  faqat ish haqi qatorlari
"Ta'minotchi" →  Qism xaridi shabloni  →  qism nomi, narx, chek fotosi
```

Usta qism narxini kiritmaydi, chunki **uning shablonida bunday maydon yo'q** —
texnik taqiq emas, tuzilmaviy ajratish. Natija bir xil, lekin model ancha sodda
va admin uni istalgan paytda o'zgartira oladi.

## 7. Kirish va identifikatsiya

```
Telegram'da /start
      ↓
Telefon raqamini so'rash (request_contact tugmasi)
      ↓
contact.user_id == message.from.id ?     ← ❗ boshqa odamning raqamini oldini oladi
      ↓
Raqam `employees` reyestrida bormi?
      ├─ Yo'q  → "Siz ro'yxatda yo'qsiz, adminga murojaat qiling"
      └─ Ha    → tg_user_id biriktiriladi (bir marta) → rol yuklanadi
                       ↓
                 Roliga mos Mini App menyusi ochiladi
```

- **Xodim avval admin tomonidan reyestrga kiritiladi**, keyin o'zi bog'lanadi.
  O'z-o'zidan ro'yxatdan o'tish yo'q.
- Reyestrga kiritish — Mini App'dagi **«👥 Xodimlar»** ekrani (admin) yoki
  `manage.py employee-add`. Ekranda kim bog'langani (`🔗`), kim kutayotgani
  (`⏳`) ko'rinadi; shu yerdan rol beriladi va bloklash/bo'shatish qilinadi.
- ⚠️ Ikkinchi qadam **faqat botda** bo'ladi: Mini App telefon raqamini
  ko'rmaydi, shuning uchun bog'lanish `/start` → `request_contact` orqali.
- Telefon `+998XXXXXXXXX` ko'rinishida normalizatsiya qilinadi.
- `tg_user_id` almashtirish — faqat admin, sabab bilan, audit log'ga yozilib.

Texnik tafsilotlar: [02-architecture/06-security.md](../02-architecture/06-security.md)

## 8. Filial (branch) tushunchasi — YO'Q

NovaCore'da ustalar **o'z ustaxonalarida** ishlaydi va filialga biriktirilmaydi.
Shuning uchun:

- ❌ `branches` jadvali yo'q
- ❌ Filial bo'yicha ma'lumot ko'lami (scoping) yo'q — admin hammasini ko'radi
- ❌ Filial geofence'i yo'q
- ✅ Xodim profilida **ixtiyoriy** `workshop_name` va koordinata (ma'lumot uchun)

Bu tizimni sezilarli soddalashtiradi: 150 mashina, 4–5 usta, bitta admin uchun
filial qatlami ortiqcha murakkablik edi.

---

**Keyingi:** [02. Xodim hisobot oqimi](02-employee-flow.md) ·
[04. Rollar va shablonlar konstruktori](04-roles-and-templates.md)
