# NovaCore Mini App

React 18 + TypeScript + Vite. Telegram WebApp SDK — Telegram tomonidan beriladi,
qo'shimcha UI kutubxonasi yo'q: **bundle ~59 KB (gzip)**, talab < 300 KB.

## Ekranlar (4 ta)

| Ekran | Nima qiladi |
|---|---|
| `HomeScreen` | Rolga qarab: usta hisoblari (qoralama, kelishuv, bu oy summasi) yoki admin paneli (tasdiq navbati, **kelishuv tejamkorligi**) |
| `FormScreen` | ⭐ Shablon JSON → forma (bo'limlar bo'yicha qadam-baqadam), foto yuklash, ishlar + o'z narxi, «Mashina ketdi», «Yuborish» |
| `DetailScreen` | Ko'rib chiqish: admin uchun narx tarixi + qarorlar; muallif uchun narx taklifiga ✅/❌ javob |
| `ProfileScreen` | Rol, til (uz/ru), ⭐ **o'z** narx statistikasi |

## Form renderer

`src/form-renderer/` — shablon JSON'ini olib forma chizadi. Yangi rol yoki
shablon qo'shilganda **bu yerda kod o'zgarmaydi**.

Qo'llab-quvvatlanadigan turlar: `text`, `textarea`, `number`, `money`, `bool`,
`select` (spravochnik bilan), `photo` (min/max, kamera), `vehicle_picker`
(raqam bo'yicha qidiruv), `lines` (ishlar/qismlar + narx).

⚠️ Tayanch narx UI'da **ko'rsatilmaydi** va server ham uni `reporter` roliga
qaytarmaydi (R3) — yashirish klientda emas, ikki tomonda.

## Ishga tushirish

```bash
npm install
npm run dev          # http://localhost:5173, /api → localhost:8000 ga proxy
npm run build        # dist/
```

Repo ildizidan: `make miniapp-build` — yig'adi va `backend/miniapp_dist/` ga
qo'yadi; backend uni `/app` yo'lida beradi (bitta domen, bitta machine).
Docker image ham shu tarzda quriladi (`backend/Dockerfile`, ikki bosqichli).

## Telegram bilan integratsiya

- `tg.initData` → `POST /api/v1/auth/telegram` (HMAC **serverda** tekshiriladi)
- `access_token` xotirada, `refresh_token` `sessionStorage`da
- `tg.BackButton` — qadamlar orasida orqaga, `tg.HapticFeedback` — tasdiqlashda
- `themeParams` → CSS o'zgaruvchilari (yorug'/qorong'i tema)
- Offline: forma qiymatlari `localStorage`da, tarmoq tiklanganda serverga ketadi
- Foto klientda siqiladi (1600 px, JPEG 0.75 → ~200 KB)

## ⚠️ Ochiq xavf (A-10)

`<input type="file" accept="image/*" capture="environment">` Telegram
WebView'ida (ayniqsa iOS) galereyani bloklashi mumkin. Shuning uchun **ikkala
tugma ham bor**: «Suratga olish» va «Galereyadan» — `media.source` bazaga
yoziladi va statistikaga tushadi. Kamera majburlash ishlamasa, botdagi foto
oqimi zaxira sifatida qoladi.
