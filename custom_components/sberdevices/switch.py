"""Support for SberDevices switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DeviceAPI, HomeAPI
from .const import DOMAIN, SWITCH_TYPES
from .entity import SberEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    home: HomeAPI = hass.data[DOMAIN][entry.entry_id]["home"]
    async_add_entities(
        [
            SberSwitchEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if any(t in device["image_set_type"] for t in SWITCH_TYPES)
        ]
    )


class SberSwitchEntity(SberEntity, SwitchEntity):
    async def async_update(self) -> None:
        await super().async_update()
        self._attr_is_on = self._api.get_state("on_off")["bool_value"]
        self._attr_extra_state_attributes = self._compute_extra_attributes()

    async def async_turn_on(self, **kwargs) -> None:
        await self._api.set_on_off(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._api.set_on_off(False)

    def _get_reported_state_value(self, key: str) -> dict[str, Any] | None:
        if "reported_state" not in self._api.device:
            return None

        for state in self._api.device["reported_state"]:
            if state["key"] == key:
                return state
        return None

    def _compute_extra_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {}

        for attr_name in ("cur_voltage", "cur_current", "cur_power"):
            state = self._get_reported_state_value(attr_name)
            if not state:
                continue

            if state["type"] == "FLOAT":
                attributes[attr_name] = state["float_value"]
            elif state["type"] == "INTEGER":
                if attr_name == "cur_current":
                    # Convert current from mA to A
                    attributes[attr_name] = float(state["integer_value"]) / 1000
                else:
                    attributes[attr_name] = state["integer_value"]

        return attributes
