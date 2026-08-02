"""Outbox yozuvini Telegram xabariga aylantirish va yuborish.

Bildirishnoma **doim** bot orqali — Mini App yopiq bo'lsa ham yetadi.
"""

from __future__ import annotations

import html
from decimal import Decimal

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.core.config import settings
from app.core.i18n import fmt_money, t
from app.db.models import Employee, Notification, Submission
from app.domain.pricing import service as pricing_service
from app.domain.role import permissions

log = structlog.get_logger(__name__)

MONEY_KEYS = ("amount", "proposed", "approved")


async def render(
    session: AsyncSession, notification: Notification, employee: Employee | None
) -> tuple[str, InlineKeyboardMarkup | None]:
    lang = employee.lang if employee else settings.default_lang
    payload = dict(notification.payload or {})
    submission_id = payload.get("submission_id")
    code = notification.template_code

    for key in MONEY_KEYS:
        if key in payload and payload[key] is not None:
            payload[key] = fmt_money(Decimal(str(payload[key])), lang)

    payload.setdefault("hours", settings.price_auto_accept_hours)
    payload.setdefault("context", "")

    if code == "notify_broadcast":
        # e'lon matnini admin qo'lda yozadi: «<» bo'lsa Telegram butun xabarni
        # rad etadi va e'lon hech kimga yetmaydi. DB'dagi matn xom qoladi.
        payload["body"] = html.escape(str(payload.get("body", "")), quote=False)

    if code == "notify_new_submission" and submission_id and employee is not None:
        payload["context"] = await _price_hint(session, submission_id, employee, lang)

    text = t(code, lang, **payload)
    markup = _markup(code, lang, submission_id)
    return text, markup


def _markup(code: str, lang: str, submission_id: int | None) -> InlineKeyboardMarkup | None:
    """Bildirishnoma ostida **bitta** tugma — Mini App'da ochish.

    Ilgari har bildirishnoma turi uchun alohida tez tugmalar bor edi
    («✅ Roziman», «✏️ Narxni kamaytirish», «Davom ettirish»). 2026-08-01 dan
    barcha amallar Mini App'da: bitta amal — bitta joyda.
    """
    return kb.open_app(lang, submission_id)


async def _price_hint(
    session: AsyncSession, submission_id: int, employee: Employee, lang: str
) -> str:
    """Adminga bildirishnoma bilan birga tarixiy narx (R3 — faqat admin/buxgalter)."""
    if not permissions.can_see_reference_price(employee):
        return ""
    submission = await session.get(Submission, submission_id)
    if submission is None:
        return ""
    contexts = await pricing_service.price_context(session, submission, employee)
    parts = []
    for ctx in contexts:
        if ctx.has_history and ctx.avg_approved is not None:
            parts.append(
                f"\n📊 {ctx.name}: {'o‘rtacha' if lang == 'uz' else 'среднее'} "
                f"{fmt_money(ctx.avg_approved, lang)} ({ctx.count})"
            )
    return "".join(parts)


async def deliver(
    bot: Bot, session: AsyncSession, notification: Notification
) -> tuple[bool, str | None]:
    """(muvaffaqiyat, xato) — xato bo'lsa outbox qayta uradi."""
    employee: Employee | None = None
    chat_id = notification.chat_id
    if notification.employee_id is not None:
        employee = await session.get(Employee, notification.employee_id)
        if employee is None or employee.tg_user_id is None:
            return False, "employee_without_telegram"
        if not employee.is_active:
            return False, "employee_inactive"
        chat_id = employee.tg_user_id

    if chat_id is None:
        return False, "no_chat"

    text, markup = await render(session, notification, employee)
    try:
        await bot.send_message(chat_id, text, reply_markup=markup)
    except TelegramForbiddenError:
        # bot bloklandi — belgilaymiz va adminga bildiramiz
        if employee is not None:
            employee.tg_blocked = True
            await session.flush()
        return False, "bot_blocked"
    except TelegramRetryAfter as exc:
        return False, f"retry_after:{exc.retry_after}"
    except Exception as exc:  # noqa: BLE001 — outbox qayta uradi
        log.warning("notification_failed", error=str(exc), code=notification.template_code)
        return False, str(exc)[:500]
    return True, None
