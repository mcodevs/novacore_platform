"""FSM holatlari — bitta qoldi.

Botda amal yo'q (2026-08-01), shuning uchun forma, ko'rik, narx kelishuvi va
davr holatlari o'chirildi. Qolgani — ro'yxatdan o'tish: telefon kutish.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_phone = State()
