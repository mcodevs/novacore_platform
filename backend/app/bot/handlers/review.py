"""Admin: ko'rib chiqish, narx kelishuvi, tasdiqlash / qaytarish / rad etish."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import sqlalchemy as sa
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot.callbacks import Act
from app.bot.states import Review
from app.bot.texts import render_card, render_history
from app.core.i18n import fmt_dt, fmt_money, status_label, t
from app.db.models import (
    Approval,
    Employee,
    LineKind,
    Submission,
    SubmissionLine,
    SubmissionStatus,
)
from app.domain.approval import service as approval_service
from app.domain.pricing import service as pricing_service
from app.domain.role import permissions
from app.domain.submission import service as submission_service

router = Router(name="review")

MENU_PENDING = {t("menu_pending", "uz"), t("menu_pending", "ru")}
DECISION_LABELS = {
    "approved": {"uz": "Tasdiqlandi", "ru": "Подтверждено"},
    "auto_approved": {"uz": "Avtomatik tasdiq", "ru": "Автоподтверждение"},
    "rejected": {"uz": "Rad etildi", "ru": "Отклонено"},
    "reopened": {"uz": "Qaytarildi", "ru": "Возвращено"},
    "price_proposed": {"uz": "Narx taklifi", "ru": "Предложение цены"},
    "price_accepted": {"uz": "Narxga rozilik", "ru": "Согласие с ценой"},
    "price_disputed": {"uz": "Nizo", "ru": "Спор"},
}


@router.message(Command("tasdiq"))
@router.message(F.text.in_(MENU_PENDING))
async def pending_list(
    message: Message, session: AsyncSession, employee: Employee | None, lang: str
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    if not permissions.can_review(employee):
        await message.answer(t("forbidden", employee.lang))
        return

    items = await submission_service.pending_review(session)
    lang = employee.lang
    if not items:
        await message.answer(t("pending_empty", lang))
        return

    rows = [
        (
            sub.id,
            f"{sub.number} · {sub.author.full_name} · "
            f"{fmt_money(sub.proposed_labor_amount, lang)}",
        )
        for sub in items
    ]
    await message.answer(
        t("pending_title", lang, n=len(items)),
        reply_markup=kb.submissions_list(rows, lang, admin=True),
    )


async def show_review_card(
    message: Message, session: AsyncSession, employee: Employee, submission: Submission
) -> None:
    lang = employee.lang
    contexts = {}
    if permissions.can_see_reference_price(employee):
        contexts = {
            ctx.line_id: ctx
            for ctx in await pricing_service.price_context(session, submission, employee)
        }

    has_photos = any(m.deleted_at is None for m in submission.media)
    text = render_card(submission, lang, contexts=contexts, show_history=True)

    if submission.status == SubmissionStatus.PRICE_DISPUTED:
        last_dispute = (
            await session.execute(
                sa.select(Approval)
                .where(
                    Approval.submission_id == submission.id,
                    Approval.decision == "price_disputed",
                )
                .order_by(Approval.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
        if last_dispute is not None:
            text += f"\n\n⚖️ <i>{last_dispute.comment}</i>"
        await message.answer(text, reply_markup=kb.dispute_actions(lang, submission.id))
        return

    await message.answer(
        text, reply_markup=kb.review_actions(lang, submission.id, has_photos=has_photos)
    )


@router.callback_query(Act.filter(F.name == "review"))
async def open_review(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    if permissions.can_review(employee):
        await approval_service.start_review(session, submission, employee)
    await callback.answer()
    await show_review_card(callback.message, session, employee, submission)


@router.callback_query(Act.filter(F.name == "photos"))
async def show_photos(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    lang = employee.lang
    photos = [m for m in submission.media if m.deleted_at is None and m.tg_file_id]
    await callback.answer()
    if not photos:
        await callback.message.answer(t("card_no_photos", lang))
        return

    # Telegram file_id — tezkor ko'rsatish keshi (asosiy nusxa omborda)
    for chunk_start in range(0, len(photos), 10):
        chunk = photos[chunk_start : chunk_start + 10]
        media_group = [
            InputMediaPhoto(media=item.tg_file_id, caption=item.field_code if idx == 0 else None)
            for idx, item in enumerate(chunk)
        ]
        await callback.message.answer_media_group(media_group)


@router.callback_query(Act.filter(F.name == "history"))
async def show_history(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    lang = employee.lang
    rows = (
        await session.execute(
            sa.select(Approval)
            .where(Approval.submission_id == submission.id)
            .order_by(Approval.created_at)
        )
    ).scalars().all()

    prepared = []
    for row in rows:
        actor_name = "—"
        if row.actor_id is not None:
            actor = await session.get(Employee, row.actor_id)
            actor_name = actor.full_name if actor else "—"
        else:
            actor_name = "tizim" if lang == "uz" else "система"
        decision = DECISION_LABELS.get(row.decision.value, {}).get(lang, row.decision.value)
        amount = ""
        if row.amount_after is not None:
            amount = f" {fmt_money(row.amount_after, lang)}"
        prepared.append(
            (fmt_dt(row.created_at, lang), actor_name, decision + amount, row.comment or "")
        )
    await callback.answer()
    await callback.message.answer(render_history(prepared, lang))


# --- Tasdiqlash --------------------------------------------------------------


@router.callback_query(Act.filter(F.name == "approve"))
async def approve(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    lang = employee.lang

    if submission.status == SubmissionStatus.PRICE_DISPUTED:
        await state.set_state(Review.waiting_final_comment)
        await state.update_data(submission_id=submission.id)
        await callback.answer()
        await callback.message.answer(t("ask_final_comment", lang), reply_markup=kb.cancel_only(lang))
        return

    await approval_service.approve(session, submission, employee)
    await callback.answer()
    await callback.message.answer(
        t(
            "approved_admin",
            lang,
            number=submission.number,
            amount=fmt_money(submission.labor_amount, lang),
        )
    )


@router.callback_query(Act.filter(F.name == "final"))
async def final_decision(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    await state.set_state(Review.waiting_final_comment)
    await state.update_data(submission_id=callback_data.id)
    await callback.answer()
    await callback.message.answer(
        t("ask_final_comment", employee.lang), reply_markup=kb.cancel_only(employee.lang)
    )


@router.message(Review.waiting_final_comment, F.text)
async def final_comment(
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
    await approval_service.approve(session, submission, employee, comment=text)
    await state.clear()
    await message.answer(
        t(
            "approved_admin",
            lang,
            number=submission.number,
            amount=fmt_money(submission.labor_amount, lang),
        ),
        reply_markup=kb.main_menu(employee),
    )


# --- Narxni kamaytirish ------------------------------------------------------


@router.callback_query(Act.filter(F.name == "reduce"))
async def choose_line(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    lang = employee.lang
    lines = [
        (line.id, line.name, line.proposed_amount)
        for line in submission.lines
        if line.kind == LineKind.labor
    ]
    if not lines:
        await callback.answer(t("nothing_found", lang), show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        t("choose_line_to_reduce", lang),
        reply_markup=kb.line_choice_for_reduce(lines, lang, submission.id),
    )


@router.callback_query(Act.filter(F.name == "reduce_line"))
async def ask_amount(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    line = await session.get(SubmissionLine, callback_data.id)
    if line is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, line.submission_id, employee)
    lang = employee.lang

    await state.set_state(Review.waiting_amount)
    await state.update_data(submission_id=submission.id, line_id=line.id)
    await callback.answer()
    await callback.message.answer(
        t(
            "ask_new_amount",
            lang,
            name=line.name,
            proposed=fmt_money(line.proposed_amount, lang),
        ),
        reply_markup=kb.cancel_only(lang),
    )

    contexts = await pricing_service.price_context(session, submission, employee)
    ctx = next((c for c in contexts if c.line_id == line.id), None)
    if ctx is not None and ctx.quick_amounts:
        markup = kb.quick_amounts(ctx.quick_amounts, lang)
        if markup is not None:
            await callback.message.answer(t("quick_amounts", lang), reply_markup=markup)


@router.callback_query(Act.filter(F.name == "quick"), Review.waiting_amount)
async def quick_amount(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    await _store_amount(
        callback.message, state, session, employee, Decimal(callback_data.arg or "0")
    )
    await callback.answer()


@router.message(Review.waiting_amount, F.text)
async def typed_amount(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        return
    text = (message.text or "").strip()
    try:
        amount = Decimal(text.replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        await message.answer(t("invalid_money", employee.lang))
        return
    await _store_amount(message, state, session, employee, amount)


async def _store_amount(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee,
    amount: Decimal,
) -> None:
    lang = employee.lang
    data = await state.get_data()
    line = await session.get(SubmissionLine, data["line_id"])
    if line is None:
        await state.clear()
        return

    if amount > line.proposed_amount:  # R2 — oshirib bo'lmaydi
        await message.answer(
            t("price_increase_forbidden", lang, proposed=fmt_money(line.proposed_amount, lang))
        )
        return
    if amount < 0:
        await message.answer(t("invalid_money", lang))
        return

    await state.update_data(new_amount=str(amount))
    await state.set_state(Review.waiting_reason)
    await message.answer(t("ask_reason", lang), reply_markup=kb.cancel_only(lang))


@router.message(Review.waiting_reason, F.text)
async def reduce_reason(
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
    await pricing_service.propose_price(
        session,
        submission,
        employee,
        changes=[(int(data["line_id"]), Decimal(data["new_amount"]))],
        comment=text,
    )
    await state.clear()
    await message.answer(t("price_proposed_admin", lang), reply_markup=kb.main_menu(employee))


# --- Qaytarish / rad etish ----------------------------------------------------


@router.callback_query(Act.filter(F.name == "reopen"))
async def ask_reopen_reason(
    callback: CallbackQuery, callback_data: Act, state: FSMContext, employee: Employee | None
) -> None:
    if employee is None:
        await callback.answer()
        return
    await state.set_state(Review.waiting_reopen_reason)
    await state.update_data(submission_id=callback_data.id)
    await callback.answer()
    await callback.message.answer(
        t("ask_reopen_reason", employee.lang), reply_markup=kb.cancel_only(employee.lang)
    )


@router.message(Review.waiting_reopen_reason, F.text)
async def do_reopen(
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
    await approval_service.reopen(session, submission, employee, comment=text)
    await state.clear()
    await message.answer(
        t("reopened_admin", lang, number=submission.number),
        reply_markup=kb.main_menu(employee),
    )


@router.callback_query(Act.filter(F.name == "reject"))
async def ask_reject_reason(
    callback: CallbackQuery, callback_data: Act, state: FSMContext, employee: Employee | None
) -> None:
    if employee is None:
        await callback.answer()
        return
    await state.set_state(Review.waiting_reject_reason)
    await state.update_data(submission_id=callback_data.id)
    await callback.answer()
    await callback.message.answer(
        t("ask_reject_reason", employee.lang), reply_markup=kb.cancel_only(employee.lang)
    )


@router.message(Review.waiting_reject_reason, F.text)
async def do_reject(
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
    await approval_service.reject(session, submission, employee, comment=text)
    await state.clear()
    await message.answer(
        t("rejected_admin", lang, number=submission.number),
        reply_markup=kb.main_menu(employee),
    )


# --- Xodim uchun: o'z hisobotini ochish ---------------------------------------


@router.callback_query(Act.filter(F.name == "open"))
async def open_own(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    await callback.answer()
    # R3 — reporter uchun tarix ko'rsatilmaydi
    await callback.message.answer(
        render_card(submission, employee.lang),
        reply_markup=(
            kb.fix_submission(employee.lang, submission.id)
            if submission.status == SubmissionStatus.REOPENED
            else None
        ),
    )
    if submission.status == SubmissionStatus.PRICE_NEGOTIATION:
        await callback.message.answer(
            status_label(submission.status, employee.lang),
            reply_markup=kb.negotiation_actions(employee.lang, submission.id),
        )
