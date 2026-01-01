from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_IDENTIFIER, CONF_LIGHT_MAX_RAW, DEFAULT_LIGHT_MAX_RAW, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)

class RorosHettaSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the user step - choose setup method."""
        if user_input is not None:
            if user_input["setup_method"] == "scan":
                return await self.async_step_scan()
            else:
                return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("setup_method", default="scan"): vol.In({
                    "scan": "Scan for devices in pairing mode",
                    "manual": "Enter device information manually"
                })
            })
        )

    async def async_step_scan(self, user_input=None) -> FlowResult:
        """Scan for devices in pairing mode."""
        errors = {}

        if user_input is not None:
            if "device" in user_input:
                # User selected a device from the scan results
                identifier = user_input["device"]
                await self.async_set_unique_id(identifier)
                self._abort_if_unique_id_configured()
                
                # Store device info for configuration step
                self.context["title_placeholders"] = {
                    "name": "RørosHetta Sense",
                    "identifier": identifier[-5:],
                }
                return await self.async_step_configure()
            else:
                # User clicked "Rescan" or "Manual Setup"
                if user_input.get("action") == "manual":
                    return await self.async_step_manual()
                # Otherwise, fall through to rescan

        # Perform device scan
        try:
            discovered_devices = await self._scan_for_pairing_devices()
            if not discovered_devices:
                errors["base"] = "no_devices_found"
            else:
                # Create dropdown with discovered devices
                device_options = {
                    device["address"]: f"{device['name']} ({device['address'][-5:]})" 
                    for device in discovered_devices
                }
                
                schema = vol.Schema({
                    vol.Required("device"): vol.In(device_options),
                })
                
                return self.async_show_form(
                    step_id="scan",
                    data_schema=schema,
                    errors=errors,
                    description_placeholders={
                        "count": len(discovered_devices)
                    }
                )
        except Exception as e:
            _LOGGER.error("Device scan failed: %s", e)
            errors["base"] = "scan_failed"

        # Show scanning form with retry/manual options
        schema = vol.Schema({
            vol.Required("action", default="rescan"): vol.In({
                "rescan": "Scan again",
                "manual": "Enter device manually"
            })
        })
        
        return self.async_show_form(
            step_id="scan",
            data_schema=schema,
            errors=errors
        )

    async def async_step_manual(self, user_input=None) -> FlowResult:
        """Handle manual device entry."""
        errors = {}

        if user_input is not None:
            identifier = user_input["identifier"].strip()
            light_max_raw = user_input.get("light_max_raw", DEFAULT_LIGHT_MAX_RAW)

            if not identifier:
                errors["base"] = "invalid_identifier"
            else:
                # Validate device connection
                try:
                    await self._test_connection(identifier)
                    await self.async_set_unique_id(identifier)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"RørosHetta Sense ({identifier[-5:]})",
                        data={
                            CONF_IDENTIFIER: identifier,
                            CONF_LIGHT_MAX_RAW: light_max_raw,
                        },
                    )
                except Exception as e:
                    _LOGGER.error("Connection test failed: %s", e)
                    errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required("identifier"): str,
            vol.Optional("light_max_raw", default=DEFAULT_LIGHT_MAX_RAW): vol.Coerce(int),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )

    async def async_step_bluetooth(self, discovery_info) -> FlowResult:
        """Handle bluetooth discovery."""
        # Extract device info from discovery_info
        device = discovery_info.device
        identifier = device.address
        
        # Set unique ID and check if already configured
        await self.async_set_unique_id(identifier)
        self._abort_if_unique_id_configured()

        # Store device info for configuration step
        self.context["title_placeholders"] = {
            "name": device.name or "RørosHetta Sense",
            "identifier": identifier[-5:],
        }
        
        # Show confirmation form to user
        return await self.async_step_confirm_discovery()

    async def async_step_confirm_discovery(self, user_input=None) -> FlowResult:
        """Confirm discovery of the device."""
        if user_input is not None:
            # User confirmed, proceed to configuration
            return await self.async_step_configure()

        # Show confirmation form
        return self.async_show_form(
            step_id="confirm_discovery",
            description_placeholders=self.context.get("title_placeholders", {})
        )

    async def async_step_configure(self, user_input=None) -> FlowResult:
        """Handle device configuration."""
        errors = {}

        if user_input is not None:
            light_max_raw = user_input.get("light_max_raw", DEFAULT_LIGHT_MAX_RAW)
            identifier = self.unique_id
            
            # Validate device connection
            try:
                await self._test_connection(identifier)
            except Exception as e:
                _LOGGER.error("Connection test failed: %s", e)
                errors["base"] = "cannot_connect"
            else:
                # Create config entry
                return self.async_create_entry(
                    title=f"RørosHetta Sense ({identifier[-5:]})",
                    data={
                        CONF_IDENTIFIER: identifier,
                        CONF_LIGHT_MAX_RAW: light_max_raw,
                    },
                )

        schema = vol.Schema({
            vol.Optional("light_max_raw", default=DEFAULT_LIGHT_MAX_RAW): vol.Coerce(int),
        })
        
        return self.async_show_form(
            step_id="configure",
            data_schema=schema,
            errors=errors,
            description_placeholders=self.context.get("title_placeholders", {})
        )


    async def _test_connection(self, identifier: str) -> None:
        """Test connection to the device."""
        device = bluetooth.async_ble_device_from_address(self.hass, identifier)
        if not device:
            raise HomeAssistantError(f"Device {identifier} not reachable")
        
        _LOGGER.debug("Connection test successful for device %s", identifier)

    async def _scan_for_pairing_devices(self) -> list[dict[str, str]]:
        """Scan for RørosHetta devices that might be in pairing mode."""
        try:
            scanner = bluetooth.async_get_scanner(self.hass)
            # Scan for devices advertising our service UUID
            discovered_devices = []
            
            # Get recent service info for our service UUID
            service_infos = bluetooth.async_discovered_service_info(
                self.hass, connectable=True
            )
            
            for service_info in service_infos:
                if SERVICE_UUID.lower() in [uuid.lower() for uuid in service_info.service_uuids]:
                    discovered_devices.append({
                        "address": service_info.address,
                        "name": service_info.name or "RørosHetta Sense",
                        "rssi": service_info.rssi
                    })
            
            return discovered_devices
            
        except Exception as e:
            _LOGGER.error("Failed to scan for devices: %s", e)
            raise
