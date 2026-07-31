"""Spravochniklar: mashinalar, shablonlar, ish turlari, qismlar."""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Query

from app.api.deps import EmployeeDep, SessionDep
from app.api.v1 import schemas, serializers
from app.core.errors import NotFound
from app.core.phone import normalize_plate
from app.db.models import (
    CatalogItem,
    PartsCatalog,
    RoleTemplate,
    Submission,
    Template,
    TemplateVersion,
    Vehicle,
    WorkCatalog,
)
from app.domain.template import engine

router = APIRouter(tags=["catalogs"])


@router.get("/vehicles", response_model=list[schemas.VehicleOut])
async def list_vehicles(
    session: SessionDep,
    employee: EmployeeDep,
    q: str | None = None,
    status: str | None = None,
    limit: int = Query(50, le=200),
):
    stmt = sa.select(Vehicle).where(Vehicle.deleted_at.is_(None))
    if q:
        like = f"%{(normalize_plate(q) or q).upper()}%"
        stmt = stmt.where(Vehicle.plate_number.like(like))
    if status:
        stmt = stmt.where(Vehicle.status == status)
    rows = (await session.execute(stmt.order_by(Vehicle.plate_number).limit(limit))).scalars()
    return [serializers.vehicle_out(row) for row in rows]


@router.get("/vehicles/lookup", response_model=schemas.VehicleOut)
async def lookup_vehicle(session: SessionDep, employee: EmployeeDep, plate: str):
    normalized = normalize_plate(plate)
    vehicle = (
        await session.execute(sa.select(Vehicle).where(Vehicle.plate_number == normalized))
    ).scalar_one_or_none()
    if vehicle is None or vehicle.deleted_at is not None:
        raise NotFound("Mashina reyestrda yo'q")
    return serializers.vehicle_out(vehicle)


@router.get("/vehicles/{vehicle_id}/history", response_model=list[schemas.SubmissionOut])
async def vehicle_history(
    session: SessionDep, employee: EmployeeDep, vehicle_id: int, limit: int = Query(20, le=100)
):
    from app.domain.role import permissions

    stmt = (
        sa.select(Submission)
        .where(
            Submission.subject_vehicle_id == vehicle_id,
            Submission.deleted_at.is_(None),
            Submission.submitted_at.is_not(None),
        )
        .order_by(Submission.submitted_at.desc())
        .limit(limit)
    )
    if not permissions.can_see_all_submissions(employee):
        stmt = stmt.where(Submission.author_id == employee.id)
    rows = (await session.execute(stmt)).scalars().all()
    return [serializers.submission_out(row) for row in rows]


@router.get("/templates", response_model=list[schemas.TemplateOut])
async def my_templates(session: SessionDep, employee: EmployeeDep):
    """**Menga tegishli** shablonlar — rolim bo'yicha."""
    stmt = (
        sa.select(Template)
        .join(RoleTemplate, RoleTemplate.template_id == Template.id)
        .where(RoleTemplate.role_id == employee.role_id, Template.is_active.is_(True))
        .order_by(RoleTemplate.sort)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [serializers.template_out(row, employee.lang) for row in rows]


@router.get("/templates/{code}")
async def template_schema(
    session: SessionDep, employee: EmployeeDep, code: str, version: int | None = None
):
    """To'liq sxema — Mini App form renderer shu bilan forma chizadi."""
    template = (
        await session.execute(sa.select(Template).where(Template.code == code))
    ).scalar_one_or_none()
    if template is None:
        raise NotFound("Shablon topilmadi")

    snapshot = (
        await session.execute(
            sa.select(TemplateVersion).where(
                TemplateVersion.template_id == template.id,
                TemplateVersion.version == (version or template.version),
            )
        )
    ).scalar_one_or_none()
    if snapshot is not None:
        return {"data": snapshot.schema_json}

    schema = engine.schema_from_template(template)
    return {
        "data": {
            "code": schema.code,
            "version": schema.version,
            "name": {"uz": schema.name_uz, "ru": schema.name_ru},
            "sections": schema.sections,
            "field_mapping": schema.field_mapping,
            "fields": [
                {
                    "code": f.code,
                    "type": f.type,
                    "label": {"uz": f.label_uz, "ru": f.label_ru},
                    "required": f.required,
                    "section": f.section,
                    "options": f.options,
                    "validation": f.validation,
                }
                for f in schema.fields
            ],
        }
    }


@router.get("/catalog-items")
async def catalog_items(session: SessionDep, employee: EmployeeDep, catalog: str):
    """Kichik spravochniklar (`select` maydonlari): nosozlik kategoriyalari…"""
    rows = (
        await session.execute(
            sa.select(CatalogItem)
            .where(CatalogItem.catalog == catalog, CatalogItem.is_active.is_(True))
            .order_by(CatalogItem.sort)
        )
    ).scalars().all()
    return {
        "data": [
            {"code": row.code, "name": row.name(employee.lang), "icon": row.icon}
            for row in rows
        ]
    }


@router.get("/work-catalog", response_model=list[schemas.WorkCatalogOut])
async def work_catalog(
    session: SessionDep, employee: EmployeeDep, q: str | None = None, limit: int = Query(100, le=300)
):
    """⚠️ `reference_price` `reporter` roliga **qaytarilmaydi** (R3)."""
    stmt = sa.select(WorkCatalog).where(WorkCatalog.is_active.is_(True))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            sa.or_(
                sa.func.lower(WorkCatalog.name_uz).like(like),
                sa.func.lower(WorkCatalog.name_ru).like(like),
            )
        )
    rows = (await session.execute(stmt.order_by(WorkCatalog.name_uz).limit(limit))).scalars()
    return [serializers.work_catalog_out(row, employee) for row in rows]


@router.get("/parts-catalog", response_model=list[schemas.PartsCatalogOut])
async def parts_catalog(
    session: SessionDep, employee: EmployeeDep, q: str | None = None, limit: int = Query(100, le=300)
):
    stmt = sa.select(PartsCatalog).where(PartsCatalog.is_active.is_(True))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            sa.or_(
                sa.func.lower(PartsCatalog.name_uz).like(like),
                sa.func.lower(PartsCatalog.name_ru).like(like),
            )
        )
    rows = (await session.execute(stmt.order_by(PartsCatalog.name_uz).limit(limit))).scalars()
    return [serializers.parts_catalog_out(row, employee) for row in rows]
