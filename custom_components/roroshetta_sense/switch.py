from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from bleak.exc import BleakError

from .const import DOMAIN
from .ble import SenseBleController

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    controller: SenseBleController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SenseFanAutoSwitch(controller),
        SenseLightAutoSwitch(controller),
    ], update_before_add=False)

class _BaseAutoSwitch(SwitchEntity):
    _attr_is_on = False

    def __init__(self, controller: SenseBleController, switch_type: str) -> None:
        self._ctl = controller
        self._attr_unique_id = f"{controller._cfg.identifier}_{switch_type}_auto"

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()

class SenseFanAutoSwitch(_BaseAutoSwitch):
    _attr_name = "RørosHetta Fan Auto"

    def __init__(self, controller: SenseBleController) -> None:
        super().__init__(controller, "fan")

    async def async_turn_on(self, **kwargs) -> None:
        try:
            await self._ctl.set_fan_auto()
            self._attr_is_on = True
            self.async_write_ha_state()
        except BleakError as e:
            _LOGGER.error("Failed to enable fan auto mode: %s", e)
        except Exception as e:
            _LOGGER.error("Unexpected error enabling fan auto mode: %s", e)

class SenseLightAutoSwitch(_BaseAutoSwitch):
    _attr_name = "RørosHetta Light Auto"

    def __init__(self, controller: SenseBleController) -> None:
        super().__init__(controller, "light")

    async def async_turn_on(self, **kwargs) -> None:
        try:
            await self._ctl.set_light_auto()
            self._attr_is_on = True
            self.async_write_ha_state()
        except BleakError as e:
            _LOGGER.error("Failed to enable light auto mode: %s", e)
        except Exception as e:
            _LOGGER.error("Unexpected error enabling light auto mode: %s", e)
