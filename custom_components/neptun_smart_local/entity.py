from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .device import Counter, NeptunSmart, WirelessSensor


def main_device_identifier(device: NeptunSmart) -> tuple[str, str]:
    return (DOMAIN, device.get_name())


def main_device_info(device: NeptunSmart, integration_version: str) -> dict:
    info = {
        "identifiers": {main_device_identifier(device)},
        "name": device.get_name(),
        "manufacturer": "Teploluxe",
        "model": device.get_model(),
        "sw_version": device.get_firmware() or integration_version,
    }
    pcb = device.get_pcb_version()
    if pcb is not None:
        info["hw_version"] = str(pcb)
    return info


class NeptunEntity(CoordinatorEntity):
    """Сущность основного модуля."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NeptunSmartCoordinator) -> None:
        super().__init__(coordinator)
        self._device: NeptunSmart = coordinator.device

    @property
    def device_info(self):
        return main_device_info(self._device, self.coordinator.integration_version)

    @property
    def available(self) -> bool:
        return super().available and self._device.is_connected()


class NeptunLineEntity(NeptunEntity):
    """Проводная линия как отдельное устройство."""

    def __init__(self, coordinator: NeptunSmartCoordinator, line_number: int) -> None:
        super().__init__(coordinator)
        self._line_number = line_number

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._device.get_name()}_line_{self._line_number}")},
            "name": f"Линия {self._line_number}",
            "manufacturer": "Teploluxe",
            "model": "Проводная линия",
            "via_device_id": self.coordinator.main_device_id,
        }


class NeptunWirelessEntity(NeptunEntity):
    """Радиодатчик как отдельное устройство."""

    def __init__(
        self,
        coordinator: NeptunSmartCoordinator,
        sensor_number: int,
        sensor: WirelessSensor,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_number = sensor_number
        self._sensor = sensor

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._device.get_name()}_wireless_{self._sensor_number}")},
            "name": f"Радиодатчик {self._sensor_number}",
            "manufacturer": "Teploluxe",
            "model": "Радиодатчик Neptun",
            "via_device_id": self.coordinator.main_device_id,
        }


class NeptunCounterEntity(NeptunEntity):
    """Счётчик воды как отдельное устройство."""

    def __init__(self, coordinator: NeptunSmartCoordinator, counter: Counter) -> None:
        super().__init__(coordinator)
        self._counter = counter

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._device.get_name()}_counter_{self._counter.get_address()}")},
            "name": self._counter.get_title(),
            "manufacturer": "Teploluxe",
            "model": self._counter.get_model_name(),
            "via_device_id": self.coordinator.main_device_id,
        }
