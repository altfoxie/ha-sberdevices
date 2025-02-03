from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness
from homeassistant.util.scaling import scale_ranged_value_to_int_range

from .api import DeviceAPI, HomeAPI
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
    def should_poll(self) -> bool:
        return True

    async def async_update(self):
        await self._api.update()

    @property
    def unique_id(self) -> str:
        return self._api.device["id"]

    @property
    def name(self) -> str:
        return self._api.device["name"]["name"]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._api.device["serial_number"])},
            name=self.name,
            manufacturer=self._api.device["device_info"]["manufacturer"],
            model=self._api.device["device_info"]["model"],
            sw_version=self._api.device["sw_version"],
            serial_number=self._api.device["serial_number"],
        )

    @property
    def is_on(self) -> bool:
        return self._api.get_state("on_off")["bool_value"]

    async def async_turn_on(self, **kwargs) -> None:
        await self._api.set_on_off(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._api.set_on_off(False)
