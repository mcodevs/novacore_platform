# 02. Qabul qilingan qarorlar va ochiq savollar

Bu hujjat loyiha bo'yicha berilgan savollar va ularning javoblarini yuritadi.
Javob kelgach tegishli hujjatlar yangilanadi va bu yerda belgilanadi.

## Holat (2026-07-31)

| | |
|---|---|
| ✅ Javob berilgan | **A-01 … A-25** (barchasi) |
| 🔬 Texnik sinov kutmoqda | **A-10** (Faza 0). ~~A-09~~ — Fleet yozuvi bekor qilingani uchun tushib qoldi |
| 🟡 Ochiq savol | — yo'q |

---

## ✅ Biznes va jarayon

### ✅ A-01. Hozir jarayon qanday ketmoqda?

**Javob:** Faqat **Telegram guruhlarida**. Narx **usta bilan yuzma-yuz ko'rishib,
gaplashib** kelishiladi — hech qayerda yozilmaydi.

**Ta'siri:** Muammo tasdiqlandi (P1, P3). Narx kelishuvini raqamlashtirish —
platformaning asosiy qiymati.

---

### ✅ A-02. Masshtab

**Javob:** ~**150** elektromobil · **4–5 usta** · kuniga **3–5 ta'mir**
(oyiga ~90–150) · **filiallar muhim emas**.

**Ta'siri:** ⭐ Arxitektura keskin soddalashtirildi —
[01-system-architecture.md](../02-architecture/01-system-architecture.md):
Redis yo'q, worker yo'q, mikroservis yo'q, bitta fly.io machine.

---

### ✅ A-03. Ustalar qayerda ishlaydi?

**Javob:** Ustalar **o'z ustaxonalarida** ishlaydi. Filialga biriktirish shart emas.

**Ta'siri:** ⭐ `branches` jadvali va filial bo'yicha ma'lumot ko'lami
**butunlay olib tashlandi**. Xodim profilida ixtiyoriy `workshop_name`.

---

### ✅ A-04. Ustalarga to'lov modeli

**Javob:** Har ish uchun to'lov. Narxni **ustaning o'zi** kiritadi, **admin
tasdiqlaydi** va gaplashib **arzonlashtira oladi**.

**Ta'siri:** [04-flows/04-price-negotiation.md](../04-flows/04-price-negotiation.md),
`proposed` / `approved` / `reference` modeli, `PRICE_NEGOTIATION` holatlari,
[ADR-0009](03-decisions.md).

---

### ✅ A-05. Ehtiyot qismni kim sotib oladi?

**Javob:** **Alohida ta'minotchi xodim.**

