"""ADR-0020 — foto **kameradan ham, galereyadan ham**.

ADR-0017 (faqat kamera) almashtirildi: `capture="environment"` iOS WebView'da
kamerani ochmasligi mumkin edi, zaxira yo'l esa umuman yo'q edi — foto yuklab
bo'lmasa, ta'mir hisoboti ham yuborilmasdi.

Manba **rad etilmaydi**, lekin **yozib qo'yiladi**: klient aytgan qiymatga
ishonib bo'lmaydi, ammo tekshiruvda foydali.
"""

from __future__ import annotations

import io

from fastapi import UploadFile

from app.api.v1 import media as media_api
from app.db.models import Media, MediaSource
from app.domain.submission import service as submission_service
from tests.conftest import get_template, make_employee

JPEG = b"\xff\xd8\xff\xe0" + bytes(64)


async def _draft(session):
    employee = await make_employee(session, role_code="mechanic")
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, employee, template)
    return employee, submission


async def _upload(session, employee, submission, source: str):
    return await media_api.upload(
        session=session,
        employee=employee,
        submission_id=submission.id,
        field_code="photo_problem",
        kind="problem",
        source=source,
        file=UploadFile(filename="a.jpg", file=io.BytesIO(JPEG)),
    )


async def test_gallery_upload_is_accepted(session, tmp_path):
    """Galereyadan yuklash ishlaydi — ilgari API uni rad etardi."""
    employee, submission = await _draft(session)
    out = await _upload(session, employee, submission, MediaSource.gallery.value)
    assert out.id is not None


async def test_source_is_recorded(session, tmp_path):
    """Qaysi tugma bosilgani saqlanadi — taqiq o'rniga iz."""
    employee, submission = await _draft(session)
    gallery = await _upload(session, employee, submission, MediaSource.gallery.value)
    camera = await _upload(session, employee, submission, MediaSource.camera.value)

    assert (await session.get(Media, gallery.id)).source == MediaSource.gallery
    assert (await session.get(Media, camera.id)).source == MediaSource.camera


def test_gallery_source_still_exists_for_history():
    """Eski yozuvlar uchun `gallery` enum qiymati saqlanadi — o'chirilmaydi."""
    assert MediaSource.gallery.value == "gallery"
