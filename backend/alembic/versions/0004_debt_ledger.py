"""Qarz daftari — davr/to'lov varaqasi o'rniga hisobot bo'yicha to'lov (ADR-0015).

O'chadi: `payouts`, `periods`, `submissions.period_id`.
Qo'shiladi: `submissions.payable_amount` / `paid_amount`,
`submission_lines.self_funded` (ADR-0016), `payments`, `payment_allocations`.

⚠️ 0001 sxemani `Base.metadata.create_all` dan quradi — toza bazada yangi
jadvallar allaqachon bor, eskilari esa yo'q. Shuning uchun migratsiya
**idempotent**.

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None

SUBMISSIONS = "submissions"
LINES = "submission_lines"
PAYMENTS = "payments"
ALLOCATIONS = "payment_allocations"
MONEY = sa.Numeric(14, 2)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    if table not in _tables():
        return set()
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    if table not in _tables():
        return set()
    return {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table)}


def _is_pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    tables = _tables()

    # --- 1. Yangi ustunlar: qarz asosi va to'langani -------------------------
    sub_cols = _columns(SUBMISSIONS)
    if "payable_amount" not in sub_cols:
        op.add_column(
            SUBMISSIONS,
            sa.Column("payable_amount", MONEY, nullable=False, server_default="0"),
        )
    if "paid_amount" not in sub_cols:
        op.add_column(
            SUBMISSIONS,
            sa.Column("paid_amount", MONEY, nullable=False, server_default="0"),
        )

    if "self_funded" not in _columns(LINES):
        op.add_column(
            LINES,
            sa.Column(
                "self_funded", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )

    # --- 2. Backfill: tasdiqlangan hisobotning qarzi = tasdiqlangan ish haqi --
    # Eski ma'lumotda `self_funded` qism yo'q (belgi endi paydo bo'ldi), shuning
    # uchun qarz asosi faqat `labor_amount`. To'langan deb belgilanganlar (`paid`)
    # to'liq yopilgan hisoblanadi — aks holda ular qarz bo'lib qayta paydo bo'lardi.
    op.execute(
        sa.text(
            f"UPDATE {SUBMISSIONS} SET payable_amount = COALESCE(labor_amount, 0) "
            "WHERE status IN ('approved', 'paid')"
        )
    )
    op.execute(
        sa.text(
            f"UPDATE {SUBMISSIONS} SET paid_amount = payable_amount WHERE status = 'paid'"
        )
    )

    # --- 3. Yangi jadvallar --------------------------------------------------
    if PAYMENTS not in tables:
        op.create_table(
            PAYMENTS,
            sa.Column(
                "id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column("employee_id", sa.BigInteger(), sa.ForeignKey("employees.id"),
                      nullable=False),
            sa.Column("amount", MONEY, nullable=False),
            sa.Column("actor_id", sa.BigInteger(), sa.ForeignKey("employees.id"),
                      nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("voided_by", sa.BigInteger(), sa.ForeignKey("employees.id"),
                      nullable=True),
            sa.Column("void_reason", sa.Text(), nullable=True),
            sa.CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
            sa.CheckConstraint(
                "voided_at IS NULL OR void_reason IS NOT NULL",
                name="ck_payment_void_reason",
            ),
        )
    if "ix_payments_employee" not in _indexes(PAYMENTS):
        op.create_index("ix_payments_employee", PAYMENTS, ["employee_id", "created_at"])

    if ALLOCATIONS not in tables:
        op.create_table(
            ALLOCATIONS,
            sa.Column(
                "id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                primary_key=True,
                autoincrement=True,
            ),
            sa.Column(
                "payment_id",
                sa.BigInteger(),
                sa.ForeignKey("payments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("submission_id", sa.BigInteger(),
                      sa.ForeignKey("submissions.id"), nullable=False),
            sa.Column("amount", MONEY, nullable=False),
            sa.CheckConstraint("amount > 0", name="ck_allocation_amount_positive"),
        )
    if "ix_allocations_submission" not in _indexes(ALLOCATIONS):
        op.create_index("ix_allocations_submission", ALLOCATIONS, ["submission_id"])

    # --- 4. Eski davr/to'lov varaqasi modelini olib tashlash ------------------
    if "payouts" in tables:
        op.drop_table("payouts")

    if "ix_submissions_author_period" in _indexes(SUBMISSIONS):
        op.drop_index("ix_submissions_author_period", table_name=SUBMISSIONS)
    if "period_id" in _columns(SUBMISSIONS):
        op.drop_column(SUBMISSIONS, "period_id")

    if "periods" in _tables():
        op.drop_table("periods")

    if _is_pg():
        for enum_name in ("period_status", "payout_status"):
            op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))

    # --- 5. Cheklovlar va indeks ---------------------------------------------
    # P2 — ortiqcha to'lov yo'q. SQLite'da mavjud jadvalga CHECK qo'shib
    # bo'lmaydi (batch rekonstruksiya kerak), toza bazada u modeldan keladi.
    if _is_pg():
        op.execute(
            sa.text(
                f"ALTER TABLE {SUBMISSIONS} DROP CONSTRAINT IF EXISTS "
                "ck_submission_paid_le_payable"
            )
        )
        op.create_check_constraint(
            "ck_submission_paid_le_payable",
            SUBMISSIONS,
            "paid_amount >= 0 AND paid_amount <= payable_amount",
        )
        # P6 — kompaniya to'lagan qismda narx bo'lmaydi
        op.execute(
            sa.text(
                f"ALTER TABLE {LINES} DROP CONSTRAINT IF EXISTS "
                "ck_line_company_part_no_price"
            )
        )
        op.create_check_constraint(
            "ck_line_company_part_no_price",
            LINES,
            "kind = 'labor' OR self_funded OR proposed_amount = 0",
        )

    if "ix_submissions_author_status" not in _indexes(SUBMISSIONS):
        op.create_index(
            "ix_submissions_author_status",
            SUBMISSIONS,
            ["author_id", "status", "submitted_at"],
        )


def downgrade() -> None:
    """Qaytarish — qarz daftari ma'lumoti yo'qoladi (davr modeli tiklanmaydi)."""
    if ALLOCATIONS in _tables():
        op.drop_table(ALLOCATIONS)
    if PAYMENTS in _tables():
        op.drop_table(PAYMENTS)

    if _is_pg():
        op.execute(
            sa.text(
                f"ALTER TABLE {SUBMISSIONS} DROP CONSTRAINT IF EXISTS "
                "ck_submission_paid_le_payable"
            )
        )
        op.execute(
            sa.text(
                f"ALTER TABLE {LINES} DROP CONSTRAINT IF EXISTS "
                "ck_line_company_part_no_price"
            )
        )
    if "ix_submissions_author_status" in _indexes(SUBMISSIONS):
        op.drop_index("ix_submissions_author_status", table_name=SUBMISSIONS)

    for column in ("payable_amount", "paid_amount"):
        if column in _columns(SUBMISSIONS):
            op.drop_column(SUBMISSIONS, column)
    if "self_funded" in _columns(LINES):
        op.drop_column(LINES, "self_funded")
