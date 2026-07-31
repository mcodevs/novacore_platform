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
    workshop_name: str | None = None


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


class PeriodOut(BaseModel):
    id: int
    year: int
    month: int
    status: str
    closed_at: dt.datetime | None


class PrecheckOut(BaseModel):
    can_close: bool
    blockers: list[dict]
    warnings: list[dict]


class PayoutOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    submissions_count: int
    proposed_total: Decimal
    labor_total: Decimal
    reduction_total: Decimal
    bonus: Decimal
    penalty: Decimal
    total: Decimal
    status: str


class AdjustPayoutRequest(BaseModel):
    bonus: Decimal | None = None
    penalty: Decimal | None = None
    reason: str


class ReopenPeriodRequest(BaseModel):
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


class RoleIn(BaseModel):
    code: str
    name_uz: str
    name_ru: str
    icon: str = "👤"
    kind: str
    template_ids: list[int] = Field(default_factory=list)


class SetRoleRequest(BaseModel):
    role_id: int
