"""Constants for the SberDevices integration."""

DOMAIN = "sberdevices"

# OAuth endpoints
AUTH_ENDPOINT = "https://online.sberbank.ru/CSAFront/oidc/authorize.do"
TOKEN_ENDPOINT = "https://online.sberbank.ru:4431/CSAFront/api/service/oidc/v3/token"
OAUTH_CLIENT_ID = "b1f0f0c6-fcb0-4ece-8374-6b614ebe3d42"

# API endpoints
GATEWAY_BASE_URL = "https://gateway.iot.sberdevices.ru/gateway/v1"
COMPANION_TOKEN_URL = "https://companion.devices.sberbank.ru/v13/smarthome/token"

# Device types
LIGHT_TYPES = ("bulb", "ledstrip", "night_lamp")
SWITCH_TYPES = ("dt_socket_sber",)

# Color temperature ranges (Kelvin) per device type
COLOR_TEMP_RANGES: dict[str, tuple[int, int]] = {
    "ledstrip": (2000, 6500),
    "bulb": (2700, 6500),
    "night_lamp": (2700, 6500),
}
DEFAULT_COLOR_TEMP_RANGE = (2700, 6500)

# HS color ranges
H_RANGE = (0, 360)
S_RANGE = (0, 100)
