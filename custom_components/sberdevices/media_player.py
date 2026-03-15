"""Support for SberDevices media players (SberTV)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DeviceAPI, HomeAPI
from .const import DOMAIN, MEDIA_PLAYER_TYPES
from .entity import SberEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    home: HomeAPI = hass.data[DOMAIN][entry.entry_id]["home"]
    async_add_entities(
        [
            SberMediaPlayerEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if device.get("image_set_type") in MEDIA_PLAYER_TYPES
        ]
    )


class SberMediaPlayerEntity(SberEntity, MediaPlayerEntity):
    """SberTV media player entity."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
    )

    def _has_state(self, key: str) -> bool:
        """Check if device has a state key."""
        try:
            self._api.get_state(key)
            return True
        except StopIteration:
            return False

    async def async_update(self) -> None:
        await super().async_update()
        if self._has_state("on_off"):
            is_on = self._api.get_state("on_off")["bool_value"]
            if self._has_state("online"):
                online = self._api.get_state("online")["bool_value"]
                if not online:
                    self._attr_state = MediaPlayerState.OFF
                elif is_on:
                    self._attr_state = MediaPlayerState.ON
                else:
                    self._attr_state = MediaPlayerState.STANDBY
            else:
                self._attr_state = MediaPlayerState.ON if is_on else MediaPlayerState.OFF

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._api.set_on_off(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._api.set_on_off(False)
