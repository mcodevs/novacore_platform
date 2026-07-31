"""Hisobot yaratish — shablon bo'yicha ketma-ket forma (bot ichida to'liq oqim).

Bu — Mini App'siz ham ishlaydigan zaxira va asosiy kanal: usta hisobotni
to'liq shu yerda to'ldiradi (foto, izoh, o'z narxi), keyin yuboradi.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import sqlalchemy as sa
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot.callbacks import Act
from app.bot.handlers.start import show_menu
from app.bot.states import Form, Lines
from app.bot.texts import render_card, submission_line_title
from app.core.errors import DomainError, ValidationFailed
from app.core.i18n import fmt_dt, fmt_duration, fmt_money, t
from app.core.phone import normalize_plate
from app.db.base import as_utc, utcnow
from app.db.models import (
    CatalogItem,
    Employee,
    LineKind,
    MediaKind,
    MediaSource,
    PartsCatalog,
    Submission,
    SubmissionStatus,
    Template,
    Vehicle,
    WorkCatalog,
)
from app.domain.media import service as media_service
from app.domain.submission import service as submission_service
from app.domain.template import builder, engine
from app.domain.template.engine import FieldSpec, TemplateSchema

router = Router(name="report")

MENU_NEW = {t("menu_car_arrived", "uz"), t("menu_car_arrived", "ru")}
MENU_DRAFTS = {t("menu_drafts", "uz"), t("menu_drafts", "ru")}
CANCEL_WORDS = {t("cancel", "uz"), t("cancel", "ru")}
DONE_WORDS = {t("done", "uz"), t("done", "ru")}
SKIP_WORDS = {t("skip", "uz"), t("skip", "ru")}
CATALOG_PAGE = 8


# --- Yordamchilar ------------------------------------------------------------


async def visible_templates(session: AsyncSession, employee: Employee) -> list[Template]:
    """Rolga biriktirilgan va nashr etilgan shablonlar (qoralama ko'rinmaydi)."""
    return await builder.visible_for(session, employee)


async def load_draft(session: AsyncSession, submission_id: int, employee: Employee) -> Submission:
    submission = await submission_service.get_for_actor(session, submission_id, employee)
    submission_service.ensure_editable(submission, employee)
    return submission


async def ask_next(
    message: Message,
    session: AsyncSession,
    employee: Employee,
    submission: Submission,
    state: FSMContext,
) -> None:
    """Keyingi to'ldirilmagan maydonni so'raydi yoki formani yakunlaydi."""
    lang = employee.lang
    schema = await engine.schema_for_submission(session, submission)
    spec = engine.next_field(schema, submission)
    await state.update_data(submission_id=submission.id)

    if spec is None:
        await state.set_state(None)
        await message.answer(
            render_card(submission, lang),
            reply_markup=kb.main_menu(employee),
        )
        await message.answer(
            t("form_complete", lang),
            reply_markup=kb.form_actions(
                lang, submission.id, has_left=submission.left_at is not None
            ),
        )
        return

    await _ask_field(message, session, employee, submission, spec, schema, state)


async def _ask_field(
    message: Message,
    session: AsyncSession,
    employee: Employee,
    submission: Submission,
    spec: FieldSpec,
    schema: TemplateSchema,
    state: FSMContext,
) -> None:
    lang = employee.lang
    label = spec.label(lang)
    hint = spec.hint(lang)
    await state.update_data(submission_id=submission.id, field=spec.code)

    if spec.type == "vehicle_picker":
        await state.set_state(Form.waiting_value)
        await message.answer(t("ask_plate", lang), reply_markup=kb.cancel_only(lang))
        return

    if spec.type == "photo":
        current = len((submission.data or {}).get(spec.code) or [])
        await state.set_state(Form.waiting_photo)
        await message.answer(
            t(
                "ask_photo",
                lang,
                label=label,
                hint=hint,
                min=max(spec.photo_min, 1 if spec.required else 0),
                max=spec.photo_max,
                done=t("done", lang),
            ),
            reply_markup=kb.photo_step(
                lang, can_finish=current >= spec.photo_min or not spec.required
            ),
        )
        return

    if spec.type == "select":
        options = await _select_options(session, spec, lang)
        await state.set_state(Form.waiting_value)
        await message.answer(
            t("ask_select", lang, label=label, hint=hint),
            reply_markup=kb.select_options(options, lang),
        )
        return

    if spec.type == "submission_picker":
        options = await _linkable_options(session, employee, submission, spec, lang)
        await state.set_state(Form.waiting_value)
        if not options:
            await message.answer(
                t("linkable_empty", lang, label=label),
                reply_markup=kb.skip_or_cancel(lang, can_skip=not spec.required),
            )
            return
        await message.answer(
            t("ask_select", lang, label=label, hint=hint),
            reply_markup=kb.select_options(options, lang),
        )
        return

    if spec.type == "bool":
        await state.set_state(Form.waiting_value)
        await message.answer(
            t("ask_bool", lang, label=label, hint=hint), reply_markup=kb.bool_choice(lang)
        )
        return

    if spec.type == "lines":
        await state.set_state(None)
        await _show_lines(message, session, employee, submission, spec)
        return

    key = {
        "number": "ask_number",
        "money": "ask_money",
        "text": "ask_text",
        "textarea": "ask_text",
    }.get(spec.type, "ask_text")
    await state.set_state(Form.waiting_value)
    await message.answer(
        t(key, lang, label=label, hint=hint),
        reply_markup=kb.skip_or_cancel(lang, can_skip=not spec.required),
    )


async def _select_options(
    session: AsyncSession, spec: FieldSpec, lang: str
) -> list[tuple[str, str]]:
    source = spec.options.get("source", "")
    if source.startswith("catalog:"):
        catalog = source.split(":", 1)[1]
        rows = (
            await session.execute(
                sa.select(CatalogItem)
                .where(CatalogItem.catalog == catalog, CatalogItem.is_active.is_(True))
                .order_by(CatalogItem.sort)
            )
        ).scalars().all()
        return [(row.code, f"{row.icon or ''} {row.name(lang)}".strip()) for row in rows]
    choices = spec.options.get("choices") or []
    result = []
    for choice in choices:
        if isinstance(choice, dict):
            label = choice.get("label", {})
            result.append(
                (choice["code"], label.get(lang) or label.get("uz") or choice["code"])
            )
        else:
            result.append((str(choice), str(choice)))
    return result


async def _linkable_options(
    session: AsyncSession,
    employee: Employee,
    submission: Submission,
    spec: FieldSpec,
    lang: str,
) -> list[tuple[str, str]]:
    """Bog'liq hisobot nomzodlari — «WO-2026-000042 · 01 A 123 BC · Usta»."""
    if submission.subject_vehicle_id is None:
        return []
    rows = await submission_service.linkable(
        session,
        employee,
        template_code=spec.options.get("template_code"),
        vehicle_id=submission.subject_vehicle_id,
        exclude_id=submission.id,
        limit=8,
    )
    return [
        (
            str(row.id),
            f"{row.number} · {fmt_dt(row.submitted_at, lang) if row.submitted_at else '—'}"
            f" · {row.author.full_name if row.author else ''}",
        )
        for row in rows
    ]


async def _show_lines(
    message: Message,
    session: AsyncSession,
    employee: Employee,
    submission: Submission,
    spec: FieldSpec,
) -> None:
    lang = employee.lang
    await session.refresh(submission)
    kind = spec.line_kind
    lines = [ln for ln in submission.lines if ln.kind == kind]

    title = t("lines_labor_title" if kind == LineKind.labor else "lines_part_title", lang)
    if lines:
        listing = "\n".join(
            f"• {line.name} — {fmt_money(line.proposed_amount, lang)}"
            if spec.has_price_field
            else f"• {line.name} ×{line.qty.normalize()}"
            for line in lines
        )
        title += t("lines_current", lang, list=listing)
    else:
        title += t("lines_empty", lang)

    can_finish = bool(lines) or not spec.required
    await message.answer(
        title,
        reply_markup=kb.lines_menu(
            lang,
            items=[(line.id, submission_line_title(line.name)) for line in lines],
            can_finish=can_finish,
        ),
    )


# --- Yangi hisobot -----------------------------------------------------------


@router.message(Command("yangi"))
@router.message(F.text.in_(MENU_NEW))
async def start_report(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    await state.clear()

    draft = await submission_service.active_draft(session, employee)
    if draft is not None:
        await message.answer(
            t("draft_exists", employee.lang, number=draft.number),
            reply_markup=kb.draft_prompt(employee.lang, draft.id),
        )
        return

    templates = await visible_templates(session, employee)
    if not templates:
        await message.answer(t("no_templates", employee.lang))
        return
    if len(templates) == 1:
        await _create_and_start(message, state, session, employee, templates[0])
        return

    await message.answer(
        t("choose_template", employee.lang),
        reply_markup=kb.template_choice(
            [(tpl.id, f"{tpl.icon} {tpl.name(employee.lang)}") for tpl in templates],
            employee.lang,
        ),
    )


async def _create_and_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee,
    template: Template,
) -> None:
    submission = await submission_service.create_draft(session, employee, template)
    await message.answer(
        t(
            "arrived_registered",
            employee.lang,
            time=fmt_dt(submission.arrived_at, employee.lang),
            number=submission.number,
        ),
        reply_markup=kb.cancel_only(employee.lang),
    )
    await ask_next(message, session, employee, submission, state)


@router.callback_query(Act.filter(F.name == "tpl"))
async def choose_template(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    template = await session.get(Template, callback_data.id)
    if template is None:
        await callback.answer(t("not_found", employee.lang), show_alert=True)
        return
    await callback.answer()
    await _create_and_start(callback.message, state, session, employee, template)


@router.callback_query(Act.filter(F.name == "draft_continue"))
async def continue_draft(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await load_draft(session, callback_data.id, employee)
    await callback.answer()
    await ask_next(callback.message, session, employee, submission, state)


@router.callback_query(Act.filter(F.name == "draft_delete"))
async def drop_draft(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    await submission_service.delete_draft(session, submission, employee)
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        t("draft_deleted", employee.lang), reply_markup=kb.main_menu(employee)
    )


@router.message(F.text.in_(MENU_DRAFTS))
async def list_drafts(
    message: Message, session: AsyncSession, employee: Employee | None, lang: str
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    drafts = await submission_service.list_for_employee(
        session,
        employee,
        statuses=(SubmissionStatus.DRAFT, SubmissionStatus.REOPENED),
    )
    drafts = [d for d in drafts if d.author_id == employee.id]
    if not drafts:
        await message.answer(t("no_drafts", employee.lang))
        return

    for draft in drafts:
        await message.answer(
            f"<code>{draft.number}</code> · {fmt_dt(draft.arrived_at, employee.lang)}",
            reply_markup=kb.draft_prompt(employee.lang, draft.id),
        )


# --- Bekor qilish ------------------------------------------------------------


@router.message(F.text.in_(CANCEL_WORDS))
async def cancel_flow(
    message: Message, state: FSMContext, employee: Employee | None, lang: str
) -> None:
    await state.clear()
    if employee is None:
        await message.answer(t("cancelled", lang))
        return
    await message.answer(t("cancelled", employee.lang))
    await show_menu(message, employee)


# --- Maydon javoblari --------------------------------------------------------


@router.message(Form.waiting_value, F.text)
async def handle_value(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", ""))
    if spec is None:
        await ask_next(message, session, employee, submission, state)
        return

    text = (message.text or "").strip()
    lang = employee.lang

    if text in SKIP_WORDS and not spec.required:
        engine.set_value(submission, spec.code, None)
        engine.mark_done(submission, spec.code)
        await session.flush()
        await ask_next(message, session, employee, submission, state)
        return

    if spec.type == "vehicle_picker":
        await _handle_plate(message, session, employee, submission, spec, state, text)
        return

    if spec.type in ("number", "money"):
        try:
            value = Decimal(text.replace(" ", "").replace(",", "."))
        except (InvalidOperation, ValueError):
            await message.answer(
                t("invalid_money" if spec.type == "money" else "invalid_number", lang)
            )
            return
        minimum = spec.validation.get("min")
        maximum = spec.validation.get("max")
        if minimum is not None and value < Decimal(str(minimum)):
            await message.answer(t("value_too_small", lang, min=minimum))
            return
        if maximum is not None and value > Decimal(str(maximum)):
            await message.answer(t("value_too_big", lang, max=maximum))
            return
        if spec.validation.get("monotonic_for_vehicle") and submission.subject_vehicle_id:
            previous = await _previous_odometer(session, submission)
            if previous is not None and value < previous:
                await message.answer(t("odometer_decreased", lang, prev=previous))
                return
        engine.set_value(
            submission, spec.code, int(value) if spec.type == "number" else str(value)
        )
    else:
        min_len = spec.validation.get("min_length")
        if min_len and len(text) < int(min_len):
            await message.answer(t("text_too_short", lang, min=min_len, n=len(text)))
            return
        max_len = spec.validation.get("max_length")
        if max_len and len(text) > int(max_len):
            await message.answer(t("value_too_big", lang, max=max_len))
            return
        engine.set_value(submission, spec.code, text)

    await session.flush()
    await ask_next(message, session, employee, submission, state)


async def _previous_odometer(session: AsyncSession, submission: Submission) -> int | None:
    value = (
        await session.execute(
            sa.select(sa.func.max(Submission.odometer_km)).where(
                Submission.subject_vehicle_id == submission.subject_vehicle_id,
                Submission.id != submission.id,
                Submission.deleted_at.is_(None),
                Submission.status.not_in([SubmissionStatus.DRAFT, SubmissionStatus.REJECTED]),
            )
        )
    ).scalar_one_or_none()
    return int(value) if value is not None else None


async def _handle_plate(
    message: Message,
    session: AsyncSession,
    employee: Employee,
    submission: Submission,
    spec: FieldSpec,
    state: FSMContext,
    text: str,
) -> None:
    lang = employee.lang
    plate = normalize_plate(text)
    vehicle = (
        await session.execute(sa.select(Vehicle).where(Vehicle.plate_number == plate))
    ).scalar_one_or_none()
    if vehicle is None or vehicle.deleted_at is not None:
        await message.answer(t("vehicle_not_found", lang, plate=plate or text))
        return

    engine.set_value(
        submission, spec.code, {"vehicle_id": vehicle.id, "plate": vehicle.plate_number}
    )
    await submission_service.attach_vehicle(session, submission, vehicle)
    await session.flush()

    extra = ""
    last = (
        await session.execute(
            sa.select(Submission)
            .where(
                Submission.subject_vehicle_id == vehicle.id,
                Submission.id != submission.id,
                Submission.deleted_at.is_(None),
                Submission.submitted_at.is_not(None),
            )
            .order_by(Submission.submitted_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if last is not None and last.submitted_at is not None:
        days = (utcnow() - as_utc(last.submitted_at)).days
        extra += t("vehicle_ctx_last_repair", lang, days=days)
    month_count = (
        await session.execute(
            sa.select(sa.func.count(Submission.id)).where(
                Submission.subject_vehicle_id == vehicle.id,
                Submission.id != submission.id,
                Submission.deleted_at.is_(None),
                Submission.period_id == submission.period_id,
            )
        )
    ).scalar_one()
    if month_count:
        extra += t("vehicle_ctx_month_count", lang, n=int(month_count) + 1)
    if vehicle.current_driver_name:
        extra += t("vehicle_ctx_driver", lang, name=vehicle.current_driver_name)

    await message.answer(t("vehicle_found", lang, title=vehicle.title, extra=extra))
    await ask_next(message, session, employee, submission, state)


@router.callback_query(Act.filter(F.name == "opt"), Form.waiting_value)
async def handle_option(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", ""))
    if spec is None:
        await callback.answer()
        return

    value: object = callback_data.arg
    if spec.type == "bool":
        value = callback_data.arg == "1"
    elif spec.type == "submission_picker":
        value = {"submission_id": int(callback_data.arg)}
    engine.set_value(submission, spec.code, value)
    await session.flush()
    await callback.answer()
    await ask_next(callback.message, session, employee, submission, state)


# --- Fotolar -----------------------------------------------------------------


@router.message(Form.waiting_photo, F.photo)
async def handle_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", ""))
    if spec is None or spec.type != "photo":
        await ask_next(message, session, employee, submission, state)
        return

    lang = employee.lang
    current = list((submission.data or {}).get(spec.code) or [])
    if len(current) >= spec.photo_max:
        await message.answer(
            t("photo_max_reached", lang, max=spec.photo_max, done=t("done", lang))
        )
        return

    photo = message.photo[-1]
    buffer = await message.bot.download(photo.file_id)
    payload = buffer.read()

    media = await media_service.store_bytes(
        session,
        submission=submission,
        uploader=employee,
        field_code=spec.code,
        data=payload,
        kind=MediaKind(spec.options.get("kind", "other")),
        tg_file_id=photo.file_id,
        width=photo.width,
        height=photo.height,
        # Telegram foto siqadi va EXIF'ni olib tashlaydi — manba noma'lum
        source=MediaSource.unknown,
    )
    await session.refresh(submission)
    engine.append_media_id(submission, spec.code, media.id)
    await session.flush()

    count = len((submission.data or {}).get(spec.code) or [])
    await message.answer(
        t("photo_saved", lang, n=count, max=spec.photo_max),
        reply_markup=kb.photo_step(lang, can_finish=count >= max(spec.photo_min, 1)),
    )
    if count >= spec.photo_max:
        engine.mark_done(submission, spec.code)
        await session.flush()
        await ask_next(message, session, employee, submission, state)


@router.message(Form.waiting_photo, F.text)
async def handle_photo_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    text = (message.text or "").strip()
    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", ""))
    lang = employee.lang
    if spec is None:
        await ask_next(message, session, employee, submission, state)
        return

    if text in DONE_WORDS:
        count = len((submission.data or {}).get(spec.code) or [])
        minimum = max(spec.photo_min, 1) if spec.required else spec.photo_min
        if count < minimum:
            await message.answer(t("photo_need_more", lang, min=minimum, n=count))
            return
        engine.mark_done(submission, spec.code)
        await session.flush()
        await ask_next(message, session, employee, submission, state)
        return

    await message.answer(t("photo_expected", lang, done=t("done", lang)))


# --- Qatorlar (ishlar / qismlar) ---------------------------------------------


@router.callback_query(Act.filter(F.name == "line_add"))
async def line_add(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", "")) or _current_lines_spec(schema, submission)
    if spec is None:
        await callback.answer()
        return

    lang = employee.lang
    await state.update_data(field=spec.code, submission_id=submission.id)
    await state.set_state(Lines.waiting_name)

    items = await _catalog_items(session, spec, lang)
    await callback.answer()
    await callback.message.answer(
        t("line_ask_name" if spec.line_kind == LineKind.labor else "line_ask_name_part", lang),
        reply_markup=kb.catalog_choice(items, lang),
    )


def _current_lines_spec(schema: TemplateSchema, submission: Submission) -> FieldSpec | None:
    for spec in schema.lines_fields():
        if not (submission.data or {}).get("_done", {}).get(spec.code):
            return spec
    return None


async def _catalog_items(
    session: AsyncSession, spec: FieldSpec, lang: str, query: str | None = None
) -> list[tuple[int, str]]:
    catalog = spec.options.get("catalog")
    if catalog == "work_catalog":
        stmt = sa.select(WorkCatalog).where(WorkCatalog.is_active.is_(True))
        if query:
            like = f"%{query.lower()}%"
            stmt = stmt.where(
                sa.or_(
                    sa.func.lower(WorkCatalog.name_uz).like(like),
                    sa.func.lower(WorkCatalog.name_ru).like(like),
                )
            )
        rows = (await session.execute(stmt.limit(CATALOG_PAGE))).scalars().all()
        # ⚠️ R3: `reference_price` bu yerda KO'RSATILMAYDI — faqat nom
        return [(row.id, row.name(lang)) for row in rows]

    stmt = sa.select(PartsCatalog).where(PartsCatalog.is_active.is_(True))
    if query:
        like = f"%{query.lower()}%"
        stmt = stmt.where(
            sa.or_(
                sa.func.lower(PartsCatalog.name_uz).like(like),
                sa.func.lower(PartsCatalog.name_ru).like(like),
            )
        )
    rows = (await session.execute(stmt.limit(CATALOG_PAGE))).scalars().all()
    return [(row.id, row.name(lang)) for row in rows]


@router.message(Lines.waiting_name, F.text)
async def line_name_typed(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        await message.answer(t("need_start", lang))
        return
    text = (message.text or "").strip()
    if text in CANCEL_WORDS:
        await cancel_flow(message, state, employee, lang)
        return

    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", ""))
    if spec is None:
        return
    lang = employee.lang

    allow_custom = bool(spec.options.get("allow_custom", True))
    matches = await _catalog_items(session, spec, lang, query=text)
    if matches:
        # katalogdan tanlash yoki o'z nomi bilan davom etish
        await state.update_data(custom_name=text)
        await message.answer(
            t("catalog_search_hint", lang),
            reply_markup=kb.catalog_choice(
                matches, lang, custom_name=text if allow_custom else None
            ),
        )
        return

    if not allow_custom:
        await message.answer(t("nothing_found", lang))
        return

    await _line_after_name(message, state, session, employee, submission, spec, text, None)


@router.callback_query(Act.filter(F.name == "cat"), Lines.waiting_name)
async def line_name_from_catalog(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", ""))
    if spec is None:
        await callback.answer()
        return

    lang = employee.lang
    if callback_data.id == 0:  # «O'z nomim»
        data = await state.get_data()
        custom = (data.get("custom_name") or "").strip()
        if not custom:
            await callback.answer(t("not_found", lang), show_alert=True)
            return
        await callback.answer()
        await _line_after_name(
            callback.message, state, session, employee, submission, spec, custom, None
        )
        return

    if spec.options.get("catalog") == "work_catalog":
        row = await session.get(WorkCatalog, callback_data.id)
    else:
        row = await session.get(PartsCatalog, callback_data.id)
    if row is None:
        await callback.answer(t("not_found", lang), show_alert=True)
        return

    await callback.answer()
    await _line_after_name(
        callback.message, state, session, employee, submission, spec, row.name(lang), row.id
    )


async def _line_after_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee,
    submission: Submission,
    spec: FieldSpec,
    name: str,
    catalog_id: int | None,
) -> None:
    lang = employee.lang
    await state.update_data(line_name=name, line_catalog_id=catalog_id, line_qty="1")

    if spec.line_kind == LineKind.part:
        await state.set_state(Lines.waiting_qty)
        await message.answer(t("line_ask_qty", lang), reply_markup=kb.cancel_only(lang))
        return

    await _ask_line_price(message, state, session, employee, submission, spec, name, catalog_id)


async def _ask_line_price(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee,
    submission: Submission,
    spec: FieldSpec,
    name: str,
    catalog_id: int | None,
) -> None:
    """⚠️ Tayanch narx ko'rsatilmaydi (R3) — faqat xodimning **o'z** oldingi narxi."""
    lang = employee.lang
    if not spec.has_price_field:
        await _store_line(message, state, session, employee, submission, spec)
        return

    own_history = ""
    if catalog_id is not None:
        from app.db.models import SubmissionLine

        previous = (
            await session.execute(
                sa.select(SubmissionLine)
                .join(Submission, Submission.id == SubmissionLine.submission_id)
                .where(
                    Submission.author_id == employee.id,
                    SubmissionLine.catalog_id == catalog_id,
                    SubmissionLine.kind == spec.line_kind,
                )
                .order_by(SubmissionLine.id.desc())
                .limit(1)
            )
        ).scalars().first()
        if previous is not None:
            own_history = t(
                "own_price_history", lang, amount=fmt_money(previous.proposed_amount, lang)
            )

    await state.set_state(Lines.waiting_price)
    await message.answer(
        t("line_ask_price", lang, name=name, own_history=own_history),
        reply_markup=kb.cancel_only(lang),
    )


@router.message(Lines.waiting_qty, F.text)
async def line_qty(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        return
    text = (message.text or "").strip()
    if text in CANCEL_WORDS:
        await cancel_flow(message, state, employee, lang)
        return
    try:
        qty = Decimal(text.replace(",", "."))
    except (InvalidOperation, ValueError):
        await message.answer(t("invalid_number", employee.lang))
        return
    if qty <= 0:
        await message.answer(t("invalid_number", employee.lang))
        return

    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", ""))
    if spec is None:
        return
    await state.update_data(line_qty=str(qty))

    if spec.has_price_field:
        await _ask_line_price(
            message,
            state,
            session,
            employee,
            submission,
            spec,
            data.get("line_name", ""),
            data.get("line_catalog_id"),
        )
        return
    await _store_line(message, state, session, employee, submission, spec)


@router.message(Lines.waiting_price, F.text)
async def line_price(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
    lang: str,
) -> None:
    if employee is None:
        return
    text = (message.text or "").strip()
    if text in CANCEL_WORDS:
        await cancel_flow(message, state, employee, lang)
        return
    try:
        price = Decimal(text.replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        await message.answer(t("invalid_money", employee.lang))
        return
    if price < 0:
        await message.answer(t("invalid_money", employee.lang))
        return

    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", ""))
    if spec is None:
        return
    await state.update_data(line_price=str(price))
    await _store_line(message, state, session, employee, submission, spec)


async def _store_line(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee,
    submission: Submission,
    spec: FieldSpec,
) -> None:
    data = await state.get_data()
    lang = employee.lang
    qty = Decimal(data.get("line_qty", "1"))
    price = Decimal(data.get("line_price", "0"))
    name = data.get("line_name", "").strip()
    if not name:
        return

    line = await submission_service.add_line(
        session,
        submission,
        employee,
        kind=spec.line_kind,
        name=name,
        qty=qty,
        unit_price=price,
        catalog_id=data.get("line_catalog_id"),
    )
    await state.set_state(None)
    await state.update_data(
        line_name=None, line_catalog_id=None, line_qty=None, line_price=None
    )

    if spec.has_price_field:
        await message.answer(
            t("line_added", lang, name=line.name, amount=fmt_money(line.proposed_amount, lang))
        )
    else:
        await message.answer(
            t("line_added_part", lang, name=line.name, qty=line.qty.normalize())
        )
    await _show_lines(message, session, employee, submission, spec)


@router.callback_query(Act.filter(F.name == "line_del"))
async def line_delete(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    await submission_service.remove_line(session, submission, employee, callback_data.id)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", "")) or _current_lines_spec(schema, submission)
    await callback.answer(t("line_removed", employee.lang))
    if spec is not None:
        await _show_lines(callback.message, session, employee, submission, spec)


@router.callback_query(Act.filter(F.name == "lines_done"))
async def lines_done(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    data = await state.get_data()
    submission = await load_draft(session, data["submission_id"], employee)
    schema = await engine.schema_for_submission(session, submission)
    spec = schema.get(data.get("field", "")) or _current_lines_spec(schema, submission)
    if spec is None:
        await callback.answer()
        return

    lines = [ln for ln in submission.lines if ln.kind == spec.line_kind]
    if spec.required and not lines:
        await callback.answer(t("lines_need_one", employee.lang), show_alert=True)
        return

    engine.mark_done(submission, spec.code)
    await session.flush()
    await callback.answer()
    await ask_next(callback.message, session, employee, submission, state)


# --- Mashina ketdi va yuborish ------------------------------------------------


@router.callback_query(Act.filter(F.name == "mark_left"))
async def mark_left(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await load_draft(session, callback_data.id, employee)
    await submission_service.mark_left(session, submission, employee)
    lang = employee.lang
    await callback.answer()
    await callback.message.answer(
        t(
            "left_registered",
            lang,
            time=fmt_dt(submission.left_at, lang),
            downtime=fmt_duration(submission.downtime_seconds, lang),
        ),
        reply_markup=kb.form_actions(lang, submission.id, has_left=True),
    )


@router.callback_query(Act.filter(F.name == "preview"))
async def preview(
    callback: CallbackQuery,
    callback_data: Act,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await submission_service.get_for_actor(session, callback_data.id, employee)
    await callback.answer()
    await callback.message.answer(render_card(submission, employee.lang))


@router.callback_query(Act.filter(F.name == "submit"))
async def submit_report(
    callback: CallbackQuery,
    callback_data: Act,
    state: FSMContext,
    session: AsyncSession,
    employee: Employee | None,
) -> None:
    if employee is None:
        await callback.answer()
        return
    submission = await load_draft(session, callback_data.id, employee)
    lang = employee.lang

    try:
        await submission_service.submit(session, submission, employee)
    except ValidationFailed as exc:
        issues = exc.details.get("issues") or []
        lines = []
        schema = await engine.schema_for_submission(session, submission)
        for issue in issues:
            spec = schema.get(issue.field_code)
            label = spec.label(lang) if spec else issue.field_code
            lines.append(f"• {label}: {t(issue.key, lang, **issue.params)}")
        await callback.answer()
        await callback.message.answer(t("submit_blocked", lang, errors="\n".join(lines)))
        await ask_next(callback.message, session, employee, submission, state)
        return
    except DomainError as exc:
        await callback.answer()
        await callback.message.answer(f"⚠️ {exc.message}")
        return

    await state.clear()
    await callback.answer()
    key = "submitted_auto_approved" if submission.auto_approved else "submitted_ok"
    amount = (
        submission.labor_amount
        if submission.labor_amount is not None
        else submission.proposed_labor_amount
    )
    await callback.message.answer(
        t(key, lang, number=submission.number, amount=fmt_money(amount, lang)),
        reply_markup=kb.main_menu(employee),
    )
