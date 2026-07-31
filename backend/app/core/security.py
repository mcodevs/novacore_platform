"""Telegram initData tekshiruvi va JWT (docs/02-architecture/06-security.md §2)."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import secrets
from urllib.parse import parse_qsl

import jwt

from app.core.config import settings
from app.core.errors import InvalidInitData, Unauthenticated
from app.db.base import utcnow

ALGORITHM = "HS256"


def validate_init_data(init_data: str, *, max_age_sec: int | None = None) -> dict:
    """Telegram rasmiy sxemasi. ❌ `user.id` ni tekshirmasdan ishlatish taqiqlanadi."""
    if not init_data:
        raise InvalidInitData("initData bo'sh")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InvalidInitData("hash yo'q")

    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    # doimiy vaqtli solishtirish (timing attack)
    if not hmac.compare_digest(calculated, received_hash):
        raise InvalidInitData("hash mos emas")

    auth_date = int(pairs.get("auth_date", "0"))
    age = utcnow().timestamp() - auth_date
    if age > (max_age_sec if max_age_sec is not None else settings.init_data_max_age_sec):
        raise InvalidInitData("auth_date eskirgan")  # replay hujumidan himoya

    user_raw = pairs.get("user")
    if not user_raw:
        raise InvalidInitData("user yo'q")
    pairs["user"] = json.loads(user_raw)
    return pairs


def build_init_data(bot_token: str, payload: dict) -> str:
    """Testlar uchun: to'g'ri imzolangan initData yasaydi."""
    from urllib.parse import urlencode

    items = {k: (json.dumps(v, separators=(",", ":")) if isinstance(v, dict) else str(v))
             for k, v in payload.items()}
    data_check_string = "\n".join(f"{k}={items[k]}" for k in sorted(items))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**items, "hash": signature})


def create_access_token(employee_id: int, role_code: str, role_kind: str) -> str:
    now = utcnow()
    payload = {
        "sub": str(employee_id),
        "role_code": role_code,
        "role_kind": role_kind,  # kesh — server baribir har so'rovda tekshiradi
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=settings.access_token_ttl_min)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise Unauthenticated(str(exc)) from exc
    if payload.get("typ") != "access":
        raise Unauthenticated("noto'g'ri token turi")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """(token, hash) — bazada faqat hash saqlanadi."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
