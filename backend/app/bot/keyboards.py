"""Klaviaturalar. Qo'llar moyli, qo'lqopda — tugmalar katta, yozish kam."""

from __future__ import annotations

from decimal import Decimal

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.core.config import settings
from app.core.i18n import fmt_money, t
from app.db.models import Employee, RoleKind
from app.bot.callbacks import Act

REMOVE = ReplyKeyboardRemove()


def phone_request(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=t("btn_share_phone", lang), request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def main_menu(employee: Employee) -> ReplyKeyboardMarkup:
    """Menyu **rolga qarab** o'zgaradi — usta admin tugmalarini ko'rmaydi."""
    lang = employee.lang
    kind = employee.role.kind
    builder = ReplyKeyboardBuilder()

    if kind in (RoleKind.reporter, RoleKind.admin):
        builder.row(KeyboardButton(text=t("menu_car_arrived", lang)))
    if kind == RoleKind.admin:
        builder.row(
            KeyboardButton(text=t("menu_pending", lang)),
            KeyboardButton(text=t("menu_daily", lang)),
        )
    if kind in (RoleKind.reporter, RoleKind.admin):
        builder.row(
            KeyboardButton(text=t("menu_negotiation", lang)),
            KeyboardButton(text=t("menu_drafts", lang)),
        )
        builder.row(
            KeyboardButton(text=t("menu_my_reports", lang)),
            KeyboardButton(text=t("menu_my_money", lang)),
        )
    if kind in (RoleKind.admin, RoleKind.accountant):
        builder.row(
            KeyboardButton(text=t("menu_period", lang)),
            KeyboardButton(text=t("menu_export", lang)),
        )
    if kind == RoleKind.accountant:
        builder.row(KeyboardButton(text=t("menu_daily", lang)))

    builder.row(
        KeyboardButton(text=t("menu_lang", lang)),
        KeyboardButton(text=t("menu_help", lang)),
    )
    return builder.as_markup(resize_keyboard=True)


def cancel_only(lang: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=t("cancel", lang)))
    return builder.as_markup(resize_keyboard=True)


def photo_step(lang: str, *, can_finish: bool) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    if can_finish:
        builder.row(KeyboardButton(text=t("done", lang)))
    builder.row(KeyboardButton(text=t("cancel", lang)))
    return builder.as_markup(resize_keyboard=True)


def skip_or_cancel(lang: str, *, can_skip: bool) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    if can_skip:
        builder.row(KeyboardButton(text=t("skip", lang)))
    builder.row(KeyboardButton(text=t("cancel", lang)))
    return builder.as_markup(resize_keyboard=True)


def lang_choice() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data=Act(name="lang", arg="uz").pack()),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data=Act(name="lang", arg="ru").pack()),
    )
    return builder.as_markup()


def open_app(lang: str) -> InlineKeyboardMarkup | None:
    if not settings.miniapp_url:
        return None
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=t("open_app", lang), web_app=WebAppInfo(url=settings.miniapp_url)
        )
    )
    return builder.as_markup()


def draft_prompt(lang: str, submission_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("draft_continue", lang),
            callback_data=Act(name="draft_continue", id=submission_id).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("draft_delete", lang),
            callback_data=Act(name="draft_delete", id=submission_id).pack(),
        )
    )
    return builder.as_markup()


def template_choice(templates: list[tuple[int, str]], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for template_id, title in templates:
        builder.row(
            InlineKeyboardButton(
                text=title, callback_data=Act(name="tpl", id=template_id).pack()
            )
        )
    return builder.as_markup()


def select_options(options: list[tuple[str, str]], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, title in options:
        builder.row(
            InlineKeyboardButton(
                text=title, callback_data=Act(name="opt", arg=code).pack()
            )
        )
    return builder.as_markup()


def bool_choice(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("yes", lang), callback_data=Act(name="opt", arg="1").pack()),
        InlineKeyboardButton(text=t("no", lang), callback_data=Act(name="opt", arg="0").pack()),
    )
    return builder.as_markup()


def lines_menu(lang: str, *, items: list[tuple[int, str]], can_finish: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("line_add", lang), callback_data=Act(name="line_add").pack())
    )
    for line_id, title in items:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {title}",
                callback_data=Act(name="line_del", id=line_id).pack(),
            )
        )
    if can_finish:
        builder.row(
            InlineKeyboardButton(
                text=t("done", lang), callback_data=Act(name="lines_done").pack()
            )
        )
    return builder.as_markup()


