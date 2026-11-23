"""Collect the raw responses of all ETA API endpoints once per config entry.

The responses are stored in the Home Assistant store (one file per entry) and
have the same format as the test fixture tests/fixtures/api_endpoint_data.json.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from ..api import EtaAPI  # noqa: TID252
from ..const import DOMAIN, INSTANCE_UUID  # noqa: TID252

STORAGE_VERSION = 1
RAW_DATA_MAX_PARALLEL_REQUESTS = 4

_LOGGER = logging.getLogger(__name__)

# Used if a translation is missing (the keys live in the "exceptions" category).
_FALLBACK_TEXTS = {
    "raw_data_title": "ETA: API data collected",
    "raw_data_finished": (
        "The raw API data of {name} was collected ({count} responses) and "
        "stored in Home Assistant."
    ),
}


def _store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.raw_eta_data_{entry_id}")


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
    hass: HomeAssistant, entry: ConfigEntry, config: dict[str, Any]
) -> None:
    """Start collecting the raw API data if it was not stored for this entry yet."""
    if not config.get(INSTANCE_UUID):
        return
    if await _store(hass, entry.entry_id).async_load() is not None:
        return
    # Cancelled by Home Assistant when the entry is unloaded; nothing is stored
    # then, so the collection runs again on the next setup.
    entry.async_create_background_task(
        hass,
        _async_collect_raw_data(hass, entry, config),
        f"{DOMAIN}_raw_data_{entry.entry_id}",
    )


async def async_remove_raw_data(hass: HomeAssistant, entry_id: str) -> None:
    """Remove the stored raw API data of a deleted entry."""
    await _store(hass, entry_id).async_remove()


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
        responses: dict[str, Any] = await eta_client.get_all_raw_responses(
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
    responses[INSTANCE_UUID] = config[INSTANCE_UUID]
    await _store(hass, entry.entry_id).async_save(responses)
    _LOGGER.info(
        "Raw API data collection for %s finished: %d responses stored", name, count
    )

    persistent_notification.async_create(
        hass,
        _text(texts, "raw_data_finished", name=name, count=count),
        title=_text(texts, "raw_data_title"),
        notification_id=raw_data_notification_id(entry.entry_id),
    )
