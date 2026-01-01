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
        # Always clean up any existing client first to prevent slot leaks
        if self._client:
            try:
                if self._client.is_connected:
                    await self._client.disconnect()
            except Exception as e:
                _LOGGER.debug("Error disconnecting existing client: %s", e)
            finally:
                self._client = None
                
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
                
                # Discover and log services/characteristics for debugging
                await self._discover_services()
                
                # Test device responsiveness on first connection
                if self._connection_attempts == 0:
                    await self.test_device_responsiveness()
                
                self._connection_attempts = 0
                return
                
            except Exception as e:
                if isinstance(e, BleakDeviceNotFoundError):
                    _LOGGER.warning(
                        "Device %s not found (attempt %d/%d)", 
                        self._cfg.identifier, attempt + 1, self._max_retries
                    )
                elif isinstance(e, BleakError):
                    _LOGGER.warning(
                        "BLE error connecting to %s (attempt %d/%d): %s",
                        self._cfg.identifier, attempt + 1, self._max_retries, e
                    )
                else:
                    _LOGGER.error(
                        "Unexpected error connecting to %s (attempt %d/%d): %s",
                        self._cfg.identifier, attempt + 1, self._max_retries, e
                    )
                # Clean up failed client to prevent slot leak
                await self._cleanup_client()
                        
            if attempt < self._max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        self._connection_attempts += 1
        raise BleakError(f"Failed to connect to device {self._cfg.identifier} after {self._max_retries} attempts")

    async def disconnect(self) -> None:
        await self._cleanup_client()

    async def _cleanup_client(self) -> None:
        """Properly clean up BLE client to prevent connection slot leaks."""
        if self._client:
            try:
                if self._client.is_connected:
                    _LOGGER.debug("Disconnecting BLE client for cleanup")
                    await self._client.disconnect()
            except Exception as e:
                _LOGGER.debug("Error during client cleanup: %s", e)
            finally:
                self._client = None
                _LOGGER.debug("BLE client cleaned up")

    async def _write(self, payload: bytes, delay_s: float = 0.2) -> None:
        _LOGGER.info(
            "BLE COMMAND: Sending %d bytes to %s: %s", 
            len(payload), COMMAND_CHAR_UUID, payload.hex().upper()
        )
        
        for attempt in range(self._max_retries):
            try:
                await self.connect()
                
                # Verify connection state before attempting write
                if not await self.verify_connection_state():
                    raise BleakError("Device not ready for commands")
                    
                _LOGGER.debug(
                    "BLE WRITE: Attempt %d/%d - Connection verified", 
                    attempt + 1, self._max_retries
                )
                
                async with self._lock:
                    _LOGGER.debug("BLE WRITE: Writing to characteristic %s", COMMAND_CHAR_UUID)
                    await self._client.write_gatt_char(COMMAND_CHAR_UUID, payload, response=False)
                    _LOGGER.info("BLE WRITE: Successfully wrote %s", payload.hex().upper())
                    
                    if delay_s:
                        await asyncio.sleep(delay_s)
                return
                
            except BleakError as e:
                _LOGGER.warning(
                    "BLE write error (attempt %d/%d): %s", 
                    attempt + 1, self._max_retries, e
                )
                # Add specific error analysis
                if "not connected" in str(e).lower():
                    _LOGGER.error("BLE ERROR: Device disconnected during write")
                elif "gatt" in str(e).lower():
                    _LOGGER.error("BLE ERROR: GATT operation failed - characteristic issue?")
                elif "timeout" in str(e).lower():
                    _LOGGER.error("BLE ERROR: Write operation timed out")
                else:
                    _LOGGER.error("BLE ERROR: Unknown BLE error type: %s", type(e).__name__)
                # Force cleanup to free connection slot
                await self._cleanup_client()
                        
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise
                    
            except Exception as e:
                _LOGGER.error("Unexpected error in BLE write: %s", e)
                # Force cleanup to free connection slot
                await self._cleanup_client()
                        
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise BleakError(f"Failed to write to device after {self._max_retries} attempts: {e}")

    async def set_fan_percent(self, percent: int) -> None:
        raw = pct_to_raw(percent, self._cfg.fan_max_raw)
        _LOGGER.info("FAN COMMAND: Setting fan to %d%% (raw value: %d/0x%02X)", percent, raw, raw)
        _LOGGER.debug("FAN COMMAND: Using template '%s' with max_raw=%d", FAN_MANUAL_CMD, self._cfg.fan_max_raw)
        command_bytes = render_cmd(FAN_MANUAL_CMD, raw)
        _LOGGER.debug("FAN COMMAND: Generated command bytes: %s", command_bytes.hex().upper())
        await self._write(command_bytes)

    async def set_fan_auto(self) -> None:
        await self._write(render_cmd(FAN_AUTO_CMD))

    async def set_light_percent(self, percent: int) -> None:
        raw = pct_to_raw(percent, self._cfg.light_max_raw)
        await self._write(render_cmd(LIGHT_LEVEL_CMD, raw))

    async def set_light_auto(self) -> None:
        await self._write(render_cmd(LIGHT_AUTO_CMD))

    async def _discover_services(self) -> None:
        """Discover and log all services and characteristics for debugging."""
        if not self._client or not self._client.is_connected:
            return
            
        try:
            _LOGGER.info("BLE DISCOVERY: Discovering services for device %s", self._cfg.identifier)
            services = await self._client.get_services()
            
            for service in services.services.values():
                _LOGGER.info("BLE SERVICE: %s (%s)", service.uuid, service.description)
                
                for char in service.characteristics:
                    properties = []
                    if "read" in char.properties:
                        properties.append("READ")
                    if "write" in char.properties:
                        properties.append("WRITE")
                    if "write-without-response" in char.properties:
                        properties.append("WRITE_NO_RESP")
                    if "notify" in char.properties:
                        properties.append("NOTIFY")
                    
                    _LOGGER.info(
                        "BLE CHAR:    %s [%s] (%s)", 
                        char.uuid, "/".join(properties), char.description
                    )
                    
                    # Highlight our target characteristic
                    if char.uuid.lower() == COMMAND_CHAR_UUID.lower():
                        _LOGGER.warning("BLE TARGET: Found our target characteristic %s", COMMAND_CHAR_UUID)
                        
        except Exception as e:
            _LOGGER.error("BLE DISCOVERY: Failed to discover services: %s", e)

    async def test_device_responsiveness(self) -> None:
        """Test different write methods and basic commands for debugging."""
        if not self._client or not self._client.is_connected:
            _LOGGER.error("DEVICE TEST: Not connected, cannot test")
            return
            
        _LOGGER.info("DEVICE TEST: Testing basic device responsiveness")
        
        # Test 1: Try write with response=True
        try:
            test_cmd = render_cmd(FAN_MANUAL_CMD, 30)  # 25% fan speed
            _LOGGER.info("DEVICE TEST: Trying write WITH response: %s", test_cmd.hex().upper())
            await self._client.write_gatt_char(COMMAND_CHAR_UUID, test_cmd, response=True)
            _LOGGER.info("DEVICE TEST: Write with response SUCCESS")
        except Exception as e:
            _LOGGER.warning("DEVICE TEST: Write with response FAILED: %s", e)
            
        await asyncio.sleep(1)
        
        # Test 2: Try write without response (current method)
        try:
            test_cmd = render_cmd(FAN_MANUAL_CMD, 60)  # 50% fan speed  
            _LOGGER.info("DEVICE TEST: Trying write WITHOUT response: %s", test_cmd.hex().upper())
            await self._client.write_gatt_char(COMMAND_CHAR_UUID, test_cmd, response=False)
            _LOGGER.info("DEVICE TEST: Write without response SUCCESS")
        except Exception as e:
            _LOGGER.warning("DEVICE TEST: Write without response FAILED: %s", e)
            
        await asyncio.sleep(1)
        
        # Test 3: Try auto command to see if device responds to any command
        try:
            auto_cmd = render_cmd(FAN_AUTO_CMD)
            _LOGGER.info("DEVICE TEST: Trying auto command: %s", auto_cmd.hex().upper())
            await self._client.write_gatt_char(COMMAND_CHAR_UUID, auto_cmd, response=False)
            _LOGGER.info("DEVICE TEST: Auto command SUCCESS")
        except Exception as e:
            _LOGGER.warning("DEVICE TEST: Auto command FAILED: %s", e)

    async def verify_connection_state(self) -> bool:
        """Verify device is properly connected and ready for commands."""
        if not self._client:
            _LOGGER.error("STATE CHECK: No BLE client exists")
            return False
            
        if not self._client.is_connected:
            _LOGGER.error("STATE CHECK: BLE client reports not connected")
            return False
            
        try:
            # Try to get services to verify connection is actually working
            services = await self._client.get_services()
            if not services:
                _LOGGER.error("STATE CHECK: No services available - connection may be stale")
                return False
                
            # Check if our target characteristic exists
            target_char = None
            for service in services.services.values():
                for char in service.characteristics:
                    if char.uuid.lower() == COMMAND_CHAR_UUID.lower():
                        target_char = char
                        break
                        
            if not target_char:
                _LOGGER.error("STATE CHECK: Target characteristic %s not found", COMMAND_CHAR_UUID)
                return False
                
            # Check if characteristic has write permissions
            if "write" not in target_char.properties and "write-without-response" not in target_char.properties:
                _LOGGER.error("STATE CHECK: Target characteristic not writable. Properties: %s", target_char.properties)
                return False
                
            _LOGGER.debug("STATE CHECK: Connection verified - ready for commands")
            return True
            
        except Exception as e:
            _LOGGER.error("STATE CHECK: Failed to verify connection: %s", e)
            return False
