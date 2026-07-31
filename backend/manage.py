#!/usr/bin/env python
"""NovaCore boshqaruv CLI.

    python manage.py seed                      # rollar, shablonlar, spravochniklar
    python manage.py employee-add "Karimov B." +998901234567 mechanic
    python manage.py employee-list
    python manage.py vehicle-add 01A123BC BYD Chazor 2024
    python manage.py vehicles-load fleet.csv   # reyestrni CSV'dan (Faza 0.3)
    python manage.py set-webhook               # BASE_URL bo'yicha
    python manage.py delete-webhook
    python manage.py demo                      # lokal sinov ma'lumoti
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings  # noqa: E402
from app.core.phone import display_plate, normalize_phone, normalize_plate  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import Employee, Role, Vehicle  # noqa: E402
from app.db.session import engine, session_scope  # noqa: E402
from app.seeds.loader import seed_all  # noqa: E402


async def cmd_create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Jadvallar yaratildi")


async def cmd_seed() -> None:
    if settings.is_sqlite:
        await cmd_create_tables()
    async with session_scope() as session:
        await seed_all(session)
    print("✅ Seed yuklandi: rollar, shablonlar, ish turlari, qismlar, kategoriyalar")


async def cmd_employee_add(name: str, phone: str, role_code: str) -> None:
    normalized = normalize_phone(phone)
    async with session_scope() as session:
        role = (
            await session.execute(sa.select(Role).where(Role.code == role_code))
        ).scalar_one_or_none()
        if role is None:
            codes = [
                r.code for r in (await session.execute(sa.select(Role))).scalars().all()
            ]
            print(f"❌ Rol topilmadi: {role_code}. Mavjud: {', '.join(codes)}")
            return
        exists = (
            await session.execute(sa.select(Employee).where(Employee.phone == normalized))
        ).scalar_one_or_none()
        if exists is not None:
            print(f"⚠️ Bu raqam allaqachon bor: {exists.full_name}")
            return
        session.add(Employee(full_name=name, phone=normalized, role_id=role.id))
    print(f"✅ Xodim qo'shildi: {name} ({normalized}) — {role_code}")
    print("   Endi u Telegram'da /start bosib telefon raqamini yuborsin.")


async def cmd_employee_list() -> None:
    async with session_scope() as session:
        rows = (
            await session.execute(sa.select(Employee).order_by(Employee.full_name))
        ).scalars().all()
        for employee in rows:
            linked = "🔗" if employee.tg_user_id else "—"
            print(
                f"{employee.id:>3} {linked} {employee.full_name:<24} {employee.phone:<15} "
                f"{employee.role.code:<12} {employee.status.value}"
            )


async def cmd_vehicle_add(plate: str, brand: str, model: str, year: int | None) -> None:
    normalized = normalize_plate(plate)
    async with session_scope() as session:
        exists = (
            await session.execute(sa.select(Vehicle).where(Vehicle.plate_number == normalized))
        ).scalar_one_or_none()
        if exists is not None:
            print(f"⚠️ Allaqachon bor: {normalized}")
            return
        session.add(
            Vehicle(
                plate_number=normalized,
                plate_display=display_plate(normalized),
                brand=brand,
                model=model,
                year=year,
            )
        )
    print(f"✅ Mashina qo'shildi: {display_plate(normalized)} {brand} {model}")


async def cmd_vehicles_load(path: str) -> None:
    """CSV ustunlari: plate_number,brand,model,year,vin,fleet_car_id"""
    added = skipped = 0
    async with session_scope() as session:
        with Path(path).open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                plate = normalize_plate(row.get("plate_number"))
                if not plate:
                    continue
                exists = (
                    await session.execute(
                        sa.select(Vehicle).where(Vehicle.plate_number == plate)
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    skipped += 1
                    continue
                year = row.get("year")
                session.add(
                    Vehicle(
                        plate_number=plate,
                        plate_display=display_plate(plate),
                        brand=row.get("brand", ""),
                        model=row.get("model", ""),
                        year=int(year) if year else None,
                        vin=row.get("vin") or None,
                        fleet_car_id=row.get("fleet_car_id") or None,
                    )
                )
                added += 1
    print(f"✅ Qo'shildi: {added}, o'tkazib yuborildi: {skipped}")


async def cmd_set_webhook() -> None:
    from app.bot.bot import create_bot

    bot = create_bot()
    try:
        await bot.set_webhook(
            settings.webhook_url,
            secret_token=settings.webhook_secret,
            drop_pending_updates=True,
        )
        info = await bot.get_webhook_info()
        print(f"✅ Webhook: {info.url}")
    finally:
        await bot.session.close()


async def cmd_delete_webhook() -> None:
    from app.bot.bot import create_bot

    bot = create_bot()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook o'chirildi (polling rejimi uchun)")
    finally:
        await bot.session.close()


async def cmd_bot_info() -> None:
    from app.bot.bot import create_bot

    bot = create_bot()
    try:
        me = await bot.get_me()
        info = await bot.get_webhook_info()
        print(f"🤖 @{me.username} (id={me.id})")
        print(f"   webhook: {info.url or '— (polling)'} · kutayotgan: {info.pending_update_count}")
    finally:
        await bot.session.close()


async def cmd_demo() -> None:
    """Lokal sinov uchun: 3 ta mashina + namunaviy xodimlar."""
    await cmd_seed()
    demo_vehicles = [
        ("01A123BC", "BYD", "Chazor", 2024),
        ("01B456CD", "BYD", "Song Plus", 2023),
        ("01C789DE", "Chevrolet", "Cobalt", 2022),
    ]
    for plate, brand, model, year in demo_vehicles:
        await cmd_vehicle_add(plate, brand, model, year)
    print("\nEndi xodimlarni qo'shing, masalan:")
    print('  python manage.py employee-add "Karimov B." +998901234567 mechanic')
    print('  python manage.py employee-add "Admin A." +998901234568 admin')


def main() -> None:
    parser = argparse.ArgumentParser(description="NovaCore boshqaruv CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed")
    sub.add_parser("create-tables")
    sub.add_parser("employee-list")
    sub.add_parser("set-webhook")
    sub.add_parser("delete-webhook")
    sub.add_parser("bot-info")
    sub.add_parser("demo")

    p = sub.add_parser("employee-add")
    p.add_argument("name")
    p.add_argument("phone")
    p.add_argument("role", nargs="?", default="mechanic")

    p = sub.add_parser("vehicle-add")
    p.add_argument("plate")
    p.add_argument("brand", nargs="?", default="")
    p.add_argument("model", nargs="?", default="")
    p.add_argument("year", nargs="?", type=int, default=None)

    p = sub.add_parser("vehicles-load")
    p.add_argument("path")

    args = parser.parse_args()
    handlers = {
        "seed": lambda: cmd_seed(),
        "create-tables": lambda: cmd_create_tables(),
        "employee-list": lambda: cmd_employee_list(),
        "employee-add": lambda: cmd_employee_add(args.name, args.phone, args.role),
        "vehicle-add": lambda: cmd_vehicle_add(args.plate, args.brand, args.model, args.year),
        "vehicles-load": lambda: cmd_vehicles_load(args.path),
        "set-webhook": lambda: cmd_set_webhook(),
        "delete-webhook": lambda: cmd_delete_webhook(),
        "bot-info": lambda: cmd_bot_info(),
        "demo": lambda: cmd_demo(),
    }
    asyncio.run(handlers[args.command]())


if __name__ == "__main__":
    main()
