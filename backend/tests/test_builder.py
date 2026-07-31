"""Shablon va rol konstruktori (Faza 2).

Asosiy talab (docs/02-architecture/03-report-templates.md §5): shablon
o'zgarganda **eski hisobotlar buzilmasin**. Konstruktorni AI yozgani uchun
versiyalash testsiz ishonchsiz — bu yerda u uchidan-uchiga tekshiriladi.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from app.core.errors import BusinessRuleViolated, LastAdminRequired, ValidationFailed
from app.db.models import RoleTemplate, Template, TemplateVersion
from app.domain.role import permissions
from app.domain.submission import service as submission_service
from app.domain.template import builder, engine
from tests.conftest import add_photo, get_role, get_template, make_employee, make_vehicle


def wash_definition(**overrides) -> dict:
    """«Yuvish» shabloni — hujjatdagi misol (04-roles-and-templates.md §3)."""
    definition = {
        "code": "car_wash",
        "name": {"uz": "Yuvish hisoboti", "ru": "Отчёт о мойке"},
        "icon": "🧼",
        "subject_type": "vehicle",
        "has_money": True,
        "negotiable": True,
        "field_mapping": {"vehicle": "plate"},
        "sections": [{"code": "main", "title": {"uz": "Yuvish"}}],
        "fields": [
            {
                "code": "plate",
                "section": "main",
                "label": {"uz": "Mashina raqami", "ru": "Гос. номер"},
                "type": "vehicle_picker",
                "required": True,
            },
            {
                "code": "photo_after",
                "section": "main",
                "label": {"uz": "Yuvishdan keyin"},
                "type": "photo",
                "required": True,
                "options": {"min": 1, "max": 3, "camera_only": True},
            },
            {
                "code": "works",
                "section": "main",
                "label": {"uz": "Bajarilgan ishlar"},
                "type": "lines",
                "required": True,
                "options": {"kind": "labor", "allow_custom": True},
            },
        ],
    }
    definition.update(overrides)
    return definition


# --- Qoralama va nashr -------------------------------------------------------


async def test_new_template_is_draft_and_invisible(session):
    """Nashr etilmagan shablon hech kimga ko'rinmaydi va ishlatilmaydi."""
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    template = await builder.create(session, admin, wash_definition())

    assert template.version == 1
    assert await builder.is_published(session, template) is False
    assert await builder.latest_published_version(session, template.id) is None

    # rolga biriktirilsa ham — qoralama ro'yxatga tushmaydi
    role = await get_role(session, "mechanic")
    session.add(RoleTemplate(role_id=role.id, template_id=template.id, sort=99))
    await session.flush()

    mechanic = await make_employee(session, role_code="mechanic")
    codes = [t.code for t in await builder.visible_for(session, mechanic)]
    assert codes == ["car_repair"]

    with pytest.raises(BusinessRuleViolated):
        await submission_service.create_draft(session, mechanic, template)


async def test_publish_makes_template_usable(session):
    """Nashrdan keyin: snapshot yoziladi, rol uni ko'radi, hisobot ochiladi."""
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    template = await builder.create(session, admin, wash_definition())
    await builder.publish(session, admin, template)

    snapshot = (
        await session.execute(
            sa.select(TemplateVersion).where(
                TemplateVersion.template_id == template.id, TemplateVersion.version == 1
            )
        )
    ).scalar_one()
    assert snapshot.published_by == admin.id
    assert [f["code"] for f in snapshot.schema_json["fields"]] == [
        "plate",
        "photo_after",
        "works",
    ]

    role = await get_role(session, "mechanic")
    session.add(RoleTemplate(role_id=role.id, template_id=template.id, sort=99))
    await session.flush()

    mechanic = await make_employee(session, role_code="mechanic")
    assert "car_wash" in [t.code for t in await builder.visible_for(session, mechanic)]

    submission = await submission_service.create_draft(session, mechanic, template)
    assert submission.template_version == 1


