from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, auth, catalogs, finance, media, submissions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(catalogs.router)
api_router.include_router(submissions.router)
api_router.include_router(media.router)
api_router.include_router(finance.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]
