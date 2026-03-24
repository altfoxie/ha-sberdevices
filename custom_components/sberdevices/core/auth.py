"""Authentication helpers for the SberDevices integration."""

from __future__ import annotations

import logging
import ssl
from pathlib import Path
from typing import Any

from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client

from ..const import AUTH_ENDPOINT, COMPANION_TOKEN_URL, OAUTH_CLIENT_ID, TOKEN_ENDPOINT

_LOGGER = logging.getLogger(__name__)

type TokenData = dict[str, Any]

_ROOT_CA_PATH = Path(__file__).parent / "russian_trusted_root_ca.pem"


def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=str(_ROOT_CA_PATH))
    return ctx


_SSL_CONTEXT = _create_ssl_context()
SBER_SSL_CONTEXT = _SSL_CONTEXT


class SberAuthClient:
    """OAuth client for Sber authentication endpoints."""

    def __init__(self, token: TokenData | None = None) -> None:
        self._code_verifier = generate_token(64)
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
    def token(self) -> TokenData:
        return self._oauth_client.token

    def create_authorization_url(self) -> str:
        return self._oauth_client.create_authorization_url(
            AUTH_ENDPOINT,
            nonce=generate_token(),
            code_verifier=self._code_verifier,
        )[0]

    async def authorize_by_url(self, url: str) -> bool:
        try:
            token = await self._oauth_client.fetch_token(
                TOKEN_ENDPOINT,
                authorization_response=url,
                code_verifier=self._code_verifier,
            )
            return token is not None
        except Exception:
            _LOGGER.exception("Failed to authorize by URL")
            return False

    async def fetch_gateway_token(self) -> str:
        return (
            await self._oauth_client.get(
                COMPANION_TOKEN_URL,
                headers={"User-Agent": "Salute+prod%2F24.08.1.15602+%28Android+34%3B+Google+sdk_gphone64_arm64%29"},
            )
        ).json()["token"]

    async def fetch_home_token(self) -> str:
        return await self.fetch_gateway_token()

    async def async_close(self) -> None:
        await self._oauth_client.aclose()


SberAPI = SberAuthClient
