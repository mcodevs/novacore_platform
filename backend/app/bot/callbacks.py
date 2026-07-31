"""Tipli callback ma'lumotlari."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class Act(CallbackData, prefix="a"):
    """Umumiy amal: `name` — amal kodi, `id` — ob'ekt, `arg` — qo'shimcha."""

    name: str
    id: int = 0
    arg: str = ""
