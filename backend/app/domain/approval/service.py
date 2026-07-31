"""Tasdiqlash oqimi — R1, R1a, R4 va holat o'tishlari.

Bitta bosqich: direktorga ko'tarish yo'q, oxirgi so'z adminda.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleViolated, Forbidden, InvalidStateTransition
from app.db.base import utcnow
from app.db.models import (
    Approval,
    ApprovalDecision,
    Employee,
    Submission,
    SubmissionStatus,
)
from app.domain import audit
from app.domain import vehicle as vehicle_domain
from app.domain.notify import service as notify
from app.domain.period import service as period_service
from app.domain.role import permissions
from app.domain.template import engine

MIN_COMMENT_LEN = 5

REVIEWABLE = (
    SubmissionStatus.SUBMITTED,
    SubmissionStatus.IN_REVIEW,
    SubmissionStatus.PRICE_DISPUTED,
)


def _require_comment(comment: str | None) -> str:
    text = (comment or "").strip()
    if len(text) < MIN_COMMENT_LEN:
        raise BusinessRuleViolated("Izoh majburiy")
    return text


def _approve_lines(submission: Submission) -> None:
    """Narx o'zgartirilmagan qatorlar: approved = proposed (R2 — oshirish yo'q)."""
    for line in submission.lines:
        if line.approved_amount is None:
            line.approved_unit_price = line.proposed_unit_price
            line.approved_amount = line.proposed_amount




async def start_review(
    session: AsyncSession, submission: Submission, actor: Employee
) -> Submission:
    """SUBMITTED → IN_REVIEW («Ko'rilmoqda» belgisi)."""
    if not permissions.can_review(actor):
        raise Forbidden("Faqat admin ko'rib chiqadi")
    if submission.status == SubmissionStatus.SUBMITTED:
        submission.status = SubmissionStatus.IN_REVIEW
        submission.reviewed_at = utcnow()
        await session.flush()
    return submission


async def approve(
    session: AsyncSession,
    submission: Submission,
    actor: Employee,
    *,
    comment: str | None = None,
) -> Submission:
    """Qo'lda tasdiqlash. R1: `approver_id ≠ author_id`."""
    if not permissions.can_review(actor):
        raise Forbidden("Faqat admin tasdiqlaydi")
    permissions.ensure_not_self_approval(actor, submission)  # R1
    await period_service.ensure_submission_period_open(session, submission)  # R4

    if submission.status not in REVIEWABLE:
        raise InvalidStateTransition(f"{submission.status.value} → approved mumkin emas")

    if submission.status == SubmissionStatus.PRICE_DISPUTED:
        comment = _require_comment(comment)  # nizoda yakuniy qaror izohi majburiy

    status_before = submission.status.value
    _approve_lines(submission)
    engine.recalculate_amounts(submission)
    submission.status = SubmissionStatus.APPROVED
    submission.decided_at = utcnow()
    await vehicle_domain.release(session, submission)

    session.add(
        Approval(
            submission_id=submission.id,
            actor_id=actor.id,
            decision=ApprovalDecision.approved,
            amount_before=submission.proposed_labor_amount,
            amount_after=submission.labor_amount,
            comment=(comment or None),
        )
    )
    await audit.log(
        session,
        action="submission.approve",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id,
        before={"status": status_before},
        after={"status": submission.status.value, "labor_amount": str(submission.labor_amount)},
    )
    await notify.enqueue(
        session,
        template_code="notify_approved",
        employee_id=submission.author_id,
        payload={
            "submission_id": submission.id,
            "number": submission.number,
            "amount": str(submission.labor_amount or submission.total_amount),
        },
    )
    await session.flush()
    return submission


async def auto_approve(session: AsyncSession, submission: Submission) -> Submission:
    """R1a — `admin` muallifi: DRAFT → APPROVED, tasdiqlovchisiz va kelishuvsiz."""
    _approve_lines(submission)
    engine.recalculate_amounts(submission)
    submission.status = SubmissionStatus.APPROVED
    submission.auto_approved = True
    submission.decided_at = utcnow()
    await vehicle_domain.release(session, submission)

    session.add(
        Approval(
            submission_id=submission.id,
            actor_id=None,  # tizim tasdiqladi
            decision=ApprovalDecision.auto_approved,
            amount_before=submission.proposed_labor_amount,
            amount_after=submission.labor_amount,
            comment="R1a: admin muallifi — avtomatik tasdiq",
        )
    )
    await audit.log(
        session,
        action="submission.auto_approve",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=None,
        after={"labor_amount": str(submission.labor_amount)},
    )
    await session.flush()
    return submission


async def reject(
    session: AsyncSession, submission: Submission, actor: Employee, comment: str
) -> Submission:
    """Ish bajarilmagan / soxta → hisobot yopiladi, to'lovga kirmaydi."""
    if not permissions.can_review(actor):
        raise Forbidden("Faqat admin rad etadi")
    permissions.ensure_not_self_approval(actor, submission)
    await period_service.ensure_submission_period_open(session, submission)
    if submission.status not in (SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW):
        raise InvalidStateTransition(f"{submission.status.value} → rejected mumkin emas")

    text = _require_comment(comment)
    submission.status = SubmissionStatus.REJECTED
    submission.decided_at = utcnow()
    await vehicle_domain.release(session, submission)

    session.add(
        Approval(
            submission_id=submission.id,
            actor_id=actor.id,
            decision=ApprovalDecision.rejected,
            comment=text,
        )
    )
    await audit.log(
        session,
        action="submission.reject",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id,
        after={"comment": text},
    )
    await notify.enqueue(
        session,
        template_code="notify_rejected",
        employee_id=submission.author_id,
        payload={"submission_id": submission.id, "number": submission.number, "comment": text},
    )
    await session.flush()
    return submission


async def reopen(
    session: AsyncSession, submission: Submission, actor: Employee, comment: str
) -> Submission:
    """Ma'lumot to'liq emas → muallifga qaytariladi, tarix saqlanadi."""
    if not permissions.can_review(actor):
        raise Forbidden("Faqat admin qaytaradi")
    await period_service.ensure_submission_period_open(session, submission)  # R4
    allowed = (
        SubmissionStatus.SUBMITTED,
        SubmissionStatus.IN_REVIEW,
        SubmissionStatus.PRICE_NEGOTIATION,
        SubmissionStatus.PRICE_DISPUTED,
        SubmissionStatus.APPROVED,
    )
    if submission.status not in allowed:
        raise InvalidStateTransition(f"{submission.status.value} → reopened mumkin emas")

    text = _require_comment(comment)
    submission.status = SubmissionStatus.REOPENED

    # kelishuv natijalari bekor qilinadi — muallif qaytadan to'ldiradi
    for line in submission.lines:
        line.approved_unit_price = None
        line.approved_amount = None
        line.price_change_reason = None
        line.price_changed_by = None
        line.mechanic_accepted_at = None
        line.mechanic_accept_mode = None
    submission.labor_amount = None
    submission.price_negotiated = False
    submission.price_proposed_at = None
    engine.recalculate_amounts(submission)

    session.add(
        Approval(
            submission_id=submission.id,
            actor_id=actor.id,
            decision=ApprovalDecision.reopened,
            comment=text,
        )
    )
    await audit.log(
        session,
        action="submission.reopen",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id,
        after={"comment": text},
    )
    await notify.enqueue(
        session,
        template_code="notify_reopened",
        employee_id=submission.author_id,
        payload={"submission_id": submission.id, "number": submission.number, "comment": text},
    )
    await session.flush()
    return submission
