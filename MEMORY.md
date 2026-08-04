# NovaCore Platform — Memory Index

- [Qarz daftari modeli](references/qarz-daftari-modeli.md) — oy yopish olib tashlandi; qarz = hisobot xususiyati; «narx bor = qarz bor»; avans (P7); ADR-0015/0016. **2026-08-03 prodga chiqarildi.** To'lov ekrani: bitta amal tugmasi + tasdiq oynasi (2026-08-04 prodda, `b2b05bf`); **«Qisman to'langan» — status emas, klientda hisoblanadigan ko'rinish**.
- [Savdolashish fokusdan olindi](references/savdolashish-fokusdan-olindi.md) — ADR-0019: kelishuv ko'rsatkichlari (Tejaldi, narx statistikasi, hisobotdagi narx tarixi) UI'dan olib tashlandi; kelishuv faqat sodir bo'ladigan joyda; backend tegilmadi.
- [Narx kelishuvi — ko'p qatorli](references/narx-kelishuvi-kop-qatorli.md) — kelishuv butun hisobot bo'yicha; `effective_sum` xatosi (qisman kamaytirishda jami kam ko'rinardi); ilova ichidagi foto ko'ruvchi va back-handler steki.
- [Mini App dizayn tizimi](references/miniapp-dizayn-tizimi.md) — bo'shliq shkalasi `--s-*`; uchta CSS tuzog'i; `.row` grid; **summa maydoni faqat `MoneyInput`** (server Decimal'ni qator qilib beradi — kasrni yaxlitlamasa 100 barobar xato).
- [Foto va shablon qarorlari](references/shablon-va-foto-qarorlari.md) — foto faqat kameradan (zaxira yo'l qolmadi — iOS sinovi bloklovchi); probeg shablondan o'chdi; chek fotosi majburiy (F5a); ADR-0017/0018.
- [Prod ma'lumot reset — 2026-08-03](references/prod-data-reset-2026-08.md) — prod baza + Tigris tozalanib bitta admin qoldirildi; R9 audit-trigger ataylab vaqtincha buzildi; zaxiralar backups/ da.
