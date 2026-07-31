"""Media ombori abstraksiyasi.

Asosiy ombor — Tigris (S3-mos, private bucket). Lokal rejim faqat dev/test
uchun. Telegram `file_id` — hech qachon asosiy manba emas
(docs/03-integrations/03-media-and-storage.md §2).
"""

from __future__ import annotations

import abc


class Storage(abc.ABC):
    @abc.abstractmethod
    async def put(self, key: str, data: bytes, *, content_type: str) -> None: ...

    @abc.abstractmethod
    async def get(self, key: str) -> bytes: ...

    @abc.abstractmethod
    async def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def signed_url(self, key: str, *, ttl_sec: int) -> str:
        """Vaqtinchalik ko'rish havolasi (15 daqiqa). Ochiq bucket yo'q."""
