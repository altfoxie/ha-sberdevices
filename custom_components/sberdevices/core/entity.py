"""Base entity helpers for the SberDevices integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from .coordinator import SberDataUpdateCoordinator
from .snapshot import DeviceAttribute, DeviceData, DeviceState, find_by_key


class SberEntity(CoordinatorEntity[SberDataUpdateCoordinator]):
    """Base class for SberDevices entities."""

    def __init__(self, coordinator: SberDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id

        device = self.device
        self._attr_unique_id = device["id"]
        self._attr_name = device["name"]["name"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["serial_number"])},
            name=device["name"]["name"],
            manufacturer=device["device_info"]["manufacturer"],
            model=device["device_info"]["model"],
            sw_version=device["sw_version"],
            serial_number=device["serial_number"],
        )

    @property
    def device(self) -> DeviceData:
        return self.coordinator.data[self._device_id]

    def get_desired_state(self, key: str) -> DeviceState:
        state = find_by_key(self.device["desired_state"], key)
        if state is None:
            raise KeyError(key)
        return state

    def get_state(self, key: str) -> DeviceState:
        return self.get_desired_state(key)

    def get_reported_state(self, key: str) -> DeviceState | None:
        if "reported_state" not in self.device:
            return None
        return find_by_key(self.device["reported_state"], key)

    @property
    def available(self) -> bool:
        if not super().available:
            return False

        online_state = self.get_reported_state("online")
        if online_state is None:
            return True

        online_value = online_state.get("bool_value")
        if isinstance(online_value, bool):
            return online_value

        return True

    def has_attribute(self, key: str) -> bool:
        return find_by_key(self.device["attributes"], key) is not None

    def get_attribute(self, key: str) -> DeviceAttribute:
        attribute = find_by_key(self.device["attributes"], key)
        if attribute is None:
            raise KeyError(key)
        return attribute

    async def async_set_states(self, states: list[DeviceState]) -> None:
        await self.coordinator.gateway_client.set_device_state(self._device_id, states)
        self.coordinator.async_patch_device_state(self._device_id, states)

    async def async_set_on_off(self, state: bool) -> None:
        await self.async_set_states([{"key": "on_off", "bool_value": state}])

    def _update_attrs(self) -> None:
        raise NotImplementedError

    def _handle_coordinator_update(self) -> None:
        self._update_attrs()
        super()._handle_coordinator_update()
