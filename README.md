# RørosHetta Sense (BLE) – Home Assistant Integration

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/lillesand/ha-roroshetta-sense.svg?style=for-the-badge)](https://github.com/lillesand/ha-roroshetta-sense/releases)

A Home Assistant custom integration for controlling RørosHetta Sense devices via Bluetooth Low Energy (BLE).

## Features

- 🌟 **Automatic Bluetooth Discovery**: Devices are automatically discovered when in range
- 📱 **Manual Configuration**: Fallback option for manual device setup
- 💨 **Fan Control**: Variable speed control (0-100%)
- 💡 **Light Control**: Brightness control with auto mode
- 🔄 **Auto Mode Switch**: Toggle automatic environmental control
- 🇳🇴 **Norwegian Support**: Full Norwegian translation included

## Supported Entities

- **Fan**: Speed control, on/off functionality
- **Light**: Brightness control, auto mode toggle  
- **Switch**: Auto mode for environmental control

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/lillesand/ha-roroshetta-sense`
6. Select category: "Integration"
7. Click "Add"
8. Find "RørosHetta Sense (BLE)" in HACS and install it
9. Restart Home Assistant

### Manual Installation

1. Copy `custom_components/roroshetta_sense` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration through the UI

## Configuration

### Automatic Discovery
1. Ensure your RørosHetta Sense device is powered on and nearby
2. Go to **Settings → Devices & Services → Add Integration**
3. Search for "RørosHetta Sense" - it should appear automatically if the device is in range
4. Follow the configuration steps

### Manual Setup
1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "RørosHetta Sense (BLE)"
3. Enter your device's MAC address
4. Configure light maximum raw value (default: 90)

## Requirements

- Home Assistant 2024.1 or newer
- Bluetooth integration enabled
- RørosHetta Sense device within Bluetooth range

## Device Protocol

This integration communicates with RørosHetta Sense devices using a custom 8-byte BLE protocol:
- **Service UUID**: `0000f00d-1212-efde-1523-785fef13d123`
- **Command Characteristic**: `0000babe-1212-efde-1523-785fef13d123`

## Troubleshooting

### Device Not Found
- Ensure the device is powered on and within Bluetooth range
- Check that Home Assistant's Bluetooth integration is enabled
- Try restarting the device and Home Assistant

### Connection Issues
- The integration includes automatic retry logic with exponential backoff
- Bluetooth adapters can be finicky - consider using an ESP32 Bluetooth proxy for better range

### Performance
- Uses optimistic entities (immediate UI response)
- Commands are serialized and throttled to avoid overwhelming the device
- Automatic reconnection on connection failures

## Contributing

Issues and pull requests are welcome! Please report any bugs or feature requests on GitHub.

## License

This project is licensed under the MIT License.