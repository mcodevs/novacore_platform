"""API sxemalari. Pul — number, vaqt — ISO 8601 UTC, nomlash — snake_case."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    init_data: str


class RoleOut(BaseModel):
    code: str
    name: str
    kind: str
    icon: str


class EmployeeOut(BaseModel):
    id: int
    full_name: str
    phone: str
    lang: str
    role: RoleOut
    role_id: int
    workshop_name: str | None = None
    status: str = "active"
    #: Xodim botga `/start` bosib telefonini yuborganmi (admin ro'yxati uchun)
    tg_linked: bool = False


class TemplateOut(BaseModel):
    id: int
    code: str
    name: str
    icon: str
    version: int
    has_money: bool
    negotiable: bool


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    employee: EmployeeOut
    templates: list[TemplateOut]


class RefreshRequest(BaseModel):
    refresh_token: str


class MeUpdate(BaseModel):
    lang: str | None = None


class VehicleOut(BaseModel):
    id: int
    plate_number: str
    plate_display: str
    brand: str
    model: str
    year: int | None
    status: str
    odometer_km: int | None
    current_driver_name: str | None = None


class WorkCatalogOut(BaseModel):
    id: int
    code: str
    name: str
    category: str | None
    # ⚠️ R3/N9 — `reference_price` faqat admin/buxgalterga qaytariladi
    reference_price: Decimal | None = None


class PartsCatalogOut(BaseModel):
    id: int
    code: str
    name: str
    category: str | None
    last_price: Decimal | None = None


class LineOut(BaseModel):
    id: int
    kind: str
    name: str
    qty: Decimal
    proposed_amount: Decimal
    approved_amount: Decimal | None
    price_change_reason: str | None
    mechanic_accepted_at: dt.datetime | None
    mechanic_accept_mode: str | None
    #: ⭐ «O'z hisobimdan» olingan qism — qarzga kiradi (ADR-0016)
    self_funded: bool = False


class MediaOut(BaseModel):
    id: int
    field_code: str | None
    kind: str
    mime: str
    url: str


class SubmissionOut(BaseModel):
    id: int
    number: str
    status: str
    template_code: str
    template_version: int
    author_id: int
    author_name: str
    vehicle: VehicleOut | None
    data: dict
    proposed_labor_amount: Decimal
    labor_amount: Decimal | None
    parts_amount: Decimal
    total_amount: Decimal
    #: ⭐ Qarz daftari (ADR-0015)
    payable_amount: Decimal
    paid_amount: Decimal
    debt: Decimal
    auto_approved: bool
    price_negotiated: bool
    arrived_at: dt.datetime | None
    left_at: dt.datetime | None
    submitted_at: dt.datetime | None
    downtime_seconds: int | None
    lines: list[LineOut]
    media: list[MediaOut] = Field(default_factory=list)


class CreateSubmissionRequest(BaseModel):
    template_code: str
    vehicle_id: int | None = None


class PatchSubmissionRequest(BaseModel):
    data: dict


class LineIn(BaseModel):
    kind: str = "labor"
    name: str
    qty: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    catalog_id: int | None = None
    supplier_name: str | None = None
    #: ⭐ «O'z hisobimdan» (ADR-0016) — faqat qism qatorida narx ochiladi
    self_funded: bool = False


class LinesRequest(BaseModel):
    lines: list[LineIn]


class CommentRequest(BaseModel):
    comment: str | None = None


class PriceChange(BaseModel):
    line_id: int
    amount: Decimal


class ProposePriceRequest(BaseModel):
    lines: list[PriceChange]
    comment: str


class PriceContextOut(BaseModel):
    line_id: int
    name: str
    proposed_amount: Decimal
    count: int
    avg_approved: Decimal | None
    min_approved: Decimal | None
    max_approved: Decimal | None
    author_avg: Decimal | None
    author_reduction_pct: Decimal | None
    quick_amounts: list[Decimal]


class PriceStatsOut(BaseModel):
    lines_total: int
    lines_reduced: int
    proposed_total: Decimal
    approved_total: Decimal
    reduction_total: Decimal
    reduction_rate_pct: Decimal
    avg_reduction_pct: Decimal
    disputes: int


class ApprovalOut(BaseModel):
    id: int
    actor_id: int | None
    decision: str
    line_id: int | None
    amount_before: Decimal | None
    amount_after: Decimal | None
    comment: str | None
    created_at: dt.datetime


# --- Qarz daftari (ADR-0015) --------------------------------------------------


class BalanceOut(BaseModel):
    """`GET /me/balance` — xodimning O'Z pul holati (boshqalarniki emas)."""

    #: Bizning shu xodimdan qarzimiz — to'lanmagan tasdiqlangan ishlar yig'indisi
    debt: Decimal
    #: Qarz qaysi ishlardan yig'ilgan (nechta hisobot)
    count: int
    #: Ishlatilmagan avans — qarzdan ortiq to'langan pul (P7)
    advance: Decimal


