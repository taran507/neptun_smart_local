from __future__ import annotations

from homeassistant.components.valve import ValveDeviceClass, ValveEntity, ValveEntityFeature
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .entity import NeptunEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    registry = er.async_get(hass)
    for zone in (1, 2):
        unique_id = f"{coordinator.device.get_name()}_Valve_{zone}_zone"
        old_entity_id = registry.async_get_entity_id("switch", DOMAIN, unique_id)
        if old_entity_id and registry.async_get(old_entity_id).config_entry_id == config_entry.entry_id:
            registry.async_remove(old_entity_id)
    async_add_entities([ZoneValve(coordinator, 1), ZoneValve(coordinator, 2)])


class ZoneValve(NeptunEntity, ValveEntity):
    _attr_icon = "mdi:pipe-valve"
    _attr_device_class = ValveDeviceClass.WATER
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    _attr_reports_position = False

    def __init__(self, coordinator: NeptunSmartCoordinator, zone: int):
        super().__init__(coordinator)
        self._zone = zone
        self._attr_name = f"Кран, зона {zone}"
        self._attr_unique_id = f"{self._device.get_name()}_Valve_{zone}_zone"

    async def async_close_valve(self) -> None:
        if self._zone == 1:
            await self._device.set_first_group_valve_state(False)
        else:
            await self._device.set_second_group_valve_state(False)
        await self.coordinator.async_request_refresh()

    async def async_open_valve(self) -> None:
        if self._zone == 1:
            await self._device.set_first_group_valve_state(True)
        else:
            await self._device.set_second_group_valve_state(True)
        await self.coordinator.async_request_refresh()

    @property
    def is_closed(self) -> bool:
        if self._zone == 1:
            return not self._device.get_first_group_valve_state()
        return not self._device.get_second_group_valve_state()

    @property
    def available(self) -> bool:
        if self._zone == 2:
            return super().available and self._device.get_dual_group_mode()
        return super().available