**Ta'siri:** [05-supplier-role.md](../01-product/05-supplier-role.md).
⚠️ A-13 javobidan keyin model o'zgardi: ta'minotchi — bu shunchaki **rol nomi**,
u ham hisobot yuboradi (o'z shabloni bilan). Alohida `part_requests` jadvali
**kerak emas** — [ADR-0010](03-decisions.md) yangilandi.

---

### ✅ A-06. Mashinani topshirish/qabul qilish

**Javob:** ❌ Bekor — haydovchilar tizimda rolga ega emas (A-12 ga qarang).
Mashinaning kelgani/ketgani **usta tomonidan** belgilanadi.

---

### ✅ A-07. Haydovchi v1'ga kiradimi?

**Javob:** Yo'q → keyin A-12 bilan **butunlay olib tashlandi**.

---

### ✅ A-08. Davr biriktirish qoidasi

**Javob:** **Yuborilgan sanaga** qarab.

---

### ✅ A-12. Haydovchi roli

**Javob:** ⭐ **Haydovchilar bu loyihada rolga ega emas** — Faza 2 dan ham olib
tashlandi. Mashinaning ustaxonaga kelgani va chiqib ketgani **usta** tomonidan
belgilanadi.

**Ta'siri:**
- `03-driver-flow.md` **o'chirildi**, hujjatlar qayta raqamlandi
- `submissions.arrived_at` / `left_at` — usta bosadigan ikki tugma
- **Downtime = `left_at − arrived_at`**
- `vehicle_assignments` jadvali olib tashlandi; joriy haydovchi Fleet'dan
  faqat **ma'lumot** sifatida sinxronlanadi
- `service_requests` (zayavka) MVP'dan chiqarildi — usta hisobotni o'zi ochadi

---

### ✅ A-13. Rol modeli ⭐ (eng ta'sirli javob)

**Javob:** *"Rollar deganda **nomlar** nazarda tutiladi. Hammada rasmga olish,
izoh yozish, narx qo'yish imkoniyatlari bor — hatto adminda ham. Ta'minotchi ham
usta nima qilsa shuni qila oladi, faqat rol nomi boshqa. **Admin bunday
rollardan bir nechta yaratishi mumkin**."*

**Ta'siri:** ⭐ Butun ruxsat modeli qayta yozildi —
[01-roles-and-permissions.md](../01-product/01-roles-and-permissions.md):
- Katta ruxsat matritsasi **olib tashlandi**
- `permissions` / `role_permissions` jadvallari **kerak emas**
- Rol = `code` + `name` + `icon` + **`kind`** (`reporter` / `admin` / `accountant`)
- Vazifalarni ajratish endi **shablon orqali**, qattiq taqiq orqali emas
- Rol konstruktori **Faza 2**ga ko'tarildi (avval Faza 3 edi)
- [ADR-0012](03-decisions.md) qo'shildi

---

### ✅ A-15. Kim tasdiqlaydi va necha bosqich?

**Javob:** Hisobot **admin va buxgalter** uchun ochiq. **Direktorga ko'tarilish
yo'q** — bitta bosqich.

**Ta'siri:** Summaga qarab ko'p bosqichli tasdiqlash olib tashlandi.

---

### ✅ A-19 / A-23. Narx nizosida oxirgi so'z

**Javob:** **Oxirgi so'z adminda.**

---

### ✅ A-24. Usta o'z narx statistikasini ko'rsinmi?

**Javob:** **Ha.** (Boshqalarnikini emas.)

---

### ✅ A-22. Qism omborga tushadimi?

**Javob:** **Yo'q.** Ombor yuritilmaydi.

---

## ✅ Texnik

### ✅ A-11 / A-19. Bitta bot yoki ikkita?

**Javob:** **Bitta bot va uning ichida bitta Mini App — hamma uchun.**
Rolga qarab menyu o'zgaradi.

---

### ✅ A-12(hosting) / A-12. Hosting qayerda?

**Javob:** **fly.io.**

**Ta'siri:** [01-system-architecture.md](../02-architecture/01-system-architecture.md) —
Fly Postgres + **Tigris** (fly.io'ning S3-mos ombori). Taxminiy narx $10–25/oy.

⚠️ **Qabul qilingan xavf:** O'zbekiston qonunchiligi shaxsiy ma'lumotlarni
mamlakat hududida saqlashni talab qiladi, fly.io serverlari chet elda. Ta'sirni
kamaytirish uchun **minimal shaxsiy ma'lumot** saqlanadi (FIO, telefon,
Telegram ID; passport/JSHSHIR yo'q) va hech qanday fly.io'ga xos xususiyat
ishlatilmaydi — kerak bo'lsa ko'chirish oson.

---

### ✅ A-14. Til

**Javob:** **O'zbek + rus, ikkalasi.**

---

### ✅ A-17. Kim yozadi?

**Javob:** ⭐ **Kodni AI yozadi**, loyiha egasi yo'naltiradi va tekshiradi.
Muddat: "qancha tez bo'lsa shuncha yaxshi".

**Ta'siri:** [Roadmap](01-roadmap.md) qayta yozildi:
- Rejalar **iteratsiyalar** bilan, haftalar bilan emas
- Hujjatlar = **texnik topshiriq** (noaniq hujjat → noto'g'ri kod)
- **Domain testlari majburiy** — AI kodini shu tekshiradi
- React tajribasi masalasi ahamiyatini yo'qotdi

---

### ✅ A-16. Eski ma'lumotlarni ko'chirish

**Javob:** **Yo'q — 0 dan boshlaymiz.**

---

### ✅ A-18. Web admin panel

**Javob:** **Mini App yetarli.**

---

### ✅ A-20. Buxgalteriya integratsiyasi

**Javob:** **Eksport bo'lsin, import shart emas.**

---

### ✅ A-13(media) / A-18. Media saqlash muddati

**Javob:** **Muhim emas — qo'lda (manual).** Avtomatik arxivlash/o'chirish yo'q;
`media.deleted_at` orqali admin xohlasa o'chiradi.

---

### ✅ A-21. Bu `driver_status_reporter` kompaniyasimi?

**Javob:** **Ha** — bu NovaCore'ning boshqa loyihasi.

**Ta'siri:** Fleet API kalitlari va tasdiqlangan bilim qayta ishlatiladi
([Fleet integratsiyasi](../03-integrations/01-yandex-fleet-api.md)).

---

## 🔬 Texnik sinovlar (Faza 0)

### ✅ A-09. Fleet'da `status=repairing` yozish ishlaydimi? — **savol tushib qoldi**

**Javob (2026-08-01):** sinov **kerak emas** — egasining qaroriga ko'ra Fleet
platformada faqat *raqam bo'yicha mashina va haydovchi ma'lumotini olish* uchun
ishlatiladi, orqaga hech narsa yozilmaydi.

Yo'l-yo'lakay aniqlangan (spec'dan): `PUT /v2/parks/vehicles/car` — **to'liq
almashtirish**, `park_profile` (callsign, fuel_type, status), `vehicle_licenses`
(licence_plate_number) va `vehicle_specifications` (brand, color, model,
transmission, year) majburiy. Ya'ni «faqat status yuborish» texnik jihatdan ham
mumkin emas edi — GET→PUT kerak bo'lardi va ДКК qulfiga urilish ehtimoli
yuqori. Batafsil: [Fleet integratsiyasi §6](../03-integrations/01-yandex-fleet-api.md).

### 🔬 A-10. Mini App'da kamerani majburlash ishlaydimi?

`<input capture="environment">` Telegram WebView'ida (Android **va** iOS)
galereyani bloklab, faqat kamerani ochadimi?
⚠️ **Butun foto-dalil g'oyasi shunga bog'liq.** Faza 0.1 — birinchi vazifa.

---

## ✅ A-25. Adminning o'z hisobotini kim tasdiqlaydi?

**Javob (2026-07-31):** **Hech kim.** Admin o'z-o'zini tasdiqlamaydi — uning
hisoboti **avtomatik tasdiqlanadi**. Unga tasdiqlovchi kerak emas.

**Ta'siri:**
- `DRAFT → APPROVED` to'g'ridan-to'g'ri o'tish (tasdiqlovchi bosqichisiz)
- `approved = proposed` — narx kelishuvi ham bo'lmaydi (kelishadigan tomon yo'q)
- `submissions.auto_approved = true` belgisi + `approvals(decision='auto_approved',
  actor_id=NULL)` yozuvi — audit izi saqlanadi
- **R1 qoidasi qayta yozildi:** "muallif o'z hisobotini tasdiqlay olmaydi" →
  "`admin` turidagi rol muallifi bo'lgan hisobot **tizim tomonidan** tasdiqlanadi"
- [ADR-0014](03-decisions.md) qo'shildi

⚠️ **Shaffoflik chorasi:** bu — nazorat halqasidagi yagona ochiq joy. Shuning
uchun avtomatik tasdiqlangan hisobotlar **alohida belgilanadi** va oylik
hisobotda hamda buxgalterning qarzlar ekranida ayrim satr sifatida
ko'rsatiladi ("avtomatik tasdiqlangan: N ta, X so'm").

---

## Javoblarni belgilash tartibi

1. Savol tagiga **✅ Javob** qo'shiladi
2. Tegishli hujjat yangilanadi va shu yerda **Ta'siri** bo'limida ko'rsatiladi
3. Arxitektura o'zgarsa — [03-decisions.md](03-decisions.md) ga ADR qo'shiladi

---

**Keyingi:** [03. Arxitektura qarorlari](03-decisions.md)
