from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_DEVICE_ID, DEFAULT_DEVICE_ID, DOMAIN
from .coordinator import NeptunSmartCoordinator
from .device import NeptunSmart

PLATFORMS = [
    "binary_sensor",
    "button",
    "select",
    "sensor",
    "switch",
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    name = entry.data["name"]
    host_port = entry.data["host_port"]
    host_ip = entry.data["host_ip"]
    device_id = entry.data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)
    device = NeptunSmart(hass, name, host_ip, host_port, device_id)
    try:
        await device.init_sensors()
    except ValueError as ex:
        raise ConfigEntryNotReady(f"Timeout while connecting {host_ip}") from ex

    coordinator = NeptunSmartCoordinator(hass, device)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: NeptunSmartCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.device.async_close()

    return unload_ok
