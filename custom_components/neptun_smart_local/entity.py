from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .device import NeptunSmart


class NeptunEntity(CoordinatorEntity):
    """Base entity bound to the shared coordinator."""

    def __init__(self, coordinator: NeptunSmartCoordinator) -> None:
        super().__init__(coordinator)
        self._device: NeptunSmart = coordinator.device

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._device.get_name())}}

    @property
    def available(self) -> bool:
        return super().available and self._device.is_connected()
