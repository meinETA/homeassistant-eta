"""The ETA Sensors integration."""

import asyncio
import logging
from typing import Any

from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST, CONF_NAME, Platform
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from .config_flow import EtaFlowHandler
from .const import (
    CHOSEN_FLOAT_SENSORS,
    CHOSEN_PENDING_SENSORS,
    CHOSEN_SWITCHES,
    CHOSEN_TEXT_SENSORS,
    CHOSEN_WRITABLE_SENSORS,
    CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
    CUSTOM_UNIT_TIMESLOT,
    CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE,
    DEFAULT_MAX_PARALLEL_REQUESTS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ERROR_UPDATE_COORDINATOR,
    FLOAT_DICT,
    FORCE_LEGACY_MODE,
    MAX_PARALLEL_REQUESTS,
    PENDING_DICT,
    PENDING_UPDATE_COORDINATOR,
    RENAME_PENDING_FROM,
    REQUEST_SEMAPHORE,
    SENSOR_UPDATE_COORDINATOR,
    STABLE_ID,
    SWITCHES_DICT,
    TEXT_DICT,
    UPDATE_INTERVAL,
    WRITABLE_DICT,
    WRITABLE_UPDATE_COORDINATOR,
)
from .coordinator import (
    ETAErrorUpdateCoordinator,
    ETAPendingNodeCoordinator,
    ETASensorUpdateCoordinator,
    ETAWritableUpdateCoordinator,
)
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

_LOGGER = logging.getLogger(__name__)


