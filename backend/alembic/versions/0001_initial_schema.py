"""Boshlang'ich sxema — docs/02-architecture/02-data-model.md.

Sxema `Base.metadata` dan quriladi (modellar — yagona manba), so'ng
PostgreSQL'ga xos indekslar qo'shiladi. Keyingi migratsiyalar odatdagidek
`alembic revision --autogenerate` bilan yoziladi.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401 — metadata to'lishi uchun

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None

# JSONB bo'yicha qidiruv uchun (docs/02-architecture/02-data-model.md §4)
PG_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_submissions_data_gin "
    "ON submissions USING GIN (data jsonb_path_ops)",
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    if bind.dialect.name == "postgresql":
        for statement in PG_INDEXES:
            op.execute(statement)
        # audit_log — o'zgartirilmaydi va o'chirilmaydi (R9)
        op.execute(
            """
            CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER audit_log_no_update_delete
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log")
        op.execute("DROP FUNCTION IF EXISTS audit_log_immutable()")
        op.execute("DROP INDEX IF EXISTS ix_submissions_data_gin")
    Base.metadata.drop_all(bind=bind)
    for enum_name in (
        "role_kind",
        "employee_status",
        "vehicle_status",
        "subject_type",
        "submission_status",
        "submission_resolution",
        "line_kind",
        "accept_mode",
        "media_kind",
        "media_source",
        "approval_decision",
        "flag_severity",
        "flag_resolution",
        "period_status",
        "payout_status",
        "notification_status",
    ):
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
