"""Shablon konstruktori (Faza 2) — admin kod yozmasdan shablon yaratadi.

docs/02-architecture/03-report-templates.md §5, §7 · docs/01-product/04-roles-and-templates.md §7

Versiyalash qoidasi (§5) — **nashr etilgan versiya o'zgarmas**:

    v1 nashr etilgan  →  snapshot `template_versions(version=1)`
    admin tahrirlaydi →  `templates.version` 2 ga ko'tariladi (qoralama, snapshot yo'q)
    v2 nashr etiladi  →  snapshot `template_versions(version=2)`

Eski hisobot `submissions.template_version = 1` bilan qoladi va **o'z
versiyasidagi** yorliqlar bilan ko'rsatiladi. Yangi hisobotlar esa doim
**oxirgi nashr etilgan** versiyada ochiladi — qoralamada emas.

Alohida `status` ustuni kerak emas: qoralama = joriy `version` uchun snapshot
yo'qligi.
"""

from __future__ import annotations

import re
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleViolated, NotFound, ValidationFailed
from app.db.models import (
    Employee,
    LineKind,
    RoleTemplate,
    SubjectType,
    Template,
    TemplateField,
    TemplateVersion,
)
from app.domain import audit
from app.domain.template import engine

CODE_RE = re.compile(r"^[a-z][a-z0-9_]{2,39}$")

#: `field_mapping` qabul qiladigan yadro tushunchalari (§4)
MAPPING_KEYS = {
    "vehicle",
    "employee",
    "related_submission",
    "proposed_labor_amount",
    "labor_amount",
    "parts_amount",
    "total_amount",
    "started_at",
    "finished_at",
}
#: `@lines.labor`, `@auto.submit` — maydonga emas, yadroga ishora qiladi
SPECIAL_MAPPING_PREFIX = "@"


# --- Nashr holati ------------------------------------------------------------


async def latest_published_version(session: AsyncSession, template_id: int) -> int | None:
    """Oxirgi nashr etilgan versiya. `None` — hali nashr etilmagan qoralama."""
    return (
        await session.execute(
            sa.select(sa.func.max(TemplateVersion.version)).where(
                TemplateVersion.template_id == template_id
            )
        )
    ).scalar_one_or_none()


async def is_published(session: AsyncSession, template: Template) -> bool:
    """Joriy `template.version` nashr etilganmi (ya'ni snapshot bormi)."""
    row = (
        await session.execute(
            sa.select(TemplateVersion.id).where(
                TemplateVersion.template_id == template.id,
                TemplateVersion.version == template.version,
            )
        )
    ).first()
    return row is not None


def _is_published_clause():  # noqa: ANN202
    """Shablonning kamida bitta nashr etilgan versiyasi bormi."""
    return (
        sa.select(TemplateVersion.id)
        .where(TemplateVersion.template_id == Template.id)
        .exists()
    )


async def visible_for(session: AsyncSession, employee: Employee) -> list[Template]:
    """Xodim ko'radigan shablonlar: roliga biriktirilgan **va nashr etilgan**.

    Qoralama shablon hech kimga ko'rinmaydi — admin uni nashr etmaguncha.
    """
    stmt = (
        sa.select(Template)
        .join(RoleTemplate, RoleTemplate.template_id == Template.id)
        .where(
            RoleTemplate.role_id == employee.role_id,
            Template.is_active.is_(True),
            _is_published_clause(),
        )
        .order_by(RoleTemplate.sort)
    )
    return list((await session.execute(stmt)).scalars().all())


async def usable_version(session: AsyncSession, template: Template) -> int:
    """Yangi hisobot qaysi versiyada ochiladi — **faqat nashr etilgani**."""
    version = await latest_published_version(session, template.id)
    if version is None:
        raise BusinessRuleViolated(
            f"«{template.code}» shabloni hali nashr etilmagan", code=template.code
        )
    return version


# --- Sxema ↔ model -----------------------------------------------------------


