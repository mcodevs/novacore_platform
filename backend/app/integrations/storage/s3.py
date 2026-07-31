"""Tigris (fly.io S3-mos) ombori — private bucket + presigned URL."""

from __future__ import annotations

import asyncio
from functools import cached_property

from app.core.config import settings
from app.integrations.storage.base import Storage


class S3Storage(Storage):
    def __init__(self) -> None:
        self.bucket = settings.s3_bucket

    @cached_property
    def _client(self):  # noqa: ANN202 — boto3 klienti
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        def _read() -> bytes:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()

        return await asyncio.to_thread(_read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self.bucket, Key=key)

    def signed_url(self, key: str, *, ttl_sec: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=ttl_sec,
        )
