from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN

class SberSensorEntity:
    @property
    def should_poll(self) -> bool:
        return True

    async def async_update(self):
        await self._api.update()

    @property
    def unique_id(self) -> str:
        return self._api.device["id"]

    @property
    def name(self) -> str:
        return (
            self._api.device["group"] + ": "
            if self._api.device["group"] else ""
        ) + self._api.device["name"]["name"]

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

    def _get_reported_state_value(self, key: str):
        if "reported_state" not in self._api.device:
            return None

        for state in self._api.device["reported_state"]:
            if state["key"] == key:
                return state
        return None

    @property
    def extra_state_attributes(self):
        attributes = {}

        attr_names = ['battery_percentage', 'signal_strength', 'battery_low_power', 'cur_voltage', 'cur_current', 'cur_power']

        for attr_name in attr_names:
            state = self._get_reported_state_value(attr_name)
            if not state:
                continue

            if state["type"] == "FLOAT":
                attributes[attr_name] = state["float_value"]
            elif state["type"] == "INTEGER":
                if attr_name == "cur_current":
                    # Convert current from mA to A
                    attributes[attr_name] = float(state["integer_value"]) / 1000
                else:
                    attributes[attr_name] = state["integer_value"]
            elif state["type"] == "BOOL":
                attributes[attr_name] = state["bool_value"]

        return attributes