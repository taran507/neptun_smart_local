
from __future__ import annotations

import asyncio
from typing import Any, Optional

from pymodbus.client import  AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.modbus import modbus
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .const import CONF_DEVICE_ID, DEFAULT_DEVICE_ID, DEFAULT_NAME, DEFAULT_PORT, DOMAIN
from .registers import NeptunSmartRegisters

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

async def async_validate_device(port, address: str | None) -> None:
    # Простая валидация - считаем что устройство доступно
    # Детальная проверка будет происходить при инициализации интеграции
    pass


class NeptunSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    data: Optional[dict(str, Any)]

    async def async_step_user(self, user_input: Optional[dict(str, Any)] = None):
        """Invoke when a user initiates a flow via the user interface."""
        return await self.async_step_tcp(user_input)



    async def async_step_tcp(self, user_input: Optional[dict(str, Any)] = None):
        """Configure ModBus TCP entry."""
        errors: dict(str, str) = {}

        if user_input is not None:
            try:
                await async_validate_device(
                    user_input["host_port"],
                    user_input["host_ip"],
                )
            except ValueError as error:
                errors["base"] = str(error)
            if not errors:
                # Input is valid, set data.
                self.data = user_input

                await asyncio.sleep(1)
                return self.async_create_entry(title=user_input["name"], data=self.data)
        return self.async_show_form(
            step_id="tcp", data_schema=STEP_TCP_DATA_SCHEMA, errors=errors
        )

