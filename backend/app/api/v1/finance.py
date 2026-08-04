"""Qarz daftari, to'lovlar, hisobotlar va eksport (ADR-0015).

⚠️ `/periods` va `/payouts` endpointlari **yo'q** — davr va to'lov varaqasi
tushunchalari olib tashlangan. Qarz hisobot darajasida yuritiladi.
"""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import EmployeeDep, FinanceDep, SessionDep
from app.api.v1 import schemas
from app.core.errors import BusinessRuleViolated, NotFound
from app.db.base import ZERO
from app.db.models import Payment, Submission, SubmissionStatus, Vehicle, VehicleStatus
from app.domain.export import service as export_service
from app.domain.payment import service as payment_service
from app.domain.stats import service as stats_service

router = APIRouter(tags=["finance"])


# --- Qarzlar -------------------------------------------------------------------


@router.get("/debts", response_model=schemas.DebtSummaryOut)
async def debts(session: SessionDep, employee: FinanceDep):
    """Qarzdorlar: umumiy summa + xodimlar kesimi (buxgalter ekranining boshi)."""
    summary = await payment_service.debt_summary(session)
    return schemas.DebtSummaryOut(
        total=summary.total,
        advance_total=summary.advance_total,
        employees=[
            schemas.EmployeeDebtOut(
                employee_id=row.employee_id,
                full_name=row.full_name,
                debt=row.debt,
                count=row.count,
                advance=row.advance,
            )
            for row in summary.employees
        ],
    )


@router.get("/debts/{employee_id}", response_model=list[schemas.DebtItemOut])
async def employee_debts(employee_id: int, session: SessionDep, employee: FinanceDep):
    """Xodimning to'lanmagan hisobotlari — **eng eskisidan** (FIFO tartibi)."""
    rows = await payment_service.employee_debts(session, employee_id)
    return [
        schemas.DebtItemOut(
            submission_id=row.id,
            number=row.number,
            vehicle=row.vehicle.plate_display if row.vehicle else None,
            submitted_at=row.submitted_at,
            payable_amount=row.payable_amount,
            paid_amount=row.paid_amount,
            debt=row.payable_amount - row.paid_amount,
        )
        for row in rows
    ]


# --- To'lovlar -----------------------------------------------------------------


def _payment_out(payment: Payment) -> schemas.PaymentOut:
    return schemas.PaymentOut(
        id=payment.id,
        employee_id=payment.employee_id,
        employee_name=payment.employee.full_name,
        amount=payment.amount,
        note=payment.note,
        created_at=payment.created_at,
        voided_at=payment.voided_at,
        void_reason=payment.void_reason,
        allocations=[
            schemas.AllocationOut(
                submission_id=item.submission_id,
                amount=item.amount,
                fully_paid=False,
            )
            for item in payment.allocations
        ],
    )


async def _fill_allocations(
    session: AsyncSession, payments: list[schemas.PaymentOut]
) -> None:
    """Allokatsiyalarga hisobot raqami va joriy `fully_paid` holatini qo'yadi.

    ⚠️ Bog'lanish orqali emas, **bitta so'rov** bilan: `PaymentAllocation` da
    `submission` relationship yo'q, uni async kontekstda lazy o'qish
    `MissingGreenlet` beradi. Ro'yxatda esa to'lov ko'p — N+1 bo'lardi.
    """
    ids = {item.submission_id for payment in payments for item in payment.allocations}
    if not ids:
        return
    rows = (
        await session.execute(sa.select(Submission).where(Submission.id.in_(ids)))
    ).scalars().all()
    found = {row.id: row for row in rows}
    for payment in payments:
        for item in payment.allocations:
            submission = found.get(item.submission_id)
            if submission is None:
                continue
            item.number = submission.number
            item.fully_paid = submission.status == SubmissionStatus.PAID


@router.post("/payments", response_model=schemas.PaymentOut)
async def create_payment(
    payload: schemas.CreatePaymentRequest, session: SessionDep, employee: FinanceDep
):
    """To'lovni qayd etadi — chekbox / FIFO / qisman (uchalasi bitta mexanizm)."""
    payment = await payment_service.create_payment(
        session,
        employee_id=payload.employee_id,
        actor_id=employee.id,
        submission_ids=payload.submission_ids,
        amount=payload.amount,
        note=payload.note,
    )
    out = _payment_out(payment)
    await _fill_allocations(session, [out])
    return out


@router.get("/payments", response_model=list[schemas.PaymentOut])
async def list_payments(
    session: SessionDep,
    employee: FinanceDep,
    employee_id: int | None = None,
    limit: int = Query(100, le=500),
):
    rows = await payment_service.payments_of(session, employee_id=employee_id, limit=limit)
    outs = [_payment_out(row) for row in rows]
    await _fill_allocations(session, outs)
    return outs


