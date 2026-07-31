"""Davr (kalendar oy) — R4: yopilgan davrga yozuv qo'shilmaydi va o'zgarmaydi.

Hisobot **yuborilgan** sanaga qarab davrga tushadi (A-08), ish bajarilgan
sanaga emas.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import TASHKENT, settings
from app.core.errors import BusinessRuleViolated, PeriodClosed
from app.db.base import as_utc, utcnow
from app.db.models import Period, PeriodStatus, Submission, SubmissionStatus


def period_key(moment: dt.datetime | None = None) -> tuple[int, int]:
    """Davr kaliti — Toshkent vaqti bo'yicha yil va oy."""
    moment = moment or utcnow()
    local = as_utc(moment).astimezone(TASHKENT)
    return local.year, local.month


async def get_or_create_period(
    session: AsyncSession, moment: dt.datetime | None = None
) -> Period:
    year, month = period_key(moment)
    period = (
        await session.execute(
            sa.select(Period).where(Period.year == year, Period.month == month)
        )
    ).scalar_one_or_none()
    if period is None:
        period = Period(year=year, month=month, status=PeriodStatus.open)
        session.add(period)
        await session.flush()
    return period


async def current_period(session: AsyncSession) -> Period:
    return await get_or_create_period(session)


def ensure_open(period: Period | None) -> None:
    """R4 — yopilgan davrda hech narsa o'zgarmaydi."""
    if period is None:
        return
    if period.status == PeriodStatus.closed:
        raise PeriodClosed(f"{period.title} davri yopilgan")


async def ensure_submission_period_open(session: AsyncSession, submission: Submission) -> None:
    if submission.period_id is None:
        return
    period = await session.get(Period, submission.period_id)
    ensure_open(period)


@dataclass
class PrecheckResult:
    blockers: list[tuple[str, dict]] = field(default_factory=list)
    warnings: list[tuple[str, dict]] = field(default_factory=list)

    @property
    def can_close(self) -> bool:
        return not self.blockers


BLOCKING_STATUSES = (
    SubmissionStatus.SUBMITTED,
    SubmissionStatus.IN_REVIEW,
    SubmissionStatus.PRICE_DISPUTED,
    SubmissionStatus.REOPENED,
)


async def precheck(session: AsyncSession, period: Period) -> PrecheckResult:
    """Oyni yopishga to'sqinlik qiluvchilar (docs/04-flows/03-payroll-and-reports.md §2)."""
    result = PrecheckResult()

    unapproved = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.period_id == period.id,
                Submission.deleted_at.is_(None),
                Submission.status.in_(
                    [SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW]
                ),
            )
        )
    ).scalar_one()
    if unapproved:
        result.blockers.append(("precheck_unapproved", {"n": unapproved}))

    reopened = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.period_id == period.id,
                Submission.deleted_at.is_(None),
                Submission.status == SubmissionStatus.REOPENED,
            )
        )
    ).scalar_one()
    if reopened:
        result.blockers.append(("precheck_reopened", {"n": reopened}))

    disputed = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.period_id == period.id,
                Submission.deleted_at.is_(None),
                Submission.status == SubmissionStatus.PRICE_DISPUTED,
            )
        )
    ).scalar_one()
    if disputed:
        result.blockers.append(("precheck_negotiation", {"n": disputed}))

    # ⚠️ Ochiq kelishuv — TO'SIQ: davr yopilgach `accept_price` ham, 48 soatlik
    # avtomatik rozilik ham `period_closed` bilan rad etiladi va hisobot
    # to'lanmagan holda osilib qoladi
    # (docs/04-flows/03-payroll-and-reports.md §3).
    negotiating = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.period_id == period.id,
                Submission.deleted_at.is_(None),
                Submission.status == SubmissionStatus.PRICE_NEGOTIATION,
            )
        )
    ).scalar_one()
    if negotiating:
        result.blockers.append(("precheck_negotiation", {"n": negotiating}))

    stale_days = settings.draft_alert_days
    threshold = utcnow() - dt.timedelta(days=stale_days)
    stale_drafts = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.status == SubmissionStatus.DRAFT,
                Submission.deleted_at.is_(None),
                Submission.created_at < threshold,
            )
        )
    ).scalar_one()
    if stale_drafts:
        result.warnings.append(("precheck_drafts", {"n": stale_drafts, "days": stale_days}))

    return result


async def close_period(session: AsyncSession, period: Period, actor_id: int) -> None:
    """Davrni yopish — precheck to'sqinliklari bo'lmasa."""
    if period.status == PeriodStatus.closed:
        raise PeriodClosed(f"{period.title} allaqachon yopilgan")

    result = await precheck(session, period)
    if not result.can_close:
        raise BusinessRuleViolated("Davrni yopib bo'lmaydi", blockers=result.blockers)

    period.status = PeriodStatus.closed
    period.closed_by = actor_id
    period.closed_at = utcnow()

    # APPROVED → PAID (davr yopildi)
    await session.execute(
        sa.update(Submission)
        .where(
            Submission.period_id == period.id,
            Submission.status == SubmissionStatus.APPROVED,
        )
        .values(status=SubmissionStatus.PAID)
    )
    await session.flush()


async def reopen_period(
    session: AsyncSession, period: Period, actor_id: int, reason: str
) -> None:
    if not reason or len(reason.strip()) < 5:
        raise BusinessRuleViolated("Qayta ochish sababi majburiy")
    period.status = PeriodStatus.open
    period.reopened_by = actor_id
    period.reopened_at = utcnow()
    period.reopen_reason = reason.strip()
    await session.flush()
