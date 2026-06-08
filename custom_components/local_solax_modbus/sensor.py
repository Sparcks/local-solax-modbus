"""Diagnostic sensor platform for Local Solax ModBus integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PROXY_KEY
from .server import ModbusTCPProxy, ProxyStats

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

_DEVICE_INFO_BASE = {
    "manufacturer": "Local Solax ModBus",
    "model": "Modbus TCP Proxy",
    "name": "Local Solax ModBus Proxy",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up diagnostic sensors for the proxy."""
    proxy: ModbusTCPProxy = hass.data[DOMAIN][config_entry.entry_id][PROXY_KEY]
    entry_id = config_entry.entry_id
    async_add_entities(
        [
            ProxyStatsSensor(proxy, entry_id, desc)
            for desc in _SENSOR_DESCRIPTIONS
        ]
    )


@dataclass
class ProxyStatsSensorDescription(SensorEntityDescription):
    """Describes a proxy diagnostic sensor."""

    get_value: Callable[[ProxyStats], Any] = lambda _: None


_SENSOR_DESCRIPTIONS: list[ProxyStatsSensorDescription] = [
    ProxyStatsSensorDescription(
        key="dongle_online",
        name="Dongle online",
        icon="mdi:lan-connect",
        get_value=lambda s: "online" if s.dongle_online else "offline",
    ),
    ProxyStatsSensorDescription(
        key="upstream_requests",
        name="Upstream requests",
        icon="mdi:arrow-up-circle",
        native_unit_of_measurement="requests",
        state_class=SensorStateClass.TOTAL_INCREASING,
        get_value=lambda s: s.upstream_requests,
    ),
    ProxyStatsSensorDescription(
        key="downstream_requests",
        name="Downstream requests",
        icon="mdi:arrow-down-circle",
        native_unit_of_measurement="requests",
        state_class=SensorStateClass.TOTAL_INCREASING,
        get_value=lambda s: s.downstream_requests,
    ),
    ProxyStatsSensorDescription(
        key="cache_hits",
        name="Cache hits",
        icon="mdi:database-check",
        native_unit_of_measurement="requests",
        state_class=SensorStateClass.TOTAL_INCREASING,
        get_value=lambda s: s.cache_hits,
    ),
    ProxyStatsSensorDescription(
        key="cache_hit_ratio",
        name="Cache hit ratio",
        icon="mdi:percent",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        get_value=lambda s: round(s.cache_hit_ratio * 100, 1),
    ),
    ProxyStatsSensorDescription(
        key="upstream_errors",
        name="Upstream errors",
        icon="mdi:alert-circle",
        native_unit_of_measurement="errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        get_value=lambda s: s.upstream_errors,
    ),
    ProxyStatsSensorDescription(
        key="last_error",
        name="Last error",
        icon="mdi:alert",
        get_value=lambda s: s.last_error or "none",
    ),
]


class ProxyStatsSensor(SensorEntity):
    """A diagnostic sensor that surfaces a single ProxyStats field."""

    should_poll = True

    def __init__(
        self,
        proxy: ModbusTCPProxy,
        entry_id: str,
        description: ProxyStatsSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        self._proxy = proxy
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._get_value = description.get_value

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info so all sensors group under one device."""
        return DeviceInfo(
            identifiers={(DOMAIN, "proxy")},
            **_DEVICE_INFO_BASE,
        )

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self._get_value(self._proxy.stats)

    async def async_update(self) -> None:
        """No-op — stats are updated in-place by the proxy."""
        return
