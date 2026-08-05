"""Qarz daftari — hisobot bo'yicha to'lov (ADR-0015).

⚠️ Platforma pul o'tkazmaydi — faqat qayd etadi.

Invariantlar:
    P1  to'lov faqat `APPROVED` hisobotga
    P2  `paid_amount ≤ payable_amount` — bitta hisobot qarzidan ortiq yopilmaydi
    P3  `payable_amount` serverda `submission_lines`dan hisoblanadi (engine)
    P4  `sum(allocations.amount) ≤ payment.amount`; qoldiq — avans
    P5  to'lov o'zgarmas; xato → `void` (sabab majburiy)
    P7  qarzdan ortiq to'lov **avans** bo'lib xodim hisobida turadi va yangi
        qarz paydo bo'lishi bilan avtomatik ishlatiladi
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    NotFound,
    PaymentAlreadyVoided,
    SubmissionNotPayable,
    ValidationFailed,
)
from app.db.base import ZERO, money, utcnow
from app.db.models import (
    Employee,
    Payment,
    PaymentAllocation,
    Submission,
    SubmissionStatus,
)
from app.domain import audit

#: Qarz ro'yxatiga tushadigan holatlar (P1). `PAID` — to'liq yopilgani.
PAYABLE = (SubmissionStatus.APPROVED, SubmissionStatus.PAID)


@dataclass
class EmployeeDebt:
    employee_id: int
    full_name: str
    debt: Decimal = ZERO
    count: int = 0
    #: Ishlatilmagan avans — qarzdan ortiq to'langan pul (P7)
    advance: Decimal = ZERO


@dataclass
class DebtSummary:
    total: Decimal = ZERO
    #: Barcha xodimlardagi ishlatilmagan avans yig'indisi
    advance_total: Decimal = ZERO
    employees: list[EmployeeDebt] = field(default_factory=list)


# --- O'qish -------------------------------------------------------------------


def _debt_expr() -> sa.ColumnElement[Decimal]:
    return Submission.payable_amount - Submission.paid_amount


def _open_debt_where() -> list[sa.ColumnElement[bool]]:
    """Qarzi ochiq hisobotlar: tasdiqlangan, o'chirilmagan, to'liq to'lanmagan."""
    return [
        Submission.deleted_at.is_(None),
        Submission.status.in_(PAYABLE),
        Submission.payable_amount > Submission.paid_amount,
    ]


async def debt_summary(session: AsyncSession) -> DebtSummary:
    """Qarzdorlar ro'yxati — buxgalter ekranining birinchi qatlami."""
    stmt = (
        sa.select(
            Submission.author_id,
            Employee.full_name,
            sa.func.sum(_debt_expr()).label("debt"),
            sa.func.count(Submission.id).label("cnt"),
        )
        .join(Employee, Employee.id == Submission.author_id)
        .where(*_open_debt_where())
        .group_by(Submission.author_id, Employee.full_name)
        .order_by(sa.desc("debt"))
    )
    rows = (await session.execute(stmt)).all()
    result = DebtSummary()
    seen: set[int] = set()
    for author_id, full_name, debt, cnt in rows:
        seen.add(author_id)
        result.employees.append(
            EmployeeDebt(
                employee_id=author_id, full_name=full_name, debt=money(debt), count=int(cnt)
            )
        )
        result.total = money(result.total + debt)

    # Avansi bor xodimlar ham ko'rinadi — qarzi bo'lmasa ham (P7)
    for row in await _employees_with_advance(session):
        advance = await advance_of(session, row.id)
        if advance <= ZERO:
            continue
        result.advance_total = money(result.advance_total + advance)
        existing = next((e for e in result.employees if e.employee_id == row.id), None)
        if existing is not None:
            existing.advance = advance
        elif row.id not in seen:
            result.employees.append(
                EmployeeDebt(employee_id=row.id, full_name=row.full_name, advance=advance)
            )
    return result


async def _employees_with_advance(session: AsyncSession) -> list[Employee]:
    """To'lov olgan xodimlar — avans qoldig'i shular orasidan qidiriladi."""
    stmt = (
        sa.select(Employee)
        .join(Payment, Payment.employee_id == Employee.id)
        .where(Payment.voided_at.is_(None))
        .distinct()
    )
    return list((await session.execute(stmt)).scalars().all())


