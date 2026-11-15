"""Base entity for WindRose."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import APP_URL, DOMAIN, MANUFACTURER
from .coordinator import StationData, WindRoseCoordinator


def dig(data: dict[str, Any] | None, *path: str) -> Any:
    """Walk nested dicts; None as soon as a step is missing."""
    cur: Any = data
    for step in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(step)
    return cur


class WindRoseEntity(CoordinatorEntity[WindRoseCoordinator]):
    """An entity that belongs to one WindRose station."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WindRoseCoordinator, station_id: int) -> None:
        super().__init__(coordinator)
        self._station_id = station_id
        station = coordinator.data[station_id].station
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(station_id))},
            name=station.get("name") or f"WindRose {station_id}",
            manufacturer=MANUFACTURER,
            model="Weather station",
            configuration_url=APP_URL,
        )

    @property
    def station(self) -> StationData | None:
        """This station's latest data (None if it left the account)."""
        return self.coordinator.data.get(self._station_id)

    @property
    def available(self) -> bool:
        """Available while the station is still listed and the last poll worked."""
        return super().available and self.station is not None
