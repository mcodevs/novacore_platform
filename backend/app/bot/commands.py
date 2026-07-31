"""`setMyCommands` — buyruqlar ro'yxati **rolga qarab** beriladi."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.db.models import Employee, RoleKind

COMMON = {
    "uz": [("start", "Boshlash / menyu"), ("til", "Til"), ("yordam", "Qo'llanma")],
    "ru": [("start", "Старт / меню"), ("til", "Язык"), ("yordam", "Справка")],
}

BY_KIND = {
    RoleKind.reporter: {
        "uz": [
            ("yangi", "Yangi hisobot"),
            ("mening", "Mening hisobotlarim"),
            ("hisob", "Bu oydagi summa"),
            ("kelishuv", "Narx takliflari"),
        ],
        "ru": [
            ("yangi", "Новый отчёт"),
            ("mening", "Мои отчёты"),
            ("hisob", "Сумма за месяц"),
            ("kelishuv", "Предложения по цене"),
        ],
    },
    RoleKind.admin: {
        "uz": [
            ("tasdiq", "Tasdiq kutayotganlar"),
            ("kunlik", "Bugungi hisobot"),
            ("yangi", "Yangi hisobot"),
            ("davr", "Davr va oy yopilishi"),
            ("eksport", "Excel eksport"),
        ],
        "ru": [
            ("tasdiq", "Ожидают подтверждения"),
            ("kunlik", "Отчёт за сегодня"),
            ("yangi", "Новый отчёт"),
            ("davr", "Период и закрытие месяца"),
            ("eksport", "Экспорт в Excel"),
        ],
    },
    RoleKind.accountant: {
        "uz": [
            ("davr", "Davr va oy yopilishi"),
            ("eksport", "Excel eksport"),
            ("kunlik", "Bugungi hisobot"),
        ],
        "ru": [
            ("davr", "Период и закрытие месяца"),
            ("eksport", "Экспорт в Excel"),
            ("kunlik", "Отчёт за сегодня"),
        ],
    },
}


def _commands(kind: RoleKind, lang: str) -> list[BotCommand]:
    items = BY_KIND[kind].get(lang, BY_KIND[kind]["uz"]) + COMMON.get(lang, COMMON["uz"])
    return [BotCommand(command=code, description=title) for code, title in items]


async def set_commands_for(bot: Bot, employee: Employee) -> None:
    """Usta admin buyruqlarini ko'rmaydi."""
    await bot.set_my_commands(
        _commands(employee.role.kind, employee.lang),
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
