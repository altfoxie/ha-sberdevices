"""Support for SberDevices switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SWITCH_TYPES
from .core.coordinator import SberDataUpdateCoordinator
from .core.entity import SberEntity
from .core.runtime import SberConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: SberConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime_data = entry.runtime_data
    async_add_entities(
        [
            SberSwitchEntity(runtime_data.coordinator, device["id"])
            for device in runtime_data.coordinator.data.values()
            if any(t in device["image_set_type"] for t in SWITCH_TYPES)
        ]
    )


class SberSwitchEntity(SberEntity, SwitchEntity):
    def __init__(self, coordinator: SberDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._update_attrs()

    def _update_attrs(self) -> None:
        self._attr_is_on = self.get_desired_state("on_off")["bool_value"]
        self._attr_extra_state_attributes = self._compute_extra_attributes()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_set_on_off(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_on_off(False)

    def _compute_extra_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {}

        for attr_name in ("cur_voltage", "cur_current", "cur_power"):
            state = self.get_reported_state(attr_name)
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
