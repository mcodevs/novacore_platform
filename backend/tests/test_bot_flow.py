"""Uchidan-uchiga bot oqimi: /start → hisobot → narx kelishuvi → tasdiq.

Telegram bilan aloqa soxta sessiya orqali — tarmoq kerak emas.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
import sqlalchemy as sa
from aiogram.types import Update

from app.db.base import Base
from app.db.models import (
    AcceptMode,
    Employee,
    Notification,
    Submission,
    SubmissionStatus,
    Template,
    Vehicle,
)
from app.db.session import SessionFactory, engine
from app.seeds.loader import seed_all
from tests import fake_telegram as ft

MECHANIC_TG = 5001
ADMIN_TG = 5002
MECHANIC_PHONE = "+998901112233"
ADMIN_PHONE = "+998901112244"


@pytest.fixture
async def bot():  # noqa: ANN201
    bot = ft.make_bot()
    yield bot
    await bot.session.close()


@pytest.fixture(scope="session")
def dispatcher():  # noqa: ANN201
    """Bitta dispatcher — routerlar modul darajasida (prod'da ham bitta)."""
    from app.bot.bot import get_dispatcher

    return get_dispatcher()


@pytest.fixture(autouse=True)
def clean_fsm(dispatcher):  # noqa: ANN001, ANN201
    from aiogram.fsm.storage.memory import MemoryStorage

    dispatcher.fsm.storage = MemoryStorage()


@pytest.fixture
async def db():  # noqa: ANN201
    """Global engine (bot middleware shundan foydalanadi) — toza baza."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        await seed_all(session)

        from app.db.models import Role

        roles = {
            role.code: role
            for role in (await session.execute(sa.select(Role))).scalars().all()
        }
        session.add_all(
            [
                Employee(
                    full_name="Karimov B.",
                    phone=MECHANIC_PHONE,
                    role_id=roles["mechanic"].id,
                    lang="uz",
                ),
                Employee(
                    full_name="Admin A.",
                    phone=ADMIN_PHONE,
                    role_id=roles["admin"].id,
                    tg_user_id=ADMIN_TG,
                    lang="uz",
                ),
                Vehicle(
                    plate_number="01A123BC",
                    plate_display="01 A 123 BC",
                    brand="BYD",
                    model="Chazor",
                    year=2024,
                ),
            ]
        )
        await session.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def feed(dispatcher, bot, payload: dict) -> None:
    update = Update.model_validate(payload, context={"bot": bot})
    await dispatcher.feed_update(bot, update)


async def fetch_submission(number: str | None = None) -> Submission:
    async with SessionFactory() as session:
        stmt = sa.select(Submission).order_by(Submission.id.desc()).limit(1)
        if number:
            stmt = sa.select(Submission).where(Submission.number == number)
        return (await session.execute(stmt)).scalars().first()


# --- Ro'yxatdan o'tish --------------------------------------------------------


async def test_registration_requires_own_contact(db, bot, dispatcher):
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "/start"))
    assert "NovaCore" in bot.session.last_text(MECHANIC_TG)

    # boshqa odamning kontakti — rad etiladi
    await feed(
        dispatcher,
        bot,
        ft.contact_update(MECHANIC_TG, MECHANIC_PHONE, contact_user_id=999999),
    )
    assert "raqamingiz emas" in bot.session.last_text(MECHANIC_TG)

    async with SessionFactory() as session:
        employee = (
            await session.execute(sa.select(Employee).where(Employee.phone == MECHANIC_PHONE))
        ).scalar_one()
        assert employee.tg_user_id is None


async def test_unknown_phone_is_rejected(db, bot, dispatcher):
    await feed(dispatcher, bot, ft.contact_update(7777, "+998900000000"))
    assert "reyestrida yo'qsiz" in bot.session.last_text(7777)


async def test_registration_links_account(db, bot, dispatcher):
    await feed(dispatcher, bot, ft.contact_update(MECHANIC_TG, MECHANIC_PHONE))

    async with SessionFactory() as session:
        employee = (
            await session.execute(sa.select(Employee).where(Employee.phone == MECHANIC_PHONE))
        ).scalar_one()
        assert employee.tg_user_id == MECHANIC_TG

    texts = " ".join(bot.session.sent_texts(MECHANIC_TG))
    assert "Karimov B." in texts
    assert "Usta" in texts


# --- To'liq oqim --------------------------------------------------------------


async def _register_mechanic(dispatcher, bot) -> None:
    await feed(dispatcher, bot, ft.contact_update(MECHANIC_TG, MECHANIC_PHONE))


async def _fill_report(dispatcher, bot, *, work_name: str = "Old tormoz kolodka") -> Submission:
    """Bot orqali ta'mir hisobotini to'liq to'ldiradi."""
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "🚗 Mashina keldi"))
    if "Qaysi hisobot" in bot.session.last_text(MECHANIC_TG):
        # rolda bir nechta shablon bor (admin) — ta'mir hisobotini tanlaymiz
        tpl = bot.session.callback_data("tpl", MECHANIC_TG)
        assert tpl is not None
        await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, tpl))
    assert "raqamini" in bot.session.last_text(MECHANIC_TG)

    # 1. mashina raqami
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "01 A 123 BC"))
    assert "BYD" in " ".join(bot.session.sent_texts(MECHANIC_TG)[-3:])

    # 2. mashina fotosi (min 1, max 2) → "Tayyor"
    await feed(dispatcher, bot, ft.photo_update(MECHANIC_TG, "photo_car_1"))
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "✅ Tayyor"))

    # 3. panel fotosi (max 1) → avtomatik keyingi qadam
    await feed(dispatcher, bot, ft.photo_update(MECHANIC_TG, "photo_odo"))

    # 4. probeg
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "48250"))

    # 5. nosozlik kategoriyasi (inline)
    data = bot.session.callback_data("opt", MECHANIC_TG)
    assert data is not None
    await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, data))

    # 6. muammo fotosi
    await feed(dispatcher, bot, ft.photo_update(MECHANIC_TG, "photo_problem"))
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "✅ Tayyor"))

    # 7. muammo tavsifi
    await feed(
        dispatcher, bot, ft.message_update(MECHANIC_TG, "Old tormoz kolodkasi to'liq yeyilgan")
    )

    # 8. bajarilgan ishlar: qo'shish → nom → narx → tayyor
    add = bot.session.callback_data("line_add", MECHANIC_TG)
    assert add is not None
    await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, add))
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, work_name))
    cat = bot.session.callback_data("cat", MECHANIC_TG)
    if cat is not None:
        # katalogdan mos ishni tanlaymiz (narx tarixi shu bo'yicha yig'iladi)
        await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, cat))
    # katalogda mos kelmasa — o'z nomi bilan to'g'ridan-to'g'ri narx so'raladi
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "250000"))
    done = bot.session.callback_data("lines_done", MECHANIC_TG)
    assert done is not None
    await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, done))

    # 9. qismlar (ixtiyoriy) → tayyor
    done = bot.session.callback_data("lines_done", MECHANIC_TG)
    await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, done))

    # 10. tuzatilgandan keyin + mashina fotosi
    await feed(dispatcher, bot, ft.photo_update(MECHANIC_TG, "photo_after"))
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "✅ Tayyor"))
    await feed(dispatcher, bot, ft.photo_update(MECHANIC_TG, "photo_car_after"))
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "✅ Tayyor"))

    # 11. izoh
    await feed(
        dispatcher, bot, ft.message_update(MECHANIC_TG, "Kolodka almashtirildi, disk normal")
    )
    # 12. tavsiya (ixtiyoriy) — o'tkazib yuboramiz
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "⏭ O'tkazib yuborish"))

    return await fetch_submission()


