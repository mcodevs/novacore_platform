# 03. Hisobot shablonlari (form konstruktor)

> Bu — platformaning **yadro abstraksiyasi**. "Barcha xodimlar uchun birdek ishlashi
> kerak" talabi shu mexanizm bilan bajariladi.
> Mahsulot tomoni: [01-product/04-roles-and-templates.md](../01-product/04-roles-and-templates.md)

## 1. Prinsip

```
Shablon (konfiguratsiya)  ──►  Form Renderer  ──►  Mini App'dagi forma
        │                                                │
        │                                          to'ldiriladi
        ▼                                                ▼
   Validatsiya qoidalari  ◄────────────────────  Submission (jsonb + promoted)
        │
        ▼
   Tasdiqlash oqimi → Bayroqlar → Davr → To'lov → Analitika
   (bularning hammasi shablonga bog'liq emas — yadro)
```

**Bitta form renderer, bitta tasdiqlash oqimi, bitta analitika.**
Yangi rol = yangi JSON, yangi kod emas.

## 2. Shablon JSON strukturasi

```json
{
  "code": "car_repair",
  "name": { "uz": "Ta'mir hisoboti", "ru": "Отчёт о ремонте" },
  "subject_type": "vehicle",
  "has_money": true,
  "negotiable": true,
  "version": 3,

  // ⚠️ "kim ko'radi" shablonda EMAS — `role_templates` jadvalida.
  // Tasdiqlovchi ham shablonda emas: har doim `kind='admin'` rolli xodim.

  "field_mapping": {
    "vehicle":       "plate",
    "labor_amount":  "@lines.labor",
    "parts_amount":  "@lines.part",
    "odometer":      "odometer_value",
    "started_at":    "@auto.first_save",
    "finished_at":   "@auto.submit"
  },

  "sections": [
    { "code": "identify", "title": { "uz": "Mashina", "ru": "Автомобиль" } },
    { "code": "before",   "title": { "uz": "Ta'mirgacha" } },
    { "code": "work",     "title": { "uz": "Bajarilgan ish" } },
    { "code": "after",    "title": { "uz": "Ta'mirdan keyin" } }
  ],

  "fields": [
    {
      "code": "plate",
      "section": "identify",
      "label": { "uz": "Mashina raqami", "ru": "Гос. номер" },
      "type": "vehicle_picker",
      "required": true
    },
    {
      "code": "photo_car_before",
      "section": "before",
      "label": { "uz": "Mashina (raqam ko'rinsin)" },
      "type": "photo",
      "required": true,
      "options": { "min": 1, "max": 2, "camera_only": true }
    },
    {
      "code": "odometer_photo",
      "section": "before",
      "label": { "uz": "Panel (probeg)" },
      "type": "photo",
      "required": true,
      "options": { "min": 1, "max": 1, "camera_only": true }
    },
    {
      "code": "odometer_value",
      "section": "before",
      "label": { "uz": "Probeg (km)" },
      "type": "number",
      "required": true,
      "validation": { "min": 0, "max": 999999, "monotonic_for_vehicle": true }
    },
    {
      "code": "category",
      "section": "before",
      "label": { "uz": "Nosozlik turi" },
      "type": "select",
      "required": true,
      "options": { "source": "catalog:fault_categories" }
    },
    {
      "code": "photo_problem",
      "section": "before",
      "label": { "uz": "Muammo fotosi" },
      "type": "photo",
      "required": true,
      "options": { "min": 1, "max": 5, "camera_only": true }
    },
    {
      "code": "works",
      "section": "work",
      "label": { "uz": "Bajarilgan ishlar" },
      "type": "lines",
      "required": true,
      "options": {
        "kind": "labor",
        "catalog": "work_catalog",
        "allow_custom": true,
        "price_source": "author",
        "hide_reference_price_from_author": true,
        "negotiable": true,
        "history_flag_threshold_pct": 30
      }
    },
    {
      "code": "parts",
      "section": "work",
      "label": { "uz": "Ishlatilgan qismlar" },
      "type": "lines",
      "required": false,
      "options": {
        "kind": "part",
        "catalog": "parts_catalog",
        "allow_custom": true,
        "price_field": false
      }
    },
    {
      "code": "photo_after",
      "section": "after",
      "label": { "uz": "Tuzatilgandan keyin" },
      "type": "photo",
      "required": true,
      "options": { "min": 1, "max": 5, "camera_only": true }
    },
    {
      "code": "comment",
      "section": "after",
      "label": { "uz": "Usta izohi" },
      "type": "textarea",
      "required": true,
      "validation": { "min_length": 10 }
    },
    {
      "code": "recommendation",
      "section": "after",
      "label": { "uz": "Tavsiya (keyingi ish)" },
      "type": "textarea",
      "required": false
    }
  ]
}
```

