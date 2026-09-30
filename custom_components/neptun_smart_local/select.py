from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .entity import NeptunEntity, NeptunLineEntity, NeptunWirelessEntity

LINE_TYPE_OPTIONS = ["Датчик", "Кнопка"]
LINE_TYPE_OPTIONS_SE = ["Датчик", "Кнопка", "Ключ"]
ZONE_OPTIONS = ["Зона 1", "Зона 2", "Обе зоны"]
RELAY_OPTIONS = ["Не переключать", "Зона 1", "Зона 2", "Обе зоны"]


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device
    selects = []
    for i in 1, 2, 3, 4:
        selects.append(LineType(coordinator, line_number=i))
        selects.append(LineZone(coordinator, line_number=i))
    selects.append(RelayOnValveClose(coordinator))
    selects.append(RelayOnAlarm(coordinator))
    for i, sensor in enumerate(device.wireless_sensors, start=1):
        selects.append(WirelessZone(coordinator, sensor, i))
    async_add_entities(selects)

    known_sensors = len(device.wireless_sensors)

    def add_new_wireless_sensors():
        nonlocal known_sensors
        new_sensors = device.wireless_sensors[known_sensors:]
        if not new_sensors:
            return
        async_add_entities([
            WirelessZone(coordinator, sensor, number)
            for number, sensor in enumerate(new_sensors, start=known_sensors + 1)
        ])
        known_sensors += len(new_sensors)

    config_entry.async_on_unload(coordinator.async_add_listener(add_new_wireless_sensors))


def _line_type_option(state: int) -> str:
    if int(state) == 2:
        return "Ключ"
    if int(state):
        return "Кнопка"
    return "Датчик"


def _zone_option(state: int) -> str:
    if state == 1:
        return "Зона 1"
    if state == 2:
        return "Зона 2"
    return "Обе зоны"


def _relay_option(state: int) -> str:
    if state == 0:
        return "Не переключать"
    if state == 1:
        return "Зона 1"
    if state == 2:
        return "Зона 2"
    return "Обе зоны"


def _zone_value(option: str) -> int:
    if option == "Зона 1":
        return 1
    if option == "Зона 2":
        return 2
    return 3


def _relay_value(option: str) -> int:
    if option == "Не переключать":
        return 0
    if option == "Зона 1":
        return 1
    if option == "Зона 2":
        return 2
    return 3


class LineType(NeptunLineEntity, SelectEntity):
    _attr_name = "Тип"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:electric-switch"

    def __init__(self, coordinator: NeptunSmartCoordinator, line_number):
        super().__init__(coordinator, line_number)
        self._attr_unique_id = f"{self._device.get_name()}_Line_{self._line_number}_config"
        self._attr_options = LINE_TYPE_OPTIONS_SE if coordinator.device.is_se() else LINE_TYPE_OPTIONS

    async def async_select_option(self, option: str) -> None:
        if option == "Ключ":
            state = 2
        elif option == "Кнопка":
            state = 1
        else:
            state = 0
        await self._device.set_line_type(self._line_number, state)
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _line_type_option(self._device.get_line_config_type(self._line_number))


class LineZone(NeptunLineEntity, SelectEntity):
    _attr_name = "Зона"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:numeric"
    _attr_options = ZONE_OPTIONS

    def __init__(self, coordinator: NeptunSmartCoordinator, line_number):
        super().__init__(coordinator, line_number)
        self._attr_unique_id = f"{self._device.get_name()}_Line_{self._line_number}_group_ config"

    async def async_select_option(self, option: str) -> None:
        await self._device.set_line_group(self._line_number, _zone_value(option))
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _zone_option(self._device.get_line_group(line_number=self._line_number))

    @property
    def available(self) -> bool:
        return super().available and self._device.get_dual_group_mode()


class RelayOnValveClose(NeptunEntity, SelectEntity):
    _attr_name = "Реле при закрытии кранов"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:electric-switch"
    _attr_options = RELAY_OPTIONS

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_RelaySwitchWhenCloseValve_config"

    async def async_select_option(self, option: str) -> None:
        await self._device.set_relay_config_valve(_relay_value(option))
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _relay_option(self._device.get_relay_config_valve())


class RelayOnAlarm(NeptunEntity, SelectEntity):
    _attr_name = "Реле при аварии"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:electric-switch"
    _attr_options = RELAY_OPTIONS

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_RelaySwitchAlert_config"

    async def async_select_option(self, option: str) -> None:
        await self._device.set_relay_config_alert(_relay_value(option))
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _relay_option(self._device.get_relay_config_alert())


class WirelessZone(NeptunWirelessEntity, SelectEntity):
    _attr_name = "Зона"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:numeric"
    _attr_options = ZONE_OPTIONS

    def __init__(self, coordinator, sensor, sensor_number):
        super().__init__(coordinator, sensor_number, sensor)
        self._attr_unique_id = f"{self._device.get_name()}_WirelessSensor{self._sensor.get_address()}_group_ config"

    async def async_select_option(self, option: str) -> None:
        await self._sensor.set_group_config(_zone_value(option))
        await self.coordinator.async_request_refresh()

    @property
    def current_option(self) -> str:
        return _zone_option(self._sensor.get_group_config())

    @property
    def available(self) -> bool:
        return super().available and self._device.get_dual_group_mode()
