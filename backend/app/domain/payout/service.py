"""To'lov varaqasi — R5: faqat `approved_amount` bo'yicha.

⚠️ Platforma pul o'tkazmaydi — faqat hisoblab beradi.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleViolated, PeriodClosed
from app.db.base import ZERO, money, utcnow
from app.db.models import (
    Payout,
    PayoutStatus,
    Period,
    PeriodStatus,
    Submission,
    SubmissionStatus,
)
from app.domain import audit

PAYABLE = (SubmissionStatus.APPROVED, SubmissionStatus.PAID)


@dataclass
class PeriodSummary:
    total_submissions: int = 0
    approved_count: int = 0
    proposed_total: Decimal = ZERO
    approved_total: Decimal = ZERO
    parts_total: Decimal = ZERO
    auto_approved_count: int = 0
    auto_approved_total: Decimal = ZERO
    disputed_count: int = 0
    auto_accepted_count: int = 0

    @property
    def saved(self) -> Decimal:
        return money(self.proposed_total - self.approved_total)

    @property
    def saved_pct(self) -> Decimal:
        if self.proposed_total <= ZERO:
            return ZERO
        return money(self.saved * 100 / self.proposed_total)


async def period_summary(session: AsyncSession, period_id: int) -> PeriodSummary:
    """⭐ «Bu oy kelishuv X so'm tejadi» — platformaning o'zini oqlashi."""
    summary = PeriodSummary()
    rows = (
        (
            await session.execute(
                sa.select(Submission).where(
                    Submission.period_id == period_id, Submission.deleted_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    for sub in rows:
        summary.total_submissions += 1
        if sub.status not in PAYABLE:
            continue
        summary.approved_count += 1
        summary.proposed_total = money(summary.proposed_total + sub.proposed_labor_amount)
        summary.approved_total = money(
            summary.approved_total + (sub.labor_amount or ZERO)
        )
        summary.parts_total = money(summary.parts_total + sub.parts_amount)
        if sub.auto_approved:
            summary.auto_approved_count += 1
            summary.auto_approved_total = money(
                summary.auto_approved_total + (sub.labor_amount or ZERO)
            )
    return summary


async def generate_for_period(session: AsyncSession, period: Period) -> list[Payout]:
    """Davr yopilganda to'lov varaqalari generatsiya qilinadi."""
    stmt = sa.select(Submission).where(
        Submission.period_id == period.id,
        Submission.deleted_at.is_(None),
        Submission.status.in_(PAYABLE),
    )
    submissions = list((await session.execute(stmt)).scalars().all())

    grouped: dict[int, list[Submission]] = {}
    for sub in submissions:
        grouped.setdefault(sub.author_id, []).append(sub)

    payouts: list[Payout] = []
    for employee_id, items in grouped.items():
        payout = (
            await session.execute(
                sa.select(Payout).where(
                    Payout.period_id == period.id, Payout.employee_id == employee_id
                )
            )
        ).scalar_one_or_none()
        if payout is None:
            payout = Payout(
                period_id=period.id, employee_id=employee_id, bonus=ZERO, penalty=ZERO
            )
            session.add(payout)

        proposed = ZERO
        approved = ZERO
        for sub in items:
            proposed = money(proposed + sub.proposed_labor_amount)
            approved = money(approved + (sub.labor_amount or ZERO))  # R5

        payout.submissions_count = len(items)
        payout.proposed_total = proposed
        payout.labor_total = approved
        payout.reduction_total = money(proposed - approved)
        payout.total = money(approved + payout.bonus - payout.penalty)
        payouts.append(payout)

    await session.flush()
    return payouts


async def adjust(
    session: AsyncSession,
    payout: Payout,
    *,
    actor_id: int,
    bonus: Decimal | None = None,
    penalty: Decimal | None = None,
    reason: str,
) -> Payout:
    """Bonus/jarima — qo'lda, sabab majburiy, audit log'ga yoziladi."""
    if not reason or len(reason.strip()) < 5:
        raise BusinessRuleViolated("Bonus/jarima uchun sabab majburiy")

    before = {"bonus": str(payout.bonus), "penalty": str(payout.penalty)}
    if bonus is not None:
        payout.bonus = money(bonus)
    if penalty is not None:
        payout.penalty = money(penalty)
    payout.adjust_reason = reason.strip()
    payout.total = money(payout.labor_total + payout.bonus - payout.penalty)

    await audit.log(
        session,
        action="payout.adjust",
        entity_type="payout",
        entity_id=payout.id,
        actor_id=actor_id,
        before=before,
        after={
            "bonus": str(payout.bonus),
            "penalty": str(payout.penalty),
            "reason": payout.adjust_reason,
        },
    )
    await session.flush()
    return payout


async def mark_paid(session: AsyncSession, payout: Payout, *, actor_id: int) -> Payout:
    period = await session.get(Period, payout.period_id)
    if period is not None and period.status != PeriodStatus.closed:
        raise PeriodClosed("To'lov faqat yopilgan davrda belgilanadi")
    payout.status = PayoutStatus.paid
    payout.paid_at = utcnow()
    await audit.log(
        session,
        action="payout.mark_paid",
        entity_type="payout",
        entity_id=payout.id,
        actor_id=actor_id,
    )
    await session.flush()
    return payout
