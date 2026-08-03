"""Xulosa ko'rsatkichlari — **sana oralig'i** bo'yicha.

⚠️ `periods` yo'q (ADR-0015): oylik kesim `submitted_at` bo'yicha filtrlanadi.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import ZERO, money
from app.db.models import Submission, SubmissionStatus

PAYABLE = (SubmissionStatus.APPROVED, SubmissionStatus.PAID)


@dataclass
class RangeSummary:
    """`period_summary` o'rnini bosadi — davr emas, sana oralig'i."""

    title: str = ""
    total_submissions: int = 0
    approved_count: int = 0
    proposed_total: Decimal = ZERO
    approved_total: Decimal = ZERO
    parts_total: Decimal = ZERO
    auto_approved_count: int = 0
    auto_approved_total: Decimal = ZERO
    debt_total: Decimal = ZERO
    paid_total: Decimal = ZERO

    @property
    def saved(self) -> Decimal:
        return money(self.proposed_total - self.approved_total)

    @property
    def saved_pct(self) -> Decimal:
        if self.proposed_total <= ZERO:
            return ZERO
        return money(self.saved * 100 / self.proposed_total)


def month_range(year: int, month: int) -> tuple[dt.datetime, dt.datetime]:
    """Kalendar oyning [boshi, oxiri) chegarasi — UTC."""
    last = calendar.monthrange(year, month)[1]
    start = dt.datetime(year, month, 1, tzinfo=dt.UTC)
    end = dt.datetime(year, month, last, 23, 59, 59, 999999, tzinfo=dt.UTC)
    return start, end


def current_month_range() -> tuple[dt.datetime, dt.datetime]:
    now = dt.datetime.now(dt.UTC)
    return month_range(now.year, now.month)


def range_title(frm: dt.datetime | None, to: dt.datetime | None) -> str:
    if frm is None and to is None:
        return "butun davr"
    left = frm.date().isoformat() if frm else "…"
    right = to.date().isoformat() if to else "…"
    return f"{left} — {right}"


def in_range(
    frm: dt.datetime | None, to: dt.datetime | None
) -> list[sa.ColumnElement[bool]]:
    where: list[sa.ColumnElement[bool]] = [Submission.deleted_at.is_(None)]
    if frm is not None:
        where.append(Submission.submitted_at >= frm)
    if to is not None:
        where.append(Submission.submitted_at <= to)
    return where


async def range_summary(
    session: AsyncSession,
    *,
    frm: dt.datetime | None = None,
    to: dt.datetime | None = None,
) -> RangeSummary:
    """⭐ «Kelishuv X so'm tejadi» — platformaning o'zini oqlashi."""
    summary = RangeSummary(title=range_title(frm, to))
    rows = (
        (await session.execute(sa.select(Submission).where(*in_range(frm, to))))
        .scalars()
        .all()
    )
    for sub in rows:
        summary.total_submissions += 1
        if sub.status not in PAYABLE:
            continue
        summary.approved_count += 1
        summary.proposed_total = money(summary.proposed_total + sub.proposed_labor_amount)
        summary.approved_total = money(summary.approved_total + (sub.labor_amount or ZERO))
        summary.parts_total = money(summary.parts_total + sub.parts_amount)
        summary.paid_total = money(summary.paid_total + sub.paid_amount)
        summary.debt_total = money(
            summary.debt_total + (sub.payable_amount - sub.paid_amount)
        )
        if sub.auto_approved:
            summary.auto_approved_count += 1
            summary.auto_approved_total = money(
                summary.auto_approved_total + (sub.labor_amount or ZERO)
            )
    return summary
