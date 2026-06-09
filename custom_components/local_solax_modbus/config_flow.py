"""Config flow for the Local Solax ModBus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_CACHE_TTL,
    CONF_CONNECT_TIMEOUT,
    CONF_DONGLE_HOST,
    CONF_DONGLE_PORT,
    CONF_LISTEN_PORT,
    CONF_MIN_UPSTREAM_INTERVAL,
    CONF_RECONNECT_DELAY,
    DOMAIN,
)
from .const_defaults import (
    DEFAULT_CACHE_TTL,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_DONGLE_PORT,
    DEFAULT_LISTEN_PORT,
    DEFAULT_MIN_UPSTREAM_INTERVAL,
    DEFAULT_RECONNECT_DELAY,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DONGLE_HOST): str,
        vol.Required(CONF_DONGLE_PORT, default=DEFAULT_DONGLE_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_LISTEN_PORT, default=DEFAULT_LISTEN_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_CACHE_TTL, default=DEFAULT_CACHE_TTL): vol.All(
            vol.Coerce(float), vol.Range(min=0.0)
        ),
        vol.Optional(CONF_MIN_UPSTREAM_INTERVAL, default=DEFAULT_MIN_UPSTREAM_INTERVAL): vol.All(
            vol.Coerce(float), vol.Range(min=0.0)
        ),
        vol.Optional(CONF_CONNECT_TIMEOUT, default=DEFAULT_CONNECT_TIMEOUT): vol.All(
            vol.Coerce(float), vol.Range(min=1.0)
        ),
        vol.Optional(CONF_RECONNECT_DELAY, default=DEFAULT_RECONNECT_DELAY): vol.All(
            vol.Coerce(float), vol.Range(min=1.0)
        ),
    }
)


async def validate_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    if not data[CONF_DONGLE_HOST].strip():
        raise InvalidDongleHostError
    return data


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Local Solax ModBus proxy."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Return the options flow handler."""
        return OptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

        errors = {}

        try:
            await validate_input(user_input)
        except InvalidDongleHostError:
            errors[CONF_DONGLE_HOST] = "invalid_dongle_host"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title="Local Solax ModBus", data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Local Solax ModBus."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        cfg = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CACHE_TTL,
                    default=cfg.get(CONF_CACHE_TTL, DEFAULT_CACHE_TTL),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
                vol.Optional(
                    CONF_MIN_UPSTREAM_INTERVAL,
                    default=cfg.get(CONF_MIN_UPSTREAM_INTERVAL, DEFAULT_MIN_UPSTREAM_INTERVAL),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
                vol.Optional(
                    CONF_CONNECT_TIMEOUT,
                    default=cfg.get(CONF_CONNECT_TIMEOUT, DEFAULT_CONNECT_TIMEOUT),
                ): vol.All(vol.Coerce(float), vol.Range(min=1.0)),
                vol.Optional(
                    CONF_RECONNECT_DELAY,
                    default=cfg.get(CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY),
                ): vol.All(vol.Coerce(float), vol.Range(min=1.0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class InvalidDongleHostError(HomeAssistantError):
    """Error raised when the dongle host is blank."""