async def test_full_flow_report_to_price_agreement(db, bot, dispatcher):
    await _register_mechanic(dispatcher, bot)
    submission = await _fill_report(dispatcher, bot)

    assert submission.status == SubmissionStatus.DRAFT
    assert submission.subject_vehicle_id is not None
    assert submission.data["odometer_value"] == 48250
    assert submission.data["category"] == "brakes"
    assert len(submission.lines) == 1
    assert submission.lines[0].proposed_amount == Decimal("250000.00")
    assert len(submission.media) == 5

    # mashina ketdi → left_at server vaqti
    left = bot.session.callback_data("mark_left", MECHANIC_TG)
    assert left is not None
    await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, left))
    submission = await fetch_submission(submission.number)
    assert submission.left_at is not None

    # yuborish
    submit = bot.session.callback_data("submit", MECHANIC_TG)
    assert submit is not None
    await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, submit))

    submission = await fetch_submission(submission.number)
    assert submission.status == SubmissionStatus.SUBMITTED
    assert submission.proposed_labor_amount == Decimal("250000.00")
    assert submission.odometer_km == 48250  # promoted (field_mapping)
    assert submission.period_id is not None

    # adminga bildirishnoma outbox'ga tushdi
    async with SessionFactory() as session:
        pending = (
            await session.execute(
                sa.select(Notification).where(
                    Notification.template_code == "notify_new_submission"
                )
            )
        ).scalars().all()
        assert len(pending) == 1

    # --- Admin ko'rib chiqadi va narxni kamaytiradi ---
    bot.session.clear()
    await feed(dispatcher, bot, ft.message_update(ADMIN_TG, "/tasdiq"))
    open_card = bot.session.callback_data("review", ADMIN_TG)
    assert open_card is not None
    await feed(dispatcher, bot, ft.callback_update(ADMIN_TG, open_card))

    card = bot.session.last_text(ADMIN_TG)
    assert "250 000" in card
    assert "Karimov B." in card

    reduce = bot.session.callback_data("reduce", ADMIN_TG)
    await feed(dispatcher, bot, ft.callback_update(ADMIN_TG, reduce))
    reduce_line = bot.session.callback_data("reduce_line", ADMIN_TG)
    assert reduce_line is not None
    await feed(dispatcher, bot, ft.callback_update(ADMIN_TG, reduce_line))

    # R2 — oshirishga urinish rad etiladi
    await feed(dispatcher, bot, ft.message_update(ADMIN_TG, "300000"))
    assert "oshirib bo'lmaydi" in bot.session.last_text(ADMIN_TG)

    await feed(dispatcher, bot, ft.message_update(ADMIN_TG, "180000"))
    assert "Sabab" in bot.session.last_text(ADMIN_TG)
    await feed(dispatcher, bot, ft.message_update(ADMIN_TG, "Bu ish odatda 175 000 ga bo'lgan"))

    submission = await fetch_submission(submission.number)
    assert submission.status == SubmissionStatus.PRICE_NEGOTIATION
    assert submission.lines[0].approved_amount == Decimal("180000.00")
    assert submission.lines[0].proposed_amount == Decimal("250000.00")  # R2a

    # --- Usta rozilik beradi ---
    bot.session.clear()
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "💬 Narx kelishuvi"))
    accept = bot.session.callback_data("accept_price", MECHANIC_TG)
    assert accept is not None
    await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, accept))

    submission = await fetch_submission(submission.number)
    assert submission.status == SubmissionStatus.APPROVED
    assert submission.labor_amount == Decimal("180000.00")
    assert submission.lines[0].mechanic_accept_mode == AcceptMode.manual


