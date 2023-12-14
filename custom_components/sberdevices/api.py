from datetime import datetime

from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from httpx import AsyncClient

AUTH_ENDPOINT = "https://online.sberbank.ru/CSAFront/oidc/authorize.do"
TOKEN_ENDPOINT = "https://online.sberbank.ru/CSAFront/api/service/oidc/v3/token"


class SberAPI:
    def __init__(self, token: dict = None) -> None:
        self._verify_token = generate_token(64)
        self._oauth_client = AsyncOAuth2Client(
            client_id="b1f0f0c6-fcb0-4ece-8374-6b614ebe3d42",
            authorization_endpoint=TOKEN_ENDPOINT,
            token_endpoint=TOKEN_ENDPOINT,
            redirect_uri="companionapp://host",
            code_challenge_method="S256",
            scope="openid",
            grant_type="authorization_code",
            token=token,
        )

    @property
    def token(self) -> dict[str, any]:
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
        except:
            return False

    async def fetch_home_token(self) -> str:
        return (
            await self._oauth_client.get("https://mp.aihome.dev/v11/smarthome/token")
        ).json()["token"]


class HomeAPI:
    def __init__(self, sber: SberAPI) -> None:
        self._sber = sber
        self._client = AsyncClient(
            base_url="https://gateway.iot.sberdevices.ru/gateway/v1",
        )
        self._token_alive = False
        self._devices = {}

    async def update_token(self) -> None:
        if self._token_alive:
            return

        token = await self._sber.fetch_home_token()
        if token is not None:
            self._client.headers.update({"X-AUTH-jwt": token})

    async def request(
        self, method: str, url: str, retry: bool = True, **kwargs
    ) -> dict[str, any]:
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

    async def get_device_tree(self) -> list[dict[str, any]]:
        return (await self.request("GET", "/device_groups/tree"))["result"]

    # Cache
    async def update_devices_cache(self) -> list[dict[str, any]]:
        self._devices = extract_devices(await self.get_device_tree())

    def get_cached_devices(self) -> list[dict[str, any]]:
        return self._devices

    def get_cached_device(self, device_id: str) -> dict[str, any]:
        return self._devices[device_id]

    async def set_device_state(self, device_id: str, state: [dict[str, any]]) -> None:
        await self._client.request(
            "PUT",
            f"/devices/{device_id}/state",
            json={
                "device_id": device_id,
                "desired_state": state,
                "timestamp": datetime.now().isoformat()
                + "Z",  # 2023-12-01T17:00:35.537Z
            },
        )

        # Merge
        for state_val in state:
            for attribute in self._devices[device_id]["desired_state"]:
                if attribute["key"] == state_val["key"]:
                    attribute.update(state_val)
                    break


class DeviceAPI:
    def __init__(self, home: HomeAPI, device_id: str) -> None:
        self._home = home
        self._id = device_id

    @property
    def device(self) -> dict[str, any]:
        return self._home.get_cached_device(self._id)

    async def update(self) -> None:
        await self._home.update_devices_cache()

    def get_state(self, key: str) -> dict[str, any]:
        return find_from_list(self.device["desired_state"], key)

    def get_attribute(self, key: str) -> dict[str, any]:
        return find_from_list(self.device["attributes"], key)

    async def set_states(self, states: [dict[str, any]]) -> None:
        await self._home.set_device_state(self._id, states)

    async def set_state(self, state: dict[str, any]) -> None:
        await self.set_states([state])

    async def set_state_bool(self, key: str, value: bool) -> None:
        await self.set_state({"key": key, "bool_value": value})

    async def set_state_integer(self, key: str, value: int) -> None:
        await self.set_state({"key": key, "integer_value": value})

    async def set_on_off(self, state: bool) -> None:
        await self.set_state_bool("on_off", state)


def find_from_list(data: [dict[str, any]], key: str) -> dict[str, any] | None:
    for item in data:
        if item["key"] == key:
            return item
    return None


def does_exist_in_list(data: [dict[str, any]], key: str) -> bool:
    return find_from_list(data, key) is not None

def extract_devices(d: dict[str, any]) -> list[dict[str, any]]:
    devices: list[dict[str, any]] = {device["id"]: device for device in d)}
    for children in d["children"]:
        devices.extend(extract_devices(children))
    return devices