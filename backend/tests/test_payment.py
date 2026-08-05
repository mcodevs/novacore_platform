"""⭐ Qarz daftari testlari — P1…P6, FIFO, qisman to'lov, `void` (ADR-0015/0016)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.errors import (
    PaymentAlreadyVoided,
    SubmissionNotPayable,
    ValidationFailed,
)
from app.db.models import LineKind, SubmissionStatus
from app.domain.approval import service as approval_service
from app.domain.payment import service as payment_service
from app.domain.submission import service as submission_service
from tests.conftest import add_photo, create_ready_submission, make_employee, make_vehicle


_plate_seq = 0


async def _next_vehicle(session):
    """Har hisobotga alohida mashina — `plate_number` unique."""
    global _plate_seq
    _plate_seq += 1
    return await make_vehicle(session, plate=f"01A{_plate_seq:03d}BC")


async def _approved(session, mechanic, admin, *, price=Decimal("250000"), vehicle=None):
    """Tasdiqlangan hisobot — ya'ni muallifga qarz."""
    vehicle = vehicle or await _next_vehicle(session)
    submission = await create_ready_submission(
        session, mechanic, vehicle, works=[("Tormoz kolodkasi", price)]
    )
    await submission_service.submit(session, submission, mechanic)
    await approval_service.approve(session, submission, admin)
    await session.refresh(submission)
    return submission


async def _team(session):
    mechanic = await make_employee(session, role_code="mechanic", name="Karimov B.")
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    return mechanic, admin


# --- R5/P3: qarz asosi --------------------------------------------------------


async def test_payable_equals_approved_labor(session):
    """R5 — qarz asosi tasdiqlangan ish haqi (usta so'ragan emas)."""
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin, price=Decimal("250000"))

    assert submission.payable_amount == Decimal("250000.00")
    assert submission.paid_amount == Decimal("0.00")
    assert submission.debt == Decimal("250000.00")


async def test_company_part_has_no_price_and_no_debt(session):
    """ADR-0016/P6 — kompaniya olgan qism **narxsiz** qayd etiladi va qarzga kirmaydi."""
    mechanic, admin = await _team(session)
    vehicle = await _next_vehicle(session)
    submission = await create_ready_submission(
        session, mechanic, vehicle, works=[("Ish haqi", Decimal("200000"))]
    )
    line = await submission_service.add_line(
        session,
        submission,
        mechanic,
        kind=LineKind.part,
        name="Tormoz kolodka (kompaniya oldi)",
        qty=1,
        unit_price=None,  # narx kiritilmaydi — belgi ham qo'yilmagan
    )
    assert line.proposed_amount == Decimal("0.00")
    assert line.self_funded is False

    await submission_service.submit(session, submission, mechanic)
    await approval_service.approve(session, submission, admin)
    await session.refresh(submission)

    # faqat ish haqi qarzga kiradi
    assert submission.payable_amount == Decimal("200000.00")


async def test_price_on_part_implies_self_funded(session):
    """⭐ «Narx bor = qarz bor» — narx kiritilsa belgi avtomatik qo'yiladi.

    Ta'minotchining xaridi ham shu qoida bilan qarzga aylanadi.
    """
    mechanic, _admin = await _team(session)
    vehicle = await _next_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    line = await submission_service.add_line(
        session,
        submission,
        mechanic,
        kind=LineKind.part,
        name="Kolodka",
        qty=1,
        unit_price=Decimal("180000"),
    )

    assert line.self_funded is True
    assert line.proposed_amount == Decimal("180000.00")


async def test_self_funded_part_adds_to_debt(session):
    """ADR-0016 — usta o'z puliga olgan qism qarzga qo'shiladi."""
    mechanic, admin = await _team(session)
    vehicle = await _next_vehicle(session)
    submission = await create_ready_submission(
        session, mechanic, vehicle, works=[("Ish haqi", Decimal("200000"))]
    )
    await submission_service.add_line(
        session,
        submission,
        mechanic,
        kind=LineKind.part,
        name="Kolodka (o'z hisobimdan)",
        qty=1,
        unit_price=Decimal("400000"),
        self_funded=True,
    )
    await add_photo(session, submission, mechanic, "photo_receipt")  # chek — ixtiyoriy
    await submission_service.submit(session, submission, mechanic)
    await approval_service.approve(session, submission, admin)
    await session.refresh(submission)

    assert submission.payable_amount == Decimal("600000.00")


