"""Hisobot hayotiy sikli: mashina keldi → forma → mashina ketdi → yuborish."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import TASHKENT, settings
from app.core.errors import (
    BusinessRuleViolated,
    Forbidden,
    InvalidStateTransition,
    NotFound,
    ValidationFailed,
)
from app.db.base import ZERO, as_utc, money, utcnow
from app.db.models import (
    Counter,
    EDITABLE_STATUSES,
    Employee,
    LineKind,
    RoleKind,
    Submission,
    SubmissionLine,
    SubmissionStatus,
    Template,
    Vehicle,
)
from app.domain import audit
from app.domain.antifraud import service as antifraud
from app.domain.approval import service as approval_service
from app.domain.notify import service as notify
from app.domain.period import service as period_service
from app.domain.role import permissions
from app.domain.template import engine
from app.domain import vehicle as vehicle_domain


# --- Raqamlash ---------------------------------------------------------------


async def next_number(session: AsyncSession, *, moment: dt.datetime | None = None) -> str:
    """WO-2026-000123 — yillik hisoblagich."""
    year = as_utc(moment or utcnow()).astimezone(TASHKENT).year
    key = f"submission:{year}"

    counter = await session.get(Counter, key, with_for_update=not settings.is_sqlite)
    if counter is None:
        counter = Counter(key=key, value=0)
        session.add(counter)
        await session.flush()
    counter.value += 1
    await session.flush()
    return f"WO-{year}-{counter.value:06d}"


# --- Qoralama ----------------------------------------------------------------


async def active_draft(session: AsyncSession, employee: Employee) -> Submission | None:
    """Xodimning tugallanmagan hisoboti (DRAFT yoki REOPENED)."""
    stmt = (
        sa.select(Submission)
        .where(
            Submission.author_id == employee.id,
            Submission.deleted_at.is_(None),
            Submission.status.in_(EDITABLE_STATUSES),
        )
        .order_by(Submission.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


async def create_draft(
    session: AsyncSession,
    author: Employee,
    template: Template,
    *,
    vehicle_id: int | None = None,
) -> Submission:
    """«🚗 Mashina keldi» — `arrived_at` SERVER vaqti bilan yoziladi (R6)."""
    if not permissions.can_create_submission(author):
        raise Forbidden("Sizning rolingiz hisobot yaratmaydi")

    period = await period_service.current_period(session)
    period_service.ensure_open(period)  # R4

    submission = Submission(
        number=await next_number(session),
        template_id=template.id,
        template_version=template.version,
        author_id=author.id,
        status=SubmissionStatus.DRAFT,
        data={},
        arrived_at=utcnow(),  # server vaqti — klientga ishonilmaydi
    )
    session.add(submission)
    await session.flush()

    if vehicle_id is not None:
        vehicle = await session.get(Vehicle, vehicle_id)
        if vehicle is not None:
            await attach_vehicle(session, submission, vehicle)

    await audit.log(
        session,
        action="submission.create",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=author.id,
        after={"number": submission.number, "arrived_at": submission.arrived_at.isoformat()},
    )
    await session.refresh(submission)
    return submission


async def attach_vehicle(
    session: AsyncSession, submission: Submission, vehicle: Vehicle
) -> None:
    """Mashina biriktirildi → status IN_SERVICE (downtime taymeri ketmoqda)."""
    await vehicle_domain.to_service(session, submission, vehicle)


async def delete_draft(session: AsyncSession, submission: Submission, actor: Employee) -> None:
    """Faqat DRAFT, faqat muallif. O'chirish yo'q — `deleted_at` (R9)."""
    if submission.author_id != actor.id:
        raise Forbidden("Faqat muallif o'chira oladi")
    if submission.status != SubmissionStatus.DRAFT:
        raise InvalidStateTransition("Faqat qoralamani o'chirish mumkin")

    submission.deleted_at = utcnow()
    await vehicle_domain.release(session, submission)
    await audit.log(
        session,
        action="submission.delete_draft",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id,
    )
    await session.flush()


def ensure_editable(submission: Submission, actor: Employee) -> None:
    if submission.author_id != actor.id:
        raise Forbidden("Faqat muallif tahrirlaydi")
    if submission.status not in EDITABLE_STATUSES:
        raise InvalidStateTransition("Bu holatda tahrirlash mumkin emas")


# --- Qatorlar ----------------------------------------------------------------


async def add_line(
    session: AsyncSession,
    submission: Submission,
    actor: Employee,
    *,
    kind: LineKind,
    name: str,
    qty: Decimal | float | int = 1,
    unit_price: Decimal | float | int | None = None,
    catalog_id: int | None = None,
    supplier_name: str | None = None,
) -> SubmissionLine:
    """Ish yoki qism qatori. Narxni **muallif** qo'yadi (labor uchun)."""
    ensure_editable(submission, actor)

    quantity = Decimal(str(qty or 1)).quantize(Decimal("0.01"))
    if quantity <= ZERO:
        raise BusinessRuleViolated("Miqdor 0 dan katta bo'lishi kerak")

    price = money(unit_price if unit_price is not None else 0)
    line = SubmissionLine(
        submission_id=submission.id,
        kind=kind,
        catalog_id=catalog_id,
        name=name.strip(),
        qty=quantity,
        proposed_unit_price=price,
        proposed_amount=money(price * quantity),
        supplier_name=supplier_name,
    )
    session.add(line)
    await session.flush()
    await session.refresh(submission)
    engine.recalculate_amounts(submission)
    await session.flush()
    return line


