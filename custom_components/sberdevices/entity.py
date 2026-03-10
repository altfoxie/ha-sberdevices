"""Base entity for SberDevices integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .api import DeviceAPI
from .const import DOMAIN


class SberEntity(Entity):
    """Base class for SberDevices entities."""

    _attr_should_poll = True

    def __init__(self, api: DeviceAPI) -> None:
        self._api = api
        self._attr_unique_id = api.device["id"]
        self._attr_name = api.device["name"]["name"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, api.device["serial_number"])},
            name=api.device["name"]["name"],
            manufacturer=api.device["device_info"]["manufacturer"],
            model=api.device["device_info"]["model"],
            sw_version=api.device["sw_version"],
            serial_number=api.device["serial_number"],
        )

    async def async_update(self) -> None:
        await self._api.update()
