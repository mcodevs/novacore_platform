"""Probeg hisobotdan olib tashlandi (egasining qarori, 2026-08-03).

O'chadi: `submissions.odometer_km` (promoted ustun). Shablondagi
`odometer_value` / `odometer_photo` maydonlari va `field_mapping.odometer`
bog'lanishi ham olib tashlandi (seed orqali).

⚠️ `vehicles.odometer_km` — TEGILMAYDI. U avtopark reyestri, Yandex Fleet
sinxronidan keladi va shablonga aloqasi yo'q.

⚠️ 0001 sxemani `Base.metadata.create_all` dan quradi — toza bazada ustun
allaqachon yo'q. Shuning uchun migratsiya **idempotent**.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None

SUBMISSIONS = "submissions"
COLUMN = "odometer_km"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    if table not in _tables():
        return set()
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if COLUMN in _columns(SUBMISSIONS):
        op.drop_column(SUBMISSIONS, COLUMN)


def downgrade() -> None:
    """Ustun qaytariladi, lekin qiymatlar tiklanmaydi (ma'lumot yo'qolgan)."""
    if SUBMISSIONS in _tables() and COLUMN not in _columns(SUBMISSIONS):
        op.add_column(SUBMISSIONS, sa.Column(COLUMN, sa.Integer(), nullable=True))
