"""SQLAlchemy 2 asoslari va portativ tiplar.

Asosiy baza — PostgreSQL. SQLite faqat lokal ishga tushirish va testlar uchun
qo'llab-quvvatlanadi, shuning uchun PG'ga xos tiplar `with_variant` bilan
beriladi.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Annotated

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

UTC = dt.timezone.utc


def utcnow() -> dt.datetime:
    """Server vaqti — doim UTC, doim tz-aware (R6)."""
    return dt.datetime.now(UTC)


def as_utc(value: dt.datetime | None) -> dt.datetime | None:
    """SQLite tz-siz datetime qaytaradi — solishtirishdan oldin UTC biriktiriladi."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


# --- Portativ tiplar ---------------------------------------------------------

JSONType = JSONB().with_variant(sa.JSON(), "sqlite")
# SQLite'da avtoinkrement faqat INTEGER PK uchun ishlaydi
PKType = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
BigIntArray = ARRAY(sa.BigInteger()).with_variant(sa.JSON(), "sqlite")

Money = Annotated[Decimal, mapped_column(sa.Numeric(14, 2))]
Qty = Annotated[Decimal, mapped_column(sa.Numeric(10, 2))]
Coord = Annotated[Decimal, mapped_column(sa.Numeric(9, 6))]

ZERO = Decimal("0.00")


def money(value: object) -> Decimal:
    """Har qanday kiruvchi qiymatni NUMERIC(14,2) ga keltiradi."""
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    return Decimal(str(value)).quantize(Decimal("0.01"))


def py_enum(enum_cls: type, name: str) -> sa.Enum:
    """Python enum → DB enum (qiymatlar bo'yicha, nomlar bo'yicha emas)."""
    return sa.Enum(
        enum_cls,
        name=name,
        values_callable=lambda e: [item.value for item in e],
        native_enum=True,
    )


class Base(DeclarativeBase):
    type_annotation_map = {
        dt.datetime: sa.DateTime(timezone=True),
        dict: JSONType,
        list: JSONType,
    }


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class SoftDeleteMixin:
    """R9 — o'chirish yo'q, faqat `deleted_at`."""

    deleted_at: Mapped[dt.datetime | None] = mapped_column(default=None)
