"""Seed yuklovchi — rollar, shablonlar, spravochniklar (idempotent).

Faza 1'da rollar va shablonlar vizual konstruktor orqali emas, JSON seed
sifatida yuklanadi (docs/02-architecture/03-report-templates.md §7).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CatalogItem,
    PartsCatalog,
    Role,
    RoleKind,
    RoleTemplate,
    Template,
    TemplateField,
    TemplateVersion,
    WorkCatalog,
)

SEEDS_DIR = Path(__file__).parent


def _load(name: str) -> object:
    return json.loads((SEEDS_DIR / name).read_text(encoding="utf-8"))


def _money(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


async def seed_templates(session: AsyncSession) -> dict[str, Template]:
    """Shablon JSON'larini yuklaydi va nashr snapshot'ini yozadi."""
    result: dict[str, Template] = {}
    for path in sorted((SEEDS_DIR / "templates").glob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        code = schema["code"]
        tpl = (
            await session.execute(sa.select(Template).where(Template.code == code))
        ).scalar_one_or_none()
        if tpl is None:
            tpl = Template(code=code)
            session.add(tpl)

        tpl.name_uz = schema["name"]["uz"]
        tpl.name_ru = schema["name"].get("ru", schema["name"]["uz"])
        tpl.subject_type = schema.get("subject_type", "vehicle")
        tpl.has_money = schema.get("has_money", True)
        tpl.negotiable = schema.get("negotiable", True)
        tpl.field_mapping = schema.get("field_mapping", {})
        tpl.sections = schema.get("sections", [])
        tpl.icon = schema.get("icon", "📝")
        tpl.version = schema.get("version", 1)
        tpl.is_active = schema.get("is_active", True)
        await session.flush()

        # maydonlar — to'liq qayta yoziladi (seed = yagona manba)
        await session.execute(
            sa.delete(TemplateField).where(TemplateField.template_id == tpl.id)
        )
        for idx, field in enumerate(schema.get("fields", []), start=1):
            session.add(
                TemplateField(
                    template_id=tpl.id,
                    code=field["code"],
                    label_uz=field["label"]["uz"],
                    label_ru=field["label"].get("ru", field["label"]["uz"]),
                    hint_uz=(field.get("hint") or {}).get("uz"),
                    hint_ru=(field.get("hint") or {}).get("ru"),
                    type=field["type"],
                    section=field.get("section"),
                    sort=field.get("sort", idx * 10),
                    is_required=field.get("required", False),
                    options=field.get("options", {}),
                    validation=field.get("validation", {}),
                    visible_if=field.get("visible_if"),
                )
            )

        # nashr snapshot'i (versiyalash — eski hisobot buzilmasin)
        exists = (
            await session.execute(
                sa.select(TemplateVersion).where(
                    TemplateVersion.template_id == tpl.id,
                    TemplateVersion.version == tpl.version,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(
                TemplateVersion(template_id=tpl.id, version=tpl.version, schema_json=schema)
            )
        else:
            exists.schema_json = schema

        result[code] = tpl
    await session.flush()
    return result


async def seed_roles(session: AsyncSession, templates: dict[str, Template]) -> None:
    for item in _load("roles.json"):
        role = (
            await session.execute(sa.select(Role).where(Role.code == item["code"]))
        ).scalar_one_or_none()
        if role is None:
            role = Role(code=item["code"])
            session.add(role)
        role.name_uz = item["name_uz"]
        role.name_ru = item["name_ru"]
        role.icon = item.get("icon", "👤")
        role.kind = RoleKind(item["kind"])
        role.is_system = item.get("is_system", False)
        role.sort = item.get("sort", 100)
        role.is_active = True
        await session.flush()

        await session.execute(sa.delete(RoleTemplate).where(RoleTemplate.role_id == role.id))
        for idx, code in enumerate(item.get("templates", []), start=1):
            tpl = templates.get(code)
            if tpl is not None:
                session.add(
                    RoleTemplate(role_id=role.id, template_id=tpl.id, sort=idx * 10)
                )
    await session.flush()


async def seed_catalogs(session: AsyncSession) -> None:
    catalogs: dict = _load("catalogs.json")
    for catalog, items in catalogs.items():
        for item in items:
            row = (
                await session.execute(
                    sa.select(CatalogItem).where(
                        CatalogItem.catalog == catalog, CatalogItem.code == item["code"]
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                row = CatalogItem(catalog=catalog, code=item["code"])
                session.add(row)
            row.name_uz = item["name_uz"]
            row.name_ru = item["name_ru"]
            row.icon = item.get("icon")
            row.sort = item.get("sort", 100)
            row.is_active = True

    for item in _load("work_catalog.json"):
        row = (
            await session.execute(
                sa.select(WorkCatalog).where(WorkCatalog.code == item["code"])
            )
        ).scalar_one_or_none()
        if row is None:
            row = WorkCatalog(code=item["code"])
            session.add(row)
        row.name_uz = item["name_uz"]
        row.name_ru = item["name_ru"]
        row.category = item.get("category")
        row.reference_price = _money(item.get("reference_price"))
        row.standard_minutes = item.get("standard_minutes")
        row.warranty_days = item.get("warranty_days")
        row.is_active = True

    for item in _load("parts_catalog.json"):
        row = (
            await session.execute(
                sa.select(PartsCatalog).where(PartsCatalog.code == item["code"])
            )
        ).scalar_one_or_none()
        if row is None:
            row = PartsCatalog(code=item["code"])
            session.add(row)
        row.name_uz = item["name_uz"]
        row.name_ru = item["name_ru"]
        row.article = item.get("article")
        row.category = item.get("category")
        row.last_price = _money(item.get("last_price"))
        row.is_active = True

    await session.flush()


async def seed_all(session: AsyncSession) -> None:
    templates = await seed_templates(session)
    await seed_roles(session, templates)
    await seed_catalogs(session)
