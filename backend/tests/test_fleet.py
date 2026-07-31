"""Yandex Fleet integratsiyasi (Faza 3) — ⚠️ **faqat o'qish**.

Fleet bu loyihada bitta ish uchun: *raqam bo'yicha mashina va haydovchi
ma'lumotini olish*. Platforma Fleet'ga hech narsa yozmaydi — buni ham
tekshiramiz (`test_client_never_writes_to_fleet`).

Tarmoqqa chiqilmaydi: `httpx.MockTransport` bilan soxta park.
"""

from __future__ import annotations

import httpx
import pytest
import sqlalchemy as sa

from app.core.config import settings
from app.db.models import Vehicle
from app.domain.fleet import service as fleet_service
from app.integrations.fleet import FleetAuthError, FleetClient, FleetError
from tests.conftest import make_vehicle

PARK_ID = "test-park"

CARS = [
    {
        "id": "car-1",
        "number": "01A123BC",
        "brand": "BYD",
        "model": "Chazor",
        "year": 2024,
        "color": "Oq",
        "vin": "VIN0000000000001",
        "status": "working",
    },
    {
        "id": "car-2",
        "number": "01 760 LMA",  # bo'sh joyli ko'rinish — normalizatsiya sinovi
        "brand": "BYD",
        "model": "Song Plus",
        "year": 2023,
        "color": "Qora",
        "status": "repairing",
    },
]

PROFILES = [
    {
        "driver_profile": {
            "id": "drv-1",
            "first_name": "Bekzod",
            "last_name": "Karimov",
            "middle_name": "Aliyevich",
            "phones": ["+998901112233"],
            "work_status": "working",
        },
        "car": {"id": "car-1", "number": "01A123BC"},
    },
    {
        "driver_profile": {
            "id": "drv-2",
            "first_name": "Sobir",
            "last_name": "Toshev",
            "phones": ["901112244"],
            "work_status": "fired",  # bo'shatilgan — biriktirilmaydi
        },
        "car": {"id": "car-2", "number": "01760LMA"},
    },
]


@pytest.fixture(autouse=True)
def fleet_env(monkeypatch):
    """Har testda Fleet yoqilgan bo'lsin (haqiqiy kalitlarsiz)."""
    monkeypatch.setattr(settings, "fleet_enabled", True)
    monkeypatch.setattr(settings, "fleet_api_key", "test-key")
    monkeypatch.setattr(settings, "fleet_park_id", PARK_ID)
    monkeypatch.setattr(settings, "fleet_client_id", "")  # → taxi/park/<id>
    monkeypatch.setattr(settings, "fleet_page_pause_sec", 0.0)
    monkeypatch.setattr(settings, "fleet_page_size", 100)
    monkeypatch.setattr(settings, "fleet_backoff_base_sec", 0.0)  # test kutmasin


class FakeFleet:
    """Soxta park: so'rovlarni yozib boradi, javoblarni sozlash mumkin."""

    def __init__(self, *, cars=None, profiles=None, fail_times: int = 0, status: int = 200):
        self.cars = CARS if cars is None else cars
        self.profiles = PROFILES if profiles is None else profiles
        self.fail_times = fail_times
        self.status = status
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)

        if self.fail_times > 0:
            self.fail_times -= 1
            return httpx.Response(429, json={"message": "rate limit"})
        if self.status != 200:
            return httpx.Response(self.status, json={"message": "xato", "code": "some_code"})

        if request.url.path.endswith("/cars/list"):
            return httpx.Response(
                200, json={"cars": self.cars, "total": len(self.cars), "limit": 100, "offset": 0}
            )
        if request.url.path.endswith("/driver-profiles/list"):
            return httpx.Response(
                200, json={"driver_profiles": self.profiles, "total": len(self.profiles)}
            )
        return httpx.Response(404, json={"message": "topilmadi"})

    def client(self) -> FleetClient:
        return FleetClient(transport=httpx.MockTransport(self.handler))


# --- Klient ------------------------------------------------------------------


async def test_client_sends_auth_headers_and_park_id():
    fake = FakeFleet()
    async with fake.client() as client:
        await client.list_cars()

    request = fake.requests[0]
    assert request.headers["X-Api-Key"] == "test-key"
    assert request.headers["X-Client-ID"] == f"taxi/park/{PARK_ID}"
    import json

    assert json.loads(request.content)["query"]["park"]["id"] == PARK_ID


async def test_client_retries_on_429():
    """Rate-limit real — backoff bilan qayta uriladi (hujjat §7)."""
    fake = FakeFleet(fail_times=2)
    async with fake.client() as client:
        cars = await client.list_cars()

    assert len(cars) == 2
    assert len(fake.requests) == 3  # 2 marta 429, uchinchisi muvaffaqiyatli


