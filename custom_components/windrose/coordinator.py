"""Data update coordinator for WindRose."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    WindRoseAuthError,
    WindRoseClient,
    WindRoseError,
    WindRosePlanError,
)
from .const import DOMAIN, FORECAST_EVERY, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type WindRoseConfigEntry = ConfigEntry[WindRoseCoordinator]


@dataclass
class StationData:
    """Everything known about one station."""

    station: dict[str, Any]
    current: dict[str, Any] = field(default_factory=dict)
    forecast: dict[str, Any] | None = None


class WindRoseCoordinator(DataUpdateCoordinator[dict[int, StationData]]):
    """Polls every station the key can read."""

    config_entry: WindRoseConfigEntry

    def __init__(self, hass: HomeAssistant, entry: WindRoseConfigEntry, client: WindRoseClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self._ticks = 0

    async def _async_update_data(self) -> dict[int, StationData]:
        previous = self.data or {}
        refresh_forecast = self._ticks % FORECAST_EVERY == 0
        self._ticks += 1

        try:
            stations = await self.client.stations()
        except WindRoseAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except WindRoseError as err:
            raise UpdateFailed(str(err)) from err

        result: dict[int, StationData] = {}
        failures = 0
        for station in stations:
            sid = int(station["id"])
            old = previous.get(sid)
            data = StationData(station=station, forecast=old.forecast if old else None)
            try:
                data.current = await self.client.current(sid)
            except WindRoseAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except WindRoseError as err:
                failures += 1
                _LOGGER.debug("Station %s: current conditions failed: %s", sid, err)
                data.current = old.current if old else {}
            if refresh_forecast or data.forecast is None:
                try:
                    data.forecast = await self.client.forecast(sid)
                except WindRosePlanError:
                    data.forecast = None
                except WindRoseError as err:
                    _LOGGER.debug("Station %s: forecast failed: %s", sid, err)
            result[sid] = data

        if stations and failures == len(stations) and not previous:
            raise UpdateFailed("No station answered")
        return result
