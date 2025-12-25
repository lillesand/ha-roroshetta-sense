from __future__ import annotations

import logging

from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from bleak.exc import BleakError

from .const import DOMAIN
from .ble import SenseBleController

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    controller: SenseBleController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SenseLight(controller)], update_before_add=False)

class SenseLight(LightEntity):
    _attr_name = "RørosHetta Light"
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_brightness = 0
    _attr_is_on = False

    def __init__(self, controller: SenseBleController) -> None:
        self._ctl = controller
        self._attr_unique_id = f"{controller._cfg.identifier}_light"

    async def async_turn_on(self, **kwargs) -> None:
        try:
            brightness = int(kwargs.get("brightness", 255))
            pct = round(brightness * 100 / 255)
            await self._ctl.set_light_percent(pct)
            self._attr_brightness = brightness
            self._attr_is_on = True
            self.async_write_ha_state()
        except BleakError as e:
            _LOGGER.error("Failed to turn on light: %s", e)
        except Exception as e:
            _LOGGER.error("Unexpected error turning on light: %s", e)

    async def async_turn_off(self, **kwargs) -> None:
        try:
            await self._ctl.set_light_percent(0)
            self._attr_brightness = 0
            self._attr_is_on = False
            self.async_write_ha_state()
        except BleakError as e:
            _LOGGER.error("Failed to turn off light: %s", e)
        except Exception as e:
            _LOGGER.error("Unexpected error turning off light: %s", e)
