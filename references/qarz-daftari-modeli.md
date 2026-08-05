---
name: qarz-daftari-modeli
description: 2026-08-03 — oy yopish olib tashlandi, o'rniga hisobot bo'yicha qarz daftari + avans (ADR-0015/0016)
metadata:
  type: project
---

# Qarz daftari — davr modelini almashtirdi

**Sana:** 2026-08-03 · **ADR-0015** va **ADR-0016** (`docs/05-delivery/03-decisions.md`)

## Nima uchun

Egasi oyni tasodifan yopib qo'yib, ishlay olmay qoldi ([[prod-data-reset-2026-08]]).
Sabab chuqurroq edi: to'lov real hayotda **oy chegarasiga bo'ysunmaydi** —
ustaga hafta o'rtasida, qisman, bir nechta ish uchun birdan pul beriladi.
Buxgalterning yagona savoli — *«kimga qancha qarzmiz?»* — davr modelida umuman
hisoblanmasdi, `payouts` esa all-or-nothing edi.

## Yangi model

**Oy yopish tushunchasi butunlay yo'q.** `periods`, `payouts`, `period_id`,
precheck, davr holat mashinasi — o'chirildi (~1440 qator).

- Har `APPROVED` hisobot = muallifga qarz: `payable_amount − paid_amount`
- To'lov: `payments` + `payment_allocations` daftari; o'zgarmas, xato → `void`
  (sabab majburiy, qarz qayta ochiladi)
- Uch usul: chekbox · summa kiritish (**FIFO**, eng eskidan, oxirgisi qisman) ·
  bitta hisobot kartochkasidan
- Oylik kesim `submitted_at` bo'yicha filtrlanadi — alohida jadval kerak emas

## Eng muhim g'oya — «narx bor = qarz bor»

Usta qismni **o'z cho'ntagidan** olishi mumkin (ADR-0016). Belgi va pul
**bitta harakat**: `self_funded` serverda narxdan kelib chiqadi —
`kind == part AND (belgi OR narx > 0)`; belgisiz qism narxi `0` ga tushiriladi.
Shu sababli «belgi yo'q, lekin qarz bor» holati **printsipial imkonsiz**.

⚠️ **Ta'minotchi ham qarzdor** (egasining qarori): u ham o'z puliga oladi va
kompaniya qaytaradi. Uning xaridi doim narx bilan kiritilgani uchun avtomatik
`self_funded` — alohida qoida yozilmadi, bitta qoida ikkala rolni qamradi.

⚠️ **ADR-0010 teshigi qisman qayta ochildi** (F5a): usta kompaniya olgan qismga
soxta belgi qo'yishi mumkin. Yagona to'siq — **chek fotosi** + admin ko'rigi.

## Avans (P7) — 2026-08-03 qo'shimchasi

Qarzdan **ortiq** to'lov rad etilmaydi: ortiqcha summa xodim hisobida **avans**
bo'lib turadi va yangi qarz tasdiqlanishi bilan **avtomatik** (FIFO) ishlatiladi.

- Avans = `Σ(to'lovlar) − Σ(allokatsiyalar)` — **alohida jadval yo'q**
- Avans allokatsiyasi o'sha to'lov yozuviga biriktiriladi → `void` avansni ham
  izsiz qaytaradi
- Qarzi yo'q xodimga to'lov ham mumkin — sof avans
- `apply_advance()` `approve` / `auto_approve` / `accept_price` oxirida chaqiriladi

## Invariantlar (yangi raqamlash)

`P1` faqat `APPROVED` to'lanadi · `P2` `paid ≤ payable` (DB CHECK, **bitta
hisobot** darajasida) · `P3` `payable` serverda hisoblanadi ·
`P4` `sum(allocations) ≤ payment.amount`, qoldiq — avans · `P5` to'lov
o'zgarmas, faqat `void` · `P6` kompaniya qismida narx yo'q · **`P7` avans**.

