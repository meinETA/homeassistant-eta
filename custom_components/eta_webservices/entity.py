"""Common entity definitions for the ETA sensor integration."""

from abc import abstractmethod
from typing import Any, Generic, TypeVar, cast

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import EtaAPI, ETAEndpoint
from .const import (
    DEFAULT_MAX_PARALLEL_REQUESTS,
    MAX_PARALLEL_REQUESTS,
    REQUEST_SEMAPHORE,
    STABLE_ID,
)
from .coordinator import ETAErrorUpdateCoordinator
from .utils import create_device_info

_EntityT = TypeVar("_EntityT")


class EtaEntity(Entity):
    """Common entity definition for all ETA entities."""

    def __init__(  # noqa: D107
        self,
        config: dict,
        hass: HomeAssistant,
        unique_id: str,
        endpoint_info: ETAEndpoint,
        entity_id_format: str,
    ) -> None:
        self.session = async_get_clientsession(hass)
        self.host = config.get(CONF_HOST, "")
        self.port = config.get(CONF_PORT, "")
        self.uri = endpoint_info["url"]
        self.max_parallel_requests = int(
            config.get(MAX_PARALLEL_REQUESTS, DEFAULT_MAX_PARALLEL_REQUESTS)
        )
        self.request_semaphore = config.get(REQUEST_SEMAPHORE)

        # Extract the FUB from the friendly name, e.g. "ETA > Living Room" -> "ETA"
        fub_name = (
            endpoint_info["friendly_name"].split(" > ")[0].strip()
            if ">" in endpoint_info["friendly_name"]
            else None
        )

        # Remove the FUB from the friendly name to avoid redundancy, e.g. "ETA > Living Room Sensor" -> "Living Room Sensor"
        if fub_name and fub_name in endpoint_info["friendly_name"]:
            self._attr_name = endpoint_info["friendly_name"].replace(
                fub_name + " > ", "", 1
            )
        else:
            self._attr_name = endpoint_info["friendly_name"]

        # Install name (konzept-v2) = display prefix for entity_id + device name.
        # Migrated installs have none and keep their entity_id via registry match.
        install_name = config.get(CONF_NAME)
        # One device per FUB; name prefixed with the install name.
        self._attr_device_info = create_device_info(
            self.host, self.port, fub_name, install_name
        )
        id_prefix = install_name or "eta"
        self.entity_id = generate_entity_id(
            entity_id_format,
            id_prefix + " " + endpoint_info["friendly_name"],
            hass=hass,
        )
        self._attr_unique_id = unique_id

    def _create_eta_client(self) -> EtaAPI:
        # Reuse configured concurrency settings for all entity-level write operations.
        return EtaAPI(
            self.session,
            self.host,
            self.port,
            max_concurrent_requests=self.max_parallel_requests,
            request_semaphore=self.request_semaphore,
        )


class EtaCoordinatedSensorEntity(
    EtaEntity,
    CoordinatorEntity[DataUpdateCoordinator[dict[str, float | str | bool]]],
    Generic[_EntityT],
):
    """Common coordinated sensor entity definition for normal ETA sensors."""

    def __init__(  # noqa: D107
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        config: dict,
        hass: HomeAssistant,
        unique_id: str,
        endpoint_info: ETAEndpoint,
        entity_id_format: str,
    ) -> None:
        EtaEntity.__init__(
            self, config, hass, unique_id, endpoint_info, entity_id_format
        )
        CoordinatorEntity.__init__(self, coordinator)  # pyright: ignore[reportArgumentType]

        self._attr_should_poll = False
        data = self.coordinator.data.get(self.uri)
        self.handle_data_updates(cast(_EntityT, data) if data is not None else None)

    @abstractmethod
    def handle_data_updates(self, data: _EntityT | None) -> None:  # noqa: D102
        raise NotImplementedError

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        data = self.coordinator.data.get(self.uri)
        if self.coordinator.data:
            self.handle_data_updates(cast(_EntityT, data) if data is not None else None)
        super()._handle_coordinator_update()


class EtaErrorEntity(CoordinatorEntity[ETAErrorUpdateCoordinator]):
    """Entity definition for all ETA error sensors."""

    def __init__(  # noqa: D107
        self,
        coordinator: ETAErrorUpdateCoordinator,
        config: dict,
        hass: HomeAssistant,
        entity_id_format: str,
        unique_id_suffix: str,
    ) -> None:
        super().__init__(coordinator)

        host = config.get(CONF_HOST, "")
        port = config.get(CONF_PORT, "")

        # Stable id (IP-independent); host fallback for un-migrated installs.
        stable = config.get(STABLE_ID) or host.replace(".", "_")
        self._attr_unique_id = "eta_" + stable + "_" + str(port) + unique_id_suffix

        self.entity_id = generate_entity_id(
            entity_id_format, self._attr_unique_id, hass=hass
        )

        self._attr_device_info = create_device_info(
            host, port, None, config.get(CONF_NAME)
        )

    @abstractmethod
    def handle_data_updates(self, data) -> None:  # noqa: D102
        raise NotImplementedError

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        self.handle_data_updates(self.coordinator.data)
        super()._handle_coordinator_update()
