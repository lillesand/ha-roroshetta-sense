from __future__ import annotations

FAN_MANUAL_CMD  = "01 20 00 00 XX 00 00 00"
FAN_AUTO_CMD    = "04 20 00 00 02 00 00 00"

LIGHT_LEVEL_CMD = "05 20 00 00 XX 00 00 00"
LIGHT_AUTO_CMD  = "08 20 00 00 02 00 00 00"

FAN_MAX_RAW_DEFAULT = 120  # observed max (0x78)

def pct_to_raw(pct: int, max_raw: int) -> int:
    pct = max(0, min(100, int(pct)))
    return round(pct * max_raw / 100)

def render_cmd(template: str, value: int | None = None) -> bytes:
    if value is None:
        return bytes.fromhex(template)
    return bytes.fromhex(template.replace("XX", f"{value:02x}"))
