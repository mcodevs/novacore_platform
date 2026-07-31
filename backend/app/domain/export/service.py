"""Excel eksport — import YO'Q, faqat eksport (docs/04-flows/03-payroll-and-reports.md §6)."""

from __future__ import annotations

import io

import sqlalchemy as sa
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import TASHKENT
from app.db.base import ZERO, as_utc
from app.db.models import (
    Employee,
    Payout,
    Period,
    Submission,
    SubmissionLine,
    SubmissionStatus,
    Vehicle,
)
from app.domain.payout import service as payout_service

HEADER_FONT = Font(bold=True)
MONEY_FMT = "#,##0"


def _autosize(ws) -> None:  # noqa: ANN001
    for column in ws.columns:
        width = max((len(str(cell.value or "")) for cell in column), default=10)
        ws.column_dimensions[get_column_letter(column[0].column)].width = min(max(width + 2, 10), 45)


def _write_header(ws, headers: list[str]) -> None:  # noqa: ANN001
    ws.append(headers)
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2"


def _fmt_dt(value) -> str:  # noqa: ANN001
    if value is None:
        return ""
    return as_utc(value).astimezone(TASHKENT).strftime("%d.%m.%Y %H:%M")


async def export_submissions(session: AsyncSession, period: Period) -> tuple[str, bytes]:
    """`tamirlar_YYYY_MM.xlsx` — barcha hisobotlar, to'liq ma'lumot."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Ta'mirlar"
    _write_header(
        ws,
        [
            "Raqam",
            "Holat",
            "Xodim",
            "Mashina",
            "Keldi",
            "Ketdi",
            "Downtime (soat)",
            "Probeg",
            "So'ralgan ish haqi",
            "Tasdiqlangan ish haqi",
            "Kamaytirildi",
            "Qismlar",
            "Jami",
            "Avtomatik tasdiq",
            "Yuborilgan",
        ],
    )

    stmt = (
        sa.select(Submission)
        .where(Submission.period_id == period.id, Submission.deleted_at.is_(None))
        .order_by(Submission.submitted_at)
    )
    for sub in (await session.execute(stmt)).scalars().all():
        author = await session.get(Employee, sub.author_id)
        vehicle = (
            await session.get(Vehicle, sub.subject_vehicle_id)
            if sub.subject_vehicle_id
            else None
        )
        downtime = sub.downtime_seconds
        approved = sub.labor_amount if sub.labor_amount is not None else None
        ws.append(
            [
                sub.number,
                sub.status.value,
                author.full_name if author else "",
                vehicle.plate_display if vehicle else "",
                _fmt_dt(sub.arrived_at),
                _fmt_dt(sub.left_at),
                round(downtime / 3600, 1) if downtime is not None else "",
                sub.odometer_km or "",
                float(sub.proposed_labor_amount),
                float(approved) if approved is not None else "",
                float(sub.proposed_labor_amount - (approved or ZERO))
                if approved is not None
                else "",
                float(sub.parts_amount),
                float(sub.total_amount),
                "ha" if sub.auto_approved else "",
                _fmt_dt(sub.submitted_at),
            ]
        )

    for row in ws.iter_rows(min_row=2, min_col=9, max_col=13):
        for cell in row:
            cell.number_format = MONEY_FMT
    _autosize(ws)

    # Ish qatorlari alohida varaqda
    ws2 = wb.create_sheet("Ish qatorlari")
    _write_header(
        ws2,
        [
            "Hisobot",
            "Xodim",
            "Tur",
            "Nomi",
            "Soni",
            "So'ralgan",
            "Tasdiqlangan",
            "Kamaytirish sababi",
            "Rozilik",
        ],
    )
    line_stmt = (
        sa.select(SubmissionLine, Submission)
        .join(Submission, Submission.id == SubmissionLine.submission_id)
        .where(Submission.period_id == period.id, Submission.deleted_at.is_(None))
        .order_by(Submission.number)
    )
    for line, sub in (await session.execute(line_stmt)).all():
        author = await session.get(Employee, sub.author_id)
        ws2.append(
            [
                sub.number,
                author.full_name if author else "",
                line.kind.value,
                line.name,
                float(line.qty),
                float(line.proposed_amount),
                float(line.approved_amount) if line.approved_amount is not None else "",
                line.price_change_reason or "",
                line.mechanic_accept_mode.value if line.mechanic_accept_mode else "",
            ]
        )
    _autosize(ws2)

    buffer = io.BytesIO()
    wb.save(buffer)
    return f"tamirlar_{period.year}_{period.month:02d}.xlsx", buffer.getvalue()


async def export_payouts(session: AsyncSession, period: Period) -> tuple[str, bytes]:
    """`tolovlar_YYYY_MM.xlsx` — buxgalteriyaga."""
    wb = Workbook()
    ws = wb.active
    ws.title = "To'lovlar"
    _write_header(
        ws,
        [
            "Xodim",
            "Rol",
            "Ishlar soni",
            "So'ralgan",
            "Tasdiqlangan (to'lov asosi)",
            "Kelishuvda kamaydi",
            "Bonus",
            "Jarima",
            "JAMI",
            "Status",
        ],
    )

    stmt = sa.select(Payout).where(Payout.period_id == period.id)
    for payout in (await session.execute(stmt)).scalars().all():
        employee = payout.employee
        ws.append(
            [
                employee.full_name,
                employee.role.name_uz,
                payout.submissions_count,
                float(payout.proposed_total),
                float(payout.labor_total),
                float(payout.reduction_total),
                float(payout.bonus),
                float(payout.penalty),
                float(payout.total),
                payout.status.value,
            ]
        )
    for row in ws.iter_rows(min_row=2, min_col=4, max_col=9):
        for cell in row:
            cell.number_format = MONEY_FMT
    _autosize(ws)

    buffer = io.BytesIO()
    wb.save(buffer)
    return f"tolovlar_{period.year}_{period.month:02d}.xlsx", buffer.getvalue()


async def export_savings(session: AsyncSession, period: Period) -> tuple[str, bytes]:
    """⭐ `kelishuv_YYYY_MM.xlsx` — narx kelishuvi tejamkorligi."""
    summary = await payout_service.period_summary(session, period.id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Kelishuv"
    ws.append([f"Narx kelishuvi — {period.year}-{period.month:02d}"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    ws.append(["Ustalar so'radi", float(summary.proposed_total)])
    ws.append(["Tasdiqlandi", float(summary.approved_total)])
    ws.append(["TEJALDI", float(summary.saved)])
    ws.append(["Tejamkorlik %", float(summary.saved_pct)])
    ws.append(["Tasdiqlangan hisobotlar", summary.approved_count])
    ws.append(["Avtomatik tasdiqlangan (admin)", summary.auto_approved_count])
    ws.append(["Avtomatik tasdiqlangan summa", float(summary.auto_approved_total)])
    for row in ws.iter_rows(min_row=3, max_row=9, min_col=2, max_col=2):
        for cell in row:
            cell.number_format = MONEY_FMT

    ws2 = wb.create_sheet("Xodimlar kesimi")
    _write_header(
        ws2,
        ["Xodim", "Ishlar", "So'radi", "Tasdiqlandi", "Kamaytirish %", "Nizolar"],
    )
    stmt = (
        sa.select(Submission.author_id)
        .where(Submission.period_id == period.id, Submission.deleted_at.is_(None))
        .group_by(Submission.author_id)
    )
    from app.domain.pricing import service as pricing_service

    for (employee_id,) in (await session.execute(stmt)).all():
        employee = await session.get(Employee, employee_id)
        stats = await pricing_service.employee_price_stats(
            session, employee_id, period_id=period.id
        )
        count = (
            await session.execute(
                sa.select(sa.func.count(Submission.id)).where(
                    Submission.period_id == period.id,
                    Submission.author_id == employee_id,
                    Submission.deleted_at.is_(None),
                    Submission.status.in_(
                        [SubmissionStatus.APPROVED, SubmissionStatus.PAID]
                    ),
                )
            )
        ).scalar_one()
        ws2.append(
            [
                employee.full_name if employee else str(employee_id),
                int(count),
                float(stats.proposed_total),
                float(stats.approved_total),
                float(stats.avg_reduction_pct),
                stats.disputes,
            ]
        )
    _autosize(ws2)

    buffer = io.BytesIO()
    wb.save(buffer)
    return f"kelishuv_{period.year}_{period.month:02d}.xlsx", buffer.getvalue()


EXPORTS = {
    "submissions": export_submissions,
    "payouts": export_payouts,
    "savings": export_savings,
}


async def build(session: AsyncSession, kind: str, period: Period) -> tuple[str, bytes]:
    if kind not in EXPORTS:
        raise ValueError(f"unknown export: {kind}")
    return await EXPORTS[kind](session, period)


__all__ = ["build", "export_payouts", "export_savings", "export_submissions"]
