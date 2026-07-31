"""Bitta async engine + sessiya fabrikasi (bitta process — ADR-0004)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

if settings.is_sqlite:
    # Toza klonda `var/` papkasi yo'q — SQLite uni o'zi yaratmaydi
    _path = settings.database_url.split("///", 1)[-1]
    if _path and _path != ":memory:":
        Path(_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

_connect_args: dict = {}
if settings.is_sqlite:
    _connect_args = {"check_same_thread": False}
elif settings.uses_pgbouncer:
    # asyncpg + pgbouncer (transaction pooling): tayyorlangan so'rovlar keshi
    # o'chiriladi. Ikkalasi ham **DBAPI** argumenti — `connect_args` ichida.
    _connect_args = {"statement_cache_size": 0, "prepared_statement_cache_size": 0}

_engine_kwargs: dict = {"echo": settings.db_echo, "connect_args": _connect_args}
if not settings.is_sqlite:
    # Bitta machine, RPS < 1 — kichik pool yetadi
    _engine_kwargs |= {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}
engine = create_async_engine(settings.database_url, **_engine_kwargs)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Tranzaksiya doirasi: xato bo'lsa rollback, aks holda commit."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency."""
    async with session_scope() as session:
        yield session
