"""Various functions to handle instance UUIDs."""

from __future__ import annotations

import uuid

from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id

from ..const import INSTANCE_UUID, STABLE_ID  # noqa: TID252
from .utils import create_device_info


def create_new_instance_uuid():
    """Create a new Instance UUID."""
    return str(uuid.uuid4())


class EtaInstanceUUIDSensor(SensorEntity):
    """Representation of a sensor showing the instance UUID."""

    def __init__(self, config: dict, hass: HomeAssistant) -> None:  # noqa: D107
        host = config.get(CONF_HOST, "")
        port = config.get(CONF_PORT, "")

        self._attr_device_info = create_device_info(
            host, port, None, config.get(CONF_NAME)
        )

        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True
        self._attr_translation_key = "instance_uuid"

        stable = config.get(STABLE_ID) or host.replace(".", "_")
        self._attr_unique_id = "eta_" + stable + "_" + str(port) + "_instance_uuid"
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )

        self._attr_native_value = config.get(INSTANCE_UUID, "")
