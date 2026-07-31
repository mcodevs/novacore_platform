"""Hisobotlar va narx kelishuvi endpointlari."""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Query

from app.api.deps import EmployeeDep, SessionDep
from app.api.v1 import schemas, serializers
from app.core.errors import NotFound, ValidationFailed
from app.db.models import (
    Approval,
    LineKind,
    Submission,
    SubmissionStatus,
    Template,
    Vehicle,
)
from app.domain.approval import service as approval_service
from app.domain.pricing import service as pricing_service
from app.domain.submission import service as submission_service
from app.domain.template import engine

router = APIRouter(tags=["submissions"])


@router.get("/submissions", response_model=list[schemas.SubmissionOut])
async def list_submissions(
    session: SessionDep,
    employee: EmployeeDep,
    status: str | None = None,
    author_id: str | None = None,
    period_id: int | None = None,
    vehicle_id: int | None = None,
    limit: int = Query(20, le=100),
):
    from app.domain.role import permissions

    stmt = sa.select(Submission).where(Submission.deleted_at.is_(None))
    if not permissions.can_see_all_submissions(employee):
        stmt = stmt.where(Submission.author_id == employee.id)
    elif author_id == "me":
        stmt = stmt.where(Submission.author_id == employee.id)
    elif author_id:
        stmt = stmt.where(Submission.author_id == int(author_id))
    if status:
        stmt = stmt.where(Submission.status == SubmissionStatus(status))
    if period_id:
        stmt = stmt.where(Submission.period_id == period_id)
    if vehicle_id:
        stmt = stmt.where(Submission.subject_vehicle_id == vehicle_id)

    rows = (
        await session.execute(stmt.order_by(Submission.created_at.desc()).limit(limit))
    ).scalars().all()
    return [serializers.submission_out(row) for row in rows]


@router.get("/submissions/linkable", response_model=list[schemas.LinkableSubmissionOut])
async def linkable_submissions(
    session: SessionDep,
    employee: EmployeeDep,
    template_code: str | None = None,
    vehicle_id: int | None = None,
    exclude_id: int | None = None,
    limit: int = Query(20, le=50),
):
    """`submission_picker` nomzodlari — qism xaridini ta'mirga bog'lash uchun."""
    rows = await submission_service.linkable(
        session,
        employee,
        template_code=template_code,
        vehicle_id=vehicle_id,
        exclude_id=exclude_id,
        limit=limit,
    )
    return [serializers.linkable_out(row) for row in rows]


@router.post("/submissions", response_model=schemas.SubmissionOut, status_code=201)
async def create_submission(
    payload: schemas.CreateSubmissionRequest, session: SessionDep, employee: EmployeeDep
):
    """⭐ `arrived_at` — server vaqti bilan yoziladi (R6)."""
    template = (
        await session.execute(sa.select(Template).where(Template.code == payload.template_code))
    ).scalar_one_or_none()
    if template is None:
        raise NotFound("Shablon topilmadi")
    submission = await submission_service.create_draft(
        session, employee, template, vehicle_id=payload.vehicle_id
    )
    return serializers.submission_out(submission)


@router.get("/submissions/{submission_id}", response_model=schemas.SubmissionOut)
async def get_submission(submission_id: int, session: SessionDep, employee: EmployeeDep):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    return serializers.submission_out(submission)


@router.patch("/submissions/{submission_id}", response_model=schemas.SubmissionOut)
async def patch_submission(
    submission_id: int,
    payload: schemas.PatchSubmissionRequest,
    session: SessionDep,
    employee: EmployeeDep,
):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    submission_service.ensure_editable(submission, employee)

    previous_vehicle_id = submission.subject_vehicle_id
    data = dict(submission.data or {})
    data.update(payload.data)
    submission.data = data
    schema = await engine.schema_for_submission(session, submission)
    engine.apply_field_mapping(schema, submission)

    # Mashina shu qadamda tanlanadi (Mini App `vehicle_id`siz qoralama ochadi) —
    # bot oqimidagi kabi mashina IN_SERVICE ga o'tishi kerak, aks holda u
    # ta'mirda turib "liniyada" ko'rinadi.
    if submission.subject_vehicle_id and submission.subject_vehicle_id != previous_vehicle_id:
        vehicle = await session.get(Vehicle, submission.subject_vehicle_id)
        if vehicle is not None:
            await submission_service.attach_vehicle(session, submission, vehicle)

    await session.flush()
    return serializers.submission_out(submission)


@router.put("/submissions/{submission_id}/lines", response_model=schemas.SubmissionOut)
async def replace_lines(
    submission_id: int,
    payload: schemas.LinesRequest,
    session: SessionDep,
    employee: EmployeeDep,
):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    submission_service.ensure_editable(submission, employee)

    for line in list(submission.lines):
        await session.delete(line)
    await session.flush()
    await session.refresh(submission)

    for item in payload.lines:
        await submission_service.add_line(
            session,
            submission,
            employee,
            kind=LineKind(item.kind),
            name=item.name,
            qty=item.qty,
            unit_price=item.unit_price,
            catalog_id=item.catalog_id,
            supplier_name=item.supplier_name,
        )
    await session.refresh(submission)
    return serializers.submission_out(submission)


@router.post("/submissions/{submission_id}/mark-left", response_model=schemas.SubmissionOut)
async def mark_left(submission_id: int, session: SessionDep, employee: EmployeeDep):
    """⭐ «Mashina ketdi» → `left_at` server vaqti (R6)."""
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    await submission_service.mark_left(session, submission, employee)
    return serializers.submission_out(submission)


