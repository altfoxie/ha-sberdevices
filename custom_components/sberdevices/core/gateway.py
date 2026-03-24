"""Gateway client helpers for the SberDevices integration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from httpx import AsyncClient

from ..const import GATEWAY_BASE_URL
from .auth import SBER_SSL_CONTEXT, SberAuthClient
from .snapshot import DeviceCache, DeviceState, DeviceTreeNode, extract_devices

type GatewayPayload = dict[str, Any]


def _decode_device_tree_response(payload: GatewayPayload) -> DeviceTreeNode:
    """Extract the typed device tree from the raw gateway payload."""
    return payload["result"]


class SberHomeGatewayClient:
    """Gateway client for Sber smart-home APIs."""

    def __init__(self, auth_client: SberAuthClient) -> None:
        self._auth_client = auth_client
        self._client = AsyncClient(base_url=GATEWAY_BASE_URL, verify=SBER_SSL_CONTEXT)
        self._has_gateway_token = False

    async def async_close(self) -> None:
        await self._client.aclose()

    async def _ensure_gateway_token(self) -> None:
        if self._has_gateway_token:
            return

        token = await self._auth_client.fetch_gateway_token()
        if token is not None:
            self._client.headers.update({"X-AUTH-jwt": token})
            self._has_gateway_token = True

    async def update_token(self) -> None:
        await self._ensure_gateway_token()

    async def _request(self, method: str, url: str, retry: bool = True, **kwargs: Any) -> GatewayPayload:
        await self._ensure_gateway_token()

        res = await self._client.request(method, url, **kwargs)
        payload = res.json()
        if res.status_code != 200:
            code = payload["code"]
            if code == 16:
                self._has_gateway_token = False
                if retry:
                    return await self._request(method, url, retry=False, **kwargs)

            raise Exception(f"{code} ({res.status_code}): {payload['message']}")
        return payload

    async def request(self, method: str, url: str, retry: bool = True, **kwargs: Any) -> GatewayPayload:
        return await self._request(method, url, retry=retry, **kwargs)

    async def get_device_tree(self) -> DeviceTreeNode:
        return _decode_device_tree_response(await self._request("GET", "/device_groups/tree"))

    async def get_devices(self) -> DeviceCache:
        return extract_devices(await self.get_device_tree())

    async def async_get_devices(self) -> DeviceCache:
        return await self.get_devices()

    async def set_device_state(self, device_id: str, state: list[DeviceState]) -> None:
        await self._request(
            "PUT",
            f"/devices/{device_id}/state",
            json={
                "device_id": device_id,
                "desired_state": state,
                "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            },
        )


HomeAPI = SberHomeGatewayClient
