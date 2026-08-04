# 05. Holat mashinalari

Har holat o'zgarishi: **kim** qila oladi, **qachon** mumkin, **nima** sodir bo'ladi.
O'tishlar serverda tekshiriladi; ruxsatsiz o'tish → `409 invalid_state_transition`.

Tizimda **uchta** holat mashinasi bor: hisobot, mashina, davr.
(Zayavka va qism so'rovi mashinalari **yo'q** — ular alohida ob'ekt emas.)

## 1. Hisobot (`submissions`)

```mermaid
stateDiagram-v2
    [*] --> DRAFT: "Mashina keldi" bosildi
    DRAFT --> SUBMITTED: yuborildi (reporter)
    DRAFT --> APPROVED: yuborildi (admin) — AVTOMATIK
    DRAFT --> [*]: o'chirildi (faqat muallif)
    SUBMITTED --> IN_REVIEW: admin ochdi
    SUBMITTED --> APPROVED: narx o'zgarishsiz tasdiqlandi
    IN_REVIEW --> APPROVED: narx o'zgarishsiz tasdiqlandi
    IN_REVIEW --> PRICE_NEGOTIATION: admin narxni kamaytirdi
    PRICE_NEGOTIATION --> APPROVED: muallif rozi / 48 soat sukut
    PRICE_NEGOTIATION --> PRICE_DISPUTED: muallif rozi emas
    PRICE_DISPUTED --> PRICE_NEGOTIATION: admin yangi taklif
    PRICE_DISPUTED --> APPROVED: admin yakuniy qaror
    PRICE_DISPUTED --> REOPENED: hisobot qaytarildi
    SUBMITTED --> REOPENED: qaytarildi
    IN_REVIEW --> REOPENED
    IN_REVIEW --> REJECTED: rad etildi
    REOPENED --> SUBMITTED: muallif tuzatib qayta yubordi
    APPROVED --> PAID: qarz to'liq to'landi
    PAID --> APPROVED: to'lov void qilindi
    APPROVED --> REOPENED: admin qaytardi (to'lanmagan, audit bilan)
    REJECTED --> [*]
    PAID --> [*]
```

| Holat | Kim o'zgartira oladi | Tahrirlash | To'lovga kiradi |
|---|---|---|---|
| `DRAFT` | Muallif | ✅ | ❌ |
| `SUBMITTED` | — | ❌ | ❌ |
| `IN_REVIEW` | Admin | faqat narx | ❌ |
| **`PRICE_NEGOTIATION`** | **Muallif (rozilik)** | ❌ | ❌ |
| **`PRICE_DISPUTED`** | Admin | faqat narx | ❌ |
| `REOPENED` | Muallif | ✅ | ❌ |
| `APPROVED` | — | ❌ | ✅ |
| `REJECTED` | — | ❌ | ❌ |
| `PAID` | — | ❌ | ✅ (yopilgan) |

### O'tish qoidalari

| O'tish | Kim | Shartlar | Yon ta'sirlar |
|---|---|---|---|
| `→ DRAFT` | Muallif | — | `arrived_at = now()`, mashina `in_service` |
| `DRAFT → SUBMITTED` | Muallif (`reporter`) | Validatsiya o'tdi, `left_at` to'ldirilgan | Bayroq hisoblash, adminga bildirishnoma, `proposed_*` qulflanadi |
| **`DRAFT → APPROVED`** ⭐ | Muallif (`admin`) | Shu shartlar | **Avtomatik tasdiq (R1a):** `approved = proposed`, `auto_approved = true`, `approvals(decision='auto_approved', actor_id=NULL)`. Bildirishnoma yo'q, kelishuv yo'q |
| `SUBMITTED → IN_REVIEW` | Admin | Ruxsat bor | "Ko'rilmoqda" belgisi |
| `→ APPROVED` (narx o'zgarishsiz) | Admin | **R1: `approver ≠ author`** | `approved = proposed`, `payable_amount` hisoblanadi (R5), `approvals`, muallifga bildirishnoma |
| **`IN_REVIEW → PRICE_NEGOTIATION`** | Admin | `new < proposed`, **sabab majburiy** | `approvals(price_proposed)`, bildirishnoma, 48 soatlik taymer |
| **`PRICE_NEGOTIATION → APPROVED`** | Muallif yoki tizim | Rozilik yoki 48 soat sukut | `mechanic_accept_mode = manual / auto_48h` |
| **`PRICE_NEGOTIATION → PRICE_DISPUTED`** | Muallif | Izoh majburiy | Adminga bildirishnoma |
| **`PRICE_DISPUTED → APPROVED`** | Admin | **Yakuniy qaror adminda**, izoh majburiy | Muallifga bildirishnoma |
| `→ REOPENED` | Admin | Izoh majburiy | Tahrirlash ochiladi |
| `→ REJECTED` | Admin | Izoh majburiy | To'lovdan chiqadi |
| `APPROVED → PAID` | Tizim | `paid_amount == payable_amount` | To'lov qayd etilganda avtomatik |
| `PAID → APPROVED` | Tizim | To'lov `void` qilindi | `paid_amount` qayta hisoblanadi, qarz qayta ochiladi |
| `APPROVED → REOPENED` | Admin | **To'lanmagan** (`paid_amount = 0`), sabab majburiy | Audit log |

> ❗ **Qattiq cheklovlar:**
> - `approved_amount ≤ proposed_amount` — admin narxni **oshira olmaydi** (R2)
> - `approver_id ≠ author_id` — hech kim o'z hisobotini **qo'lda** tasdiqlay
>   olmaydi (R1)
> - **`admin` muallifi bo'lgan hisobot tizim tomonidan avtomatik tasdiqlanadi**
>   (R1a) — u `SUBMITTED` / `PRICE_NEGOTIATION` holatlariga umuman kirmaydi

### `arrived_at` / `left_at`

Haydovchi bo'lmagani uchun mashinaning kelgani va ketgani ustaning ikki
tugmasi orqali qayd etiladi:

```
[ 🚗 Mashina keldi ]  → arrived_at = SERVER vaqti, mashina → in_service
   ... ish ...
[ 🚙 Mashina ketdi ]  → left_at = SERVER vaqti, mashina → active
```

- Vaqt **serverda** yoziladi — klient yuborgan qiymatga ishonilmaydi
- `left_at` to'ldirilmasa hisobot yuborilmaydi
- **Downtime = `left_at − arrived_at`**
- `left_at < arrived_at` → `422 business_rule_violated`

## 2. Mashina (`vehicles.status`)

```mermaid
stateDiagram-v2
    [*] --> ACTIVE: parkka qo'shildi
    ACTIVE --> IN_SERVICE: "Mashina keldi"
    IN_SERVICE --> WAITING_PARTS: qism kutilmoqda
    WAITING_PARTS --> IN_SERVICE: qism keldi
    IN_SERVICE --> ACTIVE: "Mashina ketdi"
    ACTIVE --> INACTIVE: vaqtincha ishlatilmaydi
    INACTIVE --> ACTIVE
    ACTIVE --> SOLD: sotildi
    INACTIVE --> SOLD
    SOLD --> [*]
```

**Yandex Fleet bilan bog'liqlik** (Faza 3):

| Platforma statusi | Fleet `car.status` |
|---|---|
| `ACTIVE` | `working` |
| `IN_SERVICE` / `WAITING_PARTS` | `repairing` |
| `INACTIVE` | `not_working` |

> ⚠️ **2026-08-01 dan bu jadval faqat ma'lumot uchun** — platforma Fleet'ga
> status yozmaydi ([Fleet §6](../03-integrations/01-yandex-fleet-api.md)).
> Avvalgi g'oya: ta'mir boshlanganda mashinani Fleet'da `repairing` qilish zakaz kelmasligini
> ta'minlaydi — [Fleet integratsiyasi](../03-integrations/01-yandex-fleet-api.md).

## 3. Qarz va to'lov

> ⚠️ **Davr (`periods`) holat mashinasi YO'Q** — oy yopish tushunchasi olib
> tashlangan ([ADR-0015](../05-delivery/03-decisions.md#adr-0015--qarz-daftari-oy-yopish-orniga-hisobot-boyicha-tolov-)).

Qarz — alohida holat emas, hisobotning **hisoblanadigan xususiyati**:

```mermaid
stateDiagram-v2
    [*] --> QARZ: APPROVED bo'ldi (paid_amount = 0)
    QARZ --> QISMAN: qisman to'lov
    QISMAN --> QISMAN: yana qisman to'lov
    QARZ --> PAID: to'liq to'lov
    QISMAN --> PAID: qoldiq to'landi
    PAID --> QISMAN: to'lov void qilindi
    QISMAN --> QARZ: to'lov void qilindi
```

| Ko'rinish | Shart |
|---|---|
| **Qarz** | `status = APPROVED` va `paid_amount < payable_amount` |
| **Qisman** | `0 < paid_amount < payable_amount` — «Qarzlar» tabida qoldiq bilan |
| **To'langan** | `paid_amount == payable_amount` → `status = PAID` |

⭐ **«Qisman» endi Mini App'da ham ko'rinadi** (2026-08-04): hisobot belgisi
`Tasdiqlangan → Qisman to'langan → To'langan` bo'lib o'zgaradi va kartochkada
«To'lanadi · To'langan · Qoldi» qatorlari turadi.

⚠️ Bu **ko'rsatish holati** — bazada `partly_paid` statusi YO'Q va qo'shilmaydi.
Holat mashinasi o'zgarmagan: `status` qisman to'lov davrida hamon `APPROVED`.
Farq `paid_amount`/`payable_amount` dan hisoblanadi (`miniapp/src/display-status.ts`,
testi bor). Yangi status kiritilsa migratsiya, `_sync_status` va barcha
filtrlar buzilardi — foyda esa faqat ko'rinishda edi.

To'lovning o'zi ikki holatda: **faol** yoki **`void`** (bekor qilingan, sabab
majburiy). To'lov hech qachon tahrirlanmaydi — faqat `void` (P5).

## 4. Xodim (`employees.status`)

```mermaid
stateDiagram-v2
    [*] --> ACTIVE: reyestrga kiritildi
    ACTIVE --> BLOCKED: vaqtincha bloklandi
    BLOCKED --> ACTIVE
    ACTIVE --> FIRED: ishdan bo'shadi
    BLOCKED --> FIRED
    FIRED --> ACTIVE: qayta ishga olindi
```

**Hech qachon o'chirilmaydi** — eski hisobotlar baribir kerak.
⚠️ Oxirgi `kind='admin'` xodimni bloklash/bo'shatish taqiqlanadi (R8).

## 5. Bayroq (`flags`)

```mermaid
stateDiagram-v2
    [*] --> OPEN: avtomatik qo'yildi
    OPEN --> ACCEPTED: admin "sabab bor" dedi
    OPEN --> FALSE_POSITIVE: admin "xato bayroq" dedi
    OPEN --> CONFIRMED_FRAUD: admin tasdiqladi
    ACCEPTED --> [*]
    FALSE_POSITIVE --> [*]
    CONFIRMED_FRAUD --> [*]
```

`FALSE_POSITIVE` statistikasi anti-fraud chegaralarini sozlash uchun ishlatiladi.

---

**Keyingi:** [06. Xavfsizlik](06-security.md)
