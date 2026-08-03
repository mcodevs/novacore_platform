"""ADR-0017 — foto **faqat kameradan**, galereya yopiq.

Galereya tugmasi Mini App'dan olib tashlangan, lekin klientga ishonilmaydi:
API ham `source=gallery` ni rad etishi kerak.
"""

from __future__ import annotations

import pytest
from fastapi import UploadFile

from app.api.v1 import media as media_api
from app.core.errors import ValidationFailed
from app.db.models import MediaSource
from app.domain.submission import service as submission_service
from tests.conftest import get_template, make_employee

JPEG = b"\xff\xd8\xff\xe0" + bytes(64)


async def _draft(session):
    employee = await make_employee(session, role_code="mechanic")
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, employee, template)
    return employee, submission


async def test_gallery_upload_is_rejected(session, tmp_path):
    """Galereyadan yuklash API darajasida bloklanadi."""
    import io

    employee, submission = await _draft(session)
    upload = UploadFile(filename="a.jpg", file=io.BytesIO(JPEG))

    with pytest.raises(ValidationFailed):
        await media_api.upload(
            session=session,
            employee=employee,
            submission_id=submission.id,
            field_code="photo_problem",
            kind="problem",
            source=MediaSource.gallery.value,
            file=upload,
        )


def test_gallery_source_still_exists_for_history():
    """Eski yozuvlar uchun `gallery` enum qiymati saqlanadi — o'chirilmaydi."""
    assert MediaSource.gallery.value == "gallery"
