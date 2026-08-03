"""Media — yuklash va vaqtinchalik ko'rish havolasi."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from app.api.deps import EmployeeDep, SessionDep
from app.api.v1 import schemas, serializers
from app.core.errors import NotFound, ValidationFailed
from app.db.models import MediaKind, MediaSource
from app.domain.media import service as media_service
from app.domain.submission import service as submission_service
from app.integrations.storage import get_storage

router = APIRouter(tags=["media"])


@router.post("/media/upload", response_model=schemas.MediaOut, status_code=201)
async def upload(
    session: SessionDep,
    employee: EmployeeDep,
    submission_id: int = Form(...),
    field_code: str = Form(...),
    kind: str = Form("other"),
    source: str = Form("unknown"),
    file: UploadFile = File(...),
):
    """Mini App fotoni siqib shu yerga yuboradi; server MIME'ni mazmuniga qarab tekshiradi.

    ⚠️ ADR-0017 — foto **faqat kameradan**. Galereya klientda olib tashlangan,
    lekin klientga ishonilmaydi: server ham `gallery` manbasini rad etadi.
    """
    if MediaSource(source) == MediaSource.gallery:
        raise ValidationFailed("Foto faqat kameradan olinadi (galereya yopiq)")

    submission = await submission_service.get_for_actor(session, submission_id, employee)
    submission_service.ensure_editable(submission, employee)

    payload = await file.read()
    media = await media_service.store_bytes(
        session,
        submission=submission,
        uploader=employee,
        field_code=field_code,
        data=payload,
        kind=MediaKind(kind),
        mime=file.content_type,
        source=MediaSource(source),
    )
    from app.domain.template import engine

    await session.refresh(submission)
    engine.append_media_id(submission, field_code, media.id)
    await session.flush()
    return serializers.media_out(media)


@router.get("/media/{media_id}", response_model=schemas.MediaOut)
async def get_media(media_id: int, session: SessionDep, employee: EmployeeDep):
    media = await media_service.get_for_actor(session, media_id, employee)
    return serializers.media_out(media)


@router.get("/media/{media_id}/raw")
async def raw_media(media_id: int, session: SessionDep, employee: EmployeeDep):
    """Lokal ombor rejimi uchun — S3'da signed URL ishlatiladi."""
    media = await media_service.get_for_actor(session, media_id, employee)
    payload = await get_storage().get(media.storage_key)
    return Response(content=payload, media_type=media.mime)


@router.delete("/media/{media_id}")
async def delete_media(media_id: int, session: SessionDep, employee: EmployeeDep):
    """Qo'lda o'chirish (admin) — metadata qoladi (R9)."""
    media = await media_service.get_for_actor(session, media_id, employee)
    if media is None:
        raise NotFound("Media topilmadi")
    await media_service.soft_delete(session, media, employee)
    return {"data": {"ok": True}}
