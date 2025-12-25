from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_IDENTIFIER, CONF_LIGHT_MAX_RAW, DEFAULT_LIGHT_MAX_RAW

class RorosHettaSenseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            identifier = user_input[CONF_IDENTIFIER].strip()
            light_max_raw = int(user_input.get(CONF_LIGHT_MAX_RAW, DEFAULT_LIGHT_MAX_RAW))

            if not identifier:
                errors["base"] = "invalid_identifier"
            else:
                await self.async_set_unique_id(identifier)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="RorosHetta Sense",
                    data={
                        CONF_IDENTIFIER: identifier,
                        CONF_LIGHT_MAX_RAW: light_max_raw,
                    },
                )

        schema = vol.Schema({
            vol.Required(CONF_IDENTIFIER): str,
            vol.Optional(CONF_LIGHT_MAX_RAW, default=DEFAULT_LIGHT_MAX_RAW): vol.Coerce(int),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
