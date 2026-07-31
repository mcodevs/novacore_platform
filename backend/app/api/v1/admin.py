"""Admin CRUD: mashina, xodim, rol, ish turlari, audit, bayroqlar."""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Query

from app.api.deps import AdminDep, SessionDep
from app.api.v1 import schemas, serializers
from app.core.errors import BusinessRuleViolated, NotFound
from app.core.phone import display_plate, normalize_phone, normalize_plate
from app.db.models import (
    AuditLog,
    Employee,
    EmployeeStatus,
    Flag,
    FlagResolution,
    Role,
    RoleKind,
    RoleTemplate,
    Template,
    Vehicle,
    WorkCatalog,
)
from app.domain import audit
from app.domain.fleet import service as fleet_service
from app.domain.role import permissions
from app.domain.template import builder

router = APIRouter(tags=["admin"], prefix="/admin")


# --- Mashinalar ---------------------------------------------------------------


@router.post("/vehicles", response_model=schemas.VehicleOut, status_code=201)
async def create_vehicle(payload: schemas.VehicleIn, session: SessionDep, actor: AdminDep):
    plate = normalize_plate(payload.plate_number)
    if not plate:
        raise BusinessRuleViolated("Raqam noto'g'ri")
    exists = (
        await session.execute(sa.select(Vehicle).where(Vehicle.plate_number == plate))
    ).scalar_one_or_none()
    if exists is not None:
        raise BusinessRuleViolated("Bu raqam allaqachon mavjud")

    vehicle = Vehicle(
        plate_number=plate,
        plate_display=display_plate(plate),
        brand=payload.brand,
        model=payload.model,
        year=payload.year,
        color=payload.color,
        vin=payload.vin,
        tariff=payload.tariff,
        fleet_car_id=payload.fleet_car_id,
    )
    session.add(vehicle)
    await session.flush()
    await audit.log(
        session,
        action="vehicle.create",
        entity_type="vehicle",
        entity_id=vehicle.id,
        actor_id=actor.id,
        after={"plate": plate},
    )
    return serializers.vehicle_out(vehicle)


@router.patch("/vehicles/{vehicle_id}", response_model=schemas.VehicleOut)
async def update_vehicle(
    vehicle_id: int, payload: schemas.VehicleIn, session: SessionDep, actor: AdminDep
):
    vehicle = await session.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise NotFound("Mashina topilmadi")
    before = {"plate": vehicle.plate_number, "brand": vehicle.brand, "model": vehicle.model}

    plate = normalize_plate(payload.plate_number)
    if plate:
        vehicle.plate_number = plate
        vehicle.plate_display = display_plate(plate)
    vehicle.brand = payload.brand or vehicle.brand
    vehicle.model = payload.model or vehicle.model
    vehicle.year = payload.year or vehicle.year
    vehicle.color = payload.color or vehicle.color
    vehicle.vin = payload.vin or vehicle.vin
    vehicle.tariff = payload.tariff or vehicle.tariff
    await session.flush()

    await audit.log(
        session,
        action="vehicle.update",
        entity_type="vehicle",
        entity_id=vehicle.id,
        actor_id=actor.id,
        before=before,
        after={"plate": vehicle.plate_number},
    )
    return serializers.vehicle_out(vehicle)


# --- Xodimlar -----------------------------------------------------------------


@router.get("/employees", response_model=list[schemas.EmployeeOut])
async def list_employees(session: SessionDep, actor: AdminDep, status: str | None = None):
    stmt = sa.select(Employee).where(Employee.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Employee.status == EmployeeStatus(status))
    rows = (await session.execute(stmt.order_by(Employee.full_name))).scalars().all()
    return [serializers.employee_out(row) for row in rows]


@router.post("/employees", response_model=schemas.EmployeeOut, status_code=201)
async def create_employee(payload: schemas.EmployeeIn, session: SessionDep, actor: AdminDep):
    """Xodim avval reyestrga kiritiladi, keyin o'zi Telegram'da bog'lanadi."""
    phone = normalize_phone(payload.phone)
    if not phone:
        raise BusinessRuleViolated("Telefon raqami noto'g'ri")
    exists = (
        await session.execute(sa.select(Employee).where(Employee.phone == phone))
    ).scalar_one_or_none()
    if exists is not None:
        raise BusinessRuleViolated("Bu raqam allaqachon reyestrda")

    role = await session.get(Role, payload.role_id)
    if role is None:
        raise NotFound("Rol topilmadi")

    employee = Employee(
        full_name=payload.full_name,
        phone=phone,
        role_id=role.id,
        workshop_name=payload.workshop_name,
        lang=payload.lang,
    )
    session.add(employee)
    await session.flush()
    await session.refresh(employee)
    await audit.log(
        session,
        action="employee.create",
        entity_type="employee",
        entity_id=employee.id,
        actor_id=actor.id,
        after={"phone": phone, "role": role.code},
    )
    return serializers.employee_out(employee)


