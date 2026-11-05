"""Tests for restoring a setup from the migration snapshot."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

from custom_components.eta_webservices import migration_restore
from custom_components.eta_webservices.config_flow import EtaFlowHandler
from custom_components.eta_webservices.migration_restore import (
    RESTORE_SNAPSHOT_ID,
    async_find_snapshot,
    async_remove_snapshot,
    async_restore_registries,
)
from homeassistant.const import CONF_HOST, CONF_PORT

IDENTIFIERS = [["eta_webservices", "eta_1_2_3_4_8080"]]


def _snapshot(version=8, host="1.2.3.4"):
    return {
        "version": version,
        "minor_version": 1,
        "title": f"ETA at {host}",
        "data": {CONF_HOST: host, CONF_PORT: 8080},
        "devices": [
            {
                "identifiers": IDENTIFIERS,
                "name": "ETA",
                "name_by_user": "Boiler",
                "area_id": "cellar",
                "disabled_by": None,
                "labels": ["heating"],
            }
        ],
        "entities": [
            {
                "entity_id": "sensor.eta_old",
                "unique_id": "old_unique_id",
                "device_identifiers": IDENTIFIERS,
                "name": "Custom name",
                "icon": None,
                "area_id": None,
                "disabled_by": "user",
                "hidden_by": None,
                "labels": [],
                "options": {"sensor": {"suggested_display_precision": 1}},
                "original_name": "Old",
                "original_device_class": None,
                "unit_of_measurement": "kg",
                "entity_category": None,
            }
        ],
    }


def _store(snapshots):
    store = Mock()
    store.async_load = AsyncMock(return_value=snapshots)
    store.async_save = AsyncMock()
    store.async_remove = AsyncMock()
    return store


async def test_find_snapshot_returns_unconfigured_old_entry():
    """Find snapshot returns unconfigured old entry."""
    with patch.object(
        migration_restore, "_store", return_value=_store({"a": _snapshot()})
    ):
        assert await async_find_snapshot(Mock(), [], 9) == ("a", _snapshot())


async def test_find_snapshot_skips_configured_address():
    """Find snapshot skips configured address."""
    entry = Mock(data={CONF_HOST: "1.2.3.4", CONF_PORT: "8080"})
    with patch.object(
        migration_restore, "_store", return_value=_store({"a": _snapshot()})
    ):
        assert await async_find_snapshot(Mock(), [entry], 9) is None


async def test_find_snapshot_skips_current_version():
    """Find snapshot skips current version."""
    with patch.object(
        migration_restore, "_store", return_value=_store({"a": _snapshot(version=9)})
    ):
        assert await async_find_snapshot(Mock(), [], 9) is None


async def test_restore_recreates_registry_identity():
    """Restore recreates registry identity."""
    device_registry = MagicMock()
    device_registry.async_get_or_create.return_value = Mock(id="device")
    entity_registry = MagicMock()
    entity_registry.async_get_or_create.return_value = Mock(entity_id="sensor.new")
    entry = Mock(entry_id="entry")

    with (
        patch.object(
            migration_restore, "_store", return_value=_store({"a": _snapshot()})
        ),
        patch.object(migration_restore.dr, "async_get", return_value=device_registry),
        patch.object(migration_restore.er, "async_get", return_value=entity_registry),
    ):
        await async_restore_registries(Mock(), entry, "a")

    assert device_registry.async_update_device.call_args.kwargs["name_by_user"] == (
        "Boiler"
    )
    create = entity_registry.async_get_or_create.call_args
    assert create.args == ("sensor", "eta_webservices", "old_unique_id")
    assert create.kwargs["device_id"] == "device"
    update = entity_registry.async_update_entity.call_args
    assert update.args == ("sensor.new",)
    assert update.kwargs["new_entity_id"] == "sensor.eta_old"
    assert update.kwargs["disabled_by"] == "user"
    entity_registry.async_update_entity_options.assert_called_once_with(
        "sensor.eta_old", "sensor", {"suggested_display_precision": 1}
    )


async def test_restore_without_snapshot_changes_nothing():
    """Restore without snapshot changes nothing."""
    with (
        patch.object(migration_restore, "_store", return_value=_store({})),
        patch.object(migration_restore.dr, "async_get") as device_registry,
    ):
        await async_restore_registries(Mock(), Mock(), "missing")

    device_registry.assert_not_called()


async def test_remove_snapshot_keeps_other_entries():
    """Remove snapshot keeps other entries."""
    store = _store({"a": _snapshot(), "b": _snapshot()})
    with patch.object(migration_restore, "_store", return_value=store):
        await async_remove_snapshot(Mock(), "a")

    store.async_save.assert_awaited_once_with({"b": _snapshot()})
    store.async_remove.assert_not_awaited()


async def test_remove_last_snapshot_deletes_file():
    """Remove last snapshot deletes file."""
    store = _store({"a": _snapshot()})
    with patch.object(migration_restore, "_store", return_value=store):
        await async_remove_snapshot(Mock(), "a")

    store.async_remove.assert_awaited_once()


async def test_restore_step_creates_entry_in_old_version():
    """Restore step creates entry in old version."""
    flow = EtaFlowHandler()
    flow._restore_candidate = ("a", _snapshot())
    with patch.object(
        flow, "async_create_entry", side_effect=lambda **kwargs: dict(kwargs)
    ):
        result = await flow.async_step_restore()

    assert result["version"] == 8
    assert result["minor_version"] == 1
    assert result["data"][RESTORE_SNAPSHOT_ID] == "a"
