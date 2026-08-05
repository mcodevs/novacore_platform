"""Ma'lumotlar modeli — docs/02-architecture/02-data-model.md.

⚠️ Ataylab YO'Q: `permissions`, `role_permissions`, `branches`,
`service_requests`, `part_requests`, `vehicle_assignments`, ombor jadvallari.
Ularni qayta kiritmang — har biri ADR bilan rad etilgan.
"""

from __future__ import annotations

import datetime as dt
import enum
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.i18n import pick
from app.db.base import (
    Base,
    PKType,
    BigIntArray,
    Coord,
    JSONType,
    Money,
    Qty,
    SoftDeleteMixin,
    TimestampMixin,
    py_enum,
    utcnow,
)

# --- Enumlar ----------------------------------------------------------------


class RoleKind(str, enum.Enum):
    """Faqat uchta tur. Nomlar cheksiz — ular `roles.name_uz`da."""

    reporter = "reporter"
    admin = "admin"
    accountant = "accountant"


class EmployeeStatus(str, enum.Enum):
    active = "active"
    blocked = "blocked"
    fired = "fired"


class VehicleStatus(str, enum.Enum):
    active = "active"
    in_service = "in_service"
    waiting_parts = "waiting_parts"
    inactive = "inactive"
    sold = "sold"


class SubjectType(str, enum.Enum):
    none = "none"
    vehicle = "vehicle"
    employee = "employee"


class SubmissionStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    PRICE_NEGOTIATION = "price_negotiation"
    PRICE_DISPUTED = "price_disputed"
    REOPENED = "reopened"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


#: To'lovga kiradigan holatlar (R5)
PAYABLE_STATUSES = (SubmissionStatus.APPROVED, SubmissionStatus.PAID)
#: Muallif tahrirlashi mumkin bo'lgan holatlar
EDITABLE_STATUSES = (SubmissionStatus.DRAFT, SubmissionStatus.REOPENED)


class LineKind(str, enum.Enum):
    labor = "labor"
    part = "part"


class AcceptMode(str, enum.Enum):
    manual = "manual"
    auto_48h = "auto_48h"


class MediaKind(str, enum.Enum):
    before = "before"
    problem = "problem"
    after = "after"
    receipt = "receipt"
    odometer = "odometer"
    other = "other"


class MediaSource(str, enum.Enum):
    camera = "camera"
    gallery = "gallery"
    unknown = "unknown"


class ApprovalDecision(str, enum.Enum):
    approved = "approved"
    auto_approved = "auto_approved"  # R1a — tizim tasdiqlagan, actor_id = NULL
    rejected = "rejected"
    reopened = "reopened"
    price_proposed = "price_proposed"
    price_accepted = "price_accepted"
    price_disputed = "price_disputed"


class FlagSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class FlagResolution(str, enum.Enum):
    accepted = "accepted"
    false_positive = "false_positive"
    confirmed_fraud = "confirmed_fraud"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Resolution(str, enum.Enum):
    repaired = "repaired"
    no_defect = "no_defect"
    external = "external"


# --- Rollar va xodimlar ------------------------------------------------------