async def test_publishing_twice_is_rejected(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    template = await builder.create(session, admin, wash_definition())
    await builder.publish(session, admin, template)

    with pytest.raises(BusinessRuleViolated):
        await builder.publish(session, admin, template)


# --- ⭐ Versiyalash: eski hisobot buzilmasin ----------------------------------


async def test_editing_published_template_does_not_break_old_submissions(session):
    """v1 dagi hisobot v2 nashr etilgach ham **o'z yorliqlari** bilan qoladi."""
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    template = await builder.create(session, admin, wash_definition())
    await builder.publish(session, admin, template)

    role = await get_role(session, "mechanic")
    session.add(RoleTemplate(role_id=role.id, template_id=template.id, sort=99))
    await session.flush()
    mechanic = await make_employee(session, role_code="mechanic")

    old = await submission_service.create_draft(session, mechanic, template)
    assert old.template_version == 1

    # admin maydonni qayta nomlaydi va bittasini o'chiradi
    changed = wash_definition()
    changed["fields"][1]["label"] = {"uz": "Yuvishdan keyingi foto"}
    changed["fields"] = changed["fields"][:2]  # `works` olib tashlandi
    await builder.update(session, admin, template, changed)

    assert template.version == 2
    assert await builder.is_published(session, template) is False  # yangi qoralama

    # eski hisobot — v1 sxemasi bilan
    old_schema = await engine.schema_for_submission(session, old)
    assert old_schema.version == 1
    assert old_schema.get("photo_after").label_uz == "Yuvishdan keyin"
    assert old_schema.get("works") is not None  # o'chirilgan maydon arxivda qoladi

    # v1 snapshot'i ustidan yozilmagan
    v1 = (
        await session.execute(
            sa.select(TemplateVersion).where(
                TemplateVersion.template_id == template.id, TemplateVersion.version == 1
            )
        )
    ).scalar_one()
    assert len(v1.schema_json["fields"]) == 3


async def test_new_submissions_use_published_version_not_draft(session):
    """Qoralama tahrir yangi hisobotlarga ta'sir qilmaydi — nashrgacha."""
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    template = await builder.create(session, admin, wash_definition())
    await builder.publish(session, admin, template)

    role = await get_role(session, "mechanic")
    session.add(RoleTemplate(role_id=role.id, template_id=template.id, sort=99))
    await session.flush()
    mechanic = await make_employee(session, role_code="mechanic")

    await builder.update(session, admin, template, wash_definition(icon="🚿"))
    assert template.version == 2

    during_draft = await submission_service.create_draft(session, mechanic, template)
    assert during_draft.template_version == 1  # hali v1

    await builder.publish(session, admin, template)
    after_publish = await submission_service.create_draft(session, mechanic, template)
    assert after_publish.template_version == 2


# --- Validatsiya -------------------------------------------------------------


@pytest.mark.parametrize(
    ("mutation", "field_key"),
    [
        pytest.param({"code": "Car Wash"}, "code", id="invalid_code"),
        pytest.param({"name": {"uz": "  "}}, "name", id="empty_name"),
        pytest.param({"fields": []}, "fields", id="no_fields"),
        pytest.param({"subject_type": "spaceship"}, "subject_type", id="bad_subject"),
    ],
)
async def test_definition_validation_rejects(session, mutation, field_key):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    with pytest.raises(ValidationFailed) as exc:
        await builder.create(session, admin, wash_definition(**mutation))
    assert field_key in exc.value.fields


async def test_unsupported_field_type_is_rejected(session):
    """Hujjatda tur bor, lekin renderer chizolmasa — forma to'ldirilmaydi."""
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    broken = wash_definition()
    broken["fields"][0]["type"] = "signature"  # hali qo'llab-quvvatlanmaydi

    with pytest.raises(ValidationFailed) as exc:
        await builder.create(session, admin, broken)
    assert exc.value.fields["fields.0.type"] == "unsupported_type"


async def test_duplicate_field_code_is_rejected(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    broken = wash_definition()
    broken["fields"][1]["code"] = "plate"

    with pytest.raises(ValidationFailed) as exc:
        await builder.create(session, admin, broken)
    assert exc.value.fields["fields.1.code"] == "duplicate_code"


async def test_field_mapping_must_point_to_existing_field(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    broken = wash_definition(field_mapping={"vehicle": "nonexistent"})

    with pytest.raises(ValidationFailed) as exc:
        await builder.create(session, admin, broken)
    assert exc.value.fields["field_mapping.vehicle"] == "unknown_field"


async def test_unknown_mapping_key_is_rejected(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    broken = wash_definition(field_mapping={"salary": "plate"})

    with pytest.raises(ValidationFailed) as exc:
        await builder.create(session, admin, broken)
    assert "field_mapping.salary" in exc.value.fields


async def test_visible_if_must_reference_existing_field(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    broken = wash_definition()
    broken["fields"][1]["visible_if"] = {"field": "ghost", "equals": True}

    with pytest.raises(ValidationFailed) as exc:
        await builder.create(session, admin, broken)
    assert exc.value.fields["fields.1.visible_if"] == "unknown_field"


async def test_unknown_section_is_rejected(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    broken = wash_definition()
    broken["fields"][0]["section"] = "nowhere"

    with pytest.raises(ValidationFailed) as exc:
        await builder.create(session, admin, broken)
    assert exc.value.fields["fields.0.section"] == "unknown_section"


async def test_duplicate_template_code_is_rejected(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    with pytest.raises(BusinessRuleViolated):
        await builder.create(session, admin, wash_definition(code="car_repair"))


async def test_template_code_is_immutable(session):
    """Rollar shablonga kod orqali tayanadi — kod o'zgarmaydi."""
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    template = await builder.create(session, admin, wash_definition())
    await builder.update(session, admin, template, wash_definition(code="renamed"))
    assert template.code == "car_wash"


# --- Rol konstruktori (R8) ---------------------------------------------------


async def test_last_admin_role_kind_cannot_change(session):
    """R8 — yagona admin rolini `reporter`ga aylantirib bo'lmaydi."""
    await make_employee(session, role_code="admin", name="Admin A.")
    admin_role = await get_role(session, "admin")

    with pytest.raises(LastAdminRequired):
        await permissions.ensure_admin_remains_without_role(session, admin_role)


async def test_admin_role_kind_can_change_when_another_admin_role_exists(session):
    from app.db.models import Role, RoleKind

    await make_employee(session, role_code="admin", name="Admin A.")
    spare = Role(
        code="director", name_uz="Direktor", name_ru="Директор", kind=RoleKind.admin
    )
    session.add(spare)
    await session.flush()
    await make_employee(session, role_code="director", name="Direktor D.")

    admin_role = await get_role(session, "admin")
    await permissions.ensure_admin_remains_without_role(session, admin_role)  # xato yo'q


async def test_reporter_role_change_is_not_guarded(session):
    mechanic_role = await get_role(session, "mechanic")
    await permissions.ensure_admin_remains_without_role(session, mechanic_role)


# --- Uchidan-uchiga: yangi rol + shablon (Faza 2 chiqish mezoni) --------------


async def test_new_role_with_new_template_works_end_to_end(session):
    """«Admin 30 daqiqada yangi rol yaratadi va u ishlaydi» — kod yozmasdan."""
    from app.db.models import Role, RoleKind

    admin = await make_employee(session, role_code="admin", name="Admin A.")

    template = await builder.create(session, admin, wash_definition())
    await builder.publish(session, admin, template)

    washer_role = Role(
        code="washer", name_uz="Yuvuvchi", name_ru="Мойщик", icon="🧼", kind=RoleKind.reporter
    )
    session.add(washer_role)
    await session.flush()
    session.add(RoleTemplate(role_id=washer_role.id, template_id=template.id, sort=10))
    await session.flush()

    washer = await make_employee(session, role_code="washer", name="Yuvuvchi Y.")
    assert [t.code for t in await builder.visible_for(session, washer)] == ["car_wash"]

    vehicle = await make_vehicle(session, "01A777AA")
    submission = await submission_service.create_draft(session, washer, template)
    assert submission.template_version == 1

    # forma yangi shablon bo'yicha chiziladi — yadro kodi o'zgarmagan
    schema = await engine.schema_for_submission(session, submission)
    assert [f.code for f in schema.fields] == ["plate", "photo_after", "works"]
    assert engine.next_field(schema, submission).code == "plate"

    engine.set_value(submission, "plate", {"vehicle_id": vehicle.id})
    await submission_service.attach_vehicle(session, submission, vehicle)
    await session.flush()
    assert submission.subject_vehicle_id == vehicle.id


async def test_seeded_templates_stay_published(session):
    """Seed shablonlari nashr etilgan holatda bo'lishi shart (regressiya)."""
    for code in ("car_repair", "part_purchase"):
        template = await get_template(session, code)
        assert await builder.is_published(session, template) is True
        assert await builder.usable_version(session, template) == template.version


async def test_to_definition_roundtrips_through_engine(session):
    """`to_definition` → `schema_from_json` — nashr snapshot'i o'qilishi kerak."""
    template = await get_template(session, "car_repair")
    schema = engine.schema_from_json(builder.to_definition(template))
    assert schema.code == "car_repair"
    assert schema.get("works").line_kind.value == "labor"
    assert [f.code for f in schema.fields] == [
        f.code for f in engine.schema_from_template(template).fields
    ]


# --- Bog'liq hisobotlar: qism xaridi ↔ ta'mir (Faza 2) ------------------------


async def test_part_purchase_links_to_repair_report(session):
    """Ta'minotchi xaridni **ustaning** ta'mir hisobotiga biriktiradi."""
    from app.db.models import LineKind

    mechanic = await make_employee(session, role_code="mechanic", name="Usta U.")
    supplier = await make_employee(session, role_code="supplier", name="Ta'minotchi T.")
    vehicle = await make_vehicle(session, "01A500BB")

    from tests.conftest import create_ready_submission

    repair = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, repair, mechanic)

    # ta'minotchi nomzodlar ro'yxatini ko'radi (o'zi muallif bo'lmasa ham)
    options = await submission_service.linkable(
        session, supplier, template_code="car_repair", vehicle_id=vehicle.id
    )
    assert [s.id for s in options] == [repair.id]

    purchase_tpl = await get_template(session, "part_purchase")
    purchase = await submission_service.create_draft(session, supplier, purchase_tpl)
    engine.set_value(purchase, "plate", {"vehicle_id": vehicle.id})
    await submission_service.attach_vehicle(session, purchase, vehicle)
    engine.set_value(purchase, "repair_link", {"submission_id": repair.id})
    engine.set_value(purchase, "supplier", "Avto-Parts MChJ")
    engine.set_value(purchase, "is_original", True)
    await add_photo(session, purchase, supplier, "photo_receipt")
    await submission_service.add_line(
        session,
        purchase,
        supplier,
        kind=LineKind.part,
        name="Tormoz kolodkasi",
        qty=1,
        unit_price=180000,
    )
    engine.mark_done(purchase, "parts")
    await submission_service.mark_left(session, purchase, supplier)
    await submission_service.submit(session, purchase, supplier)

    assert purchase.related_submission_id == repair.id  # field_mapping ishladi
    assert purchase.parts_amount == 180000


async def test_reporter_cannot_browse_all_submissions_via_picker(session):
    """Mashina ko'rsatilmasa — reporter butun bazani varaqlay olmaydi."""
    supplier = await make_employee(session, role_code="supplier", name="Ta'minotchi T.")
    with pytest.raises(BusinessRuleViolated):
        await submission_service.linkable(session, supplier, template_code="car_repair")


async def test_admin_can_browse_linkable_without_vehicle(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    assert await submission_service.linkable(session, admin) == []


async def test_drafts_are_not_linkable(session):
    """Yuborilmagan qoralamaga bog'lab bo'lmaydi."""
    mechanic = await make_employee(session, role_code="mechanic", name="Usta U.")
    supplier = await make_employee(session, role_code="supplier", name="Ta'minotchi T.")
    vehicle = await make_vehicle(session, "01A501BB")

    template = await get_template(session, "car_repair")
    draft = await submission_service.create_draft(session, mechanic, template)
    await submission_service.attach_vehicle(session, draft, vehicle)

    options = await submission_service.linkable(
        session, supplier, template_code="car_repair", vehicle_id=vehicle.id
    )
    assert options == []


async def test_part_purchase_seed_is_v2_with_link_field(session):
    """Seed v2 ga ko'tarildi (v1 snapshot'i ustidan yozilmasin uchun).

    Ishlab turgan bazada v1 snapshot'i saqlanib qoladi va undagi hisobotlar
    o'z sxemasida ochiladi — buni `test_editing_published_template_…` tekshiradi.
    """
    template = await get_template(session, "part_purchase")
    assert template.version == 2
    assert await builder.is_published(session, template) is True

    v2 = await engine.load_schema(session, template.id, 2)
    assert v2.get("repair_link").type == "submission_picker"
    assert v2.get("repair_link").options["template_code"] == "car_repair"
    assert v2.field_mapping["related_submission"] == "repair_link"
