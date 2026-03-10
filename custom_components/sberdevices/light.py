"""Support for SberDevices lights."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_WHITE,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness
from homeassistant.util.scaling import scale_ranged_value_to_int_range

from .api import DeviceAPI, HomeAPI
from .const import (
    COLOR_TEMP_RANGES,
    DEFAULT_COLOR_TEMP_RANGE,
    DOMAIN,
    H_RANGE,
    LIGHT_TYPES,
    S_RANGE,
)
from .entity import SberEntity


def get_color_temp_range(device_type: str) -> tuple[int, int]:
    return COLOR_TEMP_RANGES.get(device_type, DEFAULT_COLOR_TEMP_RANGE)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    home: HomeAPI = hass.data[DOMAIN][entry.entry_id]["home"]
    async_add_entities(
        [
            SberLightEntity(
                DeviceAPI(home, device["id"]),
                next(t for t in LIGHT_TYPES if t in device["image_set_type"]),
            )
            for device in home.get_cached_devices().values()
            if any(t in device["image_set_type"] for t in LIGHT_TYPES)
        ]
    )


class SberLightEntity(SberEntity, LightEntity):
    def __init__(self, api: DeviceAPI, device_type: str) -> None:
        super().__init__(api)

        # Static color temp range (from device type)
        self._real_color_temp_range = get_color_temp_range(device_type)
        self._attr_min_color_temp_kelvin = self._real_color_temp_range[0]
        self._attr_max_color_temp_kelvin = self._real_color_temp_range[1]

        # Supported color modes (from device attributes, static)
        modes: set[ColorMode] = set()
        attr_to_mode = {
            "light_brightness": ColorMode.BRIGHTNESS,
            "light_colour_temp": ColorMode.COLOR_TEMP,
        }
        for attr, mode in attr_to_mode.items():
            if api.has_attribute(attr):
                modes.add(mode)
        light_mode_values = api.get_attribute("light_mode")["enum_values"]["values"]
        if "white" in light_mode_values:
            modes.add(ColorMode.WHITE)
        if "colour" in light_mode_values:
            modes.add(ColorMode.HS)
        self._modes = modes
        self._attr_supported_color_modes = modes

        # Internal ranges for calculations (from device attributes, static)
        if ColorMode.BRIGHTNESS in modes:
            br = api.get_attribute("light_brightness")["int_values"]["range"]
            self._brightness_range = (br["min"], br["max"])

        if ColorMode.COLOR_TEMP in modes:
            ct = api.get_attribute("light_colour_temp")["int_values"]["range"]
            self._color_temp_range = (ct["min"], ct["max"])

        if ColorMode.HS in modes:
            cv = api.get_attribute("light_colour")["color_values"]
            self._color_range: dict[str, tuple[int, int]] = {
                "h": (cv["h"]["min"], cv["h"]["max"]),
                "s": (cv["s"]["min"], cv["s"]["max"]),
                "v": (cv["v"]["min"], cv["v"]["max"]),
            }

    async def async_update(self) -> None:
        await super().async_update()

        self._attr_is_on = self._api.get_state("on_off")["bool_value"]

        mode = self._api.get_state("light_mode")["enum_value"]
        match mode:
            case "white":
                self._attr_color_mode = ColorMode.COLOR_TEMP
            case "colour":
                self._attr_color_mode = ColorMode.HS
            case _:
                self._attr_color_mode = ColorMode.UNKNOWN

        if ColorMode.BRIGHTNESS in self._modes:
            if self._attr_color_mode == ColorMode.HS:
                v = self._api.get_state("light_colour")["color_value"]["v"]
                self._attr_brightness = value_to_brightness(self._color_range["v"], v)
            else:
                v = int(self._api.get_state("light_brightness")["integer_value"])
                self._attr_brightness = value_to_brightness(self._brightness_range, v)

        if ColorMode.COLOR_TEMP in self._modes:
            ct = int(self._api.get_state("light_colour_temp")["integer_value"])
            self._attr_color_temp_kelvin = scale_ranged_value_to_int_range(
                self._color_temp_range, self._real_color_temp_range, ct
            )

        if ColorMode.HS in self._modes:
            self._attr_hs_color = self._compute_hs_color()

    def _compute_hs_color(self) -> tuple[float, float]:
        colour = self._api.get_state("light_colour")["color_value"]
        return (
            scale_ranged_value_to_int_range(
                self._color_range["h"],
                H_RANGE,
                colour["h"],
            ),
            scale_ranged_value_to_int_range(
                self._color_range["s"],
                S_RANGE,
                colour["s"],
            ),
        )

    async def async_turn_on(self, **kwargs) -> None:
        states: list[dict[str, Any]] = [
            {"key": "on_off", "bool_value": True},
        ]

        if ATTR_BRIGHTNESS in kwargs and self.color_mode == ColorMode.HS:
            color = self.hs_color or self._compute_hs_color()
            states.extend(
                (
                    {
                        "key": "light_mode",
                        "enum_value": "colour",
                    },
                    {
                        "key": "light_brightness",
                        "integer_value": math.ceil(
                            brightness_to_value(
                                self._brightness_range,
                                kwargs[ATTR_BRIGHTNESS],
                            )
                        ),
                    },
                    {
                        "key": "light_colour",
                        "color_value": {
                            "h": scale_ranged_value_to_int_range(
                                H_RANGE,
                                self._color_range["h"],
                                color[0],
                            ),
                            "s": scale_ranged_value_to_int_range(
                                S_RANGE,
                                self._color_range["s"],
                                color[1],
                            ),
                            "v": math.ceil(
                                brightness_to_value(
                                    self._color_range["v"],
                                    kwargs[ATTR_BRIGHTNESS],
                                )
                            ),
                        },
                    },
                )
            )

        brightness = kwargs.get(ATTR_BRIGHTNESS) or kwargs.get(ATTR_WHITE)
        if (self.color_mode != ColorMode.HS or ATTR_WHITE in kwargs) and brightness is not None:
            states.extend(
                (
                    {
                        "key": "light_mode",
                        "enum_value": "white",
                    },
                    {
                        "key": "light_brightness",
                        "integer_value": math.ceil(brightness_to_value(self._brightness_range, brightness)),
                    },
                )
            )

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            t = scale_ranged_value_to_int_range(
                self._real_color_temp_range,
                self._color_temp_range,
                kwargs[ATTR_COLOR_TEMP_KELVIN],
            )
            if t < 0:
                t = 0

            states.extend(
                (
                    {
                        "key": "light_mode",
                        "enum_value": "white",
                    },
                    {
                        "key": "light_colour_temp",
                        "integer_value": t,
                    },
                )
            )

        if ATTR_HS_COLOR in kwargs:
            (h, s) = kwargs[ATTR_HS_COLOR]
            self._attr_hs_color = (h, s)
            current_brightness = self.brightness
            assert current_brightness is not None

            states.extend(
                (
                    {
                        "key": "light_mode",
                        "enum_value": "colour",
                    },
                    {
                        "key": "light_colour",
                        "color_value": {
                            "h": scale_ranged_value_to_int_range(
                                H_RANGE,
                                self._color_range["h"],
                                h,
                            ),
                            "s": scale_ranged_value_to_int_range(
                                S_RANGE,
                                self._color_range["s"],
                                s,
                            ),
                            "v": math.ceil(
                                brightness_to_value(
                                    self._color_range["v"],
                                    current_brightness,
                                )
                            ),
                        },
                    },
                )
            )

        await self._api.set_states(states)

    async def async_turn_off(self, **kwargs) -> None:
        await self._api.set_on_off(False)