class EmployeeDebtOut(BaseModel):
    employee_id: int
    full_name: str
    debt: Decimal
    count: int
    #: Ishlatilmagan avans — qarzdan ortiq to'langan pul (P7)
    advance: Decimal = Decimal("0")


class DebtSummaryOut(BaseModel):
    total: Decimal
    advance_total: Decimal = Decimal("0")
    employees: list[EmployeeDebtOut]


class DebtItemOut(BaseModel):
    """Qarz ro'yxatidagi bitta hisobot — eng eskisidan tartiblanadi (FIFO)."""

    submission_id: int
    number: str
    vehicle: str | None
    submitted_at: dt.datetime | None
    payable_amount: Decimal
    paid_amount: Decimal
    debt: Decimal


class AllocationOut(BaseModel):
    submission_id: int
    #: Hisobot raqami — to'lov kartochkasida «#WO-…» bo'lib ko'rinadi.
    #: `_payment_out` uni bilmaydi (bog'lanish yuklanmagan), endpoint to'ldiradi.
    number: str = ""
    amount: Decimal
    fully_paid: bool


class PaymentOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    amount: Decimal
    note: str | None
    created_at: dt.datetime
    voided_at: dt.datetime | None
    void_reason: str | None
    allocations: list[AllocationOut]


class CreatePaymentRequest(BaseModel):
    """Uch rejim: `submission_ids` (chekbox) · `amount` (FIFO) · ikkalasi (qisman)."""

    employee_id: int
    submission_ids: list[int] | None = None
    amount: Decimal | None = None
    note: str | None = None


class VoidPaymentRequest(BaseModel):
    reason: str


class DashboardOut(BaseModel):
    period: str
    total_submissions: int
    approved_count: int
    proposed_total: Decimal
    approved_total: Decimal
    parts_total: Decimal
    saved: Decimal
    saved_pct: Decimal
    auto_approved_count: int
    auto_approved_total: Decimal
    pending_review: int
    in_negotiation: int
    vehicles_in_service: int
    debt_total: Decimal
    paid_total: Decimal


class VehicleIn(BaseModel):
    plate_number: str
    brand: str = ""
    model: str = ""
    year: int | None = None
    color: str | None = None
    vin: str | None = None
    tariff: str | None = None
    fleet_car_id: str | None = None


class EmployeeIn(BaseModel):
    full_name: str
    phone: str
    role_id: int
    workshop_name: str | None = None
    lang: str = "uz"


class LinkableSubmissionOut(BaseModel):
    """`submission_picker` nomzodi — summa YO'Q (R3 ruhi)."""

    id: int
    number: str
    status: str
    template_code: str
    author_name: str
    vehicle_plate: str | None
    submitted_at: dt.datetime | None


class RoleIn(BaseModel):
    code: str
    name_uz: str
    name_ru: str
    icon: str = "👤"
    kind: str
    template_ids: list[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Rol konstruktori (Faza 2) — `code` o'zgarmas, qolgani tahrirlanadi."""

    name_uz: str | None = None
    name_ru: str | None = None
    icon: str | None = None
    kind: str | None = None
    template_ids: list[int] | None = None
    is_active: bool | None = None
    sort: int | None = None


class TemplateIn(BaseModel):
    """Shablon konstruktori (Faza 2) — seed JSON'i bilan bir xil ko'rinish.

    Chuqur tekshiruv `domain/template/builder.validate_definition` da: maydon
    turlari, kodlar, `field_mapping` va `visible_if` havolalari.
    """

    code: str = ""
    name: dict[str, str]
    icon: str = "📝"
    subject_type: str = "vehicle"
    has_money: bool = True
    negotiable: bool = True
    is_active: bool | None = None
    field_mapping: dict[str, str] = Field(default_factory=dict)
    sections: list[dict] = Field(default_factory=list)
    fields: list[dict] = Field(default_factory=list)


class SetRoleRequest(BaseModel):
    role_id: int


class SetStatusRequest(BaseModel):
    """`active` / `blocked` / `fired` — R5: ma'lumot qoladi, kirish bloklanadi."""

    status: str


class BroadcastIn(BaseModel):
    """E'lon matni — **xom** ko'rinishda keladi va shundayligicha saqlanadi.

    Uzunlik/bo'shlik tekshiruvi ataylab shu yerda emas, `domain/broadcast` da:
    Pydantic 422 ni FastAPI o'z shaklida qaytaradi, domen xatosi esa hamma
    joydagidek `{"error": {...}}` 400 bo'ladi — klient bitta shaklga tayanadi.
    """

    body: str


class BroadcastOut(BaseModel):
    """E'lon + yetkazilish hisobi (`notifications.broadcast_id` bo'yicha).

    POST javobida barcha yozuvlar hali navbatda: `pending == recipients_total`.
    """

    id: int
    body: str
    recipients_total: int
    created_at: dt.datetime
    author_name: str
    delivered: int = 0
    failed: int = 0
    pending: int = 0
