"""Config flow for SberDevices integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .api import SberAPI
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("url"): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SberDevices."""

    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._client = SberAPI()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._client.authorize_by_url(user_input["url"])
            if not result:
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(title="SberDevices", data={"token": self._client.token})

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            description_placeholders={
                "auth_url": self._client.create_authorization_url(),
            },
            errors=errors,
        )
