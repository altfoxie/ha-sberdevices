"""
Test that calls the real SberDevices API.

Requires a valid OAuth token in .env.local (created by scripts/get_token.py)
or in environment variables.

Run:
    pytest tests/test_real_api.py -s
"""

import json
import os
from pathlib import Path

import pytest

from custom_components.sberdevices.api import HomeAPI, SberAPI

ENV_FILE = Path(__file__).resolve().parent.parent / ".env.local"


def load_env_file():
    """Load variables from .env.local if it exists."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key and _ and key not in os.environ:
            os.environ[key] = value


def load_token() -> dict:
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
async def test_get_device_tree():
    """Fetch real device tree from SberDevices API."""
    token = load_token()
    sber = SberAPI(token=token)
    home = HomeAPI(sber)

    device_tree = await home.get_device_tree()

    assert device_tree is not None
    assert "devices" in device_tree
    print(json.dumps(device_tree, indent=2, ensure_ascii=False))
