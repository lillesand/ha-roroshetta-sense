from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .ble import SenseBleController

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    controller: SenseBleController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SenseFan(controller)], update_before_add=False)

class SenseFan(FanEntity):
    _attr_name = "RorosHetta Fan"
    _attr_supported_features = FanEntityFeature.SET_SPEED
    _attr_percentage = 0
    _attr_is_on = False

    def __init__(self, controller: SenseBleController) -> None:
        self._ctl = controller
        self._attr_unique_id = f"{controller._cfg.identifier}_fan"

    async def async_set_percentage(self, percentage: int) -> None:
        await self._ctl.set_fan_percent(percentage)
        self._attr_percentage = int(percentage)
        self._attr_is_on = int(percentage) > 0
        self.async_write_ha_state()

    async def async_turn_on(self, percentage: int | None = None, **kwargs) -> None:
        await self.async_set_percentage(percentage if percentage is not None else 25)

    async def async_turn_off(self, **kwargs) -> None:
        await self.async_set_percentage(0)
