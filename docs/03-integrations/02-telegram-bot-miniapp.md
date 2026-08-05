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
| Excel'ni **hujjat sifatida yetkazish** | Qarzlar, to'lovni qayd etish |
| Mini App'ni ochish tugmasi | Arxiv, statistika, xodimlar, konstruktor |

**Nima uchun kirish botda qoladi:** Telegram `initData` da telefon raqami
**yo'q** — bog'lanish faqat botdagi `request_contact` orqali mumkin
(texnik cheklov, tanlov emas).

**Nima uchun eksport botga tushadi:** Telegram WebView'da fayl yuklab olish,
ayniqsa iOS'da, ishonchsiz. Tugma Mini App'da, fayl esa suhbatga keladi —
bu *amal* emas, *yetkazib berish*.

⚠️ **Yon ta'sir:** botdagi foto oqimi ham o'chdi — u
[A-10](../05-delivery/02-open-questions.md) kamera xavfining zaxirasi edi.
Zaxira Mini App ichida: «🖼 Galereyadan» tugmasi (ADR-0020 bilan qaytarildi,
ADR-0017 davrida u ham yo'q edi). Kamera sinovi baribir kerak, lekin u endi
**bloklovchi emas**.

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
| **To'lov qayd etildi** (to'liq / qisman) | Muallif |
| Fleet sinxroni (yangi/yo'qolgan mashina yoki xato) | Admin |
| **📢 E'lon (admin yozgan)** ⭐ | **Barcha faol xodimlar** |

**Guruh bildirishnomalari:** admin guruhiga umumiy signal (kritik bayroq, uzoq
downtime). `driver_status_reporter`dagi kabi — bu yondashuv ishlaydi.

> ❌ Zayavka va haydovchi bildirishnomalari **yo'q** — bu rollar tizimda yo'q
> ([ADR-0013](../05-delivery/03-decisions.md#adr-0013--haydovchi-tizimda-rolga-ega-emas)).

### E'lon (broadcast) yetkazish

E'lonni admin **Mini App'da** yozadi, bot faqat yetkazadi — botda e'lon buyrug'i
yo'q ([admin oqimi §8](../01-product/03-admin-flow.md#8-elon-broadcast)).
Boshqa bildirishnomalardan farqi: qabul qiluvchi bitta emas, **hammasi**.

Shablon `notify_broadcast` (uz + ru), xabar ostida odatdagi yagona
`🧩 Ochish` tugmasi:

```
📢 E'lon                 |  📢 Объявление

<admin yozgan matn>      |  <текст админа>
```

**⚠️ HTML escape — buzilmasligi shart**

Bot xabarlarni `parse_mode=HTML` bilan yuboradi. Admin matnida `<` belgisi
bo'lsa (masalan «narx < 200 000»), Telegram butun xabarni **rad etadi** va
e'lon **hech kimga yetmaydi**.

Shuning uchun `notify_broadcast` render qilinishida matn shablonga
qo'yilishidan **oldin** escape qilinadi. Xom matn esa bazada va `payload`da
o'zgarishsiz qoladi — Mini App tarixida e'lon admin yozganidek ko'rinsin.

**Yetkazish tezligi**

Outbox sikli navbatni bo'shatguncha aylanadi, lekin Telegram limitiga
urilmaslik uchun har xabar orasida pauza bilan
([outbox](../02-architecture/02-data-model.md#notifications--chiquvchi-navbat-outbox)):

| Parametr | Qiymat | Manba |
|---|---|---|
| Bir partiya | **20** | `tasks/worker.py` → `BATCH` |
| Bir tickda ko'pi bilan | **300** | `MAX_PER_TICK` |
| Xabarlar orasida pauza | **0.05 sek** (~20 xabar/sek) | `SEND_PAUSE_SEC` |
| Tick oralig'i | **60 sek** | `background_tick_sec` |
| **~150 xodim** | **≈ 8 sekund** | bitta tick ichida |

⚠️ **Navbat tartibi FIFO emas.** Tanlov `broadcast_id IS NULL` yozuvlarni
oldinga qo'yadi: e'lon ommaviy, lekin shoshilinch emas — 150 kishilik e'lon
narx kelishuvi yoki yangi hisobot signalini ortida ushlab qolmasligi kerak.

⚠️ **Har yozuv alohida commit qilinadi.** Deploy yoki ulanish uzilganda
allaqachon Telegram'ga ketgan xabar `pending` bo'lib qolmaydi — aks holda
keyingi tik uni qayta yuborardi (bitta partiyada 20 kishigacha dublikat).

**Blok qilgan xodim:** bot bloklangan bo'lsa xabar `failed` bo'ladi
(qayta urinilmaydi) — e'lon boshqalarga baribir yetadi.

**Flood-limit (`429`):** Telegram `retry_after` bergan bo'lsa bu urinish
sifatida **sanalmaydi** va kutish vaqti serverning o'z qiymatidan olinadi
(`2**attempts` formulasi emas). Aks holda e'lon 5 ta flood-waitdan keyin
butunlay `failed` bo'lib qolardi.

**Takroriy so'rov:** zaif internetda klient POST'ni qayta yuborishi mumkin
(javob yo'lda yo'qolganda `fetch` ham rad etadi). Shuning uchun bitta admin
**60 sekund** ichida aynan bir xil matn yuborsa yangi e'lon yaratilmaydi —
mavjudi qaytariladi (`domain/broadcast.DEDUP_WINDOW_SEC`).

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

**Choralar:**

| Chora | Tafsilot |
|---|---|
| 🔁 **Zaxira yo'l** | «🖼 Galereyadan» tugmasi — `capture` ishlamasa ham foto yuklanadi (ADR-0020) |
| 🔬 **Qurilmada sinash** | Haqiqiy Android va iOS'da tekshirish — endi bloklovchi emas |
| 🕵️ **Server tekshiruvi** | EXIF sanasi yo'q yoki eski → `photo_not_fresh` bayrog'i |
| 📊 **Statistika** | `media.source` (camera/gallery/unknown) yozib boriladi — taqiq emas, **iz** |

> ADR-0020 dan keyin bu xavf **modulni to'xtatmaydi**: eng yomon holatda usta
> galereya tugmasidan foydalanadi. Foto-dalilning kuchi **admin ko'rigi** bilan
> ushlab turiladi (chek fotosi ham to'siq edi — ADR-0021 dan keyin u faqat
> so'raladi, majburiy emas).
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

- `uz` (lotin), `uz_cyrl` (**kirill**) va `ru`
- Til `employees.lang`da saqlanadi (oddiy `text`, migratsiya kerak emas),
  `/til` yoki Profil ekranidan almashadi
- Telegram `initData.user.language_code` — boshlang'ich taxmin
- Shablon yorliqlari bazada ikki tilda (`label_uz`, `label_ru`)

**Kirillcha lug'at qo'lda yuritilmaydi.** `uz_cyrl` — lotinchadan avtomatik
translitatsiya: `backend/app/core/translit.py` va `miniapp/src/translit.ts`
(bir xil qoidalar, ikkalasi ham testlangan). Sabab: ~200 kalitni ikki nusxada
yuritish bir necha kunda uzilib qoladi, yangi kalit esa kirillchada hech kim
eslamasdan paydo bo'lishi kerak. Bazadagi nomlar (`name_uz`, `label_uz`) ham
shu yo'l bilan o'giriladi — uchinchi ustun **qo'shilmaydi**.

- Atoqli nomlar lotin qoladi: `KEEP_WORDS` (NovaCore, Telegram, Excel, Yandex…)
- `{param}`, HTML teg, URL va `/buyruq` tegilmaydi
- Biror kalitda translitatsiya noto'g'ri chiqsa — lug'atga `"uz_cyrl": "…"` ni
  ochiq yozib qo'yish yetarli, avtomatika unga tegmaydi

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
