"""Tests for the one-time collection of the raw ETA API data."""

import asyncio
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.eta_webservices.const import DOMAIN, INSTANCE_UUID
from custom_components.eta_webservices.utils import raw_data
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError

UUID = "1234-uuid"
CONFIG = {CONF_HOST: "1.2.3.4", CONF_PORT: 8080, INSTANCE_UUID: UUID}
RESPONSES = {"/user/menu": "<menu/>", "/user/var//120/1": "<value/>"}


def _store(stored=None):
    store = Mock()
    store.async_load = AsyncMock(return_value=stored)
    store.async_save = AsyncMock()
    store.async_remove = AsyncMock()
    return store


def _entry():
    entry = MagicMock()
    entry.entry_id = "entry1"
    entry.title = "ETA Boiler"
    return entry


def _hass():
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {}
    return hass


async def test_start_skips_collection_if_stored():
    """No background task is started if data is stored already."""
    entry = _entry()
    with patch.object(raw_data, "_store", return_value=_store({"version": 1})):
        await raw_data.async_start_raw_data_collection(_hass(), entry, CONFIG)

    entry.async_create_background_task.assert_not_called()


async def test_start_creates_background_task():
    """Without stored data the collection starts as an entry background task."""
    entry = _entry()
    hass = _hass()
    with (
        patch.object(raw_data, "_store", return_value=_store(None)) as store_factory,
        patch.object(raw_data, "_async_collect_raw_data", Mock(return_value="coro")),
    ):
        await raw_data.async_start_raw_data_collection(hass, entry, CONFIG)

    store_factory.assert_called_once_with(hass, "entry1")
    entry.async_create_background_task.assert_called_once_with(
        hass, "coro", f"{DOMAIN}_raw_data_entry1"
    )


async def test_start_force_overwrites_stored_data():
    """With force=True the collection starts even if data is stored already."""
    entry = _entry()
    hass = _hass()
    store = _store({"version": 1, "responses": {}})
    with (
        patch.object(raw_data, "_store", return_value=store),
        patch.object(raw_data, "_async_collect_raw_data", Mock(return_value="coro")),
    ):
        await raw_data.async_start_raw_data_collection(hass, entry, CONFIG, force=True)

    store.async_load.assert_not_awaited()
    entry.async_create_background_task.assert_called_once_with(
        hass, "coro", f"{DOMAIN}_raw_data_entry1"
    )


async def test_start_while_running():
    """A running collection blocks a forced restart and skips a normal start."""
    entry = _entry()
    hass = _hass()
    release = asyncio.Event()
    started: list[asyncio.Task] = []

    async def _collect(*_args):
        await release.wait()

    def _create_task(_hass, coro, _name):
        started.append(asyncio.create_task(coro))
        return started[-1]

    entry.async_create_background_task.side_effect = _create_task
    store = _store(None)
    with (
        patch.object(raw_data, "_store", return_value=store),
        patch.object(raw_data, "_async_collect_raw_data", _collect),
    ):
        await raw_data.async_start_raw_data_collection(hass, entry, CONFIG)
        assert len(started) == 1

        with pytest.raises(HomeAssistantError) as err:
            await raw_data.async_start_raw_data_collection(
                hass, entry, CONFIG, force=True
            )
        assert err.value.translation_key == "raw_data_already_running"
        assert err.value.translation_placeholders == {"name": "ETA Boiler"}

        store.async_load.reset_mock()
        await raw_data.async_start_raw_data_collection(hass, entry, CONFIG)
        store.async_load.assert_not_awaited()
        assert len(started) == 1

        # Once finished, the task is forgotten and a forced restart works again.
        release.set()
        await started[0]
        assert hass.data[raw_data._TASKS_KEY] == {}
        await raw_data.async_start_raw_data_collection(hass, entry, CONFIG, force=True)
        assert len(started) == 2
        await started[1]


async def test_collect_without_uuid_stores_empty_uuid():
    """A missing instance UUID does not stop the collection; it is stored empty."""
    entry = _entry()
    hass = _hass()
    store = _store(None)
    config = {CONF_HOST: "1.2.3.4", CONF_PORT: 8080}
    with (
        patch.object(raw_data, "_async_collect_raw_data", Mock(return_value="coro")),
        patch.object(raw_data, "_store", return_value=store),
    ):
        await raw_data.async_start_raw_data_collection(hass, entry, config)
    entry.async_create_background_task.assert_called_once()

    with _patched_collection(store, AsyncMock(return_value=dict(RESPONSES))):
        await raw_data._async_collect_raw_data(hass, entry, config)

    saved = store.async_save.await_args.args[0]
    assert saved[INSTANCE_UUID] == ""
    assert saved["responses"] == RESPONSES


