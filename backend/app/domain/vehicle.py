"""Mashina statusi bilan bog'liq umumiy yordamchilar (holat mashinasi §2)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Submission, Vehicle, VehicleStatus


async def vehicle_of(session: AsyncSession, submission: Submission) -> Vehicle | None:
    if submission.subject_vehicle_id is None:
        return None
    if submission.vehicle is not None:
        return submission.vehicle
    return await session.get(Vehicle, submission.subject_vehicle_id)


async def to_service(session: AsyncSession, submission: Submission, vehicle: Vehicle) -> None:
    """«Mashina keldi» — ta'mirda (zakaz kelmasligi uchun Fleet'da ham `repairing`)."""
    submission.subject_vehicle_id = vehicle.id
    submission.vehicle = vehicle
    if vehicle.status == VehicleStatus.active:
        vehicle.status = VehicleStatus.in_service
    await session.flush()


async def release(session: AsyncSession, submission: Submission) -> None:
    """«Mashina ketdi» yoki hisobot yopildi — mashina liniyaga qaytadi."""
    vehicle = await vehicle_of(session, submission)
    if vehicle is not None and vehicle.status in (
        VehicleStatus.in_service,
        VehicleStatus.waiting_parts,
    ):
        vehicle.status = VehicleStatus.active
        await session.flush()
