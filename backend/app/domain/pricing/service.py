"""⭐ Narx kelishuvi — platformaning yuragi.

N1 `proposed_amount` o'zgarmaydi · N2 sabab majburiy · N3 nizoda admin qayta
ko'radi · N4 48 soat sukut → avtomatik rozilik · N5 oshirish yo'q ·
N6 har qadam audit'da · N8 admin hisoboti kelishuvga kirmaydi ·
N9 tayanch narx `reporter`ga API'da ham berilmaydi.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    BusinessRuleViolated,
    Forbidden,
    InvalidStateTransition,
    PriceIncreaseForbidden,
)
from app.db.base import ZERO, as_utc, money, utcnow
from app.db.models import (
    AcceptMode,
    Approval,
    ApprovalDecision,
    Employee,
    LineKind,
    Submission,
    SubmissionLine,
    SubmissionStatus,
)
from app.domain import audit
from app.domain import vehicle as vehicle_domain
from app.domain.notify import service as notify
from app.domain.period import service as period_service
from app.domain.role import permissions
from app.domain.template import engine

MIN_REASON_LEN = 5
HISTORY_DAYS = 90
APPROVED_STATUSES = (SubmissionStatus.APPROVED, SubmissionStatus.PAID)


# --- Narx tarixi (admin ekrani uchun) ---------------------------------------


@dataclass
class LinePriceContext:
    line_id: int
    name: str
    proposed_amount: Decimal
    count: int = 0
    avg_approved: Decimal | None = None
    min_approved: Decimal | None = None
    max_approved: Decimal | None = None
    author_avg: Decimal | None = None
    author_reduction_pct: Decimal | None = None
    quick_amounts: list[Decimal] = field(default_factory=list)

    @property
    def has_history(self) -> bool:
        return self.count > 0


async def _catalog_history(
    session: AsyncSession, catalog_id: int | None, name: str, *, author_id: int | None = None
) -> tuple[int, Decimal | None, Decimal | None, Decimal | None]:
    """Oxirgi 90 kunda tasdiqlangan narxlar: (soni, o'rtacha, min, maks)."""
    since = utcnow() - dt.timedelta(days=HISTORY_DAYS)
    stmt = (
        sa.select(
            sa.func.count(SubmissionLine.id),
            sa.func.avg(SubmissionLine.approved_amount),
            sa.func.min(SubmissionLine.approved_amount),
            sa.func.max(SubmissionLine.approved_amount),
        )
        .join(Submission, Submission.id == SubmissionLine.submission_id)
        .where(
            SubmissionLine.kind == LineKind.labor,
            SubmissionLine.approved_amount.is_not(None),
            Submission.status.in_(APPROVED_STATUSES),
            Submission.decided_at >= since,
        )
    )
    if catalog_id is not None:
        stmt = stmt.where(SubmissionLine.catalog_id == catalog_id)
    else:
        stmt = stmt.where(SubmissionLine.name == name, SubmissionLine.catalog_id.is_(None))
    if author_id is not None:
        stmt = stmt.where(Submission.author_id == author_id)

    count, avg_v, min_v, max_v = (await session.execute(stmt)).one()
    return (
        int(count or 0),
        money(avg_v) if avg_v is not None else None,
        money(min_v) if min_v is not None else None,
        money(max_v) if max_v is not None else None,
    )


async def price_context(
    session: AsyncSession, submission: Submission, actor: Employee
) -> list[LinePriceContext]:
    """Admin uchun savdolashuv ma'lumoti. R3/N9 — `reporter`ga berilmaydi."""
    permissions.ensure_reference_price_visible(actor)

    contexts: list[LinePriceContext] = []
    for line in submission.lines:
        if line.kind != LineKind.labor:
            continue
        count, avg_v, min_v, max_v = await _catalog_history(session, line.catalog_id, line.name)
        _, author_avg, _, _ = await _catalog_history(
            session, line.catalog_id, line.name, author_id=submission.author_id
        )
        stats = await employee_price_stats(session, submission.author_id)
        ctx = LinePriceContext(
            line_id=line.id,
            name=line.name,
            proposed_amount=line.proposed_amount,
            count=count,
            avg_approved=avg_v,
            min_approved=min_v,
            max_approved=max_v,
            author_avg=author_avg,
            author_reduction_pct=stats.reduction_rate_pct,
        )
        ctx.quick_amounts = _quick_amounts(line.proposed_amount, avg_v, min_v, max_v)
        contexts.append(ctx)
    return contexts


def _quick_amounts(
    proposed: Decimal, avg_v: Decimal | None, min_v: Decimal | None, max_v: Decimal | None
) -> list[Decimal]:
    """Tez tanlov tugmalari — admin summani qo'lda yozmasligi uchun."""
    candidates: list[Decimal] = []
    for value in (avg_v, max_v, min_v):
        if value is not None and ZERO < value < proposed:
            candidates.append(money(value))
    for pct in (Decimal("0.9"), Decimal("0.8"), Decimal("0.7")):
        candidates.append(money((proposed * pct / 10000).quantize(Decimal("1")) * 10000))

    result: list[Decimal] = []
    for value in candidates:
        if ZERO < value < proposed and value not in result:
            result.append(value)
        if len(result) == 3:
            break
    return result


@dataclass
class EmployeePriceStats:
    """Xodim o'z statistikasini ko'radi (A-24), boshqalarnikini emas."""

    lines_total: int = 0
    lines_reduced: int = 0
    proposed_total: Decimal = ZERO
    approved_total: Decimal = ZERO
    disputes: int = 0

    @property
    def reduction_total(self) -> Decimal:
        return money(self.proposed_total - self.approved_total)

    @property
    def reduction_rate_pct(self) -> Decimal:
        """Necha % hollarda narxi kamaytirilgan."""
        if not self.lines_total:
            return ZERO
        return money(Decimal(self.lines_reduced) * 100 / Decimal(self.lines_total))

    @property
    def avg_reduction_pct(self) -> Decimal:
        """O'rtacha necha % kamaytirilgan."""
        if self.proposed_total <= ZERO:
            return ZERO
        return money(self.reduction_total * 100 / self.proposed_total)


async def employee_price_stats(
    session: AsyncSession, employee_id: int, *, period_id: int | None = None
) -> EmployeePriceStats:
    stmt = (
        sa.select(SubmissionLine, Submission.status)
        .join(Submission, Submission.id == SubmissionLine.submission_id)
        .where(
            Submission.author_id == employee_id,
            Submission.deleted_at.is_(None),
            SubmissionLine.kind == LineKind.labor,
            SubmissionLine.approved_amount.is_not(None),
            Submission.status.in_(APPROVED_STATUSES),
        )
    )
    if period_id is not None:
        stmt = stmt.where(Submission.period_id == period_id)

    stats = EmployeePriceStats()
    for line, _status in (await session.execute(stmt)).all():
        stats.lines_total += 1
        stats.proposed_total = money(stats.proposed_total + line.proposed_amount)
        stats.approved_total = money(stats.approved_total + (line.approved_amount or ZERO))
        if (line.approved_amount or ZERO) < line.proposed_amount:
            stats.lines_reduced += 1

    disputes_stmt = (
        sa.select(sa.func.count(Approval.id))
        .join(Submission, Submission.id == Approval.submission_id)
        .where(
            Submission.author_id == employee_id,
            Approval.decision == ApprovalDecision.price_disputed,
        )
    )
    stats.disputes = int((await session.execute(disputes_stmt)).scalar_one() or 0)
    return stats


# --- Kelishuv oqimi ----------------------------------------------------------


async def propose_price(
    session: AsyncSession,
    submission: Submission,
    actor: Employee,
    *,
    changes: list[tuple[int, Decimal]],
    comment: str,
) -> Submission:
    """Admin narxni kamaytiradi. N2 — sabab majburiy, N5 — oshirish taqiqlanadi."""
    if not permissions.can_review(actor):
        raise Forbidden("Faqat admin narx taklif qiladi")
    permissions.ensure_not_self_approval(actor, submission)  # N8 bilan birga
    await period_service.ensure_submission_period_open(session, submission)  # R4/N7

    allowed = (
        SubmissionStatus.SUBMITTED,
        SubmissionStatus.IN_REVIEW,
        SubmissionStatus.PRICE_NEGOTIATION,
        SubmissionStatus.PRICE_DISPUTED,
    )
    if submission.status not in allowed:
        raise InvalidStateTransition(
            f"{submission.status.value} → price_negotiation mumkin emas"
        )

    reason = (comment or "").strip()
    if len(reason) < MIN_REASON_LEN:
        raise BusinessRuleViolated("Narxni kamaytirishda sabab majburiy (N2)")

    lines_by_id = {line.id: line for line in submission.lines}
    applied = 0
    for line_id, raw_amount in changes:
        line = lines_by_id.get(line_id)
        if line is None:
            raise BusinessRuleViolated(f"Qator topilmadi: {line_id}")

        amount = money(raw_amount)
        if amount < ZERO:
            raise BusinessRuleViolated("Summa manfiy bo'lishi mumkin emas")
        if amount > line.proposed_amount:
            raise PriceIncreaseForbidden(  # R2 / N5
                "Admin narxni oshira olmaydi",
                line_id=line_id,
                proposed=str(line.proposed_amount),
            )
        if amount == line.proposed_amount:
            continue  # o'zgarish yo'q

        before = line.approved_amount
        line.approved_amount = amount
        line.approved_unit_price = (
            money(amount / line.qty) if line.qty and line.qty > ZERO else amount
        )
        line.price_change_reason = reason
        line.price_changed_by = actor.id
        line.mechanic_accepted_at = None
        line.mechanic_accept_mode = None

        # tarixiy tayanch snapshot (tasdiqlash paytidagi holat)
        count, avg_v, _, _ = await _catalog_history(session, line.catalog_id, line.name)
        if count and avg_v is not None:
            line.reference_amount = avg_v
            if avg_v > ZERO:
                line.deviation_pct = money(
                    (line.proposed_amount - avg_v) * 100 / avg_v
                )

        session.add(
            Approval(
                submission_id=submission.id,
                actor_id=actor.id,
                decision=ApprovalDecision.price_proposed,
                line_id=line.id,
                amount_before=before if before is not None else line.proposed_amount,
                amount_after=amount,
                comment=reason,
            )
        )
        applied += 1

    if applied == 0:
        raise BusinessRuleViolated("Hech qanday narx o'zgartirilmadi")

    submission.status = SubmissionStatus.PRICE_NEGOTIATION
    submission.price_negotiated = True
    submission.price_proposed_at = utcnow()
    submission.labor_amount = None  # kelishuv tugagunicha yakuniy summa yo'q
    data = dict(submission.data or {})
    data.pop("_price_reminder_sent", None)
    submission.data = data

    await audit.log(
        session,
        action="submission.propose_price",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id,
        after={"lines": applied, "reason": reason},
    )
    await _notify_price_proposed(session, submission, reason)
    await session.flush()
    return submission


async def _notify_price_proposed(
    session: AsyncSession, submission: Submission, reason: str
) -> None:
    proposed = engine.sum_lines(list(submission.lines), LineKind.labor)
    approved = engine.sum_lines(list(submission.lines), LineKind.labor, approved=True)
    await notify.enqueue(
        session,
        template_code="notify_price_proposed",
        employee_id=submission.author_id,
        payload={
            "submission_id": submission.id,
            "number": submission.number,
            "proposed": str(proposed),
            "approved": str(approved),
            "reason": reason,
        },
    )


async def accept_price(
    session: AsyncSession,
    submission: Submission,
    actor: Employee | None,
    *,
    mode: AcceptMode = AcceptMode.manual,
) -> Submission:
    """Muallif rozi bo'ldi (yoki 48 soat sukut) → APPROVED."""
    if submission.status != SubmissionStatus.PRICE_NEGOTIATION:
        raise InvalidStateTransition(f"{submission.status.value} → accept mumkin emas")
    if mode == AcceptMode.manual:
        if actor is None or not permissions.is_author(actor, submission):
            raise Forbidden("Faqat hisobot muallifi rozilik beradi")
    await period_service.ensure_submission_period_open(session, submission)

    now = utcnow()
    for line in submission.lines:
        if line.approved_amount is None:
            line.approved_unit_price = line.proposed_unit_price
            line.approved_amount = line.proposed_amount
        elif line.approved_amount < line.proposed_amount:
            line.mechanic_accepted_at = now
            line.mechanic_accept_mode = mode

    engine.recalculate_amounts(submission)
    submission.status = SubmissionStatus.APPROVED
    submission.decided_at = now

    await vehicle_domain.release(session, submission)

    session.add(
        Approval(
            submission_id=submission.id,
            actor_id=actor.id if actor is not None else None,
            decision=ApprovalDecision.price_accepted,
            amount_before=submission.proposed_labor_amount,
            amount_after=submission.labor_amount,
            comment=("auto_48h" if mode == AcceptMode.auto_48h else None),
        )
    )
    await audit.log(
        session,
        action="submission.accept_price",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id if actor is not None else None,
        after={"mode": mode.value, "labor_amount": str(submission.labor_amount)},
    )
    await notify.enqueue(
        session,
        template_code=(
            "notify_auto_accepted" if mode == AcceptMode.auto_48h else "notify_approved"
        ),
        employee_id=submission.author_id,
        payload={
            "submission_id": submission.id,
            "number": submission.number,
            "amount": str(submission.labor_amount or ZERO),
        },
    )
    await session.flush()
    return submission


async def dispute_price(
    session: AsyncSession, submission: Submission, actor: Employee, *, comment: str
) -> Submission:
    """Muallif rozi emas → admin qayta ko'radi (N3). Avtomatik rad etish yo'q."""
    if not permissions.is_author(actor, submission):
        raise Forbidden("Faqat hisobot muallifi nizo ochadi")
    if submission.status != SubmissionStatus.PRICE_NEGOTIATION:
        raise InvalidStateTransition(f"{submission.status.value} → dispute mumkin emas")

    text = (comment or "").strip()
    if len(text) < MIN_REASON_LEN:
        raise BusinessRuleViolated("Nizo izohi majburiy")

    submission.status = SubmissionStatus.PRICE_DISPUTED
    session.add(
        Approval(
            submission_id=submission.id,
            actor_id=actor.id,
            decision=ApprovalDecision.price_disputed,
            comment=text,
        )
    )
    await audit.log(
        session,
        action="submission.dispute_price",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id,
        after={"comment": text},
    )
    await notify.notify_admins(
        session,
        template_code="notify_price_disputed",
        payload={
            "submission_id": submission.id,
            "number": submission.number,
            "author": actor.full_name,
            "comment": text,
        },
    )
    await session.flush()
    return submission


# --- Fon vazifalari ----------------------------------------------------------


async def expired_negotiations(session: AsyncSession) -> list[Submission]:
    """N4 — 48 soatdan oshgan kelishuvlar."""
    deadline = utcnow() - dt.timedelta(hours=settings.price_auto_accept_hours)
    stmt = sa.select(Submission).where(
        Submission.status == SubmissionStatus.PRICE_NEGOTIATION,
        Submission.deleted_at.is_(None),
        Submission.price_proposed_at.is_not(None),
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return [s for s in rows if as_utc(s.price_proposed_at) <= deadline]


async def negotiations_needing_reminder(session: AsyncSession) -> list[Submission]:
    """24 soat javob bo'lmasa — eslatma (bir marta)."""
    threshold = utcnow() - dt.timedelta(hours=settings.price_reminder_hours)
    stmt = sa.select(Submission).where(
        Submission.status == SubmissionStatus.PRICE_NEGOTIATION,
        Submission.deleted_at.is_(None),
        Submission.price_proposed_at.is_not(None),
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return [
        s
        for s in rows
        if as_utc(s.price_proposed_at) <= threshold
        and not (s.data or {}).get("_price_reminder_sent")
    ]


def mark_reminder_sent(submission: Submission) -> None:
    data = dict(submission.data or {})
    data["_price_reminder_sent"] = True
    submission.data = data
