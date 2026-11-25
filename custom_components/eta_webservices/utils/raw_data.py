"""Collect the raw responses of all ETA API endpoints once per config entry.

The data is stored in the Home Assistant store (one file per entry) as
{"version": 1, "instance_uuid": ..., "collected_at": ..., "responses": {...}}.
"responses" has the same format as the test fixture
tests/fixtures/api_endpoint_data.json.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import translation
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from ..api import EtaAPI  # noqa: TID252
from ..const import DOMAIN, INSTANCE_UUID  # noqa: TID252

STORAGE_VERSION = 1
# Version of the layout of the stored dict.
RAW_DATA_VERSION = 1
# we use a separate SEMAPHORE to limit the requests, because using the shared one from the config
# would cause the coordinators to fail with a timeout error
RAW_DATA_MAX_PARALLEL_REQUESTS = 2

# hass.data key of the running collection tasks, by config entry id.
# this must be a global key in case of multiple config entries
_TASKS_KEY = f"{DOMAIN}_raw_data_tasks"

_LOGGER = logging.getLogger(__name__)

# Used if a translation is missing (the keys live in the "exceptions" category).
_FALLBACK_TEXTS = {
    "raw_data_title": "ETA: Upload Plant Data",
    "raw_data_finished": (
        "You can help further development of this integration by uploading your anonymized plant data for debugging purposes. "
        "Please click the button in the general ETA device ('ETA {name} > Upload Plant Data').\n\n"
        "This step is completely optional and no personal information is ever transmitted. "
        "You can download the integration diagnostic data to check what would be transmitted."
    ),
}


def _store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.raw_eta_data_{entry_id}")


def _running_tasks(hass: HomeAssistant) -> dict[str, asyncio.Task[None]]:
    return hass.data.setdefault(_TASKS_KEY, {})


def raw_data_notification_id(entry_id: str) -> str:
    """Return the id of the persistent raw data notification of an entry."""
    return f"{DOMAIN}_raw_data_{entry_id}"


def _text(texts: dict[str, str], key: str, **placeholders: Any) -> str:
    """Return a translated notification text with filled placeholders."""
    template = texts.get(
        f"component.{DOMAIN}.exceptions.{key}.message", _FALLBACK_TEXTS[key]
    )
    try:
        return template.format(**placeholders)
    except (KeyError, IndexError, ValueError):
        # A broken translation must never break the data collection.
        return _FALLBACK_TEXTS[key].format(**placeholders)


async def async_start_raw_data_collection(
    hass: HomeAssistant,
    entry: ConfigEntry,
    config: dict[str, Any],
    force: bool = False,
) -> None:
    """Start collecting the raw API data if it was not stored for this entry yet.

    :param force: Collect the data again and overwrite the stored data
    :raises HomeAssistantError: If force is set and a collection is already running
    """
    tasks = _running_tasks(hass)
    running = tasks.get(entry.entry_id)
    if running is not None and not running.done():
        if force:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="raw_data_already_running",
                translation_placeholders={"name": entry.title},
            )
        return
    if not force and await _store(hass, entry.entry_id).async_load() is not None:
        return
    # Cancelled by Home Assistant when the entry is unloaded; nothing is stored
    # then, so the collection runs again on the next setup.
    task = entry.async_create_background_task(
        hass,
        _async_collect_raw_data(hass, entry, config),
        f"{DOMAIN}_raw_data_{entry.entry_id}",
    )
    tasks[entry.entry_id] = task

    def _forget_task(finished: asyncio.Task[None]) -> None:
        if tasks.get(entry.entry_id) is finished:
            del tasks[entry.entry_id]

    task.add_done_callback(_forget_task)


async def async_remove_raw_data(hass: HomeAssistant, entry_id: str) -> None:
    """Remove the stored raw API data of a deleted entry."""
    await _store(hass, entry_id).async_remove()


async def async_get_raw_data(hass: HomeAssistant, entry: ConfigEntry) -> dict | None:
    """Load the stored raw API data and return them.

    Data collected while the entry had no UUID yet gets the entry's UUID.
    """
    data = await _store(hass, entry.entry_id).async_load()
    if data is not None and not data.get(INSTANCE_UUID):
        data[INSTANCE_UUID] = entry.data.get(INSTANCE_UUID) or ""
    return data


async def _async_collect_raw_data(
    hass: HomeAssistant, entry: ConfigEntry, config: dict[str, Any]
) -> None:
    """Request all endpoints, store the responses and notify the user."""
    name = entry.title
    texts = await translation.async_get_translations(
        hass, hass.config.language, "exceptions", {DOMAIN}
    )
    # Own limiter, so the regular updates keep running alongside.
    eta_client = EtaAPI(
        async_get_clientsession(hass),
        config[CONF_HOST],
        config[CONF_PORT],
        request_semaphore=asyncio.Semaphore(RAW_DATA_MAX_PARALLEL_REQUESTS),
    )

    def _on_progress(message: str, progress: float | None) -> None:
        _LOGGER.debug("Raw data collection for %s: %s", name, message)

    _LOGGER.info("Starting raw API data collection for %s", name)
    try:
        responses = await eta_client.get_all_raw_responses(
            progress_callback=_on_progress
        )
    except asyncio.CancelledError:
        _LOGGER.info(
            "Raw API data collection for %s cancelled, it is retried on the next setup",
            name,
        )
        raise
    except Exception:
        _LOGGER.exception(
            "Raw API data collection for %s failed, it is retried on the next setup",
            name,
        )
        return

    count = len(responses)
    await _store(hass, entry.entry_id).async_save(
        {
            "version": RAW_DATA_VERSION,
            # A missing UUID is stored empty instead of skipping the collection. This should never happen.
            "instance_uuid": config.get(INSTANCE_UUID) or "",
            "collected_at": dt_util.utcnow().isoformat(),
            "responses": responses,
        }
    )
    _LOGGER.info(
        "Raw API data collection for %s finished: %d responses stored", name, count
    )

    persistent_notification.async_create(
        hass,
        _text(texts, "raw_data_finished", name=name),
        title=_text(texts, "raw_data_title"),
        notification_id=raw_data_notification_id(entry.entry_id),
    )
