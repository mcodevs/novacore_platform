"""Audit log — hech qachon o'chirilmaydi va tahrirlanmaydi (R9)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


async def log(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    actor_id: int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip: str | None = None,
    tg_user_id: int | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        ip=ip,
        tg_user_id=tg_user_id,
    )
    session.add(entry)
    await session.flush()
    return entry
