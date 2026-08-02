"""E'lon (broadcast) testlari — kim yuboradi, kimga yetadi, matn qanday ketadi.

Eng muhimi — HTML escape regressiyasi: bot `parse_mode=HTML` bilan yuboradi,
shuning uchun admin matnidagi bitta «<» butun e'lonni hech kimga yetkazmay
qo'yishi mumkin.
"""

from __future__ import annotations

import datetime as dt

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient

from app.bot import notifier
from app.core.config import settings
from app.core.errors import ValidationFailed
from app.core.security import build_init_data
from app.db.base import Base, as_utc
from app.db.models import (
    AuditLog,
    Broadcast,
    Employee,
    EmployeeStatus,
    Notification,
    NotificationStatus,
    Role,
)
from app.db.session import SessionFactory, engine
from app.domain.broadcast import service as broadcast_service
from app.domain.notify import service as notify
from app.seeds.loader import seed_all
from app.tasks import worker
from tests import fake_telegram as ft
from tests.conftest import make_employee

MECHANIC_TG = 7301
ADMIN_TG = 7302
ACCOUNTANT_TG = 7303


# --- Qabul qiluvchilar tanlovi -------------------------------------------------


async def test_recipients_only_active_and_linked(session):
    """Bloklangan, bo'shatilgan, o'chirilgan va botsiz xodim e'lon olmaydi."""
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    mechanic = await make_employee(session, role_code="mechanic", name="Karimov B.")
    blocked = await make_employee(
        session, role_code="mechanic", name="Bloklangan", status=EmployeeStatus.blocked
    )
    fired = await make_employee(
        session, role_code="mechanic", name="Bo'shatilgan", status=EmployeeStatus.fired
    )
    deleted = await make_employee(session, role_code="mechanic", name="O'chirilgan")
    deleted.deleted_at = dt.datetime.now(dt.UTC)
    unlinked = await make_employee(
        session, role_code="accountant", name="Botsiz", tg_user_id=None
    )
    unlinked.tg_user_id = None  # make_employee'ning avtomatik raqamini bekor qilamiz
    await session.flush()

    ids = set(await broadcast_service.recipient_ids(session))

    assert ids == {admin.id, mechanic.id}
    assert blocked.id not in ids
    assert fired.id not in ids
    assert deleted.id not in ids
    assert unlinked.id not in ids


# --- Matn tekshiruvi -----------------------------------------------------------


@pytest.mark.parametrize("body", ["", "   ", "\n\t  \n"])
async def test_empty_body_rejected(session, body):
    admin = await make_employee(session, role_code="admin")
    with pytest.raises(ValidationFailed):
        await broadcast_service.send(session, author=admin, body=body)

    assert (await session.execute(sa.select(sa.func.count(Broadcast.id)))).scalar_one() == 0


async def test_too_long_body_rejected(session):
    admin = await make_employee(session, role_code="admin")
    await make_employee(session, role_code="mechanic")

    # chegaraning o'zi o'tadi, undan bitta belgi ortig'i — yo'q
    limit = await broadcast_service.send(
        session, author=admin, body="a" * broadcast_service.MAX_BODY
    )
    assert limit.recipients_total == 2

    with pytest.raises(ValidationFailed):
        await broadcast_service.send(
            session, author=admin, body="a" * (broadcast_service.MAX_BODY + 1)
        )


async def test_body_is_trimmed_and_stored_raw(session):
    """DB'da matn xom qoladi — Mini App tarixida asliday ko'rinsin."""
    admin = await make_employee(session, role_code="admin")
    raw = "  <b>Ertaga</b> ish 9:00 dan  "

    broadcast = await broadcast_service.send(session, author=admin, body=raw)

    assert broadcast.body == "<b>Ertaga</b> ish 9:00 dan"
    stored = await session.get(Broadcast, broadcast.id)
    assert stored.body == "<b>Ertaga</b> ish 9:00 dan"


# --- Outbox --------------------------------------------------------------------


