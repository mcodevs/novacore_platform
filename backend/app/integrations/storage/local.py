"""Lokal fayl ombori — dev va testlar uchun."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import settings
from app.integrations.storage.base import Storage


class LocalStorage(Storage):
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.media_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await asyncio.to_thread(self._path(key).write_bytes, data)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    def signed_url(self, key: str, *, ttl_sec: int) -> str:
        # Lokal rejimda imzo yo'q — API `/api/v1/media/{id}/raw` orqali beradi
        return f"{settings.base_url.rstrip('/')}/api/v1/media/file/{key}"
