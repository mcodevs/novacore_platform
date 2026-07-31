"""Bot va Dispatcher fabrikasi. FastAPI bilan **bitta process** (ADR-0004)."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import build_router
from app.bot.middlewares import DbSessionMiddleware, EmployeeMiddleware, ErrorGuardMiddleware
from app.core.config import settings

_bot: Bot | None = None
_dispatcher: Dispatcher | None = None


def create_bot() -> Bot:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN sozlanmagan")
    session = None
    if settings.telegram_proxy:
        from aiogram.client.session.aiohttp import AiohttpSession

        session = AiohttpSession(proxy=settings.telegram_proxy)
    return Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())

    for observer in (dispatcher.message, dispatcher.callback_query, dispatcher.my_chat_member):
        observer.middleware(DbSessionMiddleware())
        observer.middleware(EmployeeMiddleware())
        observer.middleware(ErrorGuardMiddleware())

    dispatcher.include_router(build_router())
    return dispatcher


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = create_bot()
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = create_dispatcher()
    return _dispatcher


def reset() -> None:
    """Testlar uchun — global holatni tozalash."""
    global _bot, _dispatcher
    _bot = None
    _dispatcher = None
