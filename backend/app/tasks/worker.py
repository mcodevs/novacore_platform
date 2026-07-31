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
from app.domain.notify import service as notify
from app.domain.period import service as period_service
from app.domain.pricing import service as pricing_service

log = structlog.get_logger(__name__)

MAX_ATTEMPTS = 5
BATCH = 20


async def dispatch_notifications(bot: Bot) -> int:
    sent = 0
    async with session_scope() as session:
        stmt = (
            sa.select(Notification)
            .where(
                Notification.status == NotificationStatus.pending,
                Notification.not_before <= utcnow(),
            )
            .order_by(Notification.id)
            .limit(BATCH)
        )
        if not settings.is_sqlite:
            stmt = stmt.with_for_update(skip_locked=True)

        for notification in (await session.execute(stmt)).scalars().all():
            ok, error = await notifier.deliver(bot, session, notification)
            notification.attempts += 1
            if ok:
                notification.status = NotificationStatus.sent
                notification.sent_at = utcnow()
                sent += 1
            else:
                notification.last_error = error
                if notification.attempts >= MAX_ATTEMPTS or error in (
                    "bot_blocked",
                    "employee_inactive",
                    "employee_without_telegram",
                    "no_chat",
                ):
                    notification.status = NotificationStatus.failed
                else:
                    notification.not_before = utcnow() + dt.timedelta(
                        minutes=2 ** notification.attempts
                    )
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


async def remind_period_closing() -> int:
    """Oy yopilishiga 3 kun — admin va buxgalterga."""
    now_local = utcnow().astimezone(TASHKENT)
    next_month = (now_local.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    days_left = (next_month.date() - now_local.date()).days
    if days_left != 3:
        return 0

    async with session_scope() as session:
        period = await period_service.current_period(session)
        marker = f"period_closing:{period.id}"
        exists = (
            await session.execute(
                sa.select(Notification.id).where(Notification.template_code == marker)
            )
        ).first()
        if exists:
            return 0

        payload = {"period": period.title, "days": days_left}
        await notify.notify_admins(
            session, template_code="notify_period_closing", payload=payload
        )
        await notify.notify_accountants(
            session, template_code="notify_period_closing", payload=payload
        )
        # takrorlanmasligi uchun marker
        session.add(
            Notification(
                template_code=marker,
                payload=payload,
                status=NotificationStatus.sent,
                sent_at=utcnow(),
            )
        )
    return 1


async def tick(bot: Bot) -> None:
    """Bitta sikl — xatolar butun siklni to'xtatmasin."""
    for step in (
        auto_accept_expired,
        send_negotiation_reminders,
        remind_stale_drafts,
        alert_long_service,
        remind_period_closing,
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
