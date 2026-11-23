"""Tests for the one-time collection of the raw ETA API data."""

import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.eta_webservices.const import DOMAIN, INSTANCE_UUID
from custom_components.eta_webservices.utils import raw_data
from homeassistant.const import CONF_HOST, CONF_PORT

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
    return hass


@pytest.mark.parametrize(
    ("stored", "config"),
    [
        pytest.param({"/user/menu": "<menu/>"}, CONFIG, id="already-stored"),
        pytest.param(None, {CONF_HOST: "1.2.3.4", CONF_PORT: 8080}, id="no-uuid"),
    ],
)
async def test_start_skips_collection(stored, config):
    """No background task is started if data exists or the UUID is missing."""
    entry = _entry()
    with patch.object(raw_data, "_store", return_value=_store(stored)):
        await raw_data.async_start_raw_data_collection(_hass(), entry, config)

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


@contextmanager
def _patched_collection(store, get_all_raw_responses):
    """Patch everything _async_collect_raw_data talks to.

    Yields the EtaAPI class mock and the persistent notification mock.
    """
    api = Mock()
    api.get_all_raw_responses = get_all_raw_responses
    texts = {
        f"component.{DOMAIN}.exceptions.raw_data_finished.message": "{name}: {count}"
    }
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
    with _patched_collection(store, AsyncMock(return_value=dict(RESPONSES))) as (
        eta_api,
        notification,
    ):
        await raw_data._async_collect_raw_data(hass, _entry(), CONFIG)

    semaphore = eta_api.call_args.kwargs["request_semaphore"]
    assert semaphore._value == raw_data.RAW_DATA_MAX_PARALLEL_REQUESTS
    store.async_save.assert_awaited_once_with({**RESPONSES, INSTANCE_UUID: UUID})
    notification.assert_called_once_with(
        hass,
        "ETA Boiler: 2",
        title=raw_data._FALLBACK_TEXTS["raw_data_title"],
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
    assert raw_data._text(texts, "raw_data_finished", name="X", count=3) == (
        raw_data._FALLBACK_TEXTS["raw_data_finished"].format(name="X", count=3)
    )


async def test_remove_raw_data_removes_store_file():
    """Deleting an entry removes its stored raw data."""
    store = _store()
    with patch.object(raw_data, "_store", return_value=store) as store_factory:
        await raw_data.async_remove_raw_data(hass := _hass(), "entry1")

    store_factory.assert_called_once_with(hass, "entry1")
    store.async_remove.assert_awaited_once()
