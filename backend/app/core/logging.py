"""structlog → JSON (fly logs). Token va telefon maskalanadi."""

from __future__ import annotations

import logging
import re
import sys

import structlog

from app.core.config import settings

_TOKEN = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b")
_PHONE = re.compile(r"\+998\d{9}")


def _mask(_logger, _method, event_dict):  # noqa: ANN001, ANN201
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            value = _TOKEN.sub("***BOT_TOKEN***", value)
            value = _PHONE.sub(lambda m: m.group(0)[:7] + "****", value)
            event_dict[key] = value
    return event_dict


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    # DEBUG faqat o'z kodimiz uchun — kutubxonalar log'ni bosib ketmasin
    logging.getLogger("app").setLevel(logging.DEBUG if settings.debug else logging.INFO)
    for noisy in ("aiosqlite", "asyncio", "aiohttp.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _mask,
            structlog.processors.JSONRenderer()
            if settings.env == "production"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        cache_logger_on_first_use=True,
    )