@contextmanager
def _patched_collection(store, get_all_raw_responses):
    """Patch everything _async_collect_raw_data talks to.

    Yields the EtaAPI class mock and the persistent notification mock.
    """
    api = Mock()
    api.get_all_raw_responses = get_all_raw_responses
    texts = {f"component.{DOMAIN}.exceptions.raw_data_finished.message": "Done: {name}"}
    with (
        patch.object(raw_data, "_store", return_value=store),
        patch.object(raw_data, "EtaAPI", return_value=api) as eta_api,
        patch.object(raw_data, "async_get_clientsession"),
        patch.object(
            raw_data.translation,
            "async_get_translations",
            AsyncMock(return_value=texts),
        ),
        patch.object(raw_data.persistent_notification, "async_create") as notification,
    ):
        yield eta_api, notification


async def test_collect_stores_responses_and_notifies():
    """The responses plus the instance UUID are stored, then the user is notified."""
    store = _store()
    hass = _hass()
    with (
        patch.object(
            raw_data.dt_util,
            "utcnow",
            return_value=datetime(2026, 11, 24, 10, 0, tzinfo=UTC),
        ),
        _patched_collection(store, AsyncMock(return_value=dict(RESPONSES))) as (
            eta_api,
            notification,
        ),
    ):
        await raw_data._async_collect_raw_data(hass, _entry(), CONFIG)

    semaphore = eta_api.call_args.kwargs["request_semaphore"]
    assert semaphore._value == raw_data.RAW_DATA_MAX_PARALLEL_REQUESTS
    store.async_save.assert_awaited_once_with(
        {
            "version": raw_data.RAW_DATA_VERSION,
            INSTANCE_UUID: UUID,
            "collected_at": "2026-11-24T10:00:00+00:00",
            "responses": RESPONSES,
        }
    )
    notification.assert_called_once_with(
        hass,
        # The texts themselves may change; only check that the translation is
        # used and that the title falls back when it is not translated.
        "Done: ETA Boiler",
        title=raw_data._text({}, "raw_data_title"),
        notification_id=f"{DOMAIN}_raw_data_entry1",
    )


async def test_collect_failure_stores_nothing():
    """A failed collection is only logged, so it is retried on the next setup."""
    store = _store()
    failing = AsyncMock(side_effect=RuntimeError("menu failed"))
    with _patched_collection(store, failing) as (_, notification):
        await raw_data._async_collect_raw_data(_hass(), _entry(), CONFIG)

    store.async_save.assert_not_awaited()
    notification.assert_not_called()


async def test_collect_cancel_stores_nothing():
    """A cancelled collection stores nothing and passes on the cancellation."""
    store = _store()
    cancelled = AsyncMock(side_effect=asyncio.CancelledError)
    with (
        _patched_collection(store, cancelled) as (_, notification),
        pytest.raises(asyncio.CancelledError),
    ):
        await raw_data._async_collect_raw_data(_hass(), _entry(), CONFIG)

    store.async_save.assert_not_awaited()
    notification.assert_not_called()


def test_broken_translation_falls_back():
    """A translation with unknown placeholders uses the fallback text."""
    texts = {f"component.{DOMAIN}.exceptions.raw_data_finished.message": "{oops}"}
    assert raw_data._text(texts, "raw_data_finished", name="X") == (
        raw_data._FALLBACK_TEXTS["raw_data_finished"].format(name="X")
    )


async def test_remove_raw_data_removes_store_file():
    """Deleting an entry removes its stored raw data."""
    store = _store()
    with patch.object(raw_data, "_store", return_value=store) as store_factory:
        await raw_data.async_remove_raw_data(hass := _hass(), "entry1")

    store_factory.assert_called_once_with(hass, "entry1")
    store.async_remove.assert_awaited_once()


async def test_get_raw_data_fills_missing_uuid():
    """Data collected before the entry had a UUID gets the entry's UUID."""
    entry = _entry()
    entry.data = {INSTANCE_UUID: UUID}
    stored = {"version": 1, INSTANCE_UUID: "", "responses": RESPONSES}
    with patch.object(raw_data, "_store", return_value=_store(stored)):
        data = await raw_data.async_get_raw_data(_hass(), entry)
    assert data[INSTANCE_UUID] == UUID


async def test_get_raw_data_keeps_stored_uuid():
    """A stored UUID is not replaced."""
    entry = _entry()
    entry.data = {INSTANCE_UUID: "other"}
    stored = {"version": 1, INSTANCE_UUID: UUID, "responses": RESPONSES}
    with patch.object(raw_data, "_store", return_value=_store(stored)):
        data = await raw_data.async_get_raw_data(_hass(), entry)
    assert data[INSTANCE_UUID] == UUID
