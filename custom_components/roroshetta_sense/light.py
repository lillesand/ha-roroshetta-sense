from __future__ import annotations

from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .ble import SenseBleController

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    controller: SenseBleController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SenseLight(controller)], update_before_add=False)

class SenseLight(LightEntity):
    _attr_name = "RorosHetta Light"
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_brightness = 0
    _attr_is_on = False

    def __init__(self, controller: SenseBleController) -> None:
        self._ctl = controller

    async def async_turn_on(self, **kwargs) -> None:
        brightness = int(kwargs.get("brightness", 255))
        pct = round(brightness * 100 / 255)
        await self._ctl.set_light_percent(pct)
        self._attr_brightness = brightness
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._ctl.set_light_percent(0)
        self._attr_brightness = 0
        self._attr_is_on = False
        self.async_write_ha_state()
