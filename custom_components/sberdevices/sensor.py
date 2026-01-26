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
            SberTempSensorEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if "cat_sensor_temp_humidity" in device["image_set_type"]
        ]
    )
    async_add_entities(
        [
            SberHumiditySensorEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if "cat_sensor_temp_humidity" in device["image_set_type"]
        ]
    )

class SberTempSensorEntity(SberSensorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"
    
    def __init__(self, api: DeviceAPI) -> None:
        self._id = api.device["id"]
        self._api = api

    @property
    def unique_id(self) -> str:
        return self._api.device["id"] + "_temperature"

    @property
    def native_value(self) -> float | None:
        return float(super()._get_reported_state_value("temperature")["float_value"])

class SberHumiditySensorEntity(SberSensorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:water"
    
    def __init__(self, api: DeviceAPI) -> None:
        self._id = api.device["id"]
        self._api = api

    @property
    def unique_id(self) -> str:
        return self._api.device["id"] + "_humidity"

    @property
    def native_value(self) -> float | None:
        return float(super()._get_reported_state_value("humidity")["float_value"])
