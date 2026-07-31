"""Yandex Fleet partner API klienti (docs/03-integrations/01-yandex-fleet-api.md).

⚠️ **FAQAT O'QISH.** Fleet bu loyihada bitta ish uchun ishlatiladi: *mashina
raqami bo'yicha mashina va haydovchi ma'lumotini olish*. Platforma Fleet'ga
**hech narsa yozmaydi** — status ham (egasining qarori, 2026-08-01).

Tasdiqlangan cheklovlar (`driver_status_reporter` da 31 endpoint skanerlangan —
qayta tekshirish shart emas):

• GPS / real-vaqt joylashuv YO'Q · ДКК natijasi YO'Q · reyting YO'Q
• Rate-limit (429) **real** — backoff va sahifalar orasida pauza majburiy
• v1 endpointlarda park ID **body ichida** (`query.park.id`)
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

CARS_LIST_PATH = "/v1/parks/cars/list"
DRIVER_PROFILES_LIST_PATH = "/v1/parks/driver-profiles/list"

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

#: Mashina foydalanish holati (fotokontrol natijasi EMAS) — faqat o'qiladi
FLEET_STATUSES = ("working", "not_working", "repairing", "no_driver", "pending")


class FleetError(RuntimeError):
    """Fleet bilan aloqada xato. Platforma ishini **to'xtatmasligi** kerak."""

    def __init__(self, message: str, *, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


class FleetAuthError(FleetError):
    """401/403 — kalit yaroqsiz. Adminga darhol alert (hujjat §8)."""


class FleetNotConfigured(FleetError):
    """`FLEET_ENABLED=false` yoki kalit yo'q."""


class FleetClient:
    """Bitta park uchun klient. `async with` bilan ishlatiladi."""

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.fleet_ready:
            raise FleetNotConfigured("Fleet o'chirilgan yoki kalit/park ID yo'q")
        self._client = httpx.AsyncClient(
            base_url=settings.fleet_base_url,
            timeout=settings.fleet_timeout_sec,
            transport=transport,
            headers={
                "X-Api-Key": settings.fleet_api_key,
                "X-Client-ID": settings.fleet_client_header,
                "Accept-Language": "ru",
            },
        )

    async def __aenter__(self) -> FleetClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # --- Past daraja ---------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:
        delay = settings.fleet_backoff_base_sec
        last_error: FleetError | None = None

        for attempt in range(settings.fleet_max_retries):
            try:
                response = await self._client.request(
                    method, path, json=json, params=params, headers=headers
                )
            except httpx.HTTPError as exc:  # tarmoq/timeout
                last_error = FleetError(f"Fleet bilan aloqa yo'q: {exc}")
                if attempt == settings.fleet_max_retries - 1:
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
                continue

            if response.status_code in (401, 403):
                raise FleetAuthError(
                    "Fleet kaliti yaroqsiz yoki ruxsat yo'q", status=response.status_code
                )

            if response.status_code in RETRYABLE_STATUS:
                last_error = FleetError(
                    f"Fleet {response.status_code}", status=response.status_code
                )
                if attempt == settings.fleet_max_retries - 1:
                    break
                log.warning("fleet_retry", status=response.status_code, attempt=attempt + 1)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
                continue

            if response.status_code >= 400:
                payload = _safe_json(response)
                raise FleetError(
                    payload.get("message") or f"Fleet {response.status_code}",
                    status=response.status_code,
                    code=payload.get("code"),
                )

            return _safe_json(response)

        raise last_error or FleetError("Fleet so'rovi bajarilmadi")

    # --- Mashinalar ----------------------------------------------------------

    async def list_cars(self) -> list[dict[str, Any]]:
        """Butun park reyestri — sahifalab, orasida pauza bilan (§5)."""
        cars: list[dict[str, Any]] = []
        offset = 0
        total: int | None = None

        while True:
            payload = await self._request(
                "POST",
                CARS_LIST_PATH,
                json={
                    "query": {"park": {"id": settings.fleet_park_id}},
                    "limit": settings.fleet_page_size,
                    "offset": offset,
                    "fields": {
                        "car": [
                            "id",
                            "number",
                            "vin",
                            "brand",
                            "model",
                            "year",
                            "color",
                            "status",
                            "callsign",
                            "category",
                        ]
                    },
                },
            )
            batch = payload.get("cars") or []
            total = payload.get("total", total)
            cars.extend(batch)

            if not batch or (total is not None and len(cars) >= total):
                break
            offset += settings.fleet_page_size
            await asyncio.sleep(settings.fleet_page_pause_sec)

        return cars

    # --- Haydovchilar --------------------------------------------------------

    async def list_driver_profiles(self) -> list[dict[str, Any]]:
        """Haydovchi profillari — **mashinaga bog'lanishi bilan**.

        Javobdagi `car` maydoni haydovchiga biriktirilgan mashinani beradi;
        raqam bo'yicha «kim minadi» shu orqali topiladi (boshqa endpoint kerak
        emas — `driver_status_reporter` da tasdiqlangan yo'l).
        """
        profiles: list[dict[str, Any]] = []
        offset = 0
        total: int | None = None

        while True:
            payload = await self._request(
                "POST",
                DRIVER_PROFILES_LIST_PATH,
                json={
                    "query": {"park": {"id": settings.fleet_park_id}},
                    "limit": settings.fleet_page_size,
                    "offset": offset,
                    "fields": {
                        "driver_profile": [
                            "id",
                            "first_name",
                            "last_name",
                            "middle_name",
                            "phones",
                            "work_status",
                        ],
                        "car": ["id", "number", "brand", "model"],
                    },
                },
            )
            batch = payload.get("driver_profiles") or []
            total = payload.get("total", total)
            profiles.extend(batch)

            if not batch or (total is not None and len(profiles) >= total):
                break
            offset += settings.fleet_page_size
            await asyncio.sleep(settings.fleet_page_pause_sec)

        return profiles


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {"data": payload}