async def test_self_funded_part_without_receipt_is_allowed(session):
    """⭐ ADR-0021 — chek fotosi MAJBURIY EMAS: usta doim chek ola bilmaydi.

    Ilgari (F5a) chekcsiz hisobot umuman yuborilmasdi va usta butun ishini
    yubora olmay qolardi. Endi chek — kutiladigan dalil, to'siq esa admin
    ko'rigi. Qarz baribir hisoblanadi (R5).
    """
    mechanic, admin = await _team(session)
    vehicle = await _next_vehicle(session)
    submission = await create_ready_submission(
        session, mechanic, vehicle, works=[("Ish haqi", Decimal("200000"))]
    )
    await submission_service.add_line(
        session,
        submission,
        mechanic,
        kind=LineKind.part,
        name="Kolodka (o'z hisobimdan)",
        qty=1,
        unit_price=Decimal("400000"),
        self_funded=True,
    )

    await submission_service.submit(session, submission, mechanic)  # cheksiz — xato yo'q
    assert submission.status == SubmissionStatus.SUBMITTED

    await approval_service.approve(session, submission, admin)
    await session.refresh(submission)
    assert submission.payable_amount == Decimal("600000.00")


async def test_company_part_needs_no_receipt(session):
    """Kompaniya olgan qism (narxsiz) uchun chek talab qilinmaydi."""
    mechanic, _admin = await _team(session)
    vehicle = await _next_vehicle(session)
    submission = await create_ready_submission(
        session, mechanic, vehicle, works=[("Ish haqi", Decimal("200000"))]
    )
    await submission_service.add_line(
        session,
        submission,
        mechanic,
        kind=LineKind.part,
        name="Kolodka (kompaniya oldi)",
        qty=1,
        unit_price=None,
    )

    await submission_service.submit(session, submission, mechanic)  # xato bo'lmasligi kerak
    assert submission.status == SubmissionStatus.SUBMITTED


# --- P1: faqat APPROVED to'lanadi --------------------------------------------


async def test_unapproved_submission_is_not_payable(session):
    """P1 — tasdiqlanmagan hisobotga to'lov qilib bo'lmaydi."""
    mechanic, admin = await _team(session)
    vehicle = await _next_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, submission, mechanic)

    with pytest.raises(SubmissionNotPayable):
        await payment_service.create_payment(
            session,
            employee_id=mechanic.id,
            actor_id=admin.id,
            submission_ids=[submission.id],
        )


# --- 1-rejim: chekbox ---------------------------------------------------------


async def test_checkbox_mode_pays_selected_in_full(session):
    mechanic, admin = await _team(session)
    first = await _approved(session, mechanic, admin, price=Decimal("100000"))
    second = await _approved(session, mechanic, admin, price=Decimal("300000"))

    payment = await payment_service.create_payment(
        session,
        employee_id=mechanic.id,
        actor_id=admin.id,
        submission_ids=[first.id],
    )

    assert payment.amount == Decimal("100000.00")
    assert len(payment.allocations) == 1
    await session.refresh(first)
    await session.refresh(second)
    assert first.status == SubmissionStatus.PAID
    assert first.debt == Decimal("0.00")
    # ikkinchisiga tegilmaydi
    assert second.status == SubmissionStatus.APPROVED
    assert second.debt == Decimal("300000.00")


# --- 2-rejim: FIFO ------------------------------------------------------------