@dataclass
class EmployeeBalance:
    """Bitta xodimning pul holati — o'zi ko'radigan ikki raqam.

    ⚠️ Serverda hisoblanadi (R7). Klient buni `listSubmissions` dan yig'a
    olmaydi: ro'yxat sahifalangan (20 ta) va avans umuman hisobotlarda emas.
    """

    debt: Decimal = ZERO
    count: int = 0
    advance: Decimal = ZERO


async def balance_of(session: AsyncSession, employee_id: int) -> EmployeeBalance:
    """Xodimdan qancha qarzdormiz va uning hisobida qancha avans bor."""
    debt, count = (
        await session.execute(
            sa.select(
                sa.func.coalesce(sa.func.sum(_debt_expr()), 0),
                sa.func.count(Submission.id),
            ).where(*_open_debt_where(), Submission.author_id == employee_id)
        )
    ).one()
    return EmployeeBalance(
        debt=money(debt),
        count=int(count or 0),
        advance=await advance_of(session, employee_id),
    )


async def employee_debts(session: AsyncSession, employee_id: int) -> list[Submission]:
    """Xodimning to'lanmagan hisobotlari — **eng eskisidan** (FIFO tartibi)."""
    stmt = (
        sa.select(Submission)
        .where(*_open_debt_where(), Submission.author_id == employee_id)
        .order_by(Submission.submitted_at.asc(), Submission.id.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def total_debt(session: AsyncSession, employee_id: int) -> Decimal:
    stmt = sa.select(sa.func.coalesce(sa.func.sum(_debt_expr()), 0)).where(
        *_open_debt_where(), Submission.author_id == employee_id
    )
    return money((await session.execute(stmt)).scalar_one())


# --- To'lov -------------------------------------------------------------------


def _ensure_payable(submission: Submission) -> None:
    """P1 — faqat tasdiqlangan hisobot to'lanadi."""
    if submission.deleted_at is not None or submission.status not in PAYABLE:
        raise SubmissionNotPayable(
            f"#{submission.number}: faqat tasdiqlangan hisobot to'lanadi"
        )


def ensure_not_paid(submission: Submission) -> None:
    """F9/N7 — to'lov qayd etilgan hisobot qaytarilmaydi va narxi o'zgarmaydi.

    Aks holda to'langan summa `payable_amount` dan oshib ketardi (P2).
    """
    if submission.paid_amount > ZERO:
        raise SubmissionNotPayable(
            f"#{submission.number} bo'yicha to'lov qayd etilgan — avval to'lovni bekor qiling"
        )


def _allocate(
    targets: list[Submission], amount: Decimal
) -> tuple[list[tuple[Submission, Decimal]], Decimal]:
    """FIFO taqsimot: eng eski qarzdan boshlab, oxirgisi qisman yopilishi mumkin.

    Qaytaradi: `(taqsimot, qoldiq)`. **Qoldiq — avans** (P7): u hech qaysi
    hisobotga biriktirilmaydi va xodim hisobida turadi.
    """
    allocations: list[tuple[Submission, Decimal]] = []
    left = amount
    for submission in targets:
        if left <= ZERO:
            break
        debt = submission.payable_amount - submission.paid_amount
        if debt <= ZERO:
            continue
        take = debt if debt <= left else left
        allocations.append((submission, money(take)))
        left = money(left - take)
    return allocations, left


async def create_payment(
    session: AsyncSession,
    *,
    employee_id: int,
    actor_id: int,
    submission_ids: list[int] | None = None,
    amount: Decimal | None = None,
    note: str | None = None,
) -> Payment:
    """To'lovni qayd etadi. Uch rejim bitta mexanizmga tushadi:

    1. `submission_ids` — belgilanganlarning qarzi **to'liq** yopiladi (chekbox)
    2. `amount` — **FIFO**: eng eski qarzdan boshlab taqsimlanadi
    3. `submission_ids` + `amount` — aynan shu hisobotlarga, qisman ham mumkin
    """
    if not submission_ids and amount is None:
        raise ValidationFailed("Hisobotlarni belgilang yoki summa kiriting")
    if amount is not None and amount <= ZERO:
        raise ValidationFailed("Summa noldan katta bo'lishi kerak")

    if submission_ids:
        rows = (
            await session.execute(
                sa.select(Submission)
                .where(Submission.id.in_(submission_ids))
                .order_by(Submission.submitted_at.asc(), Submission.id.asc())
            )
        ).scalars().all()
        found = {row.id for row in rows}
        missing = [sid for sid in submission_ids if sid not in found]
        if missing:
            raise NotFound(f"Hisobot topilmadi: {missing}")

        targets = list(rows)
        for submission in targets:
            _ensure_payable(submission)
            if submission.author_id != employee_id:
                raise ValidationFailed(
                    f"#{submission.number} boshqa xodimning hisoboti"
                )
    else:
        # Qarz bo'lmasa ham to'lov qilinadi — bu **sof avans** (P7)
        targets = await employee_debts(session, employee_id)

    if amount is None:
        # 1-rejim: belgilanganlarning qolgan qarzi to'liq
        total = ZERO
        for submission in targets:
            total = money(total + (submission.payable_amount - submission.paid_amount))
        if total <= ZERO:
            raise ValidationFailed("Belgilangan hisobotlar allaqachon to'langan")
        amount = total

    allocations, advance = _allocate(targets, money(amount))

    # ⚠️ `employee` va `allocations` obyekt qurilishida biriktiriladi. Aks holda
    # chaqiruvchi (API serializatori) ularga murojaat qilganda SQLAlchemy lazy
    # yuklashga urinadi va async kontekstdan tashqarida `MissingGreenlet` beradi.
    employee = await session.get(Employee, employee_id)
    if employee is None:
        raise NotFound(f"Xodim topilmadi: {employee_id}")

    payment = Payment(
        employee=employee,
        amount=money(amount),
        actor_id=actor_id,
        note=note,
        allocations=[
            PaymentAllocation(submission_id=submission.id, amount=part)
            for submission, part in allocations
        ],
    )
    session.add(payment)

    for submission, part in allocations:
        submission.paid_amount = money(submission.paid_amount + part)
        _sync_status(submission)

    await session.flush()

    await audit.log(
        session,
        action="payment.create",
        entity_type="payment",
        entity_id=payment.id,
        actor_id=actor_id,
        after={
            "employee_id": employee_id,
            "amount": str(payment.amount),
            "advance": str(advance),  # qarzdan ortgani — avans (P7)
            "allocations": [
                {"submission_id": s.id, "amount": str(a)} for s, a in allocations
            ],
        },
    )
    await session.flush()

    if advance > ZERO:
        # Belgilangan hisobotlardan ortgan pul boshqa ochiq qarzlarga tushsin;
        # qolgani xodim hisobida avans bo'lib turadi (P7).
        await apply_advance(session, employee_id)
    return payment


# --- Avans (P7) ----------------------------------------------------------------


async def advance_of(session: AsyncSession, employee_id: int) -> Decimal:
    """Xodim hisobidagi avans: to'langan, lekin hech qaysi hisobotga tushmagan pul.

    `Σ(bekor qilinmagan to'lovlar) − Σ(ularning allokatsiyalari)`.
    """
    paid = (
        await session.execute(
            sa.select(sa.func.coalesce(sa.func.sum(Payment.amount), 0)).where(
                Payment.employee_id == employee_id, Payment.voided_at.is_(None)
            )
        )
    ).scalar_one()
    allocated = (
        await session.execute(
            sa.select(sa.func.coalesce(sa.func.sum(PaymentAllocation.amount), 0))
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .where(Payment.employee_id == employee_id, Payment.voided_at.is_(None))
        )
    ).scalar_one()
    return money(max(ZERO, Decimal(paid) - Decimal(allocated)))


async def _advance_payments(session: AsyncSession, employee_id: int) -> list[Payment]:
    """Qoldig'i bor to'lovlar — eng eskisidan (avansni sarflash tartibi)."""
    return list(
        (
            await session.execute(
                sa.select(Payment)
                .where(Payment.employee_id == employee_id, Payment.voided_at.is_(None))
                .order_by(Payment.created_at.asc(), Payment.id.asc())
            )
        )
        .scalars()
        .all()
    )


def _remainder(payment: Payment) -> Decimal:
    used = ZERO
    for allocation in payment.allocations:
        used = money(used + allocation.amount)
    return money(payment.amount - used)


async def apply_advance(session: AsyncSession, employee_id: int) -> Decimal:
    """P7 — xodimda avans bo'lsa, uni ochiq qarzlarga **avtomatik** yopadi.

    Hisobot tasdiqlanganda va yangi to'lov qayd etilganda chaqiriladi: avans
    ishlatilmay turib qolmasligi kerak. Taqsimot FIFO — eng eski qarzdan.
    Yangi allokatsiya **o'sha to'lov yozuviga** biriktiriladi, shuning uchun
    to'lov `void` qilinsa avans ham izsiz qaytadi.
    """
    applied = ZERO
    debts = await employee_debts(session, employee_id)
    if not debts:
        return applied

    for payment in await _advance_payments(session, employee_id):
        left = _remainder(payment)
        if left <= ZERO:
            continue
        for submission in debts:
            if left <= ZERO:
                break
            debt = submission.payable_amount - submission.paid_amount
            if debt <= ZERO:
                continue
            take = money(debt if debt <= left else left)
            payment.allocations.append(
                PaymentAllocation(submission_id=submission.id, amount=take)
            )
            submission.paid_amount = money(submission.paid_amount + take)
            _sync_status(submission)
            left = money(left - take)
            applied = money(applied + take)

    if applied > ZERO:
        await session.flush()
    return applied


async def void_payment(
    session: AsyncSession, payment: Payment, *, actor_id: int, reason: str
) -> Payment:
    """P5 — to'lov tahrirlanmaydi, faqat bekor qilinadi. Qarz qayta ochiladi."""
    if payment.is_voided:
        raise PaymentAlreadyVoided("Bu to'lov allaqachon bekor qilingan")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationFailed("Bekor qilish sababi majburiy")

    payment.voided_at = utcnow()
    payment.voided_by = actor_id
    payment.void_reason = reason

    for allocation in payment.allocations:
        submission = await session.get(Submission, allocation.submission_id)
        if submission is None:
            continue
        submission.paid_amount = money(
            max(ZERO, submission.paid_amount - allocation.amount)
        )
        _sync_status(submission)

    await audit.log(
        session,
        action="payment.void",
        entity_type="payment",
        entity_id=payment.id,
        actor_id=actor_id,
        before={"amount": str(payment.amount)},
        after={"void_reason": reason},
    )
    await session.flush()
    return payment


def _sync_status(submission: Submission) -> None:
    """`PAID` — qarz to'liq yopilganda; `void` bo'lsa `APPROVED`ga qaytadi."""
    if submission.payable_amount > ZERO and submission.paid_amount >= submission.payable_amount:
        submission.status = SubmissionStatus.PAID
    elif submission.status == SubmissionStatus.PAID:
        submission.status = SubmissionStatus.APPROVED


async def recalc_paid(session: AsyncSession, submission: Submission) -> None:
    """`paid_amount` ni bekor qilinmagan allokatsiyalardan qayta hisoblaydi."""
    stmt = (
        sa.select(sa.func.coalesce(sa.func.sum(PaymentAllocation.amount), 0))
        .join(Payment, Payment.id == PaymentAllocation.payment_id)
        .where(
            PaymentAllocation.submission_id == submission.id,
            Payment.voided_at.is_(None),
        )
    )
    submission.paid_amount = money((await session.execute(stmt)).scalar_one())
    _sync_status(submission)


async def payments_of(
    session: AsyncSession,
    *,
    employee_id: int | None = None,
    limit: int = 100,
) -> list[Payment]:
    stmt = sa.select(Payment).order_by(Payment.created_at.desc()).limit(limit)
    if employee_id is not None:
        stmt = stmt.where(Payment.employee_id == employee_id)
    return list((await session.execute(stmt)).scalars().all())
