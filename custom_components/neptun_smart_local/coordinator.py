from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import SCAN_INTERVAL
from .device import NeptunSmart

_LOGGER = logging.getLogger(__name__)


class NeptunSmartCoordinator(DataUpdateCoordinator):
    """Single polling loop for the Neptun Smart module."""

    def __init__(self, hass: HomeAssistant, device: NeptunSmart) -> None:
        coordinator_kwargs = {
            "name": device.get_name(),
            "update_interval": SCAN_INTERVAL,
        }
        try:
            super().__init__(hass, _LOGGER, always_update=True, **coordinator_kwargs)
        except TypeError:
            super().__init__(hass, _LOGGER, **coordinator_kwargs)
        self.device = device

    async def _async_update_data(self) -> bool:
        """Пометить все сущности недоступными, если опрос Modbus не удался."""
        try:
            success = await self.device.update()
        except Exception as err:
            raise UpdateFailed(f"Ошибка обновления {self.device.get_name()}: {err}") from err
        if not success:
            raise UpdateFailed(f"Нет связи с устройством {self.device.get_name()}")
        return True
