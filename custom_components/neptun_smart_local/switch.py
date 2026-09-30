from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .entity import NeptunEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device
    switches = [
        FloorWashing(coordinator),
        PairWirelessSensors(coordinator),
        DualZoneMode(coordinator),
        CloseOnLostSensor(coordinator),
        LockButtons(coordinator),
    ]
    if device.is_se():
        switches.extend(
            [
                CloseOnLowVoltage(coordinator),
                SensorFeedback(coordinator),
                MicroleakMode(coordinator),
                CloseOnMicroleak(coordinator),
            ]
        )
    async_add_entities(switches)


class FloorWashing(NeptunEntity, SwitchEntity):
    _attr_name = "Мойка пола"
    _attr_icon = "mdi:pail"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_Floor_washing_mode"

    async def async_turn_off(self, **kwargs):
        await self._device.set_floor_washing_mode(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_floor_washing_mode(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_floor_washing_mode()

    @property
    def icon(self):
        if self._device.get_floor_washing_mode():
            return "mdi:pail"
        return "mdi:pail-off"


class PairWirelessSensors(NeptunEntity, SwitchEntity):
    _attr_name = "Регистрация радиодатчиков"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:router-wireless"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_Connecting_wireless_sensors_mode"

    async def async_turn_off(self, **kwargs):
        await self._device.set_connecting_wireless_sensors_mode(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_connecting_wireless_sensors_mode(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_connecting_wireless_sensors_mode()

    @property
    def icon(self):
        if self._device.get_connecting_wireless_sensors_mode():
            return "mdi:router-wireless"
        return "mdi:router-wireless-off"


class DualZoneMode(NeptunEntity, SwitchEntity):
    _attr_name = "Две зоны"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:numeric-2-circle-outline"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_dual_group_mode"

    async def async_turn_off(self, **kwargs):
        await self._device.set_dual_group_mode(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_dual_group_mode(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_dual_group_mode()

    @property
    def icon(self):
        if self._device.get_dual_group_mode():
            return "mdi:numeric-2-circle-outline"
        return "mdi:numeric-1-circle-outline"


class CloseOnLostSensor(NeptunEntity, SwitchEntity):
    _attr_name = "Закрывать при потере датчика"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:pipe-valve"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_Close_valve_when_lost_sensors_mode"

    async def async_turn_off(self, **kwargs):
        await self._device.set_close_valve_when_lost_sensors_mode(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_close_valve_when_lost_sensors_mode(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_close_valve_when_lost_sensors_mode()


class LockButtons(NeptunEntity, SwitchEntity):
    _attr_name = "Блокировка кнопок"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_Lock_buttons"

    async def async_turn_off(self, **kwargs):
        await self._device.set_lock_buttons(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_lock_buttons(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_lock_buttons()

    @property
    def icon(self):
        if self._device.get_lock_buttons():
            return "mdi:keyboard-off-outline"
        return "mdi:keyboard-close-outline"


class CloseOnLowVoltage(NeptunEntity, SwitchEntity):
    _attr_name = "Закрывать при низком напряжении"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:flash-alert"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_Close_valve_when_low_voltage"

    async def async_turn_off(self, **kwargs):
        await self._device.set_close_valve_when_low_voltage(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_close_valve_when_low_voltage(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_close_valve_when_low_voltage()


class SensorFeedback(NeptunEntity, SwitchEntity):
    _attr_name = "Контроль проводных датчиков"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:transit-connection-variant"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_sensor_feedback"

    async def async_turn_off(self, **kwargs):
        await self._device.set_sensor_feedback(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_sensor_feedback(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_sensor_feedback()


class MicroleakMode(NeptunEntity, SwitchEntity):
    _attr_name = "Контроль микропротечек"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:water-check"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_elp_mode"

    async def async_turn_off(self, **kwargs):
        await self._device.set_elp_mode(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_elp_mode(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_elp_mode()


class CloseOnMicroleak(NeptunEntity, SwitchEntity):
    _attr_name = "Закрывать при микропротечке"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:pipe-valve"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_close_on_elp"

    async def async_turn_off(self, **kwargs):
        await self._device.set_close_on_elp(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_close_on_elp(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_close_on_elp()
