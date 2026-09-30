from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .entity import NeptunEntity, NeptunLineEntity, NeptunWirelessEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device
    binary_sensors = [
        SystemAlarm(coordinator),
        ZoneLeak(coordinator, 1),
        ZoneLeak(coordinator, 2),
        WirelessBatteryLowAny(coordinator),
        WirelessLostAny(coordinator),
    ]
    for i in 1, 2, 3, 4:
        binary_sensors.append(LineLeak(coordinator, i))
    for i, sensor in enumerate(device.wireless_sensors, start=1):
        binary_sensors.append(WirelessLeak(coordinator, i, sensor))
        binary_sensors.append(WirelessBatteryLow(coordinator, i, sensor))
        binary_sensors.append(WirelessLost(coordinator, i, sensor))
    if device.is_se():
        binary_sensors.extend(
            [
                SupplyVoltageProblem(coordinator),
                Microleak(coordinator),
                ZoneClosedLostSensor(coordinator, 1),
                ZoneClosedLostSensor(coordinator, 2),
            ]
        )
        for i in 1, 2, 3, 4:
            binary_sensors.append(LineProblem(coordinator, i))
    async_add_entities(binary_sensors)

    known_sensors = len(device.wireless_sensors)

    def add_new_wireless_sensors():
        nonlocal known_sensors
        new_sensors = device.wireless_sensors[known_sensors:]
        if not new_sensors:
            return
        entities = []
        for number, sensor in enumerate(new_sensors, start=known_sensors + 1):
            entities.extend((
                WirelessLeak(coordinator, number, sensor),
                WirelessBatteryLow(coordinator, number, sensor),
                WirelessLost(coordinator, number, sensor),
            ))
        known_sensors += len(new_sensors)
        async_add_entities(entities)

    config_entry.async_on_unload(coordinator.async_add_listener(add_new_wireless_sensors))


class SystemAlarm(NeptunEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Авария"
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = self._device.get_name()

    @property
    def extra_state_attributes(self):
        if not self._device.is_se():
            return None
        attrs = {
            "код_ошибки": self._device.get_error_code(),
            "ошибки": self._device.get_error_names(),
        }
        attrs.update(self._device.get_expansion_modules())
        return attrs

    @property
    def is_on(self) -> bool:
        return bool(self._device.get_first_group_alarm() or self._device.get_second_group_alarm())


class ZoneLeak(NeptunEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: NeptunSmartCoordinator, zone: int):
        super().__init__(coordinator)
        self._zone = zone
        if zone == 1:
            self._attr_unique_id = f"{self._device.get_name()}_first_group_alarm_module_alert"
            self._attr_name = "Протечка, зона 1"
        else:
            self._attr_unique_id = f"{self._device.get_name()}_second_group_alarm_module_alert"
            self._attr_name = "Протечка, зона 2"

    @property
    def available(self) -> bool:
        if self._zone == 2:
            return super().available and self._device.get_dual_group_mode()
        return super().available

    @property
    def is_on(self) -> bool:
        if self._zone == 1:
            return self._device.get_first_group_alarm()
        return self._device.get_second_group_alarm()


class WirelessBatteryLowAny(NeptunEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_name = "Разряд радиодатчиков"
    _attr_icon = "mdi:battery"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_discharge_wireless_sensors"

    @property
    def is_on(self) -> bool:
        return self._device.get_discharge_wireless_sensors()


class WirelessLostAny(NeptunEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Потеря радиодатчиков"
    _attr_icon = "mdi:wifi-off"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_lost_wireless_sensors"

    @property
    def is_on(self) -> bool:
        return self._device.get_lost_wireless_sensors()


class LineLeak(NeptunLineEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_name = "Протечка"
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: NeptunSmartCoordinator, line_number):
        super().__init__(coordinator, line_number)
        self._attr_unique_id = f"{self._device.get_name()}_WiredAlertStatus_line{line_number}"

    @property
    def is_on(self) -> bool:
        return self._device.get_line_status(line_number=self._line_number)


class WirelessLeak(NeptunWirelessEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_name = "Протечка"
    _attr_icon = "mdi:water"

    def __init__(self, coordinator, sensor_number, sensor):
        super().__init__(coordinator, sensor_number, sensor)
        self._attr_unique_id = f"{self._device.get_name()}_WirelessAlertStatus_sensor{sensor_number}"

    @property
    def is_on(self) -> bool:
        return self._sensor.get_alert_status()


class WirelessBatteryLow(NeptunWirelessEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_name = "Разряд"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:battery"

    def __init__(self, coordinator, sensor_number, sensor):
        super().__init__(coordinator, sensor_number, sensor)
        self._attr_unique_id = f"{self._device.get_name()}_WirelessDischargeStatus_sensor{sensor_number}"

    @property
    def is_on(self) -> bool:
        return self._sensor.get_discharge_status()


class WirelessLost(NeptunWirelessEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Потеря связи"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:wifi-off"

    def __init__(self, coordinator, sensor_number, sensor):
        super().__init__(coordinator, sensor_number, sensor)
        self._attr_unique_id = f"{self._device.get_name()}_WirelessLostStatus_sensor{sensor_number}"

    @property
    def is_on(self) -> bool:
        return self._sensor.get_lost_sensor_status()


class SupplyVoltageProblem(NeptunEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Проблема питания"
    _attr_icon = "mdi:flash-alert"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_supply_voltage_problem"

    @property
    def is_on(self) -> bool:
        return self._device.get_supply_voltage_problem()


class Microleak(NeptunEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_name = "Микропротечка"
    _attr_icon = "mdi:water-alert"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_elp_leak"

    @property
    def is_on(self) -> bool:
        return self._device.get_elp_leak()


class ZoneClosedLostSensor(NeptunEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:pipe-disconnected"

    def __init__(self, coordinator: NeptunSmartCoordinator, zone: int):
        super().__init__(coordinator)
        self._zone = zone
        if zone == 1:
            self._attr_unique_id = f"{self._device.get_name()}_first_group_closed_lost_sensor"
            self._attr_name = "Зона 1 закрыта из-за потери датчика"
        else:
            self._attr_unique_id = f"{self._device.get_name()}_second_group_closed_lost_sensor"
            self._attr_name = "Зона 2 закрыта из-за потери датчика"

    @property
    def available(self) -> bool:
        if self._zone == 2:
            return super().available and self._device.get_dual_group_mode()
        return super().available

    @property
    def is_on(self) -> bool:
        return self._device.get_group_closed_lost_sensor(self._zone)


class LineProblem(NeptunLineEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Неисправность"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: NeptunSmartCoordinator, line_number):
        super().__init__(coordinator, line_number)
        self._attr_unique_id = f"{self._device.get_name()}_WiredLineProblem_line{line_number}"

    @property
    def is_on(self) -> bool:
        return self._device.get_wired_line_error(self._line_number) != 0

    @property
    def extra_state_attributes(self):
        return {"ошибка": self._device.get_wired_line_error_text(self._line_number)}
