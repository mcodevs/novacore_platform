"""Shablon dvigateli testlari — majburiy maydonlar, foto min/max, versiyalash."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.errors import ValidationFailed
from app.db.models import LineKind, TemplateVersion
from app.domain.submission import service as submission_service
from app.domain.template import engine
from tests.conftest import (
    add_photo,
    create_ready_submission,
    fill_valid_repair,
    get_template,
    make_employee,
    make_vehicle,
)


async def test_required_fields_block_submit(session):
    mechanic = await make_employee(session, role_code="mechanic")
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)

    with pytest.raises(ValidationFailed) as excinfo:
        await submission_service.submit(session, submission, mechanic)

    fields = excinfo.value.fields
    assert "plate" in fields
    assert "photo_car_before" in fields
    assert "works" in fields


async def test_photo_min_enforced(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)
    await fill_valid_repair(session, submission, mechanic, vehicle)

    # majburiy fotoni olib tashlaymiz
    engine.set_value(submission, "photo_problem", [])
    await session.flush()

    with pytest.raises(ValidationFailed) as excinfo:
        await submission_service.submit(session, submission, mechanic)
    assert excinfo.value.fields["photo_problem"] == "photo_need_more"


async def test_photo_max_enforced(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)
    await fill_valid_repair(session, submission, mechanic, vehicle)

    # photo_car_before: max = 2, uchinchisini qo'shamiz
    await add_photo(session, submission, mechanic, "photo_car_before", payload=b"second")
    await add_photo(session, submission, mechanic, "photo_car_before", payload=b"third")
    await session.flush()

    with pytest.raises(ValidationFailed) as excinfo:
        await submission_service.submit(session, submission, mechanic)
    assert excinfo.value.fields["photo_car_before"] == "photo_max_reached"


async def test_textarea_min_length(session):
    """Eng kam uzunlik 3 ta belgi (2026-08-05): ilgari 10 edi va usta «Tozalandi»
    deb yoza olmasdi. Tekshiruvning o'zi esa joyida qoladi — bo'sh «.» o'tmaydi."""
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)
    await fill_valid_repair(session, submission, mechanic, vehicle)
    engine.set_value(submission, "comment", "ok")
    await session.flush()

    with pytest.raises(ValidationFailed) as excinfo:
        await submission_service.submit(session, submission, mechanic)
    assert excinfo.value.fields["comment"] == "text_too_short"


async def test_lines_required(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)
    await fill_valid_repair(session, submission, mechanic, vehicle)

    await submission_service.remove_line(
        session, submission, mechanic, submission.lines[0].id
    )
    await submission_service.mark_left(session, submission, mechanic)

    with pytest.raises(ValidationFailed) as excinfo:
        await submission_service.submit(session, submission, mechanic)
    assert excinfo.value.fields["works"] == "lines_need_one"


async def test_field_mapping_promotes_columns(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(
        session,
        mechanic,
        vehicle,
        works=[("Ish 1", Decimal("150000")), ("Ish 2", Decimal("100000"))],
    )
    await submission_service.submit(session, submission, mechanic)

    assert submission.subject_vehicle_id == vehicle.id
    assert submission.proposed_labor_amount == Decimal("250000.00")
    assert submission.parts_amount == Decimal("0.00")
    assert submission.total_amount == Decimal("250000.00")


async def test_amounts_recalculated_from_lines(session):
    """R7 — klient hisobiga ishonilmaydi, summa qatorlardan qayta hisoblanadi."""
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)

    # "klient" yolg'on summa yubordi
    submission.proposed_labor_amount = Decimal("999999.00")
    await session.flush()

    await submission_service.submit(session, submission, mechanic)
    assert submission.proposed_labor_amount == Decimal("250000.00")


async def test_next_field_walks_the_form(session):
    """Bot ketma-ket forma uchun keyingi to'ldirilmagan maydonni oladi."""
    mechanic = await make_employee(session, role_code="mechanic")
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)
    schema = await engine.schema_for_submission(session, submission)

    first = engine.next_field(schema, submission)
    assert first is not None and first.code == "plate"

    engine.set_value(submission, "plate", {"vehicle_id": 1, "plate": "01A123BC"})
    second = engine.next_field(schema, submission)
    assert second is not None and second.code == "photo_car_before"


async def test_old_submission_uses_its_own_schema_version(session):
    """Versiyalash — shablon o'zgarsa eski hisobot buzilmasin.

    ⚠️ Test seed'dagi versiya raqamiga bog'lanmaydi: `car_repair` vaqti-vaqti
    bilan yangi versiyaga o'tadi (masalan 2026-08-05 da v2 — «Tavsiya» maydoni
    olib tashlandi). Muhimi — **eskisi o'z snapshot'ida qolishi**.
    """
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, submission, mechanic)

    template = await get_template(session, "car_repair")
    old_version = submission.template_version
    assert old_version == template.version  # yangi hisobot — joriy versiyada

    old_schema = await engine.load_schema(session, template.id, old_version)

    # shablon keyingi versiyaga o'tadi: yangi majburiy maydon qo'shildi
    raw = dict(old_schema.__dict__)
    next_version = old_version + 1
    new_json = {
        "code": "car_repair",
        "name": {"uz": "Ta'mir hisoboti (yangi)", "ru": "Отчёт (новый)"},
        "version": next_version,
        "fields": [
            {
                "code": "new_required",
                "type": "text",
                "label": {"uz": "Yangi maydon"},
                "required": True,
            }
        ],
    }
    session.add(
        TemplateVersion(template_id=template.id, version=next_version, schema_json=new_json)
    )
    template.version = next_version
    await session.flush()

    # eski hisobot hamon o'z versiyasidagi sxema bilan o'qiladi
    schema = await engine.schema_for_submission(session, submission)
    assert schema.version == old_version
    assert schema.get("comment") is not None
    assert schema.get("new_required") is None
    assert raw["code"] == "car_repair"

    # yangi hisobot esa keyingi versiyada ochiladi
    fresh = await submission_service.create_draft(session, mechanic, template)
    fresh_schema = await engine.schema_for_submission(session, fresh)
    assert fresh_schema.version == next_version
    assert fresh_schema.get("new_required") is not None


async def test_part_lines_do_not_touch_labor(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)

    await submission_service.add_line(
        session, submission, mechanic, kind=LineKind.part, name="Tormoz kolodka", qty=1
    )
    await session.refresh(submission)
    engine.recalculate_amounts(submission)

    assert submission.proposed_labor_amount == Decimal("250000.00")
    assert submission.parts_amount == Decimal("0.00")  # narxni usta kiritmaydi
