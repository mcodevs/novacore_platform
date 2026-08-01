"""Routerlar tartibi muhim: fallback — eng oxirida.

⚠️ **Bot doirasi (egasining qarori, 2026-08-01):** botda faqat *kirish* va
*bildirishnoma* qoladi — ro'yxatdan o'tish (telefon bog'lash), til, yordam va
Mini App'ni ochish. Barcha **amallar** Mini App'da: hisobot yozish, ko'rib
chiqish, narx kelishuvi, davr, eksport, statistika.

Sabab: bitta amalni ikki joydan bajarish odamni chalkashtiradi. Shuning uchun
`report`, `review`, `negotiation`, `stats`, `period` handlerlari o'chirildi
(~2100 qator) — ular Mini App ekranlari bilan takrorlanardi.
"""

from __future__ import annotations

from aiogram import Router

from app.bot.handlers import common, start


def build_router() -> Router:
    router = Router(name="root")
    router.include_router(start.router)
    router.include_router(common.router)  # oxirgi
    return router
