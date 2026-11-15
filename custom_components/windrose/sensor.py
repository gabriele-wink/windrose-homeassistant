"""Sensors for WindRose stations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    DEGREE,
    PERCENTAGE,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import WindRoseConfigEntry, WindRoseCoordinator
from .entity import WindRoseEntity, dig

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class WindRoseSensorDescription(SensorEntityDescription):
    """A sensor and where its value lives in /current/{id}."""

    value_fn: Callable[[dict[str, Any]], Any]


def _temp(key: str, *path: str, enabled: bool = True) -> WindRoseSensorDescription:
    return WindRoseSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=enabled,
        value_fn=lambda d: dig(d, *path),
    )


SENSORS: tuple[WindRoseSensorDescription, ...] = (
    _temp("temperature", "temperature", "value"),
    WindRoseSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "humidity", "value"),
    ),
    _temp("dew_point", "dew_point", "value"),
    WindRoseSensorDescription(
        key="wind_speed",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "wind", "speed", "value"),
    ),
    WindRoseSensorDescription(
        key="wind_gust",
        translation_key="wind_gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "wind", "gust_10min", "value"),
    ),
    WindRoseSensorDescription(
        key="wind_average",
        translation_key="wind_average",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: dig(d, "wind", "avg_10min", "value"),
    ),
    WindRoseSensorDescription(
        key="wind_direction",
        translation_key="wind_direction",
        device_class=SensorDeviceClass.WIND_DIRECTION,
        native_unit_of_measurement=DEGREE,
        # An angle: statistics must not average 350° and 10° to 180°.
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        value_fn=lambda d: dig(d, "wind", "direction", "degrees"),
    ),
    WindRoseSensorDescription(
        key="wind_cardinal",
        translation_key="wind_cardinal",
        icon="mdi:compass",
        entity_registry_enabled_default=False,
        value_fn=lambda d: dig(d, "wind", "direction", "cardinal"),
    ),
    WindRoseSensorDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "pressure", "sea_level", "value"),
    ),
    WindRoseSensorDescription(
        key="rain_today",
        translation_key="rain_today",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: dig(d, "rain", "today_mm"),
    ),
    WindRoseSensorDescription(
        key="rain_rate",
        translation_key="rain_rate",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "rain", "rate_mm_h"),
    ),
    WindRoseSensorDescription(
        key="rain_24h",
        translation_key="rain_24h",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        # A rolling total: neither a measurement nor an ever-growing counter.
        entity_registry_enabled_default=False,
        value_fn=lambda d: dig(d, "rain", "last_24hr_mm"),
    ),
    WindRoseSensorDescription(
        key="rain_month",
        translation_key="rain_month",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda d: dig(d, "rain", "monthly_mm"),
    ),
    WindRoseSensorDescription(
        key="solar_radiation",
        translation_key="solar_radiation",
        device_class=SensorDeviceClass.IRRADIANCE,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "solar_radiation", "value"),
    ),
    WindRoseSensorDescription(
        key="uv_index",
        translation_key="uv_index",
        native_unit_of_measurement="UV index",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sun-wireless",
        value_fn=lambda d: dig(d, "uv_index", "value"),
    ),
    _temp("heat_index", "heat_index", "value", enabled=False),
    _temp("wind_chill", "wind_chill", "value", enabled=False),
    _temp("wet_bulb", "wet_bulb", "value", enabled=False),
    _temp("indoor_temperature", "indoor", "temp_c"),
    WindRoseSensorDescription(
        key="indoor_humidity",
        translation_key="indoor_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "indoor", "hum_pct"),
    ),
    WindRoseSensorDescription(
        key="pm25",
        translation_key="pm25",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "air_quality", "pm_2p5"),
    ),
    WindRoseSensorDescription(
        key="pm10",
        translation_key="pm10",
        device_class=SensorDeviceClass.PM10,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "air_quality", "pm_10"),
    ),
    WindRoseSensorDescription(
        key="aqi",
        translation_key="aqi",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "air_quality", "aqi_val"),
    ),
    WindRoseSensorDescription(
        key="lightning_strikes",
        translation_key="lightning_strikes",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:weather-lightning",
        value_fn=lambda d: dig(d, "lightning", "strikes_today"),
    ),
    WindRoseSensorDescription(
        key="lightning_distance",
        translation_key="lightning_distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: dig(d, "lightning", "last_strike_km"),
    ),
    WindRoseSensorDescription(
        key="evapotranspiration",
        translation_key="evapotranspiration",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:water-sync",
        value_fn=lambda d: dig(d, "evapotranspiration", "day_mm"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WindRoseConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create a sensor for every value a station reports, now and later."""
    coordinator = entry.runtime_data
    known: set[tuple[int, str]] = set()

    @callback
    def _discover() -> None:
        new: list[WindRoseSensor] = []
        for station_id, data in coordinator.data.items():
            for description in SENSORS:
                marker = (station_id, description.key)
                if marker in known or description.value_fn(data.current) is None:
                    continue
                known.add(marker)
                new.append(WindRoseSensor(coordinator, station_id, description))
        if new:
            async_add_entities(new)

    _discover()
    # A sensor that only starts reporting later (an AirLink, a lightning
    # detector) appears on the next poll without a reload.
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class WindRoseSensor(WindRoseEntity, SensorEntity):
    """One reading of one station."""

    entity_description: WindRoseSensorDescription

    def __init__(
        self,
        coordinator: WindRoseCoordinator,
        station_id: int,
        description: WindRoseSensorDescription,
    ) -> None:
        super().__init__(coordinator, station_id)
        self.entity_description = description
        self._attr_unique_id = f"{station_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """The latest reading."""
        station = self.station
        return self.entity_description.value_fn(station.current) if station else None
