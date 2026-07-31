"""Bildirishnoma outbox — Postgres navbat, Redis yo'q (ADR-0004).

Yozuv shu yerda qo'shiladi, yuborish esa fon siklida (`app/tasks/worker.py`).
"""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import utcnow
from app.db.models import (
    Employee,
    EmployeeStatus,
    Notification,
    NotificationStatus,
    Role,
    RoleKind,
)


async def enqueue(
    session: AsyncSession,
    *,
    template_code: str,
    employee_id: int | None = None,
    chat_id: int | None = None,
    payload: dict | None = None,
    not_before: dt.datetime | None = None,
) -> Notification | None:
    if employee_id is None and chat_id is None:
        return None
    notification = Notification(
        employee_id=employee_id,
        chat_id=chat_id,
        template_code=template_code,
        payload=payload or {},
        status=NotificationStatus.pending,
        not_before=not_before or utcnow(),
    )
    session.add(notification)
    await session.flush()
    return notification


async def active_admin_ids(session: AsyncSession, *, exclude: int | None = None) -> list[int]:
    stmt = (
        sa.select(Employee.id)
        .join(Role, Role.id == Employee.role_id)
        .where(
            Role.kind == RoleKind.admin,
            Employee.status == EmployeeStatus.active,
            Employee.deleted_at.is_(None),
            Employee.tg_user_id.is_not(None),
        )
    )
    if exclude is not None:
        stmt = stmt.where(Employee.id != exclude)
    return list((await session.execute(stmt)).scalars().all())


async def notify_admins(
    session: AsyncSession,
    *,
    template_code: str,
    payload: dict,
    exclude_employee_id: int | None = None,
    include_group: bool = False,
) -> None:
    for employee_id in await active_admin_ids(session, exclude=exclude_employee_id):
        await enqueue(
            session,
            template_code=template_code,
            employee_id=employee_id,
            payload=payload,
        )
    if include_group and settings.admin_group_id:
        await enqueue(
            session,
            template_code=template_code,
            chat_id=settings.admin_group_id,
            payload=payload,
        )


async def notify_accountants(
    session: AsyncSession, *, template_code: str, payload: dict
) -> None:
    stmt = (
        sa.select(Employee.id)
        .join(Role, Role.id == Employee.role_id)
        .where(
            Role.kind == RoleKind.accountant,
            Employee.status == EmployeeStatus.active,
            Employee.deleted_at.is_(None),
            Employee.tg_user_id.is_not(None),
        )
    )
    for employee_id in (await session.execute(stmt)).scalars().all():
        await enqueue(
            session, template_code=template_code, employee_id=employee_id, payload=payload
        )
