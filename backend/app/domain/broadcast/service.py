"""E'lon (broadcast) — admin barcha xodimlarga bitta xabar yuboradi.

Yetkazish mavjud outbox ustida (`notifications`) — alohida navbat yo'q
(ADR-0004: Redis/Celery yo'q). Har xodimga alohida yozuv, chunki matn
tilga qarab emas, lekin sarlavha (`notify_broadcast`) tarjima qilinadi.

⚠️ Matn DB'da **xom** saqlanadi. HTML escape faqat botga yuborishdan oldin
(`app/bot/notifier.py:render`) — shunda Mini App tarixida matn asliday ko'rinadi.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailed
from app.db.base import utcnow
from app.db.models import (
    Broadcast,
    Employee,
    EmployeeStatus,
    Notification,
    NotificationStatus,
)
from app.domain import audit
from app.domain.notify import service as notify

MAX_BODY = 3500

TEMPLATE_CODE = "notify_broadcast"

# Takroriy so'rov oynasi: shu muddat ichida aynan shu admin aynan shu matnni
# yuborsa — yangi e'lon yaratilmaydi (pastdagi `send` izohiga qarang).
DEDUP_WINDOW_SEC = 60


async def recipient_ids(session: AsyncSession) -> list[int]:
    """Kimga yetadi: faol, o'chirilmagan va botga bog'langan xodimlar.

    Rol ahamiyatsiz — e'lon hammaga (adminning o'ziga ham: yuborilganini ko'radi).
    """
    stmt = sa.select(Employee.id).where(
        Employee.status == EmployeeStatus.active,
        Employee.deleted_at.is_(None),
        Employee.tg_user_id.is_not(None),
    )
    return list((await session.execute(stmt)).scalars().all())


async def send(session: AsyncSession, *, author: Employee, body: str) -> Broadcast:
    """E'lonni yozadi va har bir qabul qiluvchi uchun outbox yozuvi qo'shadi.

    Ruxsat (`role.kind == 'admin'`) API qatlamida tekshiriladi (AdminDep).
    """
    text = (body or "").strip()
    if not text:
        raise ValidationFailed("E'lon matni bo'sh", fields={"body": "required"})
    if len(text) > MAX_BODY:
        raise ValidationFailed(
            f"E'lon matni {MAX_BODY} belgidan uzun", fields={"body": "too_long"}
        )

    # ⚠️ Takroriy so'rovdan himoya. Zaif internetda javob yo'lda yo'qolsa klient
    # POST'ni qayta yuborishi mumkin — server esa birinchi so'rovni allaqachon
    # bajarib bo'lgan bo'ladi. E'lonni qaytarib bo'lmaydi (xabar Telegram'da,
    # yozuv R9 bo'yicha o'chirilmaydi), shuning uchun oynadagi aynan shu matn
    # ikkinchi marta yozilmaydi — mavjudi qaytariladi.
    duplicate = (
        await session.execute(
            sa.select(Broadcast)
            .where(
                Broadcast.author_id == author.id,
                Broadcast.body == text,
                Broadcast.created_at >= utcnow() - dt.timedelta(seconds=DEDUP_WINDOW_SEC),
            )
            .order_by(Broadcast.id.desc())
            .limit(1)
        )
    ).scalars().first()
    if duplicate is not None:
        return duplicate

    broadcast = Broadcast(author_id=author.id, body=text)
    session.add(broadcast)
    await session.flush()

    count = 0
    for employee_id in await recipient_ids(session):
        notification = await notify.enqueue(
            session,
            template_code=TEMPLATE_CODE,
            employee_id=employee_id,
            payload={"body": text, "broadcast_id": broadcast.id},
        )
        if notification is None:
            continue
        # yetkazilish statistikasi ustun bo'yicha sanaladi (JSON so'rovsiz)
        notification.broadcast_id = broadcast.id
        count += 1

    broadcast.recipients_total = count
    await session.flush()

    await audit.log(
        session,
        action="broadcast_sent",
        entity_type="broadcast",
        entity_id=broadcast.id,
        actor_id=author.id,
        after={"recipients": count, "length": len(text)},
    )
    return broadcast


async def history(session: AsyncSession, *, limit: int = 20) -> list[dict[str, Any]]:
    """Oxirgi e'lonlar + har biri bo'yicha yetkazilish hisobi."""
    rows = (
        await session.execute(
            sa.select(Broadcast, Employee.full_name)
            .join(Employee, Employee.id == Broadcast.author_id)
            .order_by(Broadcast.id.desc())
            .limit(limit)
        )
    ).all()
    if not rows:
        return []

    ids = [broadcast.id for broadcast, _ in rows]
    stats: dict[int, dict[str, int]] = {
        broadcast_id: {"delivered": 0, "failed": 0, "pending": 0} for broadcast_id in ids
    }
    counts = await session.execute(
        sa.select(
            Notification.broadcast_id,
            Notification.status,
            sa.func.count(Notification.id),
        )
        .where(Notification.broadcast_id.in_(ids))
        .group_by(Notification.broadcast_id, Notification.status)
    )
    key = {
        NotificationStatus.sent: "delivered",
        NotificationStatus.failed: "failed",
        NotificationStatus.pending: "pending",
    }
    for broadcast_id, status, total in counts:
        bucket = stats.get(broadcast_id)
        if bucket is not None:
            bucket[key[NotificationStatus(status)]] += total

    return [
        {
            "id": broadcast.id,
            "body": broadcast.body,
            "recipients_total": broadcast.recipients_total,
            "created_at": broadcast.created_at,
            "author_name": author_name,
            **stats[broadcast.id],
        }
        for broadcast, author_name in rows
    ]
