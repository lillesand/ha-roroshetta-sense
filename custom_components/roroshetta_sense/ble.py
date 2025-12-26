from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from bleak import BleakClient
from bleak.exc import BleakError, BleakDeviceNotFoundError
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import COMMAND_CHAR_UUID, DEFAULT_LIGHT_MAX_RAW
from .protocol import (
    FAN_MANUAL_CMD, FAN_AUTO_CMD,
    LIGHT_LEVEL_CMD, LIGHT_AUTO_CMD,
    FAN_MAX_RAW_DEFAULT, pct_to_raw, render_cmd,
)

_LOGGER = logging.getLogger(__name__)

@dataclass
class DeviceConfig:
    identifier: str
    light_max_raw: int = DEFAULT_LIGHT_MAX_RAW
    fan_max_raw: int = FAN_MAX_RAW_DEFAULT

class SenseBleController:
    def __init__(self, cfg: DeviceConfig, hass: HomeAssistant) -> None:
        self._cfg = cfg
        self._hass = hass
        self._client: Optional[BleakClient] = None
        self._lock = asyncio.Lock()
        self._connection_attempts = 0
        self._max_retries = 3

    async def connect(self) -> None:
        if self._client and self._client.is_connected:
            return
            
        for attempt in range(self._max_retries):
            try:
                _LOGGER.debug(
                    "Attempting BLE connection to %s (attempt %d/%d)",
                    self._cfg.identifier, attempt + 1, self._max_retries
                )
                
                # Use Home Assistant's bluetooth API to get the device
                ble_device = bluetooth.async_ble_device_from_address(self._hass, self._cfg.identifier)
                if not ble_device:
                    raise BleakDeviceNotFoundError(f"Device {self._cfg.identifier} not reachable")
                
                self._client = BleakClient(ble_device, timeout=10.0)
                await self._client.connect()
                _LOGGER.debug("BLE connection successful to %s", self._cfg.identifier)
                self._connection_attempts = 0
                return
                
            except BleakDeviceNotFoundError:
                _LOGGER.warning(
                    "Device %s not found (attempt %d/%d)", 
                    self._cfg.identifier, attempt + 1, self._max_retries
                )
                if self._client:
                    self._client = None
                    
            except BleakError as e:
                _LOGGER.warning(
                    "BLE error connecting to %s (attempt %d/%d): %s",
                    self._cfg.identifier, attempt + 1, self._max_retries, e
                )
                if self._client:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    finally:
                        self._client = None
                        
            except Exception as e:
                _LOGGER.error(
                    "Unexpected error connecting to %s (attempt %d/%d): %s",
                    self._cfg.identifier, attempt + 1, self._max_retries, e
                )
                if self._client:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    finally:
                        self._client = None
                        
            if attempt < self._max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        self._connection_attempts += 1
        raise BleakError(f"Failed to connect to device {self._cfg.identifier} after {self._max_retries} attempts")

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.disconnect()
            finally:
                self._client = None

    async def _write(self, payload: bytes, delay_s: float = 0.2) -> None:
        for attempt in range(self._max_retries):
            try:
                await self.connect()
                if not self._client or not self._client.is_connected:
                    raise BleakError("Not connected to device")
                    
                async with self._lock:
                    await self._client.write_gatt_char(COMMAND_CHAR_UUID, payload, response=False)
                    if delay_s:
                        await asyncio.sleep(delay_s)
                return
                
            except BleakError as e:
                _LOGGER.warning(
                    "BLE write error (attempt %d/%d): %s", 
                    attempt + 1, self._max_retries, e
                )
                # Force reconnection on next attempt
                if self._client:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    finally:
                        self._client = None
                        
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise
                    
            except Exception as e:
                _LOGGER.error("Unexpected error in BLE write: %s", e)
                # Force reconnection on next attempt  
                if self._client:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    finally:
                        self._client = None
                        
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise BleakError(f"Failed to write to device after {self._max_retries} attempts: {e}")

    async def set_fan_percent(self, percent: int) -> None:
        raw = pct_to_raw(percent, self._cfg.fan_max_raw)
        await self._write(render_cmd(FAN_MANUAL_CMD, raw))

    async def set_fan_auto(self) -> None:
        await self._write(render_cmd(FAN_AUTO_CMD))

    async def set_light_percent(self, percent: int) -> None:
        raw = pct_to_raw(percent, self._cfg.light_max_raw)
        await self._write(render_cmd(LIGHT_LEVEL_CMD, raw))

    async def set_light_auto(self) -> None:
        await self._write(render_cmd(LIGHT_AUTO_CMD))
