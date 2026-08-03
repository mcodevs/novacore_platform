"""Buxgalter sinovi uchun test hisobotlari — PROD (bir martalik).

Har xil holatdagi **tugatilgan, lekin to'lanmagan** hisobotlar yaratadi:
qarz ro'yxati, FIFO, qisman to'lov va avans oqimini sinash uchun.

⚠️ Qoidalar:
  • Faqat **mavjud** xodim va mashinalar ishlatiladi — hech kim yaratilmaydi
  • Hamma narsa domen servislari orqali → barcha invariantlar saqlanadi
  • Bitta tranzaksiya: oxirida soxta bildirishnomalar commitdan OLDIN
    o'chiriladi, real xodimlarga xabar bormaydi
  • Har bir hisobotda `data["_seed"]` belgisi — keyin topib o'chirish uchun

Ishlatish:
    DRY (xavfsiz):  python3 seed_test_debts.py
    Yaratish:       CONFIRM=YES python3 seed_test_debts.py
"""

from __future__ import annotations

import asyncio
import base64
import os
from decimal import Decimal

import sqlalchemy as sa

from app.db.models import (
    Employee,
    LineKind,
    MediaKind,
    Notification,
    RoleKind,
    Submission,
    Template,
    Vehicle,
)
from app.db.session import session_scope
from app.domain.approval import service as approval_service
from app.domain.media import service as media_service
from app.domain.payment import service as payment_service
from app.domain.pricing import service as pricing_service
from app.domain.submission import service as submission_service
from app.domain.template import engine

SEED_MARK = "acct-test-2026-08-03"
CONFIRM = os.environ.get("CONFIRM") == "YES"
JPEG = base64.b64decode("/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAQKADAAQAAAABAAAAQAAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklNBCUAAAAAABDUHYzZjwCyBOmACZjs+EJ+/8AAEQgAQABAAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/bAEMAAgICAgICAwICAwUDAwMFBgUFBQUGCAYGBgYGCAoICAgICAgKCgoKCgoKCgwMDAwMDA4ODg4ODw8PDw8PDw8PD//bAEMBAgICBAQEBwQEBxALCQsQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEP/dAAQABP/aAAwDAQACEQMRAD8A4eiiiv7APzsKKKKACiiigAooooA//9Dh6KKK/sA/OwooooAKKKKACiiigD//0eHooor+wD87CiiigAooooAKKKKAP//S4eiiiv7APzsKKKKACiiigAooooA//9k=")

PHOTO_FIELDS = [
    ("photo_car_before", MediaKind.before),
    ("photo_problem", MediaKind.problem),
    ("photo_after", MediaKind.after),
    ("photo_car_after", MediaKind.after),
]


async def _photo(session, submission, author, field_code, kind, salt):
    #  Har fotoga o'z bayti — sha256 takrorlanmasin (dublikat bayrog'i)
    data = JPEG + salt.encode()
    media = await media_service.store_bytes(
        session,
        submission=submission,
        uploader=author,
        field_code=field_code,
        data=data,
        kind=kind,
        mime="image/jpeg",
    )
    #  Fotoni MAYDONGA bog'lash — `store_bytes` buni qilmaydi (API alohida qiladi)
    await session.refresh(submission)
    engine.append_media_id(submission, field_code, media.id)
    engine.mark_done(submission, field_code)
    await session.flush()
    return media


async def _build(session, author, vehicle, template, *, works, note, receipt=False):
    """To'ldirilgan va yuborilgan hisobot (ta'mir shabloni bo'yicha)."""
    submission = await submission_service.create_draft(
        session, author, template, vehicle_id=vehicle.id
    )
    engine.set_value(
        submission, "plate", {"vehicle_id": vehicle.id, "plate": vehicle.plate_number}
    )
    for code, kind in PHOTO_FIELDS:
        await _photo(session, submission, author, code, kind, f"{submission.id}{code}")

    engine.set_value(submission, "category", "brakes")
    engine.set_value(submission, "problem_description", note)
    engine.set_value(submission, "comment", "Ish bajarildi, sinovdan o'tkazildi")
    engine.mark_done(submission, "parts")

    for name, price in works:
        await submission_service.add_line(
            session, submission, author, kind=LineKind.labor, name=name, unit_price=price
        )
    engine.mark_done(submission, "works")

    if receipt:
        await submission_service.add_line(
            session,
            submission,
            author,
            kind=LineKind.part,
            name="Tormoz kolodkasi (o'z hisobimdan)",
            unit_price=Decimal("350000"),
            self_funded=True,
        )
        await _photo(
            session, submission, author, "photo_receipt", MediaKind.receipt,
            f"{submission.id}receipt",
        )

    data = dict(submission.data or {})
    data["_seed"] = SEED_MARK
    submission.data = data

    await submission_service.mark_left(session, submission, author)
    await session.refresh(submission)
    try:
        await submission_service.submit(session, submission, author)
    except Exception as exc:  # qaysi maydon yetishmayotganini ko'rsatish
        print('VALIDATSIYA XATOSI:', getattr(exc, 'fields', None) or exc)
        raise
    await session.refresh(submission)
    return submission