async def test_client_raises_auth_error_on_403():
    fake = FakeFleet(status=403)
    async with fake.client() as client:
        with pytest.raises(FleetAuthError):
            await client.list_cars()


async def test_client_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(settings, "fleet_max_retries", 2)
    fake = FakeFleet(fail_times=99)
    async with fake.client() as client:
        with pytest.raises(FleetError):
            await client.list_cars()
    assert len(fake.requests) == 2


async def test_client_never_writes_to_fleet():
    """⚠️ Egasining qarori: Fleet'ga yozish YO'Q — faqat GET/POST-list."""
    fake = FakeFleet()
    async with fake.client() as client:
        await client.list_cars()
        await client.list_driver_profiles()

    assert {r.method for r in fake.requests} == {"POST"}
    assert all("list" in r.url.path for r in fake.requests)
    # yozish uchun metod umuman mavjud emas
    assert not hasattr(client, "set_status")
    assert not hasattr(client, "update_car")


# --- Sinxron -----------------------------------------------------------------


async def test_sync_creates_vehicles_and_links_drivers(session):
    fake = FakeFleet()
    report = await fleet_service.sync(session, client=fake.client())

    assert report.ok
    assert report.created == 2
    assert report.drivers_linked == 1  # `fired` haydovchi biriktirilmaydi

    vehicle = (
        await session.execute(sa.select(Vehicle).where(Vehicle.fleet_car_id == "car-1"))
    ).scalar_one()
    assert vehicle.plate_number == "01A123BC"
    assert vehicle.plate_display == "01 A 123 BC"
    assert vehicle.brand == "BYD" and vehicle.model == "Chazor"
    assert vehicle.fleet_status == "working"
    assert vehicle.current_driver_name == "Karimov Bekzod Aliyevich"
    assert vehicle.current_driver_fleet_id == "drv-1"
    assert vehicle.fleet_synced_at is not None

    # bo'sh joyli raqam normalizatsiya qilinadi
    second = (
        await session.execute(sa.select(Vehicle).where(Vehicle.fleet_car_id == "car-2"))
    ).scalar_one()
    assert second.plate_number == "01760LMA"
    assert second.plate_display == "01 760 LMA"
    assert second.current_driver_name is None  # `fired`


async def test_sync_updates_existing_vehicle_matched_by_plate(session):
    """Qo'lda kiritilgan mashina Fleet bilan bog'lanadi, dublikat yaratilmaydi."""
    manual = await make_vehicle(session, "01A123BC", brand="", model="")
    assert manual.fleet_car_id is None

    report = await fleet_service.sync(session, client=FakeFleet().client())
    assert report.created == 1 and report.updated == 1

    await session.refresh(manual)
    assert manual.fleet_car_id == "car-1"
    assert manual.brand == "BYD"

    total = (
        await session.execute(
            sa.select(sa.func.count(Vehicle.id)).where(Vehicle.plate_number == "01A123BC")
        )
    ).scalar_one()
    assert total == 1


async def test_sync_marks_missing_but_never_deletes(session):
    """Fleet'dan yo'qolgan mashina o'chirilmaydi — ta'mir tarixi qoladi (§5)."""
    await fleet_service.sync(session, client=FakeFleet().client())

    # keyingi sinxronda car-2 yo'q
    report = await fleet_service.sync(session, client=FakeFleet(cars=[CARS[0]]).client())
    assert report.missing == 1

    gone = (
        await session.execute(sa.select(Vehicle).where(Vehicle.fleet_car_id == "car-2"))
    ).scalar_one()
    assert gone.deleted_at is None  # o'chirilmagan
    assert gone.fleet_missing is True


async def test_sync_survives_fleet_outage(session):
    """Fleet javob bermasa — platforma ishlashda davom etadi (§8)."""
    report = await fleet_service.sync(session, client=FakeFleet(status=500).client())

    assert report.ok is False
    assert report.error
    assert report.created == 0


async def test_sync_skips_cars_without_plate(session):
    broken = [{"id": "car-x", "number": "", "brand": "BYD"}, CARS[0]]
    report = await fleet_service.sync(session, client=FakeFleet(cars=broken).client())

    assert report.created == 1
    assert report.skipped == ["car-x"]  # adminga tushunarli bo'lishi uchun ID


async def test_sync_is_disabled_without_keys(session, monkeypatch):
    monkeypatch.setattr(settings, "fleet_enabled", False)
    report = await fleet_service.sync(session)

    assert report.ok is False
    assert "o'chirilgan" in report.error


# --- ⭐ Raqam bo'yicha qidiruv (asosiy foydalanish) ---------------------------


async def test_lookup_returns_local_vehicle_without_touching_fleet(session):
    await make_vehicle(session, "01A123BC")
    fake = FakeFleet()

    found = await fleet_service.lookup_plate(session, "01 A 123 BC", client=fake.client())

    assert found is not None and found.plate_number == "01A123BC"
    assert fake.requests == []  # reyestrda bor — Fleet bezovta qilinmaydi


