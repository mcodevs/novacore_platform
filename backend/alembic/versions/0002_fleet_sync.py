"""Fleet sinxroni uchun `vehicles` ustunlari (Faza 3).

⚠️ 0001 sxemani `Base.metadata.create_all` dan quradi — ya'ni **toza bazada**
bu ustunlar allaqachon yaratilgan bo'ladi. Shuning uchun bu migratsiya
idempotent: mavjud ustun qayta qo'shilmaydi.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None

TABLE = "vehicles"

NEW_COLUMNS = [
    sa.Column("fleet_status", sa.Text(), nullable=True),
    sa.Column("fleet_synced_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column(
        "fleet_missing", sa.Boolean(), nullable=False, server_default=sa.false()
    ),
]


def _existing() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(TABLE)}


def upgrade() -> None:
    existing = _existing()
    for column in NEW_COLUMNS:
        if column.name not in existing:
            op.add_column(TABLE, column.copy())


def downgrade() -> None:
    existing = _existing()
    for column in reversed(NEW_COLUMNS):
        if column.name in existing:
            op.drop_column(TABLE, column.name)
