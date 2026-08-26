from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .entity import NeptunEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    device = coordinator.device
    switches = [Valve_1_zone(coordinator)]

    if device.get_dual_group_mode():
        switches.append(Valve_2_zone(coordinator))

    switches.extend(
        [
            Floor_washing_mode(coordinator),
            Connecting_wireless_sensors_mode(coordinator),
            Dual_group_mode(coordinator),
            Close_valve_when_lost_sensors_mode(coordinator),
            Lock_buttons(coordinator),
        ]
    )
    async_add_entities(switches)


class Valve_1_zone(NeptunEntity, SwitchEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Valve First Zone"
        self._attr_unique_id = f"{self._device.get_name()}_Valve_1_zone"

    async def async_turn_off(self, **kwargs):
        await self._device.set_first_group_valve_state(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_first_group_valve_state(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_first_group_valve_state()

    @property
    def icon(self):
        return "mdi:pipe-valve"


class Valve_2_zone(NeptunEntity, SwitchEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Valve Second Zone"
        self._attr_unique_id = f"{self._device.get_name()}_Valve_2_zone"

    async def async_turn_off(self, **kwargs):
        await self._device.set_second_group_valve_state(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_second_group_valve_state(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_second_group_valve_state()

    @property
    def available(self) -> bool:
        return super().available and self._device.get_dual_group_mode()

    @property
    def icon(self):
        return "mdi:pipe-valve"


class Floor_washing_mode(NeptunEntity, SwitchEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Floor Washing Mode"
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


class Connecting_wireless_sensors_mode(NeptunEntity, SwitchEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Connecting wireless sensors mode"
        self._attr_unique_id = f"{self._device.get_name()}_Connecting_wireless_sensors_mode"
        self._attr_entity_category = EntityCategory.CONFIG

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


class Dual_group_mode(NeptunEntity, SwitchEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Dual group mode"
        self._attr_unique_id = f"{self._device.get_name()}_dual_group_mode"
        self._attr_entity_category = EntityCategory.CONFIG

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


class Close_valve_when_lost_sensors_mode(NeptunEntity, SwitchEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Close valve when lost sensors"
        self._attr_unique_id = f"{self._device.get_name()}_Close_valve_when_lost_sensors_mode"
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_turn_off(self, **kwargs):
        await self._device.set_close_valve_when_lost_sensors_mode(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._device.set_close_valve_when_lost_sensors_mode(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        return self._device.get_close_valve_when_lost_sensors_mode()

    @property
    def icon(self):
        return "mdi:pipe-valve"


class Lock_buttons(NeptunEntity, SwitchEntity):
    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Lock Buttons"
        self._attr_unique_id = f"{self._device.get_name()}_Lock_buttons"
        self._attr_entity_category = EntityCategory.CONFIG

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
