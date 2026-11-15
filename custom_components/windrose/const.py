"""Constants for the WindRose integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "windrose"
MANUFACTURER: Final = "WindRose"

CONF_KEY_ID: Final = "key_id"
CONF_KEY_SECRET: Final = "key_secret"

API_BASE: Final = "https://app.windroses.world/api/v1"
APP_URL: Final = "https://app.windroses.world"

# The station's live state is refreshed by WindRose itself; five minutes keeps
# Home Assistant current while staying far below the per-key rate limit
# (30 requests a minute on the Free plan).
UPDATE_INTERVAL: Final = timedelta(minutes=5)
# The forecast is a weather model (Open-Meteo), not the station: it changes
# slowly, so it is fetched every sixth update.
FORECAST_EVERY: Final = 6
