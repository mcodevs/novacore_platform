"""Usta tomoni: narx taklifiga rozilik yoki nizo."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot.callbacks import Act
from app.bot.states import Negotiation
from app.bot.texts import render_negotiation
from app.core.config import settings
from app.core.i18n import fmt_money, t
from app.db.models import Employee
from app.domain.pricing import service as pricing_service
from app.domain.submission import service as submission_service

router = Router(name="negotiation")

MENU_NEGOTIATION = {t("menu_negotiation", "uz"), t("menu_negotiation", "ru")}


@router.message(Command("kelishuv"))
@router.message(F.text.in_(MENU_NEGOTIATION))
async def list_negotiations(
    message: Message, session: AsyncSession, employee: Employee | None, lang: str
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    lang = employee.lang
    items = await submission_service.awaiting_author_decision(session, employee)
    if not items:
        await message.answer(t("negotiation_empty", lang))
        return

    for submission in items:
        await message.answer(
            render_negotiation(submission, lang, hours=settings.price_auto_accept_hours),
            reply_markup=kb.negotiation_actions(lang, submission.id),
        )


@router.callback_query(Act.filter(F.name == "accept_price"))
async def accept_price(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    await pricing_service.accept_price(session, submission, employee)
    lang = employee.lang
    await callback.answer()
    await callback.message.answer(
        t(
            "price_accepted",
            lang,
            number=submission.number,
            amount=fmt_money(submission.labor_amount, lang),
        ),
        reply_markup=kb.main_menu(employee),
    )


@router.callback_query(Act.filter(F.name == "dispute_price"))
async def ask_dispute_comment(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    await state.set_state(Negotiation.waiting_dispute_comment)
    await state.update_data(submission_id=callback_data.id)
    await callback.answer()
    await callback.message.answer(
        t("ask_dispute_comment", employee.lang), reply_markup=kb.cancel_only(employee.lang)
    )


@router.message(Negotiation.waiting_dispute_comment, F.text)
async def do_dispute(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        return
    text = (message.text or "").strip()
    lang = employee.lang
    if len(text) < 5:
        await message.answer(t("reason_too_short", lang))
        return

    data = await state.get_data()
    submission = await submission_service.get_for_actor(session, data["submission_id"], employee)
    await pricing_service.dispute_price(session, submission, employee, comment=text)
    await state.clear()
    await message.answer(t("price_disputed_ok", lang), reply_markup=kb.main_menu(employee))