async def test_admin_report_is_auto_approved_in_bot(db, bot, dispatcher):
    """R1a — admin hisoboti botda ham avtomatik tasdiqlanadi."""
    global MECHANIC_TG
    await feed(dispatcher, bot, ft.message_update(ADMIN_TG, "/start"))

    # admin ham usta kabi hisobot to'ldiradi
    original = MECHANIC_TG
    MECHANIC_TG = ADMIN_TG
    try:
        submission = await _fill_report(dispatcher, bot)
        left = bot.session.callback_data("mark_left", ADMIN_TG)
        await feed(dispatcher, bot, ft.callback_update(ADMIN_TG, left))
        submit = bot.session.callback_data("submit", ADMIN_TG)
        await feed(dispatcher, bot, ft.callback_update(ADMIN_TG, submit))
    finally:
        MECHANIC_TG = original

    submission = await fetch_submission(submission.number)
    assert submission.status == SubmissionStatus.APPROVED
    assert submission.auto_approved is True
    assert submission.labor_amount == submission.proposed_labor_amount
    assert "Avtomatik tasdiqlandi" in " ".join(bot.session.sent_texts(ADMIN_TG))


async def test_reporter_menu_has_no_admin_buttons(db, bot, dispatcher):
    await _register_mechanic(dispatcher, bot)
    bot.session.clear()
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "/start"))

    markup = bot.session.last_markup(MECHANIC_TG)
    labels = {button.text for row in markup.keyboard for button in row}
    assert "🚗 Mashina keldi" in labels
    assert "⏳ Tasdiq kutmoqda" not in labels  # admin tugmasi
    assert "📅 Davr" not in labels


