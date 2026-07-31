# 03. Arxitektura qarorlari (ADR)

Har bir muhim qaror: **kontekst → qaror → sabab → oqibatlar → rad etilgan
variantlar**. Qaror o'zgarsa — eski yozuv qoladi, yangisi qo'shiladi.

---

## ADR-0001 — Universal hisobot shabloni (dinamik forma)

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi

### Kontekst
Talab: platforma faqat ustalar uchun emas, **barcha xodimlar** uchun ishlashi kerak.
Har rol uchun alohida modul yozish har yangi rolda 2–3 hafta talab qiladi va
5-roldan keyin loyihani to'xtatadi.

### Qaror
Yagona **shablon dvigateli**: `templates` + `template_fields` + `submissions.data`
(JSONB). Ta'mir hisoboti — shunchaki birinchi shablon, alohida modul emas.

### Sabab
- Yangi rol = konfiguratsiya, kod emas (30 daqiqa vs 2 hafta)
- Bitta tasdiqlash oqimi, bitta anti-fraud, bitta analitika
- Kod hajmi keskin kam

### Oqibatlar
- ➕ Kengayish arzon
- ➕ Yadro yaxshilansa — barcha rollar foyda ko'radi
- ➖ Boshlang'ich murakkablik yuqoriroq (JSONB, versiyalash)
- ➖ Analitika uchun `field_mapping` mexanizmi kerak (ADR-0002)

### Rad etilgan variantlar
| Variant | Nega rad etildi |
|---|---|
| Har rol uchun alohida jadval va modul | Kengaytirish qimmat, kod takrorlanadi |
| Faqat ta'mir moduli, keyin o'ylaymiz | Keyinchalik qayta yozish kerak bo'ladi |
| To'liq no-code platforma (Retool kabi) | Telegram Mini App bilan mos emas, nazorat yo'q |

---

## ADR-0002 — JSONB + "promoted" ustunlar (gibrid model)

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi

### Kontekst
ADR-0001 dinamik maydonlarni JSONB'da saqlashni talab qiladi. Lekin analitika
(`mashinaga oylik xarajat`) uchun tez va ishonchli so'rovlar kerak, FK cheklovlari
kerak.

### Qaror
Barcha qiymatlar `submissions.data` (JSONB)da, **shu bilan birga** shablonning
`field_mapping` tavsifiga ko'ra muhim qiymatlar alohida ustunlarga ham yoziladi:
`subject_vehicle_id`, `total_amount`, `labor_amount`, `odometer_km`, ...

### Sabab
- Analitika oddiy SQL bilan, GIN indeks va JSONB operatorlarisiz
- FK cheklovlari ishlaydi (mashina haqiqatan mavjud)
- Forma to'liq dinamik qoladi

### Oqibatlar
- ➕ Tez so'rovlar, ma'lumot yaxlitligi
- ➖ Ikki joyda saqlash → saqlash paytida sinxronlash mantiqi kerak
- ➖ `field_mapping` noto'g'ri sozlansa — analitika buziladi (test bilan qoplanadi)

### Rad etilgan variantlar
| Variant | Nega rad etildi |
|---|---|
| Faqat JSONB | Analitika og'ir, FK yo'q, xato topish qiyin |
| EAV (`submission_values` jadvali) | Har hisobot uchun 20 qator, JOIN do'zaxi |
| Ta'mir uchun alohida tipli jadval | ADR-0001 ni buzadi, ikkita oqim |

---

## ADR-0003 — Media o'z omborimizda (Telegram `file_id` emas)

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi

### Kontekst
Fotolarni Telegram'da qoldirib `file_id` saqlash bepul va oson ko'rinadi.

### Qaror
Barcha media **Tigris (S3-mos)**da saqlanadi. `file_id` — faqat tezkor ko'rsatish keshi.

### Sabab
- `file_id` bot tokeniga bog'langan — bot almashsa barcha dalillar yo'qoladi
- Foto — bu **moliyaviy dalil**, tashqi servisga bog'liq bo'lmasligi kerak
- Mini App'dan to'g'ridan-to'g'ri kirish oson (signed URL)

