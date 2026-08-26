from __future__ import annotations

import json
import os

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .device import WirelessSensor
from .entity import NeptunEntity


def get_integration_version():
    """Получает версию интеграции из manifest.json"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        manifest_path = os.path.join(current_dir, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            return manifest.get("version", "unknown")
    except Exception:
        return "unknown"


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device
    binary_sensors = [
        MainModule(coordinator),
        FirstGroupModuleAlert(coordinator),
    ]
    if device.get_dual_group_mode():
        binary_sensors.append(SecondGroupModuleAlert(coordinator))
    binary_sensors.append(DischargeWirelessSensors(coordinator))
    binary_sensors.append(LostWirelessSensors(coordinator))
    for i in 1, 2, 3, 4:
        binary_sensors.append(WiredLineAlertStatus(coordinator, line_number=i))
    for i, sensor in enumerate(device.wireless_sensors, start=1):
        binary_sensors.append(WirelessSensorAlertStatus(coordinator, i, sensor))
        binary_sensors.append(WirelessSensorDischargeStatus(coordinator, i, sensor))
        binary_sensors.append(WirelessSensorLostStatus(coordinator, i, sensor))
    async_add_entities(binary_sensors)


class MainModule(NeptunEntity, BinarySensorEntity):
    """Основной модуль - общая авария системы"""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = self._device.get_name()
        self._attr_name = self._device.get_name()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device.get_name())},
            "name": self._device.get_name(),
            "sw_version": get_integration_version(),
            "model": "Neptun Smart",
            "manufacturer": "Teploluxe",
        }

    @property
    def icon(self):
        return "mdi:water-pump"

    @property
    def is_on(self) -> bool:
        return bool(self._device.get_first_group_alarm() or self._device.get_second_group_alarm())


class FirstGroupModuleAlert(NeptunEntity, BinarySensorEntity):
    """Авария первой группы - датчик протечки воды"""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_first_group_alarm_module_alert"
        self._attr_name = "First group water leak"

    @property
    def icon(self):
        return "mdi:water"

    @property
    def is_on(self) -> bool:
        return self._device.get_first_group_alarm()


class SecondGroupModuleAlert(NeptunEntity, BinarySensorEntity):
    """Авария второй группы - датчик протечки воды"""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_second_group_alarm_module_alert"
        self._attr_name = "Second group water leak"

    @property
    def icon(self):
        return "mdi:water"

    @property
    def is_on(self) -> bool:
        return self._device.get_second_group_alarm()

    @property
    def available(self) -> bool:
        return super().available and self._device.get_dual_group_mode()


class DischargeWirelessSensors(NeptunEntity, BinarySensorEntity):
    """Разряд беспроводных датчиков"""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_discharge_wireless_sensors"
        self._attr_name = "Wireless sensors battery low"

    @property
    def icon(self):
        return "mdi:battery"

    @property
    def is_on(self) -> bool:
        return self._device.get_discharge_wireless_sensors()


class LostWirelessSensors(NeptunEntity, BinarySensorEntity):
    """Потеря связи с беспроводными датчиками"""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_lost_wireless_sensors"
        self._attr_name = "Wireless sensors connection lost"

    @property
    def icon(self):
        return "mdi:wifi"

    @property
    def is_on(self) -> bool:
        return self._device.get_lost_wireless_sensors()


class WiredLineAlertStatus(NeptunEntity, BinarySensorEntity):
    """Статус аварии проводных линий"""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    def __init__(self, coordinator: NeptunSmartCoordinator, line_number):
        super().__init__(coordinator)
        self._line_number = line_number
        self._attr_unique_id = f"{self._device.get_name()}_WiredAlertStatus_line{line_number}"
        self._attr_name = f"Wired line {line_number} water leak"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def icon(self):
        return "mdi:water"

    @property
    def is_on(self) -> bool:
        return self._device.get_line_status(line_number=self._line_number)


class WirelessSensorAlertStatus(NeptunEntity, BinarySensorEntity):
    """Статус аварии беспроводного датчика"""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    def __init__(self, coordinator: NeptunSmartCoordinator, sensor_number, sensor: WirelessSensor):
        super().__init__(coordinator)
        self._sensor_number = sensor_number
        self._sensor = sensor
        self._attr_unique_id = f"{self._device.get_name()}_WirelessAlertStatus_sensor{sensor_number}"
        self._attr_name = f"Wireless sensor {sensor_number} water leak"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def icon(self):
        return "mdi:water"

    @property
    def is_on(self) -> bool:
        return self._sensor.get_alert_status()


class WirelessSensorDischargeStatus(NeptunEntity, BinarySensorEntity):
    """Статус разряда беспроводного датчика"""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, coordinator: NeptunSmartCoordinator, sensor_number, sensor: WirelessSensor):
        super().__init__(coordinator)
        self._sensor_number = sensor_number
        self._sensor = sensor
        self._attr_unique_id = f"{self._device.get_name()}_WirelessDischargeStatus_sensor{sensor_number}"
        self._attr_name = f"Wireless sensor {sensor_number} battery low"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def icon(self):
        return "mdi:battery"

    @property
    def is_on(self) -> bool:
        return self._sensor.get_discharge_status()


class WirelessSensorLostStatus(NeptunEntity, BinarySensorEntity):
    """Статус потери связи с беспроводным датчиком"""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: NeptunSmartCoordinator, sensor_number, sensor: WirelessSensor):
        super().__init__(coordinator)
        self._sensor_number = sensor_number
        self._sensor = sensor
        self._attr_unique_id = f"{self._device.get_name()}_WirelessLostStatus_sensor{sensor_number}"
        self._attr_name = f"Wireless sensor {sensor_number} connection lost"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def icon(self):
        return "mdi:wifi"

    @property
    def is_on(self) -> bool:
        return self._sensor.get_lost_sensor_status()
