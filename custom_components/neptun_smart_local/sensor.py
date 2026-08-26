from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfVolume
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .device import Counter, WirelessSensor
from .entity import NeptunEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device
    sensors = [WirelessSensorsConnected(coordinator)]
    for i, sensor in enumerate(device.wireless_sensors, start=1):
        sensors.append(WirelessSensorsBatteryLevel(coordinator, i, sensor))
        sensors.append(WirelessSensorsSignalLevel(coordinator, i, sensor))
    for counter in device.counters:
        sensors.append(CounterSensor(coordinator, counter))
    async_add_entities(sensors)


class WirelessSensorsConnected(NeptunEntity, SensorEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_Wireless_sensors_connected"
        self._attr_name = "Connected wireless sensors"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return self._device.get_number_of_connected_wireless_sensors()

    @property
    def icon(self):
        return "mdi:sun-wireless-outline"


class WirelessSensorsBatteryLevel(NeptunEntity, SensorEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator, sensor_number, sensor: WirelessSensor):
        super().__init__(coordinator)
        self._sensor_number = sensor_number
        self._sensor = sensor
        self._attr_unique_id = f"{self._device.get_name()}_WirelessSensors{sensor_number}BatteryLevel"
        self._attr_name = f"Wireless sensor {sensor_number} battery level"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return self._sensor.get_battery_level()

    @property
    def icon(self):
        return "mdi:battery-high"


class WirelessSensorsSignalLevel(NeptunEntity, SensorEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator, sensor_number, sensor: WirelessSensor):
        super().__init__(coordinator)
        self._sensor_number = sensor_number
        self._sensor = sensor
        self._attr_unique_id = f"{self._device.get_name()}_WirelessSensors{sensor_number}SignalLevel"
        self._attr_name = f"Wireless sensor {sensor_number} signal level"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return self._sensor.get_signal_level()

    @property
    def icon(self):
        return "mdi:signal"


class CounterSensor(NeptunEntity, SensorEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator, counter: Counter):
        super().__init__(coordinator)
        self._counter = counter
        self._attr_unique_id = f"{self._device.get_name()}_Counter{counter.get_address()}"
        self._attr_name = f"Counter {counter.get_address()}"
        self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        return self._counter.get_value() / 1000

    @property
    def icon(self):
        return "mdi:counter"
