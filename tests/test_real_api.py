"""Live SberDevices API smoke test.

Requires a valid OAuth token in .env.local (created by scripts/get_token.py)
or in environment variables.

Run:
    ./scripts/test tests/test_real_api.py -s
"""

import json
import os
from pathlib import Path

import pytest

from custom_components.sberdevices.core.auth import SberAuthClient
from custom_components.sberdevices.core.gateway import SberHomeGatewayClient

ENV_FILE = Path(__file__).resolve().parent.parent / ".env.local"


def load_env_file(env_file: Path = ENV_FILE) -> None:
    """Load variables from a dotenv-like file if it exists."""
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        key, sep, value = line.partition("=")
        if key and sep and key not in os.environ:
            os.environ[key] = value


def load_token() -> dict[str, str | int]:
    load_env_file()

    access_token = os.environ.get("SBER_ACCESS_TOKEN")
    refresh_token = os.environ.get("SBER_REFRESH_TOKEN")

    if not access_token:
        pytest.skip("SBER_ACCESS_TOKEN not set — skipping real API test")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token or "",
        "token_type": os.environ.get("SBER_TOKEN_TYPE", "Bearer"),
        "expires_at": int(os.environ.get("SBER_EXPIRES_AT", "0")),
    }


@pytest.mark.asyncio
async def test_get_device_tree() -> None:
    """Fetch real device tree from SberDevices API."""
    token = load_token()
    auth_client = SberAuthClient(token=token)
    gateway_client = SberHomeGatewayClient(auth_client)

    try:
        device_tree = await gateway_client.get_device_tree()
    finally:
        await gateway_client.async_close()
        await auth_client.async_close()

    assert device_tree is not None
    assert "devices" in device_tree
    print(json.dumps(device_tree, indent=2, ensure_ascii=False))
