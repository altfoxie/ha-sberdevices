"""Runtime data for the SberDevices integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .auth import SberAuthClient
from .coordinator import SberDataUpdateCoordinator
from .gateway import SberHomeGatewayClient


@dataclass(slots=True)
class SberRuntimeData:
    """Runtime resources bound to a config entry."""

    auth_client: SberAuthClient
    gateway_client: SberHomeGatewayClient
    coordinator: SberDataUpdateCoordinator

    async def async_close(self) -> None:
        await self.gateway_client.async_close()
        await self.auth_client.async_close()

    @property
    def sber_api(self) -> SberAuthClient:
        return self.auth_client

    @property
    def home_api(self) -> SberHomeGatewayClient:
        return self.gateway_client


type SberConfigEntry = ConfigEntry[SberRuntimeData]
