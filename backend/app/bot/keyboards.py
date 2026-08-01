"""Bot klaviaturalari — juda kam qoldi va shunday bo'lishi kerak.

⚠️ **Bot doirasi (2026-08-01):** botda **amal yo'q**. Faqat kirish
(telefon bog'lash), til, yordam va Mini App'ni ochish. Shuning uchun bu yerda
faqat to'rtta klaviatura bor; ilgari 20 dan ortiq edi (forma qadamlari, ko'rik
tugmalari, narx kelishuvi, davr, eksport) — hammasi Mini App'ga ko'chdi.
"""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.bot.callbacks import Act
from app.core.config import settings
from app.core.i18n import t
from app.db.models import Employee

REMOVE = ReplyKeyboardRemove()


def _https() -> bool:
    """`web_app` tugmasi faqat HTTPS bilan ishlaydi (lokal dev'da yo'q)."""
    return settings.miniapp_url.startswith("https://")


def app_url(submission_id: int | None = None) -> str:
    """Mini App havolasi; `submission_id` berilsa o'sha kartochka ochiladi."""
    base = settings.miniapp_url
    return f"{base}?submission={submission_id}" if submission_id else base


def phone_request(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=t("btn_share_phone", lang), request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def main_menu(employee: Employee) -> ReplyKeyboardMarkup:
    """Botda amal yo'q — menyu Mini App'ni ochishga olib boradi.

    ⚠️ **Bu yerda `web_app` ISHLATILMAYDI.** Reply-klaviaturadagi `web_app`
    tugmasi Mini App'ni ochadi, lekin unga **`initData` bermaydi** (u
    `sendData()` orqali oddiy ma'lumot yig'ish uchun mo'ljallangan). Natijada
    ilova o'zini Telegram tashqarisida deb hisoblaydi va «Bu sahifa Telegram
    ichida ochilishi kerak» xatosini beradi.

    To'g'ri yo'llar — `initData` imzolangan holda keladi:
    • BotFather Menu Button (pastdagi «NovaCore» tugmasi)
    • **inline** klaviaturadagi `web_app` tugmasi → `open_app()`

    Shuning uchun bu tugma oddiy matn yuboradi, `cmd_app` esa javobiga inline
    tugma qo'yadi.
    """
    lang = employee.lang
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=t("menu_app", lang)))
    builder.row(
        KeyboardButton(text=t("menu_lang", lang)), KeyboardButton(text=t("menu_help", lang))
    )
    return builder.as_markup(resize_keyboard=True)


def lang_choice() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data=Act(name="lang", arg="uz").pack()),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data=Act(name="lang", arg="ru").pack()),
    )
    return builder.as_markup()


def open_app(lang: str, submission_id: int | None = None) -> InlineKeyboardMarkup | None:
    """Bildirishnoma ostidagi yagona tugma — Mini App'da ochish.

    Ilgari bu yerda «✅ Roziman», «✏️ Narxni kamaytirish» kabi tez tugmalar
    bor edi. Ular olib tashlandi: bitta amal — bitta joyda.
    """
    if not _https():
        return None
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=t("open_app", lang), web_app=WebAppInfo(url=app_url(submission_id))
        )
    )
    return builder.as_markup()