async def test_send_enqueues_one_notification_per_recipient(session):
    admin = await make_employee(session, role_code="admin")
    mechanic = await make_employee(session, role_code="mechanic")
    accountant = await make_employee(session, role_code="accountant")
    await make_employee(
        session, role_code="mechanic", name="Bloklangan", status=EmployeeStatus.blocked
    )

    broadcast = await broadcast_service.send(session, author=admin, body="Ertaga yig'ilish")

    notifications = list(
        (
            await session.execute(
                sa.select(Notification).where(Notification.broadcast_id == broadcast.id)
            )
        )
        .scalars()
        .all()
    )
    assert {n.employee_id for n in notifications} == {admin.id, mechanic.id, accountant.id}
    assert all(n.template_code == "notify_broadcast" for n in notifications)
    assert all(n.status == NotificationStatus.pending for n in notifications)
    assert all(n.payload["body"] == "Ertaga yig'ilish" for n in notifications)
    assert all(n.payload["broadcast_id"] == broadcast.id for n in notifications)

    # R7 uslubi: son serverda sanaladi, klient aytgani emas
    assert broadcast.recipients_total == len(notifications) == 3


async def test_audit_log_written(session):
    """R9 — kim, qachon, nechta odamga yuborgani izsiz qolmaydi."""
    admin = await make_employee(session, role_code="admin")
    await make_employee(session, role_code="mechanic")

    broadcast = await broadcast_service.send(session, author=admin, body="Salom")

    entry = (
        await session.execute(
            sa.select(AuditLog).where(
                AuditLog.action == "broadcast_sent",
                AuditLog.entity_type == "broadcast",
                AuditLog.entity_id == broadcast.id,
            )
        )
    ).scalar_one()
    assert entry.actor_id == admin.id
    assert entry.after == {"recipients": 2, "length": len("Salom")}


# --- ⚠️ HTML escape regressiyasi ------------------------------------------------


async def test_render_escapes_admin_text_but_keeps_template_tags(session):
    """Admin matnidagi «<» escape qilinadi, shablonning o'z tegi buzilmaydi.

    Escape bo'lmasa Telegram xabarni rad etadi va e'lon HECH KIMGA yetmaydi.
    """
    admin = await make_employee(session, role_code="admin")
    raw = "<b>salom</b> a < b"

    broadcast = await broadcast_service.send(session, author=admin, body=raw)
    notification = (
        await session.execute(
            sa.select(Notification).where(Notification.broadcast_id == broadcast.id)
        )
    ).scalar_one()

    text, _ = await notifier.render(session, notification, admin)

    # shablonning o'z tegi — tirik
    assert text.startswith("📢 <b>E'lon</b>")
    # admin matni — escape qilingan
    assert "&lt;b&gt;salom&lt;/b&gt; a &lt; b" in text
    assert "<b>salom</b>" not in text
    # xom matn DB'da ham, payload'da ham o'zgarmagan
    assert broadcast.body == raw
    assert notification.payload["body"] == raw


async def test_render_ru_template_also_escapes(session):
    """i18n ikkala tilda ham ishlaydi va escape tildan qat'i nazar bo'ladi."""
    admin = await make_employee(session, role_code="admin")
    reader = await make_employee(session, role_code="mechanic")
    reader.lang = "ru"
    await session.flush()

    broadcast = await broadcast_service.send(session, author=admin, body="a < b")
    notification = (
        await session.execute(
            sa.select(Notification).where(
                Notification.broadcast_id == broadcast.id,
                Notification.employee_id == reader.id,
            )
        )
    ).scalar_one()

    text, _ = await notifier.render(session, notification, reader)

    assert text.startswith("📢 <b>Объявление</b>")
    assert "a &lt; b" in text


# --- Tarix ---------------------------------------------------------------------


