# 04. Rollar va shablonlar konstruktori

> Talab: *"Platforma faqat ustalar uchun emas, barcha ishchilar uchun birdek
> ishlashi kerak. Admin rollardan bir nechta yaratishi mumkin."*

Bu hujjat shu talabni **qanday qilib kod yozmasdan** bajarishni tushuntiradi.
Rol modelining o'zi: [01-roles-and-permissions.md](01-roles-and-permissions.md).

## 1. Muammo: har rol uchun alohida modul yozish — o'lim yo'li

Agar har bir rol uchun alohida kod yozilsa:

```
usta moduli      → 3 hafta
ta'minotchi      → 2 hafta
yuvuvchi         → 2 hafta
elektrik         → 2 hafta
...
```

Har yangi rol = yangi sprint, yangi deploy, yangi bug. 5-rolda loyiha to'xtaydi.
Bu — ko'p ichki platformalar o'ladigan joy.

## 2. Yechim: rol = nom + shablon

NovaCore'da **hamma rollar bir xil ish qiladi**:

> *Xodim* → rasmga oladi → izoh yozadi → narx qo'yadi → hisobot yuboradi →
> admin kelishadi va tasdiqlaydi → pulga aylanadi

Farq faqat **nomda** va **maydonlar to'plamida**. Demak:

```
                    ┌──────────────────────────┐
                    │   YADRO (bir marta yoziladi)│
                    │                          │
                    │  • Xodim + rol           │
                    │  • Shablon dvigateli     │
                    │  • Foto yuklash          │
                    │  • Tasdiqlash oqimi      │
                    │  • Bayroqlar (anti-fraud)│
                    │  • Qarz va to'lov        │
                    │  • Bildirishnoma         │
                    │  • Audit log             │
                    │  • Eksport / analitika   │
                    └────────────┬─────────────┘
                                 │
        ┌────────────┬───────────┼───────────┬────────────┐
        ▼            ▼           ▼           ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ TA'MIR  │ │  QISM   │ │ YUVISH  │ │  ELEKTR │ │ ... yangi│
   │ shabloni│ │ XARIDI  │ │ shabloni│ │ shabloni│ │ shablon  │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
      "Usta"   "Ta'minotchi" "Yuvuvchi"  "Elektrik"   admin
                                                     yaratadi

   Har biri — ADMIN PANELDAN yaratiladigan KONFIGURATSIYA, kod emas
```

Texnik model: [02-architecture/03-report-templates.md](../02-architecture/03-report-templates.md)

## 3. Shablon nima?

Shablon = **maydonlar ro'yxati + sozlamalar**:

```yaml
kod: car_wash
nom: "Mashina yuvish hisoboti"
ob'ekt: vehicle          # hisobot mashinaga bog'lanadi
pul_bor: true            # summa maydoni bor, qarz daftariga kiradi
kelishiladi: true        # narx kelishuvi oqimiga tushadi
# kim ko'radi — ROLDA belgilanadi (role_templates), shablonda emas

maydonlar:
  - kod: plate
    nom: "Mashina raqami"
    tur: vehicle_picker
    majburiy: true

  - kod: photo_before
    nom: "Yuvishdan oldin"
    tur: photo
    min: 2
    kamera_majburiy: true

  - kod: wash_type
    nom: "Yuvish turi"
    tur: select
    variantlar: [tashqi, tashqi+salon, kimyoviy_tozalash]

  - kod: photo_after
    nom: "Yuvishdan keyin"
    tur: photo
    min: 2
    kamera_majburiy: true

  - kod: amount
    nom: "Summa"
    tur: money
    rol: total_amount     # yadro shu maydonni "summa" deb tushunadi
```

Natija: yuvuvchi Mini App'ga kirganda **o'z shabloniga mos forma** ko'radi.
Admin ko'rib chiqish ekranida — **xuddi usta hisobotidagi kabi** interfeys.
Analitika, eksport, audit — hammasi avtomatik ishlaydi.

## 4. Rejalashtirilgan shablonlar

