"""Data coordinator for the SberDevices integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import COORDINATOR_UPDATE_INTERVAL, DOMAIN
from .gateway import SberHomeGatewayClient
from .snapshot import DeviceCache, DeviceState, apply_device_state_patch

_LOGGER = logging.getLogger(__name__)


class SberDataUpdateCoordinator(DataUpdateCoordinator[DeviceCache]):
    """Coordinate polling device state from SberDevices."""

    def __init__(self, hass: HomeAssistant, gateway_client: SberHomeGatewayClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=COORDINATOR_UPDATE_INTERVAL,
        )
        self.gateway_client = gateway_client

    @property
    def home_api(self) -> SberHomeGatewayClient:
        return self.gateway_client

    async def _async_update_data(self) -> DeviceCache:
        try:
            return await self.gateway_client.get_devices()
        except Exception as err:
            raise UpdateFailed(f"Error fetching {DOMAIN} devices: {err}") from err

    def async_patch_device_state(self, device_id: str, state: list[DeviceState]) -> None:
        """Publish an optimistic update into coordinator.data."""
        apply_device_state_patch(self.data[device_id], state)
        self.async_set_updated_data(self.data)


SberDevicesDataUpdateCoordinator = SberDataUpdateCoordinator
