"""The Local Solax ModBus integration setup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .const import (
    CONF_CACHE_TTL,
    CONF_CONNECT_TIMEOUT,
    CONF_DONGLE_HOST,
    CONF_DONGLE_PORT,
    CONF_LISTEN_PORT,
    CONF_MIN_UPSTREAM_INTERVAL,
    CONF_RECONNECT_DELAY,
    DOMAIN,
    PROXY_KEY,
)
from .const_defaults import (
    DEFAULT_CACHE_TTL,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_DONGLE_PORT,
    DEFAULT_LISTEN_PORT,
    DEFAULT_MIN_UPSTREAM_INTERVAL,
    DEFAULT_RECONNECT_DELAY,
)
from .server import ModbusTCPProxy

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the proxy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    cfg = entry.data
    proxy = ModbusTCPProxy(
        listen_host="0.0.0.0",  # noqa: S104
        listen_port=cfg.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT),
        dongle_host=cfg[CONF_DONGLE_HOST],
        dongle_port=cfg.get(CONF_DONGLE_PORT, DEFAULT_DONGLE_PORT),
        cache_ttl=cfg.get(CONF_CACHE_TTL, DEFAULT_CACHE_TTL),
        min_upstream_interval=cfg.get(CONF_MIN_UPSTREAM_INTERVAL, DEFAULT_MIN_UPSTREAM_INTERVAL),
        connect_timeout=cfg.get(CONF_CONNECT_TIMEOUT, DEFAULT_CONNECT_TIMEOUT),
        reconnect_delay=cfg.get(CONF_RECONNECT_DELAY, DEFAULT_RECONNECT_DELAY),
    )
    await proxy.start()

    hass.data[DOMAIN][entry.entry_id] = {PROXY_KEY: proxy}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and stop the proxy."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        proxy: ModbusTCPProxy | None = entry_data.get(PROXY_KEY)
        if proxy is not None:
            await proxy.stop()
    return unload_ok