async def remove_line(
    session: AsyncSession, submission: Submission, actor: Employee, line_id: int
) -> None:
    ensure_editable(submission, actor)
    line = await session.get(SubmissionLine, line_id)
    if line is None or line.submission_id != submission.id:
        raise NotFound("Qator topilmadi")
    await session.delete(line)
    await session.flush()
    await session.refresh(submission)
    engine.recalculate_amounts(submission)
    await session.flush()


# --- Mashina ketdi -----------------------------------------------------------


async def mark_left(
    session: AsyncSession, submission: Submission, actor: Employee
) -> Submission:
    """«🚙 Mashina ketdi» — `left_at` SERVER vaqti (R6)."""
    ensure_editable(submission, actor)
    now = utcnow()
    if submission.arrived_at is not None and now < as_utc(submission.arrived_at):
        raise BusinessRuleViolated("left_at < arrived_at")

    submission.left_at = now
    await vehicle_domain.release(session, submission)

    await audit.log(
        session,
        action="submission.mark_left",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id,
        after={"left_at": now.isoformat()},
    )
    await session.flush()
    return submission


# --- Yuborish ----------------------------------------------------------------


async def _business_checks(
    session: AsyncSession, submission: Submission
) -> list[engine.ValidationIssue]:
    issues: list[engine.ValidationIssue] = []

    if submission.left_at is None:
        issues.append(engine.ValidationIssue("_left_at", "need_left_first", {}))
    elif submission.arrived_at is not None and as_utc(submission.left_at) < as_utc(
        submission.arrived_at
    ):
        issues.append(engine.ValidationIssue("_left_at", "invalid_state", {}))

    # probeg kamaymasin (monotonic_for_vehicle)
    if submission.odometer_km is not None and submission.subject_vehicle_id is not None:
        previous = (
            await session.execute(
                sa.select(sa.func.max(Submission.odometer_km)).where(
                    Submission.subject_vehicle_id == submission.subject_vehicle_id,
                    Submission.id != submission.id,
                    Submission.deleted_at.is_(None),
                    Submission.status.not_in(
                        [SubmissionStatus.DRAFT, SubmissionStatus.REJECTED]
                    ),
                )
            )
        ).scalar_one_or_none()
        if previous is not None and submission.odometer_km < previous:
            issues.append(
                engine.ValidationIssue("odometer_value", "odometer_decreased", {"prev": previous})
            )
    return issues


async def validate_for_submit(
    session: AsyncSession, submission: Submission
) -> list[engine.ValidationIssue]:
    schema = await engine.schema_for_submission(session, submission)
    issues = list(engine.validate(schema, submission))
    engine.apply_field_mapping(schema, submission)
    issues.extend(await _business_checks(session, submission))
    return issues


