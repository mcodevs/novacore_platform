"""Fon sikli — asyncio, shu process ichida. Redis/Celery YO'Q (ADR-0004).

• notifications outbox
• 48 soat → avtomatik rozilik (N4)
• 24 soat → kelishuv eslatmasi
• turib qolgan qoralamalar
• uzoq downtime signali
• oy yopilishiga 3 kun qolganda eslatma
"""

from __future__ import annotations

import asyncio
import datetime as dt

import sqlalchemy as sa
import structlog
from aiogram import Bot

from app.bot import notifier
from app.core.config import TASHKENT, settings
from app.db.base import as_utc, utcnow
from app.db.models import (
    AcceptMode,
    Notification,
    NotificationStatus,
    Submission,
    SubmissionStatus,
)
from app.db.session import session_scope
from app.domain.fleet import service as fleet_service
from app.domain.notify import service as notify
from app.domain.pricing import service as pricing_service

log = structlog.get_logger(__name__)

MAX_ATTEMPTS = 5
BATCH = 20
# Bitta tikda ko'pi bilan shuncha xabar. E'lon bir zumda 150 ta yozuv qo'shadi:
# eski BATCH=20 bilan u 8 tikka (~8 daqiqa) cho'zilar va ortidagi narx kelishuvi
# bildirishnomasini ham shuncha ushlab turardi.
MAX_PER_TICK = 300
# Telegram ~30 xabar/sek ruxsat beradi — undan pastda turamiz.
SEND_PAUSE_SEC = 0.05
# Qayta urinish foydasiz bo'lgan xatolar — darhol `failed`
TERMINAL_ERRORS = frozenset(
    {"bot_blocked", "employee_inactive", "employee_without_telegram", "no_chat"}
)
RETRY_AFTER_PREFIX = "retry_after:"
MAX_RETRY_AFTER_SEC = 3600


def _reschedule(notification: Notification, error: str) -> None:
    """Xatodan keyin: qayta urinish vaqti yoki yakuniy `failed`.

    `retry_after:` — Telegram flood-limiti, ya'ni **vaqtinchalik** cheklov, xato
    emas. Uni urinish sifatida sanasak, e'lon 5 ta flood-waitdan keyin butunlay
    yiqilardi; kutish vaqti ham serverning o'z qiymatidan olinadi.
    """
    notification.last_error = error
    if error.startswith(RETRY_AFTER_PREFIX):
        try:
            wait = int(error[len(RETRY_AFTER_PREFIX) :])
        except ValueError:
            wait = 5
        wait = min(max(wait, 1), MAX_RETRY_AFTER_SEC)
        notification.not_before = utcnow() + dt.timedelta(seconds=wait + 1)
        return

    notification.attempts += 1
    if notification.attempts >= MAX_ATTEMPTS or error in TERMINAL_ERRORS:
        notification.status = NotificationStatus.failed
    else:
        notification.not_before = utcnow() + dt.timedelta(
            minutes=2 ** notification.attempts
        )


async def _dispatch_batch(bot: Bot, limit: int) -> tuple[int, int]:
    """(yuborildi, ko'rib chiqildi) — bitta partiya."""
    sent = 0
    seen = 0
    async with session_scope() as session:
        stmt = (
            sa.select(Notification)
            .where(
                Notification.status == NotificationStatus.pending,
                Notification.not_before <= utcnow(),
            )
            # E'lon ommaviy, lekin shoshilinch emas: 150 kishilik e'lon narx
            # kelishuvi yoki yangi hisobot signalini navbatda ushlab qolmasin.
            .order_by(Notification.broadcast_id.is_not(None), Notification.id)
            .limit(limit)
        )
        if not settings.is_sqlite:
            stmt = stmt.with_for_update(skip_locked=True)

        for notification in (await session.execute(stmt)).scalars().all():
            seen += 1
            ok, error = await notifier.deliver(bot, session, notification)
            if ok:
                notification.attempts += 1
                notification.status = NotificationStatus.sent
                notification.sent_at = utcnow()
                sent += 1
            else:
                _reschedule(notification, error or "unknown")
            # Har yozuv alohida commit: deploy yoki ulanish uzilganda allaqachon
            # Telegram'ga ketgan xabarlar `pending` bo'lib qolmasin (aks holda
            # keyingi tik ularni qayta yuboradi — e'londa bu 20 kishigacha).
            await session.commit()
            await asyncio.sleep(SEND_PAUSE_SEC)
    return sent, seen


async def dispatch_notifications(bot: Bot) -> int:
    """Navbatni bo'shatgunicha aylanadi (bitta tikda MAX_PER_TICK gacha)."""
    sent = 0
    handled = 0
    while handled < MAX_PER_TICK:
        limit = min(BATCH, MAX_PER_TICK - handled)
        batch_sent, seen = await _dispatch_batch(bot, limit)
        sent += batch_sent
        handled += seen
        if seen < limit:  # navbat bo'shadi
            break
    return sent


