---
name: prod-data-reset-2026-08
description: 2026-08-03 prod baza va Tigris tozalanib, bitta admin login qoldirildi; R9 ataylab vaqtincha buzildi
metadata:
  type: project
---

# Prod ma'lumot reset — 2026-08-03

**Nima uchun:** Admin bu oy davrini (`period`) tasodifan yopib qo'ygan va ortga
qaytara olmagan (R4 — yopiq davr o'zgarmaydi). Yechim: toza start — bitta admin
qoldirib, boshqa hamma narsani o'chirish.

**Yakuniy holat (prod `novacore-platform` / MPG `novacore-db`):**
- Qoldi: faqat `+998993081155` (Murod Erkinov, `employees.id=1`, active).
- O'chdi (hard delete, 189 qator): boshqa 3 xodim, BARCHA `submissions`
  (adminniki ham) + `submission_lines`/`media`/`approvals`/`flags`, BARCHA
  `periods` + `payouts`, `notifications`, `broadcasts`, o'chgan xodim tokenlari.
- Saqlandi (konfiguratsiya): `templates` (2), `roles` (4), `vehicles` (166),
  `work_catalog` (37), kataloglar.
- Tigris `novacore-media` bucket: 56 yetim media obyekti (11 MB) o'chirildi → bo'sh.

**⚠️ Muhim qaror — R9 ataylab vaqtincha buzildi:**
`audit_log` append-only trigger (`audit_log_no_update_delete`) 70 yozuvda
`actor_id` ni o'chirilgan xodimlarga bog'lab turgani uchun xodimni hard-delete
qilishga to'sqinlik qildi. Egasining ochiq roziligi bilan: trigger vaqtincha
`DISABLE` qilinib, `actor_id = NULL` qilindi, so'ng trigger `ENABLE` qilinib
**qayta tekshirildi** (UPDATE bloklanishi tasdiqlandi). `audit_log` qatorlari
o'chirilmadi — anonimlashtirildi. Odatiy yo'l soft-delete edi, lekin egasi
to'liq hard-delete tanladi. Bog'liq: [[R9-audit-log-immutable]].

**Zaxiralar (tiklash uchun):**
- MPG to'liq snapshot `20260803-113048F` (o'chirishdan oldin) + soatlik PITR.
- `backups/novacore_cleanup_backup_20260803_115024.json` — o'chgan DB qatorlari.
- `backups/tigris_media_backup_20260803_120027.zip` — o'chgan media fayllar.
- ⚠️ `backups/` ichida real PII (ism/telefon/foto) — Git'ga qo'shilmasin.

**Skriptlar (bir martalik):** `scripts/cleanup_prod.py`, `scripts/clean_tigris.py`
— ikkalasi ham `CONFIRM=YES` bilan qo'riqlanadi va nishon admin topilmasa to'xtaydi.


## Keyingi holat — 2026-08 davri qo'lda ochildi (2026-08-03)

Tozalashdan keyin yangi `2026-08` davri yaratilgan va yana `closed` bo'lgan
(`periods.id=2`, `closed_by=5` — reset'dan keyin yangi xodimlar qo'shilgan).
Egasi so'roviga ko'ra faqat shu davr ochildi (boshqa hech narsaga tegilmadi):
`status=open`, `closed_by/closed_at=NULL`, `reopened_by=1`, `reopened_at=now`,
`reopen_reason='Admin tomonidan qo'lda ochildi'`. To'lovlar/hisobotlar qoldirildi.