class Role(Base, TimestampMixin):
    """Rol = NOM + `kind`. Ruxsat to'plami emas."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.Text, unique=True)
    name_uz: Mapped[str] = mapped_column(sa.Text)
    name_ru: Mapped[str] = mapped_column(sa.Text)
    icon: Mapped[str] = mapped_column(sa.Text, default="👤")
    kind: Mapped[RoleKind] = mapped_column(py_enum(RoleKind, "role_kind"))
    is_system: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    sort: Mapped[int] = mapped_column(default=100)

    templates: Mapped[list[RoleTemplate]] = relationship(
        back_populates="role", cascade="all, delete-orphan", lazy="selectin"
    )

    def name(self, lang: str = "uz") -> str:
        return pick(lang, self.name_uz, self.name_ru)


class RoleTemplate(Base):
    """Rol qaysi shablonlarni ko'radi."""

    __tablename__ = "role_templates"

    role_id: Mapped[int] = mapped_column(
        sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    template_id: Mapped[int] = mapped_column(
        sa.ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True
    )
    sort: Mapped[int] = mapped_column(default=100)

    role: Mapped[Role] = relationship(back_populates="templates")
    template: Mapped[Template] = relationship(lazy="selectin")


class Employee(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    tg_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, unique=True, default=None)
    tg_username: Mapped[str | None] = mapped_column(sa.Text, default=None)
    phone: Mapped[str] = mapped_column(sa.Text, unique=True)
    full_name: Mapped[str] = mapped_column(sa.Text)
    role_id: Mapped[int] = mapped_column(sa.ForeignKey("roles.id"))  # bitta rol
    workshop_name: Mapped[str | None] = mapped_column(sa.Text, default=None)
    workshop_lat: Mapped[Coord | None] = mapped_column(default=None)
    workshop_lon: Mapped[Coord | None] = mapped_column(default=None)
    status: Mapped[EmployeeStatus] = mapped_column(
        py_enum(EmployeeStatus, "employee_status"), default=EmployeeStatus.active
    )
    hired_at: Mapped[dt.date | None] = mapped_column(default=None)
    fired_at: Mapped[dt.date | None] = mapped_column(default=None)
    lang: Mapped[str] = mapped_column(sa.Text, default="uz")
    tg_blocked: Mapped[bool] = mapped_column(default=False)
    settings: Mapped[dict] = mapped_column(JSONType, default=dict)

    role: Mapped[Role] = relationship(lazy="selectin")

    __table_args__ = (sa.Index("ix_employees_role_status", "role_id", "status"),)

    @property
    def kind(self) -> RoleKind:
        return self.role.kind

    @property
    def is_active(self) -> bool:
        return self.status == EmployeeStatus.active and self.deleted_at is None


# --- Avtopark ----------------------------------------------------------------


class Vehicle(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    plate_number: Mapped[str] = mapped_column(sa.Text, unique=True)  # 01A123BC
    plate_display: Mapped[str] = mapped_column(sa.Text)  # 01 A 123 BC
    vin: Mapped[str | None] = mapped_column(sa.Text, default=None)
    brand: Mapped[str] = mapped_column(sa.Text, default="")
    model: Mapped[str] = mapped_column(sa.Text, default="")
    year: Mapped[int | None] = mapped_column(default=None)
    color: Mapped[str | None] = mapped_column(sa.Text, default=None)
    tariff: Mapped[str | None] = mapped_column(sa.Text, default=None)
    is_electric: Mapped[bool] = mapped_column(default=True)
    battery_kwh: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 2), default=None)
    battery_soh: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2), default=None)
    status: Mapped[VehicleStatus] = mapped_column(
        py_enum(VehicleStatus, "vehicle_status"), default=VehicleStatus.active
    )
    odometer_km: Mapped[int | None] = mapped_column(default=None)
    odometer_updated_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    fleet_car_id: Mapped[str | None] = mapped_column(sa.Text, unique=True, default=None)
    current_driver_name: Mapped[str | None] = mapped_column(sa.Text, default=None)
    current_driver_fleet_id: Mapped[str | None] = mapped_column(sa.Text, default=None)
    notes: Mapped[str | None] = mapped_column(sa.Text, default=None)

    # --- Fleet sinxroni (Faza 3) — ⚠️ FAQAT O'QISH ---
    #: Fleet'dagi status (ma'lumot uchun; platforma uni **yozmaydi**)
    fleet_status: Mapped[str | None] = mapped_column(sa.Text, default=None)
    fleet_synced_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    #: Fleet'da yo'q, platformada bor — o'chirilmaydi, faqat belgilanadi (§5)
    fleet_missing: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (sa.Index("ix_vehicles_status", "status"),)

    @property
    def title(self) -> str:
        parts = [self.plate_display]
        if self.brand or self.model:
            parts.append(f"{self.brand} {self.model}".strip())
        return " · ".join(p for p in parts if p)


