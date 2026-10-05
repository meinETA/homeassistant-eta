"""Tests for eta_webservices/__init__.py migrations."""

from copy import deepcopy
from unittest.mock import MagicMock, Mock, patch

import pytest

from custom_components.eta_webservices import (
    _apply_pending_rename,
    _sync_migration_issue,
    async_migrate_entry,
)
from custom_components.eta_webservices.const import (
    CHOSEN_FLOAT_SENSORS,
    CHOSEN_PENDING_SENSORS,
    CHOSEN_SWITCHES,
    CHOSEN_TEXT_SENSORS,
    CHOSEN_WRITABLE_SENSORS,
    CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
    CUSTOM_UNIT_TIMESLOT,
    CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE,
    FLOAT_DICT,
    FORCE_LEGACY_MODE,
    PENDING_DICT,
    RENAME_PENDING_FROM,
    STABLE_ID,
    SWITCHES_DICT,
    TEXT_DICT,
    WRITABLE_DICT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant


def _v9_key(url, writable=False, host="192.168.0.25"):
    """Return the url-based unique_id migrate_to_v9 assigns to an entry."""
    key = f"eta_{host.replace('.', '_')}_{url.strip('/').replace('/', '_')}"
    return key + "_writable" if writable else key


def _remap_data_to_v9(data, host="192.168.0.25"):
    """Rewrite dict keys + chosen lists to the v9 scheme, mirroring migrate_to_v9.

    Lets the pre-v9 key-based expectations in these tests match the url-based
    unique_ids the full migration now produces.
    """
    stable_id = host.replace(".", "_")

    def rebuild(dict_name, chosen_name, writable):
        local_map = {}
        old_dict = data.get(dict_name, {})
        if isinstance(old_dict, dict):
            rebuilt = {}
            for old_key, endpoint in old_dict.items():
                url = endpoint.get("url", "") if isinstance(endpoint, dict) else ""
                if not url:
                    rebuilt[old_key] = endpoint
                    continue
                new_key = f"eta_{stable_id}_{url.strip('/').replace('/', '_')}"
                if writable:
                    new_key += "_writable"
                local_map[old_key] = new_key
                rebuilt[new_key] = endpoint
            data[dict_name] = rebuilt
        old_list = data.get(chosen_name, [])
        if isinstance(old_list, list):
            data[chosen_name] = [local_map.get(i, i) for i in old_list]

    rebuild(FLOAT_DICT, CHOSEN_FLOAT_SENSORS, False)
    rebuild(SWITCHES_DICT, CHOSEN_SWITCHES, False)
    rebuild(TEXT_DICT, CHOSEN_TEXT_SENSORS, False)
    rebuild(PENDING_DICT, CHOSEN_PENDING_SENSORS, False)
    rebuild(WRITABLE_DICT, CHOSEN_WRITABLE_SENSORS, True)
    return data


@pytest.mark.asyncio
async def test_async_migrate_entry_v5_to_v6(load_fixture):
    """Test migration from version 5 to 6 with real fixture data.

    This test verifies:
    - Entries in FLOAT_DICT without custom unit stay in FLOAT_DICT
    - Entries in FLOAT_DICT with custom unit move to TEXT_DICT
    - Chosen entries in CHOSEN_FLOAT_SENSORS with custom unit move to CHOSEN_TEXT_SENSORS
    - All other dicts and lists remain unchanged
    """
    # Setup
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()

    # Create config entry for version 5
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.version = 5
    config_entry.entry_id = "test_entry_id"

    # Load real fixture data from extracted ETA config
    fixture_file = load_fixture("v5_config_data.json")
    original_data = deepcopy(fixture_file["data"])
    original_options = deepcopy(fixture_file.get("options", {}))

    # Map fixture keys to const keys in data
    original_data[FLOAT_DICT] = original_data.pop("FLOAT_DICT")
    original_data[TEXT_DICT] = original_data.pop("TEXT_DICT", {})
    original_data[SWITCHES_DICT] = original_data.pop("SWITCHES_DICT", {})
    original_data[CHOSEN_FLOAT_SENSORS] = original_data.pop("chosen_float_sensors")
    original_data[CHOSEN_TEXT_SENSORS] = original_data.pop("chosen_text_sensors")
    original_data[CHOSEN_WRITABLE_SENSORS] = original_data.pop(
        "chosen_writable_sensors"
    )
    original_data[WRITABLE_DICT] = original_data.pop("WRITABLE_DICT", {})
    original_data[FORCE_LEGACY_MODE] = original_data.pop("force_legacy_mode")

    # Map fixture keys to const keys in data
    original_options[FLOAT_DICT] = original_options.pop("FLOAT_DICT")
    original_options[TEXT_DICT] = original_options.pop("TEXT_DICT", {})
    original_options[SWITCHES_DICT] = original_options.pop("SWITCHES_DICT", {})
    original_options[CHOSEN_FLOAT_SENSORS] = original_options.pop(
        "chosen_float_sensors"
    )
    original_options[CHOSEN_TEXT_SENSORS] = original_options.pop("chosen_text_sensors")
    original_options[CHOSEN_WRITABLE_SENSORS] = original_options.pop(
        "chosen_writable_sensors"
    )
    original_options[WRITABLE_DICT] = original_options.pop("WRITABLE_DICT", {})
    original_options[FORCE_LEGACY_MODE] = original_options.pop("force_legacy_mode")

    # Use deepcopy to ensure original_data is not modified by config_entry.data
    config_entry.data = deepcopy(original_data)
    config_entry.options = deepcopy(original_options)

    # Mock async_update_entry
    hass.config_entries.async_update_entry = Mock()

    # Execute migration (patch entity registry used by migrate_to_v8)
    with (
        patch("homeassistant.helpers.entity_registry.async_get") as mock_er_get,
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        mock_er_get.return_value = MagicMock()
        result = await async_migrate_entry(hass, config_entry)

    # Assertions
    assert result is True

    # Merge original options into original data for comparison
    original_data.update(original_options)
    # v9 rewrites unique_ids to the url-based scheme; align expectations.
    _remap_data_to_v9(original_data)

    # Get the data that was passed to async_update_entry
    hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = hass.config_entries.async_update_entry.call_args.kwargs
    new_data = call_kwargs["data"]
    new_options = call_kwargs.get("options", {})

    # Verify version was bumped beyond the starting version
    assert call_kwargs["version"] > config_entry.version

    # ===== FLOAT_DICT Assertions =====
    # Count entries with custom unit in original FLOAT_DICT
    original_float_count = len(original_data[FLOAT_DICT])
    custom_unit_entries = [
        k
        for k, v in original_data[FLOAT_DICT].items()
        if v.get("unit") == CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT
    ]
    expected_float_count = original_float_count - len(custom_unit_entries)

    # Entries with standard units should remain in FLOAT_DICT
    assert len(new_data[FLOAT_DICT]) == expected_float_count, (
        f"Expected {expected_float_count} entries in FLOAT_DICT, got {len(new_data[FLOAT_DICT])}"
    )

    # None of the entries in FLOAT_DICT should have custom unit
    for entry_key, entry_data in new_data[FLOAT_DICT].items():
        assert entry_data.get("unit") != CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT, (
            f"Entry {entry_key} with custom unit should not be in FLOAT_DICT"
        )

    # Verify that all non-custom-unit entries from original FLOAT_DICT are still present
    for orig_key, orig_data in original_data[FLOAT_DICT].items():
        if orig_data.get("unit") != CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT:
            assert orig_key in new_data[FLOAT_DICT], (
                f"Non-custom-unit entry {orig_key} should still be in FLOAT_DICT"
            )

    # ===== TEXT_DICT Assertions =====
    # All original text entries should still exist
    for orig_key in original_data[TEXT_DICT]:
        assert orig_key in new_data[TEXT_DICT], (
            f"Original text entry {orig_key} should still be in TEXT_DICT"
        )

    # All custom unit entries from FLOAT_DICT should now be in TEXT_DICT
    for custom_unit_key in custom_unit_entries:
        assert custom_unit_key in new_data[TEXT_DICT], (
            f"Entry {custom_unit_key} with custom unit should be in TEXT_DICT"
        )
        assert (
            new_data[TEXT_DICT][custom_unit_key]["unit"]
            == CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT
        ), f"Entry {custom_unit_key} should have custom unit in TEXT_DICT"

    # TEXT_DICT should have grown by the number of entries migrated
    original_text_count = len(original_data[TEXT_DICT])
    new_text_count = len(new_data[TEXT_DICT])
    migrated_count = new_text_count - original_text_count
    assert migrated_count == len(custom_unit_entries), (
        f"TEXT_DICT should have {len(custom_unit_entries)} more entries after migration, but has {migrated_count} more"
    )

    # ===== CHOSEN_FLOAT_SENSORS Assertions =====
    # Entries without custom unit should remain
    original_chosen_float = original_data[CHOSEN_FLOAT_SENSORS].copy()
    expected_chosen_float = [
        k for k in original_chosen_float if k not in custom_unit_entries
    ]

    assert set(new_data[CHOSEN_FLOAT_SENSORS]) == set(expected_chosen_float), (
        f"CHOSEN_FLOAT_SENSORS mismatch. Expected {set(expected_chosen_float)}, got {set(new_data[CHOSEN_FLOAT_SENSORS])}"
    )

    # Entry with custom unit should be removed from CHOSEN_FLOAT_SENSORS
    for custom_unit_key in custom_unit_entries:
        assert custom_unit_key not in new_data[CHOSEN_FLOAT_SENSORS], (
            f"Custom unit entry {custom_unit_key} should be removed from CHOSEN_FLOAT_SENSORS"
        )

    # ===== CHOSEN_TEXT_SENSORS Assertions =====
    # Original entries should still be there
    original_chosen_text = original_data[CHOSEN_TEXT_SENSORS].copy()
    # Add custom unit entries that were in CHOSEN_FLOAT_SENSORS
    custom_unit_in_chosen = [
        k for k in custom_unit_entries if k in original_chosen_float
    ]
    expected_chosen_text = original_chosen_text + custom_unit_in_chosen

    assert set(new_data[CHOSEN_TEXT_SENSORS]) == set(expected_chosen_text), (
        f"CHOSEN_TEXT_SENSORS mismatch. Expected {set(expected_chosen_text)}, got {set(new_data[CHOSEN_TEXT_SENSORS])}"
    )

    # Entries with custom unit that were in CHOSEN_FLOAT_SENSORS should be added
    for custom_unit_key in custom_unit_entries:
        if custom_unit_key in original_chosen_float:
            assert custom_unit_key in new_data[CHOSEN_TEXT_SENSORS], (
                f"Custom unit entry {custom_unit_key} should be added to CHOSEN_TEXT_SENSORS"
            )

    # ===== Other Assertions =====
    # Other fields should remain unchanged
    assert new_data[CHOSEN_WRITABLE_SENSORS] == original_data[CHOSEN_WRITABLE_SENSORS]
    assert new_data[WRITABLE_DICT] == original_data[WRITABLE_DICT]
    assert new_data[FORCE_LEGACY_MODE] == original_data[FORCE_LEGACY_MODE]

    # Preserve additional config fields
    assert "host" in new_data
    assert "port" in new_data

    # ===== Options Merge Assertions =====
    # Verify that options were merged into the migrated data
    # The migrate_to_v6() function merges options into new_data before processing
    assert new_options == {}, "Options should be empty after migration"


@pytest.mark.asyncio
async def test_migration_v6_to_v7_adds_pending_fields():
    """Migration from v6 to v7 must add PENDING_DICT={} and CHOSEN_PENDING_SENSORS=[].

    Existing sensors must not be affected.
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.version = 6
    config_entry.entry_id = "test_entry_id"

    float_sensor_key = "eta_192_168_0_25__kessel_kesseltemperatur"
    float_sensor = {
        "url": "/120/10101/0/0/12080",
        "unit": "°C",
        "endpoint_type": "DEFAULT",
        "friendly_name": "Kessel > Kesseltemperatur",
        "value": 72.3,
        "valid_values": None,
    }

    config_entry.data = {
        FLOAT_DICT: {float_sensor_key: float_sensor},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {},
        CHOSEN_FLOAT_SENSORS: [float_sensor_key],
        CHOSEN_SWITCHES: [],
        CHOSEN_TEXT_SENSORS: [],
        CHOSEN_WRITABLE_SENSORS: [],
        FORCE_LEGACY_MODE: False,
        "host": "192.168.0.25",
        "port": "8080",
    }
    config_entry.options = {}

    with (
        patch("homeassistant.helpers.entity_registry.async_get") as mock_er_get,
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        mock_er_get.return_value = MagicMock()
        result = await async_migrate_entry(hass, config_entry)

    assert result is True

    hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = hass.config_entries.async_update_entry.call_args.kwargs
    new_data = call_kwargs["data"]

    # Version must be bumped beyond the starting version.
    assert call_kwargs["version"] > config_entry.version

    # New fields must be present and empty.
    assert PENDING_DICT in new_data, "PENDING_DICT must be added by migration"
    assert new_data[PENDING_DICT] == {}, "PENDING_DICT must be empty after migration"
    assert CHOSEN_PENDING_SENSORS in new_data, (
        "CHOSEN_PENDING_SENSORS must be added by migration"
    )
    assert new_data[CHOSEN_PENDING_SENSORS] == [], (
        "CHOSEN_PENDING_SENSORS must be empty after migration"
    )

    # Existing sensors must survive migration (v9 rewrites the key to url-based).
    new_key = _v9_key(float_sensor["url"])
    assert new_key in new_data[FLOAT_DICT], (
        "Existing float sensor must survive migration"
    )
    assert new_data[CHOSEN_FLOAT_SENSORS] == [new_key], (
        "Existing chosen float sensors must survive migration"
    )


@pytest.mark.asyncio
async def test_migration_v6_to_v7_with_options():
    """Migration from v6 to v7 preserves options-overridden sensor lists."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.version = 6
    config_entry.entry_id = "test_entry_id"

    float_sensor_key = "eta_192_168_0_25__kessel_kesseltemperatur"
    float_sensor = {
        "url": "/120/10101/0/0/12080",
        "unit": "°C",
        "endpoint_type": "DEFAULT",
        "friendly_name": "Kessel > Kesseltemperatur",
        "value": 72.3,
        "valid_values": None,
    }

    # Baseline data — minimal chosen lists
    config_entry.data = {
        FLOAT_DICT: {float_sensor_key: float_sensor},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {},
        CHOSEN_FLOAT_SENSORS: [],
        CHOSEN_SWITCHES: [],
        CHOSEN_TEXT_SENSORS: [],
        CHOSEN_WRITABLE_SENSORS: [],
        FORCE_LEGACY_MODE: False,
        "host": "192.168.0.25",
        "port": "8080",
    }
    # Options override chosen list
    config_entry.options = {
        FLOAT_DICT: {float_sensor_key: float_sensor},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {},
        CHOSEN_FLOAT_SENSORS: [float_sensor_key],
        CHOSEN_SWITCHES: [],
        CHOSEN_TEXT_SENSORS: [],
        CHOSEN_WRITABLE_SENSORS: [],
        FORCE_LEGACY_MODE: False,
    }

    with (
        patch("homeassistant.helpers.entity_registry.async_get") as mock_er_get,
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        mock_er_get.return_value = MagicMock()
        result = await async_migrate_entry(hass, config_entry)
    assert result is True

    call_kwargs = hass.config_entries.async_update_entry.call_args.kwargs
    new_data = call_kwargs["data"]
    new_options = call_kwargs.get("options", {})

    assert call_kwargs["version"] > config_entry.version
    assert PENDING_DICT in new_data
    assert new_data[PENDING_DICT] == {}
    assert CHOSEN_PENDING_SENSORS in new_data
    assert new_data[CHOSEN_PENDING_SENSORS] == []
    # The migration merges options into data, so the options-overridden
    # CHOSEN_FLOAT_SENSORS wins over data's empty list (v9 key is url-based).
    new_key = _v9_key(float_sensor["url"])
    assert new_data[CHOSEN_FLOAT_SENSORS] == [new_key]
    # The float sensor from data must still be present
    assert new_key in new_data[FLOAT_DICT]

    assert new_options == {}, "Options should be empty after migration"


@pytest.mark.asyncio
async def test_async_migrate_entry_v1_to_v7():
    """Test the full migration path from version 1 to 8.

    v1 data lacks WRITABLE_DICT, CHOSEN_WRITABLE_SENSORS, and FORCE_LEGACY_MODE.
    The migration must:
    - Add those three fields with their default values.
    - Move float sensors whose unit is CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT to
      TEXT_DICT and adjust CHOSEN_FLOAT/TEXT_SENSORS accordingly (migrate_to_v6).
    - Add PENDING_DICT and CHOSEN_PENDING_SENSORS (migrate_to_v7).
    - Store the result in a single flat data dict, clear options, and set version=8.
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()

    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.version = 1
    config_entry.entry_id = "test_entry_id"
    config_entry.options = {}
    config_entry.data = {
        "host": "192.168.0.25",
        "port": 8080,
        FLOAT_DICT: {
            "sensor_normal": {
                "unit": "%",
                "value": 42.0,
                "url": "/uri/normal",
                "endpoint_type": "DEFAULT",
                "friendly_name": "Normal sensor",
                "valid_values": None,
            },
            "sensor_custom": {
                "unit": CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
                "value": 480.0,
                "url": "/uri/custom",
                "endpoint_type": "DEFAULT",
                "friendly_name": "Custom unit sensor",
                "valid_values": None,
            },
        },
        TEXT_DICT: {},
        CHOSEN_FLOAT_SENSORS: ["sensor_normal", "sensor_custom"],
        CHOSEN_TEXT_SENSORS: [],
    }

    hass.config_entries.async_update_entry = Mock()

    with (
        patch("homeassistant.helpers.entity_registry.async_get") as mock_er_get,
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        mock_er_get.return_value = MagicMock()
        result = await async_migrate_entry(hass, config_entry)

    assert result is True

    hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = hass.config_entries.async_update_entry.call_args.kwargs

    assert call_kwargs["version"] > config_entry.version
    assert call_kwargs.get("options") == {}

    new_data = call_kwargs["data"]

    # Fields added by the v1-specific step.
    assert new_data[WRITABLE_DICT] == []
    assert new_data[CHOSEN_WRITABLE_SENSORS] == []
    assert new_data[FORCE_LEGACY_MODE] is False

    # Fields added by migrate_to_v7.
    assert new_data[PENDING_DICT] == {}
    assert new_data[CHOSEN_PENDING_SENSORS] == []

    # v9 rewrites unique_ids to the url-based scheme.
    normal_key = _v9_key("/uri/normal")
    custom_key = _v9_key("/uri/custom")

    # migrate_to_v6: custom-unit sensor must leave FLOAT_DICT.
    assert normal_key in new_data[FLOAT_DICT]
    assert custom_key not in new_data[FLOAT_DICT]

    # migrate_to_v6: custom-unit sensor must arrive in TEXT_DICT.
    assert custom_key in new_data[TEXT_DICT]
    assert new_data[TEXT_DICT][custom_key]["unit"] == CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT

    # migrate_to_v6: CHOSEN_FLOAT_SENSORS updated, CHOSEN_TEXT_SENSORS updated.
    assert normal_key in new_data[CHOSEN_FLOAT_SENSORS]
    assert custom_key not in new_data[CHOSEN_FLOAT_SENSORS]
    assert custom_key in new_data[CHOSEN_TEXT_SENSORS]

    # Connection fields must be preserved.
    assert new_data["host"] == "192.168.0.25"
    assert new_data["port"] == 8080


def _make_v7_config_entry(
    text_dict=None, chosen_text=None, writable_dict=None, chosen_writable=None
):
    """Build a minimal v7 config entry for migration testing."""
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.version = 7
    config_entry.entry_id = "test_entry_id"
    config_entry.options = {}
    config_entry.data = {
        FLOAT_DICT: {},
        SWITCHES_DICT: {},
        TEXT_DICT: text_dict or {},
        WRITABLE_DICT: writable_dict or {},
        CHOSEN_FLOAT_SENSORS: [],
        CHOSEN_SWITCHES: [],
        CHOSEN_TEXT_SENSORS: chosen_text or [],
        CHOSEN_WRITABLE_SENSORS: chosen_writable or [],
        FORCE_LEGACY_MODE: False,
        PENDING_DICT: {},
        CHOSEN_PENDING_SENSORS: [],
        "host": "192.168.0.25",
        "port": 8080,
    }
    return config_entry


def _make_entity_entry(unique_id, entity_id):
    entry = MagicMock()
    entry.unique_id = unique_id
    entry.entity_id = entity_id
    return entry


@pytest.mark.asyncio
async def test_migration_v7_to_v8_disables_timeslot_with_writable_counterpart():
    """migrate_to_v8 must disable text-side timeslot entities that have a writable counterpart.

    When a sensor key like 'ts_key' appears in CHOSEN_TEXT_SENSORS with a timeslot unit
    AND 'ts_key_writable' appears in CHOSEN_WRITABLE_SENSORS, the corresponding entity
    registry entry for 'ts_key' must be disabled by the integration.
    Non-timeslot and timeslot-without-writable entries must be left untouched.
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    timeslot_key = "ts_monday"
    timeslot_plus_temp_key = "ts_tuesday"
    standalone_timeslot_key = (
        "ts_wednesday"  # no writable counterpart → must NOT be disabled
    )
    regular_text_key = "text_status"

    text_dict = {
        timeslot_key: {
            "unit": CUSTOM_UNIT_TIMESLOT,
            "url": "/u/1",
            "endpoint_type": "DEFAULT",
            "friendly_name": "Mon",
            "value": "",
            "valid_values": None,
        },
        timeslot_plus_temp_key: {
            "unit": CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE,
            "url": "/u/2",
            "endpoint_type": "DEFAULT",
            "friendly_name": "Tue",
            "value": "",
            "valid_values": None,
        },
        standalone_timeslot_key: {
            "unit": CUSTOM_UNIT_TIMESLOT,
            "url": "/u/3",
            "endpoint_type": "DEFAULT",
            "friendly_name": "Wed",
            "value": "",
            "valid_values": None,
        },
        regular_text_key: {
            "unit": "",
            "url": "/u/4",
            "endpoint_type": "TEXT",
            "friendly_name": "Status",
            "value": "on",
            "valid_values": None,
        },
    }
    writable_dict = {
        timeslot_key + "_writable": {
            "unit": CUSTOM_UNIT_TIMESLOT,
            "url": "/u/1",
            "endpoint_type": "DEFAULT",
            "friendly_name": "Mon",
            "value": "",
            "valid_values": {},
        },
        timeslot_plus_temp_key + "_writable": {
            "unit": CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE,
            "url": "/u/2",
            "endpoint_type": "DEFAULT",
            "friendly_name": "Tue",
            "value": "",
            "valid_values": {},
        },
    }
    chosen_text = [
        timeslot_key,
        timeslot_plus_temp_key,
        standalone_timeslot_key,
        regular_text_key,
    ]
    chosen_writable = [timeslot_key + "_writable", timeslot_plus_temp_key + "_writable"]

    config_entry = _make_v7_config_entry(
        text_dict, chosen_text, writable_dict, chosen_writable
    )

    # Simulate two existing entity registry entries for the to-be-disabled sensors.
    entity_entries = [
        _make_entity_entry(timeslot_key, "sensor.ts_monday"),
        _make_entity_entry(timeslot_plus_temp_key, "sensor.ts_tuesday"),
        _make_entity_entry(standalone_timeslot_key, "sensor.ts_wednesday"),
        _make_entity_entry(regular_text_key, "sensor.text_status"),
    ]

    mock_registry = MagicMock()
    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=entity_entries,
        ),
    ):
        result = await async_migrate_entry(hass, config_entry)

    assert result is True
    assert (
        hass.config_entries.async_update_entry.call_args.kwargs["version"]
        > config_entry.version
    )

    # Only the two entries with writable counterparts must have been disabled.
    # (v9 also rewrites unique_ids via new_unique_id=; count only the disables.)
    disabled_entity_ids = {
        call.kwargs["entity_id"] if "entity_id" in call.kwargs else call.args[0]
        for call in mock_registry.async_update_entity.call_args_list
        if "disabled_by" in call.kwargs
    }
    assert "sensor.ts_monday" in disabled_entity_ids
    assert "sensor.ts_tuesday" in disabled_entity_ids
    assert "sensor.ts_wednesday" not in disabled_entity_ids
    assert "sensor.text_status" not in disabled_entity_ids
    assert len(disabled_entity_ids) == 2


@pytest.mark.asyncio
async def test_migration_v7_to_v8_no_entities_to_disable():
    """migrate_to_v8 must not touch the entity registry when there are no timeslot
    sensors with writable counterparts — including when the registry is empty.
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    # Only a plain float sensor — no timeslot sensors at all.
    config_entry = _make_v7_config_entry(
        chosen_text=["regular_text"],
        text_dict={
            "regular_text": {
                "unit": "",
                "url": "/u/1",
                "endpoint_type": "TEXT",
                "friendly_name": "S",
                "value": "x",
                "valid_values": None,
            }
        },
    )

    mock_registry = MagicMock()
    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        result = await async_migrate_entry(hass, config_entry)

    assert result is True
    mock_registry.async_update_entity.assert_not_called()


@pytest.mark.asyncio
async def test_migration_v7_to_v8_timeslot_without_writable_not_disabled():
    """Timeslot text sensors that have no writable counterpart must not be disabled."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    timeslot_key = "ts_standalone"
    config_entry = _make_v7_config_entry(
        text_dict={
            timeslot_key: {
                "unit": CUSTOM_UNIT_TIMESLOT,
                "url": "/u/1",
                "endpoint_type": "DEFAULT",
                "friendly_name": "S",
                "value": "",
                "valid_values": None,
            }
        },
        chosen_text=[timeslot_key],
        chosen_writable=[],  # no writable counterpart
    )

    entity_entries = [_make_entity_entry(timeslot_key, "sensor.ts_standalone")]
    mock_registry = MagicMock()
    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=entity_entries,
        ),
    ):
        result = await async_migrate_entry(hass, config_entry)

    assert result is True
    # v9 may rewrite the unique_id, but nothing must be disabled here.
    disabled = [
        call
        for call in mock_registry.async_update_entity.call_args_list
        if "disabled_by" in call.kwargs
    ]
    assert disabled == []


