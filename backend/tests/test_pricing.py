"""⭐ Narx kelishuvi testlari — R2, R2a, R2b, N3, N4, R1a, R3."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from app.core.errors import (
    BusinessRuleViolated,
    Forbidden,
    InvalidStateTransition,
    PriceIncreaseForbidden,
    PriceReferenceHidden,
)
from app.db.base import utcnow
from app.db.models import AcceptMode, ApprovalDecision, SubmissionStatus
from app.domain.approval import service as approval_service
from app.domain.pricing import service as pricing_service
from app.domain.submission import service as submission_service
from tests.conftest import create_ready_submission, make_employee, make_vehicle


async def _submitted(session, *, price=Decimal("250000")):
    mechanic = await make_employee(session, role_code="mechanic", name="Karimov B.")
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(
        session, mechanic, vehicle, works=[("Old tormoz kolodkasi", price)]
    )
    await submission_service.submit(session, submission, mechanic)
    return mechanic, admin, submission


async def test_propose_price_reduces_and_starts_negotiation(session):
    mechanic, admin, submission = await _submitted(session)
    line = submission.lines[0]

    await pricing_service.propose_price(
        session,
        submission,
        admin,
        changes=[(line.id, Decimal("180000"))],
        comment="Bu ish odatda 175 000 ga bo'lgan",
    )

    assert submission.status == SubmissionStatus.PRICE_NEGOTIATION
    assert submission.price_negotiated is True
    assert line.approved_amount == Decimal("180000.00")
    assert line.price_change_reason == "Bu ish odatda 175 000 ga bo'lgan"
    assert line.price_changed_by == admin.id
    # R2a — so'ralgan summa hech qachon ustidan yozilmaydi
    assert line.proposed_amount == Decimal("250000.00")
    # yakuniy summa kelishuv tugagunicha yo'q
    assert submission.labor_amount is None


async def test_price_increase_forbidden(session):
    """R2 / N5 — admin narxni oshira olmaydi."""
    _, admin, submission = await _submitted(session)
    line = submission.lines[0]

    with pytest.raises(PriceIncreaseForbidden):
        await pricing_service.propose_price(
            session,
            submission,
            admin,
            changes=[(line.id, Decimal("300000"))],
            comment="qo'shimcha ish bor edi",
        )
    assert line.approved_amount is None
    assert submission.status == SubmissionStatus.SUBMITTED


async def test_reason_is_required_for_reduction(session):
    """R2b / N2 — sabab majburiy."""
    _, admin, submission = await _submitted(session)
    line = submission.lines[0]

    with pytest.raises(BusinessRuleViolated):
        await pricing_service.propose_price(
            session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="ok"
        )
    assert line.approved_amount is None


async def test_author_accepts_price(session):
    mechanic, admin, submission = await _submitted(session)
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="tarixga ko'ra"
    )

    await pricing_service.accept_price(session, submission, mechanic)

    assert submission.status == SubmissionStatus.APPROVED
    assert submission.labor_amount == Decimal("180000.00")  # to'lov asosi
    assert line.mechanic_accept_mode == AcceptMode.manual
    assert line.mechanic_accepted_at is not None
    assert line.proposed_amount == Decimal("250000.00")  # R2a


async def test_only_author_can_accept(session):
    _, admin, submission = await _submitted(session)
    other = await make_employee(session, role_code="mechanic", name="Boshqa usta")
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="sabab bor"
    )

    with pytest.raises(Forbidden):
        await pricing_service.accept_price(session, submission, other)


async def test_auto_accept_after_48h(session):
    """N4 — 48 soat javob bo'lmasa avtomatik rozilik."""
    mechanic, admin, submission = await _submitted(session)
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="tarix bo'yicha"
    )

    # taklif 49 soat oldin qilingan deb belgilaymiz
    submission.price_proposed_at = utcnow() - dt.timedelta(hours=49)
    await session.flush()

    expired = await pricing_service.expired_negotiations(session)
    assert [s.id for s in expired] == [submission.id]

    await pricing_service.accept_price(
        session, submission, None, mode=AcceptMode.auto_48h
    )
    assert submission.status == SubmissionStatus.APPROVED
    assert submission.labor_amount == Decimal("180000.00")
    assert line.mechanic_accept_mode == AcceptMode.auto_48h


async def test_not_expired_before_48h(session):
    _, admin, submission = await _submitted(session)
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="sabab bor"
    )
    submission.price_proposed_at = utcnow() - dt.timedelta(hours=47)
    await session.flush()

    assert await pricing_service.expired_negotiations(session) == []


async def test_reminder_sent_once(session):
    _, admin, submission = await _submitted(session)
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="sabab bor"
    )
    submission.price_proposed_at = utcnow() - dt.timedelta(hours=25)
    await session.flush()

    assert len(await pricing_service.negotiations_needing_reminder(session)) == 1
    pricing_service.mark_reminder_sent(submission)
    await session.flush()
    assert await pricing_service.negotiations_needing_reminder(session) == []


async def test_dispute_then_admin_final_decision(session):
    """N3 — nizoda avtomatik rad etish yo'q, oxirgi so'z adminda."""
    mechanic, admin, submission = await _submitted(session)
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="tarixga ko'ra"
    )

    await pricing_service.dispute_price(
        session, submission, mechanic, comment="Boltlar zanglagan edi, kesib olindi"
    )
    assert submission.status == SubmissionStatus.PRICE_DISPUTED

    # yakuniy qarorda izoh majburiy
    with pytest.raises(BusinessRuleViolated):
        await approval_service.approve(session, submission, admin)

    await approval_service.approve(
        session, submission, admin, comment="Gaplashdik, 200 000 ga kelishdik"
    )
    assert submission.status == SubmissionStatus.APPROVED


