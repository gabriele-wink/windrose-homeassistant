"""Small async client for the WindRose REST API v1.

Every request is signed with HMAC-SHA256: the key secret never leaves Home
Assistant, only the signature of "METHOD\\nPATH\\nSORTED_QUERY\\nTIMESTAMP".
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode, urlsplit

import aiohttp

from .const import API_BASE

TIMEOUT = aiohttp.ClientTimeout(total=30)


class WindRoseError(Exception):
    """Base error for the WindRose API."""


class WindRoseAuthError(WindRoseError):
    """The key is wrong, revoked or expired."""


class WindRosePlanError(WindRoseError):
    """The account's plan does not include this."""


class WindRoseRateLimitError(WindRoseError):
    """Too many requests for this key."""


class WindRoseConnectionError(WindRoseError):
    """WindRose could not be reached or answered with an error."""


def sign(method: str, path: str, query: dict[str, Any] | None, timestamp: int, secret: str) -> str:
    """Signature the server expects (api/v1/lib/ApiAuth.php)."""
    sorted_query = urlencode(sorted((query or {}).items()))
    payload = f"{method.upper()}\n{path}\n{sorted_query}\n{timestamp}"
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


class WindRoseClient:
    """WindRose API client bound to one key."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        key_id: str,
        key_secret: str,
        base_url: str = API_BASE,
    ) -> None:
        self._session = session
        self._key_id = key_id.strip()
        self._secret = key_secret.strip()
        self._base = base_url.rstrip("/")

    async def _request(
        self,
        method: str,
        endpoint: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base}{endpoint}"
        ts = int(time.time())
        headers = {
            "X-Api-Key": self._key_id,
            "X-Api-Timestamp": str(ts),
            "X-Api-Signature": sign(method, urlsplit(url).path, query, ts, self._secret),
            "Accept": "application/json",
        }
        try:
            async with self._session.request(
                method, url, params=query, json=body, headers=headers, timeout=TIMEOUT
            ) as resp:
                try:
                    payload = await resp.json(content_type=None)
                except ValueError as err:
                    raise WindRoseConnectionError(f"WindRose answered HTTP {resp.status} without JSON") from err
                status = resp.status
        except (aiohttp.ClientError, TimeoutError) as err:
            raise WindRoseConnectionError(f"Cannot reach WindRose: {err}") from err

        if isinstance(payload, dict) and payload.get("ok"):
            return payload.get("data")

        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        code = error.get("code", "") if isinstance(error, dict) else ""
        message = error.get("message", f"HTTP {status}") if isinstance(error, dict) else f"HTTP {status}"
        if status == 401 or code.startswith("AUTH_"):
            raise WindRoseAuthError(message)
        if status == 403 and code.startswith("PLAN_"):
            raise WindRosePlanError(message)
        if status == 429:
            raise WindRoseRateLimitError(message)
        raise WindRoseConnectionError(f"{code or status}: {message}")

    async def stations(self) -> list[dict[str, Any]]:
        """Stations the key can read (all of the owner's, or the key's scope)."""
        data = await self._request("GET", "/stations")
        return list((data or {}).get("stations") or [])

    async def current(self, station_id: int) -> dict[str, Any]:
        """Current conditions of one station, metric."""
        return await self._request("GET", f"/current/{station_id}") or {}

    async def forecast(self, station_id: int, days: int = 7) -> dict[str, Any]:
        """Open-Meteo forecast at the station (a model, not the station)."""
        return (
            await self._request(
                "POST",
                "/tools/forecast",
                body={"station_id": station_id, "days": days, "hourly": "1h"},
            )
            or {}
        )
