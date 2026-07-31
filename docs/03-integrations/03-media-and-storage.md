# 03. Media va saqlash

Fotolar — bu platformaning **asosiy dalili**. Ular yo'qolsa, hisobot qiymatsiz.
Shu sababli media alohida jiddiy ko'rib chiqiladi.

## 1. Media hajmi baholari

| Ko'rsatkich | Qiymat |
|---|---|
| Bitta hisobotda foto | 5–10 ta |
| Kunlik hisobotlar | 3–5 |
| Kunlik fotolar | 30–50 |
| Siqilgandan keyin bitta foto | ~150–250 KB |
| Kunlik hajm | ~8–12 MB |
| Yillik hajm | ~2–3 GB |

Xulosa: **oddiy Tigris (S3-mos) yetadi**, murakkab CDN kerak emas.

## 2. Saqlash strategiyasi

```
┌──────────────────────────────────────────────────┐
│  ASOSIY OMBOR:  Tigris (S3)  (private bucket)     │
│  • originalga yaqin (siqilgan) nusxa             │
│  • thumbnail (400px) — ro'yxatlar uchun          │
│  • metadata → PostgreSQL `media` jadvali         │
└──────────────────────────────────────────────────┘
                    │
                    │ ixtiyoriy kesh
                    ▼
┌──────────────────────────────────────────────────┐
│  TELEGRAM file_id  (tez ko'rsatish uchun)        │
│  ⚠️ Asosiy manba EMAS                            │
└──────────────────────────────────────────────────┘
```

### ⚠️ Nima uchun Telegram `file_id` ga tayanmaymiz

Vasvasa bor: foto Telegram'da, `file_id` saqlaymiz — bepul ombor. **Bu xato.**

| Xavf | Oqibati |
|---|---|
| `file_id` bot tokeniga bog'langan | Bot almashsa — barcha fotolar yo'qoladi |
| Bot o'chirilsa / token rotatsiya | Barcha dalillar yo'qoladi |
| Telegram siyosati o'zgarishi | Nazoratimiz yo'q |
| Mini App'dan to'g'ridan-to'g'ri kirish qiyin | Har safar bot orqali olish kerak |
| Yuridik nizoda dalil | Tashqi servisga bog'liqlik |

**Qoida:** foto **doim** o'z omborimizga yuklanadi. `file_id` — faqat tezkor
ko'rsatish uchun kesh.

## 3. Yuklash oqimi (Mini App'dan)

```
1. Foydalanuvchi foto oladi (camera)
        ↓
2. KLIENTDA siqish (canvas):
   • maksimal o'lcham: 1600 px (uzun tomon)
   • JPEG sifat: 0.75
   • 3.5 MB → ~200 KB
        ↓
3. POST /media/upload-url
   { submission_id, field_code, mime, size, sha256, exif? }
        ↓
4. Server: ruxsat tekshiradi → presigned PUT URL qaytaradi
        ↓
5. Klient → S3 ga to'g'ridan-to'g'ri PUT (server orqali emas!)
   • progress ko'rsatiladi
   • xato bo'lsa 3 marta qayta urinish
        ↓
6. POST /media/{id}/complete
        ↓
7. Fon sikli:
   • EXIF o'qish (sana, GPS, qurilma) → bazaga
   • EXIF fayldan tozalash
   • thumbnail generatsiya
   • pHash hisoblash → dublikat tekshiruvi
   • bayroqlar (photo_not_fresh, duplicate_photo)
```

**Nima uchun presigned URL:** foto backend orqali o'tmaydi → server yuklanmaydi,
tezroq, arzonroq.

## 4. Klientda siqish (majburiy)

```js
// Konseptual
async function compress(file, maxSide = 1600, quality = 0.75) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = new OffscreenCanvas(bitmap.width * scale, bitmap.height * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return canvas.convertToBlob({ type: 'image/jpeg', quality });
}
```

⚠️ **Diqqat:** `canvas` orqali qayta chizishda **EXIF yo'qoladi**. Shuning uchun:
- EXIF **siqishdan oldin** klientda o'qib olinadi va metadata sifatida yuboriladi,
  **yoki**
- Original fayl EXIF'i bilan yuboriladi va siqish serverda bo'ladi (sekinroq, lekin
  ishonchliroq)

📌 Tavsiya: **EXIF'ni klientda o'qib, alohida maydonda yuborish** + server
`uploaded_at` bilan solishtirish. Klient EXIF'ini soxtalashtirish mumkin, lekin
server vaqti va yuklash ketma-ketligi baribir tekshiriladi.

