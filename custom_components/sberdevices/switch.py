from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness
from homeassistant.util.scaling import scale_ranged_value_to_int_range

from .api import DeviceAPI, HomeAPI
from .entity import SberSensorEntity
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    home: HomeAPI = hass.data[DOMAIN][entry.entry_id]["home"]
    await home.update_devices_cache()
    async_add_entities(
        [
            SberSwitchEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if "dt_socket_sber" in device["image_set_type"]
        ]
    )


class SberSwitchEntity(SwitchEntity):
    def __init__(self, api: DeviceAPI) -> None:
        self._id = api.device["id"]
        self._api = api

    @property
    def is_on(self) -> bool:
        return super()._get_reported_state_value("on_off")["bool_value"]
