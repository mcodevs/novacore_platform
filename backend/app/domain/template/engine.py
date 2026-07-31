"""Shablon dvigateli — yadro abstraksiyasi.

Shablon JSON → forma → validatsiya → promoted ustunlar.
Yangi rol/shablon = yangi JSON, yangi kod EMAS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import ZERO, money
from app.db.models import (
    LineKind,
    Media,
    Submission,
    SubmissionLine,
    Template,
    TemplateVersion,
)

# Bot va Mini App qo'llab-quvvatlaydigan maydon turlari
SUPPORTED_TYPES = {
    "text",
    "textarea",
    "number",
    "money",
    "bool",
    "select",
    "photo",
    "vehicle_picker",
    "submission_picker",  # bog'liq hisobot: qism xaridi ↔ ta'mir (Faza 2)
    "lines",
    "geo",
}


@dataclass(frozen=True)
class ValidationIssue:
    """Maydon xatosi — i18n kaliti bilan (matn UI qatlamida tarjima qilinadi)."""

    field_code: str
    key: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldSpec:
    code: str
    type: str
    label_uz: str
    label_ru: str
    required: bool = False
    section: str | None = None
    sort: int = 100
    hint_uz: str | None = None
    hint_ru: str | None = None
    options: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    visible_if: dict | None = None

    def label(self, lang: str = "uz") -> str:
        return self.label_ru if lang == "ru" else self.label_uz

    def hint(self, lang: str = "uz") -> str:
        return (self.hint_ru if lang == "ru" else self.hint_uz) or ""

    @property
    def photo_min(self) -> int:
        return int(self.options.get("min", 1 if self.required else 0))

    @property
    def photo_max(self) -> int:
        return int(self.options.get("max", 10))

    @property
    def line_kind(self) -> LineKind:
        return LineKind(self.options.get("kind", "labor"))

    @property
    def has_price_field(self) -> bool:
        return bool(self.options.get("price_field", self.line_kind == LineKind.labor))


@dataclass
class TemplateSchema:
    code: str
    version: int
    name_uz: str
    name_ru: str
    icon: str
    subject_type: str
    has_money: bool
    negotiable: bool
    field_mapping: dict
    sections: list
    fields: list[FieldSpec]

    def name(self, lang: str = "uz") -> str:
        return self.name_ru if lang == "ru" else self.name_uz

    def get(self, code: str) -> FieldSpec | None:
        for spec in self.fields:
            if spec.code == code:
                return spec
        return None

    def lines_fields(self) -> list[FieldSpec]:
        return [f for f in self.fields if f.type == "lines"]

    def field_for_line_kind(self, kind: LineKind) -> FieldSpec | None:
        for spec in self.lines_fields():
            if spec.line_kind == kind:
                return spec
        return None


def schema_from_json(raw: dict) -> TemplateSchema:
    fields: list[FieldSpec] = []
    for idx, item in enumerate(raw.get("fields", []), start=1):
        label = item.get("label", {})
        hint = item.get("hint") or {}
        fields.append(
            FieldSpec(
                code=item["code"],
                type=item["type"],
                label_uz=label.get("uz", item["code"]),
                label_ru=label.get("ru", label.get("uz", item["code"])),
                required=item.get("required", False),
                section=item.get("section"),
                sort=item.get("sort", idx * 10),
                hint_uz=hint.get("uz"),
                hint_ru=hint.get("ru"),
                options=item.get("options", {}) or {},
                validation=item.get("validation", {}) or {},
                visible_if=item.get("visible_if"),
            )
        )
    fields.sort(key=lambda f: f.sort)
    name = raw.get("name", {})
    return TemplateSchema(
        code=raw["code"],
        version=raw.get("version", 1),
        name_uz=name.get("uz", raw["code"]),
        name_ru=name.get("ru", name.get("uz", raw["code"])),
        icon=raw.get("icon", "📝"),
        subject_type=raw.get("subject_type", "vehicle"),
        has_money=raw.get("has_money", True),
        negotiable=raw.get("negotiable", True),
        field_mapping=raw.get("field_mapping", {}),
        sections=raw.get("sections", []),
        fields=fields,
    )


def schema_from_template(template: Template) -> TemplateSchema:
    """Joriy (nashr etilmagan) holatdan sxema — snapshot topilmaganda zaxira."""
    fields = [
        FieldSpec(
            code=f.code,
            type=f.type,
            label_uz=f.label_uz,
            label_ru=f.label_ru,
            required=f.is_required,
            section=f.section,
            sort=f.sort,
            hint_uz=f.hint_uz,
            hint_ru=f.hint_ru,
            options=f.options or {},
            validation=f.validation or {},
            visible_if=f.visible_if,
        )
        for f in sorted(template.fields, key=lambda x: x.sort)
    ]
    return TemplateSchema(
        code=template.code,
        version=template.version,
        name_uz=template.name_uz,
        name_ru=template.name_ru,
        icon=template.icon,
        subject_type=template.subject_type.value,
        has_money=template.has_money,
        negotiable=template.negotiable,
        field_mapping=template.field_mapping or {},
        sections=template.sections or [],
        fields=fields,
    )


async def load_schema(
    session: AsyncSession, template_id: int, version: int | None = None
) -> TemplateSchema:
    """Hisobot **o'z versiyasidagi** sxema bilan ko'rsatiladi (versiyalash)."""
    if version is not None:
        snapshot = (
            await session.execute(
                sa.select(TemplateVersion).where(
                    TemplateVersion.template_id == template_id,
                    TemplateVersion.version == version,
                )
            )
        ).scalar_one_or_none()
        if snapshot is not None:
            return schema_from_json(snapshot.schema_json)

    template = await session.get(Template, template_id)
    if template is None:
        raise LookupError(f"template {template_id} not found")
    return schema_from_template(template)


async def schema_for_submission(session: AsyncSession, submission: Submission) -> TemplateSchema:
    return await load_schema(session, submission.template_id, submission.template_version)


# --- Ko'rinish sharti -------------------------------------------------------


def is_visible(spec: FieldSpec, data: dict) -> bool:
    """`visible_if`: {"field": "code", "equals": value} yoki {"field": .., "in": [...]}"""
    cond = spec.visible_if
    if not cond:
        return True
    other = data.get(cond.get("field"))
    if "equals" in cond:
        return other == cond["equals"]
    if "in" in cond:
        return other in cond["in"]
    return bool(other)


# --- Qiymatlar --------------------------------------------------------------


def is_answered(spec: FieldSpec, submission: Submission) -> bool:
    """Maydon to'ldirilganmi (majburiyligidan qat'i nazar)."""
    data = submission.data or {}
    value = data.get(spec.code)
    done = bool((data.get("_done", {}) or {}).get(spec.code))

    if spec.type == "photo":
        ids = value or []
        if not isinstance(ids, list):
            return False
        if done and len(ids) >= spec.photo_min:
            return True
        return len(ids) >= max(spec.photo_min, 1) and len(ids) >= spec.photo_max

    if spec.type == "lines":
        return done

    if done:
        # ixtiyoriy maydon ataylab o'tkazib yuborilgan
        return True

    if spec.type == "bool":
        return isinstance(value, bool)

    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def mark_done(submission: Submission, field_code: str) -> None:
    """`photo` / `lines` maydonlari uchun «tugadim» belgisi."""
    data = dict(submission.data or {})
    done = dict(data.get("_done", {}) or {})
    done[field_code] = True
    data["_done"] = done
    submission.data = data


def set_value(submission: Submission, field_code: str, value: Any) -> None:
    data = dict(submission.data or {})
    data[field_code] = value
    submission.data = data


def append_media_id(submission: Submission, field_code: str, media_id: int) -> None:
    data = dict(submission.data or {})
    ids = list(data.get(field_code) or [])
    ids.append(media_id)
    data[field_code] = ids
    submission.data = data


def next_field(schema: TemplateSchema, submission: Submission) -> FieldSpec | None:
    """Ketma-ket forma uchun: keyingi to'ldirilmagan maydon."""
    data = submission.data or {}
    for spec in schema.fields:
        if not is_visible(spec, data):
            continue
        if spec.type not in SUPPORTED_TYPES:
            continue
        if is_answered(spec, submission):
            continue
        return spec
    return None


