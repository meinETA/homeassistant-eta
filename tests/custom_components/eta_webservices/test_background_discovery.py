"""Tests for the endpoint discovery running in the background after setup."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_webservices._api.sensor_discovery_v11 import (
    SensorDiscoveryV11,
)
from custom_components.eta_webservices._api.sensor_discovery_v12 import (
    SensorDiscoveryV12,
)
from custom_components.eta_webservices.config_flow import (
    EtaFlowHandler,
    EtaOptionsFlowHandler,
)
from custom_components.eta_webservices.const import (
    BACKGROUND_DISCOVERY,
    CHOSEN_FLOAT_SENSORS,
    CHOSEN_PENDING_SENSORS,
    CHOSEN_SWITCHES,
    CHOSEN_TEXT_SENSORS,
    CHOSEN_WRITABLE_SENSORS,
    DEFAULT_MAX_PARALLEL_REQUESTS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    FLOAT_DICT,
    FORCE_LEGACY_MODE,
    MAX_PARALLEL_REQUESTS,
    PAUSE_COORDINATORS_START_TIMESTAMP,
    PENDING_DICT,
    REQUEST_SEMAPHORE,
    STABLE_ID,
    SWITCHES_DICT,
    TEXT_DICT,
    UPDATE_INTERVAL,
    WRITABLE_DICT,
)
from custom_components.eta_webservices.discovery import (
    _text,
    async_run_background_discovery,
    discovery_notification_id,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

GET_ALL_SENSORS = "custom_components.eta_webservices.discovery.EtaAPI.get_all_sensors"
NOTIFICATION = "custom_components.eta_webservices.discovery.persistent_notification"


def _endpoint(url: str, unit: str = "°C") -> dict:
    return {
        "url": url,
        "unit": unit,
        "value": 1.0,
        "endpoint_type": "DEFAULT",
        "friendly_name": "Test",
        "valid_values": None,
    }


def _add_entry(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=9,
        title="Boiler",
        data={
            CONF_NAME: "Boiler",
            CONF_HOST: "192.168.0.25",
            CONF_PORT: 8080,
            STABLE_ID: "boiler",
            FORCE_LEGACY_MODE: False,
            MAX_PARALLEL_REQUESTS: 5,
            UPDATE_INTERVAL: 60,
            BACKGROUND_DISCOVERY: True,
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    return entry


def _runtime_config(entry: MockConfigEntry) -> dict:
    return {**entry.data, REQUEST_SEMAPHORE: asyncio.Semaphore(5)}


async def _fill_dicts(
    force_legacy_mode,
    float_dict,
    switches_dict,
    text_dict,
    writable_dict,
    pending_dict,
    progress_callback=None,
    stable_id=None,
):
    assert stable_id == "boiler"
    progress_callback("halfway", 0.5)
    float_dict["eta_boiler_1"] = _endpoint("/1")
    switches_dict["eta_boiler_2"] = _endpoint("/2", "")
    text_dict["eta_boiler_3"] = _endpoint("/3", "")
    writable_dict["eta_boiler_1_writable"] = _endpoint("/1")
    pending_dict["eta_boiler_4"] = _endpoint("/4", "")
    return True


# ---------------------------------------------------------------------------
# async_run_background_discovery
# ---------------------------------------------------------------------------


async def test_discovery_stores_results_and_selects_everything(hass: HomeAssistant):
    """Results land in entry.data, everything is chosen and the flag is cleared."""
    entry = _add_entry(
        hass,
        # Stale selection copies must not shadow the new data; other options stay.
        options={FLOAT_DICT: {}, CHOSEN_FLOAT_SENSORS: [], UPDATE_INTERVAL: 30},
    )
    config = _runtime_config(entry)

    with (
        patch(GET_ALL_SENSORS, side_effect=_fill_dicts),
        patch(NOTIFICATION) as notification,
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        await async_run_background_discovery(hass, entry, config)

    update_entry.assert_called_once()
    data = update_entry.call_args.kwargs["data"]
    options = update_entry.call_args.kwargs["options"]
    assert BACKGROUND_DISCOVERY not in data
    assert set(data[FLOAT_DICT]) == {"eta_boiler_1"}
    assert data[CHOSEN_FLOAT_SENSORS] == ["eta_boiler_1"]
    assert data[CHOSEN_SWITCHES] == ["eta_boiler_2"]
    assert data[CHOSEN_TEXT_SENSORS] == ["eta_boiler_3"]
    assert data[CHOSEN_WRITABLE_SENSORS] == ["eta_boiler_1_writable"]
    assert data[CHOSEN_PENDING_SENSORS] == ["eta_boiler_4"]
    assert data[STABLE_ID] == "boiler"
    assert options == {UPDATE_INTERVAL: 30}
    assert config[PAUSE_COORDINATORS_START_TIMESTAMP] is None

    messages = [c.args[1] for c in notification.async_create.call_args_list]
    assert "Boiler: 0 %" in messages[0]
    assert any("Boiler: 50 %" in m for m in messages)
    assert "5 entities were added" in messages[-1]
    assert "compatibility mode" not in messages[-1]
    assert all(
        c.kwargs["notification_id"] == discovery_notification_id(entry.entry_id)
        for c in notification.async_create.call_args_list
    )


async def test_discovery_triggers_reload_via_update_listener(hass: HomeAssistant):
    """Storing the results fires the entry's update listener (which reloads)."""
    entry = _add_entry(hass)
    listener = AsyncMock()
    entry.add_update_listener(listener)

    with patch(GET_ALL_SENSORS, side_effect=_fill_dicts), patch(NOTIFICATION):
        await async_run_background_discovery(hass, entry, _runtime_config(entry))
        await hass.async_block_till_done()

    listener.assert_awaited_once()
    assert BACKGROUND_DISCOVERY not in entry.data
    assert entry.data[CHOSEN_FLOAT_SENSORS] == ["eta_boiler_1"]


