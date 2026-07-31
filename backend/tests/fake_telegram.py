"""Soxta Telegram sessiyasi — bot handlerlarini tarmoqsiz sinash uchun."""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncGenerator
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.types import File, Message, User

FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"0" * 512


class FakeSession(BaseSession):
    """Barcha chiquvchi so'rovlarni yozib boradi, tarmoqqa chiqmaydi."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[tuple[str, TelegramMethod]] = []
        self._message_id = 1000

    # --- BaseSession API ---

    async def close(self) -> None:  # pragma: no cover
        return None

    async def make_request(  # type: ignore[override]
        self, bot: Bot, method: TelegramMethod, timeout: int | None = None
    ) -> Any:
        name = method.__api_method__
        self.requests.append((name, method))

        if name == "getMe":
            return User(id=1, is_bot=True, first_name="NovaCore", username="novacore_bot")
        if name == "getFile":
            return File(
                file_id=getattr(method, "file_id", "f"),
                file_unique_id="u",
                file_size=len(FAKE_JPEG),
                file_path="photos/file_1.jpg",
            )
        if name in ("sendMessage", "sendDocument", "sendPhoto"):
            return self._fake_message(method)
        if name == "sendMediaGroup":
            return [self._fake_message(method)]
        return True

    async def stream_content(  # type: ignore[override]
        self,
        url: str,
        headers: dict | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        yield FAKE_JPEG

    # --- Yordamchilar ---

    def _fake_message(self, method: TelegramMethod) -> Message:
        self._message_id += 1
        chat_id = int(getattr(method, "chat_id", 1) or 1)
        return Message.model_validate(
            {
                "message_id": self._message_id,
                "date": dt.datetime.now(dt.timezone.utc),
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": 1, "is_bot": True, "first_name": "NovaCore"},
                "text": getattr(method, "text", None) or getattr(method, "caption", "") or "",
            }
        )

    # --- Testlarda tekshirish uchun ---

    def sent_texts(self, chat_id: int | None = None) -> list[str]:
        result = []
        for name, method in self.requests:
            if name != "sendMessage":
                continue
            if chat_id is not None and int(getattr(method, "chat_id", 0)) != chat_id:
                continue
            result.append(getattr(method, "text", ""))
        return result

    def last_text(self, chat_id: int | None = None) -> str:
        texts = self.sent_texts(chat_id)
        return texts[-1] if texts else ""

    def last_markup(self, chat_id: int | None = None):  # noqa: ANN201
        for name, method in reversed(self.requests):
            if name != "sendMessage":
                continue
            if chat_id is not None and int(getattr(method, "chat_id", 0)) != chat_id:
                continue
            return getattr(method, "reply_markup", None)
        return None

    def callback_data(self, needle: str, chat_id: int | None = None) -> str | None:
        """Oxirgi klaviaturadan `needle` bo'lgan callback_data'ni topadi."""
        for name, method in reversed(self.requests):
            if name != "sendMessage":
                continue
            if chat_id is not None and int(getattr(method, "chat_id", 0)) != chat_id:
                continue
            markup = getattr(method, "reply_markup", None)
            if markup is None or not getattr(markup, "inline_keyboard", None):
                continue
            for row in markup.inline_keyboard:
                for button in row:
                    if button.callback_data and needle in button.callback_data:
                        return button.callback_data
        return None

    def documents(self) -> list[str]:
        return [
            getattr(method, "document").filename
            for name, method in self.requests
            if name == "sendDocument"
        ]

    def clear(self) -> None:
        self.requests.clear()


def make_bot() -> Bot:
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    return Bot(
        token="123456:AAFakeTokenForTestsOnly_0000000000000",
        session=FakeSession(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


# --- Update quruvchilar -------------------------------------------------------

_update_id = 0


def _next_update_id() -> int:
    global _update_id
    _update_id += 1
    return _update_id


def _user(user_id: int) -> dict:
    return {
        "id": user_id,
        "is_bot": False,
        "first_name": "Test",
        "username": f"user{user_id}",
        "language_code": "uz",
    }


def message_update(user_id: int, text: str) -> dict:
    return {
        "update_id": _next_update_id(),
        "message": {
            "message_id": _next_update_id(),
            "date": int(dt.datetime.now(dt.timezone.utc).timestamp()),
            "chat": {"id": user_id, "type": "private"},
            "from": _user(user_id),
            "text": text,
        },
    }


def contact_update(user_id: int, phone: str, *, contact_user_id: int | None = None) -> dict:
    return {
        "update_id": _next_update_id(),
        "message": {
            "message_id": _next_update_id(),
            "date": int(dt.datetime.now(dt.timezone.utc).timestamp()),
            "chat": {"id": user_id, "type": "private"},
            "from": _user(user_id),
            "contact": {
                "phone_number": phone,
                "first_name": "Test",
                "user_id": contact_user_id if contact_user_id is not None else user_id,
            },
        },
    }


def photo_update(user_id: int, file_id: str = "AgACPhoto") -> dict:
    return {
        "update_id": _next_update_id(),
        "message": {
            "message_id": _next_update_id(),
            "date": int(dt.datetime.now(dt.timezone.utc).timestamp()),
            "chat": {"id": user_id, "type": "private"},
            "from": _user(user_id),
            "photo": [
                {
                    "file_id": file_id,
                    "file_unique_id": file_id,
                    "width": 1280,
                    "height": 960,
                    "file_size": len(FAKE_JPEG),
                }
            ],
        },
    }


def callback_update(user_id: int, data: str) -> dict:
    return {
        "update_id": _next_update_id(),
        "callback_query": {
            "id": str(_next_update_id()),
            "from": _user(user_id),
            "chat_instance": "1",
            "data": data,
            "message": {
                "message_id": _next_update_id(),
                "date": int(dt.datetime.now(dt.timezone.utc).timestamp()),
                "chat": {"id": user_id, "type": "private"},
                "from": {"id": 1, "is_bot": True, "first_name": "NovaCore"},
                "text": "…",
            },
        },
    }
