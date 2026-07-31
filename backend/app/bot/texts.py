"""Xabar matnlarini yig'ish — kartochka, kelishuv, statistika."""

from __future__ import annotations

from decimal import Decimal

from app.core.i18n import fmt_dt, fmt_duration, fmt_money, status_label, t
from app.db.base import ZERO
from app.db.models import LineKind, Submission, SubmissionStatus
from app.domain.pricing.service import LinePriceContext


def submission_line_title(name: str, limit: int = 32) -> str:
    return name if len(name) <= limit else name[: limit - 1] + "…"


def render_card(
    submission: Submission,
    lang: str,
    *,
    contexts: dict[int, LinePriceContext] | None = None,
    show_history: bool = False,
) -> str:
    """Hisobot kartochkasi. `show_history` — faqat admin/buxgalter uchun (R3)."""
    parts: list[str] = [
        t(
            "card_header",
            lang,
            number=submission.number,
            status=status_label(submission.status, lang),
            author=submission.author.full_name if submission.author else "—",
        )
    ]
    if submission.vehicle is not None:
        parts.append(t("card_vehicle", lang, title=submission.vehicle.title))
    if submission.arrived_at:
        parts.append(
            t(
                "card_times",
                lang,
                arrived=fmt_dt(submission.arrived_at, lang),
                left=fmt_dt(submission.left_at, lang),
                downtime=fmt_duration(submission.downtime_seconds, lang),
            )
        )
    if submission.odometer_km:
        parts.append(t("card_odometer", lang, km=f"{submission.odometer_km:,}".replace(",", " ")))

    labor_lines = [ln for ln in submission.lines if ln.kind == LineKind.labor]
    if labor_lines:
        parts.append(t("card_labor", lang))
        for line in labor_lines:
            row = f"🔧 {line.name}"
            if line.qty and line.qty != Decimal("1.00"):
                row += f" ×{line.qty.normalize()}"
            row += f"\n   {fmt_money(line.proposed_amount, lang)}"
            if line.approved_amount is not None and line.approved_amount != line.proposed_amount:
                row += f" → <b>{fmt_money(line.approved_amount, lang)}</b>"
            parts.append(row)
            if show_history and contexts and line.id in contexts:
                parts.append(_history_block(contexts[line.id], submission, lang))

    part_lines = [ln for ln in submission.lines if ln.kind == LineKind.part]
    if part_lines:
        parts.append(t("card_parts", lang))
        for line in part_lines:
            row = f"📦 {line.name} ×{line.qty.normalize()}"
            amount = line.approved_amount if line.approved_amount is not None else line.proposed_amount
            if amount and amount > ZERO:
                row += f" — {fmt_money(amount, lang)}"
            parts.append(row)

    data = submission.data or {}
    for field_code in ("problem_description", "comment", "recommendation"):
        value = data.get(field_code)
        if value:
            parts.append(t("card_comment", lang, text=value))

    parts.append("")
    parts.append(t("card_total_proposed", lang, amount=fmt_money(submission.proposed_labor_amount, lang)))
    if submission.labor_amount is not None:
        parts.append(
            t("card_total_approved", lang, amount=fmt_money(submission.labor_amount, lang))
        )
    if submission.auto_approved:
        parts.append(t("card_auto_approved", lang))

    return "\n".join(parts)


def _history_block(ctx: LinePriceContext, submission: Submission, lang: str) -> str:
    if not ctx.has_history:
        return t("price_context_none", lang)
    block = t(
        "price_context",
        lang,
        n=ctx.count,
        avg=fmt_money(ctx.avg_approved, lang),
        min=fmt_money(ctx.min_approved, lang),
        max=fmt_money(ctx.max_approved, lang),
    )
    if ctx.author_avg is not None:
        block += t(
            "price_context_author",
            lang,
            name=submission.author.full_name if submission.author else "—",
            avg=fmt_money(ctx.author_avg, lang),
            pct=int(ctx.author_reduction_pct or 0),
        )
    return block


def render_negotiation(submission: Submission, lang: str, *, hours: int) -> str:
    """Ustaga: nima so'raganingiz va admin nima taklif qilgani."""
    rows: list[str] = []
    reason = ""
    for line in submission.lines:
        if line.kind != LineKind.labor or line.approved_amount is None:
            continue
        if line.approved_amount >= line.proposed_amount:
            continue
        rows.append(
            t(
                "negotiation_line",
                lang,
                name=line.name,
                proposed=fmt_money(line.proposed_amount, lang),
                approved=fmt_money(line.approved_amount, lang),
            )
        )
        reason = line.price_change_reason or reason

    return t(
        "negotiation_card",
        lang,
        number=submission.number,
        vehicle=submission.vehicle.plate_display if submission.vehicle else "—",
        lines="\n".join(rows),
        reason=reason or "—",
        hours=hours,
    )


def render_list_row(submission: Submission, lang: str) -> str:
    amount = (
        submission.labor_amount
        if submission.labor_amount is not None
        else submission.proposed_labor_amount
    )
    plate = submission.vehicle.plate_display if submission.vehicle else "—"
    return f"{status_label(submission.status, lang)} · {plate} · {fmt_money(amount, lang)}"


def render_history(rows: list[tuple[str, str, str, str]], lang: str) -> str:
    """Kelishuv tarixi: (vaqt, kim, qaror, izoh)."""
    if not rows:
        return t("nothing_found", lang)
    lines = []
    for moment, actor, decision, comment in rows:
        line = f"• {moment} — <b>{decision}</b> ({actor})"
        if comment:
            line += f"\n   <i>{comment}</i>"
        lines.append(line)
    return "\n".join(lines)


def can_author_edit(submission: Submission) -> bool:
    return submission.status in (SubmissionStatus.DRAFT, SubmissionStatus.REOPENED)
