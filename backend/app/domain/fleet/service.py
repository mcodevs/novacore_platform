"""Fleet → platforma sinxroni (Faza 3) — ⚠️ **bir tomonlama, faqat o'qish**.

Maqsad bitta: *mashina raqami bo'yicha mashina va haydovchi ma'lumotini olish*,
ya'ni usta raqamni kiritganda marka/model/yil va joriy haydovchi o'zi to'lsin.

Platforma Fleet'ga **hech narsa yozmaydi** (egasining qarori, 2026-08-01) —
`repairing` statusini yozish ham yo'q.

Egalik (hujjat §4): davlat raqami, VIN, marka, model, haydovchi FIO/telefon —
**Fleet'niki**, platformada tahrirlanmaydi. Ta'mir tarixi, narx, rollar —
platformaniki.

⚠️ Fleet'dan yo'qolgan mashina **o'chirilmaydi** — `fleet_missing` belgilanadi,
ta'mir tarixi joyida qoladi (§5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.phone import display_plate, normalize_phone, normalize_plate
from app.db.base import utcnow
from app.db.models import Vehicle
from app.domain import audit
from app.integrations.fleet import FleetClient, FleetError, FleetNotConfigured

log = structlog.get_logger(__name__)


@dataclass
class SyncReport:
    """«3 ta yangi, 1 ta yo'qolgan, 12 ta yangilandi» (hujjat §5)."""

    created: int = 0
    updated: int = 0
    missing: int = 0
    drivers_linked: int = 0
    #: Bitta raqamga bir nechta Fleet yozuvi (parkdagi dublikatlar)
    duplicate_plates: int = 0
    #: Bitta mashinaga bir nechta `working` haydovchi — kimligi aniq emas
    drivers_ambiguous: int = 0
    skipped: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def summary(self) -> str:
        if self.error:
            return f"❌ Fleet sinxroni: {self.error}"
        text = (
            f"🔄 Fleet: +{self.created} yangi · {self.updated} yangilandi · "
            f"{self.drivers_linked} haydovchi · {self.missing} yo'qolgan"
        )
        if self.duplicate_plates:
            text += f"\n⚠️ {self.duplicate_plates} raqamda bir nechta Fleet yozuvi bor"
        if self.drivers_ambiguous:
            text += (
                f"\n⚠️ {self.drivers_ambiguous} mashinada joriy haydovchi aniq emas "
                "(bir nechta faol profil) — yozilmadi"
            )
        return text


def _full_name(profile: dict) -> str:
    parts = [
        (profile.get("last_name") or "").strip(),
        (profile.get("first_name") or "").strip(),
        (profile.get("middle_name") or "").strip(),
    ]
    return " ".join(p for p in parts if p)


def _first_phone(profile: dict) -> str | None:
    for phone in profile.get("phones") or []:
        normalized = normalize_phone(str(phone))
        if normalized:
            return normalized
    return None


async def _dedupe_by_plate(
    session: AsyncSession, cars: list[dict], report: SyncReport
) -> list[dict]:
    """Bitta raqamga bir nechta Fleet yozuvi bo'lsa — bittasini tanlaydi.

    ⚠️ Real parkda tekshirilgan (2026-08-01): 292 Fleet yozuvi, atigi 164
    unikal raqam; 66 raqamda 2–5 tadan yozuv bor va **hammasi `working`** —
    ya'ni status ajratmaydi. Platformada esa raqam unikal (bitta jismoniy
    mashina = bitta yozuv), shuning uchun tanlash kerak.

    Tanlov **deterministik** bo'lishi shart, aks holda har sinxronda
    `fleet_car_id` sakrab yuradi:

    1. Allaqachon platformaga bog'langan yozuv ustunlikka ega
    2. Aks holda `id` bo'yicha eng kichigi

    Dublikatlar hisoboti adminga chiqadi — tozalash Fleet tomonida qilinadi.
    """
    by_plate: dict[str, list[dict]] = {}
    for car in cars:
        plate = normalize_plate(car.get("number"))
        if not plate:
            report.skipped.append(str(car.get("id") or car.get("number") or "?"))
            continue
        by_plate.setdefault(plate, []).append(car)

    chosen: list[dict] = []
    for plate, group in by_plate.items():
        if len(group) == 1:
            chosen.append(group[0])
            continue

        report.duplicate_plates += 1
        linked = (
            await session.execute(
                sa.select(Vehicle.fleet_car_id).where(
                    Vehicle.plate_number == plate, Vehicle.fleet_car_id.is_not(None)
                )
            )
        ).scalar_one_or_none()

        preferred = next((c for c in group if c.get("id") == linked), None)
        chosen.append(preferred or min(group, key=lambda c: str(c.get("id") or "")))
    return chosen


