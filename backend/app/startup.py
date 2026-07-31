"""Deploydan keyingi qadam: seed'ni yuklash (idempotent).

`alembic upgrade head` sxemani beradi, bu esa rollar/shablonlar/spravochniklarni
yangilaydi. Har deployda xavfsiz ishlaydi.
"""

from __future__ import annotations

import asyncio

import structlog

from app.core.logging import configure_logging
from app.db.session import engine, session_scope
from app.seeds.loader import seed_all

log = structlog.get_logger(__name__)


async def main() -> None:
    configure_logging()
    async with session_scope() as session:
        await seed_all(session)
    await engine.dispose()
    log.info("seed_completed")


if __name__ == "__main__":
    asyncio.run(main())