def to_definition(template: Template) -> dict[str, Any]:
    """Model → seed JSON'i bilan **bir xil** ko'rinish (yagona format)."""
    return {
        "code": template.code,
        "name": {"uz": template.name_uz, "ru": template.name_ru},
        "icon": template.icon,
        "subject_type": template.subject_type.value,
        "has_money": template.has_money,
        "negotiable": template.negotiable,
        "version": template.version,
        "field_mapping": template.field_mapping or {},
        "sections": template.sections or [],
        "fields": [
            {
                "code": f.code,
                "section": f.section,
                "label": {"uz": f.label_uz, "ru": f.label_ru},
                "hint": ({"uz": f.hint_uz, "ru": f.hint_ru} if f.hint_uz or f.hint_ru else None),
                "type": f.type,
                "required": f.is_required,
                "sort": f.sort,
                "options": f.options or {},
                "validation": f.validation or {},
                "visible_if": f.visible_if,
            }
            for f in sorted(template.fields, key=lambda x: x.sort)
        ],
    }


# --- Validatsiya -------------------------------------------------------------


def _label_uz(raw: dict) -> str:
    return str((raw.get("label") or {}).get("uz") or "").strip()


def validate_definition(raw: dict[str, Any]) -> None:
    """Konstruktor yuborgan sxemani tekshiradi. Server — oxirgi hakam (§6)."""
    errors: dict[str, str] = {}

    code = str(raw.get("code") or "").strip()
    if not CODE_RE.match(code):
        errors["code"] = "invalid_code"

    if not str((raw.get("name") or {}).get("uz") or "").strip():
        errors["name"] = "field_required"

    subject = raw.get("subject_type", SubjectType.vehicle.value)
    if subject not in {s.value for s in SubjectType}:
        errors["subject_type"] = "invalid_value"

    fields = raw.get("fields") or []
    if not fields:
        errors["fields"] = "lines_need_one"

    seen: set[str] = set()
    for idx, field in enumerate(fields):
        prefix = f"fields.{idx}"
        field_code = str(field.get("code") or "").strip()
        if not CODE_RE.match(field_code):
            errors[f"{prefix}.code"] = "invalid_code"
        elif field_code in seen:
            errors[f"{prefix}.code"] = "duplicate_code"
        else:
            seen.add(field_code)

        field_type = field.get("type")
        if field_type not in engine.SUPPORTED_TYPES:
            # Hujjatdagi ro'yxat kengroq, lekin bot va Mini App faqat shularni
            # chiza oladi — qo'llab-quvvatlanmagan turdagi formani hech kim
            # to'ldira olmaydi.
            errors[f"{prefix}.type"] = "unsupported_type"

        if not _label_uz(field):
            errors[f"{prefix}.label"] = "field_required"

        options = field.get("options") or {}
        if field_type == "lines":
            if options.get("kind", "labor") not in {k.value for k in LineKind}:
                errors[f"{prefix}.options.kind"] = "invalid_value"
        if field_type == "photo":
            minimum = int(options.get("min", 0) or 0)
            maximum = int(options.get("max", 10) or 0)
            if minimum < 0 or maximum < 1 or minimum > maximum:
                errors[f"{prefix}.options"] = "invalid_range"

        cond = field.get("visible_if")
        if cond and not str(cond.get("field") or "").strip():
            errors[f"{prefix}.visible_if"] = "field_required"

    # `visible_if` va `field_mapping` mavjud maydonlarga ishora qilishi shart
    for idx, field in enumerate(fields):
        cond = field.get("visible_if")
        if cond and cond.get("field") and cond["field"] not in seen:
            errors[f"fields.{idx}.visible_if"] = "unknown_field"

    for key, value in (raw.get("field_mapping") or {}).items():
        if key not in MAPPING_KEYS:
            errors[f"field_mapping.{key}"] = "unknown_mapping"
        elif isinstance(value, str) and not value.startswith(SPECIAL_MAPPING_PREFIX):
            if value not in seen:
                errors[f"field_mapping.{key}"] = "unknown_field"

    section_codes = {
        str(s.get("code")) for s in (raw.get("sections") or []) if isinstance(s, dict)
    }
    if section_codes:
        for idx, field in enumerate(fields):
            section = field.get("section")
            if section and section not in section_codes:
                errors[f"fields.{idx}.section"] = "unknown_section"

    if errors:
        raise ValidationFailed("Shablon sxemasi noto'g'ri", fields=errors)


# --- CRUD --------------------------------------------------------------------