async def test_history_counts_delivery_states(session):
    admin = await make_employee(session, role_code="admin", name="Admin A.")
    await make_employee(session, role_code="mechanic")
    await make_employee(session, role_code="accountant")
    await make_employee(session, role_code="supplier")

    first = await broadcast_service.send(session, author=admin, body="Birinchi")
    second = await broadcast_service.send(session, author=admin, body="Ikkinchi")

    notifications = list(
        (
            await session.execute(
                sa.select(Notification)
                .where(Notification.broadcast_id == first.id)
                .order_by(Notification.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(notifications) == 4
    notifications[0].status = NotificationStatus.sent
    notifications[1].status = NotificationStatus.sent
    notifications[2].status = NotificationStatus.failed
    await session.flush()

    history = await broadcast_service.history(session, limit=20)

    assert [item["id"] for item in history] == [second.id, first.id]  # yangisi birinchi
    latest, oldest = history
    assert oldest["body"] == "Birinchi"
    assert oldest["author_name"] == "Admin A."
    assert oldest["recipients_total"] == 4
    assert (oldest["delivered"], oldest["failed"], oldest["pending"]) == (2, 1, 1)
    # ikkinchi e'lon hali navbatda — birinchisining hisobi unga oqib o'tmaydi
    assert (latest["delivered"], latest["failed"], latest["pending"]) == (0, 0, 4)


async def test_history_limit_and_empty(session):
    admin = await make_employee(session, role_code="admin")
    assert await broadcast_service.history(session, limit=5) == []

    for i in range(3):
        await broadcast_service.send(session, author=admin, body=f"E'lon {i}")

    assert len(await broadcast_service.history(session, limit=2)) == 2


# --- API: faqat admin ----------------------------------------------------------


@pytest.fixture
async def api():  # noqa: ANN201
    """Toza baza + ASGI klient (tarmoqsiz)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        await seed_all(session)
        roles = {
            role.code: role
            for role in (await session.execute(sa.select(Role))).scalars().all()
        }
        session.add_all(
            [
                Employee(
                    full_name="Karimov B.",
                    phone="+998901220001",
                    role_id=roles["mechanic"].id,
                    tg_user_id=MECHANIC_TG,
                ),
                Employee(
                    full_name="Admin A.",
                    phone="+998901220002",
                    role_id=roles["admin"].id,
                    tg_user_id=ADMIN_TG,
                ),
                Employee(
                    full_name="Buxgalter B.",
                    phone="+998901220003",
                    role_id=roles["accountant"].id,
                    tg_user_id=ACCOUNTANT_TG,
                ),
            ]
        )
        await session.commit()

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def init_data_for(tg_user_id: int) -> str:
    import time

    return build_init_data(
        settings.bot_token,
        {
            "auth_date": int(time.time()),
            "query_id": "AAF",
            "user": {"id": tg_user_id, "first_name": "Test", "language_code": "uz"},
        },
    )


async def token_for(client: AsyncClient, tg_user_id: int) -> str:
    response = await client.post(
        "/api/v1/auth/telegram", json={"init_data": init_data_for(tg_user_id)}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("tg_user_id", [MECHANIC_TG, ACCOUNTANT_TG])
async def test_only_admin_can_broadcast(api, tg_user_id):
    """Klientga ishonilmaydi — ruxsat serverda, `role.kind` bo'yicha."""
    headers = auth_header(await token_for(api, tg_user_id))

    created = await api.post("/api/v1/admin/broadcasts", headers=headers, json={"body": "Salom"})
    assert created.status_code == 403

    listed = await api.get("/api/v1/admin/broadcasts", headers=headers)
    assert listed.status_code == 403


async def test_broadcast_requires_token(api):
    response = await api.post("/api/v1/admin/broadcasts", json={"body": "Salom"})
    assert response.status_code == 401


async def test_admin_sends_and_sees_history(api):
    headers = auth_header(await token_for(api, ADMIN_TG))

    created = await api.post(
        "/api/v1/admin/broadcasts", headers=headers, json={"body": "Ertaga ish 9:00 dan"}
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["recipients_total"] == 3  # usta + admin + buxgalter
    assert body["pending"] == 3
    assert body["author_name"] == "Admin A."
    assert body["body"] == "Ertaga ish 9:00 dan"

    listed = await api.get("/api/v1/admin/broadcasts", headers=headers)
    assert listed.status_code == 200
    item = listed.json()[0]
    assert item["id"] == body["id"]
    assert (item["delivered"], item["failed"], item["pending"]) == (0, 0, 3)


async def test_api_rejects_empty_body(api):
    headers = auth_header(await token_for(api, ADMIN_TG))
    response = await api.post("/api/v1/admin/broadcasts", headers=headers, json={"body": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"


# --- ⚠️ Takroriy so'rov (zaif internet) ----------------------------------------


async def test_repeated_send_does_not_duplicate(session):
    """Klient POST'ni takrorlasa e'lon ikkinchi marta ketmaydi.

    `fetch` javob yo'lda yo'qolganda ham rad etadi — ya'ni server so'rovni
    allaqachon bajargan bo'lishi mumkin. E'lonni qaytarib bo'lmaydi.
    """
    admin = await make_employee(session, role_code="admin")
    await make_employee(session, role_code="mechanic")

    first = await broadcast_service.send(session, author=admin, body="Ertaga yig'ilish")
    second = await broadcast_service.send(session, author=admin, body="Ertaga yig'ilish")

    assert second.id == first.id
    assert (await session.execute(sa.select(sa.func.count(Broadcast.id)))).scalar_one() == 1
    assert (
        await session.execute(sa.select(sa.func.count(Notification.id)))
    ).scalar_one() == 2  # 2 ta xodim, 4 emas
    assert (
        await session.execute(
            sa.select(sa.func.count(AuditLog.id)).where(AuditLog.action == "broadcast_sent")
        )
    ).scalar_one() == 1


async def test_different_body_is_a_new_broadcast(session):
    """Deduplikatsiya faqat aynan bir xil matn uchun — yangi e'lon to'silmaydi."""
    admin = await make_employee(session, role_code="admin")
    await make_employee(session, role_code="mechanic")

    first = await broadcast_service.send(session, author=admin, body="Birinchi")
    second = await broadcast_service.send(session, author=admin, body="Ikkinchi")

    assert second.id != first.id


async def test_same_body_after_window_is_a_new_broadcast(session):
    """Oyna tugagach bir xil matnni qayta yuborish mumkin (kunlik eslatma)."""
    admin = await make_employee(session, role_code="admin")
    await make_employee(session, role_code="mechanic")

    first = await broadcast_service.send(session, author=admin, body="Ustaxona 9:00 da")
    first.created_at = dt.datetime.now(dt.UTC) - dt.timedelta(
        seconds=broadcast_service.DEDUP_WINDOW_SEC + 5
    )
    await session.flush()

    second = await broadcast_service.send(session, author=admin, body="Ustaxona 9:00 da")

    assert second.id != first.id


async def test_other_admin_sends_own_broadcast(session):
    """Dedup muallif bo'yicha — boshqa admin bir xil matnni yubora oladi."""
    first_admin = await make_employee(session, role_code="admin", name="Admin A.")
    second_admin = await make_employee(session, role_code="admin", name="Admin B.")

    one = await broadcast_service.send(session, author=first_admin, body="Salom")
    two = await broadcast_service.send(session, author=second_admin, body="Salom")

    assert one.id != two.id


# --- Outbox drenaji (fon sikli) ------------------------------------------------


@pytest.fixture
async def outbox():  # noqa: ANN201
    """Global engine + soxta bot — `worker.dispatch_notifications` shu ustida ishlaydi."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        await seed_all(session)
        roles = {
            role.code: role
            for role in (await session.execute(sa.select(Role))).scalars().all()
        }
        session.add_all(
            [
                Employee(
                    full_name="Admin A.",
                    phone="+998901230001",
                    role_id=roles["admin"].id,
                    tg_user_id=ADMIN_TG,
                ),
                Employee(
                    full_name="Karimov B.",
                    phone="+998901230002",
                    role_id=roles["mechanic"].id,
                    tg_user_id=MECHANIC_TG,
                ),
                Employee(
                    full_name="Buxgalter B.",
                    phone="+998901230003",
                    role_id=roles["accountant"].id,
                    tg_user_id=ACCOUNTANT_TG,
                ),
            ]
        )
        await session.commit()

    bot = ft.make_bot()
    yield bot
    await bot.session.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _send_broadcast(body: str) -> int:
    async with SessionFactory() as session:
        admin = (
            await session.execute(sa.select(Employee).where(Employee.tg_user_id == ADMIN_TG))
        ).scalar_one()
        broadcast = await broadcast_service.send(session, author=admin, body=body)
        await session.commit()
        return broadcast.id


async def test_broadcast_does_not_block_regular_notifications(outbox):
    """E'lon ortida turgan narx/hisobot signali navbat oxirida qolib ketmasin.

    Ilgari tanlov qat'iy FIFO edi: 150 kishilik e'lon oddiy bildirishnomani
    bir necha tikka (daqiqalarga) kechiktirardi.
    """
    bot = outbox
    await _send_broadcast("E'lon matni")

    async with SessionFactory() as session:
        admin = (
            await session.execute(sa.select(Employee).where(Employee.tg_user_id == ADMIN_TG))
        ).scalar_one()
        # e'londan KEYIN kelgan yozuv — id bo'yicha oxirida turadi
        await notify.enqueue(
            session,
            template_code="notify_period_closing",
            employee_id=admin.id,
            payload={"period": "2026-08", "days": 3},
        )
        await session.commit()

    assert await worker.dispatch_notifications(bot) == 4  # 3 e'lon + 1 oddiy

    texts = bot.session.sent_texts()
    assert len(texts) == 4
    assert "2026-08" in texts[0], "oddiy bildirishnoma e'lon ortida qoldi"
    assert all("E'lon" in text for text in texts[1:])


async def test_each_notification_is_committed_separately(outbox, monkeypatch):
    """Uzilish paytida allaqachon Telegram'ga ketgan xabar `pending` qolmaydi.

    Aks holda keyingi tik uni qayta yuboradi — e'londa bu 20 kishigacha dublikat.
    """
    bot = outbox
    await _send_broadcast("Uzun e'lon")

    real_deliver = notifier.deliver
    calls = {"n": 0}

    async def flaky(bot_, session_, notification):  # noqa: ANN001, ANN202
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("ulanish uzildi")
        return await real_deliver(bot_, session_, notification)

    monkeypatch.setattr(notifier, "deliver", flaky)

    with pytest.raises(RuntimeError):
        await worker.dispatch_notifications(bot)

    async with SessionFactory() as session:
        rows = (
            await session.execute(sa.select(Notification).order_by(Notification.id))
        ).scalars().all()
        statuses = [row.status for row in rows]

    assert statuses.count(NotificationStatus.sent) == 2
    assert statuses.count(NotificationStatus.pending) == 1


async def test_retry_after_uses_telegram_value_and_keeps_attempts(outbox, monkeypatch):
    """Flood-limit — vaqtinchalik cheklov, urinish sifatida sanalmaydi.

    Ilgari `retry_after` faqat matn sifatida saqlanardi, kutish esa
    `2**attempts` formulasidan olinardi: 5 ta flood-waitdan keyin e'lon
    butunlay `failed` bo'lib qolardi.
    """
    bot = outbox
    await _send_broadcast("Flood sinovi")

    async def flooded(bot_, session_, notification):  # noqa: ANN001, ANN202
        return False, "retry_after:30"

    monkeypatch.setattr(notifier, "deliver", flooded)

    assert await worker.dispatch_notifications(bot) == 0

    async with SessionFactory() as session:
        rows = (await session.execute(sa.select(Notification))).scalars().all()
        for row in rows:
            assert row.attempts == 0
            assert row.status == NotificationStatus.pending
            wait = (as_utc(row.not_before) - dt.datetime.now(dt.UTC)).total_seconds()
            # serverning qiymati (30 s), `2**attempts` = 2 daqiqa emas
            assert 25 < wait <= 32


async def test_permanent_error_still_fails_after_max_attempts(outbox, monkeypatch):
    """Haqiqiy nosozlik cheksiz urinilmaydi — eski himoya joyida qoladi."""
    bot = outbox
    await _send_broadcast("Xatolik sinovi")

    async def broken(bot_, session_, notification):  # noqa: ANN001, ANN202
        return False, "boom"

    monkeypatch.setattr(notifier, "deliver", broken)

    for _ in range(worker.MAX_ATTEMPTS):
        async with SessionFactory() as session:
            await session.execute(
                sa.update(Notification).values(not_before=dt.datetime.now(dt.UTC))
            )
            await session.commit()
        await worker.dispatch_notifications(bot)

    async with SessionFactory() as session:
        rows = (await session.execute(sa.select(Notification))).scalars().all()
        assert all(row.status == NotificationStatus.failed for row in rows)
        assert all(row.attempts == worker.MAX_ATTEMPTS for row in rows)
