"""Routerlar tartibi muhim: fallback — eng oxirida."""

from __future__ import annotations

from aiogram import Router

from app.bot.handlers import common, negotiation, period, report, review, start


def build_router() -> Router:
    router = Router(name="root")
    router.include_router(start.router)
    router.include_router(report.router)
    router.include_router(negotiation.router)
    router.include_router(review.router)
    from app.bot.handlers import stats

    router.include_router(stats.router)
    router.include_router(period.router)
    router.include_router(common.router)  # oxirgi
    return router