async def test_fifo_allocates_oldest_first_and_splits_last(session):
    """⭐ Summa kiritildi → eng eskidan taqsimlanadi, oxirgisi qisman yopiladi."""
    mechanic, admin = await _team(session)
    first = await _approved(session, mechanic, admin, price=Decimal("450000"))
    second = await _approved(session, mechanic, admin, price=Decimal("890000"))
    third = await _approved(session, mechanic, admin, price=Decimal("320000"))

    payment = await payment_service.create_payment(
        session,
        employee_id=mechanic.id,
        actor_id=admin.id,
        amount=Decimal("1500000"),
    )

    # P4 — daftar balansi
    assert sum(a.amount for a in payment.allocations) == payment.amount

    await session.refresh(first)
    await session.refresh(second)
    await session.refresh(third)

    assert first.status == SubmissionStatus.PAID
    assert second.status == SubmissionStatus.PAID
    # 1 500 000 − 450 000 − 890 000 = 160 000 → uchinchisiga qisman
    assert third.paid_amount == Decimal("160000.00")
    assert third.debt == Decimal("160000.00")
    assert third.status == SubmissionStatus.APPROVED  # hali qarz


# --- Qisman to'lov -------------------------------------------------------------


async def test_partial_then_rest_closes_debt(session):
    """Qisman → qoldiq → to'liq yopiladi."""
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin, price=Decimal("500000"))

    await payment_service.create_payment(
        session,
        employee_id=mechanic.id,
        actor_id=admin.id,
        submission_ids=[submission.id],
        amount=Decimal("200000"),
    )
    await session.refresh(submission)
    assert submission.debt == Decimal("300000.00")
    assert submission.status == SubmissionStatus.APPROVED

    await payment_service.create_payment(
        session,
        employee_id=mechanic.id,
        actor_id=admin.id,
        amount=Decimal("300000"),
    )
    await session.refresh(submission)
    assert submission.debt == Decimal("0.00")
    assert submission.status == SubmissionStatus.PAID


# --- P7: avans -----------------------------------------------------------------


async def test_overpayment_becomes_advance(session):
    """⭐ P7 — qarzdan ortiq to'lov rad etilmaydi, ortiqcha summa avans bo'ladi."""
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin, price=Decimal("100000"))

    payment = await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, amount=Decimal("150000")
    )

    await session.refresh(submission)
    assert submission.status == SubmissionStatus.PAID
    assert submission.paid_amount == Decimal("100000.00")  # P2 buzilmadi
    assert payment.amount == Decimal("150000.00")
    assert await payment_service.advance_of(session, mechanic.id) == Decimal("50000.00")


async def test_payment_without_any_debt_is_pure_advance(session):
    """Qarzi yo'q xodimga to'lov — sof avans."""
    mechanic, admin = await _team(session)

    await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, amount=Decimal("300000")
    )

    assert await payment_service.advance_of(session, mechanic.id) == Decimal("300000.00")
    assert (await payment_service.debt_summary(session)).total == Decimal("0.00")


async def test_advance_auto_applies_to_new_debt(session):
    """⭐ Avans yangi qarz paydo bo'lishi bilan avtomatik ishlatiladi."""
    mechanic, admin = await _team(session)
    await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, amount=Decimal("300000")
    )

    # yangi ish tasdiqlandi — avans undan ushlab qolinadi
    submission = await _approved(session, mechanic, admin, price=Decimal("250000"))
    await session.refresh(submission)

    assert submission.status == SubmissionStatus.PAID
    assert submission.debt == Decimal("0.00")
    assert await payment_service.advance_of(session, mechanic.id) == Decimal("50000.00")


async def test_advance_partially_covers_bigger_debt(session):
    """Avans qarzdan kichik bo'lsa — qisman yopadi, qolgani qarz bo'lib qoladi."""
    mechanic, admin = await _team(session)
    await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, amount=Decimal("100000")
    )

    submission = await _approved(session, mechanic, admin, price=Decimal("250000"))
    await session.refresh(submission)

    assert submission.paid_amount == Decimal("100000.00")
    assert submission.debt == Decimal("150000.00")
    assert submission.status == SubmissionStatus.APPROVED
    assert await payment_service.advance_of(session, mechanic.id) == Decimal("0.00")


async def test_void_returns_advance_too(session):
    """To'lov bekor qilinsa avans ham izsiz qaytadi."""
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin, price=Decimal("100000"))
    payment = await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, amount=Decimal("150000")
    )
    assert await payment_service.advance_of(session, mechanic.id) == Decimal("50000.00")

    await payment_service.void_payment(
        session, payment, actor_id=admin.id, reason="Xato summa"
    )
    await session.refresh(submission)

    assert await payment_service.advance_of(session, mechanic.id) == Decimal("0.00")
    assert submission.debt == Decimal("100000.00")
    assert submission.status == SubmissionStatus.APPROVED


