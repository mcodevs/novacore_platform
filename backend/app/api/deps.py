"""FastAPI dependency'lari — har so'rovda rol va status qayta tekshiriladi."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden, Unauthenticated
from app.core.security import decode_access_token
from app.db.models import Employee, RoleKind
from app.db.session import get_session


async def db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(db_session)]


async def current_employee(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Employee:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthenticated("token yo'q")
    payload = decode_access_token(authorization.split(" ", 1)[1])

    employee = await session.get(Employee, int(payload["sub"]))
    if employee is None or not employee.is_active:
        raise Unauthenticated("xodim faol emas")
    return employee


EmployeeDep = Annotated[Employee, Depends(current_employee)]


def require_kind(*kinds: RoleKind):  # noqa: ANN201
    async def _dependency(employee: EmployeeDep) -> Employee:
        if employee.role.kind not in kinds:
            raise Forbidden("Ruxsat yo'q")
        return employee

    return _dependency


AdminDep = Annotated[Employee, Depends(require_kind(RoleKind.admin))]
FinanceDep = Annotated[Employee, Depends(require_kind(RoleKind.admin, RoleKind.accountant))]
