"""Fallback — hech qaysi handlerga tushmagan xabarlar."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards as kb
from app.core.i18n import t
from app.db.models import Employee

router = Router(name="common")


@router.message(F.text)
async def fallback(message: Message, employee: Employee | None, lang: str) -> None:
    if employee is None:
        await message.answer(t("need_start", lang), reply_markup=kb.phone_request(lang))
        return
    await message.answer(t("unknown_command", employee.lang), reply_markup=kb.main_menu(employee))


@router.message()
async def fallback_any(message: Message, employee: Employee | None, lang: str) -> None:
    if employee is None:
        await message.answer(t("need_start", lang), reply_markup=kb.phone_request(lang))
        return
    await message.answer(t("unknown_command", employee.lang))


@router.callback_query()
async def fallback_callback(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()