async def test_debt_summary_shows_advance(session):
    """Avansi bor xodim qarzi bo'lmasa ham ro'yxatda ko'rinadi."""
    mechanic, admin = await _team(session)
    await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, amount=Decimal("200000")
    )

    summary = await payment_service.debt_summary(session)

    assert summary.advance_total == Decimal("200000.00")
    row = next(e for e in summary.employees if e.employee_id == mechanic.id)
    assert row.advance == Decimal("200000.00")
    assert row.debt == Decimal("0.00")


# --- P5: void ------------------------------------------------------------------


async def test_void_reopens_debt(session):
    """P5 — to'lov bekor qilinsa qarz qayta ochiladi, status qaytadi."""
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin, price=Decimal("250000"))

    payment = await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, submission_ids=[submission.id]
    )
    await session.refresh(submission)
    assert submission.status == SubmissionStatus.PAID

    await payment_service.void_payment(
        session, payment, actor_id=admin.id, reason="Xato kiritildi"
    )
    await session.refresh(submission)

    assert payment.is_voided
    assert submission.paid_amount == Decimal("0.00")
    assert submission.debt == Decimal("250000.00")
    assert submission.status == SubmissionStatus.APPROVED


async def test_void_requires_reason(session):
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin)
    payment = await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, submission_ids=[submission.id]
    )

    with pytest.raises(ValidationFailed):
        await payment_service.void_payment(session, payment, actor_id=admin.id, reason="  ")


async def test_double_void_is_rejected(session):
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin)
    payment = await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, submission_ids=[submission.id]
    )
    await payment_service.void_payment(session, payment, actor_id=admin.id, reason="Xato")

    with pytest.raises(PaymentAlreadyVoided):
        await payment_service.void_payment(session, payment, actor_id=admin.id, reason="Yana")


# --- Qarzdorlar ro'yxati -------------------------------------------------------


async def test_debt_summary_groups_by_employee(session):
    mechanic, admin = await _team(session)
    other = await make_employee(session, role_code="mechanic", name="Sobirov A.")
    await _approved(session, mechanic, admin, price=Decimal("100000"))
    await _approved(session, mechanic, admin, price=Decimal("200000"))
    await _approved(session, other, admin, price=Decimal("50000"))

    summary = await payment_service.debt_summary(session)

    assert summary.total == Decimal("350000.00")
    by_id = {row.employee_id: row for row in summary.employees}
    assert by_id[mechanic.id].debt == Decimal("300000.00")
    assert by_id[mechanic.id].count == 2
    assert by_id[other.id].debt == Decimal("50000.00")


async def test_paid_submission_leaves_debt_list(session):
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin, price=Decimal("100000"))

    await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, submission_ids=[submission.id]
    )
    debts = await payment_service.employee_debts(session, mechanic.id)

    assert debts == []
    assert (await payment_service.debt_summary(session)).total == Decimal("0.00")


# --- F9/N7: to'langan hisobot qulflanadi ---------------------------------------


async def test_paid_submission_cannot_be_reopened(session):
    """F9 — to'lov qayd etilgan hisobot qaytarilmaydi."""
    mechanic, admin = await _team(session)
    submission = await _approved(session, mechanic, admin, price=Decimal("250000"))
    await payment_service.create_payment(
        session, employee_id=mechanic.id, actor_id=admin.id, submission_ids=[submission.id]
    )

    with pytest.raises(SubmissionNotPayable):
        await approval_service.reopen(
            session, submission, admin, comment="Ma'lumot yetishmaydi"
        )


async def test_payment_for_other_employee_is_rejected(session):
    """Boshqa xodimning hisobotini bu xodimga to'lab bo'lmaydi."""
    mechanic, admin = await _team(session)
    other = await make_employee(session, role_code="mechanic", name="Sobirov A.")
    submission = await _approved(session, mechanic, admin)

    with pytest.raises(ValidationFailed):
        await payment_service.create_payment(
            session,
            employee_id=other.id,
            actor_id=admin.id,
            submission_ids=[submission.id],
        )
