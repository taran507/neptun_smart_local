from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import NeptunSmartCoordinator
from .entity import NeptunEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: NeptunSmartCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    if not coordinator.device.is_se():
        return
    async_add_entities([ResetAlarm(coordinator)])


class ResetAlarm(NeptunEntity, ButtonEntity):
    _attr_name = "Сброс аварии"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:alarm-light-off"

    def __init__(self, coordinator: NeptunSmartCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.get_name()}_reset_alarm"

    async def async_press(self) -> None:
        await self._device.reset_alarm()
        await self.coordinator.async_request_refresh()
