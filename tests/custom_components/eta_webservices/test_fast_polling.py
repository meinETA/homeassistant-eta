"""Tests for the faster poll of the values shown on the plant card."""

from asyncio import Lock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_webservices.const import (
    CHOSEN_FLOAT_SENSORS,
    CHOSEN_SWITCHES,
    CHOSEN_TEXT_SENSORS,
    CHOSEN_WRITABLE_SENSORS,
    DOMAIN,
    FAST_UPDATE_LABEL_ID,
    FAST_UPDATE_LABEL_NAME,
    FLOAT_DICT,
    READ_LOCK,
    STABLE_ID,
    SWITCHES_DICT,
    TEXT_DICT,
    WRITABLE_DICT,
)
from custom_components.eta_webservices.coordinator import (
    ETAFastUpdateCoordinator,
    ETASensorUpdateCoordinator,
    ETAWritableUpdateCoordinator,
)
from custom_components.eta_webservices.topology import (
    Block,
    async_ensure_fast_label,
    async_fast_uris,
    card_entities,
    entity_uris,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import entity_registry as er, label_registry as lr

BOILER = "/112/10021/0/11109/0"
STATE = "/112/10021/0/0/12000"
SWITCH = "/112/10021/0/0/12080"
TOTAL = "/112/10021/0/0/12016"
SETPOINT = "/112/10101/0/0/12125"

_MODULE = "custom_components.eta_webservices.coordinator"


def _config() -> dict:
    return {
        CONF_HOST: "eta",
        CONF_PORT: 8080,
        FLOAT_DICT: {
            "boiler": {"url": BOILER, "unit": "°C"},
            "total": {"url": TOTAL, "unit": "kg"},
        },
        TEXT_DICT: {"state": {"url": STATE, "unit": ""}},
        SWITCHES_DICT: {
            "onoff": {
                "url": SWITCH,
                "valid_values": {"on_value": 1803, "off_value": 1802},
            }
        },
        WRITABLE_DICT: {"setpoint_writable": {"url": SETPOINT, "unit": "°C"}},
        CHOSEN_FLOAT_SENSORS: ["boiler", "total"],
        CHOSEN_TEXT_SENSORS: ["state"],
        CHOSEN_SWITCHES: ["onoff"],
        CHOSEN_WRITABLE_SENSORS: ["setpoint_writable"],
    }


class FakeApi:
    """Answers reads from a value table and records what was asked."""

    def __init__(self, values: dict) -> None:  # noqa: D107
        self.values = values
        self.asked: list[str] = []
        self.get_all_data = AsyncMock(side_effect=self._data)
        self.get_all_switch_states = AsyncMock(side_effect=self._switches)

    async def _data(self, queries):
        self.asked += list(queries)
        return {uri: self.values[uri] for uri in queries if uri in self.values}

    async def _switches(self, uris):
        self.asked += list(uris)
        return {uri: self.values[uri] for uri in uris if uri in self.values}


@pytest.fixture
def api():
    """Patch the coordinators' API with a value table."""
    fake = FakeApi(
        {BOILER: 45.3, STATE: "Heizen", SWITCH: 1803, TOTAL: 12345.0, SETPOINT: 21.0}
    )
    with (
        patch(f"{_MODULE}.async_get_clientsession"),
        patch(f"{_MODULE}.EtaAPI", return_value=fake),
        patch("homeassistant.helpers.frame.report_usage"),
    ):
        yield fake


async def _coordinators(config: dict, card: set[str]):
    sensor = ETASensorUpdateCoordinator(MagicMock(), config)
    writable = ETAWritableUpdateCoordinator(MagicMock(), config)
    sensor.data = await sensor._async_update_data()
    writable.data = await writable._async_update_data()
    sensor.last_update_success = True
    sensor.async_update_listeners = MagicMock()
    writable.async_update_listeners = MagicMock()
    fast = ETAFastUpdateCoordinator(MagicMock(), config, MagicMock(), sensor, writable)
    patcher = patch(f"{_MODULE}.async_fast_uris", return_value=card)
    patcher.start()
    return sensor, writable, fast, patcher


async def test_fast_poll_reads_only_card_values(api):
    """Only the card's uris are read; unchanged values notify nobody."""
    sensor, writable, fast, patcher = await _coordinators(
        _config(), {BOILER, SWITCH, SETPOINT}
    )
    try:
        api.asked.clear()
        assert await fast._async_update_data() == 0
        assert sorted(api.asked) == sorted([BOILER, SWITCH, SETPOINT])
        sensor.async_update_listeners.assert_not_called()
        writable.async_update_listeners.assert_not_called()
    finally:
        patcher.stop()


async def test_fast_poll_updates_changed_values(api):
    """Changed values reach the regular coordinators, as the regular poll would."""
    sensor, writable, fast, patcher = await _coordinators(
        _config(), {BOILER, SWITCH, SETPOINT}
    )
    try:
        api.values.update({BOILER: 47.0, SWITCH: 1802, SETPOINT: 22.0})
        assert await fast._async_update_data() == 3
        assert sensor.data[BOILER] == 47.0
        assert sensor.data[SWITCH] is False
        assert writable.data[SETPOINT] == 22.0
        assert sensor.data[TOTAL] == 12345.0  # not on the card, untouched
        sensor.async_update_listeners.assert_called_once()
        writable.async_update_listeners.assert_called_once()
        # identical to what the regular poll reads now
        assert await sensor._async_update_data() == sensor.data
    finally:
        patcher.stop()


async def test_fast_poll_skips_while_regular_poll_reads(api):
    """Fast and regular polls never read at the same time."""
    config = {**_config(), READ_LOCK: Lock()}
    _sensor, _writable, fast, patcher = await _coordinators(config, {BOILER})
    try:
        api.asked.clear()
        async with config[READ_LOCK]:
            assert await fast._async_update_data() == 0
        assert api.asked == []
    finally:
        patcher.stop()


async def test_fast_poll_skips_after_failed_regular_poll(api):
    """While the terminal is unreachable only the regular poll keeps trying."""
    sensor, _writable, fast, patcher = await _coordinators(_config(), {BOILER})
    try:
        sensor.last_update_success = False
        api.asked.clear()
        assert await fast._async_update_data() == 0
        assert api.asked == []
    finally:
        patcher.stop()


async def test_fast_poll_without_card_values_reads_nothing(api):
    """A plant without card values sends no request."""
    _sensor, _writable, fast, patcher = await _coordinators(_config(), set())
    try:
        api.asked.clear()
        assert await fast._async_update_data() == 0
        assert api.asked == []
    finally:
        patcher.stop()


def _plant():
    boiler = Block(
        id="112/10021",
        type="boiler",
        roles={
            "temperature": "sensor.boiler",
            "ash_limit": "sensor.ash_limit",
            "consumption_total": "sensor.total",
        },
    )
    buffer = Block(
        id="112/10251",
        type="buffer",
        roles={
            "top": "sensor.buf_top",
            "sensor_1": "sensor.buf_1",
            "sensor_2": "sensor.buf_2",
        },
    )
    circuit = Block(
        id="112/10101",
        type="heating_circuit",
        roles={"flow": "sensor.flow", "pump": "sensor.pump", "slot_0_0": "sensor.slot"},
    )
    return [boiler, buffer, circuit], {"outside": "sensor.outside"}


def test_card_entities_without_settings():
    """Detected roles and plant values; slots and calculation-only roles stay slow."""
    blocks, plant = _plant()
    assert card_entities(blocks, plant, {}) == {
        "sensor.boiler",
        "sensor.buf_top",
        "sensor.buf_1",
        "sensor.buf_2",
        "sensor.flow",
        "sensor.pump",
        "sensor.outside",
    }


def test_card_entities_follow_card_settings():
    """Hidden parts and hidden roles drop out, hand-picked values come in."""
    blocks, plant = _plant()
    card = {
        "hidden": ["112/10101"],
        "roles": {
            "112/10021": {"temperature": "sensor.other_boiler"},
            "112/10251": {"middle": "sensor.buf_mid"},
            "plant": {"outside": "-"},
            "manual1": {"temperature": "sensor.stove"},
        },
        "extra": [{"id": "manual1", "type": "external_heat"}],
    }
    assert card_entities(blocks, plant, card) == {
        "sensor.other_boiler",
        "sensor.buf_top",
        "sensor.buf_mid",  # numbered buffer sensors replaced by the picked one
        "sensor.stove",
    }


def test_entity_uris_only_for_this_entry():
    """Entities of other integrations have no ETA address and are skipped."""
    uid_of = {
        "sensor.flow": "eta_s1_112_10101_0_0_12241",
        "number.setpoint": "eta_s1_112_10101_0_0_12125_writable",
    }
    assert entity_uris(
        {"sensor.flow", "number.setpoint", "sensor.other_integration"}, uid_of, "s1"
    ) == {"/112/10101/0/0/12241", "/112/10101/0/0/12125"}


async def test_fast_label_is_created_once(hass):
    """The label exists after setup, keeps working when renamed, returns if deleted."""
    label_reg = lr.async_get(hass)
    async_ensure_fast_label(hass)
    label = label_reg.async_get_label(FAST_UPDATE_LABEL_ID)
    assert label is not None
    assert label.name == FAST_UPDATE_LABEL_NAME

    label_reg.async_update(FAST_UPDATE_LABEL_ID, name="Schnell")
    async_ensure_fast_label(hass)
    assert len(label_reg.async_list_labels()) == 1

    label_reg.async_delete(FAST_UPDATE_LABEL_ID)
    async_ensure_fast_label(hass)
    assert label_reg.async_get_label(FAST_UPDATE_LABEL_ID) is not None


async def test_labelled_entities_are_polled_fast(hass):
    """An entity with the label joins the fast poll, without it it does not."""
    entry = MockConfigEntry(domain=DOMAIN, data={STABLE_ID: "s1"})
    entry.add_to_hass(hass)
    ent_reg = er.async_get(hass)
    flow = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        "eta_s1_112_10531_0_0_13000",
        config_entry=entry,
        suggested_object_id="fwm_durchfluss",
    )
    assert async_fast_uris(hass, entry) == set()

    async_ensure_fast_label(hass)
    ent_reg.async_update_entity(flow.entity_id, labels={FAST_UPDATE_LABEL_ID})
    assert async_fast_uris(hass, entry) == {"/112/10531/0/0/13000"}
