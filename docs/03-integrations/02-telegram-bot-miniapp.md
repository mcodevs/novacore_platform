# 02. Telegram bot + Mini App

## 1. Vazifalarni bo'lish

> ⭐ **Prinsip (egasining qarori, 2026-08-01): barcha AMALLAR — Mini App'da.**
> *«Botdan ham, Mini App'dan ham bir amalni qilish odamni chalkashtiradi.»*
> Botda faqat **kirish** va **bildirishnoma** qoladi.

| Bot (chat) — amal YO'Q | Mini App — barcha amallar |
|---|---|
| Ro'yxatdan o'tish (`/start`, telefon) | Hisobot yozish, foto, narx qo'yish |
| **Bildirishnomalar** (+ «Ochish» tugmasi) | Ko'rib chiqish, tasdiqlash, narxni kamaytirish |
| Til, yordam | Narxga rozilik / nizo |
| Excel'ni **hujjat sifatida yetkazish** | Davr, oy yopilishi, to'lov varaqalari |
| Mini App'ni ochish tugmasi | Arxiv, statistika, xodimlar, konstruktor |

**Nima uchun kirish botda qoladi:** Telegram `initData` da telefon raqami
**yo'q** — bog'lanish faqat botdagi `request_contact` orqali mumkin
(texnik cheklov, tanlov emas).

**Nima uchun eksport botga tushadi:** Telegram WebView'da fayl yuklab olish,
ayniqsa iOS'da, ishonchsiz. Tugma Mini App'da, fayl esa suhbatga keladi —
bu *amal* emas, *yetkazib berish*.

⚠️ **Yon ta'sir:** botdagi foto oqimi ham o'chdi — u
[A-10](../05-delivery/02-open-questions.md) kamera xavfining zaxirasi edi.
Endi zaxira faqat Mini App ichida: «🖼 Galereyadan» tugmasi.
**Kamera sinovi endi kechiktirib bo'lmaydi.**

## 2. Bot buyruqlari

| Buyruq | Tavsif |
|---|---|
| `/start` | Ro'yxatdan o'tish / menyu |
| `/app` | Mini App'ni ochish |
| `/til` | Til almashtirish (uz/ru) |
| `/yordam` | Qo'llanma |

**Hammasi shu — to'rtta.** Rolga xos buyruq yo'q: amal qolmagach, rol farqi
ham menyuda emas, Mini App ichida. Menyu klaviaturasi uch tugmadan iborat:
`🧩 Mini App` · `🌐 Til` · `❓ Yordam`.

O'chirilgan buyruqlar (`/yangi`, `/tasdiq`, `/kelishuv`, `/hisob`, `/mening`,
`/kunlik`, `/davr`, `/eksport`) endi javob bermaydi — fallback matni chiqadi.

**Menu button** (BotFather → Menu Button) → Mini App'ni ochadi. Bu eng ko'p
ishlatiladigan kirish nuqtasi bo'ladi.

## 3. Bildirishnomalar matritsasi

Har bir bildirishnoma ostida **bitta** tugma: `🧩 Ochish` — Mini App'da o'sha
kartochkani ochadi (`?submission=<id>`). Tez tugmalar (`✅ Roziman`,
`✏️ Narxni kamaytirish`) **olib tashlandi**: bitta amal — bitta joyda.

