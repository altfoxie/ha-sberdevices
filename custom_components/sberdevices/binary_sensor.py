"""Support for SberDevices binary sensors (SberBoom detector, online status)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DeviceAPI, HomeAPI
from .const import DOMAIN, SPEAKER_TYPES
from .entity import SberEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    home: HomeAPI = hass.data[DOMAIN][entry.entry_id]["home"]
    entities: list[BinarySensorEntity] = []

    for device in home.get_cached_devices().values():
        if device.get("image_set_type") not in SPEAKER_TYPES:
            continue

        api = DeviceAPI(home, device["id"])

        # Online status sensor
        entities.append(
            SberOnlineSensor(api, suffix="online")
        )

        # Detector (motion/sound) sensor if available
        state_keys = [s["key"] for s in device.get("desired_state", [])]
        if "detector" in state_keys:
            entities.append(
                SberDetectorSensor(api, suffix="detector")
            )

    async_add_entities(entities)


class SberOnlineSensor(SberEntity, BinarySensorEntity):
    """Online status sensor for SberBoom speakers."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, api: DeviceAPI, suffix: str) -> None:
        super().__init__(api)
        self._attr_unique_id = f"{api.device['id']}_{suffix}"
        self._attr_name = f"{api.device['name']['name']} Online"

    async def async_update(self) -> None:
        await super().async_update()
        try:
            self._attr_is_on = self._api.get_state("online")["bool_value"]
        except StopIteration:
            self._attr_is_on = None


class SberDetectorSensor(SberEntity, BinarySensorEntity):
    """Sound/motion detector for SberBoom speakers."""

    _attr_device_class = BinarySensorDeviceClass.SOUND

    def __init__(self, api: DeviceAPI, suffix: str) -> None:
        super().__init__(api)
        self._attr_unique_id = f"{api.device['id']}_{suffix}"
        self._attr_name = f"{api.device['name']['name']} Detector"

    async def async_update(self) -> None:
        await super().async_update()
        try:
            self._attr_is_on = self._api.get_state("detector")["bool_value"]
        except StopIteration:
            self._attr_is_on = None
