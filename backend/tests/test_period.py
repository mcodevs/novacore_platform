"""Davr va to'lov testlari — R4, R5, precheck."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.errors import BusinessRuleViolated, PeriodClosed
from app.db.models import PeriodStatus, SubmissionStatus
from app.domain.approval import service as approval_service
from app.domain.payout import service as payout_service
from app.domain.period import service as period_service
from app.domain.pricing import service as pricing_service
from app.domain.submission import service as submission_service
from tests.conftest import create_ready_submission, get_template, make_employee, make_vehicle


async def _approved_submission(session, mechanic, admin, vehicle, *, price, approved=None):
    submission = await create_ready_submission(
        session, mechanic, vehicle, works=[("Ish", Decimal(price))]
    )
    await submission_service.submit(session, submission, mechanic)
    if approved is None:
        await approval_service.approve(session, submission, admin)
    else:
        line = submission.lines[0]
        await pricing_service.propose_price(
            session, submission, admin, changes=[(line.id, Decimal(approved))],
            comment="tarixga ko'ra kamaytirildi",
        )
        await pricing_service.accept_price(session, submission, mechanic)
    return submission


async def test_precheck_blocks_on_unapproved(session):
    mechanic = await make_employee(session, role_code="mechanic")
    await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, submission, mechanic)

    period = await period_service.current_period(session)
    result = await period_service.precheck(session, period)

    assert not result.can_close
    assert ("precheck_unapproved", {"n": 1}) in result.blockers


async def test_close_period_blocked(session):
    mechanic = await make_employee(session, role_code="mechanic")
    admin = await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, submission, mechanic)

    period = await period_service.current_period(session)
    with pytest.raises(BusinessRuleViolated):
        await period_service.close_period(session, period, admin.id)


async def test_close_period_generates_payouts_from_approved_amount(session):
    """R5 — to'lov faqat `approved_amount` bo'yicha."""
    mechanic = await make_employee(session, role_code="mechanic", name="Karimov B.")
    admin = await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)
    vehicle2 = await make_vehicle(session, plate="01F333CC")

    await _approved_submission(session, mechanic, admin, vehicle, price="250000", approved="180000")
    await _approved_submission(session, mechanic, admin, vehicle2, price="120000")

    period = await period_service.current_period(session)
    payouts = await payout_service.generate_for_period(session, period)

    assert len(payouts) == 1
    payout = payouts[0]
    assert payout.submissions_count == 2
    assert payout.proposed_total == Decimal("370000.00")
    assert payout.labor_total == Decimal("300000.00")  # 180 000 + 120 000
    assert payout.reduction_total == Decimal("70000.00")
    assert payout.total == Decimal("300000.00")


async def test_closed_period_blocks_new_submission(session):
    """R4 — yopilgan davrga yozuv qo'shilmaydi."""
    mechanic = await make_employee(session, role_code="mechanic")
    admin = await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)

    period = await period_service.current_period(session)
    await period_service.close_period(session, period, admin.id)

    template = await get_template(session, "car_repair")
    with pytest.raises(PeriodClosed):
        await submission_service.create_draft(session, mechanic, template)


async def test_closed_period_blocks_approval(session):
    mechanic = await make_employee(session, role_code="mechanic")
    admin = await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, submission, mechanic)

    period = await period_service.current_period(session)
    period.status = PeriodStatus.closed
    await session.flush()

    with pytest.raises(PeriodClosed):
        await approval_service.approve(session, submission, admin)


async def test_close_moves_approved_to_paid(session):
    mechanic = await make_employee(session, role_code="mechanic")
    admin = await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)
    submission = await _approved_submission(
        session, mechanic, admin, vehicle, price="200000"
    )

    period = await period_service.current_period(session)
    await period_service.close_period(session, period, admin.id)
    await session.refresh(submission)

    assert period.status == PeriodStatus.closed
    assert submission.status == SubmissionStatus.PAID


async def test_period_summary_savings(session):
    """⭐ «Bu oy kelishuv X so'm tejadi»."""
    mechanic = await make_employee(session, role_code="mechanic")
    admin = await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)
    await _approved_submission(
        session, mechanic, admin, vehicle, price="250000", approved="180000"
    )

    period = await period_service.current_period(session)
    summary = await payout_service.period_summary(session, period.id)

    assert summary.proposed_total == Decimal("250000.00")
    assert summary.approved_total == Decimal("180000.00")
    assert summary.saved == Decimal("70000.00")
    assert summary.saved_pct == Decimal("28.00")


async def test_auto_approved_counted_separately(session):
    """Shaffoflik: admin hisoboti oylik hisobotda alohida satr."""
    admin = await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session, plate="01G444DD")
    submission = await create_ready_submission(
        session, admin, vehicle, works=[("Diagnostika", Decimal("100000"))]
    )
    await submission_service.submit(session, submission, admin)

    period = await period_service.current_period(session)
    summary = await payout_service.period_summary(session, period.id)

    assert summary.auto_approved_count == 1
    assert summary.auto_approved_total == Decimal("100000.00")


async def test_reopen_period_requires_reason(session):
    admin = await make_employee(session, role_code="admin")
    period = await period_service.current_period(session)
    await period_service.close_period(session, period, admin.id)

    with pytest.raises(BusinessRuleViolated):
        await period_service.reopen_period(session, period, admin.id, "x")

    await period_service.reopen_period(
        session, period, admin.id, "Buxgalteriya xatosi tuzatildi"
    )
    assert period.status == PeriodStatus.open