# --- Shablon dvigateli -------------------------------------------------------


class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.Text, unique=True)
    name_uz: Mapped[str] = mapped_column(sa.Text)
    name_ru: Mapped[str] = mapped_column(sa.Text)
    subject_type: Mapped[SubjectType] = mapped_column(
        py_enum(SubjectType, "subject_type"), default=SubjectType.vehicle
    )
    has_money: Mapped[bool] = mapped_column(default=True)
    negotiable: Mapped[bool] = mapped_column(default=True)
    field_mapping: Mapped[dict] = mapped_column(JSONType, default=dict)
    sections: Mapped[list] = mapped_column(JSONType, default=list)
    icon: Mapped[str] = mapped_column(sa.Text, default="📝")
    color: Mapped[str | None] = mapped_column(sa.Text, default=None)
    version: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(default=True)

    fields: Mapped[list[TemplateField]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TemplateField.sort",
    )

    def name(self, lang: str = "uz") -> str:
        return pick(lang, self.name_uz, self.name_ru)


class TemplateField(Base):
    __tablename__ = "template_fields"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(sa.ForeignKey("templates.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(sa.Text)
    label_uz: Mapped[str] = mapped_column(sa.Text)
    label_ru: Mapped[str] = mapped_column(sa.Text)
    hint_uz: Mapped[str | None] = mapped_column(sa.Text, default=None)
    hint_ru: Mapped[str | None] = mapped_column(sa.Text, default=None)
    type: Mapped[str] = mapped_column(sa.Text)
    section: Mapped[str | None] = mapped_column(sa.Text, default=None)
    sort: Mapped[int] = mapped_column(default=100)
    is_required: Mapped[bool] = mapped_column(default=False)
    options: Mapped[dict] = mapped_column(JSONType, default=dict)
    validation: Mapped[dict] = mapped_column(JSONType, default=dict)
    visible_if: Mapped[dict | None] = mapped_column(JSONType, default=None)

    template: Mapped[Template] = relationship(back_populates="fields")

    __table_args__ = (sa.UniqueConstraint("template_id", "code", name="uq_template_field_code"),)


class TemplateVersion(Base):
    """Nashr etilgan snapshot — eski hisobot o'z versiyasi bilan ko'rsatiladi."""

    __tablename__ = "template_versions"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(sa.ForeignKey("templates.id", ondelete="CASCADE"))
    version: Mapped[int]
    schema_json: Mapped[dict] = mapped_column("schema", JSONType)
    published_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    published_by: Mapped[int | None] = mapped_column(sa.ForeignKey("employees.id"), default=None)

    __table_args__ = (sa.UniqueConstraint("template_id", "version", name="uq_template_version"),)


# --- Hisobot yadrosi ---------------------------------------------------------


class Submission(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(sa.Text, unique=True)
    template_id: Mapped[int] = mapped_column(sa.ForeignKey("templates.id"))
    template_version: Mapped[int] = mapped_column(default=1)
    author_id: Mapped[int] = mapped_column(sa.ForeignKey("employees.id"))
    co_authors: Mapped[list] = mapped_column(BigIntArray, default=list)
    subject_vehicle_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("vehicles.id"), default=None
    )
    subject_employee_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("employees.id"), default=None
    )
    related_submission_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("submissions.id"), default=None
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        py_enum(SubmissionStatus, "submission_status"), default=SubmissionStatus.DRAFT
    )
    data: Mapped[dict] = mapped_column(JSONType, default=dict)

    # promoted ustunlar (field_mapping orqali to'ldiriladi)
    proposed_labor_amount: Mapped[Money] = mapped_column(default=Decimal("0.00"))
    labor_amount: Mapped[Money | None] = mapped_column(default=None)  # tasdiqlangan
    parts_amount: Mapped[Money] = mapped_column(default=Decimal("0.00"))
    total_amount: Mapped[Money] = mapped_column(default=Decimal("0.00"))

    price_negotiated: Mapped[bool] = mapped_column(default=False)
    auto_approved: Mapped[bool] = mapped_column(default=False)  # R1a

    arrived_at: Mapped[dt.datetime | None] = mapped_column(default=None)  # server vaqti
    left_at: Mapped[dt.datetime | None] = mapped_column(default=None)  # server vaqti
    resolution: Mapped[Resolution | None] = mapped_column(
        py_enum(Resolution, "submission_resolution"), default=None
    )
    is_external: Mapped[bool] = mapped_column(default=False)
    submitted_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    decided_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    price_proposed_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    # --- qarz daftari (ADR-0015) ---
    #: Qarz asosi: tasdiqlangan ish haqi + `self_funded` qismlar. Serverda hisoblanadi (R5/P3)
    payable_amount: Mapped[Money] = mapped_column(default=Decimal("0.00"))
    #: To'langani. P2 — hech qachon `payable_amount` dan oshmaydi
    paid_amount: Mapped[Money] = mapped_column(default=Decimal("0.00"))

    geo_lat: Mapped[Coord | None] = mapped_column(default=None)
    geo_lon: Mapped[Coord | None] = mapped_column(default=None)
    flags_count: Mapped[int] = mapped_column(default=0)

    author: Mapped[Employee] = relationship(foreign_keys=[author_id], lazy="selectin")
    template: Mapped[Template] = relationship(lazy="selectin")
    vehicle: Mapped[Vehicle | None] = relationship(lazy="selectin")
    lines: Mapped[list[SubmissionLine]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SubmissionLine.id",
    )
    media: Mapped[list[Media]] = relationship(
        back_populates="submission", lazy="selectin", order_by="Media.id"
    )

    __table_args__ = (
        # P2 — ortiqcha to'lov yo'q
        sa.CheckConstraint(
            "paid_amount >= 0 AND paid_amount <= payable_amount",
            name="ck_submission_paid_le_payable",
        ),
        sa.Index("ix_submissions_status_submitted", "status", "submitted_at"),
        sa.Index("ix_submissions_vehicle", "subject_vehicle_id", "submitted_at"),
        # qarz ro'yxati: kim, qancha qarz, eng eskisidan (FIFO)
        sa.Index("ix_submissions_author_status", "author_id", "status", "submitted_at"),
    )

    @property
    def debt(self) -> Decimal:
        """Qolgan qarz. `APPROVED` bo'lmasa — 0."""
        if self.status not in PAYABLE_STATUSES:
            return Decimal("0.00")
        return self.payable_amount - self.paid_amount

    @property
    def downtime_seconds(self) -> int | None:
        if self.arrived_at is None or self.left_at is None:
            return None
        from app.db.base import as_utc

        return int((as_utc(self.left_at) - as_utc(self.arrived_at)).total_seconds())


