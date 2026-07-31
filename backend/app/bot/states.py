"""FSM holatlari. Saqlash — xotirada; qoralamaning o'zi bazada (Redis yo'q)."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_phone = State()


class Form(StatesGroup):
    """Ketma-ket forma: qaysi maydon kutilayotgani `state.data['field']`da."""

    waiting_value = State()
    waiting_photo = State()


class Lines(StatesGroup):
    waiting_name = State()
    waiting_qty = State()
    waiting_price = State()


class Review(StatesGroup):
    """Admin: narxni kamaytirish va qarorlar."""

    waiting_amount = State()
    waiting_reason = State()
    waiting_reject_reason = State()
    waiting_reopen_reason = State()
    waiting_final_comment = State()


class Negotiation(StatesGroup):
    waiting_dispute_comment = State()


class PeriodFlow(StatesGroup):
    waiting_reopen_reason = State()
