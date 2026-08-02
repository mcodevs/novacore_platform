"""Ilova sozlamalari — hammasi environment orqali (docs/02-architecture/06-security.md §6)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

TASHKENT = ZoneInfo("Asia/Tashkent")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Umumiy ---
    env: Literal["local", "production"] = "local"
    debug: bool = False
    app_name: str = "NovaCore Platform"
    base_url: str = "http://localhost:8000"

    # --- Ma'lumotlar bazasi ---
    # production: postgresql+asyncpg://...   lokal: sqlite+aiosqlite:///./var/novacore.db
    # `fly mpg attach` oddiy `postgresql://` beradi — quyida drayver qo'shiladi.
    database_url: str = "sqlite+aiosqlite:///./var/novacore.db"
    db_echo: bool = False

    # --- Telegram ---
    bot_token: str = ""
    bot_mode: Literal["webhook", "polling"] = "polling"
    # Ixtiyoriy: cheklangan tarmoqdan chiqish uchun (aiohttp-socks talab qiladi)
    telegram_proxy: str | None = None
    webhook_path: str = "/tg/webhook"
    webhook_secret: str = "change-me-webhook-secret"
    admin_group_id: int | None = None  # kritik signal yuboriladigan guruh

    # --- Mini App / API ---
    miniapp_url: str = ""
    # Bundle versiyasi (build hash) — Mini App havolasiga `?v=` bo'lib qo'shiladi.
    # Telegram WebView index.html'ni keshlab, eski bundle'ni ushlab qolmasligi
    # uchun har deployda o'zgaradi (startup'da index.html'dan hisoblanadi).
    miniapp_version: str = ""
    # NoDecode: `.env` dagi bo'sh yoki vergulli qiymat JSON deb o'qilmasin
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    jwt_secret: str = "change-me-at-least-32-bytes-long-secret!"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30
    init_data_max_age_sec: int = 3600

    # --- Media ---
    storage_backend: Literal["local", "s3"] = "local"
    media_root: str = "./var/media"
    # `fly storage create` sirlarni AWS_* nomlari bilan qo'yadi — ikkalasi ham ishlaydi
    s3_endpoint_url: str = Field(
        default="https://fly.storage.tigris.dev",
        validation_alias=AliasChoices("S3_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"),
    )
    s3_bucket: str = Field(
        default="novacore-media",
        validation_alias=AliasChoices("S3_BUCKET", "BUCKET_NAME"),
    )
    s3_access_key: str = Field(
        default="", validation_alias=AliasChoices("S3_ACCESS_KEY", "AWS_ACCESS_KEY_ID")
    )
    s3_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("S3_SECRET_KEY", "AWS_SECRET_ACCESS_KEY"),
    )
    s3_region: str = Field(
        default="auto", validation_alias=AliasChoices("S3_REGION", "AWS_REGION")
    )
    signed_url_ttl_sec: int = 900  # 15 daqiqa
    max_photo_mb: int = 10

    # --- Biznes qoidalari ---
    price_auto_accept_hours: int = 48  # N4: 48 soat javob bo'lmasa — avtomatik rozilik
    price_reminder_hours: int = 24  # 24 soatda eslatma
    draft_reminder_hours: int = 24
    draft_alert_days: int = 7
    long_service_alert_hours: int = 24  # mashina ustaxonada 24 soatdan ortiq
    background_tick_sec: int = 60

    # Faza 1'da bayroqlar o'chirilgan (docs/04-flows/02-antifraud.md §9 — v1)
    antifraud_enabled: bool = False

    # --- Yandex Fleet (Faza 3) ---
    # Kalitlar `driver_status_reporter` loyihasidagi bilan bir xil park uchun.
    # O'chirilgan bo'lsa platforma Fleet'siz to'liq ishlaydi.
    fleet_enabled: bool = False
    fleet_base_url: str = "https://fleet-api.taxi.yandex.net"
    fleet_api_key: str = ""
    fleet_park_id: str = ""
    fleet_client_id: str = ""  # bo'sh bo'lsa — `taxi/park/<park_id>`
    fleet_page_size: int = 1000  # API maksimumi
    fleet_page_pause_sec: float = 1.5  # sahifalar orasida — 429 dan qochish
    fleet_timeout_sec: float = 6.0  # «Mashina keldi» tugmasi kutib qolmasin
    fleet_max_retries: int = 5  # 429/5xx uchun eksponensial backoff
    fleet_backoff_base_sec: float = 2.0  # 2 → 4 → 8 … (maks 30); testlarda 0
    fleet_sync_hour: int = 4  # kunlik reyestr sinxroni (Asia/Tashkent)

    default_lang: Literal["uz", "ru"] = "uz"

    @field_validator("admin_group_id", "telegram_proxy", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        """`.env` da `KEY=` (bo'sh) — bu «berilmagan» degani, xato emas."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("database_url", mode="after")
    @classmethod
    def _ensure_async_driver(cls, value: str) -> str:
        """`postgresql://` → `postgresql+asyncpg://` (Fly shu ko'rinishda beradi)."""
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://") :]
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def uses_pgbouncer(self) -> bool:
        """pgbouncer (transaction pooling) tayyorlangan so'rovlar bilan ishlamaydi."""
        return "pgbouncer" in self.database_url

    @property
    def webhook_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.webhook_path}"

    @property
    def fleet_client_header(self) -> str:
        """`X-Client-ID` — odatda `taxi/park/<park_id>`."""
        return self.fleet_client_id or f"taxi/park/{self.fleet_park_id}"

    @property
    def fleet_ready(self) -> bool:
        return bool(self.fleet_enabled and self.fleet_api_key and self.fleet_park_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
