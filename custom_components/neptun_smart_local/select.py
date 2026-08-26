from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .device import WirelessSensor
from .entity import NeptunEntity

LINE_TYPE_OPTIONS = ["Sensor", "Button"]
LINE_GROUP_OPTIONS = ["First", "Second", "Both"]
RELAY_OPTIONS = ["Not Switch", "First group", "Second group", "Both group"]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device
    selects = []
    for i in 1, 2, 3, 4:
        selects.append(LineTypeConfig(coordinator, line_number=i))
        if device.get_dual_group_mode():
            selects.append(LineGroupConfig(coordinator, line_number=i))
    selects.append(RelaySwitchWhenCloseValve(coordinator))
    selects.append(RelaySwitchWhenAlert(coordinator))
    if device.get_dual_group_mode():
        for i, sensor in enumerate(device.wireless_sensors, start=1):
            selects.append(WirelessSensorGroupConfig(coordinator, sensor, i))
    async_add_entities(selects)


def _line_type_option(is_button: bool) -> str:
    return "Button" if is_button else "Sensor"


def _group_option(state: int) -> str:
    if state == 1:
        return "First"
    if state == 2:
        return "Second"
    return "Both"


def _relay_option(state: int) -> str:
    if state == 0:
        return "Not Switch"
    if state == 1:
        return "First group"
    if state == 2:
        return "Second group"
    return "Both group"


class LineTypeConfig(NeptunEntity, SelectEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator, line_number):
        super().__init__(coordinator)
        self._line_number = line_number
        self._attr_unique_id = f"{self._device.get_name()}_Line_{self._line_number}_config"
        self._attr_name = f"Line {self._line_number} type"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = LINE_TYPE_OPTIONS

    async def async_select_option(self, option: str) -> None:
        await self._device.set_line_type(self._line_number, option != "Sensor")
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _line_type_option(self._device.get_line_config_type(self._line_number))


class LineGroupConfig(NeptunEntity, SelectEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator, line_number):
        super().__init__(coordinator)
        self._line_number = line_number
        self._attr_unique_id = f"{self._device.get_name()}_Line_{self._line_number}_group_ config"
        self._attr_name = f"Line {self._line_number} group"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = LINE_GROUP_OPTIONS

    async def async_select_option(self, option: str) -> None:
        if option == "First":
            state = 1
        elif option == "Second":
            state = 2
        else:
            state = 3
        await self._device.set_line_group(self._line_number, state)
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _group_option(self._device.get_line_group(line_number=self._line_number))

    @property
    def available(self) -> bool:
        return super().available and self._device.get_dual_group_mode()


class RelaySwitchWhenCloseValve(NeptunEntity, SelectEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_RelaySwitchWhenCloseValve_config"
        self._attr_name = "Switch relay when close valve"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = RELAY_OPTIONS

    async def async_select_option(self, option: str) -> None:
        if option == "Not Switch":
            state = 0
        elif option == "First group":
            state = 1
        elif option == "Second group":
            state = 2
        else:
            state = 3
        await self._device.set_relay_config_valve(state)
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _relay_option(self._device.get_relay_config_valve())


class RelaySwitchWhenAlert(NeptunEntity, SelectEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_RelaySwitchAlert_config"
        self._attr_name = "Switch relay when alert"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = RELAY_OPTIONS

    async def async_select_option(self, option: str) -> None:
        if option == "Not Switch":
            state = 0
        elif option == "First group":
            state = 1
        elif option == "Second group":
            state = 2
        else:
            state = 3
        await self._device.set_relay_config_alert(state)
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _relay_option(self._device.get_relay_config_alert())


class WirelessSensorGroupConfig(NeptunEntity, SelectEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator, sensor: WirelessSensor, sensor_number):
        super().__init__(coordinator)
        self._sensor = sensor
        self._sensor_number = sensor_number
        self._attr_unique_id = f"{self._device.get_name()}_WirelessSensor{self._sensor.get_address()}_group_ config"
        self._attr_name = f"Wireless Sensor {self._sensor_number} group"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = LINE_GROUP_OPTIONS

    async def async_select_option(self, option: str) -> None:
        if option == "First":
            state = 1
        elif option == "Second":
            state = 2
        else:
            state = 3
        await self._sensor.set_group_config(state)
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _group_option(self._sensor.get_group_config())
