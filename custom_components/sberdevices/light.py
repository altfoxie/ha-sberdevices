"""Support for SberDevices lights."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_WHITE,
    EFFECT_OFF,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness
from homeassistant.util.scaling import scale_ranged_value_to_int_range

from .const import (
    COLOR_TEMP_RANGES,
    DEFAULT_COLOR_TEMP_RANGE,
    H_RANGE,
    LIGHT_TYPES,
    S_RANGE,
)
from .core.coordinator import SberDataUpdateCoordinator
from .core.entity import SberEntity
from .core.runtime import SberConfigEntry
from .core.snapshot import DeviceState


def get_color_temp_range(device_type: str) -> tuple[int, int]:
    return COLOR_TEMP_RANGES.get(device_type, DEFAULT_COLOR_TEMP_RANGE)


async def async_setup_entry(
    hass: HomeAssistant, entry: SberConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime_data = entry.runtime_data
    async_add_entities(
        [
            SberLightEntity(
                runtime_data.coordinator,
                device["id"],
                next(t for t in LIGHT_TYPES if t in device["image_set_type"]),
            )
            for device in runtime_data.coordinator.data.values()
            if any(t in device["image_set_type"] for t in LIGHT_TYPES)
        ]
    )


class SberLightEntity(SberEntity, LightEntity):
    def __init__(self, coordinator: SberDataUpdateCoordinator, device_id: str, device_type: str) -> None:
        super().__init__(coordinator, device_id)

        self._real_color_temp_range = get_color_temp_range(device_type)
        self._attr_min_color_temp_kelvin = self._real_color_temp_range[0]
        self._attr_max_color_temp_kelvin = self._real_color_temp_range[1]

        light_mode_values = self.get_attribute("light_mode")["enum_values"]["values"]
        self._supports_brightness = self.has_attribute("light_brightness")
        self._supports_color_temp = self.has_attribute("light_colour_temp")
        self._supports_hs = "colour" in light_mode_values and self.has_attribute("light_colour")
        self._supports_white_command = "white" in light_mode_values
        self._supports_white_mode = "white" in light_mode_values and self._supports_hs and not self._supports_color_temp
        self._scene_effect_values = self._enum_values("light_scene")
        self._supports_music_effect = "music" in light_mode_values
        self._supports_adaptive_effect = "adaptive" in light_mode_values
        self._effect_values = self._build_effect_list()

        # Normalize raw device capabilities into a HA-valid supported_color_modes set.
        supported_color_modes: set[ColorMode] = set()
        if self._supports_hs:
            supported_color_modes.add(ColorMode.HS)
        if self._supports_color_temp:
            supported_color_modes.add(ColorMode.COLOR_TEMP)
        elif self._supports_white_mode:
            supported_color_modes.add(ColorMode.WHITE)
        elif self._supports_brightness:
            supported_color_modes.add(ColorMode.BRIGHTNESS)
        else:
            supported_color_modes.add(ColorMode.ONOFF)
        self._attr_supported_color_modes = supported_color_modes
        if self._effect_values:
            self._attr_supported_features = LightEntityFeature.EFFECT
            self._attr_effect_list = self._effect_values

        if self._supports_brightness:
            br = self.get_attribute("light_brightness")["int_values"]["range"]
            self._brightness_range = (br["min"], br["max"])

        if self._supports_color_temp:
            ct = self.get_attribute("light_colour_temp")["int_values"]["range"]
            self._color_temp_range = (ct["min"], ct["max"])

        if self._supports_hs:
            cv = self.get_attribute("light_colour")["color_values"]
            self._color_range: dict[str, tuple[int, int]] = {
                "h": (cv["h"]["min"], cv["h"]["max"]),
                "s": (cv["s"]["min"], cv["s"]["max"]),
                "v": (cv["v"]["min"], cv["v"]["max"]),
            }

        self._update_attrs()

    def _enum_values(self, key: str) -> list[str]:
        if not self.has_attribute(key):
            return []

        enum_values = self.get_attribute(key).get("enum_values")
        if not isinstance(enum_values, dict):
            return []

        values = enum_values.get("values")
        if not isinstance(values, list):
            return []

        return [value for value in values if isinstance(value, str)]

    def _build_effect_list(self) -> list[str]:
        effect_values = [*self._scene_effect_values]
        if self._supports_music_effect:
            effect_values.append("music")
        if self._supports_adaptive_effect:
            effect_values.append("adaptive")
        return effect_values

    def _is_effect_mode(self, mode: str) -> bool:
        return (
            mode == "scene"
            or (mode == "music" and self._supports_music_effect)
            or (mode == "adaptive" and self._supports_adaptive_effect)
        )

    def _current_effect(self) -> str:
        mode = self.get_desired_state("light_mode")["enum_value"]
        if mode == "scene":
            scene = self.get_desired_state("light_scene").get("enum_value")
            if isinstance(scene, str) and scene:
                return scene
        elif mode == "music" and self._supports_music_effect:
            return "music"
        elif mode == "adaptive" and self._supports_adaptive_effect:
            return "adaptive"
        return EFFECT_OFF

    def _default_non_effect_mode(self) -> str | None:
        if self._supports_white_command:
            return "white"
        if self._supports_hs:
            return "colour"
        return None

    def _should_keep_current_effect(self, kwargs: dict[str, Any]) -> bool:
        return (
            ATTR_EFFECT not in kwargs
            and ATTR_WHITE not in kwargs
            and ATTR_BRIGHTNESS in kwargs
            and self._current_effect() != EFFECT_OFF
        )

    def _requested_effect(self, kwargs: dict[str, Any]) -> str | None:
        effect = kwargs.get(ATTR_EFFECT)
        if isinstance(effect, str):
            return effect
        return None

    def _has_active_effect_request(self, kwargs: dict[str, Any]) -> bool:
        effect = self._requested_effect(kwargs)
        return effect is not None and effect != EFFECT_OFF

    def _current_ha_color_mode(self) -> ColorMode:
        mode = self.get_desired_state("light_mode")["enum_value"]
        if self._is_effect_mode(mode):
            return ColorMode.BRIGHTNESS if self._supports_brightness else ColorMode.ONOFF

        match mode:
            case "white":
                if self._supports_color_temp:
                    return ColorMode.COLOR_TEMP
                if self._supports_white_mode:
                    return ColorMode.WHITE
                if self._supports_brightness:
                    return ColorMode.BRIGHTNESS
                return ColorMode.ONOFF
            case "colour" if self._supports_hs:
                return ColorMode.HS
            case _:
                return ColorMode.BRIGHTNESS if self._supports_brightness else ColorMode.ONOFF

    def _update_brightness_attr(self) -> None:
        if not self._supports_brightness:
            return

        if self._attr_color_mode == ColorMode.HS:
            colour = self._get_color_value()
            if colour is not None and "v" in colour:
                self._attr_brightness = value_to_brightness(self._color_range["v"], colour["v"])
                return

        brightness = int(self.get_desired_state("light_brightness")["integer_value"])
        self._attr_brightness = value_to_brightness(self._brightness_range, brightness)

    def _update_color_temp_attr(self) -> None:
        if not self._supports_color_temp:
            return

        ct = int(self.get_desired_state("light_colour_temp")["integer_value"])
        self._attr_color_temp_kelvin = scale_ranged_value_to_int_range(
            self._color_temp_range, self._real_color_temp_range, ct
        )

    def _update_hs_attr(self) -> None:
        if not self._supports_hs:
            return

        self._attr_hs_color = self._compute_hs_color()

    def _update_attrs(self) -> None:
        self._attr_is_on = self.get_desired_state("on_off")["bool_value"]
        self._attr_color_mode = self._current_ha_color_mode()
        if self._effect_values:
            self._attr_effect = self._current_effect()
        self._update_brightness_attr()
        self._update_color_temp_attr()
        self._update_hs_attr()

    def _get_color_value(self) -> dict[str, Any] | None:
        colour = self.get_desired_state("light_colour").get("color_value")
        if not isinstance(colour, dict):
            return None
        return colour

    def _compute_hs_color(self) -> tuple[float, float] | None:
        colour = self._get_color_value()
        if colour is None or "h" not in colour or "s" not in colour:
            return None

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

    def _current_or_fallback_hs_color(self) -> tuple[float, float]:
        return self.hs_color or self._compute_hs_color() or (0.0, 0.0)

    def _current_color_value_brightness(self) -> int:
        colour = self._get_color_value()
        if colour is not None and "v" in colour:
            return colour["v"]

        if self.brightness is not None:
            return math.ceil(brightness_to_value(self._color_range["v"], self.brightness))

        return self._color_range["v"][0]

    def _light_mode_state(self, mode: str) -> dict[str, Any]:
        return {"key": "light_mode", "enum_value": mode}

    def _light_brightness_state(self, brightness: int) -> dict[str, Any]:
        return {
            "key": "light_brightness",
            "integer_value": math.ceil(brightness_to_value(self._brightness_range, brightness)),
        }

    def _light_colour_state(self, hs_color: tuple[float, float], value_brightness: int) -> dict[str, Any]:
        h, s = hs_color
        return {
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
                "v": value_brightness,
            },
        }

    def _requested_white_brightness(self, kwargs: dict[str, Any]) -> Any:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is None:
            brightness = kwargs.get(ATTR_WHITE)
        return brightness

    def _requested_color_temp(self, kelvin: int) -> int:
        color_temp = scale_ranged_value_to_int_range(
            self._real_color_temp_range,
            self._color_temp_range,
            kelvin,
        )
        return max(color_temp, 0)

    def _finalize_state_patch(self, states: list[DeviceState]) -> list[DeviceState]:
        states_by_key: dict[str, DeviceState] = {}
        for state in states:
            key = state["key"]
            states_by_key.pop(key, None)
            states_by_key[key] = state
        return list(states_by_key.values())

    def _queue_power_on(self, states: list[DeviceState]) -> None:
        states.append({"key": "on_off", "bool_value": True})

    def _queue_effect_request(self, states: list[DeviceState], kwargs: dict[str, Any]) -> None:
        if ATTR_EFFECT not in kwargs or not self._effect_values:
            return

        effect = kwargs[ATTR_EFFECT]
        if not isinstance(effect, str):
            return

        if effect == EFFECT_OFF:
            if default_mode := self._default_non_effect_mode():
                states.append(self._light_mode_state(default_mode))
            return

        if effect in self._scene_effect_values:
            states.extend(
                (
                    self._light_mode_state("scene"),
                    {"key": "light_scene", "enum_value": effect},
                )
            )
            return

        if effect == "music" and self._supports_music_effect:
            states.append(self._light_mode_state("music"))
            return

        if effect == "adaptive" and self._supports_adaptive_effect:
            states.append(self._light_mode_state("adaptive"))

    def _queue_colour_brightness_request(self, states: list[DeviceState], kwargs: dict[str, Any]) -> None:
        if ATTR_BRIGHTNESS not in kwargs or self._has_active_effect_request(kwargs):
            return

        should_switch_to_colour = (
            self._requested_effect(kwargs) == EFFECT_OFF and self._default_non_effect_mode() == "colour"
        )
        if self.color_mode != ColorMode.HS and not should_switch_to_colour:
            return

        brightness = kwargs[ATTR_BRIGHTNESS]
        states.extend(
            (
                self._light_mode_state("colour"),
                self._light_brightness_state(brightness),
                self._light_colour_state(
                    self._current_or_fallback_hs_color(),
                    math.ceil(brightness_to_value(self._color_range["v"], brightness)),
                ),
            )
        )

    def _queue_white_brightness_request(self, states: list[DeviceState], kwargs: dict[str, Any]) -> None:
        brightness = self._requested_white_brightness(kwargs)
        if brightness is None:
            return

        if self._has_active_effect_request(kwargs) and ATTR_WHITE not in kwargs:
            states.append(self._light_brightness_state(brightness))
            return

        if self._should_keep_current_effect(kwargs):
            states.append(self._light_brightness_state(brightness))
            return

        if (self.color_mode == ColorMode.HS and ATTR_WHITE not in kwargs) or not self._supports_white_command:
            return

        states.extend(
            (
                self._light_mode_state("white"),
                self._light_brightness_state(brightness),
            )
        )

    def _queue_color_temperature_request(self, states: list[DeviceState], kwargs: dict[str, Any]) -> None:
        if (
            self._has_active_effect_request(kwargs)
            or ATTR_COLOR_TEMP_KELVIN not in kwargs
            or not self._supports_color_temp
        ):
            return

        states.extend(
            (
                self._light_mode_state("white"),
                {
                    "key": "light_colour_temp",
                    "integer_value": self._requested_color_temp(kwargs[ATTR_COLOR_TEMP_KELVIN]),
                },
            )
        )

    def _queue_hs_color_request(self, states: list[DeviceState], kwargs: dict[str, Any]) -> None:
        if self._has_active_effect_request(kwargs) or ATTR_HS_COLOR not in kwargs or not self._supports_hs:
            return

        hs_color = kwargs[ATTR_HS_COLOR]
        self._attr_hs_color = hs_color
        states.extend(
            (
                self._light_mode_state("colour"),
                self._light_colour_state(hs_color, self._current_color_value_brightness()),
            )
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        states: list[DeviceState] = []
        self._queue_power_on(states)
        self._queue_effect_request(states, kwargs)
        self._queue_colour_brightness_request(states, kwargs)
        self._queue_white_brightness_request(states, kwargs)
        self._queue_color_temperature_request(states, kwargs)
        self._queue_hs_color_request(states, kwargs)

        await self.async_set_states(self._finalize_state_patch(states))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_on_off(False)