class SubmissionLine(Base, TimestampMixin):
    __tablename__ = "submission_lines"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        sa.ForeignKey("submissions.id", ondelete="CASCADE")
    )
    kind: Mapped[LineKind] = mapped_column(py_enum(LineKind, "line_kind"))
    catalog_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    name: Mapped[str] = mapped_column(sa.Text)
    qty: Mapped[Qty] = mapped_column(default=Decimal("1.00"))

    # R2a — proposed_* immutable
    proposed_unit_price: Mapped[Money] = mapped_column(default=Decimal("0.00"))
    proposed_amount: Mapped[Money] = mapped_column(default=Decimal("0.00"))
    approved_unit_price: Mapped[Money | None] = mapped_column(default=None)
    approved_amount: Mapped[Money | None] = mapped_column(default=None)

    price_changed_by: Mapped[int | None] = mapped_column(
        sa.ForeignKey("employees.id"), default=None
    )
    price_change_reason: Mapped[str | None] = mapped_column(sa.Text, default=None)
    mechanic_accepted_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    mechanic_accept_mode: Mapped[AcceptMode | None] = mapped_column(
        py_enum(AcceptMode, "accept_mode"), default=None
    )
    reference_amount: Mapped[Money | None] = mapped_column(default=None)
    deviation_pct: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 2), default=None)
    supplier_name: Mapped[str | None] = mapped_column(sa.Text, default=None)
    #: ⭐ «O'z hisobimdan» — faqat `kind='part'` uchun ma'noli (ADR-0016).
    #: True → muallif o'z puliga oldi, narx kiritadi, qarzga kiradi (chek fotosi majburiy).
    #: False → kompaniya oldi, narx 0, qarzga kirmaydi.
    self_funded: Mapped[bool] = mapped_column(default=False)
    is_original: Mapped[bool | None] = mapped_column(default=None)
    warranty_days: Mapped[int | None] = mapped_column(default=None)

    submission: Mapped[Submission] = relationship(back_populates="lines")

    __table_args__ = (
        # R2 — admin narxni faqat kamaytira oladi
        sa.CheckConstraint(
            "approved_amount IS NULL OR approved_amount <= proposed_amount",
            name="ck_line_approved_le_proposed",
        ),
        # P6 — kompaniya to'lagan qismda narx bo'lmaydi (R2 CHECK buzilmasin)
        sa.CheckConstraint(
            "kind = 'labor' OR self_funded OR proposed_amount = 0",
            name="ck_line_company_part_no_price",
        ),
        # R2b — kamaytirilsa sabab majburiy
        sa.CheckConstraint(
            "approved_amount IS NULL"
            " OR approved_amount >= proposed_amount"
            " OR price_change_reason IS NOT NULL",
            name="ck_line_reduction_reason",
        ),
        sa.Index("ix_lines_submission", "submission_id"),
        sa.Index("ix_lines_catalog", "catalog_id", "kind"),
    )


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    submission_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("submissions.id", ondelete="CASCADE"), default=None
    )
    field_code: Mapped[str | None] = mapped_column(sa.Text, default=None)
    kind: Mapped[MediaKind] = mapped_column(
        py_enum(MediaKind, "media_kind"), default=MediaKind.other
    )
    storage_key: Mapped[str] = mapped_column(sa.Text)
    tg_file_id: Mapped[str | None] = mapped_column(sa.Text, default=None)
    mime: Mapped[str] = mapped_column(sa.Text, default="image/jpeg")
    size_bytes: Mapped[int] = mapped_column(default=0)
    width: Mapped[int | None] = mapped_column(default=None)
    height: Mapped[int | None] = mapped_column(default=None)
    sha256: Mapped[str] = mapped_column(sa.Text)
    phash: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    exif_taken_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    exif_lat: Mapped[Coord | None] = mapped_column(default=None)
    exif_lon: Mapped[Coord | None] = mapped_column(default=None)
    source: Mapped[MediaSource] = mapped_column(
        py_enum(MediaSource, "media_source"), default=MediaSource.unknown
    )
    uploaded_by: Mapped[int] = mapped_column(sa.ForeignKey("employees.id"))
    uploaded_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    submission: Mapped[Submission | None] = relationship(back_populates="media")

    __table_args__ = (
        sa.Index("ix_media_submission", "submission_id"),
        sa.Index("ix_media_sha256", "sha256"),
        sa.Index("ix_media_phash", "phash"),
    )