| Shablon | Rol nomi | Ob'ekt | Faza |
|---|---|---|---|
| **Ta'mir hisoboti** | Usta | mashina | **Faza 1** — asosiy modul |
| **Ehtiyot qism xaridi** | Ta'minotchi | mashina | Faza 2 |
| **Yuvish** | Yuvuvchi | mashina | Faza 2+ |
| **Elektr ishlari** | Elektrik | mashina | Faza 2+ |
| **Shina almashtirish** | Shinamontaj | mashina | Faza 2+ |
| **Kuzov ta'miri** | Kuzovchi | mashina | Faza 2+ |
| **TO (texnik ko'rik)** | Usta | mashina | Faza 4 — checklist bilan |
| **Qism so'rovi** | Usta → Ta'minotchi | mashina | Faza 4 |

> Bular — **misollar**, qat'iy ro'yxat emas. Admin ehtiyojga qarab istalgan
> nom va shablonni yaratadi.

## 5. Maydon turlari (field types)

Yadro qo'llab-quvvatlaydigan turlar — bular yetsa, deyarli har qanday hisobot yig'iladi:

| Tur | Tavsif | Misol |
|---|---|---|
| `text` | Qisqa matn | Izoh |
| `textarea` | Uzun matn | Batafsil tavsif |
| `number` | Son | kVt·soat, miqdor |
| `money` | Pul (UZS) | Ish haqi |
| `select` | Bitta tanlov | Nosozlik kategoriyasi |
| `multiselect` | Ko'p tanlov | Bajarilgan ishlar |
| `bool` | Ha/yo'q | "Kafolat ostidami?" |
| `date` / `datetime` | Sana/vaqt | Kafolat tugash sanasi |
| `photo` | Foto (min/max, kamera majburiy) | Muammo fotosi |
| `video` | Qisqa video (≤ 30 s) | Ovoz chiqarayotgan nosozlik |
| `audio` | Ovozli xabar | Usta izohi |
| `file` | Hujjat | Nakladnoy PDF |
| `vehicle_picker` | Mashina tanlash | Mashina raqami |
| `employee_picker` | Xodim tanlash | Hamkor usta |
| `catalog_picker` | Spravochnikdan tanlash | Ish turi (narx bilan) |
| `geo` | Joylashuv | Ustaxona joyi |
| `signature` | Barmoq bilan imzo | Hujjat tasdig'i |
| `lines` | Qatorlar jadvali | Ishlar / qismlar ro'yxati |
| `computed` | Hisoblanadigan | JAMI = ish haqi + qismlar |

## 6. Chegara: shablon nimani hal qilmaydi

Halol bo'lish kerak — shablon **hamma narsani** yechmaydi:

| Shablon yetarli | Alohida kod kerak |
|---|---|
| Forma to'ldirish, foto, summa | Ombor qoldig'i mantig'i (kirim−chiqim balansi) |
| Tasdiqlash, eksport | Murakkab hisob-kitob (maosh formulalari) |
| Oddiy tekshiruvlar | Tashqi tizim bilan real-vaqt integratsiya |
| Ro'yxat + kartochka | Maxsus vizualizatsiya (masalan mashina sxemasida shikast nuqtasi) |

**Qoida:** shablon bilan boshlanadi. Agar rol shablon doirasidan chiqib ketsa —
o'shanda va faqat o'shanda alohida modul yoziladi. Bu 80/20 qoidasi:
rollarning 80% shablonga sig'adi.

## 7. Yangi rolni qo'shish qadamlari (kod yozmasdan)

```
1. Admin panel → Shablonlar → [+ Yangi shablon]
   • Maydonlarni sudrab qo'yish (drag & drop)
   • Pul bormi, qaysi maydon "summa", kelishiladimi
   • [Test rejimida ochish] → o'zingiz to'ldirib ko'rasiz
   • [Nashr qilish]
        ↓
2. Admin panel → Rollar → [+ Yangi rol]
   • Nomi (uz/ru), ikonka
   • Turi: Hisobot beruvchi
   • Shablonlar: ☑ yangi shablon
        ↓
3. Xodimga shu rolni berish
        ↓
4. Xodim Mini App'ni ochadi → yangi menyu paydo bo'lgan
```

Vaqt: **15–30 daqiqa**, dasturchi ishtirokisiz, deploy'siz.

📌 Bu konstruktor **Faza 2**'da yoziladi. Faza 1 (MVP)'da rollar va shablonlar
**seed** (JSON fayl) sifatida yuklanadi — dvigatel esa allaqachon ishlaydi.

---

**Keyingi:** [02-architecture/01-system-architecture.md](../02-architecture/01-system-architecture.md)