async def _apply(session: AsyncSession, template: Template, raw: dict[str, Any]) -> None:
    """Sxemani modelga yozadi — maydonlar to'liq almashtiriladi."""
    name = raw.get("name") or {}
    template.name_uz = name["uz"].strip()
    template.name_ru = (name.get("ru") or name["uz"]).strip()
    template.icon = raw.get("icon") or "📝"
    template.subject_type = SubjectType(raw.get("subject_type", SubjectType.vehicle.value))
    template.has_money = bool(raw.get("has_money", True))
    template.negotiable = bool(raw.get("negotiable", True))
    template.field_mapping = raw.get("field_mapping") or {}
    template.sections = raw.get("sections") or []
    if raw.get("is_active") is not None:  # `None` — «tegilmasin», `False` emas
        template.is_active = bool(raw["is_active"])
    await session.flush()

    await session.execute(
        sa.delete(TemplateField).where(TemplateField.template_id == template.id)
    )
    for idx, field in enumerate(raw.get("fields") or [], start=1):
        hint = field.get("hint") or {}
        session.add(
            TemplateField(
                template_id=template.id,
                code=field["code"].strip(),
                label_uz=_label_uz(field),
                label_ru=((field.get("label") or {}).get("ru") or _label_uz(field)).strip(),
                hint_uz=hint.get("uz"),
                hint_ru=hint.get("ru"),
                type=field["type"],
                section=field.get("section"),
                sort=int(field.get("sort", idx * 10)),
                is_required=bool(field.get("required", False)),
                options=field.get("options") or {},
                validation=field.get("validation") or {},
                visible_if=field.get("visible_if"),
            )
        )
    await session.flush()
    await session.refresh(template)


async def create(session: AsyncSession, actor: Employee, raw: dict[str, Any]) -> Template:
    """Yangi shablon — **qoralama** holatida (nashr etilmaguncha ko'rinmaydi)."""
    validate_definition(raw)
    code = raw["code"].strip()
    exists = (
        await session.execute(sa.select(Template.id).where(Template.code == code))
    ).first()
    if exists:
        raise BusinessRuleViolated(f"«{code}» kodli shablon allaqachon bor")

    template = Template(code=code, version=1, is_active=raw.get("is_active") is not False)
    session.add(template)
    await _apply(session, template, raw)  # nomlarni yozadi va INSERT qiladi

    await audit.log(
        session,
        action="template.create",
        entity_type="template",
        entity_id=template.id,
        actor_id=actor.id,
        after={"code": template.code, "version": template.version},
    )
    return template


async def update(
    session: AsyncSession, actor: Employee, template: Template, raw: dict[str, Any]
) -> Template:
    """Tahrirlash. Joriy versiya nashr etilgan bo'lsa — yangi qoralama ochiladi."""
    payload = {**raw, "code": template.code}  # kod o'zgarmas: rollar unga tayanadi
    validate_definition(payload)

    before = {"version": template.version, "published": await is_published(session, template)}
    if before["published"]:
        template.version += 1  # nashr etilgan snapshot hech qachon ustidan yozilmaydi
        await session.flush()

    await _apply(session, template, payload)

    await audit.log(
        session,
        action="template.update",
        entity_type="template",
        entity_id=template.id,
        actor_id=actor.id,
        before=before,
        after={"version": template.version, "published": False},
    )
    return template


async def publish(session: AsyncSession, actor: Employee, template: Template) -> Template:
    """Qoralamani nashr etadi — snapshot yoziladi va u **o'zgarmas** bo'lib qoladi."""
    if await is_published(session, template):
        raise BusinessRuleViolated(
            f"v{template.version} allaqachon nashr etilgan — avval tahrirlang"
        )

    definition = to_definition(template)
    session.add(
        TemplateVersion(
            template_id=template.id,
            version=template.version,
            schema_json=definition,
            published_by=actor.id,
        )
    )
    await session.flush()

    await audit.log(
        session,
        action="template.publish",
        entity_type="template",
        entity_id=template.id,
        actor_id=actor.id,
        after={"version": template.version, "fields": len(definition["fields"])},
    )
    return template


async def get_or_404(session: AsyncSession, template_id: int) -> Template:
    template = await session.get(Template, template_id)
    if template is None:
        raise NotFound("Shablon topilmadi")
    return template