@pytest.mark.asyncio
async def test_migrate_to_v9_rewrites_unique_ids_to_url_scheme():
    """v9 re-keys dicts + chosen lists from the IP-name scheme to the IP-url
    scheme and rewrites the matching entity registry unique_ids.
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.version = 8
    config_entry.entry_id = "test_entry_id"
    config_entry.options = {}

    old_float = "eta_192_168_0_25_kessel_kesseltemperatur"
    old_writable = "eta_192_168_0_25_kessel_soll_writable"
    config_entry.data = {
        FLOAT_DICT: {old_float: {"url": "/120/10101/0/0/12080", "unit": "°C"}},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {old_writable: {"url": "/120/10101/0/0/12081", "unit": "°C"}},
        PENDING_DICT: {},
        CHOSEN_FLOAT_SENSORS: [old_float],
        CHOSEN_SWITCHES: [],
        CHOSEN_TEXT_SENSORS: [],
        CHOSEN_WRITABLE_SENSORS: [old_writable],
        CHOSEN_PENDING_SENSORS: [],
        FORCE_LEGACY_MODE: False,
        "host": "192.168.0.25",
        "port": "8080",
    }

    entities = [
        _make_entity_entry(old_float, "sensor.eta_192_168_0_25_kesseltemperatur"),
        _make_entity_entry(old_writable, "number.eta_192_168_0_25_soll"),
    ]
    mock_registry = MagicMock()
    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=entities,
        ),
    ):
        result = await async_migrate_entry(hass, config_entry)

    assert result is True
    new_data = hass.config_entries.async_update_entry.call_args.kwargs["data"]

    # stable_id frozen from the IP.
    assert new_data[STABLE_ID] == "192_168_0_25"

    new_float = _v9_key("/120/10101/0/0/12080")
    new_writable = _v9_key("/120/10101/0/0/12081", writable=True)

    # Dicts and chosen lists re-keyed to the url scheme.
    assert new_float in new_data[FLOAT_DICT]
    assert old_float not in new_data[FLOAT_DICT]
    assert new_writable in new_data[WRITABLE_DICT]
    assert new_data[CHOSEN_FLOAT_SENSORS] == [new_float]
    assert new_data[CHOSEN_WRITABLE_SENSORS] == [new_writable]

    # Registry unique_ids rewritten to match.
    rewrites = {
        (call.args[0], call.kwargs["new_unique_id"])
        for call in mock_registry.async_update_entity.call_args_list
        if "new_unique_id" in call.kwargs
    }
    assert ("sensor.eta_192_168_0_25_kesseltemperatur", new_float) in rewrites
    assert ("number.eta_192_168_0_25_soll", new_writable) in rewrites


@pytest.mark.asyncio
async def test_migrate_to_v9_keeps_entries_without_url():
    """An entry without a url yields no stable key and is kept under its old key."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.version = 8
    config_entry.entry_id = "test_entry_id"
    config_entry.options = {}

    old_key = "eta_192_168_0_25_legacy_no_url"
    config_entry.data = {
        FLOAT_DICT: {old_key: {"unit": "°C"}},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {},
        PENDING_DICT: {},
        CHOSEN_FLOAT_SENSORS: [old_key],
        CHOSEN_SWITCHES: [],
        CHOSEN_TEXT_SENSORS: [],
        CHOSEN_WRITABLE_SENSORS: [],
        CHOSEN_PENDING_SENSORS: [],
        FORCE_LEGACY_MODE: False,
        "host": "192.168.0.25",
        "port": "8080",
    }

    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=MagicMock(),
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        result = await async_migrate_entry(hass, config_entry)

    assert result is True
    new_data = hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert old_key in new_data[FLOAT_DICT]
    assert new_data[CHOSEN_FLOAT_SENSORS] == [old_key]