async def submit(
    session: AsyncSession, submission: Submission, actor: Employee
) -> Submission:
    """docs/02-architecture/04-api-design.md §11 — 1..11 bitta tranzaksiyada."""
    # 1–2. ruxsat va holat
    if submission.author_id != actor.id:
        raise Forbidden("Faqat muallif yuboradi")
    if submission.status not in EDITABLE_STATUSES:
        raise InvalidStateTransition(f"{submission.status.value} → submitted mumkin emas")

    # 3. davr ochiqmi
    period = await period_service.current_period(session)
    period_service.ensure_open(period)

    # 4–6. validatsiya + biznes tekshiruvlar
    schema = await engine.schema_for_submission(session, submission)
    issues = list(engine.validate(schema, submission))
    engine.apply_field_mapping(schema, submission)  # 8. promoted ustunlar
    issues.extend(await _business_checks(session, submission))
    if issues:
        raise ValidationFailed(
            "Forma to'liq to'ldirilmagan",
            fields={i.field_code: i.key for i in issues},
            issues=issues,
        )

    # 7. summalar QAYTA hisoblanadi (klientga ishonilmaydi — R7)
    engine.recalculate_amounts(submission)

    # 11. submitted_at + period
    submission.submitted_at = utcnow()
    submission.period_id = period.id

    # 9. bayroqlar (Faza 1'da o'chirilgan — docs/04-flows/02-antifraud.md §9)
    await antifraud.evaluate(session, submission)

    # 10. muallifning role.kind
    if actor.role.kind == RoleKind.admin:
        await approval_service.auto_approve(session, submission)  # R1a
    else:
        submission.status = SubmissionStatus.SUBMITTED
        await notify.notify_admins(
            session,
            template_code="notify_new_submission",
            payload={
                "submission_id": submission.id,
                "number": submission.number,
                "author": actor.full_name,
                "amount": str(submission.proposed_labor_amount),
                "vehicle": submission.vehicle.plate_display if submission.vehicle else "—",
            },
        )

    # 13. audit
    await audit.log(
        session,
        action="submission.submit",
        entity_type="submission",
        entity_id=submission.id,
        actor_id=actor.id,
        after={
            "status": submission.status.value,
            "proposed_labor_amount": str(submission.proposed_labor_amount),
            "auto_approved": submission.auto_approved,
        },
    )
    await session.flush()
    return submission


# --- Ro'yxatlar --------------------------------------------------------------


async def list_for_employee(
    session: AsyncSession,
    employee: Employee,
    *,
    statuses: tuple[SubmissionStatus, ...] | None = None,
    period_id: int | None = None,
    limit: int = 20,
) -> list[Submission]:
    stmt = sa.select(Submission).where(Submission.deleted_at.is_(None))
    if not permissions.can_see_all_submissions(employee):
        stmt = stmt.where(Submission.author_id == employee.id)
    if statuses:
        stmt = stmt.where(Submission.status.in_(list(statuses)))
    if period_id is not None:
        stmt = stmt.where(Submission.period_id == period_id)
    stmt = stmt.order_by(Submission.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def pending_review(session: AsyncSession, *, limit: int = 50) -> list[Submission]:
    stmt = (
        sa.select(Submission)
        .where(
            Submission.deleted_at.is_(None),
            Submission.status.in_(
                [
                    SubmissionStatus.SUBMITTED,
                    SubmissionStatus.IN_REVIEW,
                    SubmissionStatus.PRICE_DISPUTED,
                ]
            ),
        )
        .order_by(Submission.submitted_at.asc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def awaiting_author_decision(
    session: AsyncSession, employee: Employee, *, limit: int = 20
) -> list[Submission]:
    stmt = (
        sa.select(Submission)
        .where(
            Submission.deleted_at.is_(None),
            Submission.author_id == employee.id,
            Submission.status == SubmissionStatus.PRICE_NEGOTIATION,
        )
        .order_by(Submission.price_proposed_at.asc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_for_actor(
    session: AsyncSession, submission_id: int, actor: Employee
) -> Submission:
    submission = await session.get(Submission, submission_id)
    if submission is None or submission.deleted_at is not None:
        raise NotFound("Hisobot topilmadi")
    permissions.ensure_can_view_submission(actor, submission)
    return submission
