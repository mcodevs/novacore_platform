"""`setMyCommands` — buyruqlar ro'yxati.

⚠️ 2026-08-01 dan botda **amal yo'q**, shuning uchun rolga xos buyruqlar ham
yo'q: hamma bir xil to'rtta buyruqni ko'radi, qolgani Mini App'da.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.db.models import Employee

COMMON = {
    "uz": [
        ("start", "Boshlash"),
        ("app", "Ilovani ochish"),
        ("til", "Til"),
        ("yordam", "Qo'llanma"),
    ],
    "ru": [
        ("start", "Старт"),
        ("app", "Открыть приложение"),
        ("til", "Язык"),
        ("yordam", "Справка"),
    ],
}

def _commands(lang: str) -> list[BotCommand]:
    items = COMMON.get(lang, COMMON["uz"])
    return [BotCommand(command=code, description=title) for code, title in items]


async def set_commands_for(bot: Bot, employee: Employee) -> None:
    """Xodim tilida buyruqlar (rol farqi yo'q)."""
    await bot.set_my_commands(
        _commands(employee.lang),
        scope=BotCommandScopeChat(chat_id=employee.tg_user_id),
    )


async def set_default_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Boshlash / Старт"),
            BotCommand(command="yordam", description="Qo'llanma / Справка"),
        ],
        scope=BotCommandScopeDefault(),
    )
