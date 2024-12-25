"""The SberDevices integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import HomeAPI, SberAPI
from .const import DOMAIN
import logging

PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SberDevices from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    sber = SberAPI(token=entry.data["token"])
    home = HomeAPI(sber)
    hass.data[DOMAIN][entry.entry_id] = {
        "sber": sber,
        "home": home,
    }

    # Обновим кэш устройств
    await home.update_devices_cache()
    # Выведем список устройств в лог
    _LOGGER.warning("All devices: %s", list(home.get_cached_devices().values()))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok