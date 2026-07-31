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
        """Ikkinchi mudofaa: yo'l doim `MEDIA_ROOT` ichida qolishi shart."""
        root = self.root.resolve()
        path = (root / key).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"storage key MEDIA_ROOT dan chiqdi: {key!r}")
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
        """Lokal omborda imzolangan havola yo'q — `media_service.view_url()`
        `/api/v1/media/{id}/raw` endpointini qaytaradi. Bu — zaxira qiymat."""
        return f"{settings.base_url.rstrip('/')}/api/v1/media/raw?key={key}"
