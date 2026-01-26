from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import PERCENTAGE, UnitOfTemperature
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
            SberWaterLeakSensorEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if "dt_sensor_water_leak" in device["image_set_type"]
        ]
    )
    async_add_entities(
        [
            SberDoorSensorEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if "cat_sensor_door" in device["image_set_type"]
        ]
    )

class SberWaterLeakSensorEntity(SberSensorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_icon = "mdi:water"
    
    def __init__(self, api: DeviceAPI) -> None:
        self._id = api.device["id"]
        self._api = api

    @property
    def is_on(self) -> bool | None:
        return bool(super()._get_reported_state_value("water_leak_state")["bool_value"])

class SberDoorSensorEntity(SberSensorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_icon = "mdi:door" 
    
    def __init__(self, api: DeviceAPI) -> None:
        self._id = api.device["id"]
        self._api = api

    @property
    def is_on(self) -> bool | None:
        return bool(super()._get_reported_state_value("doorcontact_state")["bool_value"])
