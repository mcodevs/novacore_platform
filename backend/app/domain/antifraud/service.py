"""Bayroqlar — **bloklamaydi**, faqat admin e'tiborini yo'naltiradi.

⚠️ Faza 1 (v1) da o'chirilgan: `ANTIFRAUD_ENABLED=false`
(docs/04-flows/02-antifraud.md §9 — v1 da narx kelishuvi va majburiy foto
yetarli). Yoqilganda quyidagi arzon tekshiruvlar ishlaydi.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import ZERO, as_utc, money, utcnow
from app.db.models import (
    Flag,
    FlagSeverity,
    LineKind,
    Media,
    Submission,
    SubmissionLine,
    SubmissionStatus,
)

HISTORY_DAYS = 90
REWORK_DAYS = 30
PRICE_WARNING_PCT = Decimal("30")
PRICE_CRITICAL_PCT = Decimal("100")
FREQUENT_REPAIR_PER_MONTH = 3
LATE_SUBMIT_DAYS = 3


async def _avg_approved(session: AsyncSession, line: SubmissionLine) -> Decimal | None:
    since = utcnow() - dt.timedelta(days=HISTORY_DAYS)
    stmt = (
        sa.select(sa.func.avg(SubmissionLine.approved_amount))
        .join(Submission, Submission.id == SubmissionLine.submission_id)
        .where(
            SubmissionLine.approved_amount.is_not(None),
            SubmissionLine.kind == LineKind.labor,
            Submission.status.in_([SubmissionStatus.APPROVED, SubmissionStatus.PAID]),
            Submission.decided_at >= since,
        )
    )
    if line.catalog_id is not None:
        stmt = stmt.where(SubmissionLine.catalog_id == line.catalog_id)
    else:
        stmt = stmt.where(SubmissionLine.name == line.name)
    value = (await session.execute(stmt)).scalar_one_or_none()
    return money(value) if value is not None else None


async def evaluate(session: AsyncSession, submission: Submission) -> list[Flag]:
    """Hisobot yuborilganda chaqiriladi. Hech qachon yuborishni bloklamaydi."""
    if not settings.antifraud_enabled:
        return []

    flags: list[Flag] = []

    def add(code: str, severity: FlagSeverity, **details: object) -> None:
        flags.append(
            Flag(
                submission_id=submission.id,
                code=code,
                severity=severity,
                details=dict(details),
            )
        )

    # F2 — narx tarixiy o'rtachadan yuqori
    for line in submission.lines:
        if line.kind != LineKind.labor:
            continue
        avg_value = await _avg_approved(session, line)
        if avg_value is None or avg_value <= ZERO:
            continue
        deviation = (line.proposed_amount - avg_value) * 100 / avg_value
        if deviation > PRICE_CRITICAL_PCT:
            add(
                "price_far_above_history",
                FlagSeverity.critical,
                line_id=line.id,
                avg=str(avg_value),
                deviation_pct=str(money(deviation)),
            )
        elif deviation > PRICE_WARNING_PCT:
            add(
                "price_above_history",
                FlagSeverity.warning,
                line_id=line.id,
                avg=str(avg_value),
                deviation_pct=str(money(deviation)),
            )

    # F3 — aynan bir xil fayl (sha256)
    for item in submission.media:
        if item.deleted_at is not None:
            continue
        duplicate = (
            await session.execute(
                sa.select(Media.id, Media.submission_id).where(
                    Media.sha256 == item.sha256,
                    Media.id != item.id,
                    Media.deleted_at.is_(None),
                )
            )
        ).first()
        if duplicate:
            add(
                "identical_file",
                FlagSeverity.critical,
                media_id=item.id,
                similar_media_id=duplicate[0],
                similar_submission_id=duplicate[1],
            )

    # F6 — rework: shu mashina + shu kategoriya, 30 kun ichida
    category = (submission.data or {}).get("category")
    if submission.subject_vehicle_id and category:
        since = utcnow() - dt.timedelta(days=REWORK_DAYS)
        previous = list(
            (
                await session.execute(
                    sa.select(Submission).where(
                        Submission.subject_vehicle_id == submission.subject_vehicle_id,
                        Submission.id != submission.id,
                        Submission.deleted_at.is_(None),
                        Submission.status.in_(
                            [SubmissionStatus.APPROVED, SubmissionStatus.PAID]
                        ),
                        Submission.submitted_at >= since,
                    )
                )
            )
            .scalars()
            .all()
        )
        if any((s.data or {}).get("category") == category for s in previous):
            add("rework", FlagSeverity.warning, category=category, days=REWORK_DAYS)
        if len(previous) + 1 > FREQUENT_REPAIR_PER_MONTH:
            add("frequent_repair", FlagSeverity.warning, count=len(previous) + 1)

    # kech yuborilgan
    if submission.left_at is not None and submission.submitted_at is not None:
        delay = as_utc(submission.submitted_at) - as_utc(submission.left_at)
        if delay > dt.timedelta(days=LATE_SUBMIT_DAYS):
            add("late_submit", FlagSeverity.info, days=delay.days)

    for flag in flags:
        session.add(flag)
    submission.flags_count = len(flags)
    await session.flush()
    return flags