class Approval(Base):
    """Tasdiqlash va narx kelishuvining har bir qadami — nizolarda yagona dalil."""

    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        sa.ForeignKey("submissions.id", ondelete="CASCADE")
    )
    actor_id: Mapped[int | None] = mapped_column(sa.ForeignKey("employees.id"), default=None)
    decision: Mapped[ApprovalDecision] = mapped_column(
        py_enum(ApprovalDecision, "approval_decision")
    )
    line_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    amount_before: Mapped[Money | None] = mapped_column(default=None)
    amount_after: Mapped[Money | None] = mapped_column(default=None)
    comment: Mapped[str | None] = mapped_column(sa.Text, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)

    __table_args__ = (sa.Index("ix_approvals_submission", "submission_id", "created_at"),)


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        sa.ForeignKey("submissions.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(sa.Text)
    severity: Mapped[FlagSeverity] = mapped_column(py_enum(FlagSeverity, "flag_severity"))
    details: Mapped[dict] = mapped_column(JSONType, default=dict)
    resolved_by: Mapped[int | None] = mapped_column(sa.ForeignKey("employees.id"), default=None)
    resolution: Mapped[FlagResolution | None] = mapped_column(
        py_enum(FlagResolution, "flag_resolution"), default=None
    )
    resolution_comment: Mapped[str | None] = mapped_column(sa.Text, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)

    __table_args__ = (sa.Index("ix_flags_submission", "submission_id"),)


# --- Spravochniklar ----------------------------------------------------------


class WorkCatalog(Base, TimestampMixin):
    """Ish turlari. ⚠️ `reference_price` — R3: reporter roliga API'da ham berilmaydi."""

    __tablename__ = "work_catalog"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.Text, unique=True)
    name_uz: Mapped[str] = mapped_column(sa.Text)
    name_ru: Mapped[str] = mapped_column(sa.Text)
    category: Mapped[str | None] = mapped_column(sa.Text, default=None)
    reference_price: Mapped[Money | None] = mapped_column(default=None)
    standard_minutes: Mapped[int | None] = mapped_column(default=None)
    warranty_days: Mapped[int | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)

    def name(self, lang: str = "uz") -> str:
        return pick(lang, self.name_uz, self.name_ru)


