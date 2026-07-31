"""Xodim statistikasi (/hisob, /mening) va adminning kunlik hisoboti (/kunlik)."""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.core.config import TASHKENT
from app.core.i18n import fmt_money, t
from app.db.base import ZERO, money, utcnow
from app.db.models import (
    Employee,
    Submission,
    SubmissionStatus,
    Vehicle,
    VehicleStatus,
)
from app.domain.payout import service as payout_service
from app.domain.period import service as period_service
from app.domain.pricing import service as pricing_service
from app.domain.role import permissions
from app.domain.submission import service as submission_service

router = Router(name="stats")

MENU_MONEY = {t("menu_my_money", "uz"), t("menu_my_money", "ru")}
MENU_REPORTS = {t("menu_my_reports", "uz"), t("menu_my_reports", "ru")}
MENU_DAILY = {t("menu_daily", "uz"), t("menu_daily", "ru")}


@router.message(Command("hisob"))
@router.message(F.text.in_(MENU_MONEY))
async def my_money(
    message: Message, session: AsyncSession, employee: Employee | None, lang: str
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    lang = employee.lang
    period = await period_service.current_period(session)

    rows = list(
        (
            await session.execute(
                sa.select(Submission).where(
                    Submission.author_id == employee.id,
                    Submission.period_id == period.id,
                    Submission.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    proposed = ZERO
    approved = ZERO
    count = 0
    pending = 0
    negotiating = 0
    for sub in rows:
        if sub.status in (SubmissionStatus.APPROVED, SubmissionStatus.PAID):
            count += 1
            proposed = money(proposed + sub.proposed_labor_amount)
            approved = money(approved + (sub.labor_amount or ZERO))
        elif sub.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW):
            pending += 1
        elif sub.status in (
            SubmissionStatus.PRICE_NEGOTIATION,
            SubmissionStatus.PRICE_DISPUTED,
        ):
            negotiating += 1

    reduction = money(proposed - approved)
    pct = float(reduction * 100 / proposed) if proposed > ZERO else 0.0

    await message.answer(
        t(
            "my_month",
            lang,
            period=period.title,
            count=count,
            proposed=fmt_money(proposed, lang),
            approved=fmt_money(approved, lang),
            reduction=fmt_money(reduction, lang),
            pct=f"{pct:.1f}",
            pending=pending,
            negotiating=negotiating,
        )
    )

    stats = await pricing_service.employee_price_stats(session, employee.id)
    if stats.lines_total:
        # ⭐ Xodim **o'z** narx statistikasini ko'radi (A-24), boshqalarnikini emas
        await message.answer(
            f"📉 {int(stats.reduction_rate_pct)}% · "
            f"{'o‘rtacha kamaytirish' if lang == 'uz' else 'среднее снижение'}: "
            f"{stats.avg_reduction_pct}%"
        )


@router.message(Command("mening"))
@router.message(F.text.in_(MENU_REPORTS))
async def my_reports(
    message: Message, session: AsyncSession, employee: Employee | None, lang: str
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    lang = employee.lang
    items = await submission_service.list_for_employee(session, employee, limit=15)
    items = [s for s in items if s.author_id == employee.id]
    if not items:
        await message.answer(t("my_reports_empty", lang))
        return

    from app.bot.texts import render_list_row

    rows = [(sub.id, f"{sub.number} · {render_list_row(sub, lang)}") for sub in items]
    await message.answer(
        t("my_reports_title", lang),
        reply_markup=kb.submissions_list(rows, lang, admin=False),
    )


@router.message(Command("kunlik"))
@router.message(F.text.in_(MENU_DAILY))
async def daily_report(
    message: Message, session: AsyncSession, employee: Employee | None, lang: str
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    if not permissions.can_see_all_submissions(employee):
        await message.answer(t("forbidden", employee.lang))
        return

    lang = employee.lang
    now_local = utcnow().astimezone(TASHKENT)
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dt.timezone.utc)

    submitted = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.submitted_at >= day_start, Submission.deleted_at.is_(None)
            )
        )
    ).scalar_one()
    approved_rows = list(
        (
            await session.execute(
                sa.select(Submission).where(
                    Submission.decided_at >= day_start,
                    Submission.deleted_at.is_(None),
                    Submission.status.in_(
                        [SubmissionStatus.APPROVED, SubmissionStatus.PAID]
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    approved_sum = ZERO
    for sub in approved_rows:
        approved_sum = money(approved_sum + (sub.labor_amount or ZERO))

    negotiating = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.deleted_at.is_(None),
                Submission.status.in_(
                    [SubmissionStatus.PRICE_NEGOTIATION, SubmissionStatus.PRICE_DISPUTED]
                ),
            )
        )
    ).scalar_one()
    in_service = (
        await session.execute(
            sa.select(sa.func.count(Vehicle.id)).where(
                Vehicle.status.in_([VehicleStatus.in_service, VehicleStatus.waiting_parts])
            )
        )
    ).scalar_one()

    period = await period_service.current_period(session)
    summary = await payout_service.period_summary(session, period.id)

    await message.answer(
        t(
            "daily_report",
            lang,
            date=now_local.strftime("%d.%m.%Y"),
            submitted=int(submitted),
            approved=len(approved_rows),
            approved_sum=fmt_money(approved_sum, lang),
            negotiating=int(negotiating),
            in_service=int(in_service),
            period=period.title,
            m_proposed=fmt_money(summary.proposed_total, lang),
            m_approved=fmt_money(summary.approved_total, lang),
            m_saved=fmt_money(summary.saved, lang),
            m_pct=f"{summary.saved_pct}",
        )
    )
