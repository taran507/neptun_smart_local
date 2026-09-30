from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfVolume
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .entity import NeptunCounterEntity, NeptunEntity, NeptunWirelessEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device
    sensors = [WirelessSensorsCount(coordinator)]
    for i, sensor in enumerate(device.wireless_sensors, start=1):
        sensors.append(WirelessBattery(coordinator, i, sensor))
        sensors.append(WirelessSignal(coordinator, i, sensor))
    for counter in device.counters:
        sensors.append(WaterCounter(coordinator, counter))
    if device.is_se():
        sensors.append(SupplyVoltage(coordinator))
        sensors.append(DeviceError(coordinator))
        sensors.append(ValveHealth(coordinator, 1, 1))
        sensors.append(ValveHealth(coordinator, 1, 2))
        sensors.append(ValveHealth(coordinator, 2, 1))
        sensors.append(ValveHealth(coordinator, 2, 2))
    async_add_entities(sensors)


class WirelessSensorsCount(NeptunEntity, SensorEntity):
    _attr_name = "Радиодатчики"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:access-point"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_Wireless_sensors_connected"

    @property
    def native_value(self):
        return self._device.get_number_of_connected_wireless_sensors()


class WirelessBattery(NeptunWirelessEntity, SensorEntity):
    _attr_name = "Батарея"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:battery-high"

    def __init__(self, coordinator, sensor_number, sensor):
        super().__init__(coordinator, sensor_number, sensor)
        self._attr_unique_id = f"{self._device.get_name()}_WirelessSensors{sensor_number}BatteryLevel"

    @property
    def native_value(self):
        return self._sensor.get_battery_level()


class WirelessSignal(NeptunWirelessEntity, SensorEntity):
    _attr_name = "Сигнал"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:signal"

    def __init__(self, coordinator, sensor_number, sensor):
        super().__init__(coordinator, sensor_number, sensor)
        self._attr_unique_id = f"{self._device.get_name()}_WirelessSensors{sensor_number}SignalLevel"

    @property
    def native_value(self):
        return self._sensor.get_signal_level_text()

    @property
    def extra_state_attributes(self):
        return {"уровень": self._sensor.get_signal_level()}


class WaterCounter(NeptunCounterEntity, SensorEntity):
    _attr_name = "Расход воды"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator, counter):
        super().__init__(coordinator, counter)
        self._attr_unique_id = f"{self._device.get_name()}_Counter{counter.get_address()}"

    @property
    def native_value(self):
        return self._counter.get_value() / 1000


class SupplyVoltage(NeptunEntity, SensorEntity):
    _attr_name = "Питание"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 2
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:flash"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_supply_voltage"

    @property
    def native_value(self):
        return self._device.get_supply_voltage()


class DeviceError(NeptunEntity, SensorEntity):
    _attr_name = "Ошибка"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:alert-octagon-outline"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_device_error_code"

    @property
    def native_value(self):
        errors = self._device.get_error_names()
        if not errors:
            return "Нет"
        return ", ".join(errors)

    @property
    def extra_state_attributes(self):
        return {"код": self._device.get_error_code()}


class ValveHealth(NeptunEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:pipe-valve"

    def __init__(self, coordinator: NeptunSmartCoordinator, group: int, valve: int):
        super().__init__(coordinator)
        self._group = group
        self._valve = valve
        self._attr_unique_id = f"{self._device.get_name()}_valve_status_g{group}_{valve}"
        self._attr_name = f"Кран {valve}, зона {group}"

    @property
    def native_value(self):
        return self._device.get_valve_status_text(self._group, self._valve)

    @property
    def available(self) -> bool:
        if self._group == 2:
            return super().available and self._device.get_dual_group_mode()
        return super().available