@router.post("/employees/{employee_id}/role", response_model=schemas.EmployeeOut)
async def set_role(
    employee_id: int, payload: schemas.SetRoleRequest, session: SessionDep, actor: AdminDep
):
    employee = await session.get(Employee, employee_id)
    if employee is None:
        raise NotFound("Xodim topilmadi")
    role = await session.get(Role, payload.role_id)
    if role is None:
        raise NotFound("Rol topilmadi")

    # R8 — oxirgi adminni rolidan ayirish taqiqlanadi
    if employee.role.kind == RoleKind.admin:
        await permissions.ensure_admin_remains(
            session, changing_employee_id=employee.id, new_role_id=role.id
        )

    before = {"role": employee.role.code}
    employee.role_id = role.id
    await session.flush()
    await session.refresh(employee)
    await audit.log(
        session,
        action="employee.set_role",
        entity_type="employee",
        entity_id=employee.id,
        actor_id=actor.id,
        before=before,
        after={"role": role.code},
    )
    return serializers.employee_out(employee)


@router.post("/employees/{employee_id}/status", response_model=schemas.EmployeeOut)
async def set_status(
    employee_id: int, status: str, session: SessionDep, actor: AdminDep
):
    employee = await session.get(Employee, employee_id)
    if employee is None:
        raise NotFound("Xodim topilmadi")
    new_status = EmployeeStatus(status)

    if employee.role.kind == RoleKind.admin and new_status != EmployeeStatus.active:
        await permissions.ensure_admin_remains(session, changing_employee_id=employee.id)

    before = {"status": employee.status.value}
    employee.status = new_status
    await session.flush()
    await audit.log(
        session,
        action="employee.set_status",
        entity_type="employee",
        entity_id=employee.id,
        actor_id=actor.id,
        before=before,
        after={"status": new_status.value},
    )
    return serializers.employee_out(employee)


# --- Rollar (⭐ admin uchun asosiy vosita) --------------------------------------


@router.get("/roles")
async def list_roles(session: SessionDep, actor: AdminDep):
    rows = (await session.execute(sa.select(Role).order_by(Role.sort))).scalars().all()
    return {
        "data": [
            {
                "id": role.id,
                "code": role.code,
                "name_uz": role.name_uz,
                "name_ru": role.name_ru,
                "icon": role.icon,
                "kind": role.kind.value,
                "is_system": role.is_system,
                "template_ids": [rt.template_id for rt in role.templates],
            }
            for role in rows
        ]
    }


@router.post("/roles", status_code=201)
async def create_role(payload: schemas.RoleIn, session: SessionDep, actor: AdminDep):
    """Yangi rol = nom + kind + shablonlar. Kod yozilmaydi, deploy qilinmaydi."""
    if payload.kind not in {k.value for k in RoleKind}:
        raise BusinessRuleViolated("kind faqat reporter/admin/accountant bo'lishi mumkin")
    if not builder.CODE_RE.match(payload.code.strip()):
        raise BusinessRuleViolated("Rol kodi: a-z, 0-9 va _ (3–40 belgi)")

    exists = (
        await session.execute(sa.select(Role.id).where(Role.code == payload.code.strip()))
    ).first()
    if exists:
        raise BusinessRuleViolated(f"«{payload.code}» kodli rol allaqachon bor")

    role = Role(
        code=payload.code.strip(),
        name_uz=payload.name_uz,
        name_ru=payload.name_ru,
        icon=payload.icon,
        kind=RoleKind(payload.kind),
    )
    session.add(role)
    await session.flush()
    await _set_role_templates(session, role, payload.template_ids)

    await audit.log(
        session,
        action="role.create",
        entity_type="role",
        entity_id=role.id,
        actor_id=actor.id,
        after={"code": role.code, "kind": role.kind.value},
    )
    return {"data": {"id": role.id, "code": role.code}}


