"""Device snapshot helpers for the SberDevices integration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, NotRequired, TypedDict

type KeyedPayload = dict[str, Any]
type DeviceState = KeyedPayload
type DeviceAttribute = KeyedPayload


class DeviceName(TypedDict):
    """Stable device naming payload."""

    name: str


class DeviceInfo(TypedDict):
    """Stable device metadata payload."""

    manufacturer: str
    model: str


class DeviceSnapshot(TypedDict):
    """Stable envelope for a device snapshot."""

    id: str
    name: DeviceName
    serial_number: str
    device_info: DeviceInfo
    sw_version: str
    image_set_type: str
    desired_state: list[DeviceState]
    attributes: list[DeviceAttribute]
    reported_state: NotRequired[list[DeviceState]]


class DeviceTreeNode(TypedDict):
    """Nested gateway device tree."""

    devices: list[DeviceSnapshot]
    children: list[DeviceTreeNode]


type DeviceData = DeviceSnapshot
type DeviceCache = dict[str, DeviceSnapshot]


def find_by_key[T: KeyedPayload](items: Iterable[T], key: str) -> T | None:
    """Return the first keyed payload entry matching ``key``."""
    return next((item for item in items if item.get("key") == key), None)


def extract_devices(tree: DeviceTreeNode) -> DeviceCache:
    """Flatten the nested device tree into a device-id keyed snapshot."""
    devices: DeviceCache = {device["id"]: device for device in tree["devices"]}
    for child_tree in tree["children"]:
        devices.update(extract_devices(child_tree))
    return devices


def apply_device_state_patch(device: DeviceData, state_patch: list[DeviceState]) -> None:
    """Optimistically patch a device snapshot after a successful state write."""
    for patched_state in state_patch:
        desired_state = find_by_key(device["desired_state"], patched_state["key"])
        if desired_state is not None:
            desired_state.update(patched_state)