`CLAUDE.md` da **R4** va **R5** shunga mos qayta yozildi (eski R4 «yopiq davr»
endi yo'q).

## Ataylab qilinmagan

- **Bonus / jarima** — eski `payouts` da bor edi, olib tashlandi. Qarz doim
  aniq hisobotga bog'lanadi; kerak bo'lsa kelajakda `adjustment` yozuvi


## To'lov ekrani: ikkita tugma → bitta amal (2026-08-04)

Egasining kuzatuvi: chekboxli ro'yxat ostida **ikkita** to'lov tugmasi turardi
(«Belgilanganlarni to'lash» + «To'lovni qayd etish») — bir amalni ikki xil
qilish chalkashtiradi (bot ↔ Mini App dublikati bilan bir xil sabab).

**Yechim:** «Belgilanganlarni to'lash» olib tashlandi. Chekbox tanlovi endi
**Summa maydonini to'ldiradi**, uning ustida esa xulosa qatori turadi:
«Belgilangan · N ta ish → jami» (`.pick-total`, `--accent-soft` qatlam).
Kartada bitta haqiqiy amal qoldi.

- Funksiya yo'qolmadi: ilova `submission_ids` + `amount` (**server 3-rejim**)
  yuboradi → summa aynan belgilanganlarga taqsimlanadi. Ustiga qo'shimcha imkon:
  summani tahrirlab belgilanganlarga **qisman** to'lash
- `amount`siz `submission_ids` (1-rejim) API'da **qoladi** — o'chirilmadi
- Dizayn qoidasi: xulosa amal emas → to'liq urg'u rangi berilmaydi, faqat
  yupqa `accent-soft` qatlam ([[miniapp-dizayn-tizimi]])
- `docs/04-flows/03-payroll-and-reports.md` §3.1 shunga mos yangilandi

Shu kuni ikkinchi qadam — **maydon bo'sh, matn tasdiqda**:

- Summa maydonida na o'rnak summa (placeholder), na ostidagi izohlar
  (`fifo_hint` · `overpay_hint` · `advance_only_hint` o'chirildi)
- O'rniga «To'lovni qayd etish» **tasdiq oynasi** so'raydi (`confirmAction` →
  `tg.showConfirm`): summa + taqsimot usuli, qarzdan oshsa avans qismi ham
- Ortiqcha summa chegarasi tanlovga bog'liq: belgilangan hisobotlar bo'lsa pul
  **faqat ularga** taqsimlanadi, boshqa qarz qolsa ham oshgani avansga tushadi
- ⚠️ `showConfirm` `try` **ichida** chaqiriladi — eski klientda istisno tashlaydi
  va u ushlanmasa tugma «hech narsa qilmayotgandek» ko'rinadi (Broadcast
  ekranida bir marta shunday xato bo'lgan)

CSS tuzog'i (uchinchisi): `.card label:not(.check-row):not(.switch)` yorliqqa
16 px pastki bo'shliq beradi va u `.stack` ning o'z bo'shlig'iga qo'shilib
32 px bo'lardi → `.card .stack > label.field { margin-bottom: 0 }`, ataylab
o'sha qoidadan **keyin** ([[miniapp-dizayn-tizimi]]).

Tasdiq matni **bitta** (egasining qarori): «{sum} to‘lansinmi? Eng eski qarzdan
boshlab taqsimlanadi.» Tanlov bor-yo'qligiga qarab ikkiga bo'linmaydi, chunki
qoida haqiqatan bitta — server ikkala holatda ham `submitted_at` bo'yicha
eskisidan taqsimlaydi; chekbox faqat **doirani** toraytiradi (belgilanganlar
ichida, yana FIFO). Faqat avans qatori shartli qo'shiladi.

✅ **Prodga chiqarildi** — 2026-08-04, commit `b2b05bf` (main), `fly deploy`
(image `deployment-01KZ6DHRMDE0PJ0A9G319K6BCK`). Migratsiya bo'lmadi — faqat
Mini App va hujjat. Prodda tekshirildi: bundle ichida `.pick-total` va yangi
tasdiq matni bor, eski «Belgilanganlarni to'lash» yo'q.

ⓘ Deploy oxirida `fly` «app is not listening on 0.0.0.0:8000» ogohlantirishini
berdi — tekshiruv `alembic upgrade head` tugamagan lahzaga tushadi. Keyingi
health check o'tsa, bu **normal**; qo'rqib rollback qilish shart emas.


## «Qisman to'langan» — status EMAS, ko'rsatish holati (2026-08-04)

Xodim hisobotini «Tasdiqlangan» deb ko'rardi, holbuki pulning yarmi kelgan
bo'lardi: belgi to'g'ridan-to'g'ri `Tasdiqlangan → To'langan` sakrardi. Endi
oraliq qadam bor: **`Tasdiqlangan → 🧾 Qisman to'langan → 💵 To'langan`**.

⚠️ **Bazaga yangi status qo'shilmadi.** Serverda `status` qisman to'lov davrida
hamon `APPROVED` (`_sync_status` uni faqat qarz to'liq yopilganda `PAID`
qiladi). Farq `paid_amount`/`payable_amount` dan **klientda** hisoblanadi —
`miniapp/src/display-status.ts` (sof funksiya + 4 test). Yangi status
migratsiya, `_sync_status` va barcha filtrlarni buzardi, foyda esa faqat
ko'rinishda edi. `docs/02-architecture/05-state-machines.md` §3 da bu holat
allaqachon «QISMAN» ko'rinishi deb yozilgan edi — UI shunga yetdi, hujjatga
izoh qo'shildi.

- Ohang **sariq** (`wait`), yashil emas: ish tugagan, lekin pul to'liq
  berilmagan. Yashil bo'lsa qarz qolgani ko'zga tashlanmaydi
- Hisobot kartochkasida yangi blok: **To'lanadi · To'langan · Qoldi** (`.pay-state`,
  chiziq bilan ajratilgan — yuqorisi ish narxi, bu yeri pul harakati)
- ⚠️ «To'lanadi» (`payable_amount`) «Tasdiqlandi» dan **katta bo'lishi normal**:
  unga «o'z hisobimdan» qismlar ham kiradi (R5) — real hisobotda 180 000 ish
  haqi + 350 000 usta olgan kolodka = 530 000


✅ **Prodda** — 2026-08-04, commit `9fd5a78` (main, push qilingan), bundle
`index-Cmy2KlwR.js` (lokal build hashi bilan bir xil). Migratsiya yo'q.
Shu deploy bilan git ↔ prod farqi ham yopildi (oldingi deploy commit
qilinmagan papkadan chiqqan edi — [[miniapp-dizayn-tizimi]] dagi ogohlantirish).


## Avans — alohida tab (2026-08-04)

Qarzdorlar ro'yxatida avans qatorlari («+60 000 · Avans») qarz qatorlari bilan
aralash turardi va «kimga qancha qarzmiz?» degan **asosiy** savolga javob
berishni qiyinlashtirardi. Endi ekranda uchta tab: **Qarzlar · Avans ·
To'langan**.

- «Qarzlar» — faqat `debt > 0`; kartada yolg'iz «Umumiy qarz» qatori
- «Avans» — `advance > 0`; «Umumiy avans» + `advance_hint` izohi
- ⚠️ Xodim **ikkala ro'yxatda** ham bo'lishi mumkin (avans yangi ish
  tasdiqlangunicha ishlatilmaydi) — avans tabida uning qarzi izohda ko'rinadi
- Server bitta ro'yxat qaytaradi (`DebtSummary.employees`), ajratish klientda
- Xodim kartochkasidagi avans bloki **qoldi** — to'lov qayd etishda kerakli
  kontekst, global ro'yxat emas
- `tab_paid` yorlig'i «To'langanlar» → «To'langan» (ru: «Выплаты»): uchta tabda
  375 px'da yorliq torayadi. O'lchandi — har tab 108 px, ikkala tilda ham
  bitta qator ([[miniapp-dizayn-tizimi]])


✅ **Prodda** — 2026-08-04, commit `0e0698d` (main, sinxron), bundle
`index-DGfSxgBk.js` (lokal build hashi bilan bir xil). Migratsiya yo'q.
Shu deploy bilan `.tile-money` tuzatishi ham chiqdi.

## Holat (2026-08-03)

✅ **Prodga chiqarildi** — 2026-08-03, commit `e2dd3e0` (main), fly deploy.
Migratsiyalar `0004` + `0005` avtomatik bajarildi (`alembic upgrade head`
konteyner CMD ida). Prodda tasdiqlandi: `payments`/`payment_allocations` bor,
`periods`/`payouts` o'chgan, `payable_amount`/`paid_amount`/`self_funded` bor,
`odometer_km` o'chgan, `car_repair` 12 maydon + `photo_receipt`.
Zaxira: MPG `20260803-153435F` (deploy oldidan).

Backfill to'g'ri ishladi: yagona mavjud hisobot (`WO-2026-000022`, `paid`,
240 000) `payable = paid = 240000` bo'ldi — qarz bo'lib qayta paydo bo'lmadi.

✅ 253 backend + 8 miniapp test · chek fotosi majburiyligi (F5a) ·
«o'z hisobimdan» chekboksi — [[shablon-va-foto-qarorlari]]

❌ **Qolgan yagona xavf:** iOS'da kamera sinovi (ADR-0017 — zaxira yo'l yo'q).

Bog'liq: [[shablon-va-foto-qarorlari]]


## ⚠️ Ikki marta takrorlangan tuzoq — `MissingGreenlet`

`payment` modulida **ikki marta** bir xil sabab bo'yicha xato chiqdi: yangi
qurilgan `Payment` obyektining bog'lanishiga murojaat qilinganda SQLAlchemy
lazy yuklashga urinadi va async kontekstdan tashqarida yiqiladi.

1. **Testda topilgan:** `flush()` dan keyin `payment.allocations` ga murojaat.
   Yechim — allokatsiyalarni **obyekt qurilishida** biriktirish.
2. **Prodda topilgan (2026-08-03):** API `_payment_out()` da
   `payment.employee.full_name`. Yechim — `employee` bog'lanishini ham
   qurilishda biriktirish (`Payment(employee=obj, ...)`).

**Qoida:** yangi ORM obyektini qurganda, chaqiruvchi o'qishi mumkin bo'lgan
**har bir bog'lanish** konstruktorda berilishi kerak. `lazy="selectin"` faqat
**bazadan yuklangan** obyektlarga yordam beradi, yangi qurilganiga emas.

### Nima uchun testlar ushlamadi

Servis darajasidagi testlar `create_payment()` ni chaqirardi, lekin **javobni
serializatsiya qilmasdi** — xato esa aynan API qatlamida edi. Endi
`test_accountant_payment_flow` bor: qarz → to'lov → avans → tarix → `void`
oqimi **HTTP orqali** o'tadi. Test tuzatishsiz aynan `MissingGreenlet` bilan
yiqilishi tekshirib ko'rilgan.

ⓘ Ikkinchi kamchilik: klient JSON bo'lmagan javobni (`Internal Server Error`)
ko'r-ko'rona `JSON.parse` qilardi va foydalanuvchiga «JSON Parse error…»
ko'rsatib, asl muammoni yashirardi. `api.ts` endi tushunarli xato beradi.


## To'lov kartochkasi — tarixdagi qator ochiladi (2026-08-04)

«To'langan» tabidagi qatorlar o'lik matn edi: xodim, summa, sana va «3 ta ish»
— lekin **qaysi** ishlar ekani hech qayerda ko'rinmasdi. Endi qator bosiladi va
faqat o'qish uchun kartochka ochiladi (P5 — to'lov tahrirlanmaydi):

- sarlavhada xodim + summa · sana · izoh · bekor qilingan bo'lsa: sana,
  «qarz qayta ochilgan» izohi va sababi
- **«Qaysi ishlarga»** — allokatsiyalar: `#WO-…` · summa · `✅ to'liq yopildi`
  yoki `qisman yopildi`

⚠️ Buning uchun `AllocationOut` ga **`number`** qo'shildi: ilgari faqat ichki
`submission_id` qaytardi, ya'ni ekranda «#12» chiqardi. Yo'l-yo'lakay xato ham
tuzaldi — **`fully_paid` ro'yxat endpointida doim `false`** edi (u faqat to'lov
yaratilganda to'ldirilardi); endi ikkalasi bitta joydan hisoblanadi.

⚠️ **Uchinchi `MissingGreenlet` tuzog'i oldindan chetlab o'tildi.**
`PaymentAllocation` da `submission` bog'lanishi **yo'q**, uni qo'shib
`item.submission.number` deb o'qish oson yo'l ko'rinadi — lekin bu yangi
qurilgan allokatsiyada lazy yuklashga tushib, aynan yuqoridagi ikki xato kabi
yiqilardi (ro'yxatda esa N+1 bo'lardi). Shuning uchun endpoint
`_fill_allocations()` bilan **bitta so'rovda** to'ldiradi. Yangi maydonni
allokatsiyaga qo'shmoqchi bo'lsangiz — shu funksiyani kengaytiring, bog'lanish
qo'shmang.

Migratsiya yo'q — faqat javob maydoni. `test_accountant_payment_flow` ga
`number` va `fully_paid` tekshiruvlari qo'shildi (backend 256/256).

ⓘ Ataylab qilinmadi (egasining qaroriga qoldirildi): (1) kartochkada **to'lovni
bekor qilish** tugmasi — `api.voidPayment()` klientda bor, lekin UI'da hech
qayerdan chaqirilmaydi, ya'ni xato to'lovni ilovadan tuzatib bo'lmaydi;
(2) allokatsiya qatoridan hisobotning o'ziga o'tish — ekran almashganda
kartochka holati yo'qoladi (`DebtScreen` unmount bo'ladi).

