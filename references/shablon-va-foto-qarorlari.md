---
name: shablon-va-foto-qarorlari
description: 2026-08-03 — foto faqat kameradan (ADR-0017), probeg shablondan olib tashlandi (ADR-0018)
metadata:
  type: project
---

# Foto va shablon qarorlari — 2026-08-03

Egasining ikkita qarori. Ikkalasi ham **maydonni olib tashlash** yo'nalishida:
forma qanchalik qisqa bo'lsa, usta undan shunchalik kam qochadi.

## ADR-0017 — foto faqat kameradan

«🖼 Galereyadan» tugmasi **butunlay** olib tashlandi. Endi bitta tugma va bitta
`<input capture="environment">`.

Serverda ham mustahkamlandi: `POST /media/upload` `source=gallery` ni rad etadi
(klientga ishonilmaydi). `MediaSource.gallery` enum qiymati **saqlandi** — eski
media yozuvlari o'qilishi kerak.

🔴 **Eng muhim oqibat:** galereya tugmasi CLAUDE.md dagi «ochiq texnik xavf»ning
**yagona zaxira yo'li** edi (botdagi foto oqimi allaqachon o'chgan). Endi zaxira
umuman yo'q: agar Telegram WebView'da (iOS) `capture` ishlamasa —
**foto yuklab bo'lmaydi va ta'mir hisoboti yuborilmaydi**.

→ Real iOS qurilmada kamera sinovi endi **bloklovchi** vazifa. Ishlamasa
ADR-0017 qayta ko'rib chiqiladi.


### ♻️ ADR-0020 bilan almashtirildi (2026-08-04)

Egasi qarorni **qaytardi**: foto endi kameradan ham, galereyadan ham. Yuqoridagi
🔴 xavf aynan shu sabab yopildi — ishlamaydigan modul nazariy firibgarlikdan
qimmatroq.

- Mini App'da ikkita tugma: **📷 Kamera** (urg'u rangida — tavsiya etilgan yo'l)
  va **🖼 Galereya** (ikkilamchi, `multiple`). Ikki alohida `<input>`, chunki
  `capture` atributi **elementga** biriktiriladi va bosishdan oldin
  o'zgartirib bo'lmaydi
- Server `source=gallery` ni **rad etmaydi**, lekin `media.source` ga yozadi —
  taqiq o'rniga **iz** (`photo_no_exif` bayrog'i bilan birga ma'no beradi)
- Yorliqlar qisqartirildi: «Suratga olish» → «Kamera». Uzun variant 375 px'da
  ikki qatorga sinardi ([[miniapp-dizayn-tizimi]])
- `tests/test_media_source.py` **teskarisiga** yozildi: galereya qabul
  qilinishi + manba to'g'ri saqlanishi. `gallery` enum baribir saqlanadi
- CLAUDE.md: «Ataylab YO'Q» ro'yxatidan foto qatori olib tashlandi, «Ochiq
  texnik xavf» 🔴 → 🟢

⚠️ **Xulosa (kelajak uchun):** ADR-0017 dagi to'siq texnik emas, **ishonchga
asoslangan** edi — galereyani yopish faqat qulay yo'lni yopadi (skrinshot,
boshqa qurilmadan yuborish baribir ochiq), lekin evaziga modulni butunlay
ishlamay qolish xavfiga qo'yadi. Foto-dalilning haqiqiy tayanchi — **admin
ko'rigi va chek fotosi** ([[qarz-daftari-modeli]] dagi F5a).


✅ **Prodda** — 2026-08-04, commit `f6f92fb` (main, push qilingan), bundle
`index-DBsBvVHc.js` (lokal build hashi bilan bir xil). Migratsiya yo'q.

⏳ **Kutilayotgan javob:** real iOS qurilmada «📷 Kamera» tugmasi kamerani
ochadimi. Natija ADR-0020 ga yoziladi — lekin endi u **bloklovchi emas**:
ishlamasa galereya orqali foto baribir yuklanadi.

## ADR-0018 — probeg shablondan olib tashlandi

`odometer_value` + `odometer_photo` maydonlari, `field_mapping.odometer`,
`submissions.odometer_km` ustuni va `monotonic_for_vehicle` tekshiruvi o'chdi
(migratsiya `0005_drop_odometer.py`).

Sabab: har hisobotda majburiy spidometr fotosi + raqam — formadagi **eng qimmat,
foydasi nolga yaqin** maydon edi.

⚠️ **Saqlandi:** `vehicles.odometer_km` / `odometer_updated_at` — bu avtopark
reyestri, Yandex Fleet sinxronidan keladi, hisobotga aloqasi yo'q. «1 km ga
xarajat» analitikasi kelajakda **faqat shunga** tayanadi.

⚠️ `MediaKind.odometer` enum qiymati saqlandi (eski media yozuvlari uchun),
lekin endi hech qaysi shablon uni ishlatmaydi.

Bog'liq: [[qarz-daftari-modeli]]

## Chek fotosi majburiyligi — F5a yopildi (2026-08-03)

ADR-0016 ochgan teshik endi **serverda** yopildi. `engine._receipt_issues()`:
hisobotda `self_funded` va narxi > 0 bo'lgan qism qatori bo'lsa, chek fotosisiz
hisobot **yuborilmaydi** (`receipt_required`).

Ikkita loyihaviy qaror:

1. **Qoida qatorlarga bog'langan**, maydonning `required` bayrog'iga emas —
   chek maydoni shablonda ixtiyoriy turadi va faqat kerak bo'lganda talab
   qilinadi. Shablon qanday bo'lishidan qat'i nazar ishlaydi.
2. **Chek borligi maydon bo'yicha aniqlanadi** (`options.kind = "receipt"`
   bo'lgan `photo` maydoni), media `kind` i bo'yicha emas — u klientdan keladi
   va unga ishonilmaydi (R7). Bu testda ham bilinib qoldi: `conftest.add_photo`
   doim `MediaKind.other` yozadi.

`car_repair.json` ga ixtiyoriy `photo_receipt` maydoni qo'shildi (12 maydon).

## Mini App — «o'z hisobimdan» chekboksi

`LinesField.tsx`: qism qo'shishda chekboks; belgilanmaguncha **narx maydoni
ochilmaydi**. Belgi narxni boshqaradi, aksincha emas.

⚠️ Eng nozik joy: `toInput()` da `self_funded` **saqlanishi shart** — server
qatorlarni o'chirib qayta yaratadi (`PUT /lines`), belgi tushib qolsa qarz
jimgina yo'qolardi.
