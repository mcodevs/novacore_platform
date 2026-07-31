from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.integrations.storage.base import Storage


@lru_cache
def get_storage() -> Storage:
    if settings.storage_backend == "s3":
        from app.integrations.storage.s3 import S3Storage

        return S3Storage()
    from app.integrations.storage.local import LocalStorage

    return LocalStorage()


__all__ = ["Storage", "get_storage"]