## 3. Maydon turlari — to'liq spetsifikatsiya

| `type` | `options` | Saqlanish (`data`) |
|---|---|---|
| `text` | `max_length` | `"matn"` |
| `textarea` | `min_length`, `max_length` | `"uzun matn"` |
| `number` | `min`, `max`, `step`, `monotonic_for_vehicle` | `48250` |
| `money` | `min`, `max` | `150000.00` |
| `bool` | — | `true` |
| `select` | `choices[]` yoki `source: "catalog:xxx"` | `"brakes"` |
| `multiselect` | shu bilan bir xil | `["a","b"]` |
| `date` / `datetime` | `min`, `max` | ISO string |
| `photo` | `min`, `max`, `camera_only`, `kind` | `[media_id, ...]` |
| `video` | `max_seconds` | `[media_id]` |
| `audio` | `max_seconds` | `[media_id]` |
| `file` | `accept[]`, `max_mb` | `[media_id]` |
| `vehicle_picker` | `only_active` | `{ "vehicle_id": 42 }` |
| `employee_picker` | `role_kinds[]`, `multiple` | `[7, 12]` |
| `catalog_picker` | `catalog` | `{ "id": 5, "name": "...", "price": ... }` |
| `geo` | `require_accuracy_m` | `{ "lat": .., "lon": .., "acc": 12 }` |
| `signature` | — | `[media_id]` |
| `lines` | `kind`, `catalog`, `allow_custom`, `price_field`, `hide_reference_price_from_author` | `submission_lines` jadvalida |
| `submission_picker` | `template_code`, `same_vehicle` | `{ "submission_id": 1247 }` |
| `computed` | `formula` | Serverda hisoblanadi |

## 4. `field_mapping` — dinamik va tipli o'rtasidagi ko'prik

Muammo: hisobot to'liq JSONB bo'lsa, "shu mashinaga bu oyda qancha sarflandi"
so'rovi og'ir va xatoga moyil bo'ladi.

Yechim: shablon o'z maydonlaridan qaysi biri **yadro tushunchasi** ekanini aytadi:

| Yadro tushunchasi | `field_mapping` kaliti | Qayerga yoziladi |
|---|---|---|
| Mashina | `vehicle` | `submissions.subject_vehicle_id` |
| Xodim (ob'ekt) | `employee` | `submissions.subject_employee_id` |
| **So'ralgan ish haqi** | `proposed_labor_amount` | `submissions.proposed_labor_amount` |
| **Tasdiqlangan ish haqi** | `labor_amount` | `submissions.labor_amount` |
| Material xarajati | `parts_amount` | `submissions.parts_amount` |
| Umumiy summa | `total_amount` | `submissions.total_amount` |
| Probeg | `odometer` | `submissions.odometer_km` |
| Boshlanish/tugash | `started_at` / `finished_at` | shu nomdagi ustunlar |

Maxsus qiymatlar:
- `@lines.labor.proposed` — `kind='labor'` qatorlarining **so'ralgan** yig'indisi
- `@lines.labor.approved` — **tasdiqlangan** yig'indi (to'lov asosi)
- `@lines.part` — `kind='part'` yig'indisi
- `@auto.first_save` — birinchi saqlash vaqti
- `@auto.submit` — yuborish vaqti

> ⚠️ **Muhim:** `has_money = true` va `negotiable = true` bo'lgan shablonlar
> avtomatik ravishda narx kelishuvi oqimiga tushadi (`PRICE_NEGOTIATION`
> holatlari). Bu yadro xususiyati — har shablon uchun qayta yozilmaydi.

Saqlash paytida yadro `field_mapping`ni o'qiydi va promoted ustunlarni to'ldiradi.
**Barcha analitika faqat promoted ustunlar bilan ishlaydi** — shablon o'zgarsa ham
hisobotlar buzilmaydi.

## 5. Versiyalash

Shablon o'zgarganda eski hisobotlar buzilmasligi kerak.

