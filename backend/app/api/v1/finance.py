"""Davr, to'lov varaqalari, hisobotlar va eksport."""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import AdminDep, EmployeeDep, FinanceDep, SessionDep
from app.api.v1 import schemas
from app.core.errors import BusinessRuleViolated, NotFound
from app.db.models import (
    Payout,
    Period,
    Submission,
    SubmissionStatus,
    Vehicle,
    VehicleStatus,
)
from app.domain.export import service as export_service
from app.domain.payout import service as payout_service
from app.domain.period import service as period_service

router = APIRouter(tags=["finance"])


def _period_out(period: Period) -> schemas.PeriodOut:
    return schemas.PeriodOut(
        id=period.id,
        year=period.year,
        month=period.month,
        status=period.status.value,
        closed_at=period.closed_at,
    )


@router.get("/periods", response_model=list[schemas.PeriodOut])
async def list_periods(session: SessionDep, employee: EmployeeDep):
    rows = (
        await session.execute(
            sa.select(Period).order_by(Period.year.desc(), Period.month.desc()).limit(24)
        )
    ).scalars().all()
    return [_period_out(row) for row in rows]


@router.get("/periods/current", response_model=schemas.PeriodOut)
async def current_period(session: SessionDep, employee: EmployeeDep):
    return _period_out(await period_service.current_period(session))


@router.get("/periods/{period_id}/precheck", response_model=schemas.PrecheckOut)
async def precheck(period_id: int, session: SessionDep, employee: FinanceDep):
    period = await session.get(Period, period_id)
    if period is None:
        raise NotFound("Davr topilmadi")
    result = await period_service.precheck(session, period)
    return schemas.PrecheckOut(
        can_close=result.can_close,
        blockers=[{"code": code, **params} for code, params in result.blockers],
        warnings=[{"code": code, **params} for code, params in result.warnings],
    )


@router.post("/periods/{period_id}/close", response_model=schemas.PeriodOut)
async def close_period(period_id: int, session: SessionDep, employee: FinanceDep):
    period = await session.get(Period, period_id)
    if period is None:
        raise NotFound("Davr topilmadi")
    await period_service.close_period(session, period, employee.id)
    await payout_service.generate_for_period(session, period)
    return _period_out(period)


@router.post("/periods/{period_id}/reopen", response_model=schemas.PeriodOut)
async def reopen_period(
    period_id: int,
    payload: schemas.ReopenPeriodRequest,
    session: SessionDep,
    employee: AdminDep,
):
    period = await session.get(Period, period_id)
    if period is None:
        raise NotFound("Davr topilmadi")
    await period_service.reopen_period(session, period, employee.id, payload.reason)
    return _period_out(period)


# --- To'lov varaqalari ---------------------------------------------------------


def _payout_out(payout: Payout) -> schemas.PayoutOut:
    return schemas.PayoutOut(
        id=payout.id,
        employee_id=payout.employee_id,
        employee_name=payout.employee.full_name,
        submissions_count=payout.submissions_count,
        proposed_total=payout.proposed_total,
        labor_total=payout.labor_total,
        reduction_total=payout.reduction_total,
        bonus=payout.bonus,
        penalty=payout.penalty,
        total=payout.total,
        status=payout.status.value,
    )


@router.get("/payouts", response_model=list[schemas.PayoutOut])
async def list_payouts(session: SessionDep, employee: FinanceDep, period_id: int):
    rows = (
        await session.execute(sa.select(Payout).where(Payout.period_id == period_id))
    ).scalars().all()
    return [_payout_out(row) for row in rows]


@router.post("/payouts/{payout_id}/adjust", response_model=schemas.PayoutOut)
async def adjust_payout(
    payout_id: int,
    payload: schemas.AdjustPayoutRequest,
    session: SessionDep,
    employee: AdminDep,
):
    payout = await session.get(Payout, payout_id)
    if payout is None:
        raise NotFound("To'lov varaqasi topilmadi")
    await payout_service.adjust(
        session,
        payout,
        actor_id=employee.id,
        bonus=payload.bonus,
        penalty=payload.penalty,
        reason=payload.reason,
    )
    return _payout_out(payout)


@router.post("/payouts/{payout_id}/mark-paid", response_model=schemas.PayoutOut)
async def mark_paid(payout_id: int, session: SessionDep, employee: FinanceDep):
    payout = await session.get(Payout, payout_id)
    if payout is None:
        raise NotFound("To'lov varaqasi topilmadi")
    await payout_service.mark_paid(session, payout, actor_id=employee.id)
    return _payout_out(payout)


# --- Hisobotlar ----------------------------------------------------------------


@router.get("/reports/dashboard", response_model=schemas.DashboardOut)
async def dashboard(session: SessionDep, employee: FinanceDep, period_id: int | None = None):
    period = (
        await session.get(Period, period_id)
        if period_id
        else await period_service.current_period(session)
    )
    if period is None:
        raise NotFound("Davr topilmadi")
    summary = await payout_service.period_summary(session, period.id)

    pending = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.deleted_at.is_(None),
                Submission.status.in_(
                    [SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW]
                ),
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
        period=period.title,
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
    )


@router.get("/reports/negotiation-savings")
async def negotiation_savings(
    session: SessionDep, employee: FinanceDep, period_id: int | None = None
):
    """⭐ «Bu oy kelishuv X so'm tejadi» — platformaning o'zini oqlashi."""
    period = (
        await session.get(Period, period_id)
        if period_id
        else await period_service.current_period(session)
    )
    summary = await payout_service.period_summary(session, period.id)
    return {
        "data": {
            "period": period.title,
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
    kind: str = Query("submissions", pattern="^(submissions|payouts|savings)$"),
    period_id: int | None = None,
):
    period = (
        await session.get(Period, period_id)
        if period_id
        else await period_service.current_period(session)
    )
    if period is None:
        raise NotFound("Davr topilmadi")
    try:
        filename, payload = await export_service.build(session, kind, period)
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
    kind: str = Query("submissions", pattern="^(submissions|payouts|savings)$"),
    period_id: int | None = None,
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

    period = (
        await session.get(Period, period_id)
        if period_id
        else await period_service.current_period(session)
    )
    if period is None:
        raise NotFound("Davr topilmadi")
    try:
        filename, payload = await export_service.build(session, kind, period)
    except ValueError as exc:
        raise BusinessRuleViolated(str(exc)) from exc

    await get_bot().send_document(
        employee.tg_user_id,
        BufferedInputFile(payload, filename=filename),
        caption=f"📥 {filename}",
    )
    return {"data": {"ok": True, "filename": filename, "sent_to": "telegram"}}