class PartsCatalog(Base, TimestampMixin):
    __tablename__ = "parts_catalog"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.Text, unique=True)
    name_uz: Mapped[str] = mapped_column(sa.Text)
    name_ru: Mapped[str] = mapped_column(sa.Text)
    article: Mapped[str | None] = mapped_column(sa.Text, default=None)
    category: Mapped[str | None] = mapped_column(sa.Text, default=None)
    last_price: Mapped[Money | None] = mapped_column(default=None)
    avg_price_90d: Mapped[Money | None] = mapped_column(default=None)
    default_supplier: Mapped[str | None] = mapped_column(sa.Text, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)

    def name(self, lang: str = "uz") -> str:
        return pick(lang, self.name_uz, self.name_ru)


class CatalogItem(Base):
    """Universal kichik spravochnik (`select` maydonlari uchun): nosozlik kategoriyalari…"""

    __tablename__ = "catalog_items"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    catalog: Mapped[str] = mapped_column(sa.Text)  # masalan `fault_categories`
    code: Mapped[str] = mapped_column(sa.Text)
    name_uz: Mapped[str] = mapped_column(sa.Text)
    name_ru: Mapped[str] = mapped_column(sa.Text)
    icon: Mapped[str | None] = mapped_column(sa.Text, default=None)
    sort: Mapped[int] = mapped_column(default=100)
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (sa.UniqueConstraint("catalog", "code", name="uq_catalog_item"),)

    def name(self, lang: str = "uz") -> str:
        return pick(lang, self.name_uz, self.name_ru)


# --- To'lov (qarz daftari), audit --------------------------------------------
#
# ⚠️ `periods` va `payouts` YO'Q — ADR-0015. Qarz hisobot darajasida yuritiladi:
# `submissions.payable_amount − submissions.paid_amount`.