```
templates (joriy holat, version = 3)
template_versions (snapshot: version 1, 2, 3 — to'liq JSON)
submissions.template_version = 2   →  ko'rsatishda 2-versiya sxemasi ishlatiladi
```

Qoidalar:
- Shablon tahrirlanayotganda `draft` holatida bo'ladi, nashr etilganda `version++`
- Nashr etilgach o'sha versiya **o'zgarmas** (immutable)
- Eski hisobot ko'rsatilganda **o'z versiyasidagi** yorliqlar va maydonlar chiziladi
- Maydon o'chirilsa — eski hisobotda u baribir ko'rinadi (arxiv sifatida)

## 6. Validatsiya — server oxirgi hakam

```
Klient (Mini App)          Server (FastAPI)
    │                          │
    │ tez fikr-mulohaza        │ yagona haqiqat
    │ (UX uchun)               │ (xavfsizlik uchun)
    ▼                          ▼
 shu qoidalar               SHU QOIDALAR + qo'shimcha:
                              • rol ruxsati
                              • mashina reyestrda bormi
                              • davr ochiqmi
                              • probeg kamaymadimi
                              • foto haqiqatan yuklanganmi
                              • narx chetlanishi bayrog'i
```

**Hech qachon** klient hisoblagan summaga ishonilmaydi — server `submission_lines`dan
qayta hisoblaydi.

## 7. Shablon konstruktori (admin UI)

```
┌──────────────────────────────────────────────────┐
│  Shablon: Yuvish hisoboti          [Qoralama v2] │
├────────────────┬─────────────────────────────────┤
│ Maydon turlari │  Forma                          │
│                │  ┌───────────────────────────┐  │
│ ▸ Matn         │  │ ⠿ Mashina raqami      [⚙] │  │
│ ▸ Son          │  │   vehicle_picker · majburiy│ │
│ ▸ Pul          │  ├───────────────────────────┤  │
│ ▸ Foto         │  │ ⠿ Yuvishdan oldin     [⚙] │  │
│ ▸ Tanlov       │  │   photo · min 2 · kamera  │  │
│ ▸ Qatorlar     │  ├───────────────────────────┤  │
│ ▸ Joylashuv    │  │ ⠿ Summa               [⚙] │  │
│ ...            │  │   money · → total_amount  │  │
│                │  └───────────────────────────┘  │
├────────────────┴─────────────────────────────────┤
│  Kim to'ldiradi: [washer ×]                      │
│  Kim ko'radi: rollarda belgilanadi             │
│  Ob'ekt: (•) Mashina ( ) Xodim ( ) Yo'q          │
├──────────────────────────────────────────────────┤
│  [ 👁 Ko'rib chiqish ]  [ 🧪 Test ]  [ 🚀 Nashr ] │
└──────────────────────────────────────────────────┘
```

> **MVP soddalashtirish:** Faza 1'da vizual konstruktor yozilmaydi. Shablonlar
> va rollar **JSON seed fayl** sifatida repoda saqlanib, migratsiya orqali
> yuklanadi. Vizual konstruktor — **Faza 2**. Dvigatelning o'zi esa Faza 1'dan
> to'liq ishlaydi.

## 8. Boshlang'ich shablonlar (seed)

| Kod | Nom | Rol nomi | Faza |
|---|---|---|---|
| `car_repair` | Ta'mir hisoboti (narx kelishuvi bilan) | Usta | **Faza 1** |
| `part_purchase` | Ehtiyot qism xaridi | Ta'minotchi | Faza 2 |
| `car_wash` | Yuvish | Yuvuvchi | Faza 2+ |
| `tyre_change` | Shina almashtirish | Shinamontaj | Faza 2+ |
| `maintenance_to` | TO (checklist bilan) | Usta | Faza 4 |

Boshlang'ich rollar (`roles` seed):

| Kod | Nom | `kind` | Shablonlar |
|---|---|---|---|
| `mechanic` | Usta 🔧 | `reporter` | `car_repair` |
| `supplier` | Ta'minotchi 📦 | `reporter` | `part_purchase` |
| `admin` | Admin ⚙️ | `admin` | `car_repair` (o'zi ham yozishi mumkin) |
| `accountant` | Buxgalter 📊 | `accountant` | — |

---

**Keyingi:** [04. API dizayni](04-api-design.md)
