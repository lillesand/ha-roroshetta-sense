from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from bleak import BleakClient

from .const import COMMAND_CHAR_UUID, DEFAULT_LIGHT_MAX_RAW
from .protocol import (
    FAN_MANUAL_CMD, FAN_AUTO_CMD,
    LIGHT_LEVEL_CMD, LIGHT_AUTO_CMD,
    FAN_MAX_RAW_DEFAULT, pct_to_raw, render_cmd,
)

@dataclass
class DeviceConfig:
    identifier: str
    light_max_raw: int = DEFAULT_LIGHT_MAX_RAW
    fan_max_raw: int = FAN_MAX_RAW_DEFAULT

class SenseBleController:
    def __init__(self, cfg: DeviceConfig) -> None:
        self._cfg = cfg
        self._client: Optional[BleakClient] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._client and self._client.is_connected:
            return
        self._client = BleakClient(self._cfg.identifier)
        await self._client.connect()

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.disconnect()
            finally:
                self._client = None

    async def _write(self, payload: bytes, delay_s: float = 0.2) -> None:
        await self.connect()
        assert self._client is not None
        async with self._lock:
            await self._client.write_gatt_char(COMMAND_CHAR_UUID, payload, response=False)
            if delay_s:
                await asyncio.sleep(delay_s)

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