# --- Validatsiya ------------------------------------------------------------


def _parse_number(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def validate(
    schema: TemplateSchema,
    submission: Submission,
    *,
    media: list[Media] | None = None,
    lines: list[SubmissionLine] | None = None,
) -> list[ValidationIssue]:
    """Server — oxirgi hakam. Klient hisobiga ishonilmaydi."""
    issues: list[ValidationIssue] = []
    data = submission.data or {}
    media = media if media is not None else list(submission.media or [])
    lines = lines if lines is not None else list(submission.lines or [])
    live_media = {m.id for m in media if m.deleted_at is None}

    for spec in schema.fields:
        if not is_visible(spec, data):
            continue
        value = data.get(spec.code)

        if spec.type == "photo":
            ids = [i for i in (value or []) if i in live_media]
            if spec.required and len(ids) < max(spec.photo_min, 1):
                issues.append(
                    ValidationIssue(
                        spec.code, "photo_need_more", {"min": max(spec.photo_min, 1), "n": len(ids)}
                    )
                )
            elif len(ids) > spec.photo_max:
                issues.append(
                    ValidationIssue(spec.code, "photo_max_reached", {"max": spec.photo_max})
                )
            continue

        if spec.type == "lines":
            kind_lines = [ln for ln in lines if ln.kind == spec.line_kind]
            if spec.required and not kind_lines:
                issues.append(ValidationIssue(spec.code, "lines_need_one", {}))
            continue

        if spec.required and not is_answered(spec, submission):
            issues.append(ValidationIssue(spec.code, "field_required", {}))
            continue

        if value is None or (isinstance(value, str) and not value.strip()):
            continue

        if spec.type in ("number", "money"):
            number = _parse_number(value)
            if number is None:
                issues.append(ValidationIssue(spec.code, "invalid_number", {}))
                continue
            minimum = spec.validation.get("min")
            maximum = spec.validation.get("max")
            if minimum is not None and number < Decimal(str(minimum)):
                issues.append(ValidationIssue(spec.code, "value_too_small", {"min": minimum}))
            if maximum is not None and number > Decimal(str(maximum)):
                issues.append(ValidationIssue(spec.code, "value_too_big", {"max": maximum}))

        elif spec.type in ("text", "textarea"):
            text = str(value).strip()
            min_len = spec.validation.get("min_length")
            max_len = spec.validation.get("max_length")
            if min_len and len(text) < int(min_len):
                issues.append(
                    ValidationIssue(spec.code, "text_too_short", {"min": min_len, "n": len(text)})
                )
            if max_len and len(text) > int(max_len):
                issues.append(ValidationIssue(spec.code, "value_too_big", {"max": max_len}))

        elif spec.type == "vehicle_picker":
            if not isinstance(value, dict) or not value.get("vehicle_id"):
                issues.append(ValidationIssue(spec.code, "field_required", {}))

        elif spec.type == "submission_picker":
            if not isinstance(value, dict) or not value.get("submission_id"):
                issues.append(ValidationIssue(spec.code, "field_required", {}))

    return issues


# --- Promoted ustunlar (field_mapping) --------------------------------------


def sum_lines(lines: list[SubmissionLine], kind: LineKind, *, approved: bool = False) -> Decimal:
    total = ZERO
    for line in lines:
        if line.kind != kind:
            continue
        if approved:
            total += line.approved_amount if line.approved_amount is not None else ZERO
        else:
            total += line.proposed_amount or ZERO
    return money(total)


def all_lines_approved(lines: list[SubmissionLine], kind: LineKind) -> bool:
    kind_lines = [ln for ln in lines if ln.kind == kind]
    return bool(kind_lines) and all(ln.approved_amount is not None for ln in kind_lines)


def recalculate_amounts(submission: Submission, lines: list[SubmissionLine] | None = None) -> None:
    """R7 — summalar doim `submission_lines`dan qayta hisoblanadi."""
    lines = lines if lines is not None else list(submission.lines or [])

    submission.proposed_labor_amount = sum_lines(lines, LineKind.labor)
    if all_lines_approved(lines, LineKind.labor):
        submission.labor_amount = sum_lines(lines, LineKind.labor, approved=True)

    # Qism narxini usta kiritmaydi: mavjud bo'lsa `approved`, aks holda `proposed`
    parts_approved = sum_lines(lines, LineKind.part, approved=True)
    parts_proposed = sum_lines(lines, LineKind.part)
    submission.parts_amount = parts_approved if parts_approved > ZERO else parts_proposed

    labor = (
        submission.labor_amount
        if submission.labor_amount is not None
        else submission.proposed_labor_amount
    )
    submission.total_amount = money(labor + submission.parts_amount)


def apply_field_mapping(
    schema: TemplateSchema, submission: Submission, lines: list[SubmissionLine] | None = None
) -> None:
    """JSONB → promoted ustunlar. Analitika faqat shu ustunlar bilan ishlaydi."""
    data = submission.data or {}
    mapping = schema.field_mapping or {}

    vehicle_field = mapping.get("vehicle")
    if vehicle_field:
        value = data.get(vehicle_field)
        if isinstance(value, dict) and value.get("vehicle_id"):
            submission.subject_vehicle_id = int(value["vehicle_id"])

    employee_field = mapping.get("employee")
    if employee_field:
        value = data.get(employee_field)
        if isinstance(value, dict) and value.get("employee_id"):
            submission.subject_employee_id = int(value["employee_id"])

    related_field = mapping.get("related_submission")
    if related_field:
        value = data.get(related_field)
        if isinstance(value, dict) and value.get("submission_id"):
            submission.related_submission_id = int(value["submission_id"])

    odometer_field = mapping.get("odometer")
    if odometer_field:
        raw = data.get(odometer_field)
        number = _parse_number(raw)
        if number is not None:
            submission.odometer_km = int(number)

    recalculate_amounts(submission, lines)
