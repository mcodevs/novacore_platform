"""E'lonlar (broadcast) — admin barcha xodimlarga xabar yuboradi.

⚠️ 0001 sxemani `Base.metadata.create_all` dan quradi — ya'ni **toza bazada**
`broadcasts` jadvali va `notifications.broadcast_id` allaqachon yaratilgan
bo'ladi. Shuning uchun bu migratsiya idempotent.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None

BROADCASTS = "broadcasts"
NOTIFICATIONS = "notifications"
INDEX_NAME = "ix_notifications_broadcast"
FK_NAME = "fk_notifications_broadcast_id"


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    if BROADCASTS not in _tables():
        op.create_table(
            BROADCASTS,
            sa.Column(
                "id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column(
                "author_id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                sa.ForeignKey("employees.id"),
                nullable=False,
            ),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column(
                "recipients_total", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if "broadcast_id" not in _columns(NOTIFICATIONS):
        op.add_column(
            NOTIFICATIONS,
            sa.Column(
                "broadcast_id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                nullable=True,
            ),
        )
        # SQLite `ALTER TABLE` bilan FK qo'sha olmaydi (jadvalni qayta qurish
        # kerak bo'lardi). Lokal testlarda sxema `create_all` dan quriladi va
        # FK o'sha yerda bor — shuning uchun bu yerda faqat PostgreSQL.
        if op.get_bind().dialect.name == "postgresql":
            op.create_foreign_key(
                FK_NAME, NOTIFICATIONS, BROADCASTS, ["broadcast_id"], ["id"]
            )

    if INDEX_NAME not in _indexes(NOTIFICATIONS):
        op.create_index(INDEX_NAME, NOTIFICATIONS, ["broadcast_id"])


def downgrade() -> None:
    if INDEX_NAME in _indexes(NOTIFICATIONS):
        op.drop_index(INDEX_NAME, table_name=NOTIFICATIONS)
    if "broadcast_id" in _columns(NOTIFICATIONS):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(f"ALTER TABLE {NOTIFICATIONS} DROP CONSTRAINT IF EXISTS {FK_NAME}")
            op.drop_column(NOTIFICATIONS, "broadcast_id")
        else:
            # SQLite: toza bazada FK ustunga bog'langan (0001 `create_all`), shuning
            # uchun oddiy DROP COLUMN xato beradi — jadval qayta quriladi.
            with op.batch_alter_table(NOTIFICATIONS) as batch:
                batch.drop_column("broadcast_id")
    if BROADCASTS in _tables():
        op.drop_table(BROADCASTS)