async def _set_role_templates(
    session: SessionDep, role: Role, template_ids: list[int]
) -> None:
    """Rol ko'radigan shablonlar ro'yxatini to'liq almashtiradi."""
    await session.execute(sa.delete(RoleTemplate).where(RoleTemplate.role_id == role.id))
    for idx, template_id in enumerate(template_ids, start=1):
        if await session.get(Template, template_id) is None:
            raise NotFound(f"Shablon topilmadi: {template_id}")
        session.add(RoleTemplate(role_id=role.id, template_id=template_id, sort=idx * 10))
    await session.flush()


@router.patch("/roles/{role_id}")
async def update_role(
    role_id: int, payload: schemas.RoleUpdate, session: SessionDep, actor: AdminDep
):
    """Rolni tahrirlash: nom, ikonka, shablonlar, tur. `code` o'zgarmaydi."""
    role = await session.get(Role, role_id)
    if role is None:
        raise NotFound("Rol topilmadi")

    before = {
        "name_uz": role.name_uz,
        "kind": role.kind.value,
        "is_active": role.is_active,
        "template_ids": [rt.template_id for rt in role.templates],
    }

    if payload.kind is not None and payload.kind != role.kind.value:
        if payload.kind not in {k.value for k in RoleKind}:
            raise BusinessRuleViolated("kind faqat reporter/admin/accountant bo'lishi mumkin")
        if role.is_system:
            raise BusinessRuleViolated("Tizim rolining turini o'zgartirib bo'lmaydi")
        # R8 — bu roldagi xodimlar admin huquqidan ayrilsa, boshqa admin qolsinmi
        await permissions.ensure_admin_remains_without_role(session, role)
        role.kind = RoleKind(payload.kind)

    if payload.is_active is not None and payload.is_active is False:
        if role.is_system:
            raise BusinessRuleViolated("Tizim rolini o'chirib bo'lmaydi")
        await permissions.ensure_admin_remains_without_role(session, role)
        role.is_active = False
    elif payload.is_active:
        role.is_active = True

    if payload.name_uz is not None:
        role.name_uz = payload.name_uz.strip()
    if payload.name_ru is not None:
        role.name_ru = payload.name_ru.strip()
    if payload.icon is not None:
        role.icon = payload.icon
    if payload.sort is not None:
        role.sort = payload.sort
    if payload.template_ids is not None:
        await _set_role_templates(session, role, payload.template_ids)

    await session.flush()
    await session.refresh(role)
    await audit.log(
        session,
        action="role.update",
        entity_type="role",
        entity_id=role.id,
        actor_id=actor.id,
        before=before,
        after={
            "name_uz": role.name_uz,
            "kind": role.kind.value,
            "is_active": role.is_active,
            "template_ids": [rt.template_id for rt in role.templates],
        },
    )
    return {"data": {"id": role.id, "code": role.code}}


# --- Shablon konstruktori (⭐ Faza 2) -------------------------------------------


def _template_row(template: Template, *, published: int | None) -> dict:
    return {
        "id": template.id,
        "code": template.code,
        "name_uz": template.name_uz,
        "name_ru": template.name_ru,
        "icon": template.icon,
        "version": template.version,
        "published_version": published,
        "is_draft": published != template.version,
        "is_active": template.is_active,
        "has_money": template.has_money,
        "negotiable": template.negotiable,
        "fields_count": len(template.fields),
    }


@router.get("/templates")
async def list_templates(session: SessionDep, actor: AdminDep):
    """Barcha shablonlar — qoralama holati bilan."""
    rows = (await session.execute(sa.select(Template).order_by(Template.id))).scalars().all()
    data = []
    for template in rows:
        published = await builder.latest_published_version(session, template.id)
        data.append(_template_row(template, published=published))
    return {"data": data}


@router.get("/templates/{template_id}")
async def get_template(template_id: int, session: SessionDep, actor: AdminDep):
    """Joriy (tahrirlanayotgan) sxema — konstruktor shuni ochadi."""
    template = await builder.get_or_404(session, template_id)
    published = await builder.latest_published_version(session, template.id)
    return {
        "data": {
            **_template_row(template, published=published),
            "definition": builder.to_definition(template),
        }
    }


