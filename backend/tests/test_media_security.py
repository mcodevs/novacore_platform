"""Media xavfsizligi — kod ko'rigida (PR #1) topilgan kamchiliklar.

`field_code` multipart so'rovdan keladi va storage kalitiga kiradi. Tekshiruvsiz
`../../` bilan MEDIA_ROOT dan chiqib ketish mumkin edi.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.config import settings
from app.core.errors import ValidationFailed
from app.db.models import MediaKind
from app.domain.media import service as media_service
from app.integrations.storage.local import LocalStorage
from tests.conftest import get_template, make_employee, make_vehicle
from app.domain.submission import service as submission_service

JPEG = b"\xff\xd8\xff\xe0" + bytes(64)


async def _draft(session):
    employee = await make_employee(session, role_code="mechanic")
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, employee, template)
    return employee, submission


@pytest.mark.parametrize(
    "field_code",
    [
        "../../../../tmp/evil",
        "../photo_problem",
        "photo/../../../etc/passwd",
        "photo problem",
        "PHOTO_PROBLEM",
        "",
        "a" * 80,
    ],
)
async def test_dangerous_field_codes_are_rejected(session, field_code):
    employee, submission = await _draft(session)
    with pytest.raises(ValidationFailed):
        await media_service.store_bytes(
            session,
            submission=submission,
            uploader=employee,
            field_code=field_code,
            data=JPEG,
            kind=MediaKind.problem,
        )


async def test_field_code_must_exist_in_template(session):
    """Shakli to'g'ri, lekin shablonda yo'q — baribir rad etiladi."""
    employee, submission = await _draft(session)
    with pytest.raises(ValidationFailed):
        await media_service.store_bytes(
            session,
            submission=submission,
            uploader=employee,
            field_code="some_other_field",
            data=JPEG,
        )


async def test_non_media_field_is_rejected(session):
    """`comment` — matn maydoni, unga foto biriktirib bo'lmaydi."""
    employee, submission = await _draft(session)
    with pytest.raises(ValidationFailed):
        await media_service.store_bytes(
            session, submission=submission, uploader=employee, field_code="comment", data=JPEG
        )


async def test_valid_field_code_is_accepted(session):
    employee, submission = await _draft(session)
    media = await media_service.store_bytes(
        session,
        submission=submission,
        uploader=employee,
        field_code="photo_problem",
        data=JPEG,
        kind=MediaKind.problem,
    )
    assert media.field_code == "photo_problem"
    assert media.storage_key.startswith("submissions/")
    assert ".." not in media.storage_key


def test_local_storage_blocks_escaping_the_root(tmp_path):
    storage = LocalStorage(str(tmp_path / "media"))
    with pytest.raises(ValueError):
        storage._path("../../evil.jpg")
    inside = storage._path("submissions/2026/07/31/1/photo-abc.jpg")
    assert inside.is_relative_to((tmp_path / "media").resolve())


async def test_local_view_url_points_to_existing_endpoint(session):
    """Lokal omborda `media_out().url` haqiqiy endpointga ishora qilishi kerak."""
    employee, submission = await _draft(session)
    media = await media_service.store_bytes(
        session,
        submission=submission,
        uploader=employee,
        field_code="photo_problem",
        data=JPEG,
    )
    url = media_service.view_url(media)
    assert settings.storage_backend == "local"
    assert url.endswith(f"/api/v1/media/{media.id}/raw")


async def test_vehicle_moves_to_service_when_attached(session):
    """Mashina biriktirilganda IN_SERVICE ga o'tadi (bot va API bir xil)."""
    from app.db.models import VehicleStatus

    employee, submission = await _draft(session)
    vehicle = await make_vehicle(session, plate="01777AAA")
    assert vehicle.status == VehicleStatus.active

    await submission_service.attach_vehicle(session, submission, vehicle)
    assert vehicle.status == VehicleStatus.in_service
    assert submission.subject_vehicle_id == vehicle.id
    assert Decimal("0") == submission.proposed_labor_amount
