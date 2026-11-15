"""Config flow for WindRose."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    WindRoseAuthError,
    WindRoseClient,
    WindRoseConnectionError,
    WindRosePlanError,
    WindRoseRateLimitError,
)
from .const import CONF_KEY_ID, CONF_KEY_SECRET, DOMAIN

_LOGGER = logging.getLogger(__name__)

KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_KEY_ID): str,
        vol.Required(CONF_KEY_SECRET): str,
    }
)


class WindRoseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for an API key from WindRose Settings and check it."""

    VERSION = 1

    async def _check(self, data: Mapping[str, Any]) -> dict[str, str]:
        """Errors for the form; empty when the key works and sees a station."""
        client = WindRoseClient(async_get_clientsession(self.hass), data[CONF_KEY_ID], data[CONF_KEY_SECRET])
        try:
            stations = await client.stations()
        except WindRoseAuthError:
            return {"base": "invalid_auth"}
        except WindRosePlanError:
            return {"base": "plan"}
        except WindRoseRateLimitError:
            return {"base": "rate_limited"}
        except WindRoseConnectionError:
            return {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error while checking the WindRose key")
            return {"base": "unknown"}
        if not stations:
            return {"base": "no_stations"}
        return {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Enter the key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {k: v.strip() for k, v in user_input.items()}
            await self.async_set_unique_id(user_input[CONF_KEY_ID])
            self._abort_if_unique_id_configured()
            errors = await self._check(user_input)
            if not errors:
                return self.async_create_entry(title="WindRose", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(KEY_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The key stopped working (revoked or expired)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Enter a new key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {k: v.strip() for k, v in user_input.items()}
            errors = await self._check(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), unique_id=user_input[CONF_KEY_ID], data=user_input
                )
        return self.async_show_form(step_id="reauth_confirm", data_schema=KEY_SCHEMA, errors=errors)
