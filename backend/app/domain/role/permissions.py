"""Ruxsatlar — `role.kind` + biznes qoida. Boshqa hech narsa.

⚠️ `permissions` / `role_permissions` jadvallari YO'Q va bo'lmaydi
(docs/01-product/01-roles-and-permissions.md §4).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    Forbidden,
    LastAdminRequired,
    PriceReferenceHidden,
    SelfApprovalForbidden,
)
from app.db.models import Employee, EmployeeStatus, Role, RoleKind, Submission


def kind_of(employee: Employee) -> RoleKind:
    return employee.role.kind


def is_admin(employee: Employee) -> bool:
    return kind_of(employee) == RoleKind.admin


def is_accountant(employee: Employee) -> bool:
    return kind_of(employee) == RoleKind.accountant


def is_reporter(employee: Employee) -> bool:
    return kind_of(employee) == RoleKind.reporter


def require_kind(employee: Employee, *kinds: RoleKind) -> None:
    if kind_of(employee) not in kinds:
        raise Forbidden("Bu amal sizning rolingizga ruxsat etilmagan")


def can_create_submission(employee: Employee) -> bool:
    """Bazaviy imkoniyat: reporter ham, admin ham hisobot yozadi. Buxgalter — yo'q."""
    return kind_of(employee) in (RoleKind.reporter, RoleKind.admin)


def can_review(employee: Employee) -> bool:
    """Tasdiqlash / narx kelishuvi — faqat admin."""
    return is_admin(employee)


def can_see_all_submissions(employee: Employee) -> bool:
    return kind_of(employee) in (RoleKind.admin, RoleKind.accountant)


def can_see_reference_price(employee: Employee) -> bool:
    """R3 — tayanch narx va narx tarixi `reporter` roliga berilmaydi."""
    return kind_of(employee) in (RoleKind.admin, RoleKind.accountant)


def ensure_reference_price_visible(employee: Employee) -> None:
    """R3 — klientda yashirish yetarli emas, API'da ham bloklanadi."""
    if not can_see_reference_price(employee):
        raise PriceReferenceHidden("Tayanch narx ko'rsatilmaydi")


def can_close_period(employee: Employee) -> bool:
    return kind_of(employee) in (RoleKind.admin, RoleKind.accountant)


def can_export(employee: Employee) -> bool:
    return kind_of(employee) in (RoleKind.admin, RoleKind.accountant)


def is_author(employee: Employee, submission: Submission) -> bool:
    return submission.author_id == employee.id or employee.id in (submission.co_authors or [])


def can_view_submission(employee: Employee, submission: Submission) -> bool:
    return can_see_all_submissions(employee) or is_author(employee, submission)


def ensure_can_view_submission(employee: Employee, submission: Submission) -> None:
    if not can_view_submission(employee, submission):
        raise Forbidden("Bu hisobotni ko'rish huquqingiz yo'q")


def ensure_not_self_approval(actor: Employee, submission: Submission) -> None:
    """R1 — hech kim o'z hisobotini **qo'lda** tasdiqlay olmaydi."""
    if submission.author_id == actor.id:
        raise SelfApprovalForbidden("O'z hisobotingizni qo'lda tasdiqlay olmaysiz")


async def ensure_admin_remains_without_role(session: AsyncSession, role: Role) -> None:
    """R8 — rolning turi o'zgarsa yoki u o'chirilsa, boshqa admin qoladimi.

    Rol konstruktori (Faza 2): `kind='admin'` rolni `reporter`ga aylantirish shu
    roldagi **barcha** xodimlarni bir vaqtda admin huquqidan mahrum qiladi.
    """
    if role.kind != RoleKind.admin:
        return

    stmt = (
        sa.select(sa.func.count(Employee.id))
        .join(Role, Role.id == Employee.role_id)
        .where(
            Role.kind == RoleKind.admin,
            Role.id != role.id,
            Employee.status == EmployeeStatus.active,
            Employee.deleted_at.is_(None),
        )
    )
    if (await session.execute(stmt)).scalar_one() < 1:
        raise LastAdminRequired("Bu yagona admin rol — turini o'zgartirib bo'lmaydi")


async def ensure_admin_remains(
    session: AsyncSession, *, changing_employee_id: int, new_role_id: int | None = None
) -> None:
    """R8 — kamida bitta faol `kind='admin'` rolli xodim qolishi shart."""
    stmt = (
        sa.select(sa.func.count(Employee.id))
        .join(Role, Role.id == Employee.role_id)
        .where(
            Role.kind == RoleKind.admin,
            Employee.status == EmployeeStatus.active,
            Employee.deleted_at.is_(None),
            Employee.id != changing_employee_id,
        )
    )
    remaining = (await session.execute(stmt)).scalar_one()

    if new_role_id is not None:
        new_role = await session.get(Role, new_role_id)
        if new_role is not None and new_role.kind == RoleKind.admin:
            remaining += 1

    if remaining < 1:
        raise LastAdminRequired("Kamida bitta faol admin bo'lishi shart")