class Payment(Base):
    """To'lov yozuvi. Tahrirlanmaydi — xato bo'lsa faqat `void` (P5)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(sa.ForeignKey("employees.id"))  # kimga
    amount: Mapped[Money]
    actor_id: Mapped[int] = mapped_column(sa.ForeignKey("employees.id"))  # kim kiritdi
    note: Mapped[str | None] = mapped_column(sa.Text, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)

    voided_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    voided_by: Mapped[int | None] = mapped_column(sa.ForeignKey("employees.id"), default=None)
    void_reason: Mapped[str | None] = mapped_column(sa.Text, default=None)

    employee: Mapped[Employee] = relationship(foreign_keys=[employee_id], lazy="selectin")
    allocations: Mapped[list[PaymentAllocation]] = relationship(
        back_populates="payment", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        sa.CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        # P5 — bekor qilinsa sabab majburiy
        sa.CheckConstraint(
            "voided_at IS NULL OR void_reason IS NOT NULL",
            name="ck_payment_void_reason",
        ),
        sa.Index("ix_payments_employee", "employee_id", "created_at"),
    )

    @property
    def is_voided(self) -> bool:
        return self.voided_at is not None


class PaymentAllocation(Base):
    """To'lov qaysi hisobotga qancha tushdi. P4: yig'indi = `payment.amount`."""

    __tablename__ = "payment_allocations"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(
        sa.ForeignKey("payments.id", ondelete="CASCADE")
    )
    submission_id: Mapped[int] = mapped_column(sa.ForeignKey("submissions.id"))
    amount: Mapped[Money]

    payment: Mapped[Payment] = relationship(back_populates="allocations")

    __table_args__ = (
        sa.CheckConstraint("amount > 0", name="ck_allocation_amount_positive"),
        sa.Index("ix_allocations_submission", "submission_id"),
    )


class AuditLog(Base):
    """⚠️ Hech qachon o'chirilmaydi va tahrirlanmaydi (R9)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(sa.ForeignKey("employees.id"), default=None)
    action: Mapped[str] = mapped_column(sa.Text)
    entity_type: Mapped[str] = mapped_column(sa.Text)
    entity_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    before: Mapped[dict | None] = mapped_column(JSONType, default=None)
    after: Mapped[dict | None] = mapped_column(JSONType, default=None)
    ip: Mapped[str | None] = mapped_column(sa.Text, default=None)
    tg_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        sa.Index("ix_audit_entity", "entity_type", "entity_id"),
        sa.Index("ix_audit_actor", "actor_id", "created_at"),
    )


class Broadcast(Base):
    """Adminning barcha xodimlarga e'loni. ⚠️ Hech qachon o'chirilmaydi (R9) —
    soft delete ham yo'q, chunki bu yuborilgan xabar tarixi."""

    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(sa.ForeignKey("employees.id"))
    # XOM matn — HTML escape faqat botga yuborishdan oldin (app/bot/notifier.py)
    body: Mapped[str] = mapped_column(sa.Text)
    recipients_total: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)


class Notification(Base):
    """Chiquvchi navbat (outbox) — Redis o'rniga (ADR-0004)."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    employee_id: Mapped[int | None] = mapped_column(sa.ForeignKey("employees.id"), default=None)
    chat_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)  # guruh uchun
    # e'lon yetkazilishini sanash uchun — JSON payload'dan so'ramaymiz (ustun tez)
    broadcast_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("broadcasts.id"), default=None
    )
    template_code: Mapped[str] = mapped_column(sa.Text)
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[NotificationStatus] = mapped_column(
        py_enum(NotificationStatus, "notification_status"), default=NotificationStatus.pending
    )
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(sa.Text, default=None)
    not_before: Mapped[dt.datetime] = mapped_column(default=utcnow)
    sent_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        sa.Index("ix_notifications_status", "status", "not_before"),
        sa.Index("ix_notifications_broadcast", "broadcast_id"),
    )


class RefreshToken(Base):
    """Mini App uchun refresh tokenlar — rol o'zgarsa bekor qilinadi."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(sa.ForeignKey("employees.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(sa.Text, unique=True)
    expires_at: Mapped[dt.datetime]
    revoked_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)


class Counter(Base):
    """Hisobot raqami uchun yillik hisoblagich (WO-2026-000123)."""

    __tablename__ = "counters"

    key: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    value: Mapped[int] = mapped_column(default=0)