async def auto_accept_expired() -> int:
    """N4 — 48 soat javob bo'lmasa avtomatik rozilik."""
    count = 0
    async with session_scope() as session:
        for submission in await pricing_service.expired_negotiations(session):
            await pricing_service.accept_price(
                session, submission, None, mode=AcceptMode.auto_48h
            )
            count += 1
            log.info("price_auto_accepted", submission=submission.number)
    return count


async def send_negotiation_reminders() -> int:
    count = 0
    async with session_scope() as session:
        for submission in await pricing_service.negotiations_needing_reminder(session):
            remaining = settings.price_auto_accept_hours - settings.price_reminder_hours
            await notify.enqueue(
                session,
                template_code="notify_price_reminder",
                employee_id=submission.author_id,
                payload={
                    "submission_id": submission.id,
                    "number": submission.number,
                    "hours": remaining,
                },
            )
            pricing_service.mark_reminder_sent(submission)
            count += 1
    return count


async def remind_stale_drafts() -> int:
    """Qoralama 24 soat tursa — muallifga eslatma (bir marta)."""
    count = 0
    threshold = utcnow() - dt.timedelta(hours=settings.draft_reminder_hours)
    async with session_scope() as session:
        rows = (
            await session.execute(
                sa.select(Submission).where(
                    Submission.status == SubmissionStatus.DRAFT,
                    Submission.deleted_at.is_(None),
                    Submission.created_at <= threshold,
                )
            )
        ).scalars().all()
        for submission in rows:
            data = dict(submission.data or {})
            if data.get("_draft_reminder_sent"):
                continue
            await notify.enqueue(
                session,
                template_code="notify_draft_stale",
                employee_id=submission.author_id,
                payload={
                    "submission_id": submission.id,
                    "number": submission.number,
                    "hours": settings.draft_reminder_hours,
                },
            )
            data["_draft_reminder_sent"] = True
            submission.data = data
            count += 1
    return count


async def alert_long_service() -> int:
    """Mashina 24 soatdan beri ustaxonada — adminga signal."""
    count = 0
    threshold = utcnow() - dt.timedelta(hours=settings.long_service_alert_hours)
    async with session_scope() as session:
        rows = (
            await session.execute(
                sa.select(Submission).where(
                    Submission.status == SubmissionStatus.DRAFT,
                    Submission.deleted_at.is_(None),
                    Submission.left_at.is_(None),
                    Submission.arrived_at <= threshold,
                    Submission.subject_vehicle_id.is_not(None),
                )
            )
        ).scalars().all()
        for submission in rows:
            data = dict(submission.data or {})
            if data.get("_long_service_alert_sent"):
                continue
            hours = int(
                (utcnow() - as_utc(submission.arrived_at)).total_seconds() // 3600
            )
            await notify.notify_admins(
                session,
                template_code="notify_long_service",
                payload={
                    "submission_id": submission.id,
                    "number": submission.number,
                    "vehicle": submission.vehicle.plate_display if submission.vehicle else "—",
                    "hours": hours,
                },
                include_group=True,
            )
            data["_long_service_alert_sent"] = True
            submission.data = data
            count += 1
    return count


async def sync_fleet_daily() -> int:
    """Kuniga 1× mashina va haydovchi reyestri (Fleet → platforma, faqat o'qish).

    Fleet o'chirilgan bo'lsa yoki javob bermasa — platforma ishlashda davom
    etadi, keyingi urinishda davom etiladi (hujjat §8).
    """
    if not settings.fleet_ready:
        return 0

    now_local = utcnow().astimezone(TASHKENT)
    if now_local.hour != settings.fleet_sync_hour:
        return 0

    async with session_scope() as session:
        marker = f"fleet_sync:{now_local:%Y-%m-%d}"
        exists = (
            await session.execute(
                sa.select(Notification.id).where(Notification.template_code == marker)
            )
        ).first()
        if exists:
            return 0

        report = await fleet_service.sync(session)
        session.add(  # takroriy sinxron bo'lmasligi uchun marker
            Notification(
                template_code=marker,
                payload={"summary": report.summary()},
                status=NotificationStatus.sent,
                sent_at=utcnow(),
            )
        )
        if not report.ok or report.created or report.missing:
            await notify.notify_admins(
                session,
                template_code="notify_fleet_sync",
                payload={"summary": report.summary()},
            )
        log.info("fleet_sync_done", summary=report.summary())
    return 1


async def tick(bot: Bot) -> None:
    """Bitta sikl — xatolar butun siklni to'xtatmasin."""
    for step in (
        auto_accept_expired,
        send_negotiation_reminders,
        remind_stale_drafts,
        alert_long_service,
        sync_fleet_daily,
    ):
        try:
            await step()
        except Exception:  # noqa: BLE001
            log.exception("background_step_failed", step=step.__name__)
    try:
        await dispatch_notifications(bot)
    except Exception:  # noqa: BLE001
        log.exception("notification_dispatch_failed")


async def run_forever(bot: Bot) -> None:
    log.info("background_loop_started", interval=settings.background_tick_sec)
    while True:
        await tick(bot)
        await asyncio.sleep(settings.background_tick_sec)
