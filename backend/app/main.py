"""FastAPI + aiogram — bitta ASGI ilova, bitta process."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from app.api.v1 import api_router
from app.bot.bot import get_bot, get_dispatcher
from app.bot.commands import set_default_commands
from app.core.config import settings
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.db.session import engine
from app.tasks import worker

log = structlog.get_logger(__name__)


async def _prepare_database() -> None:
    """Lokal (SQLite) rejimda sxema va seed avtomatik — prod'da Alembic."""
    if not settings.is_sqlite:
        return
    from app.db.base import Base
    from app.db.session import session_scope
    from app.seeds.loader import seed_all

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_scope() as session:
        await seed_all(session)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    configure_logging()
    await _prepare_database()

    bot = get_bot()
    dispatcher = get_dispatcher()
    tasks: list[asyncio.Task] = []

    me = await bot.get_me()
    log.info("bot_started", username=me.username, mode=settings.bot_mode)
    await set_default_commands(bot)

    if settings.bot_mode == "webhook":
        await bot.set_webhook(
            settings.webhook_url,
            secret_token=settings.webhook_secret,
            drop_pending_updates=False,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        log.info("webhook_set", url=settings.webhook_url)
    else:
        await bot.delete_webhook(drop_pending_updates=False)
        tasks.append(asyncio.create_task(dispatcher.start_polling(bot, handle_signals=False)))
        log.info("polling_started")

    tasks.append(asyncio.create_task(worker.run_forever(bot)))

    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await bot.session.close()
        await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # faqat Mini App domeni
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/api/v1")

# Mini App shu domendan beriladi (HTTPS — Telegram talabi): https://<host>/app
MINIAPP_DIST = Path(__file__).resolve().parent.parent / "miniapp_dist"


class _MiniAppStatic(StaticFiles):
    """HTML (index.html) keshlanmaydi, hash'langan assetlar uzoq keshda.

    Telegram WebView `index.html` ni keshlab, eski (hash'i o'zgargan) CSS/JS
    fayllariga ishora qilib qolardi → deploy chiqsa ham eski ko'rinish. HTML'ni
    `no-cache` bilan berish har ochilganda yangi bundle'ni kafolatlaydi;
    `/assets/*` fayllari nomida hash bo'lgani uchun bemalol immutable keshlanadi.
    """

    async def get_response(self, path: str, scope: Scope):  # type: ignore[override]
        resp = await super().get_response(path, scope)
        content_type = resp.headers.get("content-type", "")
        if content_type.startswith("text/html"):
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        elif path.startswith("assets/"):
            # Vite hash'langan fayllar — nomi o'zgarganda yangilanadi
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp


if MINIAPP_DIST.is_dir():
    app.mount("/app", _MiniAppStatic(directory=MINIAPP_DIST, html=True), name="miniapp")
    if not settings.miniapp_url:
        settings.miniapp_url = f"{settings.base_url.rstrip('/')}/app"
    log.info("miniapp_mounted", url=settings.miniapp_url)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "fields": exc.fields,
            }
        },
    )


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "env": settings.env}


@app.post(settings.webhook_path)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="invalid secret token")
    update = Update.model_validate(await request.json(), context={"bot": get_bot()})
    await get_dispatcher().feed_update(get_bot(), update)
    return {"ok": True}