✅ **Prodda** — 2026-08-04, commit `e592f83` (main, sinxron), bundle
`index-De__Bx1I.js` (lokal build hashi bilan bir xil). Migratsiya yo'q.
`/api/v1/payments` avtorizatsiyasiz 401 qaytaradi — yangi maydonlar ochilib
qolmagan.

## To'lov kartochkasidan ish hisobotiga kirish (2026-08-05)

«Қайси ишларга» qatorlari bosiladigan bo'ldi → `detail` marshruti (hisobot
kartochkasi). Sabab: `#WO-2026-000032` raqamining o'zi «qaysi ish» degan
savolga javob bermaydi — mashina, sana va qatorlar faqat kartochkada.

⚠️ **Umumiy tuzoq (boshqa ekranlarga ham tegishli):** App marshrutni
almashtirganda ekran komponenti **butunlay yechiladi**, ichki holati bilan.
Bu yerda qaytishda ikki qadam yo'qolardi — «To'langan» yorlig'i va ochiq
to'lov kartochkasi. Yechim: modul darajasidagi `lastTab` / `lastPaidId` va
tarix yuklangach **bir martalik** tiklash (aks holda bo'limga oddiy kirganda
kartochka o'z-o'zidan ochilib qolardi).

Bog'liq: [[miniapp-dizayn-tizimi]] · [[kirill-lokal-translit]]

✅ **Prodda** — 2026-08-05, commit `8988364` (main), bundle `CpS4c5lb`.
Migratsiya yo'q, faqat Mini App.
