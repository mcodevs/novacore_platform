"""Tasdiqlash testlari — R1, R1a va holat o'tishlari."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.errors import (
    BusinessRuleViolated,
    Forbidden,
    InvalidStateTransition,
    SelfApprovalForbidden,
)
from app.db.models import ApprovalDecision, SubmissionStatus, VehicleStatus
from app.domain.approval import service as approval_service
from app.domain.pricing import service as pricing_service
from app.domain.submission import service as submission_service
from tests.conftest import create_ready_submission, make_employee, make_vehicle


async def _setup(session):
    mechanic = await make_employee(session, role_code="mechanic", name="Karimov B.")
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, submission, mechanic)
    return mechanic, admin, vehicle, submission


async def test_approve_without_price_change(session):
    _, admin, vehicle, submission = await _setup(session)

    await approval_service.approve(session, submission, admin)

    assert submission.status == SubmissionStatus.APPROVED
    assert submission.auto_approved is False
    assert submission.labor_amount == Decimal("250000.00")
    assert submission.lines[0].approved_amount == Decimal("250000.00")
    assert vehicle.status == VehicleStatus.active


async def test_self_approval_forbidden(session):
    """R1 — muallif o'z hisobotini qo'lda tasdiqlay olmaydi."""
    admin_author = await make_employee(session, role_code="admin", name="Admin A.")
    other_admin = await make_employee(session, role_code="admin", name="Admin B.")
    vehicle = await make_vehicle(session, plate="01D111AA")

    submission = await create_ready_submission(session, admin_author, vehicle)
    # admin muallifi — avtomatik tasdiqlanadi, ammo qo'lda tasdiqlash baribir taqiq
    submission.status = SubmissionStatus.SUBMITTED
    submission.auto_approved = False
    await session.flush()

    with pytest.raises(SelfApprovalForbidden):
        await approval_service.approve(session, submission, admin_author)

    await approval_service.approve(session, submission, other_admin)
    assert submission.status == SubmissionStatus.APPROVED


async def test_reporter_cannot_approve(session):
    mechanic, _, _, submission = await _setup(session)
    other = await make_employee(session, role_code="mechanic", name="Boshqa usta")

    with pytest.raises(Forbidden):
        await approval_service.approve(session, submission, other)


async def test_accountant_cannot_approve(session):
    _, _, _, submission = await _setup(session)
    accountant = await make_employee(session, role_code="accountant", name="Buxgalter")

    with pytest.raises(Forbidden):
        await approval_service.approve(session, submission, accountant)


async def test_cannot_approve_draft(session):
    mechanic = await make_employee(session, role_code="mechanic")
    admin = await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)

    with pytest.raises(InvalidStateTransition):
        await approval_service.approve(session, submission, admin)


async def test_reject_requires_comment(session):
    _, admin, _, submission = await _setup(session)

    with pytest.raises(BusinessRuleViolated):
        await approval_service.reject(session, submission, admin, comment="")

    await approval_service.reject(session, submission, admin, comment="Ish bajarilmagan")
    assert submission.status == SubmissionStatus.REJECTED


async def test_reopen_resets_negotiation_and_allows_edit(session):
    mechanic, admin, _, submission = await _setup(session)
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="tarixga ko'ra"
    )

    await approval_service.reopen(
        session, submission, admin, comment="Foto sifatsiz, qayta suratga oling"
    )

    assert submission.status == SubmissionStatus.REOPENED
    assert line.approved_amount is None
    assert line.price_change_reason is None
    assert submission.labor_amount is None
    assert submission.price_negotiated is False
    # muallif endi tahrirlay oladi
    submission_service.ensure_editable(submission, mechanic)


async def test_reopened_can_be_resubmitted(session):
    mechanic, admin, _, submission = await _setup(session)
    await approval_service.reopen(session, submission, admin, comment="Muammo fotosi aniq emas")

    await submission_service.submit(session, submission, mechanic)
    assert submission.status == SubmissionStatus.SUBMITTED


async def test_start_review_marks_in_review(session):
    _, admin, _, submission = await _setup(session)

    await approval_service.start_review(session, submission, admin)

    assert submission.status == SubmissionStatus.IN_REVIEW
    assert submission.reviewed_at is not None


async def test_auto_approved_writes_system_approval(session):
    """R1a — `approvals(decision='auto_approved', actor_id=NULL)`."""
    import sqlalchemy as sa

    from app.db.models import Approval

    admin = await make_employee(session, role_code="admin", name="Admin A.")
    vehicle = await make_vehicle(session, plate="01E222BB")
    submission = await create_ready_submission(session, admin, vehicle)
    await submission_service.submit(session, submission, admin)

    rows = list(
        (
            await session.execute(
                sa.select(Approval).where(Approval.submission_id == submission.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].decision == ApprovalDecision.auto_approved
    assert rows[0].actor_id is None
    assert submission.auto_approved is True