async def test_lookup_pulls_unknown_plate_from_fleet(session):
    """Reyestrda yo'q raqam — Fleet'dan mashina va haydovchi bilan tortiladi."""
    fake = FakeFleet()
    found = await fleet_service.lookup_plate(session, "01A123BC", client=fake.client())

    assert found is not None
    assert found.brand == "BYD" and found.model == "Chazor"
    assert found.current_driver_name == "Karimov Bekzod Aliyevich"
    assert found.fleet_car_id == "car-1"


async def test_lookup_returns_none_when_fleet_has_no_such_plate(session):
    assert await fleet_service.lookup_plate(session, "99Z999ZZ", client=FakeFleet().client()) is None


async def test_lookup_does_not_break_on_fleet_error(session):
    """Fleet yiqilsa oqim to'xtamaydi — shunchaki topilmadi."""
    found = await fleet_service.lookup_plate(
        session, "01A123BC", client=FakeFleet(status=500).client()
    )
    assert found is None


async def test_lookup_returns_none_when_fleet_disabled(session, monkeypatch):
    monkeypatch.setattr(settings, "fleet_enabled", False)
    assert await fleet_service.lookup_plate(session, "01A123BC") is None


# --- Real parkda topilgan ikkita muammo (2026-08-01) --------------------------


async def test_duplicate_plates_collapse_to_one_vehicle(session):
    """292 Fleet yozuvi ↔ 164 raqam: platformada raqam unikal, tanlov kerak."""
    cars = [
        {"id": "car-b", "number": "01A123BC", "brand": "BYD", "model": "Eski", "status": "working"},
        {"id": "car-a", "number": "01A123BC", "brand": "BYD", "model": "Yangi", "status": "working"},
    ]
    report = await fleet_service.sync(session, client=FakeFleet(cars=cars).client())

    assert report.created == 1
    assert report.duplicate_plates == 1
    assert "bir nechta Fleet yozuvi" in report.summary()

    rows = (
        await session.execute(sa.select(Vehicle).where(Vehicle.plate_number == "01A123BC"))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].fleet_car_id == "car-a"  # `id` bo'yicha eng kichigi


async def test_duplicate_choice_is_stable_across_syncs(session):
    """Tanlov deterministik — `fleet_car_id` har sinxronda sakramasin."""
    cars = [
        {"id": "car-b", "number": "01A123BC", "brand": "BYD", "status": "working"},
        {"id": "car-a", "number": "01A123BC", "brand": "BYD", "status": "working"},
    ]
    await fleet_service.sync(session, client=FakeFleet(cars=cars).client())
    # ikkinchi sinxronda tartib teskari kelsa ham
    await fleet_service.sync(session, client=FakeFleet(cars=list(reversed(cars))).client())

    vehicle = (
        await session.execute(sa.select(Vehicle).where(Vehicle.plate_number == "01A123BC"))
    ).scalar_one()
    assert vehicle.fleet_car_id == "car-a"


async def test_ambiguous_driver_is_not_written(session):
    """⚠️ Bitta mashinaga bir nechta faol profil → haydovchi YOZILMAYDI.

    Real parkda bitta mashinada 71 ta har xil `working` haydovchi uchradi —
    noto'g'ri ism usta hisobotida qolib ketishidan ko'ra bo'sh qolgani yaxshi.
    """
    profiles = [
        {
            "driver_profile": {"id": f"drv-{i}", "first_name": f"Haydovchi{i}",
                               "last_name": "Testov", "work_status": "working"},
            "car": {"id": "car-1"},
        }
        for i in range(3)
    ]
    report = await fleet_service.sync(
        session, client=FakeFleet(cars=[CARS[0]], profiles=profiles).client()
    )

    assert report.drivers_linked == 0
    assert report.drivers_ambiguous == 1
    assert "haydovchi aniq emas" in report.summary()

    vehicle = (
        await session.execute(sa.select(Vehicle).where(Vehicle.fleet_car_id == "car-1"))
    ).scalar_one()
    assert vehicle.current_driver_name is None


async def test_single_driver_is_written(session):
    """Bir ma'noli bo'lsa — yoziladi (asosiy foydali holat)."""
    report = await fleet_service.sync(
        session, client=FakeFleet(cars=[CARS[0]], profiles=[PROFILES[0]]).client()
    )
    assert report.drivers_linked == 1 and report.drivers_ambiguous == 0

    vehicle = (
        await session.execute(sa.select(Vehicle).where(Vehicle.fleet_car_id == "car-1"))
    ).scalar_one()
    assert vehicle.current_driver_name == "Karimov Bekzod Aliyevich"
