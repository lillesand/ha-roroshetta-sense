# Codex instructions: RorosHetta/Snøhetta Sense Home Assistant integration

## Goal
Create/extend a Home Assistant **custom integration** that controls a RorosHetta/Snøhetta Sense kitchen ventilator over BLE using a known, verified protocol.

## Non-negotiables (do not change)
- Domain: `roroshetta_sense`
- Command characteristic UUID (command sink): `0000babe-1212-efde-1523-785fef13d123`
- Service UUID present on device: `0000f00d-1212-efde-1523-785fef13d123`
- Commands are 8-byte frames.
- Templates (byte index 4 is the only replaced byte for level commands):

  - Fan manual:  `01 20 00 00 XX 00 00 00`
  - Fan auto:    `04 20 00 00 02 00 00 00`
  - Light level: `05 20 00 00 XX 00 00 00`
  - Light auto:  `08 20 00 00 02 00 00 00`

- Mapping:
  - Fan percent 0–100 -> raw 0–120 (0x00..0x78)
  - Light percent 0–100 -> raw 0–90 (observed; keep configurable but default 90)

## Architecture requirements
- Maintain **one BLE connection per config entry**.
- Serialize writes with an `asyncio.Lock`.
- Use `response=False` for writes (Write Without Response).
- Throttle writes with a small sleep (default 0.2s).
- Entities can be optimistic (no state decode required to start). Do not invent decoding unless user provides it.
- Provide entities:
  - `fan` (percentage)
  - `light` (brightness)
  - `switch` for fan auto
  - `switch` for light auto

## Config
- Config flow asks for:
  - `identifier`: CoreBluetooth identifier on macOS or BLE address/identifier on the host running HA
  - optional `light_max_raw` default 90
- Store in config entry.

## Coding style
- Keep controller logic in `ble.py` (single source of truth).
- Keep command templates and mapping in `protocol.py`.
- Keep HA glue minimal and correct.

## Testing expectations
- Writes must call `write_gatt_char(COMMAND_CHAR_UUID, payload, response=False)`.
- No scanning required; use the configured identifier/address.
