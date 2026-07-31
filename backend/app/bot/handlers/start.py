"""Ro'yxatdan o'tish, til, yordam, menyu."""

from __future__ import annotations

import sqlalchemy as sa
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Contact, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot.callbacks import Act
from app.bot.middlewares import blocked_status_message
from app.bot.states import Registration
from app.core.config import settings
from app.core.i18n import t
from app.core.phone import normalize_phone
from app.db.models import Employee, RoleKind
from app.domain import audit

router = Router(name="start")

HELP_BY_KIND = {
    RoleKind.reporter: "help_reporter",
    RoleKind.admin: "help_admin",
    RoleKind.accountant: "help_accountant",
}


async def show_menu(message: Message, employee: Employee) -> None:
    lang = employee.lang
    await message.answer(
        t(
            "menu_title",
            lang,
            icon=employee.role.icon,
            role=employee.role.name(lang),
        ),
        reply_markup=kb.main_menu(employee),
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    await state.clear()
    if employee is not None:
        blocked = blocked_status_message(employee, employee.lang)
        if blocked:
            await message.answer(blocked, reply_markup=kb.REMOVE)
            return
        from app.bot.commands import set_commands_for

        await set_commands_for(message.bot, employee)
        await show_menu(message, employee)
        return

    await state.set_state(Registration.waiting_phone)
    await message.answer(t("start_greeting", lang), reply_markup=kb.phone_request(lang))


@router.message(F.contact)
async def handle_contact(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    contact: Contact = message.contact
    if employee is not None:
        await show_menu(message, employee)
        return

    # ❗ boshqa odamning kontaktini forward qilishning oldini oladi
    if contact.user_id != message.from_user.id:
        await message.answer(t("contact_mismatch", lang), reply_markup=kb.phone_request(lang))
        return

    phone = normalize_phone(contact.phone_number)
    found = (
        await session.execute(sa.select(Employee).where(Employee.phone == phone))
    ).scalar_one_or_none()

    if found is None or found.deleted_at is not None:
        await message.answer(t("not_in_registry", lang, phone=phone), reply_markup=kb.REMOVE)
        await audit.log(
            session,
            action="auth.not_in_registry",
            entity_type="employee",
            tg_user_id=message.from_user.id,
            after={"phone": phone},
        )
        return

    if found.tg_user_id is not None and found.tg_user_id != message.from_user.id:
        # tg_user_id almashtirish — faqat admin, sabab bilan
        await message.answer(t("account_taken", lang), reply_markup=kb.REMOVE)
        return

    blocked = blocked_status_message(found, found.lang)
    if blocked:
        await message.answer(blocked, reply_markup=kb.REMOVE)
        return

    found.tg_user_id = message.from_user.id
    found.tg_username = message.from_user.username
    if message.from_user.language_code and message.from_user.language_code.startswith("ru"):
        found.lang = "ru"
    await session.flush()

    await audit.log(
        session,
        action="auth.link_telegram",
        entity_type="employee",
        entity_id=found.id,
        actor_id=found.id,
        tg_user_id=message.from_user.id,
        after={"tg_user_id": message.from_user.id, "phone": phone},
    )
    await state.clear()

    from app.bot.commands import set_commands_for

    await set_commands_for(message.bot, found)
    await message.answer(
        t(
            "registered",
            found.lang,
            name=found.full_name,
            icon=found.role.icon,
            role=found.role.name(found.lang),
        ),
        reply_markup=kb.main_menu(found),
    )
    await message.answer(t(HELP_BY_KIND[found.role.kind], found.lang))


@router.message(Registration.waiting_phone)
async def waiting_phone_fallback(message: Message, lang: str) -> None:
    await message.answer(t("start_greeting", lang), reply_markup=kb.phone_request(lang))


@router.message(Command("til"))
@router.message(F.text.in_({t("menu_lang", "uz"), t("menu_lang", "ru")}))
async def cmd_lang(message: Message, employee: Employee | None, lang: str) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    await message.answer(t("lang_choose", lang), reply_markup=kb.lang_choice())


@router.callback_query(Act.filter(F.name == "lang"))
async def set_lang(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    employee.lang = callback_data.arg or "uz"
    await session.flush()

    from app.bot.commands import set_commands_for

    await set_commands_for(callback.bot, employee)
    await callback.answer(t("lang_changed", employee.lang))
    await callback.message.answer(
        t("lang_changed", employee.lang), reply_markup=kb.main_menu(employee)
    )


@router.message(Command("yordam"))
@router.message(F.text.in_({t("menu_help", "uz"), t("menu_help", "ru")}))
async def cmd_help(message: Message, employee: Employee | None, lang: str) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    await message.answer(t(HELP_BY_KIND[employee.role.kind], employee.lang))


@router.message(Command("app"))
@router.message(F.text.in_({t("menu_app", "uz"), t("menu_app", "ru")}))
async def cmd_app(message: Message, employee: Employee | None, lang: str) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    markup = kb.open_app(employee.lang)
    if markup is None:
        await message.answer(t("app_not_configured", employee.lang))
        return
    await message.answer(settings.miniapp_url, reply_markup=markup)


@router.message(Command("menu"))
async def cmd_menu(message: Message, employee: Employee | None, lang: str) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    await show_menu(message, employee)
