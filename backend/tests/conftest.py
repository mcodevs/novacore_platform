"""Test infratuzilmasi.

Domen testlari SQLite'da ishlaydi (tez, tashqi bog'liqliksiz). Ishlab
chiqarishda baza — PostgreSQL; modellar `with_variant` orqali ikkalasiga mos.
"""

from __future__ import annotations

import os
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

TMP = Path(tempfile.mkdtemp(prefix="novacore-tests-"))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TMP / 'test.db'}")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("MEDIA_ROOT", str(TMP / "media"))
os.environ.setdefault("BOT_TOKEN", "123456:TEST")
os.environ.setdefault("JWT_SECRET", "test-secret-key-at-least-32-bytes-long!!")
os.environ.setdefault("ANTIFRAUD_ENABLED", "false")
# Testlar germetik: ishlab chiquvchining `.env` dagi haqiqiy Fleet kalitlari
# test paytida ishlatilmasin (env o'zgaruvchisi `.env` dan ustun turadi).
os.environ.setdefault("FLEET_ENABLED", "false")
os.environ.setdefault("FLEET_API_KEY", "")
os.environ.setdefault("FLEET_PARK_ID", "")
os.environ.setdefault("FLEET_CLIENT_ID", "")

import sqlalchemy as sa  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.models import (  # noqa: E402
    Employee,
    EmployeeStatus,
    LineKind,
    Media,
    MediaKind,
    Role,
    Submission,
    Template,
    Vehicle,
)
from app.domain.submission import service as submission_service  # noqa: E402
from app.domain.template import engine  # noqa: E402
from app.seeds.loader import seed_all  # noqa: E402


@pytest.fixture
async def session(tmp_path) -> AsyncSession:  # noqa: ANN001
    engine_ = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine_, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db:
        await seed_all(db)
        await db.commit()
        yield db
    await engine_.dispose()


async def get_role(session: AsyncSession, code: str) -> Role:
    return (
        await session.execute(sa.select(Role).where(Role.code == code))
    ).scalar_one()


async def get_template(session: AsyncSession, code: str) -> Template:
    return (
        await session.execute(sa.select(Template).where(Template.code == code))
    ).scalar_one()


async def make_employee(
    session: AsyncSession,
    *,
    role_code: str = "mechanic",
    name: str = "Karimov B.",
    phone: str | None = None,
    tg_user_id: int | None = None,
    status: EmployeeStatus = EmployeeStatus.active,
) -> Employee:
    role = await get_role(session, role_code)
    counter = (
        await session.execute(sa.select(sa.func.count(Employee.id)))
    ).scalar_one()
    employee = Employee(
        full_name=name,
        phone=phone or f"+9989000000{counter:02d}",
        role_id=role.id,
        tg_user_id=tg_user_id if tg_user_id is not None else 100000 + counter,
        status=status,
        lang="uz",
    )
    session.add(employee)
    await session.flush()
    await session.refresh(employee)
    return employee


async def make_vehicle(
    session: AsyncSession, plate: str = "01A123BC", **kwargs
) -> Vehicle:
    vehicle = Vehicle(
        plate_number=plate,
        plate_display=kwargs.pop("plate_display", plate),
        brand=kwargs.pop("brand", "BYD"),
        model=kwargs.pop("model", "Chazor"),
        year=kwargs.pop("year", 2024),
        **kwargs,
    )
    session.add(vehicle)
    await session.flush()
    return vehicle


async def add_photo(
    session: AsyncSession,
    submission: Submission,
    employee: Employee,
    field_code: str,
    *,
    payload: bytes | None = None,
) -> Media:
    """Testlarda foto — omborga yozmasdan, faqat metadata."""
    import hashlib

    data = payload or f"{submission.id}:{field_code}:{len(submission.media)}".encode()
    media = Media(
        submission_id=submission.id,
        field_code=field_code,
        kind=MediaKind.other,
        storage_key=f"test/{submission.id}/{field_code}-{len(submission.media)}",
        mime="image/jpeg",
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=employee.id,
    )
    session.add(media)
    await session.flush()
    await session.refresh(submission)
    engine.append_media_id(submission, field_code, media.id)
    engine.mark_done(submission, field_code)
    await session.flush()
    return media


async def fill_valid_repair(
    session: AsyncSession,
    submission: Submission,
    author: Employee,
    vehicle: Vehicle,
    *,
    works: list[tuple[str, Decimal]] | None = None,
    odometer: int = 48250,
) -> Submission:
    """Ta'mir shablonining barcha majburiy maydonlarini to'ldiradi."""
    engine.set_value(
        submission, "plate", {"vehicle_id": vehicle.id, "plate": vehicle.plate_number}
    )
    await submission_service.attach_vehicle(session, submission, vehicle)

    for field_code in (
        "photo_car_before",
        "odometer_photo",
        "photo_problem",
        "photo_after",
        "photo_car_after",
    ):
        await add_photo(session, submission, author, field_code)

    engine.set_value(submission, "odometer_value", odometer)
    engine.set_value(submission, "category", "brakes")
    engine.set_value(submission, "problem_description", "Old tormoz kolodkasi yeyilgan")
    engine.set_value(submission, "comment", "Kolodka almashtirildi, disk normal")
    engine.mark_done(submission, "parts")

    for name, price in works or [("Old tormoz kolodkasini almashtirish", Decimal("250000"))]:
        await submission_service.add_line(
            session,
            submission,
            author,
            kind=LineKind.labor,
            name=name,
            qty=1,
            unit_price=price,
        )
    engine.mark_done(submission, "works")
    await session.flush()
    await session.refresh(submission)
    return submission


async def create_ready_submission(
    session: AsyncSession,
    author: Employee,
    vehicle: Vehicle,
    *,
    works: list[tuple[str, Decimal]] | None = None,
    mark_left: bool = True,
) -> Submission:
    template = await get_template(session, "car_repair")
    submission = await submission_service.create_draft(session, author, template)
    await fill_valid_repair(session, submission, author, vehicle, works=works)
    if mark_left:
        await submission_service.mark_left(session, submission, author)
    await session.refresh(submission)
    return submission
