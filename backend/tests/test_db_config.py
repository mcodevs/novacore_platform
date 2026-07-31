"""Engine sozlamalari — Postgres/pgbouncer yo'li lokal testlarda ham tekshiriladi.

`create_async_engine` ulanmaydi, faqat argumentlarni tekshiradi — shuning uchun
bu testlar haqiqiy Postgres'siz ham noto'g'ri argumentni ushlaydi
(deployda `prepared_statement_cache_size` `create_engine()` ga berilib xato
bergani uchun qo'shildi).
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings

PG_URL = "postgresql://fly-user:secret@pgbouncer.abc123.flympg.net/fly-db"
DIRECT_URL = "postgresql://fly-user:secret@direct.abc123.flympg.net/fly-db"


def build_engine(settings: Settings):  # noqa: ANN201
    """`app/db/session.py` dagi mantiqning aynan o'zi."""
    connect_args: dict = {}
    if settings.is_sqlite:
        connect_args = {"check_same_thread": False}
    elif settings.uses_pgbouncer:
        connect_args = {"statement_cache_size": 0, "prepared_statement_cache_size": 0}

    kwargs: dict = {"echo": settings.db_echo, "connect_args": connect_args}
    if not settings.is_sqlite:
        kwargs |= {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}
    return create_async_engine(settings.database_url, **kwargs)


def test_fly_url_gets_async_driver():
    """`fly mpg attach` oddiy `postgresql://` beradi — drayver qo'shilishi shart."""
    settings = Settings(database_url=PG_URL)
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.is_sqlite is False


def test_postgres_scheme_variants():
    assert Settings(database_url="postgres://u:p@h/db").database_url.startswith(
        "postgresql+asyncpg://"
    )
    # allaqachon to'g'ri bo'lsa — o'zgarmaydi
    url = "postgresql+asyncpg://u:p@h/db"
    assert Settings(database_url=url).database_url == url


def test_pgbouncer_engine_is_constructible():
    """Regressiya: DBAPI argumenti `create_engine()` ga berilmasligi kerak."""
    settings = Settings(database_url=PG_URL)
    assert settings.uses_pgbouncer is True
    engine = build_engine(settings)  # noto'g'ri argument bo'lsa TypeError beradi
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "asyncpg"


def test_direct_postgres_engine_is_constructible():
    settings = Settings(database_url=DIRECT_URL)
    assert settings.uses_pgbouncer is False
    engine = build_engine(settings)
    assert engine.dialect.driver == "asyncpg"


def test_sqlite_engine_is_constructible(tmp_path):
    settings = Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'x.db'}")
    engine = build_engine(settings)
    assert engine.dialect.name == "sqlite"


@pytest.mark.parametrize(
    ("env_name", "field", "value"),
    [
        ("AWS_ACCESS_KEY_ID", "s3_access_key", "tid_test"),
        ("AWS_SECRET_ACCESS_KEY", "s3_secret_key", "tsec_test"),
        ("BUCKET_NAME", "s3_bucket", "novacore-media"),
        ("AWS_ENDPOINT_URL_S3", "s3_endpoint_url", "https://fly.storage.tigris.dev"),
        ("AWS_REGION", "s3_region", "auto"),
    ],
)
def test_fly_tigris_secret_names_are_accepted(env_name, field, value):
    """`fly storage create` sirlarni AWS_* nomlari bilan qo'yadi."""
    settings = Settings(**{env_name: value})
    assert getattr(settings, field) == value