def test_apply_pending_rename_rewrites_unique_and_entity_id():
    """The opt-in migration swaps the old stable-id prefix for the new one on
    both the unique_id and the entity_id, then clears the marker.
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        RENAME_PENDING_FROM: "192_168_0_25",
        STABLE_ID: "haus",
    }

    ent = _make_entity_entry(
        "eta_192_168_0_25_120_10101_0_0_12080",
        "sensor.eta_192_168_0_25_kesseltemperatur",
    )
    mock_registry = MagicMock()
    mock_registry.async_get.return_value = None  # no entity_id collision

    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[ent],
        ),
    ):
        _apply_pending_rename(hass, entry)

    call = mock_registry.async_update_entity.call_args
    assert call.args[0] == "sensor.eta_192_168_0_25_kesseltemperatur"
    assert call.kwargs["new_unique_id"] == "eta_haus_120_10101_0_0_12080"
    assert call.kwargs["new_entity_id"] == "sensor.haus_kesseltemperatur"

    # Marker removed from the persisted data.
    updated = hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert RENAME_PENDING_FROM not in updated


def test_apply_pending_rename_noop_without_marker():
    """Without the marker the opt-in migration is a no-op."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = Mock()

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {STABLE_ID: "haus"}

    mock_registry = MagicMock()
    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
            return_value=[],
        ),
    ):
        _apply_pending_rename(hass, entry)

    mock_registry.async_update_entity.assert_not_called()
    hass.config_entries.async_update_entry.assert_not_called()