### Oqibatlar
- ➕ To'liq nazorat, backup, yuridik ishonchlilik
- ➖ Ombor xarajati (~2–3 GB/yil — deyarli tekin)
- ➖ Yuklash oqimini o'zimiz yozamiz (presigned URL)

---

## ADR-0004 — Bitta process, Redis'siz

**Sana:** 2026-07-31 · **Holat:** ♻️ Yangilandi ([A-02](02-open-questions.md) javobi:
150 mashina, 4–5 usta, kuniga 3–5 hisobot)

### Kontekst
Dastlab bot / API / worker alohida processlar va Redis navbat rejalashtirilgan
edi. Real masshtab ma'lum bo'lgach bu ortiqcha ekani ko'rindi: **RPS < 1**,
kuniga ~50 bildirishnoma.

### Qaror
**Bitta Python ilova** (FastAPI + aiogram bir ASGI app'da) + Postgres + S3.
Fon vazifalari — shu process ichidagi asyncio sikli, navbat — Postgres
`notifications` outbox jadvali.

### Sabab
- 15 foydalanuvchi uchun Redis, Celery va alohida worker — foydasiz murakkablik
- Har qo'shimcha komponent = qo'shimcha nosozlik nuqtasi
- **Kodni AI yozadi, lekin nosozlikni odam tuzatadi** — sodda tizim tuzatiladi

### Oqibatlar
- ➕ Deploy: bitta fly.io machine, ~$10–25/oy
- ➕ Lokal ishga tushirish: `docker compose up` (postgres + app)
- ➖ Og'ir eksport so'rovi API'ni sekinlashtirishi mumkin — bu masshtabda
  ahamiyatsiz; kerak bo'lsa keyinchalik worker ajratiladi

---

## ADR-0005 — Python / FastAPI / aiogram 3

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi ([A-17](02-open-questions.md) javobi:
**kodni AI yozadi**, egasi yo'naltiradi)

### Kontekst
`driver_status_reporter` loyihasi bor: Python + python-telegram-bot 22.6 +
gspread + fly.io. Kodni AI yozgani uchun "jamoada qaysi til bor" savoli
ahamiyatini yo'qotdi — lekin **kodni odam o'qishi va tuzatishi** kerak, shuning
uchun mavjud tajribaga yaqin stek afzal.

### Qaror
Backend — Python 3.12, FastAPI (API) + aiogram 3 (bot) + SQLAlchemy 2 + Alembic.

### Sabab
- Mavjud tajribaga eng yaqin
- FastAPI avtomatik OpenAPI beradi (Mini App dasturchisi uchun)
- aiogram 3 async — FastAPI bilan bir ASGI ilovada birlashadi

### Frontend qarori
- **Tayyor UI kit:** `@telegram-apps/telegram-ui` — o'z dizayn tizimi yozilmaydi
- **MVP'da 4 ta ekran:** ro'yxat · forma · ko'rib chiqish · profil
- **Admin CRUD** — oddiy jadval
- State: React Query — Redux ortiqcha

### Rad etilgan variantlar
| Variant | Nega rad etildi |
|---|---|
| Go / Node / Django | Mavjud kod bazasi va tajriba Python'da; kodni odam o'qiy olishi kerak |
| **Faqat bot, Mini App'siz** | Telegram fotoni siqadi va **EXIF'ni o'chiradi** → anti-fraud signallari yo'qoladi; narx kelishuvi ekrani chat'ga sig'maydi |

---

## ADR-0006 — Anti-fraud bloklamaydi (bayroq = savol)

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi

### Kontekst
Firibgarlikni aniqlash tizimi ustalarni dushman qilib qo'yishi mumkin. Ular
tizimdan chetlab o'tsa — loyiha o'ladi.

### Qaror
Bayroqlar **avtomatik jazolamaydi va bloklamaydi** (kritiklardan tashqari).
Ular adminga ma'lumot beradi, qaror odamniki.

### Sabab
- Yolg'on ishga tushish (false positive) muqarrar
- Avtomatik jazo → ishonchsizlik → sabotaj
- Admin kontekstni biladi, algoritm bilmaydi

### Oqibatlar
- ➕ Odamlar tizimga qarshi chiqmaydi
- ➕ `false_positive` statistikasi chegaralarni sozlashga yordam beradi
- ➖ Admin ishtiroki kerak (lekin bu baribir kerak edi)

---

## ADR-0007 — Bosqichma-bosqich joriy etish, "hisobotsiz to'lov yo'q"

**Sana:** 2026-07-31 · **Holat:** 🟡 Taklif (rahbariyat qarori kerak)

### Kontekst
Ichki platformalarning asosiy o'lim sababi — odamlar ishlatmaydi.

### Qaror
1. Pilot (2 usta + admin, 2 hafta, parallel eski usul bilan)
2. Barcha ustalar, Telegram guruhda hisobot qabul qilinmaydi
3. **"Tizimda yo'q ish — to'lanmaydi"** qoidasi kuchga kiradi

### Sabab
Texnik yechim tashkiliy qo'llab-quvvatlashsiz ishlamaydi. Bu qoida —
platformaning **yagona ishonchli joriy etish mexanizmi**.

### Oqibatlar
- ➕ Ma'lumot to'liq bo'ladi
- ➖ Boshida qarshilik bo'ladi → pilot, narx kelishuvida sabab majburiyligi
  va nizo huquqi shu qarshilikni kamaytiradi

---

## ADR-0008 — Fleet API — bir tomonlama sinxron

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi

### Kontekst
Ikki tizimda ham mashina va haydovchi ma'lumoti bor. Ikki tomonlama tahrirlash
konfliktga olib keladi.

### Qaror
Har maydonning bitta egasi:
- **Fleet** → raqam, VIN, marka, model, FIO, telefon (platformada faqat o'qish)
- **Platforma** → batareya, TO, rollar, hisobotlar
  (⚠️ 2026-08-01: mashina statusini Fleet'ga yozish **bekor qilindi** — Fleet faqat o'qish uchun)

Faqat **status** platformadan Fleet'ga yoziladi.

### Sabab
- Konflikt bo'lmaydi
- Fleet ishlamasa — platforma to'xtamaydi

### Oqibatlar
- ➕ Sodda va bashoratli
- ➖ Fleet'da yo'q mashinani platformada qo'lda qo'shish kerak (kamdan-kam)

---

## ADR-0009 — Narx kelishuvi (usta ↔ admin)

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi ([A-04](02-open-questions.md) javobi)

### Kontekst
NovaCore'da usta **har ish uchun** to'lov oladi va **narxni o'zi belgilaydi**.
Admin ustalar bilan gaplashib narxni kamaytirishi mumkin. Bugun bu savdolashuv
og'zaki ketadi va hech qayerda qolmaydi.

### Qaror
Har bir narx uch qiymatga ega: `proposed_amount` (usta so'ragan, **immutable**),
`approved_amount` (admin tasdiqlagan), `reference_amount` (tarixiy tayanch).
Kelishuv `PRICE_NEGOTIATION` → usta rozi/nizo → `APPROVED` holatlari orqali
o'tadi. To'lov **faqat `approved_amount`** bo'yicha.

Qo'shimcha qarorlar:
- **Admin narxni faqat kamaytira oladi** (`approved ≤ proposed`)
- **Tayanch narx ustaga ko'rsatilmaydi** — aks holda barcha narxlar tayanchga
  yopishadi va kelishuv imkoniyati yo'qoladi
- Admin ekranida **tarixiy statistika** (o'rtacha/min/max, ustaning o'z tarixi)
- 48 soat javob bo'lmasa — avtomatik rozilik (to'lov qotib qolmasin)

### Sabab
- Savdolashuv raqamlashadi → nizolar yo'qoladi ("men 180 dedim")
- `proposed` saqlanishi ustaning "narx xulqi"ni o'lchash imkonini beradi
- Kelishuv tejamkorligi — platformaning **o'zini oqlaydigan KPI**si
- Oshirish taqiqi — admin + usta til biriktirishining oldini oladi

### Oqibatlar
- ➕ Har oyda "tizim X so'm tejadi" degan aniq raqam
- ➕ Adminning savdolashuvi tarixga tayanadi, his-tuyg'uga emas
- ➖ Qo'shimcha holatlar va ekranlar (MVP ~1.5 hafta uzayadi)
- ➖ Ustalar boshida qarshilik ko'rsatishi mumkin → sabab majburiyligi va
  nizo huquqi shu qarshilikni yumshatadi

### Rad etilgan variantlar
| Variant | Nega rad etildi |
|---|---|
| Narxnoma qat'iy, usta tanlaydi | Bozor narxi ko'rinmaydi, kelishuv imkoni yo'q — egasi talabiga zid |
| Admin qarori yakuniy (usta tasdig'isiz) | Nizolarda dalil yo'q, adolatsiz his qilinadi |
| Tayanch narx ustaga ochiq | Barcha narxlar tayanchga yopishadi, arzonlashtirish imkoni yo'qoladi |
| Admin narxni oshira olishi | Til biriktirib summa ko'tarish yo'li ochiladi |

---

## ADR-0010 — Ehtiyot qism narxini faqat ta'minotchi kiritadi

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi ([A-05](02-open-questions.md) javobi)

### Kontekst
NovaCore'da ehtiyot qismni **alohida ta'minotchi xodim** sotib oladi.
Qism odatda ta'mir xarajatining 60–75%ini tashkil qiladi.

### Qaror
Usta faqat **qaysi qism kerakligini** yozadi (nom + soni). Narx, yetkazib
beruvchi va chekni **"Ta'minotchi" rolidagi xodim** o'z hisobotida kiritadi.

> ♻️ **2026-07-31 yangilandi ([ADR-0012](#adr-0012--rol--nom-ruxsat-toplami-emas-)
> ta'sirida):** bu endi **qattiq API taqiqi emas, shablon orqali ajratish**.
> Ustaning shablonida qism narxi maydoni yo'q; ta'minotchining shablonida bor.
> Natija bir xil, lekin model sodda va admin uni o'zgartira oladi.
> Alohida `part_requests` jadvali **kerak emas** — ta'minotchining xaridi
> oddiy `submission` (o'z shabloni bilan), ta'mir hisobotiga
> `related_submission_id` orqali bog'lanadi.

### Sabab
- **Vazifalarni ajratish** (separation of duties) — usta qism narxini shishira
  olmaydi, chunki umuman kiritmaydi
- Ta'minotchi ishni o'ylab topa olmaydi (u ta'mir qilmaydi)
- `WAITING_PARTS` downtime'ining **egasi paydo bo'ladi** → SLA o'lchanadi

### Oqibatlar
- ➕ F5 (qism narxini shishirish) teshigi tuzilmaviy yopiladi
- ➕ Ta'minot xarajati chek bilan hujjatlashtiriladi
- ➕ Yangi jadval **kerak emas** — mavjud `submissions` dvigateli ishlatiladi
- ➖ Ta'minotchi shabloni Faza 2'da; MVP'da qism narxini admin kiritadi

---

## ADR-0011 — MVP: yadro + ta'mir + narx kelishuvi

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi ([A-07](02-open-questions.md),
[A-13](02-open-questions.md), [A-17](02-open-questions.md) javoblari)

### Kontekst
Kodni AI yozadi. Rollar dinamik bo'lgani uchun shablon dvigateli MVP'dan
tashqarida qololmaydi — usiz "ta'minotchi" ham, "elektrik" ham qo'shib bo'lmaydi.

### Qaror
Faza 1 = **shablon dvigateli + ta'mir shabloni + narx kelishuvi + admin
tasdiqlash + davr/eksport**. Rollar seed'da (usta, ta'minotchi, admin,
buxgalter); **rol/shablon konstruktori UI** — Faza 2.

### Sabab
- Dinamik shablon dvigateli — bu **loyihaning o'zagi**, uni keyinga qoldirish
  keyinchalik qayta yozishni anglatadi
- Alohida modul yozishdan ko'ra dvigatel yozish **arzonroq**

### Oqibatlar
- ➕ Faza 2 da yangi rol qo'shish deyarli tekin
- ➕ MVP ~2–3 hafta (AI bilan, kunlik iteratsiya)
- ➖ Ikki tomonlama tasdiq yo'q ([ADR-0013](#adr-0013--haydovchi-tizimda-rolga-ega-emas)) →
  nazorat foto + narx kelishuviga tayanadi

---

## ADR-0012 — Rol = nom, ruxsat to'plami emas ⭐

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi ([A-13](02-open-questions.md) javobi)

### Kontekst
Loyiha egasi: *"Rollar deganda nomlar nazarda tutiladi — hammada rasmga olish,
izoh yozish, narx qo'yish imkoniyatlari bor, hatto adminda ham. Ta'minotchi ham
usta nima qilsa shuni qila oladi, faqat rol nomi boshqa. Admin bunday rollardan
bir nechta yaratishi mumkin."*

### Qaror
Rol — bu **nom + ikonka + qaysi shablonlarni ko'rishi**. Ruxsatlar
`role.kind` dan kelib chiqadi va **faqat uchta tur** bor:
`reporter` · `admin` · `accountant`. Nomlar cheksiz — admin yaratadi.

### Sabab
- Real tashkilotda hamma bir xil ish qiladi (foto + izoh + narx), farq nomda
- Katta ruxsat matritsasi 15 kishilik tizim uchun ortiqcha murakkablik
- Admin yangi rolni **kod yozmasdan** qo'sha oladi — asosiy talab shu

### Oqibatlar
- ➕ `permissions` va `role_permissions` jadvallari **kerak emas**
- ➕ Ruxsat matritsasi 25 qatordan 20 qatorga, 8 ustundan 3 ustunga qisqardi
- ➕ Rol konstruktori Faza 3 dan **Faza 2** ga ko'chdi (arzonlashdi)
- ➖ Nozik ruxsat kerak bo'lsa (masalan "faqat ko'rish, tahrirlashsiz") model
  qayta ko'riladi — hozircha bunday talab yo'q
- ➖ Admin ham hisobot yozgani uchun "kim tasdiqlaydi" savoli tug'ildi →
  [ADR-0014](#adr-0014--admin-hisoboti-avtomatik-tasdiqlanadi) bilan hal qilindi

### Rad etilgan variantlar
| Variant | Nega rad etildi |
|---|---|
| To'liq RBAC (permission-per-action) | 15 foydalanuvchi uchun ortiqcha; admin yangi rolni o'zi yarata olmasdi |
| Har rol uchun kodda qattiq belgilangan ruxsat | Yangi rol = deploy → asosiy talabga zid |

---

## ADR-0013 — Haydovchi tizimda rolga ega emas

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi ([A-12](02-open-questions.md) javobi)

### Kontekst
Dastlab haydovchi ikki tomonlama tasdiq (mashinani topshirish/qabul qilish)
uchun rejalashtirilgan edi. Egasi: haydovchilar bu loyihada rolga ega emas;
mashinaning kelgani va ketgani **usta** tomonidan belgilanadi.

### Qaror
Haydovchi roli, zayavka oqimi va `vehicle_assignments` jadvali **olib tashlandi**.
Hisobotda **`arrived_at`** va **`left_at`** — usta bosadigan ikki tugma.

### Sabab
- 150 mashina uchun haydovchilarni tizimga kiritish katta tashkiliy yuk
- Usta baribir mashina oldida turadi — vaqtni u belgilashi tabiiy
- MVP sezilarli yengillashadi

### Oqibatlar
- ➕ Downtime baribir o'lchanadi (`left_at − arrived_at`)
- ➕ Bitta rol, bitta oqim — kod ancha kam
- ➖ **Ikki tomonlama tasdiq yo'q** → soxta ta'mirni faqat foto va narx
  kelishuvi ushlaydi
- ➖ Vaqtlarni usta o'zi kiritgani uchun ular **manipulyatsiya qilinishi mumkin**
  → yumshatish: server vaqti yoziladi, keyinchalik kiritilgan vaqt emas
  (tugma bosilgan lahza qayd etiladi)

---

## ADR-0014 — Admin hisoboti avtomatik tasdiqlanadi

**Sana:** 2026-07-31 · **Holat:** ✅ Qabul qilindi ([A-25](02-open-questions.md) javobi)

### Kontekst
[ADR-0012](#adr-0012--rol--nom-ruxsat-toplami-emas-) bo'yicha admin ham hisobot
yozishi mumkin. R1 qoidasi ("muallif o'z hisobotini tasdiqlay olmaydi") bunday
hisobotni **osilib qolgan** holatga olib kelardi — tasdiqlovchi yo'q.

### Qaror
Egasining javobi: *"Admin o'z-o'zini tasdiqlamaydi. U qilgan amaliyot **avto
tasdiqlanadi**. Unga tasdiqlovchi kerak emas."*

`admin` turidagi rol muallifi bo'lgan hisobot `DRAFT → APPROVED` to'g'ridan-to'g'ri
o'tadi: `approved_* = proposed_*`, `auto_approved = true`,
`approvals(decision='auto_approved', actor_id=NULL)`.
Narx kelishuvi ham bo'lmaydi — kelishadigan ikkinchi tomon mavjud emas.

### Sabab
- 1–2 adminli tashkilotda "ikkinchi admin tasdiqlaydi" sxemasi ishlamaydi
- Buxgalterni tasdiqlovchi qilish uning rolini o'zgartirardi (u faqat ko'radi)
- Osilib qolgan hisobotlar oy yopilishini bloklardi

### Oqibatlar
- ➕ Oqim sodda: hech narsa osilib qolmaydi
- ➕ Kod kam: `role.kind == 'admin'` → bitta shart
- ➖ **Nazorat halqasidagi yagona ochiq joy** — admin o'z ishiga o'zi narx qo'yadi
  va u tekshirilmaydi
- ⚠️ **Yumshatish — shaffoflik:** `auto_approved` belgisi hisobot kartochkasida;
  oylik hisobotda va oy yopish ekranida **alohida satr** ("avtomatik
  tasdiqlangan: N ta, X so'm"); `approvals` yozuvi audit log'da. Buxgalter
  hammasini ko'radi va oyni yopadi — de-fakto kuzatuvchi

### Rad etilgan variantlar
| Variant | Nega rad etildi |
|---|---|
| Ikkinchi admin tasdiqlaydi | 1–2 adminli tashkilotda ishlamaydi |
| Buxgalter tasdiqlaydi | Uning roli faqat ko'rish va oy yopish — o'zgartirish kerak bo'lardi |
| Admin umuman hisobot yozmaydi | ADR-0012 ga zid (hammada bir xil imkoniyat) |
| `SUBMITTED` holatida qoldirish | Oy yopilishini bloklaydi |

---

## Shablon (yangi ADR uchun)

```markdown
## ADR-XXXX — Sarlavha
**Sana:** YYYY-MM-DD · **Holat:** 🟡 Taklif / ✅ Qabul qilindi / ❌ Rad etildi / ♻️ Almashtirildi

### Kontekst
Qanday muammo? Qanday cheklovlar?

### Qaror
Nima qilinadi?

### Sabab
Nega aynan shunday?

### Oqibatlar
➕ Yaxshi tomonlari  ➖ Yomon tomonlari

### Rad etilgan variantlar
| Variant | Nega rad etildi |
```