@router.post("/submissions/{submission_id}/submit", response_model=schemas.SubmissionOut)
async def submit(submission_id: int, session: SessionDep, employee: EmployeeDep):
    """⭐ Muallif `admin` bo'lsa → darhol `APPROVED` (R1a)."""
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    try:
        await submission_service.submit(session, submission, employee)
    except ValidationFailed as exc:
        raise ValidationFailed(exc.message, fields=exc.fields) from exc
    return serializers.submission_out(submission)


@router.delete("/submissions/{submission_id}")
async def delete_draft(submission_id: int, session: SessionDep, employee: EmployeeDep):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    await submission_service.delete_draft(session, submission, employee)
    return {"data": {"ok": True}}


# --- Tasdiqlash ---------------------------------------------------------------


@router.post("/submissions/{submission_id}/approve", response_model=schemas.SubmissionOut)
async def approve(
    submission_id: int,
    payload: schemas.CommentRequest,
    session: SessionDep,
    employee: EmployeeDep,
):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    await approval_service.approve(session, submission, employee, comment=payload.comment)
    return serializers.submission_out(submission)


@router.post("/submissions/{submission_id}/reject", response_model=schemas.SubmissionOut)
async def reject(
    submission_id: int,
    payload: schemas.CommentRequest,
    session: SessionDep,
    employee: EmployeeDep,
):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    await approval_service.reject(session, submission, employee, comment=payload.comment or "")
    return serializers.submission_out(submission)


@router.post("/submissions/{submission_id}/reopen", response_model=schemas.SubmissionOut)
async def reopen(
    submission_id: int,
    payload: schemas.CommentRequest,
    session: SessionDep,
    employee: EmployeeDep,
):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    await approval_service.reopen(session, submission, employee, comment=payload.comment or "")
    return serializers.submission_out(submission)


# --- ⭐ Narx kelishuvi ---------------------------------------------------------


@router.get(
    "/submissions/{submission_id}/price-context", response_model=list[schemas.PriceContextOut]
)
async def price_context(submission_id: int, session: SessionDep, employee: EmployeeDep):
    """R3/N9 — `reporter` uchun `403 price_reference_hidden`."""
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    contexts = await pricing_service.price_context(session, submission, employee)
    return [
        schemas.PriceContextOut(
            line_id=ctx.line_id,
            name=ctx.name,
            proposed_amount=ctx.proposed_amount,
            count=ctx.count,
            avg_approved=ctx.avg_approved,
            min_approved=ctx.min_approved,
            max_approved=ctx.max_approved,
            author_avg=ctx.author_avg,
            author_reduction_pct=ctx.author_reduction_pct,
            quick_amounts=ctx.quick_amounts,
        )
        for ctx in contexts
    ]


@router.post("/submissions/{submission_id}/propose-price", response_model=schemas.SubmissionOut)
async def propose_price(
    submission_id: int,
    payload: schemas.ProposePriceRequest,
    session: SessionDep,
    employee: EmployeeDep,
):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    await pricing_service.propose_price(
        session,
        submission,
        employee,
        changes=[(item.line_id, item.amount) for item in payload.lines],
        comment=payload.comment,
    )
    return serializers.submission_out(submission)


@router.post("/submissions/{submission_id}/accept-price", response_model=schemas.SubmissionOut)
async def accept_price(submission_id: int, session: SessionDep, employee: EmployeeDep):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    await pricing_service.accept_price(session, submission, employee)
    return serializers.submission_out(submission)


@router.post("/submissions/{submission_id}/dispute-price", response_model=schemas.SubmissionOut)
async def dispute_price(
    submission_id: int,
    payload: schemas.CommentRequest,
    session: SessionDep,
    employee: EmployeeDep,
):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    await pricing_service.dispute_price(
        session, submission, employee, comment=payload.comment or ""
    )
    return serializers.submission_out(submission)


@router.get(
    "/submissions/{submission_id}/price-history", response_model=list[schemas.ApprovalOut]
)
async def price_history(submission_id: int, session: SessionDep, employee: EmployeeDep):
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    rows = (
        await session.execute(
            sa.select(Approval)
            .where(Approval.submission_id == submission.id)
            .order_by(Approval.created_at)
        )
    ).scalars().all()
    return [
        schemas.ApprovalOut(
            id=row.id,
            actor_id=row.actor_id,
            decision=row.decision.value,
            line_id=row.line_id,
            amount_before=row.amount_before,
            amount_after=row.amount_after,
            comment=row.comment,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/me/price-stats", response_model=schemas.PriceStatsOut)
async def my_price_stats(session: SessionDep, employee: EmployeeDep, period_id: int | None = None):
    """⭐ Xodim **o'z** statistikasini ko'radi (A-24)."""
    stats = await pricing_service.employee_price_stats(
        session, employee.id, period_id=period_id
    )
    return schemas.PriceStatsOut(
        lines_total=stats.lines_total,
        lines_reduced=stats.lines_reduced,
        proposed_total=stats.proposed_total,
        approved_total=stats.approved_total,
        reduction_total=stats.reduction_total,
        reduction_rate_pct=stats.reduction_rate_pct,
        avg_reduction_pct=stats.avg_reduction_pct,
        disputes=stats.disputes,
    )