async def main() -> None:
    async with session_scope() as session:
        admin = (
            await session.execute(
                sa.select(Employee).join(Employee.role).where(
                    sa.text("roles.kind = 'admin'"), Employee.deleted_at.is_(None)
                )
            )
        ).scalars().first()
        usta = (
            await session.execute(
                sa.select(Employee).join(Employee.role).where(
                    sa.text("roles.kind = 'reporter'"), Employee.deleted_at.is_(None)
                )
            )
        ).scalars().first()
        template = (
            await session.execute(sa.select(Template).where(Template.code == "car_repair"))
        ).scalar_one()

        if admin is None or usta is None:
            raise SystemExit("Admin yoki usta topilmadi — to'xtatildi")

        vehicles = (
            await session.execute(
                sa.select(Vehicle)
                .where(Vehicle.deleted_at.is_(None), Vehicle.status == "active")
                .order_by(Vehicle.id)
                .limit(6)
            )
        ).scalars().all()
        if len(vehicles) < 6:
            raise SystemExit("Yetarli bo'sh mashina yo'q")

        plan = [
            "1. Kelishuvsiz tasdiqlangan — qarz 220 000",
            "2. Admin kamaytirdi (300k -> 240k), usta rozi — qarz 240 000",
            "3. Ikki ish, faqat biri kamaytirildi (150k->120k + 100k) — qarz 220 000",
            "4. Ish + o'z hisobidan qism (chek bilan) — qarz 530 000",
            "5. Tasdiqlangan 400k, 150k to'landi — qarz 250 000",
            "6. ADMIN o'z hisoboti (avtomatik tasdiq, R1a) — qarz 200 000 (2-qarzdor)",
        ]
        print(f"Muallif (usta): {usta.full_name} (id={usta.id})")
        print(f"Admin         : {admin.full_name} (id={admin.id})")
        print("Mashinalar    :", [v.plate_display for v in vehicles])
        print("\nYaratiladigan holatlar:")
        for line in plan:
            print("  ", line)

        if not CONFIRM:
            print("\nDRY-RUN — hech narsa yaratilmadi. Yaratish: CONFIRM=YES")
            return

        before_notify = (
            await session.execute(sa.select(sa.func.coalesce(sa.func.max(Notification.id), 0)))
        ).scalar_one()

        created: list[Submission] = []

        # 1 — kelishuvsiz
        s1 = await _build(session, usta, vehicles[0], template,
                          works=[("Old tormoz kolodkasini almashtirish", Decimal("220000"))],
                          note="Old kolodka yeyilgan")
        await approval_service.approve(session, s1, admin)
        created.append(s1)

        # 2 — kelishuv: kamaytirildi, usta rozi
        s2 = await _build(session, usta, vehicles[1], template,
                          works=[("Tormoz diskini almashtirish", Decimal("300000"))],
                          note="Disk urib ketgan")
        await pricing_service.propose_price(
            session, s2, admin,
            changes=[(s2.lines[0].id, Decimal("240000"))],
            comment="Bu ish odatda 240 000 ga bo'lgan",
        )
        await pricing_service.accept_price(session, s2, usta)
        created.append(s2)

        # 3 — ko'p qatorli, faqat biri kamaytirildi (effective_sum sinovi)
        s3 = await _build(session, usta, vehicles[2], template,
                          works=[("Amortizatorni almashtirish (1 dona)", Decimal("150000")),
                                 ("Stabilizator tyagasini almashtirish", Decimal("100000"))],
                          note="Podveska shovqin qilyapti")
        await pricing_service.propose_price(
            session, s3, admin,
            changes=[(s3.lines[0].id, Decimal("120000"))],
            comment="Amortizator narxi biroz yuqori",
        )
        await pricing_service.accept_price(session, s3, usta)
        created.append(s3)

        # 4 — o'z hisobidan olingan qism + chek
        s4 = await _build(session, usta, vehicles[3], template,
                          works=[("Orqa tormoz kolodkasini almashtirish", Decimal("180000"))],
                          note="Orqa kolodka tugagan", receipt=True)
        await approval_service.approve(session, s4, admin)
        created.append(s4)

        # 5 — tasdiqlangan va qisman to'langan
        s5 = await _build(session, usta, vehicles[4], template,
                          works=[("Sharovoy oporani almashtirish", Decimal("400000"))],
                          note="Sharovoy bo'shagan")
        await approval_service.approve(session, s5, admin)
        await payment_service.create_payment(
            session, employee_id=usta.id, actor_id=admin.id,
            submission_ids=[s5.id], amount=Decimal("150000"),
            note="Sinov uchun qisman to'lov",
        )
        created.append(s5)

        # 6 — admin o'z hisoboti: R1a avtomatik tasdiq, ikkinchi qarzdor
        s6 = await _build(session, admin, vehicles[5], template,
                          works=[("Support (kaliper) profilaktikasi", Decimal("200000"))],
                          note="Kaliper qisib qolgan")
        created.append(s6)

        # Soxta bildirishnomalarni commitdan OLDIN o'chirish — real xodimga
        # «hisobotingiz tasdiqlandi» degan xabar bormasin
        removed = await session.execute(
            sa.delete(Notification).where(Notification.id > before_notify)
        )
        print(f"\nBildirishnomalar o'chirildi: {removed.rowcount}")

        await session.flush()
        print("\n=== YARATILDI ===")
        for s in created:
            await session.refresh(s)
            print(f"  {s.number}  {s.status.value:9} author={s.author_id}  "
                  f"payable={s.payable_amount}  paid={s.paid_amount}  "
                  f"qarz={s.payable_amount - s.paid_amount}")


asyncio.run(main())
