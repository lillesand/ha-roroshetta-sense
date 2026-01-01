from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ble import DeviceConfig, SenseBleController

PLATFORMS: list[str] = ["fan", "light", "switch"]

_LOGGER = logging.getLogger(__name__)

_LOGGER.info("Initializing Røroshetta Sense integration")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cfg = DeviceConfig(
        identifier=entry.data["identifier"],
        light_max_raw=entry.data.get("light_max_raw", 90),
    )
    controller = SenseBleController(cfg, hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    controller: SenseBleController = hass.data[DOMAIN].pop(entry.entry_id)
    await controller.disconnect()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