@router.post("/payments/{payment_id}/void", response_model=schemas.PaymentOut)
async def void_payment(
    payment_id: int,
    payload: schemas.VoidPaymentRequest,
    session: SessionDep,
    employee: FinanceDep,
):
    """P5 — to'lov tahrirlanmaydi, faqat bekor qilinadi. Qarz qayta ochiladi."""
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise NotFound("To'lov topilmadi")
    await payment_service.void_payment(
        session, payment, actor_id=employee.id, reason=payload.reason
    )
    return _payment_out(payment)


# --- Hisobotlar ----------------------------------------------------------------


def _resolve_range(
    frm: dt.datetime | None, to: dt.datetime | None
) -> tuple[dt.datetime | None, dt.datetime | None]:
    """Chegara berilmasa — joriy oy (eski «current period» xulqining o'rnini bosadi)."""
    if frm is None and to is None:
        return stats_service.current_month_range()
    return frm, to


@router.get("/reports/dashboard", response_model=schemas.DashboardOut)
async def dashboard(
    session: SessionDep,
    employee: FinanceDep,
    frm: dt.datetime | None = None,
    to: dt.datetime | None = None,
):
    frm, to = _resolve_range(frm, to)
    summary = await stats_service.range_summary(session, frm=frm, to=to)

    pending = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.deleted_at.is_(None),
                Submission.status.in_([SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW]),
            )
        )
    ).scalar_one()
    negotiating = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.deleted_at.is_(None),
                Submission.status.in_(
                    [SubmissionStatus.PRICE_NEGOTIATION, SubmissionStatus.PRICE_DISPUTED]
                ),
            )
        )
    ).scalar_one()
    in_service = (
        await session.execute(
            sa.select(sa.func.count(Vehicle.id)).where(
                Vehicle.status.in_([VehicleStatus.in_service, VehicleStatus.waiting_parts])
            )
        )
    ).scalar_one()

    return schemas.DashboardOut(
        period=summary.title,
        total_submissions=summary.total_submissions,
        approved_count=summary.approved_count,
        proposed_total=summary.proposed_total,
        approved_total=summary.approved_total,
        parts_total=summary.parts_total,
        saved=summary.saved,
        saved_pct=summary.saved_pct,
        auto_approved_count=summary.auto_approved_count,
        auto_approved_total=summary.auto_approved_total,
        pending_review=int(pending),
        in_negotiation=int(negotiating),
        vehicles_in_service=int(in_service),
        debt_total=summary.debt_total,
        paid_total=summary.paid_total,
    )


@router.get("/reports/negotiation-savings")
async def negotiation_savings(
    session: SessionDep,
    employee: FinanceDep,
    frm: dt.datetime | None = None,
    to: dt.datetime | None = None,
):
    """⭐ «Kelishuv X so'm tejadi» — platformaning o'zini oqlashi."""
    frm, to = _resolve_range(frm, to)
    summary = await stats_service.range_summary(session, frm=frm, to=to)
    return {
        "data": {
            "period": summary.title,
            "proposed_total": float(summary.proposed_total),
            "approved_total": float(summary.approved_total),
            "saved": float(summary.saved),
            "saved_pct": float(summary.saved_pct),
            "approved_count": summary.approved_count,
            "auto_approved_count": summary.auto_approved_count,
            "auto_approved_total": float(summary.auto_approved_total),
        }
    }


@router.get("/reports/export")
async def export(
    session: SessionDep,
    employee: FinanceDep,
    kind: str = Query("submissions", pattern="^(submissions|debts|savings)$"),
    frm: dt.datetime | None = None,
    to: dt.datetime | None = None,
):
    frm, to = _resolve_range(frm, to)
    try:
        filename, payload = await export_service.build(session, kind, frm=frm, to=to)
    except ValueError as exc:
        raise BusinessRuleViolated(str(exc)) from exc

    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/reports/export")
async def export_to_telegram(
    session: SessionDep,
    employee: FinanceDep,
    kind: str = Query("submissions", pattern="^(submissions|debts|savings)$"),
    frm: dt.datetime | None = None,
    to: dt.datetime | None = None,
):
    """Excel'ni **bot orqali** yuboradi (amal Mini App'da, yetkazish botda).

    Telegram WebView'da fayl yuklab olish, ayniqsa iOS'da, ishonchsiz — shuning
    uchun tugma Mini App'da bo'ladi, fayl esa suhbatga hujjat bo'lib tushadi.
    Bitta process bo'lgani uchun bot shu yerdan chaqiriladi (ADR-0004).
    """
    from aiogram.types import BufferedInputFile

    from app.bot.bot import get_bot

    if employee.tg_user_id is None:
        raise BusinessRuleViolated("Avval botda /start bosing")

    frm, to = _resolve_range(frm, to)
    try:
        filename, payload = await export_service.build(session, kind, frm=frm, to=to)
    except ValueError as exc:
        raise BusinessRuleViolated(str(exc)) from exc

    await get_bot().send_document(
        employee.tg_user_id,
        BufferedInputFile(payload, filename=filename),
        caption=f"📥 {filename}",
    )
    return {"data": {"ok": True, "filename": filename, "sent_to": "telegram"}}
