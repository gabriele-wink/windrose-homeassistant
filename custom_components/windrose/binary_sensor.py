"""Binary sensors for WindRose stations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import WindRoseConfigEntry, WindRoseCoordinator
from .entity import WindRoseEntity, dig

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class WindRoseBinaryDescription(BinarySensorEntityDescription):
    """A binary sensor derived from /current/{id}; None means "not reported"."""

    value_fn: Callable[[dict[str, Any]], bool | None]


def _raining(d: dict[str, Any]) -> bool | None:
    rate = dig(d, "rain", "rate_mm_h")
    return None if rate is None else rate > 0


BINARY_SENSORS: tuple[WindRoseBinaryDescription, ...] = (
    WindRoseBinaryDescription(
        key="raining",
        translation_key="raining",
        device_class=BinarySensorDeviceClass.MOISTURE,
        value_fn=_raining,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WindRoseConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the binary sensors each station can feed."""
    coordinator = entry.runtime_data
    known: set[tuple[int, str]] = set()

    @callback
    def _discover() -> None:
        new: list[WindRoseBinarySensor] = []
        for station_id, data in coordinator.data.items():
            for description in BINARY_SENSORS:
                marker = (station_id, description.key)
                if marker in known or description.value_fn(data.current) is None:
                    continue
                known.add(marker)
                new.append(WindRoseBinarySensor(coordinator, station_id, description))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class WindRoseBinarySensor(WindRoseEntity, BinarySensorEntity):
    """A yes/no fact about a station."""

    entity_description: WindRoseBinaryDescription

    def __init__(
        self,
        coordinator: WindRoseCoordinator,
        station_id: int,
        description: WindRoseBinaryDescription,
    ) -> None:
        super().__init__(coordinator, station_id)
        self.entity_description = description
        self._attr_unique_id = f"{station_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Whether the condition holds."""
        station = self.station
        return self.entity_description.value_fn(station.current) if station else None