## 5. Zaif internet uchun chidamlilik

Garajda internet yomon — bu **hisobga olinishi shart**:

| Muammo | Yechim |
|---|---|
| Yuklash yarmida uzildi | Qayta urinish (3×, eksponensial pauza) |
| Butunlay internet yo'q | Foto `IndexedDB`da saqlanadi, navbatga qo'yiladi |
| Mini App yopildi | Ochilganda "3 ta foto yuklanmagan, davom etamizmi?" |
| Sekin (3G) | Progress bar + "fon rejimida davom etadi" |
| Foydalanuvchi kutmoqchi emas | Qoralamani foto yuklanmasdan ham saqlash mumkin |

**Qoida:** hisobotni **yuborish** faqat barcha majburiy fotolar yuklangandan
keyin mumkin. Qoralamani esa istalgan vaqtda saqlash mumkin.

## 6. Media metadata va anti-fraud

Har bir foto uchun saqlanadigan signallar:

| Maydon | Manba | Nima uchun |
|---|---|---|
| `sha256` | Server | Aynan bir xil fayl qayta ishlatilganini aniqlash |
| `phash` | Server (fon sikli) | **O'xshash** rasmni aniqlash (kesilgan, siqilgan) |
| `exif_taken_at` | Klient/fayl | Rasm qachon olingan |
| `exif_lat/lon` | EXIF | Qayerda olingan |
| `uploaded_at` | Server | Ishonchli vaqt (soxtalashtirib bo'lmaydi) |
| `source` | Klient | `camera` / `gallery` / `unknown` |
| `width/height` | Server | Ekran skrinshoti yoki tarmoqdan olingan rasmni aniqlash |

### pHash bilan dublikat qidirish

```
Yangi foto → phash hisoblanadi
        ↓
Oxirgi 90 kundagi barcha fotolar bilan Hamming masofasi
        ↓
masofa ≤ 8  →  🚩 duplicate_photo bayrog'i
                 details: { similar_media_id, submission_id, distance }
```

Bu **eng kuchli anti-fraud vositalaridan biri**: bitta "muammo fotosi" uch xil
mashinaga qo'yilsa — darhol ko'rinadi.

⚠️ Yolg'on ishga tushish (false positive) bo'lishi mumkin: bir xil model
mashinalarning bir xil detali. Shuning uchun bayroq **bloklamaydi**, faqat
adminga ko'rsatadi.

## 7. Kirish nazorati

| Qoida | Amalga oshirish |
|---|---|
| Bucket **private** | Ochiq o'qish yo'q |
| Ko'rish — signed URL | 15 daqiqa amal qiladi |
| Kim ko'radi | Faqat bog'langan hisobotni ko'rish huquqi bor xodim |
| URL log'da qolmasin | Signed URL log'ga yozilmaydi |
| Hotlink | Referrer tekshiruvi shart emas (qisqa muddat yetadi) |

## 8. Saqlash muddati — qo'lda (manual)

✅ **Qaror** ([A-13/A-18](../05-delivery/02-open-questions.md)): avtomatik
arxivlash va o'chirish **yo'q**. Fotolar cheksiz saqlanadi.

- Yillik hajm ~2–3 GB — arzon, avtomatlashtirish ortiqcha
- Admin kerak bo'lsa **qo'lda** o'chiradi → `media.deleted_at`
- Metadata (`media` qatori) **hech qachon o'chirilmaydi** — audit uchun kerak
- Soft delete: fayl S3'dan olib tashlanadi, yozuv qoladi

## 9. Zaxira nusxa

| Nima | Qanday | Chastota |
|---|---|---|
| S3 bucket | Boshqa provayderga sinxron (rclone) | Haftada 1 |
| `media` jadvali | PostgreSQL dump ichida | Kuniga 1 |
| Tiklashni sinash | Tasodifiy 10 ta faylni tiklab tekshirish | Oyiga 1 |

## 10. Video va audio

| Tur | Limit | Ishlatilishi |
|---|---|---|
| Video | 30 s, 50 MB, `video/mp4` | Ovoz chiqarayotgan nosozlik, harakatdagi muammo |
| Audio | 60 s | Usta izohni gapirib aytadi (yozishdan tez) |

Video — **ixtiyoriy**, majburiy qilinmaydi (og'ir va zaif internetda muammo).

---

**Keyingi:** [04-flows/01-repair-lifecycle.md](../04-flows/01-repair-lifecycle.md)