def catalog_choice(
    items: list[tuple[int, str]],
    lang: str,
    *,
    custom_name: str | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for catalog_id, title in items:
        builder.row(
            InlineKeyboardButton(
                text=title, callback_data=Act(name="cat", id=catalog_id).pack()
            )
        )
    if custom_name:
        # katalogda yo'q ishni o'z nomi bilan kiritish
        builder.row(
            InlineKeyboardButton(
                text=t("line_use_custom", lang, name=submission_title(custom_name)),
                callback_data=Act(name="cat", id=0).pack(),
            )
        )
    return builder.as_markup()


def submission_title(name: str, limit: int = 28) -> str:
    return name if len(name) <= limit else name[: limit - 1] + "…"


def form_actions(lang: str, submission_id: int, *, has_left: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not has_left:
        builder.row(
            InlineKeyboardButton(
                text=t("btn_car_left", lang),
                callback_data=Act(name="mark_left", id=submission_id).pack(),
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=t("btn_submit", lang),
                callback_data=Act(name="submit", id=submission_id).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text=t("btn_preview", lang),
            callback_data=Act(name="preview", id=submission_id).pack(),
        )
    )
    return builder.as_markup()


def review_actions(lang: str, submission_id: int, *, has_photos: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_approve", lang),
            callback_data=Act(name="approve", id=submission_id).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("btn_reduce", lang),
            callback_data=Act(name="reduce", id=submission_id).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("btn_reopen", lang),
            callback_data=Act(name="reopen", id=submission_id).pack(),
        ),
        InlineKeyboardButton(
            text=t("btn_reject", lang),
            callback_data=Act(name="reject", id=submission_id).pack(),
        ),
    )
    if has_photos:
        builder.row(
            InlineKeyboardButton(
                text=t("btn_photos", lang),
                callback_data=Act(name="photos", id=submission_id).pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text=t("btn_history", lang),
            callback_data=Act(name="history", id=submission_id).pack(),
        )
    )
    return builder.as_markup()


def dispute_actions(lang: str, submission_id: int) -> InlineKeyboardMarkup:
    """Nizodan keyin admin: yakuniy qaror yoki yangi taklif."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_final_decision", lang),
            callback_data=Act(name="final", id=submission_id).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("btn_reduce", lang),
            callback_data=Act(name="reduce", id=submission_id).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("btn_reopen", lang),
            callback_data=Act(name="reopen", id=submission_id).pack(),
        )
    )
    return builder.as_markup()


def line_choice_for_reduce(
    lines: list[tuple[int, str, Decimal]], lang: str, submission_id: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for line_id, name, amount in lines:
        builder.row(
            InlineKeyboardButton(
                text=f"{name} — {fmt_money(amount, lang)}",
                callback_data=Act(name="reduce_line", id=line_id, arg=str(submission_id)).pack(),
            )
        )
    return builder.as_markup()


def quick_amounts(amounts: list[Decimal], lang: str) -> InlineKeyboardMarkup | None:
    if not amounts:
        return None
    builder = InlineKeyboardBuilder()
    builder.row(
        *[
            InlineKeyboardButton(
                text=fmt_money(value, lang),
                callback_data=Act(name="quick", arg=str(int(value))).pack(),
            )
            for value in amounts
        ]
    )
    return builder.as_markup()


def negotiation_actions(lang: str, submission_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_accept_price", lang),
            callback_data=Act(name="accept_price", id=submission_id).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("btn_dispute_price", lang),
            callback_data=Act(name="dispute_price", id=submission_id).pack(),
        )
    )
    return builder.as_markup()


def open_submission(lang: str, submission_id: int, *, admin: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_preview", lang),
            callback_data=Act(name="open" if not admin else "review", id=submission_id).pack(),
        )
    )
    return builder.as_markup()


def fix_submission(lang: str, submission_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_fix", lang),
            callback_data=Act(name="draft_continue", id=submission_id).pack(),
        )
    )
    return builder.as_markup()


def submissions_list(
    items: list[tuple[int, str]], lang: str, *, admin: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for submission_id, title in items:
        builder.row(
            InlineKeyboardButton(
                text=title,
                callback_data=Act(
                    name="review" if admin else "open", id=submission_id
                ).pack(),
            )
        )
    return builder.as_markup()


def period_actions(lang: str, period_id: int, *, can_close: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("btn_precheck", lang),
            callback_data=Act(name="precheck", id=period_id).pack(),
        )
    )
    if can_close:
        builder.row(
            InlineKeyboardButton(
                text=t("btn_close_period", lang),
                callback_data=Act(name="close_period", id=period_id).pack(),
            )
        )
    return builder.as_markup()


def export_choice(lang: str, period_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, key in (
        ("submissions", "export_submissions"),
        ("payouts", "export_payouts"),
        ("savings", "export_savings"),
    ):
        builder.row(
            InlineKeyboardButton(
                text=t(key, lang),
                callback_data=Act(name="export", id=period_id, arg=code).pack(),
            )
        )
    return builder.as_markup()
