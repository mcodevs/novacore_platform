"""Media — hisobotning asosiy dalili.

Foto **doim** o'z omborimizga yuklanadi; Telegram `file_id` faqat tezkor
ko'rsatish uchun kesh (docs/03-integrations/03-media-and-storage.md §2).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import TASHKENT, settings
from app.core.errors import FileTooLarge, Forbidden, NotFound, ValidationFailed
from app.db.base import as_utc, utcnow
from app.db.models import Employee, Media, MediaKind, MediaSource, Submission
from app.domain.role import permissions
from app.integrations.storage import get_storage

#: Maydon kodi yo'l qurishda ishlatiladi — `../` bilan MEDIA_ROOT dan chiqib
#: ketishning oldini olish uchun shakli qat'iy cheklanadi.
FIELD_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "video/mp4",
    "application/pdf",
}

_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
    (b"%PDF", "application/pdf"),
)


def sniff_mime(data: bytes, fallback: str = "image/jpeg") -> str:
    """MIME kengaytmaga emas, **fayl mazmuniga** qarab aniqlanadi."""
    for prefix, mime in _MAGIC:
        if data.startswith(prefix):
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime
    if len(data) > 8 and data[4:8] == b"ftyp":
        return "video/mp4"
    return fallback


async def ensure_valid_field_code(
    session: AsyncSession, submission: Submission, field_code: str
) -> str:
    """Maydon kodi shablondagi media maydoni bo'lishi shart.

    ⚠️ Klient yuborgan qiymat storage kalitiga kiradi — ikki bosqichli
    tekshiruv: shakl (regex) va shablon sxemasida mavjudligi.
    """
    code = (field_code or "").strip()
    if not FIELD_CODE_RE.fullmatch(code):
        raise ValidationFailed(
            "Maydon kodi noto'g'ri", fields={"field_code": "invalid_field_code"}
        )

    from app.domain.template import engine

    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(code)
    if spec is None or spec.type not in ("photo", "video", "audio", "file", "signature"):
        raise ValidationFailed(
            "Bunday media maydoni shablonda yo'q", fields={"field_code": "unknown_field"}
        )
    return code


def storage_key(submission: Submission, field_code: str, sha256: str, mime: str) -> str:
    ext = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "video/mp4": "mp4",
        "application/pdf": "pdf",
    }.get(mime, "bin")
    day = as_utc(submission.arrived_at or utcnow()).astimezone(TASHKENT).strftime("%Y/%m/%d")
    return f"submissions/{day}/{submission.id}/{field_code}-{sha256[:16]}.{ext}"


async def store_bytes(
    session: AsyncSession,
    *,
    submission: Submission,
    uploader: Employee,
    field_code: str,
    data: bytes,
    kind: MediaKind = MediaKind.other,
    mime: str | None = None,
    tg_file_id: str | None = None,
    width: int | None = None,
    height: int | None = None,
    source: MediaSource = MediaSource.unknown,
    exif_taken_at: dt.datetime | None = None,
) -> Media:
    field_code = await ensure_valid_field_code(session, submission, field_code)

    if len(data) > settings.max_photo_mb * 1024 * 1024:
        raise FileTooLarge(f"Fayl {settings.max_photo_mb} MB dan katta")

    detected = sniff_mime(data, mime or "image/jpeg")
    if detected not in ALLOWED_MIME:
        raise Forbidden(f"Ruxsat etilmagan fayl turi: {detected}")

    digest = hashlib.sha256(data).hexdigest()
    key = storage_key(submission, field_code, digest, detected)
    await get_storage().put(key, data, content_type=detected)

    media = Media(
        submission_id=submission.id,
        field_code=field_code,
        kind=kind,
        storage_key=key,
        tg_file_id=tg_file_id,
        mime=detected,
        size_bytes=len(data),
        width=width,
        height=height,
        sha256=digest,
        source=source,
        exif_taken_at=exif_taken_at,
        uploaded_by=uploader.id,
        uploaded_at=utcnow(),  # ishonchli server vaqti
    )
    session.add(media)
    await session.flush()
    return media


async def get_for_actor(session: AsyncSession, media_id: int, actor: Employee) -> Media:
    media = await session.get(Media, media_id)
    if media is None or media.deleted_at is not None:
        raise NotFound("Media topilmadi")
    if media.submission_id is not None:
        submission = await session.get(Submission, media.submission_id)
        if submission is not None:
            permissions.ensure_can_view_submission(actor, submission)
    return media


async def load_bytes(media: Media) -> bytes:
    """Asosiy nusxani ombordan o'qish (Telegram `file_id` — faqat kesh)."""
    return await get_storage().get(media.storage_key)


def view_url(media: Media) -> str:
    """S3'da — signed URL; lokal omborda — API endpointi (`/media/{id}/raw`)."""
    if settings.storage_backend == "local":
        return f"{settings.base_url.rstrip('/')}/api/v1/media/{media.id}/raw"
    return get_storage().signed_url(media.storage_key, ttl_sec=settings.signed_url_ttl_sec)


async def soft_delete(session: AsyncSession, media: Media, actor: Employee) -> None:
    """Qo'lda o'chirish (admin). Metadata qoladi — audit uchun kerak."""
    if not permissions.is_admin(actor):
        raise Forbidden("Faqat admin media o'chiradi")
    media.deleted_at = utcnow()
    await get_storage().delete(media.storage_key)
    await session.flush()
