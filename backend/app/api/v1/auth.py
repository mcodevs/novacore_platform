"""Auth — initData → JWT (docs/02-architecture/04-api-design.md §2)."""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from fastapi import APIRouter

from app.api.deps import EmployeeDep, SessionDep
from app.api.v1 import schemas, serializers
from app.core.config import settings
from app.core.errors import Forbidden, NotInRegistry, Unauthenticated
from app.core.security import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    validate_init_data,
)
from app.db.base import as_utc, utcnow
from app.db.models import Employee, RefreshToken, Template
from app.domain import audit
from app.domain.template import builder

router = APIRouter(tags=["auth"])


async def _visible_templates(session, employee: Employee) -> list[Template]:
    """Rolga biriktirilgan va nashr etilgan shablonlar (qoralama ko'rinmaydi)."""
    return await builder.visible_for(session, employee)


async def _issue(session, employee: Employee) -> schemas.AuthResponse:
    token, token_hash = new_refresh_token()
    session.add(
        RefreshToken(
            employee_id=employee.id,
            token_hash=token_hash,
            expires_at=utcnow() + dt.timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    await session.flush()
    templates = await _visible_templates(session, employee)
    return schemas.AuthResponse(
        access_token=create_access_token(
            employee.id, employee.role.code, employee.role.kind.value
        ),
        refresh_token=token,
        employee=serializers.employee_out(employee),
        templates=[serializers.template_out(tpl, employee.lang) for tpl in templates],
    )


@router.post("/auth/telegram", response_model=schemas.AuthResponse)
async def auth_telegram(payload: schemas.AuthRequest, session: SessionDep):
    parsed = validate_init_data(payload.init_data)
    tg_user = parsed["user"]

    employee = (
        await session.execute(
            sa.select(Employee).where(Employee.tg_user_id == int(tg_user["id"]))
        )
    ).scalar_one_or_none()
    if employee is None:
        raise NotInRegistry("Telegram akkaunt xodimga biriktirilmagan")
    if not employee.is_active:
        raise Forbidden("Xodim faol emas")

    await audit.log(
        session,
        action="auth.login",
        entity_type="employee",
        entity_id=employee.id,
        actor_id=employee.id,
        tg_user_id=employee.tg_user_id,
    )
    return await _issue(session, employee)


@router.post("/auth/refresh", response_model=schemas.AuthResponse)
async def refresh(payload: schemas.RefreshRequest, session: SessionDep):
    token_hash = hash_refresh_token(payload.refresh_token)
    row = (
        await session.execute(
            sa.select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None or as_utc(row.expires_at) < utcnow():
        raise Unauthenticated("refresh token yaroqsiz")

    employee = await session.get(Employee, row.employee_id)
    if employee is None or not employee.is_active:
        raise Unauthenticated("xodim faol emas")

    row.revoked_at = utcnow()  # rotatsiya
    return await _issue(session, employee)


@router.post("/auth/logout")
async def logout(payload: schemas.RefreshRequest, session: SessionDep):
    token_hash = hash_refresh_token(payload.refresh_token)
    await session.execute(
        sa.update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(revoked_at=utcnow())
    )
    return {"data": {"ok": True}}


@router.patch("/me", response_model=schemas.EmployeeOut)
async def update_me(
    payload: schemas.MeUpdate, session: SessionDep, employee: EmployeeDep
):
    """Hozircha faqat til — qolgan profil ma'lumotini admin boshqaradi."""
    if payload.lang in ("uz", "ru"):
        employee.lang = payload.lang
        await session.flush()
    return serializers.employee_out(employee)


@router.get("/me", response_model=schemas.AuthResponse)
async def me(session: SessionDep, employee: EmployeeDep):
    templates = await _visible_templates(session, employee)
    return schemas.AuthResponse(
        access_token="",
        refresh_token="",
        employee=serializers.employee_out(employee),
        templates=[serializers.template_out(tpl, employee.lang) for tpl in templates],
    )
