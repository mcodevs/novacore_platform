"""Ilova sozlamalari — hammasi environment orqali (docs/02-architecture/06-security.md §6)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    cors_origins: list[str] = Field(default_factory=list)
    jwt_secret: str = "change-me-at-least-32-bytes-long-secret!"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30
    init_data_max_age_sec: int = 3600

    # --- Media ---
    storage_backend: Literal["local", "s3"] = "local"
    media_root: str = "./var/media"
    s3_endpoint_url: str = "https://fly.storage.tigris.dev"
    s3_bucket: str = "novacore-media"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "auto"
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

    default_lang: Literal["uz", "ru"] = "uz"

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
    def webhook_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