async def test_admin_can_re_propose_after_dispute(session):
    mechanic, admin, submission = await _submitted(session)
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("180000"))], comment="tarixga ko'ra"
    )
    await pricing_service.dispute_price(
        session, submission, mechanic, comment="Ish murakkab edi"
    )

    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("210000"))], comment="yarmiga kelishdik"
    )
    assert submission.status == SubmissionStatus.PRICE_NEGOTIATION
    assert line.approved_amount == Decimal("210000.00")
    assert line.proposed_amount == Decimal("250000.00")  # R2a


async def test_dispute_only_in_negotiation(session):
    mechanic, _, submission = await _submitted(session)
    with pytest.raises(InvalidStateTransition):
        await pricing_service.dispute_price(session, submission, mechanic, comment="rozi emasman")


async def test_admin_submission_is_auto_approved(session):
    """R1a / N8 — admin hisoboti kelishuvga umuman kirmaydi."""
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    vehicle = await make_vehicle(session, plate="01B456CD")
    submission = await create_ready_submission(
        session, admin, vehicle, works=[("Diagnostika", Decimal("120000"))]
    )

    await submission_service.submit(session, submission, admin)

    assert submission.status == SubmissionStatus.APPROVED
    assert submission.auto_approved is True
    assert submission.labor_amount == submission.proposed_labor_amount == Decimal("120000.00")

    approvals = [a for a in await _approvals(session, submission.id)]
    assert len(approvals) == 1
    assert approvals[0].decision == ApprovalDecision.auto_approved
    assert approvals[0].actor_id is None  # tizim tasdiqladi


async def _approvals(session, submission_id):
    import sqlalchemy as sa

    from app.db.models import Approval

    return list(
        (
            await session.execute(
                sa.select(Approval).where(Approval.submission_id == submission_id)
            )
        )
        .scalars()
        .all()
    )


async def test_price_context_hidden_from_reporter(session):
    """R3 / N9 — tayanch narx va tarix `reporter`ga API'da ham berilmaydi."""
    mechanic, admin, submission = await _submitted(session)

    with pytest.raises(PriceReferenceHidden):
        await pricing_service.price_context(session, submission, mechanic)

    contexts = await pricing_service.price_context(session, submission, admin)
    assert len(contexts) == 1
    assert contexts[0].proposed_amount == Decimal("250000.00")


async def test_price_context_uses_history(session):
    """Admin ekranidagi «oxirgi N marta o'rtacha» statistikasi."""
    mechanic, admin, first = await _submitted(session, price=Decimal("200000"))
    line = first.lines[0]
    await pricing_service.propose_price(
        session, first, admin, changes=[(line.id, Decimal("150000"))], comment="tarixga ko'ra"
    )
    await pricing_service.accept_price(session, first, mechanic)

    vehicle2 = await make_vehicle(session, plate="01C789DE")
    second = await create_ready_submission(
        session, mechanic, vehicle2, works=[("Old tormoz kolodkasi", Decimal("250000"))]
    )
    await submission_service.submit(session, second, mechanic)

    contexts = await pricing_service.price_context(session, second, admin)
    assert contexts[0].count == 1
    assert contexts[0].avg_approved == Decimal("150000.00")
    assert contexts[0].quick_amounts  # tez tanlov tugmalari bor


async def test_employee_price_stats(session):
    mechanic, admin, submission = await _submitted(session)
    line = submission.lines[0]
    await pricing_service.propose_price(
        session, submission, admin, changes=[(line.id, Decimal("200000"))], comment="tarixga ko'ra"
    )
    await pricing_service.accept_price(session, submission, mechanic)

    stats = await pricing_service.employee_price_stats(session, mechanic.id)
    assert stats.lines_total == 1
    assert stats.lines_reduced == 1
    assert stats.reduction_total == Decimal("50000.00")
    assert stats.avg_reduction_pct == Decimal("20.00")
    assert stats.reduction_rate_pct == Decimal("100.00")


async def test_partial_multiline_reduction_reports_full_total(session):
    """⭐ Admin bir nechta xizmatdan faqat bittasini kamaytirsa — jami to'g'ri.

    Tegilmagan qatorda `approved_amount = None` bo'lib qoladi; u nol deb
    sanalsa, ustaga «Admin taklifi» haqiqatdan kam ko'rinardi.
    """
    mechanic = await make_employee(session, role_code="mechanic", name="Karimov B.")
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(
        session,
        mechanic,
        vehicle,
        works=[("Balon almashtirish", Decimal("150000")), ("Kolodka", Decimal("100000"))],
    )
    await submission_service.submit(session, submission, mechanic)
    first = submission.lines[0]

    await pricing_service.propose_price(
        session,
        submission,
        admin,
        changes=[(first.id, Decimal("120000"))],  # faqat bittasi
        comment="Bu ish odatda arzonroq",
    )

    from app.db.models import LineKind
    from app.domain.template import engine

    lines = list(submission.lines)
    assert engine.sum_lines(lines, LineKind.labor) == Decimal("250000.00")
    # 120 000 (kamaytirilgan) + 100 000 (tegilmagan, o'z narxida)
    assert engine.effective_sum(lines, LineKind.labor) == Decimal("220000.00")

    # usta rozi bo'lgach yakuniy summa ham shu
    await pricing_service.accept_price(session, submission, mechanic)
    assert submission.labor_amount == Decimal("220000.00")
