"""Endpoint discovery running in the background after the entry is set up.

The config flow can create an entry with BACKGROUND_DISCOVERY set instead of
discovering all endpoints itself (which takes several minutes). The discovery
then runs here; the results are stored in the entry, which triggers a reload so
all platforms create the new entities.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import translation
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtaAPI, ETAEndpoint
from .config_flow import _sanitize_selected_entity_ids
from .const import (
    BACKGROUND_DISCOVERY,
    CHOSEN_FLOAT_SENSORS,
    CHOSEN_PENDING_SENSORS,
    CHOSEN_SWITCHES,
    CHOSEN_TEXT_SENSORS,
    CHOSEN_WRITABLE_SENSORS,
    DEFAULT_MAX_PARALLEL_REQUESTS,
    DOMAIN,
    ENABLE_DEBUG_LOGGING,
    FLOAT_DICT,
    FORCE_LEGACY_MODE,
    MAX_PARALLEL_REQUESTS,
    PAUSE_COORDINATORS_START_TIMESTAMP,
    PENDING_DICT,
    REQUEST_SEMAPHORE,
    STABLE_ID,
    SWITCHES_DICT,
    TEXT_DICT,
    WRITABLE_DICT,
)

_LOGGER = logging.getLogger(__name__)

# Keys holding the discovery result; stale copies in the options would shadow
# the new data, because setup merges the options over the data.
_DISCOVERY_RESULT_KEYS = (
    FLOAT_DICT,
    SWITCHES_DICT,
    TEXT_DICT,
    WRITABLE_DICT,
    PENDING_DICT,
    CHOSEN_FLOAT_SENSORS,
    CHOSEN_SWITCHES,
    CHOSEN_TEXT_SENSORS,
    CHOSEN_WRITABLE_SENSORS,
    CHOSEN_PENDING_SENSORS,
)

# Used if a translation is missing (the keys live in the "exceptions" category).
_FALLBACK_TEXTS = {
    "discovery_title": "ETA: entity discovery",
    "discovery_progress": (
        "Searching for entities of {name}: {percent} %. They are added "
        "automatically when the search is finished."
    ),
    "discovery_finished": (
        "Entity discovery for {name} finished: {count} entities were added."
    ),
    "discovery_legacy_mode": (
        "The terminal does not support API v1.2, so the compatibility mode was used."
    ),
    "discovery_failed": (
        "Entity discovery for {name} failed. It is retried on the next restart "
        "or reload of the integration. See the log for details."
    ),
}


def discovery_notification_id(entry_id: str) -> str:
    """Return the id of the persistent discovery notification of an entry."""
    return f"{DOMAIN}_discovery_{entry_id}"


def _text(texts: dict[str, str], key: str, **placeholders: Any) -> str:
    """Return a translated notification text with filled placeholders."""
    template = texts.get(
        f"component.{DOMAIN}.exceptions.{key}.message", _FALLBACK_TEXTS[key]
    )
    try:
        return template.format(**placeholders)
    except KeyError, IndexError, ValueError:
        # A broken translation must never stop the discovery.
        return _FALLBACK_TEXTS[key].format(**placeholders)


async def async_run_background_discovery(
    hass: HomeAssistant, entry: ConfigEntry, config: dict[str, Any]
) -> None:
    """Discover all endpoints and store them in the config entry.

    Cancelled by Home Assistant when the entry is unloaded or HA shuts down; the
    BACKGROUND_DISCOVERY flag then stays set, so the discovery runs again on the
    next setup.
    """
    notification_id = discovery_notification_id(entry.entry_id)
    texts = await translation.async_get_translations(
        hass, hass.config.language, "exceptions", {DOMAIN}
    )
    title = _text(texts, "discovery_title")
    name = entry.title

    @callback
    def _notify(message: str) -> None:
        persistent_notification.async_create(
            hass, message, title=title, notification_id=notification_id
        )

    last_progress_step = -1

    @callback
    def _on_progress(message: str, progress: float | None) -> None:
        nonlocal last_progress_step
        _LOGGER.debug("Background discovery progress: %s", message)
        if progress is None:
            return
        # Update the notification in steps of 10 %, not on every callback.
        progress_step = int(progress * 10)
        if progress_step <= last_progress_step:
            return
        last_progress_step = progress_step
        _notify(
            _text(texts, "discovery_progress", name=name, percent=progress_step * 10)
        )

    float_dict: dict[str, ETAEndpoint] = {}
    switches_dict: dict[str, ETAEndpoint] = {}
    text_dict: dict[str, ETAEndpoint] = {}
    writable_dict: dict[str, ETAEndpoint] = {}
    pending_dict: dict[str, ETAEndpoint] = {}

    eta_client = EtaAPI(
        async_get_clientsession(hass),
        config[CONF_HOST],
        config[CONF_PORT],
        max_concurrent_requests=config.get(
            MAX_PARALLEL_REQUESTS, DEFAULT_MAX_PARALLEL_REQUESTS
        ),
        request_semaphore=config.get(REQUEST_SEMAPHORE),
    )

    # The config flow used to raise the log level while it discovered the
    # endpoints; do the same here, because the flow is already finished.
    package_logger = _LOGGER.parent
    old_log_level: int | None = None
    if config.get(ENABLE_DEBUG_LOGGING) and package_logger is not None:
        old_log_level = package_logger.level
        package_logger.setLevel(logging.DEBUG)

    # Let the coordinators skip their updates (same as the options flow
    # rediscovery), so they do not time out waiting for the request semaphore.
    config[PAUSE_COORDINATORS_START_TIMESTAMP] = time.time()
    _on_progress("Starting background discovery", 0.0)
    _LOGGER.info("Starting background endpoint discovery for %s", name)

    try:
        is_new_api = await eta_client.get_all_sensors(
            config.get(FORCE_LEGACY_MODE, False),
            float_dict,
            switches_dict,
            text_dict,
            writable_dict,
            pending_dict,
            progress_callback=_on_progress,
            stable_id=config.get(STABLE_ID),
        )
    except asyncio.CancelledError:
        _LOGGER.info(
            "Background endpoint discovery for %s cancelled, it is retried on the next setup",
            name,
        )
        persistent_notification.async_dismiss(hass, notification_id)
        raise
    except Exception:
        _LOGGER.exception("Background endpoint discovery for %s failed", name)
        _notify(_text(texts, "discovery_failed", name=name))
        return
    finally:
        config[PAUSE_COORDINATORS_START_TIMESTAMP] = None
        if old_log_level is not None and package_logger is not None:
            package_logger.setLevel(old_log_level)

    # Select everything that was found (like "auto select all entities").
    chosen = _sanitize_selected_entity_ids(
        list(float_dict),
        list(switches_dict),
        list(text_dict),
        list(writable_dict),
        list(pending_dict),
    )
    new_data = {
        **entry.data,
        FLOAT_DICT: float_dict,
        SWITCHES_DICT: switches_dict,
        TEXT_DICT: text_dict,
        WRITABLE_DICT: writable_dict,
        PENDING_DICT: pending_dict,
        CHOSEN_FLOAT_SENSORS: chosen[0],
        CHOSEN_SWITCHES: chosen[1],
        CHOSEN_TEXT_SENSORS: chosen[2],
        CHOSEN_WRITABLE_SENSORS: chosen[3],
        CHOSEN_PENDING_SENSORS: chosen[4],
    }
    new_data.pop(BACKGROUND_DISCOVERY, None)
    new_options = {
        key: value
        for key, value in entry.options.items()
        if key not in _DISCOVERY_RESULT_KEYS
    }

    count = sum(len(chosen_list) for chosen_list in chosen)
    _LOGGER.info(
        "Background endpoint discovery for %s finished: %d entities found", name, count
    )
    message = _text(texts, "discovery_finished", name=name, count=count)
    if not is_new_api:
        message += "\n\n" + _text(texts, "discovery_legacy_mode")
    _notify(message)

    # Must be the last statement: the update listener reloads the entry, which
    # cancels this task. Nothing is awaited afterwards, so that is harmless.
    hass.config_entries.async_update_entry(entry, data=new_data, options=new_options)