async def _apply_car(session: AsyncSession, car: dict, report: SyncReport) -> Vehicle | None:
    """Bitta mashinani upsert qiladi. Xato bo'lsa qolganlari saqlanadi (§8)."""
    fleet_id = car.get("id")
    plate = normalize_plate(car.get("number"))
    if not fleet_id or not plate:
        # `_dedupe_by_plate` bunilarni allaqachon ajratgan; qidiruv yo'lida esa
        # bitta mashina keladi — shuning uchun bu yerda faqat himoya
        report.skipped.append(str(fleet_id or car.get("number") or "?"))
        return None

    vehicle = (
        await session.execute(sa.select(Vehicle).where(Vehicle.fleet_car_id == fleet_id))
    ).scalar_one_or_none()
    if vehicle is None:
        # raqam bo'yicha ham qaraymiz — mashina qo'lda kiritilgan bo'lishi mumkin
        vehicle = (
            await session.execute(sa.select(Vehicle).where(Vehicle.plate_number == plate))
        ).scalar_one_or_none()

    is_new = vehicle is None
    if vehicle is None:
        vehicle = Vehicle(plate_number=plate, plate_display=display_plate(plate))
        session.add(vehicle)

    # Fleet egalik qiladigan maydonlar — har sinxronda ustidan yoziladi
    vehicle.fleet_car_id = fleet_id
    vehicle.plate_number = plate
    vehicle.plate_display = display_plate(plate)
    vehicle.brand = car.get("brand") or vehicle.brand
    vehicle.model = car.get("model") or vehicle.model
    vehicle.year = car.get("year") or vehicle.year
    vehicle.color = car.get("color") or vehicle.color
    vehicle.vin = car.get("vin") or vehicle.vin
    vehicle.fleet_status = car.get("status")
    vehicle.fleet_synced_at = utcnow()
    vehicle.fleet_missing = False

    await session.flush()
    if is_new:
        report.created += 1
    else:
        report.updated += 1
    return vehicle


async def _link_drivers(
    session: AsyncSession, profiles: list[dict], report: SyncReport
) -> None:
    """Haydovchi ↔ mashina — **faqat bir ma'noli bo'lsa**.

    ⚠️ Real parkda tekshirilgan (2026-08-01): `driver-profiles/list` dagi `car`
    maydoni *joriy* bog'lanish emas, **tarixiy** — bitta mashinaga 71 tagacha
    har xil `working` profil (71 unikal telefon, 71 unikal FIO) uchradi.
    188 mashinadan atigi 53 tasi bir ma'noli edi.

    Partner API'da «hozir kim minadi» degan ishonchli signal yo'q
    (`car-bindings` da GET yo'q, `cars/list` da haydovchi maydoni yo'q).
    Shuning uchun **noaniq bo'lsa yozmaymiz**: noto'g'ri ism ko'rsatgandan
    ko'ra bo'sh qolgani yaxshi — usta hisobotida noto'g'ri haydovchi qolib
    ketmasin.
    """
    by_car: dict[str, list[dict]] = {}
    for item in profiles:
        profile = item.get("driver_profile") or {}
        fleet_car_id = (item.get("car") or {}).get("id")
        if not fleet_car_id:
            continue
        if (profile.get("work_status") or "working") != "working":
            continue  # bo'shatilgan haydovchi biriktirilmaydi
        by_car.setdefault(fleet_car_id, []).append(profile)

    for fleet_car_id, candidates in by_car.items():
        vehicle = (
            await session.execute(
                sa.select(Vehicle).where(Vehicle.fleet_car_id == fleet_car_id)
            )
        ).scalar_one_or_none()
        if vehicle is None:
            continue

        if len(candidates) > 1:
            report.drivers_ambiguous += 1
            continue

        profile = candidates[0]
        vehicle.current_driver_name = _full_name(profile) or vehicle.current_driver_name
        vehicle.current_driver_fleet_id = profile.get("id")
        report.drivers_linked += 1
    await session.flush()


