# WindRose for Home Assistant

Your [WindRose](https://windroses.world) weather stations, **whatever the brand** (Davis, Ecowitt, Tempest, Netatmo, Ambient, AcuRite, METER, HOBO, METOS, Meteobridge, Barani, Campbell and more), as Home Assistant devices.

One integration instead of one per brand. WindRose reads your station on its own schedule and Home Assistant reads WindRose, so nothing here talks to your hardware or to the vendor's cloud.

## What you get

For every station on your account, a device with:

- **Sensors**: temperature, humidity, dew point, wind speed, gust (10 min), wind direction, pressure, rain today, rain rate, solar radiation, UV index. Where the station has them: indoor temperature and humidity, PM2.5, PM10, air quality index, lightning strikes and distance, evapotranspiration. Heat index, wind chill, wet bulb, 10-minute wind average, 24-hour and monthly rain are there too, disabled by default.
- **Binary sensor**: raining.
- **A weather entity**: the station's readings now and the forecast for its place, daily and hourly. The sky comes from the Open-Meteo model; the rain gauge overrides it when it is wet.

A sensor appears only if your station reports it, and one that starts reporting later shows up on the next update without a reload.

## Requirements

- A WindRose account. **Every plan works, Free included.**
- Home Assistant 2025.6 or newer.

## Install

**Marketplace (Home Assistant 2026.11 and newer):** open **Settings → Marketplace**, add `https://github.com/gabriele-wink/windrose-homeassistant` as a custom repository and install **WindRose**.

**HACS (older versions):** HACS → ⋮ → **Custom repositories** → paste the URL above, category **Integration** → install **WindRose**.

Restart Home Assistant.

## Set up

1. In WindRose open **Settings → API & MCP access** and press **Generate Key**. Save the **key secret**: it is shown once.
2. In Home Assistant: **Settings → Devices & services → Add integration → WindRose**.
3. Paste the **key ID** (starts with `wr_`) and the **key secret**.

A key can cover all your stations or just one: that is chosen when it is created. The integration only reads, whatever the plan. If the key is revoked or expires, Home Assistant asks you for a new one.

## Limits by plan

| Plan | Stations | Keys | Requests per key |
|------|----------|------|------------------|
| Free | 1 | 1 | 30 / min |
| Pro | 3 | 2 | 60 / min |
| Business | 10 | 5 | 300 / min |

Home Assistant asks every 5 minutes, about `1 + stations` requests plus one per station every 30 minutes for the forecast: far below any limit. The readings are as fresh as WindRose's own, which depends on the plan and on the brand of the station.

## Automation ideas

```yaml
automation:
  - alias: Close the awning in strong wind
    triggers:
      - trigger: numeric_state
        entity_id: sensor.home_garden_wind_gust_10_min
        above: 40
    actions:
      - action: cover.close_cover
        target:
          entity_id: cover.awning
```

## How it works

Requests go to `https://app.windroses.world/api/v1`, signed with HMAC-SHA256. The key secret never leaves Home Assistant: only the signature of `METHOD\nPATH\nSORTED_QUERY\nTIMESTAMP` is sent. Polling interval: 5 minutes.

## Troubleshooting

- **"The key ID or the secret is wrong"**: copy both parts again; the secret is shown only when the key is created. Generate a new key if you lost it.
- **"This key sees no station"**: the key was limited to a station that no longer exists, or the account has none.
- **A sensor is missing**: the station does not report it to WindRose. Check the station page in the WindRose app.
- Debug logs: `logger: logs: custom_components.windrose: debug`.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install pytest aiohttp
pytest
```

The signature test checks the Python code against the server's PHP implementation byte for byte.

## Licence

MIT. WindRose is a service by WindRose; this repository is the open-source client.
