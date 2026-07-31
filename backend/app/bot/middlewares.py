"""Middleware: har yangilanish uchun DB sessiyasi va xodim konteksti."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import sqlalchemy as sa
import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.core.config import settings
from app.core.errors import DomainError
from app.core.i18n import t
from app.db.models import Employee, EmployeeStatus
from app.db.session import session_scope

log = structlog.get_logger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_scope() as session:
            data["session"] = session
            return await handler(event, data)


class EmployeeMiddleware(BaseMiddleware):
    """Telegram foydalanuvchisi → reyestrdagi xodim (R6: bitta akkaunt = bitta xodim)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        session = data["session"]
        employee: Employee | None = None

        if user is not None:
            employee = (
                await session.execute(
                    sa.select(Employee).where(Employee.tg_user_id == user.id)
                )
            ).scalar_one_or_none()
            if employee is not None:
                if employee.tg_username != user.username:
                    employee.tg_username = user.username
                if employee.tg_blocked:
                    employee.tg_blocked = False

        data["employee"] = employee
        data["lang"] = employee.lang if employee else settings.default_lang
        data["is_registered"] = employee is not None and employee.is_active
        return await handler(event, data)


class ErrorGuardMiddleware(BaseMiddleware):
    """Domen xatolari foydalanuvchiga tushunarli matn bo'lib qaytadi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except DomainError as exc:
            lang = data.get("lang", settings.default_lang)
            message = _domain_message(exc, lang)
            await _reply(event, message)
            log.info("domain_error", code=exc.code, message=exc.message)
            return None


ERROR_KEYS = {
    "forbidden": "forbidden",
    "price_reference_hidden": "forbidden",
    "not_found": "not_found",
    "invalid_state_transition": "invalid_state",
    "period_closed": "period_closed_err",
    "self_approval_forbidden": "self_approval_forbidden",
    "not_in_registry": "not_in_registry",
}


def _domain_message(exc: DomainError, lang: str) -> str:
    key = ERROR_KEYS.get(exc.code)
    if key:
        return t(key, lang, phone="")
    return f"⚠️ {exc.message}"


async def _reply(event: TelegramObject, text: str) -> None:
    from aiogram.types import CallbackQuery, Message

    if isinstance(event, Message):
        await event.answer(text)
    elif isinstance(event, CallbackQuery):
        await event.answer()
        if event.message is not None:
            await event.message.answer(text)


def blocked_status_message(employee: Employee, lang: str) -> str | None:
    if employee.status == EmployeeStatus.blocked:
        return t("employee_blocked", lang)
    if employee.status == EmployeeStatus.fired:
        return t("employee_fired", lang)
    return None
