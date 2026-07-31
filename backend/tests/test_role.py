"""Rol modeli testlari — R3 (tayanch narx yopiqligi), `kind` ruxsatlari, R8."""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from app.core.errors import Forbidden, LastAdminRequired, PriceReferenceHidden
from app.db.models import EmployeeStatus, Role, RoleKind, RoleTemplate, Template
from app.domain.role import permissions
from app.domain.submission import service as submission_service
from tests.conftest import create_ready_submission, get_role, make_employee, make_vehicle


async def test_seed_roles_have_only_three_kinds(session):
    roles = list((await session.execute(sa.select(Role))).scalars().all())
    kinds = {role.kind for role in roles}
    assert kinds <= {RoleKind.reporter, RoleKind.admin, RoleKind.accountant}
    assert {r.code for r in roles} == {"mechanic", "supplier", "admin", "accountant"}


async def test_role_defines_visible_templates(session):
    """Rol = nom + qaysi shablonlarni ko'radi."""
    mechanic_role = await get_role(session, "mechanic")
    codes = [rt.template.code for rt in mechanic_role.templates]
    assert codes == ["car_repair"]

    supplier_role = await get_role(session, "supplier")
    assert [rt.template.code for rt in supplier_role.templates] == ["part_purchase"]

    accountant_role = await get_role(session, "accountant")
    assert accountant_role.templates == []


async def test_new_role_needs_no_code(session):
    """Yangi rol qo'shish = bazaga yozuv. Kod yozilmaydi, deploy qilinmaydi."""
    template = (
        await session.execute(sa.select(Template).where(Template.code == "car_repair"))
    ).scalar_one()
    electrician = Role(
        code="electrician",
        name_uz="Elektrik",
        name_ru="Электрик",
        icon="⚡",
        kind=RoleKind.reporter,
    )
    session.add(electrician)
    await session.flush()
    session.add(RoleTemplate(role_id=electrician.id, template_id=template.id))
    await session.flush()

    employee = await make_employee(session, role_code="mechanic")
    employee.role_id = electrician.id
    await session.flush()
    await session.refresh(employee)

    assert employee.role.name("uz") == "Elektrik"
    assert permissions.can_create_submission(employee) is True
    assert permissions.can_review(employee) is False


async def test_reference_price_hidden_from_reporter(session):
    """R3 — klientda yashirish yetarli emas, serverda ham yopiladi."""
    mechanic = await make_employee(session, role_code="mechanic")
    admin = await make_employee(session, role_code="admin")
    accountant = await make_employee(session, role_code="accountant")

    assert permissions.can_see_reference_price(mechanic) is False
    assert permissions.can_see_reference_price(admin) is True
    assert permissions.can_see_reference_price(accountant) is True

    with pytest.raises(PriceReferenceHidden):
        permissions.ensure_reference_price_visible(mechanic)


async def test_kind_permission_matrix(session):
    mechanic = await make_employee(session, role_code="mechanic")
    admin = await make_employee(session, role_code="admin")
    accountant = await make_employee(session, role_code="accountant")

    assert permissions.can_create_submission(mechanic) is True
    assert permissions.can_create_submission(admin) is True  # admin ham yozadi
    assert permissions.can_create_submission(accountant) is False

    assert permissions.can_review(admin) is True
    assert permissions.can_review(mechanic) is False
    assert permissions.can_review(accountant) is False

    assert permissions.can_see_all_submissions(accountant) is True
    assert permissions.can_see_all_submissions(mechanic) is False

    assert permissions.can_close_period(accountant) is True
    assert permissions.can_close_period(mechanic) is False


async def test_reporter_sees_only_own_submissions(session):
    author = await make_employee(session, role_code="mechanic", name="Karimov")
    other = await make_employee(session, role_code="mechanic", name="Sobirov")
    accountant = await make_employee(session, role_code="accountant")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, author, vehicle)

    assert permissions.can_view_submission(author, submission) is True
    assert permissions.can_view_submission(other, submission) is False
    assert permissions.can_view_submission(accountant, submission) is True

    with pytest.raises(Forbidden):
        await submission_service.get_for_actor(session, submission.id, other)


async def test_accountant_cannot_create_submission(session):
    accountant = await make_employee(session, role_code="accountant")
    from tests.conftest import get_template

    template = await get_template(session, "car_repair")
    with pytest.raises(Forbidden):
        await submission_service.create_draft(session, accountant, template)


async def test_last_admin_cannot_be_removed(session):
    """R8 — kamida bitta faol admin qolishi shart."""
    only_admin = await make_employee(session, role_code="admin")
    mechanic_role = await get_role(session, "mechanic")

    with pytest.raises(LastAdminRequired):
        await permissions.ensure_admin_remains(
            session, changing_employee_id=only_admin.id, new_role_id=mechanic_role.id
        )

    second_admin = await make_employee(session, role_code="admin", name="Admin B.")
    await permissions.ensure_admin_remains(
        session, changing_employee_id=only_admin.id, new_role_id=mechanic_role.id
    )

    # ikkinchi admin bloklansa — yana yagona admin qoladi
    second_admin.status = EmployeeStatus.blocked
    await session.flush()
    with pytest.raises(LastAdminRequired):
        await permissions.ensure_admin_remains(
            session, changing_employee_id=only_admin.id, new_role_id=mechanic_role.id
        )


async def test_promotion_to_admin_satisfies_r8(session):
    admin = await make_employee(session, role_code="admin")
    admin_role = await get_role(session, "admin")

    # adminni... adminga o'zgartirish — qoida buzilmaydi
    await permissions.ensure_admin_remains(
        session, changing_employee_id=admin.id, new_role_id=admin_role.id
    )
