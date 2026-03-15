"""Support for SberDevices vacuum cleaners."""

from __future__ import annotations

from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DeviceAPI, HomeAPI
from .const import DOMAIN, VACUUM_TYPES
from .entity import SberEntity

# Mapping Sber API status → HA state
STATUS_MAP = {
    "cleaning": "cleaning",
    "docked": "docked",
    "returning_to_dock": "returning",
    "pause": "paused",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    home: HomeAPI = hass.data[DOMAIN][entry.entry_id]["home"]
    async_add_entities(
        [
            SberVacuumEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if device.get("image_set_type") in VACUUM_TYPES
        ]
    )


class SberVacuumEntity(SberEntity, StateVacuumEntity):
    """SberDevices vacuum cleaner entity (Deerma, Xiaomi via Sber)."""

    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.BATTERY
        | VacuumEntityFeature.STATE
    )

    def _has_state(self, key: str) -> bool:
        try:
            self._api.get_state(key)
            return True
        except StopIteration:
            return False

    async def async_update(self) -> None:
        await super().async_update()

        # Battery
        if self._has_state("battery_percentage"):
            self._attr_battery_level = int(
                self._api.get_state("battery_percentage")["integer_value"]
            )

        # Status
        if self._has_state("vacuum_cleaner_status"):
            raw = self._api.get_state("vacuum_cleaner_status")["enum_value"]
            self._attr_state = STATUS_MAP.get(raw, raw)

    async def async_start(self, **kwargs: Any) -> None:
        await self._api.set_state({"key": "vacuum_cleaner_command", "enum_value": "start"})

    async def async_pause(self, **kwargs: Any) -> None:
        await self._api.set_state({"key": "vacuum_cleaner_command", "enum_value": "pause"})

    async def async_stop(self, **kwargs: Any) -> None:
        await self._api.set_state({"key": "vacuum_cleaner_command", "enum_value": "pause"})

    async def async_return_to_base(self, **kwargs: Any) -> None:
        await self._api.set_state(
            {"key": "vacuum_cleaner_command", "enum_value": "return_to_dock"}
        )
