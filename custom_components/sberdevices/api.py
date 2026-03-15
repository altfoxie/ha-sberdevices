from __future__ import annotations

import logging
import ssl
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from httpx import AsyncClient

from .const import (
    AUTH_ENDPOINT,
    COMPANION_TOKEN_URL,
    GATEWAY_BASE_URL,
    OAUTH_CLIENT_ID,
    TOKEN_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


def extract_devices(d: dict[str, Any]) -> dict[str, Any]:
    devices: dict[str, Any] = {device["id"]: device for device in d["devices"]}
    for children in d["children"]:
        devices.update(extract_devices(children))
    return devices


_ROOT_CA_PATH = Path(__file__).parent / "russian_trusted_root_ca.pem"


def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cafile=str(_ROOT_CA_PATH))
    return ctx


_SSL_CONTEXT = _create_ssl_context()


class SberAPI:
    def __init__(self, token: dict | None = None) -> None:
        self._verify_token = generate_token(64)
        self._oauth_client = AsyncOAuth2Client(
            client_id=OAUTH_CLIENT_ID,
            authorization_endpoint=TOKEN_ENDPOINT,
            token_endpoint=TOKEN_ENDPOINT,
            redirect_uri="companionapp://host",
            code_challenge_method="S256",
            scope="openid",
            grant_type="authorization_code",
            token=token,
            verify=_SSL_CONTEXT,
        )

    @property
    def token(self) -> dict[str, Any]:
        return self._oauth_client.token

    def create_authorization_url(self) -> str:
        return self._oauth_client.create_authorization_url(
            AUTH_ENDPOINT,
            nonce=generate_token(),
            code_verifier=self._verify_token,
        )[0]

    async def authorize_by_url(self, url: str) -> bool:
        try:
            token = await self._oauth_client.fetch_token(
                TOKEN_ENDPOINT,
                authorization_response=url,
                code_verifier=self._verify_token,
            )
            return token is not None
        except Exception:
            _LOGGER.exception("Failed to authorize by URL")
            return False

    async def fetch_home_token(self) -> str:
        return (
            await self._oauth_client.get(
                COMPANION_TOKEN_URL,
                headers={"User-Agent": "Salute+prod%2F24.08.1.15602+%28Android+34%3B+Google+sdk_gphone64_arm64%29"},
            )
        ).json()["token"]


class HomeAPI:
    def __init__(self, sber: SberAPI) -> None:
        self._sber = sber
        self._client = AsyncClient(
            base_url=GATEWAY_BASE_URL,
        )
        self._token_alive = False
        self._cached_devices: dict[str, Any] = {}

    async def update_token(self) -> None:
        if self._token_alive:
            return

        token = await self._sber.fetch_home_token()
        if token is not None:
            self._client.headers.update({"X-AUTH-jwt": token})
            self._token_alive = True

    async def request(self, method: str, url: str, retry: bool = True, **kwargs) -> dict[str, Any]:
        await self.update_token()

        res = await self._client.request(method, url, **kwargs)
        obj = res.json()
        if res.status_code != 200:
            code = obj["code"]
            # dead token xd
            if code == 16:
                self._token_alive = False
                if retry:
                    return await self.request(method, url, retry=False, **kwargs)

            raise Exception(f"{code} ({res.status_code}): {obj['message']}")
        return obj

    async def get_device_tree(self) -> dict[str, Any]:
        return (await self.request("GET", "/device_groups/tree"))["result"]

    async def get_all_devices(self) -> list[dict[str, Any]]:
        """Fetch all devices from /devices (includes SberBoom, TV, vacuum, etc.)."""
        res = await self.request("GET", "/devices")
        if isinstance(res, list):
            return res
        return res.get("result", [])

    # Cache
    async def update_devices_cache(self):
        # Merge devices from both endpoints: tree (IoT) + flat list (all)
        device_data = await self.get_device_tree()
        self._cached_devices = extract_devices(device_data)

        try:
            all_devices = await self.get_all_devices()
            for device in all_devices:
                if device["id"] not in self._cached_devices:
                    self._cached_devices[device["id"]] = device
        except Exception:
            _LOGGER.warning("Failed to fetch /devices, using tree only")

    def get_cached_devices(self) -> dict[str, Any]:
        return self._cached_devices

    def get_cached_device(self, device_id: str) -> dict[str, Any]:
        return self._cached_devices[device_id]

    async def set_device_state(self, device_id: str, state: list[dict[str, Any]]) -> None:
        await self.request(
            "PUT",
            f"/devices/{device_id}/state",
            json={
                "device_id": device_id,
                "desired_state": state,
                "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            },
        )

        # Merge
        for state_val in state:
            for attribute in self._cached_devices[device_id]["desired_state"]:
                if attribute["key"] == state_val["key"]:
                    attribute.update(state_val)
                    break


class DeviceAPI:
    def __init__(self, home: HomeAPI, device_id: str) -> None:
        self._home = home
        self._id = device_id

    @property
    def device(self) -> dict[str, Any]:
        return self._home.get_cached_device(self._id)

    async def update(self) -> None:
        await self._home.update_devices_cache()

    def get_state(self, key: str) -> dict[str, Any]:
        return next(item for item in self.device["desired_state"] if item["key"] == key)

    def has_attribute(self, key: str) -> bool:
        return any(item["key"] == key for item in self.device["attributes"])

    def get_attribute(self, key: str) -> dict[str, Any]:
        return next(item for item in self.device["attributes"] if item["key"] == key)

    async def set_states(self, states: list[dict[str, Any]]) -> None:
        await self._home.set_device_state(self._id, states)

    async def set_state(self, state: dict[str, Any]) -> None:
        await self.set_states([state])

    async def set_state_bool(self, key: str, value: bool) -> None:
        await self.set_state({"key": key, "bool_value": value})

    async def set_state_integer(self, key: str, value: int) -> None:
        await self.set_state({"key": key, "integer_value": value})

    async def set_on_off(self, state: bool) -> None:
        await self.set_state_bool("on_off", state)
