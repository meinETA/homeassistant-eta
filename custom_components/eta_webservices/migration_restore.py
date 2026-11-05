"""Restore a config entry from the snapshot of the previous repository."""

import logging
from typing import Any

from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST, CONF_PORT, EntityCategory
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_KEY = f"{DOMAIN}.migration"
STORAGE_VERSION = 1
RESTORE_SNAPSHOT_ID = "restore_snapshot_id"
MIGRATION_GUIDE_URL = (
    "https://github.com/meinETA/homeassistant-eta/blob/main/docs/migration.md"
)

_LOGGER = logging.getLogger(__name__)


def _store(hass: core.HomeAssistant) -> Store[dict[str, Any]]:
    return Store(hass, STORAGE_VERSION, STORAGE_KEY)


async def async_find_snapshot(
    hass: core.HomeAssistant,
    entries: list[config_entries.ConfigEntry],
    current_version: int,
) -> tuple[str, dict[str, Any]] | None:
    """Return the first snapshot that is restorable and not configured yet."""
    configured = {
        (entry.data.get(CONF_HOST), str(entry.data.get(CONF_PORT))) for entry in entries
    }
    for snapshot_id, snapshot in (await _store(hass).async_load() or {}).items():
        data = snapshot["data"]
        address = (data.get(CONF_HOST), str(data.get(CONF_PORT)))
        if snapshot["version"] < current_version and address not in configured:
            return snapshot_id, snapshot
    return None


def _restore_devices(
    hass: core.HomeAssistant,
    entry: config_entries.ConfigEntry,
    snapshot: dict[str, Any],
) -> dict[tuple[tuple[str, str], ...], str]:
    registry = dr.async_get(hass)
    device_ids: dict[tuple[tuple[str, str], ...], str] = {}
    for stored in snapshot["devices"]:
        identifiers = tuple(
            sorted((item[0], item[1]) for item in stored["identifiers"])
        )
        device = registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers=set(identifiers),
            name=stored["name"],
        )
        registry.async_update_device(
            device.id,
            area_id=stored["area_id"],
            disabled_by=(
                dr.DeviceEntryDisabler(stored["disabled_by"])
                if stored["disabled_by"]
                else None
            ),
            labels=set(stored["labels"]),
            name_by_user=stored["name_by_user"],
        )
        device_ids[identifiers] = device.id
    return device_ids


def _restore_entities(
    hass: core.HomeAssistant,
    entry: config_entries.ConfigEntry,
    snapshot: dict[str, Any],
    device_ids: dict[tuple[tuple[str, str], ...], str],
) -> None:
    registry = er.async_get(hass)
    for stored in snapshot["entities"]:
        domain, _, object_id = stored["entity_id"].partition(".")
        identifiers = tuple(
            sorted((item[0], item[1]) for item in stored["device_identifiers"] or [])
        )
        restored = registry.async_get_or_create(
            domain,
            DOMAIN,
            stored["unique_id"],
            config_entry=entry,
            device_id=device_ids.get(identifiers),
            entity_category=(
                EntityCategory(stored["entity_category"])
                if stored["entity_category"]
                else None
            ),
            original_device_class=stored["original_device_class"],
            original_name=stored["original_name"],
            suggested_object_id=object_id,
            unit_of_measurement=stored["unit_of_measurement"],
        )
        registry.async_update_entity(
            restored.entity_id,
            area_id=stored["area_id"],
            disabled_by=(
                er.RegistryEntryDisabler(stored["disabled_by"])
                if stored["disabled_by"]
                else None
            ),
            hidden_by=(
                er.RegistryEntryHider(stored["hidden_by"])
                if stored["hidden_by"]
                else None
            ),
            icon=stored["icon"],
            labels=set(stored["labels"]),
            name=stored["name"],
            new_entity_id=stored["entity_id"],
        )
        for option_domain, options in stored["options"].items():
            registry.async_update_entity_options(
                stored["entity_id"], option_domain, options
            )


async def async_restore_registries(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry, snapshot_id: str
) -> None:
    """Recreate devices and entities with their previous identity."""
    snapshot = (await _store(hass).async_load() or {}).get(snapshot_id)
    if snapshot is None:
        _LOGGER.warning("ETA migration snapshot %s not found", snapshot_id)
        return
    device_ids = _restore_devices(hass, entry, snapshot)
    _restore_entities(hass, entry, snapshot, device_ids)
    _LOGGER.info(
        "Restored %d devices and %d entities from the migration snapshot",
        len(snapshot["devices"]),
        len(snapshot["entities"]),
    )


async def async_remove_snapshot(hass: core.HomeAssistant, snapshot_id: str) -> None:
    """Forget a restored snapshot."""
    store = _store(hass)
    snapshots = await store.async_load() or {}
    snapshots.pop(snapshot_id, None)
    if snapshots:
        await store.async_save(snapshots)
    else:
        await store.async_remove()