@router.post("/templates", status_code=201)
async def create_template(payload: schemas.TemplateIn, session: SessionDep, actor: AdminDep):
    """Yangi shablon — qoralama. Nashr etilmaguncha hech kimga ko'rinmaydi."""
    template = await builder.create(session, actor, payload.model_dump())
    return {"data": _template_row(template, published=None)}


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: int, payload: schemas.TemplateIn, session: SessionDep, actor: AdminDep
):
    """Tahrirlash. Nashr etilgan versiya tegilmaydi — yangi qoralama ochiladi."""
    template = await builder.get_or_404(session, template_id)
    template = await builder.update(session, actor, template, payload.model_dump())
    published = await builder.latest_published_version(session, template.id)
    return {"data": _template_row(template, published=published)}


@router.post("/templates/{template_id}/publish")
async def publish_template(template_id: int, session: SessionDep, actor: AdminDep):
    """Nashr — shu versiya snapshot'i **o'zgarmas** bo'lib qoladi."""
    template = await builder.get_or_404(session, template_id)
    template = await builder.publish(session, actor, template)
    return {"data": _template_row(template, published=template.version)}


# --- Ish turlari (tayanch narx — faqat admin) ----------------------------------


@router.patch("/work-catalog/{item_id}")
async def update_work_item(
    item_id: int,
    reference_price: float | None = None,
    is_active: bool | None = None,
    session: SessionDep = None,  # type: ignore[assignment]
    actor: AdminDep = None,  # type: ignore[assignment]
):
    row = await session.get(WorkCatalog, item_id)
    if row is None:
        raise NotFound("Ish turi topilmadi")
    before = {"reference_price": str(row.reference_price), "is_active": row.is_active}
    if reference_price is not None:
        row.reference_price = reference_price
    if is_active is not None:
        row.is_active = is_active
    await session.flush()
    await audit.log(
        session,
        action="work_catalog.update",
        entity_type="work_catalog",
        entity_id=row.id,
        actor_id=actor.id,
        before=before,
        after={"reference_price": str(row.reference_price), "is_active": row.is_active},
    )
    return {"data": {"id": row.id}}


# --- Fleet sinxroni (Faza 3, faqat o'qish) -------------------------------------


@router.post("/fleet/sync")
async def fleet_sync(session: SessionDep, actor: AdminDep):
    """Qo'lda sinxron: Fleet → mashina va haydovchi reyestri.

    Platforma Fleet'ga hech narsa yozmaydi. Xato bo'lsa 200 bilan `error`
    qaytadi — bu buzilish emas, platforma Fleet'siz ham ishlaydi.
    """
    report = await fleet_service.sync(session, actor_id=actor.id)
    return {
        "data": {
            "ok": report.ok,
            "created": report.created,
            "updated": report.updated,
            "missing": report.missing,
            "drivers_linked": report.drivers_linked,
            "skipped": report.skipped,
            "error": report.error,
            "summary": report.summary(),
        }
    }


# --- Audit va bayroqlar --------------------------------------------------------


@router.get("/audit")
async def audit_log(
    session: SessionDep,
    actor: AdminDep,
    entity: str | None = None,
    actor_id: int | None = None,
    limit: int = Query(50, le=200),
):
    stmt = sa.select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if entity:
        stmt = stmt.where(AuditLog.entity_type == entity)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "data": [
            {
                "id": row.id,
                "actor_id": row.actor_id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "before": row.before,
                "after": row.after,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }


@router.get("/flags")
async def list_flags(session: SessionDep, actor: AdminDep, limit: int = Query(50, le=200)):
    rows = (
        await session.execute(
            sa.select(Flag).where(Flag.resolution.is_(None)).order_by(Flag.created_at.desc()).limit(limit)
        )
    ).scalars().all()
    return {
        "data": [
            {
                "id": row.id,
                "submission_id": row.submission_id,
                "code": row.code,
                "severity": row.severity.value,
                "details": row.details,
            }
            for row in rows
        ]
    }


@router.post("/flags/{flag_id}/resolve")
async def resolve_flag(
    flag_id: int,
    resolution: str,
    session: SessionDep,
    actor: AdminDep,
    comment: str | None = None,
):
    flag = await session.get(Flag, flag_id)
    if flag is None:
        raise NotFound("Bayroq topilmadi")
    flag.resolution = FlagResolution(resolution)
    flag.resolution_comment = comment
    flag.resolved_by = actor.id
    await session.flush()
    await audit.log(
        session,
        action="flag.resolve",
        entity_type="flag",
        entity_id=flag.id,
        actor_id=actor.id,
        after={"resolution": resolution, "comment": comment},
    )
    return {"data": {"ok": True}}
