
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .const import CONF_DEVICE_ID, DEFAULT_DEVICE_ID, DEFAULT_NAME, DEFAULT_PORT, DOMAIN

STEP_TCP_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name", default=DEFAULT_NAME): str,
        vol.Required("host_ip"): str,
        vol.Required("host_port", default=DEFAULT_PORT): str,
        vol.Required(CONF_DEVICE_ID, default=DEFAULT_DEVICE_ID): NumberSelector(
            NumberSelectorConfig(min=1, max=247, step=1, mode=NumberSelectorMode.BOX)
        ),
    }
)

class NeptunSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Собрать параметры Modbus; доступность проверяется при запуске интеграции."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Invoke when a user initiates a flow via the user interface."""
        return await self.async_step_tcp(user_input)

    async def async_step_tcp(self, user_input: dict[str, Any] | None = None):
        """Configure ModBus TCP entry."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)
        return self.async_show_form(
            step_id="tcp", data_schema=STEP_TCP_DATA_SCHEMA
        )