async def test_admin_menu_has_review_buttons(db, bot, dispatcher):
    await feed(dispatcher, bot, ft.message_update(ADMIN_TG, "/start"))
    markup = bot.session.last_markup(ADMIN_TG)
    labels = {button.text for row in markup.keyboard for button in row}
    assert "⏳ Tasdiq kutmoqda" in labels
    assert "📅 Davr" in labels


async def test_reporter_cannot_open_admin_queue(db, bot, dispatcher):
    await _register_mechanic(dispatcher, bot)
    bot.session.clear()
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "/tasdiq"))
    assert "ruxsat etilmagan" in bot.session.last_text(MECHANIC_TG)


async def test_language_switch(db, bot, dispatcher):
    await _register_mechanic(dispatcher, bot)
    bot.session.clear()
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "/til"))
    data = bot.session.callback_data("lang", MECHANIC_TG)
    assert data is not None
    await feed(dispatcher, bot, ft.callback_update(MECHANIC_TG, "a:lang:0:ru"))

    async with SessionFactory() as session:
        employee = (
            await session.execute(sa.select(Employee).where(Employee.phone == MECHANIC_PHONE))
        ).scalar_one()
        assert employee.lang == "ru"


async def test_custom_work_name_without_catalog(db, bot, dispatcher):
    """Katalogda yo'q ish — o'z nomi bilan kiritiladi (allow_custom)."""
    await _register_mechanic(dispatcher, bot)
    submission = await _fill_report(dispatcher, bot, work_name="Maxsus payvandlash ishi")

    assert len(submission.lines) == 1
    line = submission.lines[0]
    assert line.name == "Maxsus payvandlash ishi"
    assert line.catalog_id is None
    assert line.proposed_amount == Decimal("250000.00")


# --- Mini App'dan yuklangan fotoni botda ko'rsatish (2026-08-01 xatosi) -------


async def test_admin_sees_photos_uploaded_from_miniapp(db, bot, dispatcher):
    """⚠️ Bot «Foto yo'q» derdi, holbuki Mini App'da 5 ta foto ko'rinardi.

    Sabab: `show_photos` `tg_file_id` bo'yicha filtrlardi, Mini App'dan
    yuklangan foto esa to'g'ridan-to'g'ri omborga tushadi va Telegram'ni
    ko'rmagan bo'ladi (`tg_file_id IS NULL`).
    """
    import hashlib

    from app.db.models import Media, MediaKind
    from app.domain.media import service as media_service

    # ombor + baza: Mini App yuklagandek media yasaymiz (tg_file_id YO'Q)
    async with SessionFactory() as session:
        employee = (
            await session.execute(sa.select(Employee).where(Employee.phone == MECHANIC_PHONE))
        ).scalars().one()
        vehicle = (await session.execute(sa.select(Vehicle))).scalars().one()
        template = (
            await session.execute(sa.select(Template).where(Template.code == "car_repair"))
        ).scalars().one()

        submission = Submission(
            number="WO-2026-000777",
            template_id=template.id,
            template_version=template.version,
            author_id=employee.id,
            subject_vehicle_id=vehicle.id,
            status=SubmissionStatus.SUBMITTED,
        )
        session.add(submission)
        await session.flush()

        payload = b"\xff\xd8\xff\xe0" + bytes(64)
        key = media_service.storage_key(
            submission, "photo_problem", hashlib.sha256(payload).hexdigest(), "image/jpeg"
        )
        await media_service.get_storage().put(key, payload, content_type="image/jpeg")
        session.add(
            Media(
                submission_id=submission.id,
                field_code="photo_problem",
                kind=MediaKind.problem,
                storage_key=key,
                mime="image/jpeg",
                size_bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
                uploaded_by=employee.id,
                tg_file_id=None,  # ⬅️ Mini App yo'li
            )
        )
        await session.commit()
        submission_id = submission.id

    bot.session.clear()
    await feed(dispatcher, bot, ft.callback_update(ADMIN_TG, f"a:photos:{submission_id}:"))

    methods = [name for name, _ in bot.session.requests]
    assert "sendMediaGroup" in methods, methods
    assert all("Foto yo'q" not in text for text in bot.session.sent_texts())

    # Telegram qaytargan file_id keshlanadi — keyingi safar ombor o'qilmaydi
    async with SessionFactory() as session:
        media = (await session.execute(sa.select(Media))).scalars().one()
        assert media.tg_file_id is not None
