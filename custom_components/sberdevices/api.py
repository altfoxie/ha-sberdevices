from datetime import datetime
import tempfile

from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from httpx import AsyncClient, create_ssl_context

AUTH_ENDPOINT = "https://online.sberbank.ru/CSAFront/oidc/authorize.do"
TOKEN_ENDPOINT = "https://online.sberbank.ru:4431/CSAFront/api/service/oidc/v3/token"
# min_cifra_root_ca.cer
ROOT_CA = """-----BEGIN CERTIFICATE-----
MIIFwjCCA6qgAwIBAgICEAAwDQYJKoZIhvcNAQELBQAwcDELMAkGA1UEBhMCUlUx
PzA9BgNVBAoMNlRoZSBNaW5pc3RyeSBvZiBEaWdpdGFsIERldmVsb3BtZW50IGFu
ZCBDb21tdW5pY2F0aW9uczEgMB4GA1UEAwwXUnVzc2lhbiBUcnVzdGVkIFJvb3Qg
Q0EwHhcNMjIwMzAxMjEwNDE1WhcNMzIwMjI3MjEwNDE1WjBwMQswCQYDVQQGEwJS
VTE/MD0GA1UECgw2VGhlIE1pbmlzdHJ5IG9mIERpZ2l0YWwgRGV2ZWxvcG1lbnQg
YW5kIENvbW11bmljYXRpb25zMSAwHgYDVQQDDBdSdXNzaWFuIFRydXN0ZWQgUm9v
dCBDQTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAMfFOZ8pUAL3+r2n
qqE0Zp52selXsKGFYoG0GM5bwz1bSFtCt+AZQMhkWQheI3poZAToYJu69pHLKS6Q
XBiwBC1cvzYmUYKMYZC7jE5YhEU2bSL0mX7NaMxMDmH2/NwuOVRj8OImVa5s1F4U
zn4Kv3PFlDBjjSjXKVY9kmjUBsXQrIHeaqmUIsPIlNWUnimXS0I0abExqkbdrXbX
YwCOXhOO2pDUx3ckmJlCMUGacUTnylyQW2VsJIyIGA8V0xzdaeUXg0VZ6ZmNUr5Y
Ber/EAOLPb8NYpsAhJe2mXjMB/J9HNsoFMBFJ0lLOT/+dQvjbdRZoOT8eqJpWnVD
U+QL/qEZnz57N88OWM3rabJkRNdU/Z7x5SFIM9FrqtN8xewsiBWBI0K6XFuOBOTD
4V08o4TzJ8+Ccq5XlCUW2L48pZNCYuBDfBh7FxkB7qDgGDiaftEkZZfApRg2E+M9
G8wkNKTPLDc4wH0FDTijhgxR3Y4PiS1HL2Zhw7bD3CbslmEGgfnnZojNkJtcLeBH
BLa52/dSwNU4WWLubaYSiAmA9IUMX1/RpfpxOxd4Ykmhz97oFbUaDJFipIggx5sX
ePAlkTdWnv+RWBxlJwMQ25oEHmRguNYf4Zr/Rxr9cS93Y+mdXIZaBEE0KS2iLRqa
OiWBki9IMQU4phqPOBAaG7A+eP8PAgMBAAGjZjBkMB0GA1UdDgQWBBTh0YHlzlpf
BKrS6badZrHF+qwshzAfBgNVHSMEGDAWgBTh0YHlzlpfBKrS6badZrHF+qwshzAS
BgNVHRMBAf8ECDAGAQH/AgEEMA4GA1UdDwEB/wQEAwIBhjANBgkqhkiG9w0BAQsF
AAOCAgEAALIY1wkilt/urfEVM5vKzr6utOeDWCUczmWX/RX4ljpRdgF+5fAIS4vH
tmXkqpSCOVeWUrJV9QvZn6L227ZwuE15cWi8DCDal3Ue90WgAJJZMfTshN4OI8cq
W9E4EG9wglbEtMnObHlms8F3CHmrw3k6KmUkWGoa+/ENmcVl68u/cMRl1JbW2bM+
/3A+SAg2c6iPDlehczKx2oa95QW0SkPPWGuNA/CE8CpyANIhu9XFrj3RQ3EqeRcS
AQQod1RNuHpfETLU/A2gMmvn/w/sx7TB3W5BPs6rprOA37tutPq9u6FTZOcG1Oqj
C/B7yTqgI7rbyvox7DEXoX7rIiEqyNNUguTk/u3SZ4VXE2kmxdmSh3TQvybfbnXV
4JbCZVaqiZraqc7oZMnRoWrXRG3ztbnbes/9qhRGI7PqXqeKJBztxRTEVj8ONs1d
WN5szTwaPIvhkhO3CO5ErU2rVdUr89wKpNXbBODFKRtgxUT70YpmJ46VVaqdAhOZ
D9EUUn4YaeLaS8AjSF/h7UkjOibNc4qVDiPP+rkehFWM66PVnP1Msh93tc+taIfC
EYVMxjh8zNbFuoc7fzvvrFILLe7ifvEIUqSVIC/AzplM/Jxw7buXFeGP1qVCBEHq
391d/9RAfaZ12zkwFsl+IKwE/OZxW8AHa9i1p4GO0YSNuczzEm4=
-----END CERTIFICATE-----""".encode()

with tempfile.NamedTemporaryFile(delete_on_close=False) as temp:
    temp.write(ROOT_CA)
    temp.close()
    context = create_ssl_context(verify=temp.name)


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
            verify=context,
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
            await self._oauth_client.get("https://companion.devices.sberbank.ru/v13/smarthome/token", headers={
                "User-Agent": "Salute+prod%2F24.04.1.15123+%28Android+33%3B+Google+sdk_gphone64_arm64%29"
            })
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

    async def get_device_tree(self) -> dict[str, any]:
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

def extract_devices(d: dict[str, any]) -> dict[str, any]:
    devices: dict[str, any] = {device["id"]: device for device in d["devices"]}
    for children in d["children"]:
        devices.update(extract_devices(children))
    return devices