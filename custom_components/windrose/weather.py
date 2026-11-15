"""Weather entity: the station's conditions plus the Open-Meteo forecast at its place."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import WindRoseConfigEntry, WindRoseCoordinator
from .entity import WindRoseEntity, dig

PARALLEL_UPDATES = 0

# WMO weather interpretation codes (Open-Meteo) → Home Assistant conditions.
WMO_CONDITION: dict[int, str] = {
    0: "sunny",
    1: "sunny",
    2: "partlycloudy",
    3: "cloudy",
    45: "fog",
    48: "fog",
    51: "rainy",
    53: "rainy",
    55: "rainy",
    56: "snowy-rainy",
    57: "snowy-rainy",
    61: "rainy",
    63: "rainy",
    65: "pouring",
    66: "snowy-rainy",
    67: "snowy-rainy",
    71: "snowy",
    73: "snowy",
    75: "snowy",
    77: "snowy",
    80: "rainy",
    81: "rainy",
    82: "pouring",
    85: "snowy",
    86: "snowy",
    95: "lightning-rainy",
    96: "hail",
    99: "hail",
}


def _condition_from_hour(row: dict[str, Any]) -> str:
    """Hourly rows carry no WMO code: read the sky from rain and cloud cover."""
    rain = row.get("rain_mm") or 0
    if rain >= 4:
        return "pouring"
    if rain >= 0.1:
        return "rainy"
    cloud = row.get("cloud_pct")
    if cloud is None:
        return "cloudy"
    if cloud >= 75:
        return "cloudy"
    if cloud >= 30:
        return "partlycloudy"
    return "sunny"


def _moment(value: str, tz: ZoneInfo | None) -> str | None:
    """'2026-11-15 14:00' or '2026-11-15' in the place's own zone → ISO with offset."""
    try:
        dt = datetime.fromisoformat(value.replace(" ", "T"))
    except (AttributeError, ValueError):
        return None
    if dt.tzinfo is None and tz is not None:
        dt = dt.replace(tzinfo=tz)
    return dt.isoformat()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WindRoseConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """One weather entity per station."""
    coordinator = entry.runtime_data
    known: set[int] = set()

    @callback
    def _discover() -> None:
        new = [
            WindRoseWeather(coordinator, station_id)
            for station_id in coordinator.data
            if station_id not in known
        ]
        known.update(w._station_id for w in new)  # noqa: SLF001
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class WindRoseWeather(WindRoseEntity, WeatherEntity):
    """Station readings now, model forecast ahead."""

    _attr_name = None  # the device name is the station's
    _attr_translation_key = "station"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY

    def __init__(self, coordinator: WindRoseCoordinator, station_id: int) -> None:
        super().__init__(coordinator, station_id)
        self._attr_unique_id = f"{station_id}_weather"

    @property
    def _current(self) -> dict[str, Any]:
        station = self.station
        return station.current if station else {}

    @property
    def _forecast(self) -> dict[str, Any]:
        station = self.station
        return (station.forecast if station else None) or {}

    @property
    def native_temperature(self) -> float | None:
        return dig(self._current, "temperature", "value")

    @property
    def native_apparent_temperature(self) -> float | None:
        return dig(self._current, "heat_index", "value")

    @property
    def native_dew_point(self) -> float | None:
        return dig(self._current, "dew_point", "value")

    @property
    def humidity(self) -> float | None:
        return dig(self._current, "humidity", "value")

    @property
    def native_pressure(self) -> float | None:
        return dig(self._current, "pressure", "sea_level", "value")

    @property
    def native_wind_speed(self) -> float | None:
        return dig(self._current, "wind", "speed", "value")

    @property
    def native_wind_gust_speed(self) -> float | None:
        return dig(self._current, "wind", "gust_10min", "value")

    @property
    def wind_bearing(self) -> float | None:
        return dig(self._current, "wind", "direction", "degrees")

    @property
    def uv_index(self) -> float | None:
        return dig(self._current, "uv_index", "value")

    @property
    def condition(self) -> str | None:
        """The sky is the model's; the rain gauge overrides it when it is wet."""
        rate = dig(self._current, "rain", "rate_mm_h")
        if rate:
            return "pouring" if rate >= 4 else "rainy"
        daily = self._forecast.get("daily") or []
        if daily and (code := daily[0].get("weather_code")) is not None:
            return WMO_CONDITION.get(int(code))
        return None

    def _tz(self) -> ZoneInfo | None:
        name = dig(self._forecast, "location", "timezone")
        try:
            return ZoneInfo(name) if name else None
        except (ZoneInfoNotFoundError, ValueError):
            return None

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        rows = self._forecast.get("daily")
        if not rows:
            return None
        tz = self._tz()
        out: list[Forecast] = []
        for row in rows:
            when = _moment(row.get("time", ""), tz)
            if when is None:
                continue
            code = row.get("weather_code")
            out.append(
                Forecast(
                    datetime=when,
                    native_temperature=row.get("temp_max_c"),
                    native_templow=row.get("temp_min_c"),
                    native_precipitation=row.get("rain_mm"),
                    precipitation_probability=row.get("rain_prob_pct"),
                    native_wind_speed=row.get("wind_max_kmh"),
                    native_wind_gust_speed=row.get("gust_max_kmh"),
                    wind_bearing=row.get("wind_dir_deg"),
                    uv_index=row.get("uv_max"),
                    condition=WMO_CONDITION.get(int(code)) if code is not None else None,
                )
            )
        return out

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        rows = self._forecast.get("hourly")
        if not rows:
            return None
        tz = self._tz()
        # The model's rows start at midnight today: keep the current hour on.
        floor = dt_util.now() - timedelta(hours=1)
        out: list[Forecast] = []
        for row in rows:
            when = _moment(row.get("time", ""), tz)
            if when is None or datetime.fromisoformat(when) < floor:
                continue
            out.append(
                Forecast(
                    datetime=when,
                    native_temperature=row.get("temp_c"),
                    humidity=row.get("hum_pct"),
                    native_precipitation=row.get("rain_mm"),
                    precipitation_probability=row.get("rain_prob_pct"),
                    native_pressure=row.get("pressure_hpa"),
                    native_wind_speed=row.get("wind_kmh"),
                    native_wind_gust_speed=row.get("gust_kmh"),
                    wind_bearing=row.get("wind_dir_deg"),
                    cloud_coverage=row.get("cloud_pct"),
                    condition=_condition_from_hour(row),
                )
            )
        return out

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Daily forecast."""
        return self._async_forecast_daily()

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Hourly forecast."""
        return self._async_forecast_hourly()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        # Tell subscribers of the forecast (the weather card) it moved.
        self.hass.async_create_task(self.async_update_listeners(None))
