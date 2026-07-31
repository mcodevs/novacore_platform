"""`.env.example` yuklanadigan bo'lishi kerak.

Toza klondan `make bootstrap` shu fayldan `.env` yasaydi — agar u
o'qilmasa, ilova umuman ko'tarilmaydi. Ikki marta shunday bo'lgani uchun
(bo'sh `CORS_ORIGINS`, satr oxiridagi izoh) test qo'shildi.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"


def test_env_example_exists():
    assert ENV_EXAMPLE.is_file()


def test_env_example_loads_without_errors():
    """Namunadagi qiymatlar bilan Settings muammosiz quriladi."""
    settings = Settings(_env_file=ENV_EXAMPLE)
    assert settings.env == "local"
    assert settings.bot_mode == "polling"
    assert settings.database_url.startswith("sqlite+aiosqlite://")
    assert settings.cors_origins == []
    assert settings.admin_group_id is None
    assert settings.storage_backend == "local"
    assert settings.antifraud_enabled is False


def test_env_example_has_no_inline_comments_after_values():
    """`KEY=  # izoh` — izoh qiymatga qo'shilib ketadi (dotenv xususiyati)."""
    bad: list[str] = []
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        _, _, value = stripped.partition("=")
        if "#" in value:
            bad.append(stripped)
    assert not bad, f"satr oxirida izoh bor: {bad}"


@pytest.mark.parametrize("required", ["BOT_TOKEN", "DATABASE_URL", "JWT_SECRET"])
def test_env_example_documents_required_keys(required):
    assert f"{required}=" in ENV_EXAMPLE.read_text(encoding="utf-8")


def test_cors_origins_accepts_comma_separated_string(tmp_path):
    """`.env` orqali — aynan shu yo'lda JSON deb o'qilib xato bergan edi."""
    env_file = tmp_path / ".env"
    env_file.write_text("CORS_ORIGINS=https://a.uz, https://b.uz\n", encoding="utf-8")
    assert Settings(_env_file=env_file).cors_origins == ["https://a.uz", "https://b.uz"]


def test_empty_optional_values_are_treated_as_unset(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ADMIN_GROUP_ID=\nCORS_ORIGINS=\nTELEGRAM_PROXY=\n", encoding="utf-8")
    settings = Settings(_env_file=env_file)
    assert settings.admin_group_id is None
    assert settings.telegram_proxy is None
    assert settings.cors_origins == []