async def _mark_missing(
    session: AsyncSession, seen_fleet_ids: set[str], report: SyncReport
) -> None:
    """Fleet'da yo'q, platformada bor → belgilaymiz, **o'chirmaymiz**."""
    stmt = sa.select(Vehicle).where(
        Vehicle.deleted_at.is_(None), Vehicle.fleet_car_id.is_not(None)
    )
    for vehicle in (await session.execute(stmt)).scalars().all():
        missing = vehicle.fleet_car_id not in seen_fleet_ids
        if missing != vehicle.fleet_missing:
            vehicle.fleet_missing = missing
        if missing:
            report.missing += 1
    await session.flush()


async def sync(
    session: AsyncSession, *, actor_id: int | None = None, client: FleetClient | None = None
) -> SyncReport:
    """Kuniga 1× + qo'lda. Xato bo'lsa platforma ishlashda davom etadi (§8)."""
    report = SyncReport()
    owned = client is None

    try:
        client = client or FleetClient()
    except FleetNotConfigured as exc:
        report.error = str(exc)
        return report

    try:
        cars = await _dedupe_by_plate(session, await client.list_cars(), report)
        seen: set[str] = set()
        for car in cars:
            vehicle = await _apply_car(session, car, report)
            if vehicle is not None and vehicle.fleet_car_id:
                seen.add(vehicle.fleet_car_id)

        profiles = await client.list_driver_profiles()
        await _link_drivers(session, profiles, report)
        await _mark_missing(session, seen, report)
    except FleetError as exc:
        report.error = str(exc)
        log.warning("fleet_sync_failed", error=str(exc))
    finally:
        if owned:
            await client.aclose()

    await audit.log(
        session,
        action="fleet.sync",
        entity_type="vehicle",
        actor_id=actor_id,
        after={
            "created": report.created,
            "updated": report.updated,
            "missing": report.missing,
            "drivers_linked": report.drivers_linked,
            "skipped": len(report.skipped),
            "error": report.error,
        },
    )
    return report


async def lookup_plate(
    session: AsyncSession, plate: str, *, client: FleetClient | None = None
) -> Vehicle | None:
    """⭐ Raqam bo'yicha mashina — avval lokal reyestr, topilmasa Fleet'dan.

    Usta raqamni kiritadi → marka/model/yil va joriy haydovchi o'zi to'ladi.
    Fleet javob bermasa lokal natija qaytadi (yoki `None`) — oqim to'xtamaydi.
    """
    normalized = normalize_plate(plate)
    if not normalized:
        return None
    vehicle = (
        await session.execute(
            sa.select(Vehicle).where(
                Vehicle.plate_number == normalized, Vehicle.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if vehicle is not None:
        return vehicle

    # reyestrda yo'q — Fleet'da yangi mashina paydo bo'lgan bo'lishi mumkin
    owned = client is None
    try:
        client = client or FleetClient()
    except FleetNotConfigured:
        return None

    report = SyncReport()
    try:
        cars = [c for c in await client.list_cars()
                if normalize_plate(c.get("number")) == normalized]
        if not cars:
            return None
        # bir nechta yozuv bo'lsa — sinxrondagi bilan bir xil deterministik tanlov
        for car in await _dedupe_by_plate(session, cars, report):
            found = await _apply_car(session, car, report)
            if found is not None:
                await _link_drivers(session, await client.list_driver_profiles(), report)
            return found
    except FleetError as exc:
        log.warning("fleet_lookup_failed", plate=normalized, error=str(exc))
    finally:
        if owned:
            await client.aclose()
    return None