def test_sync_migration_issue_created_for_legacy_scheme():
    """Installs still on the IP scheme (no name) get the optional-migration issue."""
    hass = MagicMock(spec=HomeAssistant)
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {STABLE_ID: "192_168_0_25", "host": "192.168.0.25"}

    with (
        patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as create_issue,
        patch(
            "homeassistant.helpers.issue_registry.async_delete_issue"
        ) as delete_issue,
    ):
        _sync_migration_issue(hass, entry)

    delete_issue.assert_not_called()
    create_issue.assert_called_once()
    kwargs = create_issue.call_args.kwargs
    assert kwargs["is_fixable"] is False
    assert kwargs["translation_key"] == "legacy_scheme_migration"
    assert kwargs["translation_placeholders"]["old_prefix"] == "eta_192_168_0_25_"


def test_sync_migration_issue_cleared_when_named():
    """Once the entry carries a name, the issue is removed instead of created."""
    hass = MagicMock(spec=HomeAssistant)
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_NAME: "Haus", STABLE_ID: "haus"}

    with (
        patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as create_issue,
        patch(
            "homeassistant.helpers.issue_registry.async_delete_issue"
        ) as delete_issue,
    ):
        _sync_migration_issue(hass, entry)

    create_issue.assert_not_called()
    delete_issue.assert_called_once()
