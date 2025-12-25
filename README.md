# RorosHetta Sense (BLE) – Home Assistant custom integration (bootstrap)

## Install
1. Copy `custom_components/roroshetta_sense` into your Home Assistant `config/custom_components/`.
2. Restart Home Assistant.
3. Add integration: **Settings → Devices & Services → Add Integration → RorosHetta Sense (BLE)**
4. Enter the device identifier/address used by the host running HA.

## Notes
- Entities are optimistic (no state decode yet).
- Writes are serialized and throttled.
