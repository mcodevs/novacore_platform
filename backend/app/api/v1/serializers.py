"""Model → API sxema. R3 shu yerda ham qo'llanadi."""

from __future__ import annotations

from app.api.v1 import schemas
from app.db.models import (
    Employee,
    Media,
    PartsCatalog,
    Submission,
    SubmissionLine,
    Template,
    Vehicle,
    WorkCatalog,
)
from app.domain.media import service as media_service
from app.domain.role import permissions


def role_out(employee: Employee) -> schemas.RoleOut:
    role = employee.role
    return schemas.RoleOut(
        code=role.code, name=role.name(employee.lang), kind=role.kind.value, icon=role.icon
    )


def employee_out(employee: Employee) -> schemas.EmployeeOut:
    return schemas.EmployeeOut(
        id=employee.id,
        full_name=employee.full_name,
        phone=employee.phone,
        lang=employee.lang,
        role=role_out(employee),
        role_id=employee.role_id,
        workshop_name=employee.workshop_name,
        status=employee.status.value,
        tg_linked=employee.tg_user_id is not None,
    )


def template_out(template: Template, lang: str) -> schemas.TemplateOut:
    return schemas.TemplateOut(
        id=template.id,
        code=template.code,
        name=template.name(lang),
        icon=template.icon,
        version=template.version,
        has_money=template.has_money,
        negotiable=template.negotiable,
    )


def vehicle_out(vehicle: Vehicle) -> schemas.VehicleOut:
    return schemas.VehicleOut(
        id=vehicle.id,
        plate_number=vehicle.plate_number,
        plate_display=vehicle.plate_display,
        brand=vehicle.brand,
        model=vehicle.model,
        year=vehicle.year,
        status=vehicle.status.value,
        odometer_km=vehicle.odometer_km,
        current_driver_name=vehicle.current_driver_name,
    )


def work_catalog_out(row: WorkCatalog, viewer: Employee) -> schemas.WorkCatalogOut:
    """R3/N9 — tayanch narx `reporter` javobidan **serverda** chiqarib tashlanadi."""
    return schemas.WorkCatalogOut(
        id=row.id,
        code=row.code,
        name=row.name(viewer.lang),
        category=row.category,
        reference_price=(
            row.reference_price if permissions.can_see_reference_price(viewer) else None
        ),
    )


def parts_catalog_out(row: PartsCatalog, viewer: Employee) -> schemas.PartsCatalogOut:
    return schemas.PartsCatalogOut(
        id=row.id,
        code=row.code,
        name=row.name(viewer.lang),
        category=row.category,
        last_price=row.last_price if permissions.can_see_reference_price(viewer) else None,
    )


def line_out(line: SubmissionLine) -> schemas.LineOut:
    return schemas.LineOut(
        id=line.id,
        kind=line.kind.value,
        name=line.name,
        qty=line.qty,
        proposed_amount=line.proposed_amount,
        approved_amount=line.approved_amount,
        price_change_reason=line.price_change_reason,
        mechanic_accepted_at=line.mechanic_accepted_at,
        mechanic_accept_mode=(
            line.mechanic_accept_mode.value if line.mechanic_accept_mode else None
        ),
        self_funded=line.self_funded,
    )


def media_out(item: Media) -> schemas.MediaOut:
    return schemas.MediaOut(
        id=item.id,
        field_code=item.field_code,
        kind=item.kind.value,
        mime=item.mime,
        url=media_service.view_url(item),  # signed, 15 daqiqa
    )


def linkable_out(submission: Submission) -> schemas.LinkableSubmissionOut:
    """`submission_picker` ro'yxati — **faqat identifikatsiya**, summasiz.

    Ta'minotchi ustaning ta'mir hisobotini tanlashi kerak, lekin uning narxini
    ko'rishi shart emas (R3 ruhi: narx ma'lumoti reporterga berilmaydi).
    """
    return schemas.LinkableSubmissionOut(
        id=submission.id,
        number=submission.number,
        status=submission.status.value,
        template_code=submission.template.code,
        author_name=submission.author.full_name if submission.author else "",
        vehicle_plate=submission.vehicle.plate_display if submission.vehicle else None,
        submitted_at=submission.submitted_at,
    )


def submission_out(submission: Submission) -> schemas.SubmissionOut:
    return schemas.SubmissionOut(
        id=submission.id,
        number=submission.number,
        status=submission.status.value,
        template_code=submission.template.code,
        template_version=submission.template_version,
        author_id=submission.author_id,
        author_name=submission.author.full_name if submission.author else "",
        vehicle=vehicle_out(submission.vehicle) if submission.vehicle else None,
        data={k: v for k, v in (submission.data or {}).items() if not k.startswith("_")},
        proposed_labor_amount=submission.proposed_labor_amount,
        labor_amount=submission.labor_amount,
        parts_amount=submission.parts_amount,
        total_amount=submission.total_amount,
        payable_amount=submission.payable_amount,
        paid_amount=submission.paid_amount,
        debt=submission.debt,
        auto_approved=submission.auto_approved,
        price_negotiated=submission.price_negotiated,
        arrived_at=submission.arrived_at,
        left_at=submission.left_at,
        submitted_at=submission.submitted_at,
        downtime_seconds=submission.downtime_seconds,
        lines=[line_out(line) for line in submission.lines],
        media=[media_out(m) for m in submission.media if m.deleted_at is None],
    )
