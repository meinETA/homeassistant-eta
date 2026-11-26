"""Button platform for the ETA sensor integration in Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.components.button import ENTITY_ID_FORMAT, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ERROR_UPDATE_COORDINATOR, STABLE_ID
from .coordinator import ETAErrorUpdateCoordinator
from .upload import async_upload_entry
from .utils import create_device_info
from .utils.raw_data import async_start_raw_data_collection

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup button."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    error_coordinator = config[ERROR_UPDATE_COORDINATOR]

    buttons = [
        EtaResendErrorEventsButton(config, hass, error_coordinator),
        EtaStoreApiResponsesButton(config, hass, config_entry),
        EtaUploadPlantDataButton(config, hass, config_entry),
    ]

    async_add_entities(buttons)


class EtaResendErrorEventsButton(ButtonEntity):
    """Representation of a Button, which can be used to force HA to resend all error events."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(  # noqa: D107
        self, config: dict, hass: HomeAssistant, coordinator: ETAErrorUpdateCoordinator
    ) -> None:
        host = config.get(CONF_HOST, "")
        port = config.get(CONF_PORT, "")
        self.coordinator = coordinator

        self._attr_translation_key = "send_error_events_btn"
        stable = config.get(STABLE_ID) or host.replace(".", "_")
        self._attr_unique_id = "eta_" + stable + "_" + str(port) + "_send_events_btn"
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        self._attr_device_info = create_device_info(
            host, port, None, config.get(CONF_NAME)
        )
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Force the error update coordinator to resend all error events."""
        # Delete the old error list to force the coordinator to resend all events
        self.coordinator.data = []
        await self.coordinator.async_refresh()


class EtaStoreApiResponsesButton(ButtonEntity):
    """Representation of a Button, which can be used to rerun the background task to fetch the ETA API raw responses."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(  # noqa: D107
        self,
        config: dict,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        host = config.get(CONF_HOST, "")
        port = config.get(CONF_PORT, "")

        self._attr_translation_key = "store_api_responses_btn"
        stable = config.get(STABLE_ID) or host.replace(".", "_")
        self._attr_unique_id = "eta_" + stable + "_store_api_responses_btn"
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        self._attr_device_info = create_device_info(
            host, port, None, config.get(CONF_NAME)
        )
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False

        self._config_entry = config_entry
        self._config = config

    async def async_press(self) -> None:
        """Start the raw data collection background task again."""
        await async_start_raw_data_collection(
            self.hass, self._config_entry, self._config, force=True
        )


class EtaUploadPlantDataButton(ButtonEntity):
    """Representation of a Button, which can be used to upload the plant data to the backend for debugging purposes."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(  # noqa: D107
        self,
        config: dict,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        host = config.get(CONF_HOST, "")
        port = config.get(CONF_PORT, "")

        self._attr_translation_key = "upload_plant_data_btn"
        stable = config.get(STABLE_ID) or host.replace(".", "_")
        self._attr_unique_id = "eta_" + stable + "_upload_plant_data_btn"
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, self._attr_unique_id, hass=hass
        )
        self._attr_device_info = create_device_info(
            host, port, None, config.get(CONF_NAME)
        )
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        self._config_entry = config_entry
        self._config = config

    async def async_press(self) -> None:
        """Upload the plant data to the backend."""
        await async_upload_entry(self.hass, self._config_entry)