def _apply_pending_rename(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> None:
    """Rewrite unique_id + entity_id from the old to the new stable id.

    Deferred to setup (before platforms load) because a live unique_id change is
    ignored; the entry is reused in place, so history is kept.
    """
    old_stable = entry.data.get(RENAME_PENDING_FROM)
    if not old_stable:
        return
    new_stable = str(entry.data.get(STABLE_ID, ""))
    old_uid_prefix = "eta_" + old_stable + "_"
    new_uid_prefix = "eta_" + new_stable + "_"
    eid_old_prefix = "eta_" + old_stable

    entity_registry = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        changes: dict[str, str] = {}
        if ent.unique_id.startswith(old_uid_prefix):
            changes["new_unique_id"] = (
                new_uid_prefix + ent.unique_id[len(old_uid_prefix) :]
            )
        # entity_id is v1-preserved "eta_<ip>_<rest>" or freshly built
        # "eta_<rest>"; strip whichever prefix matches, prepend the new stable id.
        domain, _, object_id = ent.entity_id.partition(".")
        rest = None
        if object_id.startswith(eid_old_prefix + "_"):
            rest = object_id[len(eid_old_prefix) + 1 :]
        elif object_id.startswith("eta_"):
            rest = object_id[len("eta_") :]
        if rest is not None:
            candidate = f"{domain}.{new_stable}_{rest}"
            if (
                candidate != ent.entity_id
                and entity_registry.async_get(candidate) is None
            ):
                changes["new_entity_id"] = candidate
        if changes:
            try:
                entity_registry.async_update_entity(ent.entity_id, **changes)
            except ValueError:
                _LOGGER.warning(
                    "Skipping rename of %s: target already exists", ent.entity_id
                )

    new_data = dict(entry.data)
    new_data.pop(RENAME_PENDING_FROM, None)
    hass.config_entries.async_update_entry(entry, data=new_data)
    _LOGGER.info("Applied ETA opt-in rename to the '%s' scheme", new_stable)


def _sync_migration_issue(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> None:
    """Advertise the optional v2 migration on installs still on the IP scheme.

    Informational repair for legacy (auto-migrated) entries without a name; it
    clears once the entry has a name (fresh install or opt-in migration done).
    """
    issue_id = f"legacy_scheme_{entry.entry_id}"
    if entry.data.get(CONF_NAME):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    stable = entry.data.get(STABLE_ID) or str(entry.data.get(CONF_HOST, "")).replace(
        ".", "_"
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="legacy_scheme_migration",
        translation_placeholders={"old_prefix": f"eta_{stable}_"},
    )


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    # Before the update listener is added, so clearing the marker triggers no reload.
    _apply_pending_rename(hass, entry)
    _sync_migration_issue(hass, entry)
    config = dict(entry.data)
    # Registers update listener to update config entry when options are updated.
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    # Merge the options with the config
    # The options are set if a user configures the integration after the initial set-up
    if entry.options:
        config.update(entry.options)

    config[MAX_PARALLEL_REQUESTS] = int(
        config.get(MAX_PARALLEL_REQUESTS, DEFAULT_MAX_PARALLEL_REQUESTS)
    )
    config[UPDATE_INTERVAL] = int(config.get(UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    # Share one limiter across all API users of this config entry
    # so startup and periodic updates cannot overload slower ETA units.
    config[REQUEST_SEMAPHORE] = asyncio.Semaphore(config[MAX_PARALLEL_REQUESTS])

    error_coordinator = ETAErrorUpdateCoordinator(hass, config)
    sensor_coordinator = ETASensorUpdateCoordinator(hass, config)
    writable_coordinator = ETAWritableUpdateCoordinator(hass, config)
    pending_coordinator = ETAPendingNodeCoordinator(hass, config, entry)
    config[ERROR_UPDATE_COORDINATOR] = error_coordinator
    config[SENSOR_UPDATE_COORDINATOR] = sensor_coordinator
    config[WRITABLE_UPDATE_COORDINATOR] = writable_coordinator
    config[PENDING_UPDATE_COORDINATOR] = pending_coordinator

    # Prime coordinators once before entities are added to avoid initial update bursts.
    await error_coordinator.async_config_entry_first_refresh()
    await sensor_coordinator.async_config_entry_first_refresh()
    await writable_coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = config

    # Forward the setup to the sensor platform.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Schedule the pending-node check after platform setup so that the
    # options_update_listener (registered above) is already in place before
    # any promotion fires and updates the options.
    hass.async_create_task(pending_coordinator.async_refresh())

    await async_setup_services(hass, entry)

    return True


async def async_migrate_entry(  # noqa: C901, D103
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    # Move all sensors with the custom CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT unit
    # from the list of float sensors to the list of text sensors
    # also make sure to move currently selected sensors
    def migrate_to_v6(new_data: dict[str, Any]):
        # Merge the options with the initial data to make sure we operate on the most recent data

        chosen_custom_unit_sensors = [
            entry
            for entry in new_data[CHOSEN_FLOAT_SENSORS]
            if new_data[FLOAT_DICT][entry]["unit"] == CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT
        ]
        # remove sensors with custom units from the CHOSEN_FLOAT_SENSORS list
        new_data[CHOSEN_FLOAT_SENSORS] = [
            entry
            for entry in new_data[CHOSEN_FLOAT_SENSORS]
            if entry not in chosen_custom_unit_sensors
        ]
        # and add them to the CHOSEN_TEXT_SENSORS list instead
        new_data[CHOSEN_TEXT_SENSORS].extend(chosen_custom_unit_sensors)

        # now do the same with the FLOAT_DICT dict
        custom_unit_sensors = {
            k: v
            for k, v in new_data[FLOAT_DICT].items()
            if v.get("unit", "") == CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT
        }
        # remove sensors with custom units from the FLOAT_DICT
        new_data[FLOAT_DICT] = {
            k: v
            for k, v in new_data[FLOAT_DICT].items()
            if k not in custom_unit_sensors
        }
        # and add them to the TEXT_DICT instead
        new_data[TEXT_DICT].update(custom_unit_sensors)

    def migrate_to_v7(new_data: dict[str, Any]):
        new_data.setdefault(PENDING_DICT, {})
        new_data.setdefault(CHOSEN_PENDING_SENSORS, [])

    def migrate_to_v8(new_data: dict[str, Any]):
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        chosen_text_sensors = new_data[CHOSEN_TEXT_SENSORS]
        chosen_writable_sensors = new_data[CHOSEN_WRITABLE_SENSORS]
        to_be_disabled = [
            entity
            for entity in chosen_text_sensors
            if new_data[TEXT_DICT][entity]["unit"]
            in [CUSTOM_UNIT_TIMESLOT, CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE]
            and entity + "_writable" in chosen_writable_sensors
        ]
        entities_to_disable = [
            entity for entity in entities if entity.unique_id in to_be_disabled
        ]
        for entity_entry in entities_to_disable:
            entity_registry.async_update_entity(
                entity_entry.entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
            )

    def migrate_to_v9(new_data: dict[str, Any]):
        # Stable identity: unique_ids from "IP + translated name" -> "stable id +
        # node url"; entity_id is kept, so history/automations survive. No user
        # name yet, so freeze the current IP as the id (konzept-v2) - this also
        # matches the host-based diagnostic entities, which need no extra rewrite.
        stable_id = str(new_data.get(CONF_HOST, "")).replace(".", "_")
        new_data[STABLE_ID] = stable_id

        # Remap each chosen-list against its OWN dict only. A shared map is
        # unsafe: two same-named nodes share a key across dicts, so the last
        # rebuild clobbers it -> chosen points at the wrong dict (KeyError).
        combined_map: dict[str, str] = {}

        def _rebuild(dict_name: str, chosen_name: str, writable: bool):
            local_map: dict[str, str] = {}
            old_dict = new_data.get(dict_name, {})
            if isinstance(old_dict, dict):
                rebuilt: dict[str, Any] = {}
                for old_key, endpoint in old_dict.items():
                    url = endpoint.get("url", "") if isinstance(endpoint, dict) else ""
                    if not url:
                        # keep untouched if we cannot derive a stable id
                        rebuilt[old_key] = endpoint
                        continue
                    new_key = f"eta_{stable_id}_{url.strip('/').replace('/', '_')}"
                    if writable:
                        new_key += "_writable"
                    local_map[old_key] = new_key
                    combined_map.setdefault(old_key, new_key)
                    rebuilt[new_key] = endpoint
                new_data[dict_name] = rebuilt

            old_list = new_data.get(chosen_name, [])
            if isinstance(old_list, list):
                new_data[chosen_name] = [local_map.get(item, item) for item in old_list]

        _rebuild(FLOAT_DICT, CHOSEN_FLOAT_SENSORS, writable=False)
        _rebuild(SWITCHES_DICT, CHOSEN_SWITCHES, writable=False)
        _rebuild(TEXT_DICT, CHOSEN_TEXT_SENSORS, writable=False)
        _rebuild(PENDING_DICT, CHOSEN_PENDING_SENSORS, writable=False)
        _rebuild(WRITABLE_DICT, CHOSEN_WRITABLE_SENSORS, writable=True)

        # Host/port utility entities (errors, resend button, nbr/latest error)
        # aren't in the dicts; swap their IP prefix for the stable id.
        host_slug = str(new_data.get(CONF_HOST, "")).replace(".", "_")
        old_prefix = "eta_" + host_slug + "_"
        new_prefix = "eta_" + stable_id + "_"

        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        assigned: set[str] = set()
        for entity_entry in entities:
            uid = entity_entry.unique_id
            new_unique_id = combined_map.get(uid)
            if new_unique_id is None and host_slug and uid.startswith(old_prefix):
                new_unique_id = new_prefix + uid[len(old_prefix) :]
            if new_unique_id is None or new_unique_id == uid:
                continue
            if new_unique_id in assigned:
                _LOGGER.warning(
                    "Skipping unique_id migration for %s: target %s already assigned",
                    entity_entry.entity_id,
                    new_unique_id,
                )
                continue
            entity_registry.async_update_entity(
                entity_entry.entity_id, new_unique_id=new_unique_id
            )
            assigned.add(new_unique_id)

    def _get_current_data():
        current_data = config_entry.data.copy()
        if config_entry.options:
            current_data.update(config_entry.options)
        return current_data

    _LOGGER.debug("Migrating from version %s", config_entry.version)

    current_version = config_entry.version
    new_version = EtaFlowHandler.VERSION
    new_data = _get_current_data()
    is_migrated = False

    if current_version == 1:
        new_data[WRITABLE_DICT] = []
        new_data[CHOSEN_WRITABLE_SENSORS] = []
        current_version = 2
        is_migrated = True
    if current_version == 2:
        new_data[FORCE_LEGACY_MODE] = False
        current_version = 3
        is_migrated = True
    if current_version in (3, 4, 5):
        migrate_to_v6(new_data)
        current_version = 6
        is_migrated = True
    if current_version == 6:
        migrate_to_v7(new_data)
        current_version = 7
        is_migrated = True
    if current_version == 7:
        migrate_to_v8(new_data)
        current_version = 8
        is_migrated = True
    if current_version == 8:
        migrate_to_v9(new_data)
        current_version = 9
        is_migrated = True
    if is_migrated:
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            options={},
            version=new_version,
        )
    if not is_migrated:
        _LOGGER.warning("No migration path to version %s found", new_version)
        return True

    _LOGGER.info("Migration to version %s successful", new_version)
    return True


async def options_update_listener(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove config entry from domain.
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