async def test_discovery_mentions_legacy_mode(hass: HomeAssistant):
    """The finished notification mentions the compatibility mode if it was used."""
    entry = _add_entry(hass)

    async def _legacy(*args, **kwargs):
        await _fill_dicts(*args, **kwargs)
        return False

    with (
        patch(GET_ALL_SENSORS, side_effect=_legacy),
        patch(NOTIFICATION) as notification,
        patch.object(hass.config_entries, "async_update_entry"),
    ):
        await async_run_background_discovery(hass, entry, _runtime_config(entry))

    assert "compatibility mode" in notification.async_create.call_args.args[1]


async def test_discovery_failure_keeps_flag(hass: HomeAssistant):
    """A failed discovery stores nothing and shows a failure notification."""
    entry = _add_entry(hass)
    config = _runtime_config(entry)

    with (
        patch(GET_ALL_SENSORS, side_effect=RuntimeError("boom")),
        patch(NOTIFICATION) as notification,
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        await async_run_background_discovery(hass, entry, config)

    update_entry.assert_not_called()
    assert entry.data[BACKGROUND_DISCOVERY] is True
    assert "failed" in notification.async_create.call_args.args[1]
    assert config[PAUSE_COORDINATORS_START_TIMESTAMP] is None


async def test_discovery_cancel_keeps_flag_and_dismisses(hass: HomeAssistant):
    """Cancelling (unload/shutdown) re-raises, keeps the flag and cleans up."""
    entry = _add_entry(hass)
    config = _runtime_config(entry)
    started = asyncio.Event()

    async def _hang(*args, **kwargs):
        started.set()
        await asyncio.Event().wait()

    with (
        patch(GET_ALL_SENSORS, side_effect=_hang),
        patch(NOTIFICATION) as notification,
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        task = asyncio.create_task(async_run_background_discovery(hass, entry, config))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    update_entry.assert_not_called()
    notification.async_dismiss.assert_called_once_with(
        hass, discovery_notification_id(entry.entry_id)
    )
    assert entry.data[BACKGROUND_DISCOVERY] is True
    assert config[PAUSE_COORDINATORS_START_TIMESTAMP] is None


def test_text_uses_translation_and_falls_back():
    """Translated texts are used; missing or broken ones fall back to English."""
    key = f"component.{DOMAIN}.exceptions.discovery_finished.message"
    assert (
        _text({key: "{name}: {count} neu"}, "discovery_finished", name="A", count=3)
        == "A: 3 neu"
    )
    assert "3 entities" in _text({}, "discovery_finished", name="A", count=3)
    assert "3 entities" in _text(
        {key: "{unknown}"}, "discovery_finished", name="A", count=3
    )


# ---------------------------------------------------------------------------
# Clean cancellation of the discovery classes
# ---------------------------------------------------------------------------


class _HangingCounter:
    """Coroutine factory that never finishes and counts starts/cancellations."""

    def __init__(self) -> None:
        self.started = 0
        self.cancelled = 0

    async def __call__(self, *args, **kwargs):
        self.started += 1
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled += 1
            raise


def _http_mock(num_uris: int) -> MagicMock:
    http = MagicMock()
    http.get_sensors_dict = AsyncMock(
        return_value={f"_fub_node{i}": [f"/1/{i}"] for i in range(num_uris)}
    )
    http.host = "192.168.0.25"
    return http


async def _cancel_while_running(discovery, counter: _HangingCounter, expected: int):
    task = asyncio.create_task(discovery.get_all_sensors({}, {}, {}, {}, {}))
    for _ in range(20):
        await asyncio.sleep(0)
        if counter.started == expected:
            break
    assert counter.started == expected
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    # Every child request was cancelled together with the discovery.
    assert counter.cancelled == expected


async def test_v12_discovery_cancels_child_tasks():
    """Cancelling the v1.2 discovery cancels all pending varinfo requests."""
    http = _http_mock(10)
    discovery = SensorDiscoveryV12(http)
    counter = _HangingCounter()
    with patch.object(discovery, "_fetch_varinfo_raw", new=counter):
        await _cancel_while_running(discovery, counter, 10)


async def test_v12_discovery_cancels_data_tasks():
    """Cancelling during the value phase cancels all pending var requests."""
    http = _http_mock(10)
    counter = _HangingCounter()
    http.get_data_plus_raw = counter
    discovery = SensorDiscoveryV12(http)
    with patch.object(discovery, "_fetch_varinfo_raw", AsyncMock(return_value={})):
        await _cancel_while_running(discovery, counter, 10)


async def test_v11_discovery_cancels_child_tasks():
    """Cancelling the v1.1 discovery cancels all pending var requests."""
    http = _http_mock(10)
    counter = _HangingCounter()
    http.get_data_plus_raw = counter
    await _cancel_while_running(SensorDiscoveryV11(http), counter, 10)


# ---------------------------------------------------------------------------
# Config flow / options flow
# ---------------------------------------------------------------------------


def _make_config_flow(background: bool) -> EtaFlowHandler:
    flow = EtaFlowHandler()
    flow.hass = MagicMock()
    flow.async_update_progress = Mock()
    flow.data = {
        CONF_NAME: "Boiler",
        CONF_HOST: "192.168.0.25",
        CONF_PORT: 8080,
        FORCE_LEGACY_MODE: False,
        BACKGROUND_DISCOVERY: background,
        STABLE_ID: "boiler",
    }
    return flow


async def test_config_flow_background_mode_skips_discovery():
    """With background discovery, only the connection is checked."""
    flow = _make_config_flow(background=True)
    with (
        patch.object(flow, "_test_url", AsyncMock(return_value=1)),
        patch.object(flow, "_async_discover_possible_endpoints") as discover,
    ):
        await flow._async_validate_and_discover_endpoints("192.168.0.25", 8080, False)

    discover.assert_not_called()
    assert flow._endpoint_discovery_error is None


async def test_config_flow_foreground_mode_still_discovers():
    """Without background discovery, the flow discovers the endpoints as before."""
    flow = _make_config_flow(background=False)
    with (
        patch.object(flow, "_test_url", AsyncMock(return_value=1)),
        patch.object(flow, "_async_discover_possible_endpoints") as discover,
    ):
        await flow._async_validate_and_discover_endpoints("192.168.0.25", 8080, False)

    discover.assert_awaited_once()


@pytest.mark.parametrize(
    ("background", "next_step"),
    [(True, "create_background_entry"), (False, "select_entities")],
)
async def test_config_flow_progress_done_target(background, next_step):
    """The progress step continues with the step matching the discovery mode."""
    flow = _make_config_flow(background=background)
    done_task = asyncio.get_running_loop().create_future()
    done_task.set_result(None)
    flow._endpoint_discovery_task = done_task
    flow.async_show_progress_done = Mock(return_value="done")

    await flow.async_step_discover_entities()

    flow.async_show_progress_done.assert_called_once_with(next_step_id=next_step)


async def test_config_flow_creates_entry_with_pending_flag():
    """The background entry has the flag, no discovery data and no transient option."""
    flow = _make_config_flow(background=True)
    flow.async_create_entry = Mock(return_value="created")

    assert await flow.async_step_create_background_entry() == "created"

    data = flow.async_create_entry.call_args.kwargs["data"]
    assert flow.async_create_entry.call_args.kwargs["title"] == "Boiler"
    assert data[BACKGROUND_DISCOVERY] is True
    assert data[STABLE_ID] == "boiler"
    assert data[MAX_PARALLEL_REQUESTS] == DEFAULT_MAX_PARALLEL_REQUESTS
    assert data[UPDATE_INTERVAL] == DEFAULT_UPDATE_INTERVAL
    for key in (FLOAT_DICT, SWITCHES_DICT, TEXT_DICT, WRITABLE_DICT, PENDING_DICT):
        assert key not in data


async def test_user_form_has_background_option_enabled_by_default():
    """The first form offers the background discovery, enabled by default."""
    flow = _make_config_flow(background=True)
    flow.async_show_form = Mock(return_value="form")

    await flow._show_config_form_user({CONF_HOST: "0.0.0.0", CONF_PORT: "8080"})

    schema = flow.async_show_form.call_args.kwargs["data_schema"].schema
    marker = next(key for key in schema if key == BACKGROUND_DISCOVERY)
    assert marker.default() is True


async def test_options_flow_aborts_while_discovery_pending():
    """The options flow refuses to start while the background discovery runs."""
    flow = EtaOptionsFlowHandler()
    flow.hass = MagicMock()
    flow._get_runtime_config = Mock(return_value={BACKGROUND_DISCOVERY: True})
    flow.async_abort = Mock(return_value="aborted")

    assert await flow.async_step_init() == "aborted"
    flow.async_abort.assert_called_once_with(reason="discovery_running")
