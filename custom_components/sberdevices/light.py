"""Support for Abode Security System lights."""
from __future__ import annotations

import math

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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness
from homeassistant.util.scaling import scale_ranged_value_to_int_range

from .api import DeviceAPI, HomeAPI
from .const import DOMAIN

# hardcode xd
COLOR_TEMP_MIN = 2700
COLOR_TEMP_MAX = 6500
COLOR_TEMP_RANGE = (COLOR_TEMP_MIN, COLOR_TEMP_MAX)

H_RANGE = (0, 360)
S_RANGE = (0, 100)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    home: HomeAPI = hass.data[DOMAIN][entry.entry_id]["home"]
    await home.update_devices_cache()
    async_add_entities(
        [
            SberLightEntity(DeviceAPI(home, device["id"]))
            for device in home.get_cached_devices().values()
            if "bulb" in device["image_set_type"]  # TODO: lutiy kostyl'
        ]
    )


class SberLightEntity(LightEntity):
    def __init__(self, api: DeviceAPI) -> None:
        self._id = api.device["id"]
        self._api = api
        self._hs_color: tuple[float, float] | None = None

    @property
    def should_poll(self) -> bool:
        return True

    async def async_update(self):
        await self._api.update()
        self._hs_color = None

    @property
    def unique_id(self) -> str:
        return self._api.device["id"]

    @property
    def name(self) -> str:
        return self._api.device["name"]["name"]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._api.device["serial_number"])},
            name=self.name,
            manufacturer=self._api.device["device_info"]["manufacturer"],
            model=self._api.device["device_info"]["model"],
            sw_version=self._api.device["sw_version"],
            serial_number=self._api.device["serial_number"],
        )

    @property
    def is_on(self) -> bool:
        return self._api.get_state("on_off")["bool_value"]

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        m = {
            "light_brightness": ColorMode.BRIGHTNESS,
            "light_colour_temp": ColorMode.COLOR_TEMP,
        }
        v = {m[k] for k in m if self._api.get_attribute(k) is not None}
        light_mode = self._api.get_attribute("light_mode")["enum_values"]["values"]
        if "white" in light_mode:
            v.add(ColorMode.WHITE)
        if "colour" in light_mode:
            v.add(ColorMode.HS)

        return v

    @property
    def color_mode(self) -> ColorMode:
        mode = self._api.get_state("light_mode")["enum_value"]
        if mode == "white":
            return ColorMode.COLOR_TEMP
        elif mode == "colour":
            return ColorMode.HS
        else:
            return ColorMode.UNKNOWN

    @property
    def brightness_range(self) -> tuple[int, int]:
        brightness_range: dict[str, any] = self._api.get_attribute("light_brightness")[
            "int_values"
        ]["range"]
        return (
            brightness_range["min"],
            brightness_range["max"],
        )

    @property
    def brightness(self) -> int | None:
        if ColorMode.BRIGHTNESS not in self.supported_color_modes:
            return None

        if self.color_mode == ColorMode.HS:
            brightness = self._api.get_state("light_colour")["color_value"]["v"]
            return value_to_brightness(self.color_range["v"], brightness)

        brightness = int(self._api.get_state("light_brightness")["integer_value"])
        return value_to_brightness(self.brightness_range, brightness)

    @property
    def min_color_temp_kelvin(self) -> int:
        return COLOR_TEMP_MIN

    @property
    def max_color_temp_kelvin(self) -> int:
        return COLOR_TEMP_MAX

    @property
    def color_temp_range(self) -> tuple[int, int]:
        colour_temp_range: dict[str, any] = self._api.get_attribute(
            "light_colour_temp"
        )["int_values"]["range"]
        return (
            colour_temp_range["min"],
            colour_temp_range["max"],
        )

    @property
    def color_temp_kelvin(self) -> int:
        if ColorMode.COLOR_TEMP not in self.supported_color_modes:
            return None

        colour_temp = int(self._api.get_state("light_colour_temp")["integer_value"])
        return scale_ranged_value_to_int_range(
            self.color_temp_range, COLOR_TEMP_RANGE, colour_temp
        )

    @property
    def color_range(self) -> dict[str, tuple[int, int]]:
        colour_values = self._api.get_attribute("light_colour")["color_values"]
        return {
            "h": (colour_values["h"]["min"], colour_values["h"]["max"]),
            "s": (colour_values["s"]["min"], colour_values["s"]["max"]),
            "v": (colour_values["v"]["min"], colour_values["v"]["max"]),
        }

    @property
    def hs_color(self) -> tuple[float, float] | None:
        if ColorMode.HS not in self.supported_color_modes:
            return None

        if self._hs_color is not None:
            return self._hs_color

        colour = self._api.get_state("light_colour")["color_value"]
        return (
            scale_ranged_value_to_int_range(
                self.color_range["h"],
                H_RANGE,
                colour["h"],
            ),
            scale_ranged_value_to_int_range(
                self.color_range["s"],
                S_RANGE,
                colour["s"],
            ),
        )

    @property
    def real_hs_color(self) -> tuple[float, float]:
        colour = self._api.get_state("light_colour")["color_value"]
        return (
            scale_ranged_value_to_int_range(
                self.color_range["h"],
                H_RANGE,
                colour["h"],
            ),
            scale_ranged_value_to_int_range(
                self.color_range["s"],
                S_RANGE,
                colour["s"],
            ),
        )

    async def async_turn_on(self, **kwargs) -> None:
        states = [
            {"key": "on_off", "bool_value": True},
        ]

        if ATTR_BRIGHTNESS in kwargs and self.color_mode == ColorMode.HS:
            color = self.hs_color or self.real_hs_color
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
                                self.brightness_range,
                                kwargs[ATTR_BRIGHTNESS],
                            )
                        ),
                    },
                    {
                        "key": "light_colour",
                        "color_value": {
                            "h": scale_ranged_value_to_int_range(
                                H_RANGE,
                                self.color_range["h"],
                                color[0],
                            ),
                            "s": scale_ranged_value_to_int_range(
                                S_RANGE,
                                self.color_range["s"],
                                color[1],
                            ),
                            "v": math.ceil(
                                brightness_to_value(
                                    self.color_range["v"],
                                    kwargs[ATTR_BRIGHTNESS],
                                )
                            ),
                        },
                    },
                )
            )

        brightness = kwargs.get(ATTR_BRIGHTNESS) or kwargs.get(ATTR_WHITE)
        if (
            self.color_mode != ColorMode.HS or ATTR_WHITE in kwargs
        ) and brightness is not None:
            states.extend(
                (
                    {
                        "key": "light_mode",
                        "enum_value": "white",
                    },
                    {
                        "key": "light_brightness",
                        "integer_value": math.ceil(
                            brightness_to_value(self.brightness_range, brightness)
                        ),
                    },
                )
            )

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            t = scale_ranged_value_to_int_range(
                COLOR_TEMP_RANGE,
                self.color_temp_range,
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
            self._hs_color = (h, s)

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
                                self.color_range["h"],
                                h,
                            ),
                            "s": scale_ranged_value_to_int_range(
                                S_RANGE,
                                self.color_range["s"],
                                s,
                            ),
                            "v": math.ceil(
                                brightness_to_value(
                                    self.color_range["v"],
                                    self.brightness,
                                )
                            ),
                        },
                    },
                )
            )

        await self._api.set_states(states)

    async def async_turn_off(self, **kwargs) -> None:
        await self._api.set_on_off(False)
