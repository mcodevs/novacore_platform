# 02. Telegram bot + Mini App

## 1. Vazifalarni bo'lish

| Bot (chat) | Mini App (veb) |
|---|---|
| Ro'yxatdan o'tish (`/start`, telefon) | Forma to'ldirish |
| **Bildirishnomalar** | Foto yuklash |
| Tezkor tugmalar (`✅ Roziman`) | Ro'yxatlar, kartochkalar |
| Qisqa so'rovlar (`/hisob`) | Tasdiqlash ekrani |
| Fayl yuborish (Excel eksport) | Dashboard, analitika |
| Tarmoq zaif bo'lganda zaxira kanal | Admin panel |

> **Prinsip:** murakkab narsa — Mini App'da, tezkor narsa — bot'da.
> Bildirishnoma **doim** bot orqali (Mini App yopiq bo'lsa ham yetadi).

## 2. Bot buyruqlari

| Buyruq | Kim uchun | Tavsif |
|---|---|---|
| `/start` | Hamma | Ro'yxatdan o'tish / asosiy menyu |
| `/app` | Hamma | Mini App'ni ochish |
| `/yangi` | `reporter` | Yangi hisobot boshlash |
| `/mening` | `reporter` | Mening hisobotlarim |
| `/hisob` | `reporter` | Bu oyda: so'ralgan / tasdiqlangan summa |
| `/kelishuv` | `reporter` | Javob kutayotgan narx takliflari |
| `/tasdiq` | `admin` | Tasdiq kutayotganlar |
| `/kunlik` | `admin` | Bugungi qisqa hisobot |
| `/til` | Hamma | Til almashtirish (uz/ru) |
| `/yordam` | Hamma | Qo'llanma |

Buyruqlar ro'yxati `setMyCommands(scope=chat)` orqali **rolga qarab** beriladi —
usta admin buyruqlarini ko'rmaydi.

**Menu button** (BotFather → Menu Button) → Mini App'ni ochadi. Bu eng ko'p
ishlatiladigan kirish nuqtasi bo'ladi.

## 3. Bildirishnomalar matritsasi

| Hodisa | Kimga | Tugmalar |
|---|---|---|
| Hisobot yuborildi | Admin | `✅ Tasdiqlash` `👁 Ko'rish` |
| **Admin narxni kamaytirdi** ⭐ | Muallif | `✅ Roziman` `❌ Rozi emasman` |
| **Muallif narxga rozi bo'lmadi** | Admin | `👁 Ko'rish` |
| **Kelishuvga 24 soat javob yo'q** | Muallif (eslatma) | `✅ Roziman` |
| Hisobot tasdiqlandi | Muallif | — |
| Hisobot qaytarildi / rad etildi | Muallif | `✏️ Tuzatish` |
| Hisobotda kritik bayroq (Faza 3) | Admin | `👁 Ko'rish` |
| Mashina 24 soatdan beri ustaxonada | Admin | `👁 Ko'rish` |
| Qoralama 24 soat turdi | Muallif | `Davom ettirish` |
| Oy yopilishiga 3 kun | Admin, buxgalter | `Tekshirish` |
| Fleet sinxron xatosi (Faza 3) | Admin | — |

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
