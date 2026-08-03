"""Hisobot hayotiy sikli — `arrived_at`/`left_at`, holat o'tishlari, raqamlash."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from app.core.errors import Forbidden, InvalidStateTransition, ValidationFailed
from app.db.base import as_utc, utcnow
from app.db.models import SubmissionStatus, VehicleStatus
from app.domain.submission import service as submission_service
from tests.conftest import (
    create_ready_submission,
    fill_valid_repair,
    get_template,
    make_employee,
    make_vehicle,
)


async def test_create_draft_sets_server_arrival_time(session):
    """R6 — `arrived_at` server vaqti, klient yuborgan qiymat emas."""
    mechanic = await make_employee(session, role_code="mechanic")
    template = await get_template(session, "car_repair")

    before = utcnow()
    submission = await submission_service.create_draft(session, mechanic, template)
    after = utcnow()

    assert submission.status == SubmissionStatus.DRAFT
    assert before <= as_utc(submission.arrived_at) <= after
    assert submission.number.startswith("WO-")
    assert submission.left_at is None


async def test_numbering_is_sequential(session):
    mechanic = await make_employee(session, role_code="mechanic")
    template = await get_template(session, "car_repair")

    first = await submission_service.create_draft(session, mechanic, template)
    second = await submission_service.create_draft(session, mechanic, template)

    year = as_utc(utcnow()).year
    assert first.number == f"WO-{year}-000001"
    assert second.number == f"WO-{year}-000002"


async def test_vehicle_goes_to_service_and_back(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)

    await submission_service.attach_vehicle(session, submission, vehicle)
    assert vehicle.status == VehicleStatus.in_service

    await submission_service.mark_left(session, submission, mechanic)
    assert vehicle.status == VehicleStatus.active
    assert submission.left_at is not None


async def test_downtime_is_left_minus_arrived(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)

    submission.arrived_at = utcnow() - dt.timedelta(hours=3, minutes=26)
    await session.flush()

    downtime = submission.downtime_seconds
    assert downtime is not None
    assert 3 * 3600 + 25 * 60 <= downtime <= 3 * 3600 + 27 * 60


async def test_submit_requires_left_at(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)
    await fill_valid_repair(session, submission, mechanic, vehicle)

    with pytest.raises(ValidationFailed) as excinfo:
        await submission_service.submit(session, submission, mechanic)
    assert excinfo.value.fields["_left_at"] == "need_left_first"

    await submission_service.mark_left(session, submission, mechanic)
    await submission_service.submit(session, submission, mechanic)
    assert submission.status == SubmissionStatus.SUBMITTED
    assert submission.submitted_at is not None


async def test_only_author_can_submit_and_edit(session):
    mechanic = await make_employee(session, role_code="mechanic")
    other = await make_employee(session, role_code="mechanic", name="Boshqa")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)

    with pytest.raises(Forbidden):
        await submission_service.submit(session, submission, other)
    with pytest.raises(Forbidden):
        submission_service.ensure_editable(submission, other)


async def test_submitted_submission_is_not_editable(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, submission, mechanic)

    with pytest.raises(InvalidStateTransition):
        submission_service.ensure_editable(submission, mechanic)
    with pytest.raises(InvalidStateTransition):
        await submission_service.submit(session, submission, mechanic)


async def test_draft_soft_delete_only(session):
    """R9 — o'chirish yo'q, `deleted_at`."""
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, mechanic, template)
    await submission_service.attach_vehicle(session, submission, vehicle)

    await submission_service.delete_draft(session, submission, mechanic)

    assert submission.deleted_at is not None
    assert vehicle.status == VehicleStatus.active
    assert await submission_service.active_draft(session, mechanic) is None


async def test_active_draft_lookup(session):
    mechanic = await make_employee(session, role_code="mechanic")
    template = await get_template(session, "car_repair")
    assert await submission_service.active_draft(session, mechanic) is None

    submission = await submission_service.create_draft(session, mechanic, template)
    found = await submission_service.active_draft(session, mechanic)
    assert found is not None and found.id == submission.id


async def test_pending_review_queue(session):
    mechanic = await make_employee(session, role_code="mechanic")
    await make_employee(session, role_code="admin")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(session, mechanic, vehicle)
    await submission_service.submit(session, submission, mechanic)

    pending = await submission_service.pending_review(session)
    assert [s.id for s in pending] == [submission.id]


async def test_multi_line_totals(session):
    mechanic = await make_employee(session, role_code="mechanic")
    vehicle = await make_vehicle(session)
    submission = await create_ready_submission(
        session,
        mechanic,
        vehicle,
        works=[("Kolodka", Decimal("180000")), ("Disk", Decimal("250000"))],
    )
    await submission_service.submit(session, submission, mechanic)

    assert submission.proposed_labor_amount == Decimal("430000.00")
    assert len(submission.lines) == 2
