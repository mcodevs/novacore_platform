"""Bot oqimi — **faqat kirish va bildirishnoma** (2026-08-01 doirasi).

Botda amal yo'q: hisobot yozish, ko'rib chiqish, narx kelishuvi, davr va
eksport Mini App'da (API testlari `test_api.py` da). Bu yerda qolgani:
telefon bog'lash, menyu, til va bildirishnoma tugmasi.

Telegram bilan aloqa soxta sessiya orqali — tarmoq kerak emas.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from aiogram.types import Update

from app.db.base import Base
from app.db.models import Employee, Submission, Vehicle
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


# --- Bot doirasi: amal yo'q, faqat kirish va Mini App ------------------------


async def _register_mechanic(dispatcher, bot) -> None:
    await feed(dispatcher, bot, ft.contact_update(MECHANIC_TG, MECHANIC_PHONE))


async def test_menu_opens_miniapp_and_has_no_actions(db, bot, dispatcher):
    """⚠️ 2026-08-01: botda amal yo'q. Menyu — Mini App + til + yordam.

    Ilgari menyuda «🚗 Mashina keldi», «⏳ Tasdiq kutmoqda», «📅 Davr» kabi
    amal tugmalari bor edi va ular Mini App ekranlari bilan takrorlanardi.
    """
    await _register_mechanic(dispatcher, bot)
    bot.session.clear()
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, "/start"))

    markup = bot.session.last_markup(MECHANIC_TG)
    labels = {button.text for row in markup.keyboard for button in row}
    assert labels == {"🧩 Mini App", "🌐 Til", "❓ Yordam"}


async def test_admin_menu_is_the_same_as_reporter(db, bot, dispatcher):
    """Rol farqi endi menyuda emas — Mini App ichida."""
    await feed(dispatcher, bot, ft.message_update(ADMIN_TG, "/start"))
    markup = bot.session.last_markup(ADMIN_TG)
    labels = {button.text for row in markup.keyboard for button in row}
    assert labels == {"🧩 Mini App", "🌐 Til", "❓ Yordam"}


@pytest.mark.parametrize(
    "command", ["/yangi", "/tasdiq", "/davr", "/eksport", "/hisob", "/mening", "/kunlik"]
)
async def test_removed_commands_no_longer_act(db, bot, dispatcher, command):
    """Eski buyruqlar amal bajarmaydi — fallback javob beradi."""
    await _register_mechanic(dispatcher, bot)
    bot.session.clear()
    await feed(dispatcher, bot, ft.message_update(MECHANIC_TG, command))

    text = bot.session.last_text(MECHANIC_TG)
    assert "Tushunmadim" in text or "Menyudan" in text


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


# --- Bildirishnoma: yagona «Ochish» tugmasi ----------------------------------


async def test_notification_has_single_open_button(db, bot, dispatcher, monkeypatch):
    """Bildirishnoma ostida faqat Mini App'ni ochish — tez amallar yo'q.

    Ilgari bu yerda «✅ Roziman» / «❌ Rozi emasman» bor edi; endi usta
    kartochkani ochib javob beradi (bitta amal — bitta joyda).
    """
    from app.bot import notifier
    from app.core.config import settings
    from app.db.models import Notification

    monkeypatch.setattr(settings, "miniapp_url", "https://example.test/app")
    await _register_mechanic(dispatcher, bot)

    async with SessionFactory() as session:
        employee = (
            await session.execute(sa.select(Employee).where(Employee.phone == MECHANIC_PHONE))
        ).scalars().one()
        notification = Notification(
            employee_id=employee.id,
            template_code="notify_price_proposed",
            payload={
                "submission_id": 42,
                "number": "WO-2026-000042",
                "vehicle": "01 A 123 BC",
                "proposed": "250000",
                "approved": "200000",
                "reason": "Bozor narxi arzonroq",
            },
        )
        text, markup = await notifier.render(session, notification, employee)

    assert "{" not in text  # shablon to'liq to'ldirilgan
    buttons = [button for row in markup.inline_keyboard for button in row]
    assert len(buttons) == 1
    assert buttons[0].web_app.url == "https://example.test/app?submission=42"