| Hodisa | Kimga |
|---|---|
| Hisobot yuborildi | Admin |
| **Admin narxni kamaytirdi** ⭐ | Muallif |
| **Muallif narxga rozi bo'lmadi** | Admin |
| **Kelishuvga 24 soat javob yo'q** | Muallif (eslatma) |
| Hisobot tasdiqlandi / avtomatik qabul qilindi | Muallif |
| Hisobot qaytarildi / rad etildi | Muallif |
| Hisobotda kritik bayroq (Faza 3) | Admin |
| Mashina 24 soatdan beri ustaxonada | Admin |
| Qoralama 24 soat turdi | Muallif |
| Oy yopilishiga 3 kun | Admin, buxgalter |
| Fleet sinxroni (yangi/yo'qolgan mashina yoki xato) | Admin |

**Guruh bildirishnomalari:** admin guruhiga umumiy signal (kritik bayroq, uzoq
downtime). `driver_status_reporter`dagi kabi — bu yondashuv ishlaydi.

> ❌ Zayavka va haydovchi bildirishnomalari **yo'q** — bu rollar tizimda yo'q
> ([ADR-0013](../05-delivery/03-decisions.md#adr-0013--haydovchi-tizimda-rolga-ega-emas)).

## 4. Mini App texnik jihatlari

### Ochilish va kontekst

```js
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();                       // to'liq balandlik
// initData → serverga yuboriladi (tekshiruv serverda!)
// tg.themeParams → interfeys ranglarini moslash
// tg.BackButton, tg.MainButton → native tugmalar
```

- **`tg.MainButton`** — "Yuborish", "Tasdiqlash" kabi asosiy amal uchun.
  Native tugma klaviatura ustida turadi — mobil UX uchun juda yaxshi
- **`tg.BackButton`** — qadamlar orasida orqaga
- **`tg.HapticFeedback`** — tasdiqlashda tebranish (kichik, lekin sezilarli)
- **Tema** — Telegram temasiga moslashish (`themeParams`)
- **`tg.showConfirm`** — muhim amallardan oldin (rad etish, o'chirish)

### ⚠️ Kamera masalasi — asosiy texnik xavf

Ta'mir hisobotining butun ishonchliligi **foto shu yerda olinishiga** bog'liq.
Mini App'da bu quyidagicha amalga oshiriladi:

```html
<input type="file" accept="image/*" capture="environment">
```

`capture` atributi mobil brauzerda **kamerani to'g'ridan-to'g'ri ochadi**.

**Lekin:** Telegram'ning ichki WebView'i (ayniqsa iOS'da) turli versiyalarda
turlicha ishlaydi. Ba'zi holatlarda `capture` e'tiborsiz qoldirilib, galereya
tanlash oynasi ochilishi mumkin.

**Shuning uchun majburiy:**

| Chora | Tafsilot |
|---|---|
| 🔬 **Erta prototip** | Loyihaning **1-haftasida** haqiqiy Android va iOS'da sinash |
| 🔁 **Zaxira yo'l** | Kamera ishlamasa → "Fotoni botga yuboring" oqimi (bot'da foto qabul qilinadi) |
| 🕵️ **Server tekshiruvi** | EXIF sanasi yo'q yoki eski → `photo_not_fresh` bayrog'i |
| 📊 **Statistika** | `media.source` (camera/gallery/unknown) yozib boriladi |

> Bu — loyihaning **eng katta texnik noaniqligi**. Uni birinchi haftada
> tekshirmaslik keyinchalik butun anti-fraud g'oyasini buzishi mumkin.
> 📌 [A-10](../05-delivery/02-open-questions.md)

### Geolokatsiya

Mini App'da joylashuv olish uchun ikki yo'l:
1. **Telegram'ning `LocationManager`** (yangi Bot API versiyalarida) — foydalanuvchi
   ruxsatidan keyin
2. **Brauzer `navigator.geolocation`** — WebView'da ishlaydi, lekin ruxsat so'raladi
3. **Zaxira:** bot'da `request_location` tugmasi

Geo **majburiy emas** — yo'q bo'lsa hisobot baribir qabul qilinadi, faqat
`geo_missing` belgisi qo'yiladi.

### Ishlash tezligi

| Talab | Sabab |
|---|---|
| Bundle < 300 KB (gzip) | Garajdagi zaif internet |
| Birinchi ochilish < 2 s | Usta kutmaydi |
| Offline qoralama (`localStorage`) | Tarmoq uzilsa ish yo'qolmasin |
| Foto siqish klientda | 3 MB → ~200 KB |
| Skeleton loader | Bo'sh ekran ko'rsatmaslik |

### Til (i18n)

- `uz` (lotin) va `ru` — **1-kundan**
- Til `employees.lang`da saqlanadi, `/til` bilan almashadi
- Telegram `initData.user.language_code` — boshlang'ich taxmin
- Shablon yorliqlari bazada ikki tilda (`label_uz`, `label_ru`)

## 5. Bot texnik jihatlari

| Jihat | Qaror |
|---|---|
| Rejim | **Webhook** (polling emas) — tezroq, resurs tejaydi |
| Kutubxona | aiogram 3 (FastAPI bilan bir ASGI ilovada) |
| Holat (FSM) | Postgres yoki xotira — **Redis yo'q** ([ADR-0004](../05-delivery/03-decisions.md)) |
| Privacy mode | Yoqilgan qolsin — bot guruh xabarlarini o'qimaydi |
| Xabar yuborish limiti | ~30 xabar/sek umumiy, 20/daq bitta guruhga. Navbat orqali |
| Xato bo'lsa | `notifications` outbox — qayta urinish |
| Fayl yuborish | Excel eksport → `send_document` |

**Blok qilingan foydalanuvchi:** bot bloklansa (`403 Forbidden`) — xodimga
`tg_blocked` belgisi qo'yiladi, adminga xabar beriladi.

## 6. Botni sozlash (BotFather)

| Sozlama | Qiymat |
|---|---|
| Name | NovaCore |
| About | NovaCore xodimlari uchun ichki platforma |
| Description | Ta'mir hisobotlari, narx kelishuvi va ish nazorati |
| Botpic | NovaCore logotipi |
| Menu Button | `NovaCore` → Mini App URL |
| Commands | Yuqoridagi ro'yxat (uz + ru) |
| Domain | Mini App domeni (`/setdomain`) |
| Privacy | Enabled |

> `driver_status_reporter` loyihasida BotFather profil matnlari allaqachon
> tayyorlangan — shu uslubda davom ettirish mumkin.

## 7. Bitta bot — hamma uchun

✅ **Qaror qabul qilingan** ([A-11 / A-19](../05-delivery/02-open-questions.md)):
**bitta bot va uning ichida bitta Mini App**, hamma rollar uchun.

- Menyu va buyruqlar **rolga qarab** o'zgaradi
- Alohida admin bot yo'q — admin shu Mini App'da admin ekranlarini ko'radi
- Faqat muhitlar uchun ikkita bot: `local` va `production`

---

**Keyingi:** [03. Media va saqlash](03-media-and-storage.md)
