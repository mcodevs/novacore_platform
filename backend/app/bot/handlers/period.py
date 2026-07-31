"""Davr: precheck, oy yopilishi, to'lov varaqalari va Excel eksport."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot.callbacks import Act
from app.core.errors import BusinessRuleViolated
from app.core.i18n import fmt_money, t
from app.db.models import Employee, Period, PeriodStatus
from app.domain.export import service as export_service
from app.domain.payout import service as payout_service
from app.domain.period import service as period_service
from app.domain.role import permissions

router = Router(name="period")

MENU_PERIOD = {t("menu_period", "uz"), t("menu_period", "ru")}
MENU_EXPORT = {t("menu_export", "uz"), t("menu_export", "ru")}

STATUS_KEYS = {
    PeriodStatus.open: "period_status_open",
    PeriodStatus.locking: "period_status_locking",
    PeriodStatus.closed: "period_status_closed",
}


async def _period_card(
    message: Message, session: AsyncSession, employee: Employee, period: Period
) -> None:
    lang = employee.lang
    summary = await payout_service.period_summary(session, period.id)
    await message.answer(
        t(
            "period_card",
            lang,
            period=period.title,
            status=t(STATUS_KEYS[period.status], lang),
            total=summary.total_submissions,
            approved=summary.approved_count,
            proposed=fmt_money(summary.proposed_total, lang),
            approved_sum=fmt_money(summary.approved_total, lang),
            saved=fmt_money(summary.saved, lang),
        ),
        reply_markup=kb.period_actions(
            lang, period.id, can_close=period.status != PeriodStatus.closed
        ),
    )


@router.message(Command("davr"))
@router.message(F.text.in_(MENU_PERIOD))
async def period_info(
    message: Message, session: AsyncSession, employee: Employee | None, lang: str
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    if not permissions.can_close_period(employee):
        await message.answer(t("forbidden", employee.lang))
        return
    period = await period_service.current_period(session)
    await _period_card(message, session, employee, period)


@router.callback_query(Act.filter(F.name == "precheck"))
async def precheck(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None or not permissions.can_close_period(employee):
        await callback.answer()
        return
    period = await session.get(Period, callback_data.id)
    lang = employee.lang
    result = await period_service.precheck(session, period)

    await callback.answer()
    if result.can_close and not result.warnings:
        await callback.message.answer(t("precheck_clean", lang))
        return

    text = ""
    if result.blockers:
        items = "\n".join(t(key, lang, **params) for key, params in result.blockers)
        text += t("precheck_blockers", lang, items=items)
    if result.warnings:
        items = "\n".join(t(key, lang, **params) for key, params in result.warnings)
        text += t("precheck_warnings", lang, items=items)
    if result.can_close:
        text += "\n\n" + t("precheck_clean", lang)
    await callback.message.answer(text)


@router.callback_query(Act.filter(F.name == "close_period"))
async def close_period(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None or not permissions.can_close_period(employee):
        await callback.answer()
        return
    period = await session.get(Period, callback_data.id)
    lang = employee.lang

    try:
        await period_service.close_period(session, period, employee.id)
    except BusinessRuleViolated as exc:
        blockers = exc.details.get("blockers") or []
        items = "\n".join(t(key, lang, **params) for key, params in blockers)
        await callback.answer()
        await callback.message.answer(
            t("period_close_blocked", lang) + "\n\n" + t("precheck_blockers", lang, items=items)
        )
        return

    payouts = await payout_service.generate_for_period(session, period)
    await callback.answer()
    await callback.message.answer(t("period_closed_ok", lang, period=period.title, n=len(payouts)))
    for payout in payouts:
        await callback.message.answer(
            t(
                "payout_line",
                lang,
                name=payout.employee.full_name,
                count=payout.submissions_count,
                total=fmt_money(payout.total, lang),
            )
        )
    await callback.message.answer(
        t("export_choose", lang), reply_markup=kb.export_choice(lang, period.id)
    )


@router.message(Command("eksport"))
@router.message(F.text.in_(MENU_EXPORT))
async def export_menu(
    message: Message, session: AsyncSession, employee: Employee | None, lang: str
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    if not permissions.can_export(employee):
        await message.answer(t("forbidden", employee.lang))
        return
    period = await period_service.current_period(session)
    await message.answer(
        t("export_choose", employee.lang),
        reply_markup=kb.export_choice(employee.lang, period.id),
    )


@router.callback_query(Act.filter(F.name == "export"))
async def send_export(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None or not permissions.can_export(employee):
        await callback.answer()
        return
    period = await session.get(Period, callback_data.id)
    lang = employee.lang
    await callback.answer()
    await callback.message.answer(t("export_building", lang))

    filename, payload = await export_service.build(session, callback_data.arg, period)
    await callback.message.answer_document(
        BufferedInputFile(payload, filename=filename), caption=filename
    )
